#!/usr/bin/env python3
"""data/<slug>/ → <slug>/index.html (과목 퀴즈) + index.html (과목 선택 홈)

  python3 tools/build.py            모든 과목 빌드 + 검사
  python3 tools/build.py --pdf neuro   PDF도 다시 생성 (tools/pdf.py)

빌드 전에 tools/validate.py 검사를 돌리고, 문제가 있으면 멈춘다.
"""
import re, argparse, html, json, pathlib, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import R, load_config, jload

GEN_STUB = '/* 이 과목은 자동 생성 문항이 없습니다 */'


def subjects():
    return sorted(p.parent.name for p in (R / 'data').glob('*/meta.json'))


def load_subject(slug):
    d = R / 'data' / slug
    meta = json.loads((d / 'meta.json').read_text())
    qs = json.loads((d / 'past.json').read_text())
    if (d / 'variants.json').exists():
        qs += json.loads((d / 'variants.json').read_text())
    return meta, qs


def verify_status(qs):
    """문항들의 검증 상태 → (라벨, 개수). 라벨은 가장 약한 쪽을 따른다.
    미검증(ok=false) / 초안 검증(vb='초안') / 검안 검증(vb='검안') / 교과서(vb='교과서', 강의 근거 없음) / 검증(vb 없음, 옛 데이터)"""
    c = {'미검증': 0, '초안': 0, '검안': 0, '교과서': 0, '검증': 0}
    for x in qs:
        c['미검증' if x.get('ok') is False else (x.get('vb') or '검증')] += 1
    n = len(qs)
    if c['미검증'] == n: label = '미검증'
    elif c['미검증']: label = '일부 검증'
    elif c['초안']: label = '초안 검증'
    elif c['검증']: label = '검증'
    else: label = '검안 검증'
    return label, c


MISSING = '[그림 누락'


def missing_figs(qs):
    """그림 누락 문항 → {학습부 번호: [문항 키…]}. 번호는 근거(B)의 '학습부 NN번' 또는 '강의 NN'에서 읽는다(없으면 '?')."""
    out = {}
    for x in qs:
        if MISSING not in x.get('stem', ''):
            continue
        nums = re.findall(r'학습부 (\d+)번', x.get('B', '')) or re.findall(r'강의 (\d+)', x.get('B', '')) or ['?']
        for n in dict.fromkeys(nums):
            out.setdefault(n, []).append(x['keys'][0] if x.get('keys') else x['id'])
    return dict(sorted(out.items(), key=lambda kv: (kv[0] == '?', int(kv[0]) if kv[0].isdigit() else 0)))


def foot_html(qs):
    """페이지 맨 아래 안내: 몇 번 학습부 사진(그림)을 읽어오지 못했는지"""
    mf = missing_figs(qs)
    if not mf:
        return ''
    k = lambda key: f"20{key[:2]} #{key[3:]}"
    rows = ''.join(f'<li><b>{"학습부 " + n.zfill(2) + "번" if n != "?" else "학습부 번호 미상"}</b> 사진 누락 — '
                   f'{len(v)}문항 ({", ".join(html.escape(k(x)) for x in v)})</li>' for n, v in mf.items())
    total = len({x for v in mf.values() for x in v})
    nums = ', '.join(n.zfill(2) + '번' for n in mf if n != '?')
    return (f'<footer class="miss"><details><summary><b>그림 누락 안내</b> · {total}문항 (학습부 {nums or "번호 미상"})</summary>'
            f'원본 복원 파일에서 그림을 읽어오지 못한 문항입니다. 해당 학습부(검안본) 파일을 받으면 그림을 채웁니다.<ul>{rows}</ul></details></footer>')


def pdf_name(meta):
    return f"{meta['name']}_기출문제집.pdf"


def build_subject(slug):
    meta, qs = load_subject(slug)
    past = [x for x in qs if not x.get('v')]
    var = [x for x in qs if x.get('v')]
    years = sorted(meta.get('years', []))
    yr = f"{years[0]}–{years[-1]}" if years else ''
    ns = sum(1 for x in past if x.get('t') == 's')
    sub = f"{yr} 복원 기출 {len(past)}문항" + (f"(주관식 {ns})" if ns else '') + (f" + 예상 변형 {len(var)}문항" if var else '')
    if (R / 'data' / slug / 'gen.js').exists():
        sub += '(일부는 매번 새로 생성)'
    label, vc = verify_status(qs)
    sub += {'미검증': ' · <b>미검증</b>(복원 해설 기준, 강의 자료가 올라오면 재검증)',
            '일부 검증': f" · <b>일부 검증</b>(검안 {vc['검안']} · 초안 {vc['초안']} · 미검증 {vc['미검증']}문항" + (f" · 교과서 {vc['교과서']}" if vc['교과서'] else '') + ")",
            '초안 검증': ' · 정답·해설은 2026년 강의 기준 · <b>초안으로 검증됨</b>(검안본이 올라오면 다시 확인)',
            '검안 검증': ' · 정답·해설은 2026년 강의 기준 · <b>검안으로 검증됨</b>' + (f"(강의 근거가 없는 {vc['교과서']}문항은 교과서·진료지침으로 확인)" if vc['교과서'] else ''),
            '검증': ' · 정답·해설은 2026년 강의 기준'}[label]
    pdf = R / slug / pdf_name(meta)
    pdf_link = f'<a class="pdf" href="{html.escape(pdf.name)}" download>문제집 PDF</a>' if pdf.exists() else ''
    sm = R / 'data' / slug / 'summary.json'  # 교수님별 요약자료 (선택, 별도 페이지 <slug>/summary.html)
    summary = json.loads(sm.read_text()) if sm.exists() else None
    if summary and any(p.get('items') for p in summary.get('profs', [])):
        pdf_link = '<a class="pdf" href="summary.html">요약자료</a>' + pdf_link  # 요약자료 버튼을 맨 앞에
    for ex in meta.get('extra_pdfs', []):  # 추가 PDF(예: 주관식 예상 문제집) — <slug>/extra/ 에 둔다(pdf.py가 <slug>/*.pdf를 지우므로)
        if (R / slug / ex['file']).exists():
            pdf_link += f'<a class="pdf" href="{html.escape(ex["file"])}" download>{html.escape(ex["label"])}</a>'
    if pdf_link:
        pdf_link = f'<div class="links">{pdf_link}</div>'
    gen = R / 'data' / slug / 'gen.js'
    tr = R / 'data' / slug / 'trends.json'  # 과목·교수님별 경향 분석 (선택, 페이지 맨 아래에 표시)
    trends = json.loads(tr.read_text()) if tr.exists() else None
    data = json.dumps({'meta': {k: v for k, v in meta.items() if k != 'notes'}, 'q': qs, 'trends': trends},
                      ensure_ascii=False).replace('</', '<\\/')
    page = ((R / 'src/quiz.html').read_text()
            .replace('__NAME__', html.escape(meta['name'])).replace('__SUB__', sub).replace('__PDF__', pdf_link).replace('__FOOT__', foot_html(past))
            .replace('__GEN__', gen.read_text() if gen.exists() else GEN_STUB).replace('__DATA__', data))
    (R / slug).mkdir(exist_ok=True)
    (R / slug / 'index.html').write_text(page)
    sp = R / slug / 'summary.html'
    if summary:
        for pr in summary.get('profs', []):  # 표 조각(HTML)은 data/<slug>/summary/에 두고 페이지에 그대로 넣는다
            for it in pr.get('items', []):
                if it.get('html'):
                    it['body'] = (R / 'data' / slug / it['html']).read_text()
        sdata = json.dumps({'meta': {'name': meta['name'], 'ch': meta['ch']}, 'summary': summary},
                           ensure_ascii=False).replace('</', '<\\/')
        sp.write_text((R / 'src/summary.html').read_text()
                      .replace('__NAME__', html.escape(meta['name'])).replace('__DATA__', sdata))
    elif sp.exists():
        sp.unlink()
    card = {'slug': slug, 'name': meta['name'], 'past': len(past), 'var': len(var), 'years': years,
            'verified': bool(meta.get('verified')), 'vlabel': label, 'vcount': vc, 'exam': meta.get('exam'), 'updated': meta.get('updated'),
            'pdf': f'{slug}/{pdf.name}' if pdf.exists() else None,
            'short': ns, 'missing_figs': {n: len(v) for n, v in missing_figs(past).items()},
            'summary': f'{slug}/summary.html' if summary else None,
            'modes': {m: sum(1 for c in meta['ch'] if c['mode'] == m) for m in ('repeat', 'minor', 'major')}}
    # 홈 화면은 과목별 card.json을 읽는다 → 과목 PR끼리 index.html을 두고 충돌하지 않음
    (R / slug / 'card.json').write_text(json.dumps(card, ensure_ascii=False) + '\n')
    return card


def build_home():
    """홈은 설정·시간표에만 의존한다(과목이 추가돼도 index.html은 바뀌지 않음).
    과목 카드는 브라우저가 <slug>/card.json을 읽어 그리고, 없으면 '준비 중'으로 보여준다."""
    cfg = load_config()
    tt = jload('state/timetable.json', {}).get('subjects', {})
    subs = [{'slug': s['slug'], 'name': s['name'], 'start': tt.get(s['slug'], {}).get('start'),
             'exam': tt.get(s['slug'], {}).get('exam'), 'auto': bool(s.get('auto'))}
            for s in cfg['subjects']]
    data = json.dumps({'subjects': subs}, ensure_ascii=False).replace('</', '<\\/')
    (R / 'index.html').write_text((R / 'src/home.html').read_text().replace('__DATA__', data))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--pdf', nargs='*', help='PDF를 다시 만들 과목 slug (빈 값이면 전부)')
    a = ap.parse_args()
    r = subprocess.run([sys.executable, str(R / 'tools/validate.py')])
    if r.returncode:
        sys.exit('검사 실패 → 빌드 중단')
    if a.pdf is not None:
        for s in (a.pdf or subjects()):
            subprocess.run([sys.executable, str(R / 'tools/pdf.py'), s], check=True)
    cards = [build_subject(s) for s in subjects()]
    build_home()
    for c in cards:
        print(f"{c['slug']:8} 기출 {c['past']} · 변형 {c['var']} · {c['vlabel']} · PDF {'있음' if c['pdf'] else '없음'}")


if __name__ == '__main__':
    main()
