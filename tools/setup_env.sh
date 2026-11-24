#!/usr/bin/env bash
# 실행 환경 준비 + 검사. 매 실행(AUTOMATION.md 0단계) 처음에 한 번 돌린다.
#   bash tools/setup_env.sh        → 마지막 줄이 "환경 OK"면 통과, 아니면 exit 1 (무엇이 안 되는지 출력)
# 하는 일
#  1) 파이썬 패키지(weasyprint 70, Pillow, pyyaml, openpyxl): 가져오기·기능 검사 → 실패하면 --break-system-packages로 설치,
#     그래도 실패하면 강제 재설치. (이 컨테이너는 PEP 668 때문에 플래그 없는 pip가 조용히 실패한다)
#  2) weasyprint가 쓰는 pango 라이브러리 확인 → 없으면 apt로 설치
#  3) 한글 글꼴 "Noto Sans CJK KR": 없으면 apt(fonts-noto-cjk) → 그래도 없으면 저장소의 tools/fonts 부분 글꼴을 설치
#  4) 한글 한 줄을 실제 PDF로 만들어 글꼴이 박혔는지 확인
set -u
cd "$(dirname "$0")/.."
PY=python3
PIP="$PY -m pip install -q --disable-pip-version-check --root-user-action=ignore --break-system-packages"
log(){ echo "[setup] $*"; }

py_ok(){ $PY - <<'PYEOF' 2>/tmp/setup_py.err
import yaml, openpyxl
import PIL
from PIL import Image, ImageDraw, ImageFont, features
for f in ('freetype2', 'jpg', 'zlib'):
    assert features.check(f), f'Pillow 기능 없음: {f}'
import io; Image.new('RGB', (4, 4)).save(io.BytesIO(), 'JPEG')
import weasyprint
assert weasyprint.__version__.startswith('70'), f'weasyprint {weasyprint.__version__} (70 필요)'
PYEOF
}

apt_get(){ # apt 설치. 목록이 없으면 update 후 재시도
  DEBIAN_FRONTEND=noninteractive apt-get install -y -q "$@" >/tmp/setup_apt.log 2>&1 || {
    apt-get update -q >>/tmp/setup_apt.log 2>&1
    DEBIAN_FRONTEND=noninteractive apt-get install -y -q "$@" >>/tmp/setup_apt.log 2>&1; }
}

# 1) 파이썬 패키지
if ! py_ok; then
  log "파이썬 패키지 문제: $(tail -1 /tmp/setup_py.err) → 설치"
  $PIP weasyprint==70.0 pyyaml openpyxl pillow >/tmp/setup_pip.log 2>&1
  if ! py_ok; then
    log "아직 실패: $(tail -1 /tmp/setup_py.err) → Pillow·weasyprint 강제 재설치"
    $PIP --force-reinstall --no-cache-dir pillow weasyprint==70.0 >>/tmp/setup_pip.log 2>&1
  fi
fi

# 2) pango (weasyprint가 dlopen하는 시스템 라이브러리)
if ! $PY -c "import weasyprint.text.ffi" 2>/dev/null; then
  log "pango 라이브러리 없음 → apt 설치"
  apt_get libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libfontconfig1
fi

# 3) 한글 글꼴
has_font(){ fc-list : family | grep -q "Noto Sans CJK KR"; }
if ! has_font; then
  log "한글 글꼴 없음 → apt(fonts-noto-cjk)"
  apt_get fonts-noto-cjk fontconfig
  fc-cache -f >/dev/null 2>&1
fi
if ! has_font; then
  log "apt로도 설치하지 못함 → 저장소의 예비 글꼴(tools/fonts) 설치"
  mkdir -p ~/.local/share/fonts && cp tools/fonts/*.otf ~/.local/share/fonts/ && fc-cache -f >/dev/null 2>&1
fi

# 4) 최종 검사: 한글 PDF 한 장을 만들어 글꼴이 들어갔는지 본다
fail=0
py_ok || { echo "[setup] 실패: 파이썬 패키지 — $(tail -3 /tmp/setup_py.err | tr '\n' ' ')"; fail=1; }
has_font || { echo "[setup] 실패: 한글 글꼴 'Noto Sans CJK KR' 없음 (apt 기록: /tmp/setup_apt.log)"; fail=1; }
if [ $fail = 0 ]; then
  $PY - <<'PYEOF' || fail=1
import io, re
from weasyprint import HTML
pdf = HTML(string="<p style=\"font-family:'Noto Sans CJK KR'\">한글 글꼴 검사 ①②</p>").write_pdf(uncompressed_pdf=True)
fonts = set(re.findall(rb'/BaseFont\s*/([A-Za-z0-9+\-]+)', pdf))
if not any(b'Noto-Sans-CJK-KR' in f for f in fonts):
    raise SystemExit(f'[setup] 실패: PDF에 한글 글꼴이 들어가지 않음 (들어간 글꼴: {sorted(fonts)})')
PYEOF
fi
if [ $fail = 0 ]; then echo "환경 OK"; else echo "환경 실패 — PDF를 만들지 말고 위 내용을 보고에 적을 것"; exit 1; fi
