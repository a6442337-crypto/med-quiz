#!/usr/bin/env python3
"""data/<slug>/ → <slug>/index.html (과목 퀴즈) + index.html (과목 선택 홈)

  python3 tools/build.py            모든 과목 빌드 + 검사
  python3 tools/build.py --pdf neuro   PDF도 다시 생성 (tools/pdf.py)

빌드 전에 tools/validate.py 검사를 돌리고, 문제가 있으면 멈춘다.
"""
import argparse, html, json, pathlib, subprocess, sys
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
    미검증(ok=false) / 초안 검증(vb='초안') / 검안 검증(vb='검안') / 검증(vb 없음, 옛 데이터)"""
    c = {'미검증': 0, '초안': 0, '검안': 0, '검증': 0}
    for x in qs:
        c['미검증' if x.get('ok') is False else (x.get('vb') or '검증')] += 1
    n = len(qs)
    if c['미검증'] == n: label = '미검증'
    elif c['미검증']: label = '일부 검증'
    elif c['초안']: label = '초안 검증'
    elif c['검증']: label = '검증'
    else: label = '검안 검증'
    return label, c


def pdf_name(meta):
    return f"{meta['name']}_기출문제집.pdf"


def build_subject(slug):
    meta, qs = load_subject(slug)
    past = [x for x in qs if not x.get('v')]
    var = [x for x in qs if x.get('v')]
    years = sorted(meta.get('years', []))
    yr = f"{years[0]}–{years[-1]}" if years else ''
    sub = f"{yr} 복원 기출 {len(past)}문항" + (f" + 예상 변형 {len(var)}문항" if var else '')
    if (R / 'data' / slug / 'gen.js').exists():
        sub += '(일부는 매번 새로 생성)'
    label, vc = verify_status(qs)
    sub += {'미검증': ' · <b>미검증</b>(복원 해설 기준, 강의 자료가 올라오면 재검증)',
            '일부 검증': f" · <b>일부 검증</b>(검안 {vc['검안']} · 초안 {vc['초안']} · 미검증 {vc['미검증']}문항)",
            '초안 검증': ' · 정답·해설은 2026년 강의 기준 · <b>초안으로 검증됨</b>(검안본이 올라오면 다시 확인)',
            '검안 검증': ' · 정답·해설은 2026년 강의 기준 · <b>검안으로 검증됨</b>',
            '검증': ' · 정답·해설은 2026년 강의 기준'}[label]
    pdf = R / slug / pdf_name(meta)
    pdf_link = f'<a class="pdf" href="{html.escape(pdf.name)}" download>문제집 PDF</a>' if pdf.exists() else ''
    sm = R / 'data' / slug / 'summary.json'  # 교수님별 요약자료 (선택, 별도 페이지 <slug>/summary.html)
    summary = json.loads(sm.read_text()) if sm.exists() else None
    if summary and any(p.get('items') for p in summary.get('profs', [])):
        pdf_link += '<a class="pdf" href="summary.html">요약자료</a>'
    if pdf_link:
        pdf_link = f'<div class="links">{pdf_link}</div>'
    gen = R / 'data' / slug / 'gen.js'
    tr = R / 'data' / slug / 'trends.json'  # 과목·교수님별 경향 분석 (선택, 페이지 맨 아래에 표시)
    trends = json.loads(tr.read_text()) if tr.exists() else None
    data = json.dumps({'meta': {k: v for k, v in meta.items() if k != 'notes'}, 'q': qs, 'trends': trends},
                      ensure_ascii=False).replace('</', '<\\/')
    page = ((R / 'src/quiz.html').read_text()
            .replace('__NAME__', html.escape(meta['name'])).replace('__SUB__', sub).replace('__PDF__', pdf_link)
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
