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
bash tools/setup_env.sh              # 처음 한 번: 패키지·한글 글꼴 준비와 검사("환경 OK")
python3 tools/build.py --pdf neuro   # PDF도 다시 만들기 (한글 글꼴이 안 들어가면 중단)
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

주관식 기출은 같은 파일에 `t:"s"`로 들어갑니다.
```json
{"id":"23-2Q-34","keys":["23-2Q-34"],"y":[2023],"ch":0,"g":"소단원","t":"s","stem":"<div>…</div>","o":[],"a":-1,
 "A":"SMN1","acc":["SMN1"],"E":"해설","B":"26 학습부 17번(검안) · …","N":"","img":[],"v":false,"ok":true,"vb":"검안","ra":"SMN1"}
```
- `A`: 모범 답, `acc`: 자동 채점 인정 답(입력에 하나라도 들어 있으면 맞음, 빈 목록이면 스스로 채점). 퀴즈에서는 답을 써서 확인한 뒤 맞음/틀림을 바꿀 수 있고, '문제 형식'에서 객관식만/주관식만 고를 수 있습니다. 문제집 PDF에는 답 칸과 모범 답이 들어갑니다.
- key의 `2Q-`는 2큐(2Q) 시험 번호입니다. 넣는 방법은 `tools/short.py`(AUTOMATION.md 3-3b).
- 지문에 "그림 누락" 표시가 있는 문항은 빌드 때 모아 퀴즈 페이지 맨 아래에 "학습부 NN번 사진 누락 — n문항"으로 안내합니다(번호는 `B`의 학습부/강의 번호).

`data/<slug>/variants.json` (변형): [docs/variation-rules.md](docs/variation-rules.md) §4

`data/<slug>/summary.json` (선택, 요약자료): 있으면 과목 페이지 맨 위 「문제집 PDF」 옆에 「요약자료」 버튼이 생기고, `<slug>/summary.html`에 교수님별로 접었다 펴는 정리표를 보여 줍니다(교수님 순서는 파트 순서).
```json
{"updated":"2026-11-23","note":"페이지 상단 안내문",
 "profs":[{"prof":"안지예","items":[{"title":"소아 경련성 질환 — 발생시기·임상양상·EEG·치료",
   "html":"summary/ahn-peds-seizure.html","img":"summary/ahn-peds-seizure.jpg","pdf":"summary/ahn-peds-seizure.pdf",
   "src":"26 학습부 08번 · 소아 경련성 질환"}]}]}
```
- `html`: 표 조각(`<table>…</table>`, 스크립트·`data:` 그림 없이). 파일은 `data/<slug>/summary/`에 두고 빌드 때 페이지에 그대로 들어갑니다 → 글자라서 확대해도 선명하고 가볍습니다. 표 안 그림은 `<img src="summary/….jpg" loading="lazy">`로 `<slug>/summary/`의 파일을 참조합니다. 표 서식은 `src/summary.html`의 `.sheet` CSS(열 5개 표는 `class="w5"`, 4개는 `w4` → 좁은 화면에서 좌우 스크롤).
- `img`·`pdf`: 받기 링크로 붙습니다(`html`이 없으면 `img`를 사진으로 보여 줌). 파일은 `<slug>/summary/`에 영문·하이픈 이름으로.
- `prof`는 `meta.ch`의 교수 이름과 같아야 합니다(validate가 교수·파일·표 안 그림·금지어를 검사).

`data/<slug>/gen.js` (선택): 시작할 때마다 수치·선지를 새로 만드는 문항 생성기 (현재 내분비학만)

## 저장소 이름
옛 `endo-quiz`(내분비학 한 과목)를 여러 과목용으로 옮긴 저장소입니다. 내분비학은 `/endo/`에 있습니다.
