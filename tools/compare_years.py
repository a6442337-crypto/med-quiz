#!/usr/bin/env python3
"""교수님별 연도 간 변형 정도 비교 → 반복(repeat) / 소폭(minor) / 대폭(major) 1차 판정.

  python3 tools/compare_years.py <작업폴더> --profs 안지예,김학성,…  [--from 2020]

입력: <작업폴더>/all.json (extract_haeseol.py 출력) + 있으면 <작업폴더>/extra.json (손으로 보충한 문항, 같은 형식)
출력: <작업폴더>/modes.json  {교수: {mode, cnt{R,m,M}, pairs[{c,y,n,ry,rn,s,o}]}}

방법 (docs/variation-rules.md §2):
  올해 문항마다 이전 연도의 같은 교수 문항(본 문항 + 관련 기출) 중 가장 비슷한 것 하나와 짝짓는다.
  s = 지문 유사도(difflib), o = 선지 일치 비율.
  max(s,o) < 0.3 → 같은 개념 아님(비교 제외)
  s > 0.85 · o ≥ 0.8 · 정답 같음 → R(거의 그대로) / s ≥ 0.5 또는 o ≥ 0.5 → m(소폭) / 그 밖 → M(대폭)
  R ≥ 60% → repeat, M ≥ 40% → major, 그 밖 → minor, 비교 쌍 < 2 → minor(근거 부족)
이 결과는 1차 판정이다. 작업자는 pairs 중 몇 개를 직접 읽어 확인하고, 복원 해설의 총평
("선지만 바뀜", "작년과 동일" 등)과 다르면 고친다.
"""
import argparse, collections, difflib, json, pathlib, re

n = lambda s: re.sub(r'[\s\.,·()\-~]', '', s).lower()


def sim(a, b):
    return difflib.SequenceMatcher(None, n(a), n(b)).ratio()


def oov(a, b):
    A = {n(x) for x in a}; B = {n(x) for x in b}
    return len(A & B) / max(1, max(len(A), len(B)))


def ans_text(q):
    a = q.get('a')
    return n(q['opts'][a]) if a is not None and 0 <= a < len(q['opts']) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('work'); ap.add_argument('--profs', required=True); ap.add_argument('--from', dest='frm', type=int, default=2020)
    a = ap.parse_args()
    W = pathlib.Path(a.work)
    A = json.loads((W / 'all.json').read_text())
    if (W / 'extra.json').exists():
        A += json.loads((W / 'extra.json').read_text())
    mc = lambda q: len(q['opts']) >= 4
    res = {}
    for p in a.profs.split(','):
        mains = [q for q in A if q.get('prof') == p and mc(q)]
        pairs = []
        for q in mains:
            cands = [r for r in q.get('rel', []) if a.frm <= r['year'] < q['year'] and mc(r)] + [r for r in mains if r['year'] < q['year']]
            best = None
            for r in cands:
                s = sim(' '.join(q['stem']), ' '.join(r['stem'])); o = oov(q['opts'], r['opts'])
                if not best or max(s, o) > best[0]:
                    best = (max(s, o), s, o, r)
            if not best or best[0] < 0.3:
                continue
            _, s, o, r = best
            c = 'R' if s > 0.85 and o >= 0.8 and ans_text(q) == ans_text(r) else ('m' if s >= 0.5 or o >= 0.5 else 'M')
            pairs.append(dict(c=c, y=q['year'], n=q['num'], ry=r['year'], rn=r['num'], s=round(s, 2), o=round(o, 2)))
        cnt = collections.Counter(x['c'] for x in pairs); t = len(pairs)
        mode = 'minor' if t < 2 else 'repeat' if cnt['R'] >= 0.6 * t else 'major' if cnt['M'] >= 0.4 * t else 'minor'
        res[p] = dict(mode=mode, cnt=dict(cnt), pairs=pairs)
        print(f"{p:5} {mode:7} 그대로 {cnt['R']} · 소폭 {cnt['m']} · 대폭 {cnt['M']} (비교 {t}쌍)")
    (W / 'modes.json').write_text(json.dumps(res, ensure_ascii=False, indent=0))


if __name__ == '__main__':
    main()
