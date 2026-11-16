"""공통 함수: 설정·상태 파일 읽기/쓰기, 한국 날짜."""
import datetime as dt, json, pathlib
import yaml

R = pathlib.Path(__file__).resolve().parent.parent
KST = dt.timezone(dt.timedelta(hours=9))


def today_kst():
    return dt.datetime.now(KST).date()


def load_config():
    cfg = yaml.safe_load((R / 'config/subjects.yaml').read_text())
    cfg['go_live'] = str(cfg['go_live'])
    return cfg


def subject(cfg, key):
    """slug 또는 과목명/접두어/드라이브 표기로 과목 찾기."""
    for s in cfg['subjects']:
        if key in (s['slug'], s['name'], s['prefix'], *s['drive_names']):
            return s
    raise SystemExit(f'config/subjects.yaml에 없는 과목: {key}')


def jload(path, default):
    p = R / path
    return json.loads(p.read_text()) if p.exists() else default


def jsave(path, obj):
    p = R / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + '\n')
