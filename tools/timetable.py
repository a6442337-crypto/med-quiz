#!/usr/bin/env python3
"""시간표 시트(xlsx로 내보낸 파일)를 읽어 강의·시험·휴일·과목 시작일을 뽑는다.

시트는 Google Drive 커넥터의 download_file_content(exportMimeType=xlsx)로 받는다.
xlsx로 받아야 글자색(빨간 글씨=시험, 빨간 날짜=휴일)과 병합 셀이 남는다.

사용법
  python3 tools/timetable.py parse <시간표.xlsx> --title "v262_시간표_GY" [--today 2026-11-16]
      → state/timetable.json 갱신, 버전이 바뀌면 logs/timetable.log에 기록
  python3 tools/timetable.py lectures <slug>      과목 강의 목록(번호·날짜·강의명·교수)
  python3 tools/timetable.py subjects             과목별 시작일·종료일·시험일
"""
import argparse, datetime as dt, json, pathlib, re, sys
import openpyxl
from openpyxl.utils import column_index_from_string

R = pathlib.Path(__file__).resolve().parent.parent
OUT = R / 'state/timetable.json'
LOG = R / 'logs/timetable.log'
PERIODS = ['1', '2', '3', '4', '점심', '5', '6', '7', '8', '저녁']
RED = 'FFFF0000'
sys.path.insert(0, str(R / 'tools'))
from common import load_config, today_kst  # noqa: E402


def is_red(cell):
    c = cell.font.color if cell.font else None
    return c is not None and c.type == 'rgb' and str(c.rgb).upper() == RED


class Sheet:
    def __init__(self, ws):
        self.ws = ws
        self.span = {}
        for m in ws.merged_cells.ranges:
            self.span[(m.min_row, m.min_col)] = (m.max_row, m.max_col)

    def date(self, r, c):
        """날짜 셀 값. '=I232+1' 같은 수식은 직접 계산한다."""
        v = self.ws.cell(r, c).value
        if isinstance(v, dt.datetime):
            return v.date()
        if isinstance(v, (int, float)):  # 시트 날짜 serial
            return dt.date(1899, 12, 30) + dt.timedelta(days=int(v))
        if isinstance(v, str) and v.startswith('='):
            m = re.fullmatch(r'=\$?([A-Z]+)\$?(\d+)\s*([+-])\s*(\d+)', v.replace(' ', ''))
            if not m:
                raise ValueError(f'해석할 수 없는 날짜 수식 {v} (R{r}C{c})')
            base = self.date(int(m.group(2)), column_index_from_string(m.group(1)))
            n = int(m.group(4))
            return base + dt.timedelta(days=n if m.group(3) == '+' else -n)
        return None


KEY_RE = re.compile(r'^([가-힣A-Za-z]+?)(\d+)\s*:\s*(.*)$')


def parse_cell(text):
    """셀 텍스트 → {title, prof, dept, prefix, num, assignees, notes}"""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    out = {'title': '', 'prof': None, 'dept': None, 'keys': [], 'notes': []}
    rest = []
    for l in lines:
        k = KEY_RE.match(l)
        if k and not l.startswith('('):
            # "그룹장1: 김미현 / 그룹장5: 성민수" 처럼 한 줄에 여러 개가 있을 수 있다
            for part in re.split(r'\s*/\s*(?=[가-힣A-Za-z]+\d+\s*:)', l):
                kk = KEY_RE.match(part)
                if kk:
                    out['keys'].append({'prefix': kk.group(1), 'num': int(kk.group(2)),
                                        'assignees': [a.strip() for a in kk.group(3).split('/') if a.strip()]})
            continue
        if l.startswith('#'):
            out['notes'].append(l.lstrip('# ').strip())
            continue
        rest.append(l)
    # 교수: ① 한 줄 전체가 "(이름, Dept)"인 줄 ② 줄 끝의 "(이름, Dept)" ③ 닫는 괄호가 빠진 "(이름"
    #       쉼표 뒤가 영문 학과명이 아닌 괄호("외상(두부, 척추)")는 강의명의 일부로 본다.
    for i, l in enumerate(rest):
        m = re.fullmatch(r'\(([가-힣]{2,4}(?:\s*외\s*\d+명)?)(?:\s*,\s*([^)]*))?\)', l)
        if m and '그룹' not in l:
            out['prof'], out['dept'] = m.group(1), (m.group(2) or None)
            rest = rest[:i] + rest[i + 1:]
            break
    else:
        for i, l in enumerate(rest):
            m = (re.search(r'\s*\(([가-힣]{2,4})\s*,\s*([A-Za-z][^)]*)\)\s*$', l)
                 or re.search(r'\s*\(([가-힣]{2,4})\s*$', l))
            if m:
                out['prof'] = m.group(1)
                out['dept'] = m.group(2) if m.lastindex and m.lastindex > 1 else None
                rest[i] = l[:m.start()]
                break
    joined = '\n'.join(rest)
    out['title'] = re.sub(r'\s+', ' ', joined.split('\n')[0] if joined else '').strip()
    if not out['title'] and rest:
        out['title'] = rest[0]
    return out


def parse_workbook(path):
    wb = openpyxl.load_workbook(path)
    ws = wb['시간표']
    sh = Sheet(ws)
    heads = [r for r in range(1, ws.max_row + 1)
             if isinstance(ws.cell(r, 1).value, str) and re.fullmatch(r'\d+주', ws.cell(r, 1).value.strip())]
    term = 0
    lectures, exams, holidays, weeks = [], [], [], []
    for r in heads:
        wk = int(ws.cell(r, 1).value.strip()[:-1])
        if wk == 1:
            term += 1
        monday = sh.date(r, 3)
        weeks.append({'term': term, 'week': wk, 'monday': monday.isoformat(), 'row': r})
        for c in range(3, 10):
            day = sh.date(r, c) or monday + dt.timedelta(days=c - 3)
            if is_red(ws.cell(r, c)):
                holidays.append(day.isoformat())
            for i, per in enumerate(PERIODS):
                rr = r + 1 + i
                cell = ws.cell(rr, c)
                v = cell.value
                if not isinstance(v, str) or not v.strip():
                    continue
                end_r = sh.span.get((rr, c), (rr, c))[0]
                pers = PERIODS[i:i + (end_r - rr) + 1]
                info = parse_cell(v)
                rec = {'term': term, 'week': wk, 'date': day.isoformat(), 'periods': pers,
                       'title': info['title'], 'prof': info['prof'], 'keys': info['keys'],
                       'red': is_red(cell), 'raw': v.strip()}
                if rec['red']:
                    exams.append({'term': term, 'date': day.isoformat(), 'text': re.sub(r'\s+', ' ', v.strip())})
                lectures.append(rec)
    return lectures, exams, sorted(set(holidays)), weeks


def subjects_summary(data, cfg):
    """과목별 시작일(그 과목 강의가 처음 나오는 날) · 마지막 강의일 · 시험일."""
    res = {}
    for s in cfg['subjects']:
        ls = [l for l in data['lectures'] if l['term'] == s['term'] and not l['red']
              and any(k['prefix'] == s['prefix'] for k in l['keys'])]
        ex = [e for e in data['exams'] if e['term'] == s['term']
              and any(n in e['text'] for n in s['exam_names'])]
        res[s['slug']] = {
            'name': s['name'],
            'start': min((l['date'] for l in ls), default=None),
            'last': max((l['date'] for l in ls), default=None),
            'exam': min((e['date'] for e in ex), default=None),
            'lectures': len({k['num'] for l in ls for k in l['keys'] if k['prefix'] == s['prefix']}),
        }
    return res


def lectures_of(data, cfg, slug):
    s = next(x for x in cfg['subjects'] if x['slug'] == slug)
    out = {}
    for l in data['lectures']:
        if l['term'] != s['term'] or l['red']:
            continue
        for k in l['keys']:
            if k['prefix'] == s['prefix']:
                out.setdefault(k['num'], {'num': k['num'], 'date': l['date'], 'title': l['title'], 'prof': l['prof']})
    return [out[k] for k in sorted(out)]


def unknown_prefixes(data, cfg):
    known = {s['prefix'] for s in cfg['subjects']} | set(cfg.get('ignore_prefixes', []))
    cur = max(l['term'] for l in data['lectures'])
    return sorted({k['prefix'] for l in data['lectures'] if l['term'] == cur for k in l['keys']} - known)


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('parse'); p.add_argument('xlsx'); p.add_argument('--title', required=True)
    p.add_argument('--today')
    p = sp.add_parser('lectures'); p.add_argument('slug')
    sp.add_parser('subjects')
    a = ap.parse_args()
    cfg = load_config()
    if a.cmd == 'parse':
        lectures, exams, holidays, weeks = parse_workbook(a.xlsx)
        m = re.match(r'v(\d+)', a.title)
        data = {'title': a.title, 'version': int(m.group(1)) if m else None,
                'fetched': a.today or today_kst().isoformat(),
                'weeks': weeks, 'holidays': holidays, 'exams': exams, 'lectures': lectures}
        data['subjects'] = subjects_summary(data, cfg)
        prev = json.loads(OUT.read_text()) if OUT.exists() else None
        OUT.parent.mkdir(exist_ok=True); LOG.parent.mkdir(exist_ok=True)
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1))
        if not prev or prev.get('title') != data['title']:
            changes = []
            if prev:
                for k, v in data['subjects'].items():
                    o = prev.get('subjects', {}).get(k)
                    if o and (o['start'], o['exam']) != (v['start'], v['exam']):
                        changes.append(f"{v['name']} 시작 {o['start']}→{v['start']} 시험 {o['exam']}→{v['exam']}")
            line = f"{data['fetched']}  {prev['title'] if prev else '(처음)'} → {data['title']}"
            if changes:
                line += '  | ' + '; '.join(changes)
            with LOG.open('a') as f:
                f.write(line + '\n')
            print('버전 변경 기록:', line)
        else:
            print('버전 그대로:', data['title'])
        unk = unknown_prefixes(data, cfg)
        if unk:
            print('⚠ config/subjects.yaml에 없는 접두어:', ', '.join(unk))
        print(f"강의 {len(lectures)}개 · 시험 {len(exams)}개 · 휴일 {len(holidays)}일")
    elif a.cmd == 'subjects':
        data = json.loads(OUT.read_text())
        for k, v in subjects_summary(data, cfg).items():
            print(f"{k:9} {v['name']:12} 시작 {v['start']}  마지막강의 {v['last']}  시험 {v['exam']}  강의 {v['lectures']}개")
    elif a.cmd == 'lectures':
        data = json.loads(OUT.read_text())
        for l in lectures_of(data, cfg, a.slug):
            print(f"{l['num']:02d}  {l['date']}  {l['title']}  ({l['prof']})")


if __name__ == '__main__':
    main()
