# 프로젝트 메모 (Claude Code)
- 본과 2학년 과목별 기출 퀴즈 정적 사이트. GitHub Pages(main 루트). 예약 작업 지침은 AUTOMATION.md, 변형 규칙은 docs/variation-rules.md.
- main에 직접 커밋하지 않는다. 변경은 auto/… 또는 작업 브랜치 → PR → 검사(validate·smoke) 통과 후 스스로 머지(REST `pulls/<n>/merge`). 사용자가 사이트를 보다 오류를 알려 주면 그때 고친다.
- 정답은 복원 해설이 아니라 2026년 강의 자료(26 학습부) 기준. 복원 답과 다르면 N(비고)에 적고 ra에 복원 답을 남긴다. 강의 자료가 없으면 ok:false(미검증).
- 근거에 '학습부' 출처 표기는 해도 된다(예: "26 학습부 03번 · 강의명"). 단 학생 이름·전화번호·학습부 사진은 사이트·PDF·데이터·커밋·PR 어디에도 넣지 않는다. validate.py가 전화번호·'○○ 학우' 표기를 검사한다.
- 데이터 수정은 data/<slug>/*.json → `python3 tools/build.py [--pdf <slug>]` → `node tools/smoke.js`.
- 페이지는 외부 요청 없이 동작해야 한다(데이터·그림 모두 저장소 안). 홈은 같은 사이트의 <slug>/card.json만 읽는다.
- repeat 파트에는 변형 문항을 넣지 않는다. 내분비 gen.js 수정 후에는 정답 인덱스·선지 중복을 검사한다.
- 시간표 파일(state/timetable.json, logs/timetable.log)은 auto/timetable-vNNN PR에서만 바꾼다(과목 PR과 충돌 방지).
- 이 환경에서는 원격 브랜치를 지울 수 없다. 브랜치 이름에 날짜·버전을 붙여 재사용하지 않고, 진행 여부는 열린 PR로 판단한다(tools/state.py).
