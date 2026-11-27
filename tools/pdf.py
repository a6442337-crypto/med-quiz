#!/usr/bin/env python3
"""data/<slug>/ → <slug>/<과목>_기출문제집.pdf  (WeasyPrint)

  python3 tools/pdf.py <slug> [--html 미리보기.html]

필요: bash tools/setup_env.sh (weasyprint 70 · 한글 글꼴 Noto Sans CJK KR 준비와 검사)
"""
import argparse, html, json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import R
from build import load_subject, pdf_name, verify_status

CIR = '①②③④⑤⑥⑦'
MODE = {'repeat': '반복 출제', 'minor': '소폭 변형', 'major': '대폭 변형'}
LV = {'minor': '소폭', 'major': '대폭'}
e = html.escape


def ytag(k):
    return f'<span class="tag">20{k[:2]} #{k[3:].replace("-1", "")}</span>'


def q_html(n, x, by_id):
    tags = ''
    if x.get('v'):
        b = by_id.get(x.get('base'))
        tags += f'<span class="tag v">변형 · {LV.get(x.get("lv"), "")}</span>'
        if b:
            tags += '<span class="tag o">원본 ' + ', '.join(f'20{k[:2]} #{k[3:].replace("-1", "")}' for k in b['keys']) + '</span>'
    else:
        tags += ''.join(ytag(k) for k in x['keys'])
    if x.get('ok') is False:
        tags += '<span class="tag u">미검증</span>'
    elif x.get('vb'):
        tags += f'<span class="tag {"k1" if x["vb"] == "초안" else "k2"}">{x["vb"]} 검증</span>'
    imgs = ''.join(f'<div class="img"><img src="{(R / x["_slug"] / s).as_uri()}"></div>' for s in x.get('img', []))
    if x.get('t') == 's':  # 주관식: 선지 대신 답 쓰는 칸
        tags += '<span class="tag s">주관식</span>'
        opts = '<div class="blank">답: </div>'
        A = x['A']
    else:
        opts = '<ol class="opts">' + ''.join(f'<li><span class="c">{CIR[i]}</span>{e(o)}</li>' for i, o in enumerate(x['o'])) + '</ol>'
        A = x.get('A') if not x.get('v') and x.get('A') else CIR[x['a']]
    extra = ''
    if x.get('ok') is False:
        extra += '<div class="note">※ 미검증: 2026년 강의 자료가 아직 없어 복원 해설의 답을 실었습니다.</div>'
    elif x.get('vb') == '초안':
        extra += '<div class="src">초안으로 검증됨 · 검안본이 올라오면 다시 확인합니다.</div>'
    elif x.get('vb') == '교과서':
        extra += '<div class="src">강의 자료에 근거가 없어 교과서·진료지침으로 확인함</div>'
    elif x.get('vb'):
        extra += '<div class="src">검안으로 검증됨</div>'
    if x.get('N') and not x.get('v'):
        extra += f'<div class="note">※ {e(x["N"])}</div>'
    if x.get('v') and x.get('vn'):
        extra += f'<div class="lv">변형 내용: {e(x["vn"])}</div>'
    src = f'<div class="src">근거: {e(x["B"])}</div>' if x.get('B') else ''
    return (f'<div class="q" id="q{n}"><div class="qh"><b>{n}.</b>{tags}</div><div class="stem">{x["stem"]}</div>{imgs}'
            f'{opts}<div class="ans"><div class="h">정답 {e(A)}</div>'
            f'<div>{e(x["E"])}</div>{src}{extra}</div></div>')


def render(slug):
    meta, qs = load_subject(slug)
    for x in qs:
        x['_slug'] = slug
    by_id = {x['id']: x for x in qs}
    past = [x for x in qs if not x.get('v')]
    var = [x for x in qs if x.get('v')]
    cnt = {c['id']: sum(1 for x in past if x['ch'] == c['id']) for c in meta['ch']}
    years = sorted(meta.get('years', []))
    exam = meta.get('exam')
    exam_s = f" · {meta.get('basis', 2026)} 총괄평가({int(exam[5:7])}/{int(exam[8:])}) 대비" if exam else ''
    sub = f"{' · '.join(map(str, years))} 복원 기출 · 총 {len(past)}문항{exam_s}"
    if var:
        sub += f" · 예상 변형 {len(var)}문항"
    rows = ''.join(f'<tr><td>{e(c["title"])}</td><td class="p">{e(c["prof"])}</td><td class="n">{cnt[c["id"]]}</td></tr>'
                   for c in meta['ch'])
    notes = ''.join(f'<li>{n}</li>' for n in meta.get('notes', []))
    out = [f'<h1>{e(meta["title"])}</h1><div class="sub">{e(sub)}</div>']
    label, vc = verify_status(qs)
    if label != '미검증':
        lv = {'검안 검증': ' 모든 문항을 <b>검안</b>으로 검증했습니다.' + (f" 다만 강의 자료에 근거가 없는 {vc['교과서']}문항은 교과서·진료지침으로 확인했습니다(문항마다 표시)." if vc.get('교과서') else ''),
              '초안 검증': f" <b>초안으로 검증됨</b>(초안 {vc['초안']} · 검안 {vc['검안']}문항) — 검안본이 올라오면 다시 확인해 새 판을 올립니다.",
              '일부 검증': f" <b>일부 검증</b> — 검안 {vc['검안']} · 초안 {vc['초안']} · 미검증 {vc['미검증']}문항(문항마다 표시). 강의 자료가 올라오는 대로 새 판을 올립니다.",
              '검증': ''}[label]
        out.append('<div class="principle"><b>정답 표기 원칙</b>: 복원 해설의 답을 그대로 따르지 않고, 2026년 강의 내용으로 다시 풀어 정답을 정했습니다. 복원 해설의 답과 다른 문항은 <span class="red">빨간 ※</span>로 표시했습니다.' + lv + '</div>')
    else:
        out.append('<div class="principle"><b>정답 표기 원칙</b>: <span class="red">미검증판</span> — 2026년 강의 자료가 아직 없어 복원 해설의 답을 실었습니다(문항마다 <b>미검증</b> 표시). 강의 자료가 올라오면 다시 검증해 새 판을 올립니다.</div>')
    out.append(f'<table class="parts"><tr><th>파트</th><th>2026 담당</th><th>문항</th></tr>{rows}</table>')
    if notes:
        out.append(f'<div class="band">일러두기</div><ul class="notes">{notes}</ul>')
    n = 0
    for c in meta['ch']:
        xs = [x for x in past if x['ch'] == c['id']]
        if not xs:
            continue
        out.append(f'<section class="ch"><h2>{e(c["title"])}</h2><div class="chsub">2026 담당: {e(c["prof"])} 교수님 · {len(xs)}문항 · {MODE.get(c["mode"], c["mode"])}</div>')
        g = None
        for x in xs:
            if x.get('g') != g:
                g = x.get('g'); out.append(f'<div class="band">{e(g or "")}</div>')
            n += 1; out.append(q_html(n, x, by_id))
        out.append('</section>')
    if var:
        out.append('<section class="ch"><h2>예상 변형 문항</h2><div class="chsub">교수님별 변형 수준(소폭: 보기·수치·발문 변경 / 대폭: 같은 개념을 다른 증례·형식으로)에 맞춰 만든 예상 문제입니다.</div>')
        for c in meta['ch']:
            xs = [x for x in var if x['ch'] == c['id']]
            if not xs:
                continue
            out.append(f'<div class="band">{e(c["title"])} · {e(c["prof"])}</div>')
            for x in xs:
                n += 1; out.append(q_html(n, x, by_id))
        out.append('</section>')
    css = (R / 'src/pdf.css').read_text()
    return f'<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><style>{css}</style></head><body>{"".join(out)}</body></html>'


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('slug'); ap.add_argument('--html')
    a = ap.parse_args()
    doc = render(a.slug)
    if a.html:
        pathlib.Path(a.html).write_text(doc)
    from weasyprint import HTML
    meta, _ = load_subject(a.slug)
    (R / a.slug).mkdir(exist_ok=True)
    out = R / a.slug / pdf_name(meta)
    # 먼저 임시 파일로 만들고, 한글 글꼴이 실제로 들어갔는지 확인한 뒤에만 기존 PDF를 바꾼다.
    # (글꼴이 없는 환경에서 만든 PDF는 한글이 □로 나온다 → 그런 PDF는 올리지 않는다)
    tmp = out.with_suffix('.tmp.pdf')
    HTML(string=doc, base_url=str(R / a.slug)).write_pdf(tmp)
    fonts = set(re.findall(rb'/BaseFont\s*/([A-Za-z0-9+\-]+)', HTML(string='<style>' + (R / 'src/pdf.css').read_text() + '</style><p>한글 검사</p>').write_pdf(uncompressed_pdf=True)))
    if not any(b'Noto-Sans-CJK-KR' in f for f in fonts):
        tmp.unlink(missing_ok=True)
        raise SystemExit(f'PDF 중단: 한글 글꼴(Noto Sans CJK KR)이 들어가지 않습니다 (들어간 글꼴 {sorted(fonts)}). '
                         'bash tools/setup_env.sh 를 먼저 실행하세요. 기존 PDF는 그대로 둡니다.')
    for old in (R / a.slug).glob('*.pdf'):
        if old != tmp:
            old.unlink()
    tmp.rename(out)
    print(out.relative_to(R), f'{out.stat().st_size / 1e6:.1f}MB')


if __name__ == '__main__':
    main()
