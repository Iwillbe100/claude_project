"""처방 가지 — {TITLE}. **루프 {LOOP}.**

★ 이 파일은 `python scripts/new_detour.py` 가 복사해 쓰는 **틀**이다. 직접 등록하지 않는다.
  복사본은 `travel_graph/detours/<kind>.py` 가 되고, `{KIND}` 같은 자리가 채워진다.

증상  시험지 `scripts/detour_tests/test_{KIND}.py` 가 가려낸다
    (무엇이 보이면 이 문제인가 — 실패 기록 evidence/failures/*.jsonl 의 어느 줄에서 왔나)

고치는 법
    1회째  (정해진 절차로 고친다 — 같은 입력이면 같은 결과가 나오게)
    2회째  (1회째로 안 되면 무엇을 더 하나. 더 할 것이 없으면 적지 않는다 → 사람에게 간다)

실패 재현 (`inject`)
    (이 문제를 **일부러** 만드는 법 — 누구든 replay 에서 재현할 수 있게)

지켜야 할 것 (`check_graph_shape.py` 11번 검사 · 처방 가지 계약)
    - `fix` 는 `data` 만 고친다. 판정 · 카운터 · 게이트 칸은 노드(`nodes.fix_detour`)가
      다루므로 여기서 손댈 수 없다.
    - 시험지는 이 파일을 import 하지 않는다 (판정 독립).
    - 계약(`graph/03_CONTRACT.json`)을 낮추는 방식으로 고치지 않는다.
"""
from __future__ import annotations

KIND = "{KIND}"
INJECT_AT = "city"                  # "city"(첫 도시) 또는 "country"(국가 소개)
HOWTO = "{TITLE} — 처방 가지가 못 고쳤습니다. (게이트 화면 '고치려면' 칸에 뜨는 문장)"


def fix(data: dict, *, attempt: int, mode: str) -> dict:
    """`data`(country · days · country_intro · cities)를 **그 자리에서** 고친다.

    attempt  몇 번째 시도인가 (1부터). 시도할수록 센 방법을 쓸 수 있다
    mode     "live" 또는 "replay". replay 는 네트워크를 쓰지 않는다
    돌려주는 것  {"fixed": [고친 곳 한 줄씩], "unfixed": [못 고친 곳 한 줄씩]}
    """
    fixed, unfixed = [], []
    # TODO(교육생): 시험지가 가려낸 증상을 여기서 고친다.
    return {"fixed": fixed, "unfixed": unfixed}


def inject(obj: dict) -> str:
    """그 실패를 일부러 다시 일으킨다 (실패 재현). `INJECT_AT` 이 "city" 면 첫 도시, "country" 면 국가 소개가 온다.

    돌려주는 것  무엇을 재현했는지 한 줄 (재현하지 않았으면 빈 문자열)
    """
    return ""
