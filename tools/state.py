#!/usr/bin/env python3
"""과목별 처리 상태와 읽은 드라이브 파일 기록.

상태 파일 (과목마다 파일 하나 → 동시에 열린 PR끼리 충돌하지 않음)
  state/subjects/<slug>.json  {status, verified, years, missing_years, pr, updated, note}
     status: done(PR까지 올림) | skipped(만들지 않음)
     verified: true(26 학습부로 정답 검증) | false(미검증 → 학습부가 올라오면 재검증)
  state/sources/<slug>.json   {file_id: {name, account, kind, year, read}}
     kind: past(기출 복원) | guide(26 학습부) | other

진행 중인 작업은 상태 파일이 아니라 원격 브랜치 auto/<slug>(새 과목) ·
auto/<slug>-verify(재검증)로 판단한다. PR이 머지되기 전까지 main의 상태 파일은
바뀌지 않으므로, 브랜치가 있으면 '진행 중(검토 대기)'으로 보고 다시 만들지 않는다.

사용법
  python3 tools/state.py due [--today YYYY-MM-DD] [--subject 신경계학]
        오늘 할 일을 JSON으로 출력: {"action": "new"|"reverify"|"none", "slug": …, "waiting": […]}
  python3 tools/state.py show
  python3 tools/state.py set <slug> --status done --verified false --years 2025,2023 --missing 2024 --pr URL
  python3 tools/state.py source <slug> <file_id> --name "파일명" --account dept --kind past --year 2025
  python3 tools/state.py sources <slug>          이미 읽은 파일 목록
  python3 tools/state.py seen <slug> <file_id>   읽은 파일이면 exit 0, 아니면 1
"""
import argparse, json, subprocess, sys
from common import R, load_config, subject, jload, jsave, today_kst



def load_states():
    return {p.stem: json.loads(p.read_text()) for p in sorted((R / 'state/subjects').glob('*.json'))}


def load_sources(slug):
    return jload(f'state/sources/{slug}.json', {})


def remote_branches():
    try:
        out = subprocess.run(['git', '-C', str(R), 'ls-remote', '--heads', 'origin', 'auto/*'],
                             capture_output=True, text=True, timeout=60).stdout
    except Exception as e:  # 네트워크 문제면 안전하게 아무것도 안 함
        sys.exit(f'원격 브랜치를 확인하지 못했습니다: {e}')
    return {l.split('refs/heads/')[1] for l in out.splitlines() if 'refs/heads/' in l}


def due(today, forced=None):
    cfg = load_config()
    tt = jload('state/timetable.json', None)
    if not tt:
        sys.exit('state/timetable.json이 없습니다. 먼저 tools/timetable.py parse를 실행하세요.')
    st = load_states()
    busy = remote_branches()
    info = tt['subjects']
    if forced:
        s = subject(cfg, forced)
        slug = s['slug']
        if f'auto/{slug}' in busy:
            return {'action': 'none', 'reason': f'auto/{slug} 브랜치가 이미 있습니다(검토 대기 PR). 머지/삭제 후 다시 실행하세요.'}
        kind = 'reverify' if st.get(slug, {}).get('status') == 'done' and not st[slug].get('verified') else 'new'
        return {'action': kind, 'slug': slug, 'name': s['name'], **(info.get(slug) or {}), 'manual': True}
    cands = []
    for s in cfg['subjects']:
        i = info.get(s['slug']) or {}
        if not s.get('auto') or not i.get('start'):
            continue
        if i['start'] < cfg['go_live'] or i['start'] > today:
            continue
        if st.get(s['slug'], {}).get('status') in ('done', 'skipped') or f"auto/{s['slug']}" in busy:
            continue
        if i.get('exam') and i['exam'] < today:
            continue  # 시험이 이미 지난 과목은 만들지 않음
        cands.append((i['start'], cfg['subjects'].index(s), s, i))
    cands.sort(key=lambda x: (x[0], x[1]))
    if cands:
        _, _, s, i = cands[0]
        return {'action': 'new', 'slug': s['slug'], 'name': s['name'], **i,
                'waiting': [c[2]['slug'] for c in cands[1:]]}
    # 새 과목이 없으면 미검증 과목 중 하나(시험이 안 지난 것 우선)를 재검증 후보로
    rv = []
    for slug, v in st.items():
        if v.get('status') == 'done' and not v.get('verified') and f'auto/{slug}-verify' not in busy:
            i = info.get(slug) or {}
            rv.append((i.get('exam') or '9999', slug, i))
    rv.sort()
    if rv:
        _, slug, i = rv[0]
        s = subject(cfg, slug)
        return {'action': 'reverify-check', 'slug': slug, 'name': s['name'], **i,
                'others': [x[1] for x in rv[1:]]}
    return {'action': 'none', 'reason': '오늘 시작하는 과목도, 재검증할 과목도 없습니다.'}


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('due'); p.add_argument('--today'); p.add_argument('--subject')
    sp.add_parser('show')
    p = sp.add_parser('set'); p.add_argument('slug'); p.add_argument('--status')
    p.add_argument('--verified', choices=['true', 'false']); p.add_argument('--years')
    p.add_argument('--missing'); p.add_argument('--pr'); p.add_argument('--note')
    p = sp.add_parser('source'); p.add_argument('slug'); p.add_argument('file_id')
    p.add_argument('--name', required=True); p.add_argument('--account', default='dept')
    p.add_argument('--kind', default='past', choices=['past', 'guide', 'other']); p.add_argument('--year', type=int)
    p = sp.add_parser('sources'); p.add_argument('slug')
    p = sp.add_parser('seen'); p.add_argument('slug'); p.add_argument('file_id')
    a = ap.parse_args()
    if a.cmd == 'due':
        print(json.dumps(due(a.today or today_kst().isoformat(), a.subject), ensure_ascii=False, indent=1))
    elif a.cmd == 'show':
        print(json.dumps(load_states(), ensure_ascii=False, indent=1))
    elif a.cmd == 'set':
        cfg = load_config(); slug = subject(cfg, a.slug)['slug']
        v = jload(f'state/subjects/{slug}.json', {})
        if a.status: v['status'] = a.status
        if a.verified: v['verified'] = a.verified == 'true'
        if a.years is not None: v['years'] = [int(x) for x in a.years.split(',') if x]
        if a.missing is not None: v['missing_years'] = [int(x) for x in a.missing.split(',') if x]
        if a.pr: v['pr'] = a.pr
        if a.note: v['note'] = a.note
        v['updated'] = today_kst().isoformat()
        jsave(f'state/subjects/{slug}.json', v); print(json.dumps({slug: v}, ensure_ascii=False))
    elif a.cmd == 'source':
        cfg = load_config(); slug = subject(cfg, a.slug)['slug']
        src = load_sources(slug)
        src[a.file_id] = {'name': a.name, 'account': a.account, 'kind': a.kind,
                          'year': a.year, 'read': today_kst().isoformat()}
        jsave(f'state/sources/{slug}.json', src)
    elif a.cmd == 'sources':
        cfg = load_config(); slug = subject(cfg, a.slug)['slug']
        for fid, v in load_sources(slug).items():
            print(f"{v['kind']:5} {v.get('year') or '':4} {fid}  {v['name']}")
    elif a.cmd == 'seen':
        cfg = load_config(); slug = subject(cfg, a.slug)['slug']
        sys.exit(0 if a.file_id in load_sources(slug) else 1)


if __name__ == '__main__':
    main()
