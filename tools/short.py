#!/usr/bin/env python3
"""복원 해설에서 뽑은 주관식 → data/<slug>/past.json에 t='s' 문항으로 넣기(기존 주관식은 바꿔 끼움)

  python3 tools/short.py <slug> <작업폴더> <x.json> <연도> <큐> [<x.json> <연도> <큐> …]

입력
  <x.json>  extract_haeseol.py 출력. 선지가 4개 미만이고 답(ans)이 있는 본 문항만 주관식으로 쓴다.
            <큐>는 1 또는 2. 2큐(2Q) 문항은 key가 'YY-2Q-NN'이 된다(1큐와 번호가 겹치므로).
  <작업폴더>/short_extra.json  (선택) 작은 부처럼 대화로 들어와 손으로 옮긴 문항. 형식은 x.json 문항 + "q":1|2
  <작업폴더>/short_fix.json    (선택) {"acc":{id:[인정 답…]}, "self":[id…], "g":{id:소단원}, "A":{id:모범답},
                                "merge":[[남길 id, 합칠 id]…], "verify":{id:"26 학습부 NN번(검안) · 강의명"}, "img":{id:["figs/…"]}}
동작
  - chapters.json의 교수(2026 담당)만. 같은 교수·지문 유사도>0.75·답 유사도>0.4면 한 문항으로 묶음
  - o=[], a=-1, A=모범답, acc=자동 채점용 인정 답(답을 '/', ',', 'or', '혹은'으로 나눔), self 목록은 acc=[] → 스스로 채점
  - ok=false(미검증), verify에 있으면 ok=true·vb='검안'·B 교체
  - 해설의 학습부 파일명(학생 이름)은 잘라낸다. 그림이 있는 문항은 '그림 누락' 표시(→ 페이지 맨 아래 안내)
"""
import difflib, html, json, pathlib, re, sys, unicodedata
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from assemble import clean_ex, NEWPARA
from common import R, load_config, jload
from timetable import lectures_of

MISS = '<div class="small" style="color:#b07a12">[그림 누락: 원본 복원 파일의 그림을 아직 넣지 못했습니다]</div>'
NAME_RE = re.compile(r'\s*\d{1,2}번\s*[가-힣]+\s*\d{6}\s*\S+?[pP]\s+[가-힣]{2,4}')
nz = lambda s: re.sub(r'[\W_]', '', s).lower()


def stem_html(lines, imgs):
    paras = []
    for x in lines:
        x = re.sub(r'-{5,}', '', re.sub(r'\[(?:출처|정답|풀이)\].*', '', x)).strip()
        if not x: continue
        if paras and not NEWPARA.match(x): paras[-1] += ' ' + x
        else: paras.append(x)
    return ''.join(f'<div>{html.escape(p)}</div>' for p in paras) + (MISS if imgs else '')


def acc_of(ans):
    parts = re.split(r'\s*(?:/|,|;|\bor\b|혹은|또는)\s*', re.sub(r'\(([^)]*)\)', r'/\1', ans))
    return sorted({p.strip(' .·-–') for p in parts if len(p.strip(' .·-–')) >= 2 or p.strip().isdigit()}, key=len) or [ans]


def main():
    slug, W = sys.argv[1], pathlib.Path(sys.argv[2]); args = sys.argv[3:]
    D = R / 'data' / slug
    CH = json.loads((D / 'chapters.json').read_text()); PIDX = {c['prof']: i for i, c in enumerate(CH)}
    tt = jload('state/timetable.json', {}); LEC = {l['num']: l['title'] for l in lectures_of(tt, load_config(), slug)} if tt else {}
    glec = {n: l for c in CH for n, _, l in c['groups']}; gorder = {n: i for c in CH for i, (n, _, _) in enumerate(c['groups'])}
    Bof = lambda g: ('관련 강의: ' + ' · '.join(f'강의 {k:02d} {LEC.get(k, "")}'.strip() for k in glec[g])) if glec[g] else ''

    def g_of(p, txt):
        for name, kws, _ in CH[PIDX[p]]['groups']:
            if any(k.lower() in txt.lower() for k in kws): return name
        return CH[PIDX[p]]['groups'][-1][0]
    items = []
    for i in range(0, len(args), 3):
        for x in json.loads(unicodedata.normalize('NFC', open(args[i]).read())):
            if x['prof'] in PIDX and len(x['opts']) < 4 and x.get('ans', '').strip():
                items.append(dict(x, year=int(args[i + 1]), q=int(args[i + 2])))
    if (W / 'short_extra.json').exists():
        items += [x for x in json.loads((W / 'short_extra.json').read_text()) if x['prof'] in PIDX]
    groups = []
    for it in sorted(items, key=lambda x: -x['year']):
        for g in groups:
            h = g[0]
            if h['prof'] == it['prof'] and difflib.SequenceMatcher(None, nz(' '.join(h['stem'])), nz(' '.join(it['stem']))).ratio() > 0.75 \
                    and difflib.SequenceMatcher(None, nz(h['ans']), nz(it['ans'])).ratio() > 0.4:
                g.append(it); break
        else: groups.append([it])
    old = json.loads((D / 'past.json').read_text()); P = [x for x in old if x.get('t') != 's']; ids = {x['id'] for x in P}
    out = {}
    for g in groups:
        h = g[0]; keys = [f"{x['year'] % 100:02d}-{'2Q-' if x.get('q') == 2 else ''}{x['num']:02d}" for x in g]
        gname = g_of(h['prof'], ' '.join(h['stem']) + ' ' + h['ans'])
        e = NAME_RE.split(unicodedata.normalize('NFC', clean_ex(h.get('ex', []))))[0].strip() or '복원 해설에 따로 설명이 없습니다.'
        A = re.sub(r'\s*/\s*', ' / ', re.sub(r'\s*/\s*$', '', h['ans'].strip()))
        id_ = keys[0] + ('-s' if keys[0] in ids else '')
        out[id_] = dict(id=id_, keys=keys, ch=PIDX[h['prof']], g=gname, t='s', stem=stem_html(h['stem'], h.get('imgs')), o=[], a=-1, A=A,
                        acc=acc_of(h['ans']), E=e, B=Bof(gname), N='', img=[], v=False, y=sorted({x['year'] for x in g}), ok=False, ra=A)
    fx = json.loads((W / 'short_fix.json').read_text()) if (W / 'short_fix.json').exists() else {}
    for k, v in fx.get('acc', {}).items(): out[k]['acc'] = v
    for k in fx.get('self', []): out[k]['acc'] = []
    for k, v in fx.get('A', {}).items(): out[k]['A'] = v
    for k, v in fx.get('g', {}).items(): out[k].update(g=v, B=Bof(v))
    for k, v in fx.get('verify', {}).items(): out[k].update(ok=True, vb='검안', B=v)
    for k, v in fx.get('img', {}).items(): out[k].update(img=v, stem=out[k]['stem'].replace(MISS, ''))
    for keep, drop in fx.get('merge', []):
        out[keep]['keys'] += out[drop]['keys']; out[keep]['y'] = sorted(set(out[keep]['y'] + out.pop(drop)['y']))
    for it in sorted(out.values(), key=lambda x: (-max(x['y']), x['id'])):
        pos = [i for i, x in enumerate(P) if x['ch'] == it['ch'] and x['g'] == it['g']] or [i for i, x in enumerate(P) if x['ch'] == it['ch']] or [len(P) - 1]
        P.insert(max(pos) + 1, it)
    (D / 'past.json').write_text(json.dumps(P, ensure_ascii=False, indent=0))
    print(f'주관식 {len(items)}개 → {len(out)}문항 (그림 누락 {sum(1 for x in out.values() if MISS in x["stem"])})')


if __name__ == '__main__':
    main()
