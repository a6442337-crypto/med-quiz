#!/usr/bin/env python3
"""데이터 검사: 정답 인덱스, 선지 중복, 필수 필드, 그림 파일, 변형 원본, 요약자료, 금지어.

  python3 tools/validate.py [slug …]     문제가 있으면 exit 1
"""
import json, pathlib, re, sys, unicodedata
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import R

# 사이트·PDF·데이터에 넣지 않는 것: 학생 개인정보(전화번호, '○○ 학우' 같은 이름 표기).
# '학습부'라는 출처 표기는 허용(2026-11-16 사용자 결정).
FORBIDDEN_RE = [(re.compile(r'01[016789]-?\d{3,4}-?\d{4}'), '전화번호'), (re.compile(r'[가-힣]{2,4}\s*학우'), "'○○ 학우' 이름 표기"),
                # 학습부 파일명 형식 'NN번 과목 YYMMDD 교수P 담당학생' — 학생 이름이 들어 있음
                (re.compile(r'\d{2}번[\s_]*[가-힣]+[\s_]*\d{6}[\s_]*[가-힣]{2,4}[Pp][\s_]*[가-힣]{2,4}'), '학습부 파일명(학생 이름)')]
MODES = {'repeat', 'minor', 'major'}
REQ_PAST = ['id', 'keys', 'ch', 'g', 'stem', 'o', 'a', 'A', 'E', 'B', 'N', 'img', 'v', 'y', 'ok']
REQ_VAR = ['id', 'ch', 'base', 'lv', 'stem', 'o', 'a', 'E', 'B', 'N', 'img', 'v', 'ok']


def check(slug):
    errs, warns = [], []
    d = R / 'data' / slug
    meta = json.loads((d / 'meta.json').read_text())
    past = json.loads((d / 'past.json').read_text())
    var = json.loads((d / 'variants.json').read_text()) if (d / 'variants.json').exists() else []
    for k in ('slug', 'name', 'title', 'years', 'ch', 'verified'):
        if k not in meta: errs.append(f'meta.{k} 없음')
    chs = {c['id']: c for c in meta.get('ch', [])}
    for c in chs.values():
        if c.get('mode') not in MODES: errs.append(f"ch {c['id']} mode={c.get('mode')}")
        for k in ('title', 'prof', 'why'):
            if not c.get(k): errs.append(f"ch {c['id']} {k} 없음")
    ids = set()
    for x in past + var:
        tag = f"{slug}:{x.get('id')}"
        req = REQ_VAR if x.get('v') else REQ_PAST
        for k in req:
            if k not in x: errs.append(f'{tag} {k} 없음')
        if x.get('id') in ids: errs.append(f'{tag} id 중복')
        ids.add(x.get('id'))
        o = x.get('o', [])
        if not (2 <= len(o) <= 7): errs.append(f'{tag} 선지 수 {len(o)}')
        if len(set(map(str.strip, o))) != len(o):
            # 기출은 복원 원문 그대로 둘 수 있음(경고), 변형 문항은 오류
            (errs if x.get('v') else warns).append(f'{tag} 선지 중복')
        if not isinstance(x.get('a'), int) or not (0 <= x['a'] < len(o)): errs.append(f'{tag} 정답 인덱스 {x.get("a")}')
        if x.get('ch') not in chs: errs.append(f'{tag} ch {x.get("ch")} 없음')
        if not str(x.get('E', '')).strip(): errs.append(f'{tag} 해설 비어 있음')
        if x.get('vb') not in (None, '초안', '검안'): errs.append(f"{tag} vb={x.get('vb')} (초안|검안만 가능)")
        if x.get('ok') is False and x.get('vb'): errs.append(f'{tag} 미검증(ok:false)인데 vb가 있음')
        if x.get('ok') is True and not x.get('vb') and slug != 'endo': warns.append(f'{tag} 검증됨인데 vb(초안|검안) 없음')
        for s in x.get('img', []):
            if not (R / slug / s).exists(): errs.append(f'{tag} 그림 없음 {s}')
        if not x.get('v'):
            for k in x.get('keys', []):
                if not re.fullmatch(r'\d\d-\d+(-\d+)?', k): errs.append(f'{tag} key 형식 {k}')
            if sorted({2000 + int(k[:2]) for k in x.get('keys', [])}) != x.get('y'): errs.append(f'{tag} y가 keys와 다름')
    pids = {x['id'] for x in past}
    for x in var:
        if x.get('base') not in pids: errs.append(f"{slug}:{x['id']} 원본 {x.get('base')} 없음")
        if x.get('lv') not in ('minor', 'major'): errs.append(f"{slug}:{x['id']} lv={x.get('lv')}")
        if chs.get(x.get('ch'), {}).get('mode') == 'repeat': errs.append(f"{slug}:{x['id']} 반복 파트에 변형 문항")
    if var:  # 정답 위치 쏠림 경고 (변형 규칙: 고르게)
        cnt = [sum(1 for x in var if x['a'] == i) for i in range(5)]
        if max(cnt) > 0.4 * len(var) and len(var) >= 10: warns.append(f'{slug}: 변형 정답 위치 쏠림 {cnt}')
    trends = json.loads((d / 'trends.json').read_text()) if (d / 'trends.json').exists() else None
    if trends is not None:
        tprofs = {p.get('prof') for p in trends.get('profs', [])}
        for p in tprofs - {c['prof'] for c in chs.values()}:
            warns.append(f'{slug}: trends.json의 교수 {p}는 파트에 없음(표시 안 됨)')
    summary = json.loads((d / 'summary.json').read_text()) if (d / 'summary.json').exists() else None
    if summary is not None:  # 교수님별 요약자료 → <slug>/summary.html
        sprofs = [p.get('prof') for p in summary.get('profs', [])]
        if len(set(sprofs)) != len(sprofs): errs.append(f'{slug}: summary.json에 같은 교수가 두 번 있음')
        for p in set(sprofs) - {c['prof'] for c in chs.values()}:
            errs.append(f'{slug}: summary.json의 교수 {p}는 파트에 없음(표시 안 됨)')
        for p in summary.get('profs', []):
            for x in p.get('items', []):
                if not str(x.get('title', '')).strip(): errs.append(f"{slug}: 요약자료({p.get('prof')}) 제목 없음")
                if not x.get('img') or not (R / slug / x['img']).exists(): errs.append(f"{slug}: 요약자료 그림 없음 {x.get('img')}")
    # 복원 파일에서 온 글자는 자모가 분리된(NFD) 경우가 있어 합쳐서(NFC) 검사한다
    blob = unicodedata.normalize('NFC', json.dumps([meta, past, var, trends, summary], ensure_ascii=False))
    for rx, what in FORBIDDEN_RE:
        m = rx.search(blob)
        if m: errs.append(f'{slug}: {what} 포함 ({m.group(0)})')
    if not meta.get('verified') and any(x.get('ok') for x in past + var):
        warns.append(f'{slug}: meta.verified=false인데 ok=true 문항이 있음')
    return errs, warns


def main():
    slugs = sys.argv[1:] or sorted(p.parent.name for p in (R / 'data').glob('*/meta.json'))
    allerr = []
    for s in slugs:
        e, w = check(s)
        for x in w: print('경고:', x)
        allerr += e
    gen = R / 'data'
    for p in list(gen.glob('*/gen.js')) + [R / 'src/quiz.html', R / 'src/home.html', R / 'src/summary.html']:
        if p.exists() and any(rx.search(p.read_text()) for rx, _ in FORBIDDEN_RE): allerr.append(f'{p.relative_to(R)}: 개인정보 포함')
    for x in allerr: print('오류:', x)
    print(f'검사 {len(slugs)}과목 · 오류 {len(allerr)}개')
    sys.exit(1 if allerr else 0)


if __name__ == '__main__':
    main()
