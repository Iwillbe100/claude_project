"""처방 가지 등록부 — **한 줄이 처방 가지 하나다.**

여기 적힌 순서가 곧 **진단 우선순위**다. 한 루프 안에서 증상이 둘 이상 보이면
위에 적힌 것부터 한 번에 하나씩 처방 가지를 탄다.

    kind    이름. 노드 이름이 여기서 나온다   fix_<kind> · test_<kind>
    loop    "A" 정보량(check_information 뒤)  ·  "B" 페이지(check_page 뒤)
    title   게이트 화면과 history 에 뜨는 한국어 이름

이름만 적으면 나머지는 **자리가 정해져 있다.**

    travel_graph/detours/<kind>.py          fix() 고치는 법 · inject() 실패 재현
    scripts/detour_tests/test_<kind>.py     시험지 — 진단도 이것으로, 합격도 이것으로

★ 새 처방 가지는 `python scripts/new_detour.py <kind> --loop A --title "…"` 가
  세 조각(이 줄 · 모듈 · 시험지)을 한 번에 만들어 준다. 손으로 추가해도 된다.
  `check_graph_shape.py` 의 **11번 검사(처방 가지 계약)** 가 세 조각이 맞물렸는지 본다.

★ 이 파일은 **값만** 담는다(함수 호출 · 변수 없음). 검사기가 import 하지 않고도
  읽을 수 있어야 하기 때문이다.
"""

#: 킷 기본 셋 — 셋 다 **알아본 실패**를 규칙으로 뺀 것이다. 그래프 안에서 늘 돈다
#: (진단은 매번 · 가지는 그 실패가 났을 때만).
#:   encoding     알려진 실패 축 — Windows cp949 · 현지 글자 파일명. 로그 실측 전에 미리 구축했다
#:   image_dead   루프 킷 실행 로그 — 모델이 해시 두 글자(8/8c)를 지어내 11장 전부 죽음
#:                (킷에 든 예시 인계본 graph/04_RUN_EVIDENCE.md 1-b). 재수집(LLM)으로는 또 지어낸다
#:   image_spec   실습생 게이트 입력 — "이미지 규격이 안 맞음" (원본 크기 사진 · 검사기는 못 본다)
DETOURS = (
    {"kind": "encoding",   "loop": "A", "title": "글자가 깨짐 (인코딩)"},
    {"kind": "image_dead", "loop": "A", "title": "이미지 주소가 죽어 있음"},
    {"kind": "image_spec", "loop": "B", "title": "사진이 화면 규격에 안 맞음"},
)
