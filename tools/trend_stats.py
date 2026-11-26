#!/usr/bin/env python3
"""경향 분석용 기출 비교 통계 (AUTOMATION.md 3-10b).

  python3 tools/trend_stats.py <slug>          교수님별 연도별 문항 수·여러 해 동일 문항·소단원별 출제 연도
  python3 tools/trend_stats.py <slug> --pairs  최신 연도 문항마다 이전 연도의 가장 비슷한 문항(동일/유사/신규)

이 출력을 보고 trends.json의 analysis(과목)·profs[].analysis(교수님)에 판단을 쓴다.
"""
import json,sys,collections,re
PAIRS = r"""import json,sys,re,difflib,collections
m=json.load(open(f'data/{slug}/meta.json'));P=json.load(open(f'data/{slug}/past.json'))
ch={c['id']:c for c in m['ch']}
n=lambda s:re.sub(r'<[^>]+>|\[그림[^\]]*\]|\s','',s)
def sim(a,b): return difflib.SequenceMatcher(None,a,b).ratio()
by=collections.defaultdict(list)
for x in P: by[ch[x['ch']]['prof']].append(x)
for prof,xs in by.items():
    lat=max(y for x in xs for y in x['y'])
    print('##',prof)
    for x in xs:
        if lat not in x['y']: continue
        st=n(x['stem']); prev=[r for r in xs if r is not x and min(r['y'])<lat]
        best=max(prev,key=lambda r:sim(st,n(r['stem'])+''.join(r['o'])) ,default=None)
        s=sim(st,n(best['stem'])) if best else 0
        tag='동일' if len(x['y'])>1 else ('유사' if s>0.45 else '신규')
        ans=(x['o'][x['a']] if x.get('t')!='s' and x['o'] else x.get('A',''))[:18]
        print(f" {x['id']:10}{tag} {s:.2f} | {re.sub(r'<[^>]+>',' ',x['stem'])[:46].strip()} → {ans}" + (f"  ≈ {best['id']}" if best and tag!='신규' else ''))
"""
slug=sys.argv[1]
if '--pairs' in sys.argv:
    exec(compile(PAIRS,'pairs','exec')); sys.exit()
m=json.load(open(f'data/{slug}/meta.json'));P=json.load(open(f'data/{slug}/past.json'))
ch={c['id']:c for c in m['ch']}
by=collections.defaultdict(list)
for x in P: by[ch[x['ch']]['prof']].append(x)
for prof,xs in by.items():
    c=ch[xs[0]['ch']]
    yc=collections.Counter(y for x in xs for y in x['y'])
    rep=[x for x in xs if len(x['y'])>1]
    gy=collections.defaultdict(set)
    for x in xs:
        for y in x['y']: gy[x['g']].add(y)
    hot=sorted(gy.items(),key=lambda kv:-len(kv[1]))
    lat=max(yc) if yc else None
    L=[x for x in xs if lat in x['y']]; Lrep=[x for x in L if len(x['y'])>1]
    short=sum(1 for x in xs if x.get('t')=='s')
    print(f"## {prof} [{c['mode']}] {c['why']}")
    print('  연도별', dict(sorted(yc.items())), '| 주관식',short, '| 여러해 동일', len(rep), [x['id']+'('+','.join(str(y%100) for y in x['y'])+')' for x in rep][:8])
    print('  최신',lat,'문항',len(L),'중 이전과 동일',len(Lrep))
    print('  소단원별 출제연도', [(g,sorted(v)) for g,v in hot][:6])
