# 본과 2학년 기출 퀴즈

과목별 최근 5개년 복원 기출과, 교수님별 출제 경향에 맞춘 예상 변형 문항을 푸는 정적 사이트입니다(GitHub Pages, `main` 브랜치 루트).
새 과목은 시간표상 과목 시작일에 예약 작업이 만들어 Pull Request로 올립니다. 작업 순서는 [AUTOMATION.md](AUTOMATION.md)를 보세요.

- 홈 `index.html`: 과목 선택. 과목 카드는 각 `<slug>/card.json`을 읽어 그립니다.
- 과목 퀴즈 `<slug>/index.html`: 파트(교수님)·출제 연도·기출/변형 필터, 선지 섞기, 오답노트(브라우저 저장)
- 문제집 PDF `<slug>/<과목명>_기출문제집.pdf`

## 명령
```bash
python3 tools/validate.py            # 데이터 검사
python3 tools/build.py               # 모든 과목 페이지 + 홈 다시 만들기
python3 tools/build.py --pdf neuro   # PDF도 다시 만들기 (weasyprint 70, fonts-noto-cjk 필요)
node tools/smoke.js                  # 브라우저로 열어 확인
python3 tools/timetable.py subjects  # 과목별 시작일·시험일
python3 tools/state.py due           # 오늘 처리할 과목
```

## 데이터 형식

`data/<slug>/meta.json`
```json
{"slug":"neuro","name":"신경계학","title":"신경계학 최근 5개년 기출 문제집","years":[2025,2023,2022,2021,2020],
 "missing_years":[2024],"verified":false,"basis":2026,"exam":"2026-11-30","updated":"2026-11-16",
 "ch":[{"id":0,"title":"Ⅰ. …","prof":"안지예","mode":"minor","why":"판단 근거"}],"notes":["PDF 일러두기"]}
```
`mode`: `repeat`(해마다 거의 그대로 → 변형 없음) · `minor`(보기·수치·발문만 바꿈) · `major`(같은 개념을 다른 증례·형식으로)

`data/<slug>/past.json` (기출)
```json
{"id":"25-29","keys":["25-29","21-22"],"y":[2021,2025],"ch":0,"g":"소단원","stem":"<div>…</div>",
 "o":["…"],"a":4,"A":"⑤","ra":"⑤","E":"해설","B":"관련 강의: 강의 17 소아 말초신경, 근육질환",
 "N":"비고(복원 답과 다름 등)","img":["figs/25-29.png"],"v":false,"ok":true,"vb":"검안"}
```
- `a`: 0부터 세는 정답 인덱스, `A`: 표시용 정답, `ra`: 복원 해설의 답
- `ok`: 2026년 강의 자료로 정답을 확인했으면 true (false면 사이트·PDF에 '미검증' 표시)
- `vb`: 검증에 쓴 자료 판 — `"초안"` 또는 `"검안"` (사이트·PDF에 '초안 검증'/'검안 검증' 표시). 과목 표시는 가장 약한 쪽을 따른다: 전부 검안 → 검안 검증, 초안이 섞이면 초안 검증, 미검증이 섞이면 일부 검증

`data/<slug>/variants.json` (변형): [docs/variation-rules.md](docs/variation-rules.md) §4

`data/<slug>/summary.json` (선택, 요약자료): 있으면 과목 페이지 맨 위 「문제집 PDF」 옆에 「요약자료」 버튼이 생기고, `<slug>/summary.html`에 교수님별로 접었다 펴는 정리표 사진을 보여 줍니다(교수님 순서는 파트 순서).
```json
{"updated":"2026-11-23","note":"페이지 상단 안내문",
 "profs":[{"prof":"안지예","items":[{"title":"소아 경련성 질환 — 발생시기·임상양상·EEG·치료",
   "img":"summary/ahn-peds-seizure.jpg","src":"26 학습부 08번 · 소아 경련성 질환"}]}]}
```
- 그림은 `<slug>/summary/`에 영문·하이픈 파일명으로 둡니다(예: `ahn-primitive-reflex.jpg`). `prof`는 `meta.ch`의 교수 이름과 같아야 합니다(validate가 검사).

`data/<slug>/gen.js` (선택): 시작할 때마다 수치·선지를 새로 만드는 문항 생성기 (현재 내분비학만)

## 저장소 이름
옛 `endo-quiz`(내분비학 한 과목)를 여러 과목용으로 옮긴 저장소입니다. 내분비학은 `/endo/`에 있습니다.
