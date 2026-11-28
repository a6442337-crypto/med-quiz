#!/usr/bin/env python3
"""모의시험 출제 계획(교수님별 문항 수·객관식/주관식·변형 비율)을 만든다.

meta.json에 {"mock": {"total": 92, "per_hour": 2}} 이 있으면 build.py가 이 계획을 페이지에 넣고,
퀴즈 페이지 맨 위에 「모의시험」 패널이 생긴다. 실제 문항 뽑기는 브라우저가 시작할 때마다 새로 한다.

  python3 tools/mock.py neuro      계획 표 출력

계획 규칙
- 수업 시간: state/timetable.json에서 과목 접두어(config/subjects.yaml prefix)가 붙은 강의의 교시 수(빨간 글씨=시험 제외).
- 문항 수: 기본 시간당 per_hour 문항. total과 맞지 않으면 total을 수업 시간에 비례해 나누고(최대 나머지 방식),
  남는 문항은 나머지가 큰 교수님(동률이면 수업이 많은 교수님)께 1문항씩.
- 주관식 수: 그 교수님 기출 중 주관식 비율(주관식이 출제된 해만 셈, 같은 문항이 여러 해 나오면 해마다 셈) × 문항 수, 반올림.
  그 교수님 기출이 없으면 과목 전체 비율.
- 변형 비율: 파트 why의 연도 비교 쌍(거의 그대로 a, 보기·수치·발문만 변경 b, 다른 증례·형식 c) → (b+c)/(a+b+c).
  repeat 파트는 0(변형 문항을 넣지 않음). 쌍이 없으면 minor 0.5 · major 0.8.
"""
import collections, json, re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import R, load_config, jload

WHY = re.compile(r'거의 그대로 (\d+).*?발문만 변경 (\d+).*?형식으로 (\d+)')
DEFAULT_V = {'repeat': 0.0, 'minor': 0.5, 'major': 0.8}


def lecture_hours(slug):
    """교수 → {'hours': 교시 수, 'lectures': [강의 번호…]}"""
    cfg = load_config()
    s = next(x for x in cfg['subjects'] if x['slug'] == slug)
    tt = jload('state/timetable.json', {})
    per, prof = collections.defaultdict(set), {}
    for l in tt.get('lectures', []):
        if l['term'] != s['term'] or l['red']:
            continue
        for k in l['keys']:
            if k['prefix'] == s['prefix']:
                per[k['num']].update((l['date'], p) for p in l['periods'])
                prof[k['num']] = l['prof']
    out = {}
    for n in sorted(per):
        o = out.setdefault(prof[n], {'hours': 0, 'lectures': []})
        o['hours'] += len(per[n]); o['lectures'].append(n)
    return out, tt.get('title') or tt.get('version')


def vshare(chs):
    a = b = c = 0
    for ch in chs:
        m = WHY.search(ch.get('why', ''))
        if m:
            a += int(m[1]); b += int(m[2]); c += int(m[3])
    if any(ch['mode'] == 'repeat' for ch in chs):
        return 0.0, None
    if a + b + c:
        return round((b + c) / (a + b + c), 2), (a, b, c)
    return DEFAULT_V.get(chs[0]['mode'], 0.5), None


def plan(slug, meta, qs):
    cfgm = meta.get('mock')
    if not cfgm:
        return None
    total, ph = int(cfgm['total']), float(cfgm.get('per_hour', 2))
    hours, tt_ver = lecture_hours(slug)
    by_prof = collections.OrderedDict()
    for ch in meta['ch']:
        by_prof.setdefault(ch['prof'], []).append(ch)
    missing = [p for p in hours if p not in by_prof]
    if missing:
        raise SystemExit(f'{slug} 모의시험: 시간표 교수 {missing}가 meta.ch에 없습니다')
    profs = [p for p in by_prof if hours.get(p, {}).get('hours')]
    H = sum(hours[p]['hours'] for p in profs)
    if not H:
        raise SystemExit(f'{slug} 모의시험: 시간표에서 강의 시간을 찾지 못했습니다')
    # 문항 수: 기본 시간당 ph, total에 맞게 비례 배분(최대 나머지)
    raw = {p: total * hours[p]['hours'] / H for p in profs}
    n = {p: int(raw[p]) for p in profs}
    left = total - sum(n.values())
    order = sorted(profs, key=lambda p: (-(raw[p] - n[p]), -hours[p]['hours'], profs.index(p)))
    extra = set(order[:left])
    for p in extra:
        n[p] += 1
    # 주관식 비율: 주관식이 출제된 해만
    past = [x for x in qs if not x.get('v')]
    s_years = {y for x in past if x.get('t') == 's' for y in x.get('y', [])}
    chp = {c['id']: c['prof'] for c in meta['ch']}
    cnt = collections.Counter()
    for x in past:
        for y in x.get('y', []):
            if y in s_years:
                cnt[(chp[x['ch']], x.get('t') == 's')] += 1
    tot_s = sum(v for (p, s), v in cnt.items() if s); tot_all = sum(cnt.values())
    subj_ratio = tot_s / tot_all if tot_all else 0
    rows = []
    for p in profs:
        cs, cm = cnt[(p, True)], cnt[(p, False)]
        ratio = cs / (cs + cm) if cs + cm else subj_ratio
        ns = min(n[p], int(n[p] * ratio + 0.5))
        vs, pairs = vshare(by_prof[p])
        rows.append({'prof': p, 'ch': [c['id'] for c in by_prof[p]], 'mode': by_prof[p][0]['mode'],
                     'hours': hours[p]['hours'], 'lectures': hours[p]['lectures'], 'n': n[p], 'extra': p in extra,
                     'ns': ns, 'nm': n[p] - ns, 'sratio': round(ratio, 2), 'sbase': [cs, cm] if cs + cm else None,
                     'vshare': vs, 'pairs': pairs})
    return {'total': total, 'per_hour': ph, 'hours': H, 'timetable': tt_ver,
            's_years': sorted(s_years, reverse=True), 'subj_sratio': round(subj_ratio, 2), 'profs': rows}


if __name__ == '__main__':
    slug = sys.argv[1]
    d = R / 'data' / slug
    meta = json.loads((d / 'meta.json').read_text())
    qs = json.loads((d / 'past.json').read_text())
    pl = plan(slug, meta, qs)
    if not pl:
        sys.exit('meta.json에 mock 설정이 없습니다')
    print(f"총 {pl['total']}문항 · 수업 {pl['hours']}시간 · 주관식 비율 기준 연도 {pl['s_years']} · 시간표 {pl['timetable']}")
    for r in pl['profs']:
        print(f"{r['prof']:4} {r['hours']}시간 → {r['n']:2}문항{'(+1)' if r['extra'] else '    '} 객관식 {r['nm']:2} · 주관식 {r['ns']:2} "
              f"(주관식 {r['sratio']:.0%}) · 변형 {r['vshare']:.0%} {r['mode']}")
    print('합계', sum(r['n'] for r in pl['profs']), '· 객관식', sum(r['nm'] for r in pl['profs']), '· 주관식', sum(r['ns'] for r in pl['profs']))
