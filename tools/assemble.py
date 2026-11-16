#!/usr/bin/env python3
"""추출한 문항 → data/<slug>/past.json (+ meta.json의 ch 갱신)

  python3 tools/assemble.py <slug> <작업폴더>

입력
  <작업폴더>/all.json, extra.json(선택)   extract_haeseol.py 출력 / 손으로 보충한 문항
  <작업폴더>/modes.json                   compare_years.py 출력 (교수님별 반복/소폭/대폭)
  data/<slug>/chapters.json               작업자가 쓰는 파트 구성 (형식은 AUTOMATION.md 4단계)
     [{"prof":"안지예","title":"Ⅰ. 소아신경 (…)","groups":[["소아 경련성 질환",["경련","발작"],[8]], …]}, …]
     groups = [소단원 이름, 지문·선지에 있으면 이 소단원으로 보낼 키워드, 관련 강의 번호들]
     마지막 group은 키워드가 비어 있어도 되는 기본 소단원.
동작
  - chapters.json에 있는 교수(= 2026년 담당)의 객관식만 남김 (선지 4개 이상, 빈 선지 없음)
  - 2026년 담당 교수 본 문항의 rel 중 --rel-years(기본 2020,2021) 문항을 그 교수 문항으로 추가
  - 선지 집합·정답·지문(유사도 > 0.8)이 같으면 하나로 합치고 keys에 연도·번호를 모두 단다
  - 해설 정리: 학습부·학우·해설자 표기, 강조 기호(22Pま 등) 제거
  - ok=false(미검증), ra=복원 답. B=관련 강의(시간표의 강의 번호·강의명)
  - 빠진 문항은 <작업폴더>/dropped.json 에 남김
"""
import argparse, collections, difflib, html, json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import R, load_config, jload
from timetable import lectures_of

CIR = '①②③④⑤⑥⑦'
n = lambda s: re.sub(r'[\s\.,·()\-~]', '', s).lower()
NEWPARA = re.compile(r'^([ㄱ-ㅎ]\.|[a-eA-E]\)|[가-하]\.|<|-|•|\d+\)|[A-Za-z가-힣 ]{1,20}\s*[:：])')


def sim(a, b):
    return difflib.SequenceMatcher(None, n(a), n(b)).ratio()


def clean_ex(lines):
    out = []
    for l in lines:
        l = re.sub(r'\d{2}\s*[Pp]?\s*[ま曰王]+', '', l); l = re.sub(r'[ま曰王]', '', l).strip()
        if not l or any(w in l for w in ('학습부', '학우', '해설자', '복원장')) or re.match(r'^(문제 해설|관련 이론|관련 기출)$', l):
            continue
        out.append(l)
    return re.sub(r'\s+', ' ', ' '.join(out)).strip()[:900]


def clean_opt(o):
    return re.split(r'\s*\[(?:출처|정답|풀이)\]', re.sub(r'\s+', ' ', o))[0].strip()


def stem_html(q):
    paras = []
    for x in q['stem']:
        x = re.sub(r'\[(?:출처|정답|풀이)\].*', '', x).strip()
        if not x:
            continue
        if paras and not NEWPARA.match(x):
            paras[-1] += ' ' + x
        else:
            paras.append(x)
    s = ''.join(f'<div>{html.escape(x)}</div>' for x in paras)
    if q.get('imgs') and not q.get('img_files'):
        s += '<div class="small" style="color:#b07a12">[그림 누락: 원본 복원 파일의 그림을 아직 넣지 못했습니다]</div>'
    return s


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('slug'); ap.add_argument('work')
    ap.add_argument('--rel-years', default='2020,2021')
    a = ap.parse_args()
    W = pathlib.Path(a.work); D = R / 'data' / a.slug
    A = json.loads((W / 'all.json').read_text())
    if (W / 'extra.json').exists():
        A += json.loads((W / 'extra.json').read_text())
    CH = json.loads((D / 'chapters.json').read_text())
    PIDX = {c['prof']: i for i, c in enumerate(CH)}
    relyears = {int(y) for y in a.rel_years.split(',') if y}
    cfg = load_config(); tt = jload('state/timetable.json', {})
    LEC = {l['num']: l['title'] for l in lectures_of(tt, cfg, a.slug)} if tt else {}

    def ok_q(q):
        return len(q['opts']) >= 4 and q.get('a') is not None and q['a'] < len(q['opts']) and min(len(o.strip()) for o in q['opts']) > 0

    items, drop = [], []
    for q in A:
        p = q.get('prof')
        if p not in PIDX:
            continue
        if not ok_q(q):
            if len(q['opts']) >= 4:
                drop.append({'year': q['year'], 'num': q['num'], 'why': '선지가 비었거나(그림 선지) 정답 없음'})
            continue
        e = clean_ex(q.get('ex', [])) or '복원 해설에 따로 설명이 없습니다.'
        items.append(dict(q, prof=p, opts=[clean_opt(o) for o in q['opts']], E=e))
        for r in q.get('rel', []):
            if r['year'] in relyears and ok_q(r):
                items.append(dict(r, prof=p, opts=[clean_opt(o) for o in r['opts']], rel=True,
                                  E=f"{q['year']}년 {q['num']}번 문항과 같은 주제입니다. 복원 자료에 이 문항의 해설은 따로 없어 정답만 실었습니다. 같은 주제 해설: {e[:400]}"))
    seen, uniq = {}, []
    for it in items:
        k = (it['year'], it['num'])
        if k in seen:
            if seen[k].get('rel') is True and it.get('rel') is not True:
                uniq[uniq.index(seen[k])] = it; seen[k] = it
            continue
        seen[k] = it; uniq.append(it)
    groups = []
    for it in sorted(uniq, key=lambda x: -x['year']):
        os_ = sorted(n(o) for o in it['opts']); ans = n(it['opts'][it['a']])
        for g in groups:
            h = g[0]
            if h['prof'] == it['prof'] and sorted(n(o) for o in h['opts']) == os_ and n(h['opts'][h['a']]) == ans \
                    and sim(' '.join(h['stem']), ' '.join(it['stem'])) > 0.8:
                g.append(it); break
        else:
            groups.append([it])

    def g_of(h):
        txt = (' '.join(h['stem']) + ' ' + ' '.join(h['opts'])).lower()
        for name, kws, _ in CH[PIDX[h['prof']]]['groups']:
            if any(k.lower() in txt for k in kws):
                return name
        return CH[PIDX[h['prof']]]['groups'][-1][0]
    glec = {name: lec for c in CH for name, _, lec in c['groups']}
    gorder = {name: i for c in CH for i, (name, _, _) in enumerate(c['groups'])}
    past = []
    for g in groups:
        h = g[0]; keys = [f"{x['year'] % 100:02d}-{x['num']:02d}" for x in g]
        N = h.get('note', '')
        if len({tuple(n(o) for o in x['opts']) for x in g}) > 1:
            N = (N + ' · ' if N else '') + '연도별 선지 순서가 달라 원래 번호는 ' + ', '.join(f"{x['year']} ⇒ {CIR[x['a']]}" for x in g)
        gname = g_of(h)
        B = '관련 강의: ' + ' · '.join(f'강의 {k:02d} {LEC.get(k, "")}'.strip() for k in glec[gname]) if glec[gname] else ''
        past.append(dict(id=keys[0], keys=keys, ch=PIDX[h['prof']], g=gname, stem=stem_html(h), o=h['opts'], a=h['a'],
                         A=CIR[h['a']], E=h['E'], B=B, N=N, img=h.get('img_files', []), v=False,
                         y=sorted({x['year'] for x in g}), ok=False, ra=CIR[h['a']]))
    past.sort(key=lambda x: (x['ch'], gorder[x['g']], -max(x['y']), x['id']))
    (D / 'past.json').write_text(json.dumps(past, ensure_ascii=False, indent=0))
    (W / 'dropped.json').write_text(json.dumps(drop, ensure_ascii=False, indent=0))
    modes = json.loads((W / 'modes.json').read_text()) if (W / 'modes.json').exists() else {}
    KO = {'R': '거의 그대로', 'm': '보기·수치·발문만 변경', 'M': '같은 개념을 다른 증례·형식으로'}
    ch = []
    for i, c in enumerate(CH):
        m = modes.get(c['prof'], {'mode': 'minor', 'cnt': {}}); cnt = m['cnt']; t = sum(cnt.values())
        why = (f"이전 연도 같은 개념 문항과 비교 {t}쌍: " + ', '.join(f"{KO[k]} {cnt.get(k, 0)}" for k in 'RmM')) if t >= 2 \
            else f'비교할 이전 연도 문항이 {t}쌍뿐 → 근거 부족, 소폭 변형으로 대비'
        ch.append(dict(id=i, title=c['title'], prof=c['prof'], mode=c.get('mode') or m['mode'], why=c.get('why') or why))
    mp = D / 'meta.json'
    meta = json.loads(mp.read_text()) if mp.exists() else {}
    meta['ch'] = ch
    meta['years'] = sorted({y for x in past for y in x['y']}, reverse=True)
    mp.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(f"기출 {len(past)}문항 · 연도 {dict(collections.Counter(y for x in past for y in x['y']))} · 제외 {len(drop)}")
    print(collections.Counter(CH[x['ch']]['prof'] for x in past))


if __name__ == '__main__':
    main()
