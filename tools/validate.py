#!/usr/bin/env python3
"""데이터 검사: 정답 인덱스, 선지 중복, 필수 필드, 그림 파일, 변형 원본, 금지어.

  python3 tools/validate.py [slug …]     문제가 있으면 exit 1
"""
import json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import R

FORBIDDEN = ['학습부']           # 사이트·PDF·데이터 어디에도 쓰지 않는다
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
    blob = json.dumps([meta, past, var], ensure_ascii=False)
    for w in FORBIDDEN:
        if w in blob: errs.append(f'{slug}: 금지어 "{w}" 포함')
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
    for p in list(gen.glob('*/gen.js')) + [R / 'src/quiz.html', R / 'src/home.html']:
        if p.exists() and any(w in p.read_text() for w in FORBIDDEN): allerr.append(f'{p.relative_to(R)}: 금지어 포함')
    for x in allerr: print('오류:', x)
    print(f'검사 {len(slugs)}과목 · 오류 {len(allerr)}개')
    sys.exit(1 if allerr else 0)


if __name__ == '__main__':
    main()
