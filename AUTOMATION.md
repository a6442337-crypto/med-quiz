# AUTOMATION.md — 예약 작업 지침

이 문서만 읽고 처음부터 끝까지 수행할 수 있게 쓴 작업 지침이다. 예약 작업은 매일 한 번(한국 시간 새벽) 새 세션으로 시작한다.
할 일은 시간표상 **시작일이 된 과목 하나**에 대해 다음을 만들어 **Pull Request로 올리는 것**이다.

> 기출 수집 → 문항 데이터 → 문제집 PDF → 퀴즈 페이지 → (변형 출제 교수님 문항은) 변형문제

**절대 규칙**
1. `main`에 직접 커밋·푸시하지 않는다. 결과는 항상 `auto/…` 브랜치 + PR로 올리고, **검사를 통과하면 스스로 머지한다**(3-12). 머지되면 GitHub Pages에 배포된다. 사용자가 매일 사이트를 보다가 오류를 알려 주면 그때 고친다(2026-11-17 사용자 결정).
   - 이 환경에서는 원격 브랜치를 **지울 수 없다**(403). 그래서 브랜치 이름에 날짜·버전을 붙여 매번 새 이름을 쓰고, 이미 있는 브랜치를 다시 쓰지 않는다. 진행 중인지 여부는 브랜치가 아니라 **열린 PR**로 판단한다.
   - 오늘 날짜는 `D=$(TZ=Asia/Seoul date +%Y%m%d)`로 만든다.
2. 근거에 **학습부 출처 표기는 해도 된다**(예: `26 학습부 03번 · 갑상선기능검사`). 단 사이트·PDF·데이터·커밋 메시지·PR 본문 어디에도 **학습부 담당 학생 이름, 전화번호, 학습부 사진**은 넣지 않는다. 해설에는 근거 *내용*을 정리해 쓴다.
3. 정답은 복원 해설이 아니라 **2026년(올해) 강의 자료(26 학습부)** 기준으로 판단한다. 강의 자료가 없으면 복원 답을 싣고 `미검증`으로 표시한다.
4. 하루에 한 과목만 처리한다. 처리할 것이 없으면 바로 끝낸다.
5. 키·토큰 등 비밀값을 커밋하지 않는다.

---

## 0. 준비 (매번)

```bash
# 저장소: add_repo 도구가 있으면 a6442337-crypto/med-quiz 를 붙이고(access: push) 안내대로 클론한다.
# add_repo 도구가 없으면: cd /home/user && git clone https://github.com/a6442337-crypto/med-quiz.git
cd /home/user/med-quiz            # 클론한 위치
git config user.name  "Claude (auto)"; git config user.email "noreply@anthropic.com"
python3 -m pip install -q weasyprint==70.0 pyyaml openpyxl pillow   # 'pip'만 쓰면 다른 파이썬에 설치될 수 있다
apt-get install -y -q fonts-noto-cjk >/dev/null 2>&1 || (apt-get update -q && apt-get install -y -q fonts-noto-cjk)
fc-list | grep -q "Noto Sans CJK KR" && echo 글꼴OK
mkdir -p /tmp/work
```
- 커넥터 두 개가 필요하다.
  - **Google Drive** (`mcp__Google-Drive__*`, 환경에 따라 `mcp__Google_Drive__*`): 시간표 시트를 xlsx로 받을 때만 쓴다. 학과 드라이브 파일은 이 커넥터로 열 수 없다.
  - **drive-mcp** (`mcp__drive-mcp__search_drive`, `read_drive_file`, `get_hwp_image`): 학과 공유 드라이브(account `dept`)의 기출·학습부를 읽는다.
  - 둘 중 하나라도 없으면 아무것도 바꾸지 말고, 어느 커넥터가 없는지만 보고하고 끝낸다.
- - `git push`가 권한 오류로 실패하면 커밋을 남긴 채 멈추고, 실패 메시지를 6단계 보고에 그대로 적는다.
- Playwright·Chromium은 환경에 이미 있다(`node tools/smoke.js`에서 사용). 다시 설치하지 않는다.

## 1. 시간표 받기 · 버전 기록

1. `mcp__Google-Drive__get_file_metadata(fileId="1xcH1X2AOqbEghejABgNL55EfL8zjOXB7AYVYJZ0IaB4", excludeContentSnippets=true)` → `title` (예: `v262_시간표_GY`).
2. `mcp__Google-Drive__download_file_content(fileId=같은 ID, exportMimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")`
   → 결과에 나온 저장 경로의 xlsx를 `/tmp/work/timetable.xlsx`로 복사한다. (CSV는 글자색이 없어 시험·휴일을 알 수 없으므로 반드시 xlsx로 받는다.)
3. 버전 기록은 `auto/timetable-<버전>` 브랜치 PR로 한다(과목 PR과 충돌하지 않게 시간표 파일은 이 PR에서만 바꾼다).
   ```bash
   git fetch origin
   # 시간표 PR도 만든 뒤 3-12대로 바로 머지한다. 머지 못 한 옛 시간표 PR이 열려 있으면 그것부터 머지하거나 닫는다
   gh api "repos/a6442337-crypto/med-quiz/pulls?state=open&per_page=100" --jq '.[] | select(.head.ref|startswith("auto/timetable-")) | .head.ref'
   git checkout -B auto/timetable-<vNNN> origin/main     # <vNNN>: title 앞의 버전 (예: v263). 위 목록에 같은 이름이 있으면 이 단계 전체를 건너뛴다
   python3 tools/timetable.py parse /tmp/work/timetable.xlsx --title "<1에서 받은 title>"
   ```
   - 출력이 `버전 변경 기록:`이면 `python3 tools/build.py`로 홈을 다시 만든 뒤 `state/timetable.json logs/timetable.log index.html`만 커밋·푸시한다. 3-11과 같은 REST 방식으로 PR을 만든다(제목 `시간표 버전 기록 (vNNN)`, 본문에 logs 마지막 줄).
   - `버전 그대로:`이면 커밋하지 않는다.
   - `⚠ config/subjects.yaml에 없는 접두어`가 나오면, 그 접두어가 새 과목이면 6단계 보고에 적는다(설정을 마음대로 추가하지 않는다).
4. `git checkout main && git pull` 후 같은 parse 명령을 한 번 더 실행해 작업 트리에 최신 `state/timetable.json`을 둔다. 이 파일과 `logs/timetable.log`, `index.html`은 과목 PR에 넣지 않는다(커밋 전에 `git checkout -- state/timetable.json logs/timetable.log index.html`).

## 2. 오늘 할 일 정하기

```bash
python3 tools/state.py due                       # 예약 실행
python3 tools/state.py due --subject 신경계학     # 수동 실행 (프롬프트에 "과목: OOO"가 있을 때)
```
결과 `action`에 따라 다음 단계로 간다.
- `none`: 할 일이 없다. 1단계 결과만 짧게 보고하고 **끝낸다**.
- `new`: 새 과목 처리 → 3단계. `waiting`에 다른 과목이 있으면 내일로 넘어간다는 사실만 보고한다.
- `reverify-check`: 새 과목이 없을 때, 미검증 문항이 있거나 초안으로 검증한 문항이 있는 과목(시험 전) 확인 → 5단계.

`due`는 다음을 알아서 판단한다.
- 시작일 ≤ 오늘 ≤ 시험일인 과목 가운데 `config/subjects.yaml`에서 `auto: true`인 것
- `state/subjects/<slug>.json`이 done/skipped인 과목은 건너뜀
- 그 과목의 열린 PR(`auto/<slug>-…`)이 있으면 머지되지 못한 작업으로 보고 건너뜀(그 PR을 확인해 3-12로 머지하거나 보고). 머지된 옛 브랜치가 남아 있는 것은 상관없음
- 시작일이 빠른 과목 하나만 고름

## 3. 새 과목 처리 (`action: new`)

작업 폴더는 `W=/tmp/work/<slug>`로 둔다. 브랜치를 만든다: `git checkout -B auto/<slug>-$D origin/main` (원격에 같은 이름이 이미 있으면 `-$D-2`처럼 뒤에 번호를 붙인다)

### 3-1. 올해 강의 목록
```bash
python3 tools/timetable.py lectures <slug>
```
강의 번호, 날짜, 강의명, 교수가 나온다. 강의 번호는 학습부 파일 번호와 같다(`신경18: 초안/검안` = 18번 강의). 이 목록에 있는 교수님이 **2026년 담당 교수**다.

### 3-2. 기출 파일 찾기 (2025 → 2020)
`config/subjects.yaml`의 `drive_names`(예: 신경계학, 신경계)로 **연도마다 따로** 검색한다. 검색 결과는 20개에서 잘리므로 한 번에 몰아서 찾지 않는다.
- `search_drive(query="<연도> <과목명> 복원", account="dept")`, `"<연도> <과목명>"`, `"<두자리연도> <과목명> 복원"`도 시도한다.
- 연도마다 고르는 순서: **복원 해설(hwp) > 복원 해설(pdf) > 복원 수합/문제수합(hwp) > pdf**. 1Q/2Q(1큐/2큐)로 나뉘면 둘 다 고른다. `ver`가 여러 개면 가장 높은 버전을 고른다.
- 파일명에 "학습부·초안·검안"이 붙은 강의별 파일은 기출 원본이 아니다(관련 기출이 섞여 있음). 쓰지 않는다.
- 찾지 못한 연도는 건너뛰고 리포트의 "수집한 기출" 표에 "드라이브에 없음"으로 적는다.
- 이미 읽은 파일인지 확인: `python3 tools/state.py seen <slug> <file_id>` (exit 0이면 이미 읽음 → 같은 내용을 다시 처리하지 않는다).
- 고른 파일은 바로 기록한다: `python3 tools/state.py source <slug> <file_id> --name "<파일명>" --account dept --kind past --year <연도>`

### 3-3. 읽기와 추출
- `read_drive_file(file_id, account="dept", part=N)`로 **마지막 부까지** 모두 읽는다. 결과가 크면 "Output has been saved to <경로>"로 파일에 저장된다. 그 파일을 `$W/<연도><a|b>_<N>.txt`로 복사하고, 부를 순서대로 이어 붙여 `$W/<연도><a|b>.txt`를 만든다.
- 작은 부는 결과가 대화에 그대로 들어온다. 이때는 필요한 문항만 `$W/extra.json`에 손으로 옮긴다(형식은 아래). 마지막 부에 2026년 담당이 아닌 교수 문항이나 주관식만 남았다면 읽지 않아도 된다(첫 부의 "복원순서/출제교수님" 표로 판단).
- "Too many subrequests" 오류가 나면 1분 뒤 한 번만 다시 시도한다. 그래도 안 되면 그 파일을 건너뛰고 리포트에 적는다.
- 복원 해설(문항마다 `답:` 바로 뒤에 `# 홍길동 교수님`/`# 홍길동p`가 있는 형식)은 도구로 추출한다.
  ```bash
  python3 tools/extract_haeseol.py $W/all.json $W/2025a.txt 2025 $W/2023a.txt 2023 $W/2023b.txt 2023 …
  ```
  - 출력 문항 수를 첫 부의 "복원순서" 표(교수님별 객관식 번호 범위)와 맞춰 본다. 빠진 번호가 객관식이면 원문을 grep으로 찾아 `extra.json`에 보충한다.
  - 각 본 문항의 `rel`에는 그 해설에 실린 "관련 기출"(예: `<2021 기출>` 아래 문항)이 연도와 함께 들어간다. 교수 표기가 없는 옛 연도(문제수합)는 이 `rel`을 통해 그 교수님 문항으로 수록한다(3-5의 `--rel-years`).
- 교수 표기가 없는 형식(문제수합·옛 복원)만 있는 연도는 다음 순서로 처리한다.
  ① 그 연도 문항이 최근 해설의 `rel`에 들어 있으면 그것을 쓴다.
  ② 아니면 첫 부의 "복원순서" 표나 총평으로 번호 범위별 교수를 정하고, 같은 형식으로 `extra.json`에 넣는다.
  ③ 둘 다 안 되면 그 연도는 "교수 표기 없음 → 미수록"으로 리포트에 남긴다.
- `extra.json` 형식 (all.json과 같음):
  ```json
  [{"year":2023,"num":62,"prof":"안성환","stem":["지문 줄"],"opts":["①…","②…","③…","④…","⑤…"],
    "imgs":[],"ans":"4","a":3,"ex":["해설 문장"],"rel":[],"note":"비고(선택)"}]
  ```
- **그림**: `get_hwp_image`는 큰 그림을 파일로 저장하지만 작은 그림은 base64가 대화에 그대로 들어와 맥락을 크게 차지한다. 일부 파일에서는 "BMP 형식이 아닙니다" 오류가 난다. 그래서 그림은 **판독이 정답에 꼭 필요한 문항에만**, 과목당 최대 30개까지 받는다.
  - 결과가 파일로 저장되면 `data:image/png;base64,` 뒤를 디코드해 `<slug>/figs/<yy>-<nn>.png`로 저장하고, extra/all의 그 문항에 `"img_files":["figs/25-01.png"]`를 넣는다.
  - 오류가 나거나 결과가 대화에 들어오는 그림은 받지 않는다. 그 문항은 assemble이 지문에 "그림 누락"을 자동으로 표시한다.
  - **학습부 사진은 절대 받지 않는다.** 시험 문항 그림만 받는다.
  - **그림 누락 안내**: 읽어오지 못한 그림은 지문의 "그림 누락" 표시로 남긴다(지우지 않는다). 빌드가 이 표시가 있는 문항을 모아 퀴즈 페이지 **맨 아래**에 "학습부 NN번 사진 누락 — n문항 (2025 #12, …)"으로 적는다. 학습부 번호는 문항의 근거(B)의 `학습부 NN번` 또는 `관련 강의: 강의 NN`에서 읽으므로, 그림 누락 문항에도 B를 꼭 채운다. 6단계 보고에도 누락된 학습부 번호를 적는다(`card.json`의 `missing_figs`).
  - 사용자가 학습부(검안본) PDF를 첨부하면 그 안의 **기출 문항 그림**만 `pdfimages -png -f P -l P`로 꺼내 `<slug>/figs/<key>.jpg`로 넣고, 그 문항의 `img`를 채우고 "그림 누락" 표시를 지운다(이론 그림은 쓰지 않는다).

### 3-3b. 주관식
- 복원 해설의 주관식(선지 없이 `답:`만 있는 본 문항)도 싣는다. 3-5 조립(assemble.py)은 객관식만 만들고 기존 주관식은 건드리지 않는다. 조립 **뒤에** 실행한다.
  ```bash
  python3 tools/short.py <slug> $W $W/x2025.json 2025 1 $W/x2023a.json 2023 1 $W/x2023b.json 2023 2 …   # 마지막 숫자 = 1큐/2큐
  ```
  - 2큐(2Q) 문항의 key는 `YY-2Q-NN`이다(1큐와 번호가 겹침). 화면에는 `2023 #2Q-07`로 보인다.
  - 작은 부로 대화에 들어온 주관식은 `$W/short_extra.json`(x.json 문항 형식 + `"q":1|2`, `"opts":[]`)에 손으로 옮긴다.
  - 손볼 것은 `$W/short_fix.json`에 적는다(형식은 tools/short.py 머리말): 자동 채점 인정 답(`acc`: 영어·한글·약어·흔한 철자), 여러 항목을 써야 하는 문항(`self` → 스스로 채점), 소단원(`g`), 같은 문항 묶기(`merge`), 검안본으로 확인한 문항(`verify`), 그림(`img`). 예시: `data/neuro/work/`.
  - 2026 학습부(검안본)에 같은 기출과 답이 있으면 `verify`로 검증 표시한다. 없으면 미검증(ok:false)으로 둔다.
- 주관식 문항 형식: `t:"s"`, `o:[]`, `a:-1`, `A`=모범 답, `acc`=자동 채점 인정 답 목록(빈 목록이면 스스로 채점). 퀴즈에서는 답을 써서 확인하고, 문제집 PDF에는 답 칸과 모범 답이 들어간다. 변형 문항은 주관식으로 만들지 않는다.

### 3-4. 파트 구성 `data/<slug>/chapters.json`
2026년 담당 교수님마다 파트 하나를 만든다. 순서는 3-1 강의 순서를 따른다.
```json
[{"prof":"안지예","title":"Ⅰ. 소아신경 (발달·중추신경계질환·경련·말초신경·근육)",
  "groups":[["소아 경련성 질환",["경련","발작","뇌전증"],[8]],
            ["신경계 발달·소아신경 진단",[],[1]]]}]
```
- `title`은 그 교수님 강의명을 묶은 이름이고, 앞에 로마숫자를 붙인다.
- `groups`는 [소단원, 키워드, 관련 강의 번호]다. 마지막 소단원이 기본값이다. 키워드는 그 강의에서만 나오는 용어로 고른다.
- 2026년에 강의하지 않는 교수님 문항은 넣지 않는다(파트를 만들지 않으면 자동으로 빠진다). 빠진 교수님 이름은 리포트와 `meta.notes`에 적는다.
- 예시: `data/neuro/chapters.json`.

### 3-5. 변형 수준 판단과 조립
```bash
python3 tools/compare_years.py $W --profs "$(python3 -c "import json;print(','.join(c['prof'] for c in json.load(open('data/<slug>/chapters.json'))))")"
python3 tools/assemble.py <slug> $W            # → data/<slug>/past.json, meta.json(ch·years)
```
- `docs/variation-rules.md` §2에 따라 compare_years의 1차 판정을 확인한다. 교수님마다 `modes.json`의 pairs 중 3쌍 이상을 원문(all.json)에서 직접 비교한다. 판정을 바꾸면 chapters.json에 `"mode"`, `"why"`를 넣고 assemble을 다시 돌린다.
- assemble 출력의 교수님별 문항 수가 3-3에서 센 수와 크게 다르면 원인(합치기·제외)을 확인한다. `$W/dropped.json`에 빠진 문항(그림 선지 등)이 남는다.

### 3-6. 2026년 강의 자료로 정답 검증
1. 강의 자료를 찾는다: `search_drive("<과목명> 26", dept)`, `search_drive("번 <과목명> 26", dept)`. 파일명 형식은 `NN번 <과목명> 26MMDD <교수>P <담당> (주제) - 초안|검안`이다(26으로 시작하는 6자리 날짜가 올해 자료). 강의 번호마다 **검안 > 초안**, hwp > pdf 순으로 고른다(`.hwpx`는 읽을 수 없으니 pdf를 쓴다). `state.py source <slug> <file_id> --kind guide --name "강의 NN 검안"`으로 기록한다(파일명에 학생 이름이 있으므로 **파일명은 기록하지 않는다**).
2. 하나도 없으면 검증 없이 진행한다. 모든 문항은 `ok:false`, `meta.verified:false`로 두고, notes에 "미검증판" 문구를 넣는다(neuro 참고).
3. 있으면 강의 번호별로 그 강의의 소단원(chapters.json의 강의 번호) 문항을 검증한다.
   - 강의 자료 기준으로 정답을 다시 판단한다. 복원 답과 다르면 `a`, `A`를 고치고 `N`에 "복원 답 ③과 다름 — 2026년 강의 기준 ⑤"처럼 적는다(`ra`는 복원 답 그대로 둔다).
   - `E`는 강의 내용을 근거로 다시 쓴다. 정답 이유와 주요 오답 이유를 쓰되, 학습부 문장을 그대로 옮기지 말고 요약한다. 학생 이름, "OO 학우" 같은 표현은 넣지 않는다.
   - `B`는 검증에 쓴 자료로 `26 학습부 NN번(검안) · 강의명`처럼 쓴다(미검증 문항은 assemble이 넣는 `관련 강의: 강의 NN 강의명` 그대로). 강의 자료에 근거가 없으면 `B`에 "웹 자료(출처명)"를 덧붙이고 일반 의학 지식으로 판단한다.
   - 검증한 문항은 `ok:true`와 함께 **`vb`에 검증에 쓴 자료 판을 적는다**: 검안으로 검증했으면 `"vb":"검안"`, 초안으로 검증했으면 `"vb":"초안"`. 미검증 문항(`ok:false`)에는 `vb`를 넣지 않는다. 사이트·PDF에 문항마다 '초안 검증'/'검안 검증'/'미검증'이 표시되고, 과목 표시는 가장 약한 쪽을 따른다(하나라도 초안이면 '초안 검증', 미검증이 섞이면 '일부 검증').
   - 같은 강의에 초안과 검안이 둘 다 있으면 반드시 검안으로 검증한다. 초안만 있으면 초안으로 검증하고 `vb:"초안"`으로 둔다.
   - 모든 문항이 `ok:true`가 되면 `meta.verified:true`로 한다. 강의 자료가 일부만 올라왔으면 나머지는 `ok:false`로 둔다.
   - 강의 자료를 기록할 때 판을 이름에 넣는다: `state.py source <slug> <file_id> --kind guide --name "강의 NN 검안"` (또는 `"강의 NN 초안"`).

### 3-7. 변형문제
`docs/variation-rules.md` §3을 그대로 따른다.
- `data/<slug>/variants.json`에 쓴다. repeat 파트는 만들지 않는다. 정답 위치를 고르게 하고, `vn`에 바꾼 내용을 적는다.
- 강의 자료로 확인했으면 `ok:true`와 `vb`(초안|검안), 아니면 `ok:false`로 둔다.

### 3-8. meta.json
assemble이 `ch`와 `years`를 채운다. 나머지는 직접 채운다(neuro 참고).
```json
{"slug":"neuro","name":"신경계학","title":"신경계학 최근 5개년 기출 문제집","years":[…],"missing_years":[2024],
 "verified":false,"basis":2026,"exam":"2026-11-30","updated":"2026-11-16","ch":[…],
 "notes":["<b>…</b>: 일러두기 문장", "…"]}
```
- `exam`은 `state/timetable.json`의 `subjects.<slug>.exam`에서 가져온다.
- `notes`는 PDF 첫 장의 "일러두기"에 들어간다. 다음 내용을 쓴다: 미검증 여부, 수록 범위(제외한 교수님, 객관식·주관식 수), 연도별 출처와 빠진 연도, 묶는 기준, 그림 상태, 해설 근거.

### 3-9. 빌드와 확인
```bash
python3 tools/validate.py <slug>          # 오류 0개여야 함 (금지어·정답 인덱스·선지 중복·원본 id 확인)
python3 tools/build.py --pdf <slug>       # PDF + 모든 과목 페이지 + card.json
node tools/smoke.js                       # 홈 → 과목마다 첫 문항 풀기, 콘솔 오류 없음
pdftoppm -r 50 -png -f 1 -l 3 "<slug>/<과목명>_기출문제집.pdf" /tmp/work/p   # 표지·첫 파트를 이미지로 열어 눈으로 확인
grep -rlE "01[0-9]-?[0-9]{3,4}-?[0-9]{4}|[가-힣]{2,4} *학우" data/<slug> <slug> reports/<slug>.md && echo "개인정보 있음 → 고칠 것"
```

### 3-10. 리포트 `reports/<slug>.md`
`reports/neuro.md`와 같은 구성으로 쓴다.
1. 처리일, 시간표 버전, 검증 상태
2. **수집한 기출** 표: 연도 | 파일 | 수록 방식 | 문항 수. 빠진 연도는 "드라이브에 없음"으로 적는다.
3. 제외한 문항(교수님·그림 선지), 주관식 수, 그림 상태(누락된 학습부 번호)
4. **교수님별 변형 판단** 표: 교수님 | 판단 | 비교 쌍 수(그대로/소폭/대폭) | 비교한 문항(`2025 #12 ← 2023 #10 (소)` 형식). 판정 방법 한 줄과 직접 확인하고 고친 내용도 적는다.
5. **만든 변형 문항** 표: 번호 | 파트 | 원본 | 수준 | 바꾼 내용, 그리고 정답 위치 분포
6. 다음에 할 일 (예: 강의 자료가 올라오면 재검증, 그림 보충)

### 3-10b. 과목·교수님별 경향 분석 `data/<slug>/trends.json`
퀴즈 페이지 맨 아래 "과목·교수님별 경향 분석"에 보이는 내용이다. 예시는 `data/neuro/trends.json`.
1. 자료 모으기
   - **과목설명회**: `search_drive("과목설명회 <과목명>", dept)` → 가장 최근 것(수정일 기준) 1~2개를 읽는다. 교수님별 "강의 / 시험 / 공부 방향" 표가 있다.
   - **작년(2025) 강의 자료 첫 장**: 강의 번호마다 `NN번 <과목명> 25MMDD …` 파일 중 가장 마지막 검안본(검안2 > 검안 > 초안)을 골라 첫 부만 읽고, 첫 장의 인사말 문단(수업 분위기, "시험에 낸다/몇 문제" 언급, 기출 경향)만 쓴다. 날짜별로 검색하면 빠짐없이 찾을 수 있다(`"<과목명> 2510"` 등). 한 번에 3개 넘게 동시에 읽으면 드라이브가 "Too many subrequests" 오류를 내니 2~3개씩 읽는다.
   - **이 사이트의 연도 비교**: `meta.ch[].mode·why`(3-5 결과)와 복원 해설 총평.
2. 작성 규칙
   - `summary`: 과목 전체 경향 3~4줄(시험 형식, 반복/새 문제 경향, 올해 바뀐 교수님, 공부 순서).
   - `profs[]`: 2026년 담당 교수님마다 `{"prof","lectures":"강의 NN·NN","points":[2~3줄]}`. 강의 성향, 출제 성향(기출 반복·변형 방식·새 문제가 나오는 곳), 공부 팁. 2025년에 다른 교수님이 대신 강의했으면 그 사실과 이전 기출을 우선하라는 말을 적는다.
   - 사실만 쓰고 추측은 "~할 가능성이 높습니다"처럼 구분한다. 교수님에 대한 인상 평가(성격·감정 등)는 쓰지 않는다.
   - 출처는 `sources`에 "과목설명회(2025년 수강 기준), 2025 학습부 첫 장 코멘트, 연도별 기출 비교"처럼 적어도 된다. **학생 이름, 전화번호, 파일명은 쓰지 않는다.** validate.py가 전화번호·'○○ 학우' 표기를 검사한다.
   - 은어(야마·피마·탈마)는 쓰지 않고 "기출 반복 / 수업 중 강조 부분 / 새 문제"로 쓴다.
3. 재검증(5단계) 때 올해 강의 자료 첫 장에 새 정보(시험 범위·문항 수 언급 등)가 있으면 `trends.json`도 고치고 `updated`를 바꾼다.

### 3-11. 상태 기록 · 커밋 · PR
```bash
python3 tools/state.py set <slug> --status done --verified <true|false> --level <검안|초안|none> --years 2025,2023,… --missing 2024
# --level: 모든 문항이 검안 검증이면 검안, 초안 검증 문항이 하나라도 있으면 초안, 검증된 문항이 없으면 none
git checkout -- state/timetable.json logs/timetable.log index.html 2>/dev/null
git add data/<slug> <slug> reports/<slug>.md state/subjects/<slug>.json state/sources/<slug>.json
git status --short          # 위 경로 말고 다른 파일이 들어가지 않았는지 확인
git commit -m "<과목명> 기출 퀴즈 추가 (기출 N·변형 M, 검증|미검증)"
git -c push.negotiate=true push -u origin auto/<slug>-$D
python3 -c "import json;print(json.dumps({'title':'<과목명> 기출 퀴즈 추가','head':'auto/<slug>-$D','base':'main','body':open('/tmp/work/pr.md').read()}))" > /tmp/work/pr.json
gh api repos/a6442337-crypto/med-quiz/pulls --input /tmp/work/pr.json --jq '.html_url,.number'
```
- `gh pr create`는 이 환경에서 GraphQL이 막혀 실패한다. PR은 항상 위처럼 REST(`gh api …/pulls`)로 만든다.
- 같은 브랜치의 열린 PR이 있는지: `gh api "repos/a6442337-crypto/med-quiz/pulls?state=open&head=a6442337-crypto:auto/<slug>-$D" --jq '.[].html_url'`
PR 본문(`/tmp/work/pr.md`):
- 요약 3줄: 문항 수, 연도, 검증 여부
- 교수님별 변형 판단 요약(반복/소폭/대폭 교수님 이름)
- 빠진 연도와 미수록 사항
- 리뷰할 곳: 리포트 링크, PDF 경로, 그리고 정답을 바꾼 문항 목록(`N`에 기록한 것)
- 마지막 줄: `🤖 Generated with [Claude Code](https://claude.com/claude-code)`

### 3-12. 머지
PR을 만든 뒤 바로 머지한다. 시간표 버전 PR(1단계), 새 과목 PR(3단계), 재검증 PR(5단계) 모두 같다.
1. 머지 직전에 PR 브랜치에서 `python3 tools/validate.py`(오류 0개)와 `node tools/smoke.js`(smoke OK)를 다시 확인한다. 하나라도 실패하면 **머지하지 않고** PR 본문 맨 위에 실패 내용을 적은 뒤 6단계 보고에 남긴다.
2. 머지: `gh api -X PUT repos/a6442337-crypto/med-quiz/pulls/<번호>/merge -f merge_method=merge --jq .merged` → `true`여야 한다.
3. 머지가 충돌 등으로 실패하면(`405`/`409`) `git fetch origin main && git merge origin/main`으로 충돌을 풀고 다시 빌드·검사한 뒤 푸시하고 한 번 더 머지한다. 그래도 안 되면 PR을 열어 둔 채 보고한다.
4. 머지 후 `git checkout main && git pull`을 해서 다음 작업이 최신 main에서 시작되게 한다.

## 4. 수동 실행

예약 작업 프롬프트나 사용자가 다음처럼 지시할 수 있다.
- `과목: 감각계학` → `due --subject 감각계학` 결과에 따라 3단계 또는 5단계를 수행한다. 이미 done인 과목이면 "다시 만들기"로 보고 3단계를 처음부터 한다(브랜치는 새 날짜 이름).
- `재검증: 신경계학` → 5단계.
- `재판단: 내분비학` → 3-3~3-5를 다시 해 교수님별 판단만 3단계로 갱신하고 리포트와 PR을 만든다.

## 5. 재검증 (`action: reverify-check` 또는 `재검증: …`)

대상: 미검증 문항이 있거나(`verified:false`) 초안으로 검증한 문항이 있는(`level:초안`) 과목. 시험일이 지나면 하지 않는다.

1. `search_drive`로 그 과목의 2026년 강의 자료(3-6의 1)를 찾는다. 할 일이 생기는 경우는 둘이다(이미 읽은 파일은 `state.py seen`/`sources`로 확인).
   - **새 강의 자료**: 미검증 문항(`ok:false`)이 있는 강의의 초안 또는 검안이 새로 올라옴
   - **검안본 도착**: 초안으로 검증한(`vb:"초안"`) 문항이 있는 강의의 검안이 새로 올라옴
   둘 다 없으면 "아직 없음"이라고 보고하고 **끝낸다**.
2. 있으면 `git checkout -B auto/<slug>-verify-$D origin/main`을 하고, 3-6의 3을 **그 강의에 해당하는 문항과 변형문항에만** 수행한다. 변형문항 정답도 확인한다.
   - 검안본 도착이면 그 강의의 `vb:"초안"` 문항을 검안으로 다시 풀어 보고, 바뀐 정답·해설을 고친 뒤 `vb:"검안"`으로 바꾼다. 정답이 그대로여도 `vb`는 검안으로 바꾼다. 초안과 정답이 달라진 문항은 `N`에 "초안 기준 ③ → 검안 기준 ⑤"처럼 적는다.
3. `meta.updated`를 오늘로 바꾸고, 모두 검증되면 `meta.verified:true`로 한다. notes의 "미검증판" 문구는 상태에 맞게 고친다.
4. 3-9 빌드·확인을 하고, 리포트에 "재검증 (날짜)" 절을 추가한다(바뀐 정답 목록 포함). `state.py set <slug> --verified true|false --level 검안|초안|none` (3-11 기준).
5. 커밋하고 PR을 만든 뒤 3-12대로 머지한다(제목 `<과목명> 정답 재검증 (강의 자료 반영)`, 검안본만 반영했으면 `<과목명> 검안본 반영`). PR 본문에 검안·초안·미검증 문항 수를 적는다.

## 6. 마지막 보고 (세션 끝 메시지)

짧게 쓴다.
- 시간표 버전(바뀌었으면 이전 → 새 버전)
- 오늘 처리한 과목과 PR 링크, 머지 여부(머지 못 했으면 이유). 없으면 "처리할 과목 없음"
- 내일로 넘긴 과목
- 실패하거나 건너뛴 것(파일 오류, 빠진 연도, 그림 누락 수와 누락된 학습부 번호 — 사이트 맨 아래 안내와 같은 내용)

## 부록 A. 파일 구조

| 경로 | 내용 |
|---|---|
| `config/subjects.yaml` | 과목 매핑: slug ↔ 시간표 접두어 ↔ 드라이브 표기 ↔ 시험 표기, auto 여부, go_live |
| `state/timetable.json`, `logs/timetable.log` | 마지막 시간표 파싱 결과와 버전 기록 (auto/timetable-vNNN PR로만 변경) |
| `state/subjects/<slug>.json` | 과목 처리 상태 (done/skipped, verified, years, missing_years) |
| `state/sources/<slug>.json` | 읽은 드라이브 파일 id 목록 (past/guide) |
| `data/<slug>/meta.json · past.json · variants.json · chapters.json` | 과목 데이터 (형식: README.md) |
| `<slug>/index.html · card.json · figs/ · *_기출문제집.pdf` | 빌드 결과 (사이트) |
| `reports/<slug>.md` | 수집·판단 리포트 |
| `docs/variation-rules.md` | 변형 규칙 |
| `tools/` | timetable.py · state.py · extract_haeseol.py · compare_years.py · assemble.py · validate.py · build.py · pdf.py · smoke.js |

## 부록 B. 이번 구조를 만들 때 확인한 사실 (2026-11-16)

- 시간표 시트는 공개 링크로 읽을 수 없다(이 환경의 네트워크가 docs.google.com을 막는다). Google Drive 커넥터의 xlsx 내보내기만 된다. 2학기 블록은 날짜가 수식(`=I232+1`)으로 되어 있는데, timetable.py가 계산한다. 빨간 글씨(`FFFF0000`) 셀은 시험, 빨간 날짜 머리글은 휴일이다.
- 시트의 `레퍼런스` 탭에 과목명↔접두어·시험 키워드 정본이 있다. 새 과목 접두어가 생기면 여기를 보고 `config/subjects.yaml`을 고친다(PR로).
- 학과 드라이브 기출은 연도별 `YYYY 본과 2학년 2학기 <과목> 복원 (해설|수합)` 파일이다. 2024년 파일은 내분비·신경계 모두 없었다.
- `get_hwp_image`는 2025 신경계 해설 파일의 일부 그림에서 "BMP 형식이 아닙니다" 오류를 냈다.
