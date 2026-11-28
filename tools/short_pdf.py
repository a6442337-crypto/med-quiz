#!/usr/bin/env python3
"""주관식 기출+예상 문제집 PDF (meta extra_pdfs의 별도 PDF)

  python3 tools/short_pdf.py <slug> [--html 미리보기.html]

data/<slug>/extra_short.json(제목·학습부 목록·일러두기·문항 순서)과 past.json의 주관식(t:'s'),
variants.json의 예상 주관식(pred:true)으로 <slug>/<file>을 만든다. 순서 목록에 없는 문항은
근거(B)의 '학습부 NN번'으로 해당 학습부 끝에 붙는다. 글꼴 검사는 pdf.py와 같다.
"""
import argparse, html, json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import R
from build import load_subject

e = html.escape


def ytag(k):
    return f'<span class="tag">20{k[:2]} #{k[3:].replace("-1", "").replace("-s", "")}</span>'


def keyname(k):
    return f'20{k[:2]} #{k[3:].replace("-1", "").replace("-s", "")}'


def q_html(n, x, by_id, slug):
    if x.get('pred'):
        tags = '<span class="tag v">예상</span>'
        tags += '<span class="tag u">미검증</span>' if x.get('ok') is False else f'<span class="tag k2">{e(x.get("vb") or "")} 검증</span>'
        b = by_id.get(x.get('base'))
        if b:
            tags += '<span class="tag o">기출 변형 · ' + ', '.join(keyname(k) for k in b['keys']) + '</span>'
    else:
        tags = ''.join(ytag(k) for k in x['keys']) + '<span class="tag k2">기출</span>'
    tags += '<span class="tag s">주관식</span>'
    imgs = ''.join(f'<div class="img"><img src="{(R / slug / s).as_uri()}"></div>' for s in x.get('img', []))
    extra = ''
    if x.get('N') and not x['N'].startswith('주관식 예상'):
        extra = f'<div class="note">※ {e(x["N"])}</div>'
    if x.get('ok') is False and x.get('pred'):
        extra += '<div class="note">※ 미검증: 동기 정리본·교과서 기준 답이며 26 학습부와 대조하지 않았습니다.</div>'
    src = f'<div class="src">근거: {e(x["B"])}</div>' if x.get('B') else ''
    return (f'<div class="q"><div class="qh"><b>{n}.</b>{tags}</div><div class="stem">{x["stem"]}</div>{imgs}'
            f'<div class="blank">답: </div><div class="ans"><div class="h">정답 {e(x["A"])}</div>'
            f'<div>{e(x["E"])}</div>{src}{extra}</div></div>')


def render(slug):
    cfg = json.loads((R / 'data' / slug / 'extra_short.json').read_text())
    meta, qs = load_subject(slug)
    by_id = {x['id']: x for x in qs}
    items = [x for x in qs if (not x.get('v') and x.get('t') == 's') or x.get('pred')]
    sec_of = {i: s for s, i in cfg['order']}
    order = [i for _, i in cfg['order'] if i in by_id]
    for x in items:  # 순서 목록에 없는 새 문항
        if x['id'] not in sec_of:
            m = re.search(r'학습부 (\d+)번', x.get('B', ''))
            sec_of[x['id']] = m.group(1) if m else cfg['sections'][-1]['no']
            order.append(x['id'])
    ids = {x['id'] for x in items}
    order = [i for i in order if i in ids]
    np_ = sum(1 for i in order if not by_id[i].get('v')); nv = len(order) - np_
    fmt = dict(np=np_, nv=nv, n=len(order))
    rows = ''
    for s in cfg['sections']:
        a = sum(1 for i in order if sec_of[i] == s['no'] and not by_id[i].get('v'))
        b = sum(1 for i in order if sec_of[i] == s['no'] and by_id[i].get('v'))
        s['_c'] = (a, b)
        rows += f'<tr><td>{s["no"]}번 · {e(s["name"])}</td><td class="p">{e(s["prof"])}</td><td class="n">{a} / {b}</td></tr>'
    out = [f'<h1>{e(cfg["title"])}</h1><div class="sub">{e(cfg["sub"].format(**fmt))}</div>',
           f'<table class="parts"><tr><th>학습부</th><th>2026 담당</th><th>기출 / 예상</th></tr>{rows}</table>',
           '<div class="band">일러두기</div><ul class="notes">' + ''.join(f'<li>{n.format(**fmt)}</li>' for n in cfg['notes']) + '</ul>']
    n = 0
    for s in cfg['sections']:
        xs = [by_id[i] for i in order if sec_of[i] == s['no']]
        if not xs:
            continue
        a, b = s['_c']
        out.append(f'<section class="ch"><h2>{s["no"]}번 · {e(s["name"])}</h2><div class="chsub">{e(s["sub"])} · 기출 {a} · 예상 {b}문항</div>')
        for label, grp in (('기출 주관식', [x for x in xs if not x.get('v')]), ('변형·예상 주관식', [x for x in xs if x.get('v')])):
            if grp:
                out.append(f'<div class="band">{label}</div>')
                for x in grp:
                    n += 1; out.append(q_html(n, x, by_id, slug))
        out.append('</section>')
    css = (R / 'src/pdf.css').read_text()
    return cfg, f'<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><style>{css}</style></head><body>{"".join(out)}</body></html>'


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('slug'); ap.add_argument('--html')
    a = ap.parse_args()
    cfg, doc = render(a.slug)
    if a.html:
        pathlib.Path(a.html).write_text(doc)
    from weasyprint import HTML
    out = R / a.slug / cfg['file']
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix('.tmp.pdf')
    HTML(string=doc, base_url=str(R / a.slug)).write_pdf(tmp)
    fonts = set(re.findall(rb'/BaseFont\s*/([A-Za-z0-9+\-]+)', HTML(string='<style>' + (R / 'src/pdf.css').read_text() + '</style><p>한글 검사</p>').write_pdf(uncompressed_pdf=True)))
    if not any(b'Noto-Sans-CJK-KR' in f for f in fonts):
        tmp.unlink(missing_ok=True)
        raise SystemExit('PDF 중단: 한글 글꼴(Noto Sans CJK KR)이 들어가지 않습니다. bash tools/setup_env.sh 를 먼저 실행하세요.')
    tmp.replace(out)
    print(out.relative_to(R), f'{out.stat().st_size / 1e6:.1f}MB')


if __name__ == '__main__':
    main()
