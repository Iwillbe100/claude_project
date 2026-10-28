"""그래프 전체가 공유하는 작업 기억.

**루프의 조건① '시작 상태'가 여기로 옵니다.** 다만 뜻이 넓어집니다 —
루프에서는 "입력"이었지만 그래프에서는 **노드 사이에 흐르는 전부**입니다.

    노드는 이 중 일부만 읽고, 일부만 **변경분으로** 돌려준다.
    전체를 돌려주지 않는다. 그것이 노드가 서로를 모르게 만드는 장치다.

STEP 1 에서 이 파일의 필드 목록을 확정하고,
STEP 4 에서 `cities` · `city_failures` · `history` 에 reducer 를 붙입니다.

**진단 · 처방 가지 칸 6개는 킷 고정이다** (`inject` · `failure_kind` · `failure_evidence` ·
`detour_attempts` · `detour_limit` · `detour_verdict`). 판정은 검사기 노드가,
원인은 진단 노드가 따로 쓴다 — 라우터가 둘을 나란히 읽는다.
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

# ===========================================================================
# STEP 4 ▼ reducer 가 붙는 필드 **세 개**. **필드마다 답이 다르다.**
#
#   history        이어 붙인다        노드마다 한 줄씩 남기므로 add 가 맞다
#   cities         이름으로 덮어쓴다  재수집이 **같은 도시**를 다시 돌려주므로
#                                     add 를 쓰면 [하노이,다낭,호이안,하노이,...] 가 되어
#                                     검사기가 "도시 6개" 로 센다
#   city_failures  이름으로 덮어쓰되   실패가 사라진 것을 표현해야 하므로
#                  **빈 값이면 지운다**  add 도 단순 upsert 도 답이 아니다
#
# 되돌아오는 간선이 있는 그래프에서 reducer 는 **멱등**해야 한다.
# 아래 두 함수가 그 셋을 담당한다 (`history` 만 `operator.add`).
# ===========================================================================


def merge_cities(old: list, new: list) -> list:
    """도시 이름을 키로 upsert. 같은 이름이면 **새 것으로 교체**한다.

    `collect_city` 는 fan-out 으로 [도시1개] 를 돌려주고,
    `repair_city` 는 고친 [그 도시 1개] 를 돌려준다. 둘 다 이 reducer 를 지난다.
    순서를 지키려고 dict 가 아니라 리스트를 유지한다 (파이썬 dict 는 삽입 순서 보존).
    """
    merged = {}
    for city in list(old or []) + list(new or []):
        if isinstance(city, dict) and (city.get("name") or "").strip():
            merged[city["name"].strip()] = city
    return list(merged.values())


def merge_failures(old: list, new: list) -> list:
    """도시별 실패 기록 upsert. **`why` 가 비면 그 줄을 지운다** (= 이번엔 성공).

    이것이 없으면 한 번 실패한 도시가 재수집에 성공해도 게이트 화면에
    실패가 계속 남는다. 성공은 "기록이 사라지는 것"으로 표현한다.
    """
    merged = {}
    for row in list(old or []) + list(new or []):
        if not isinstance(row, dict) or not row.get("city"):
            continue
        if (row.get("why") or "").strip():
            merged[row["city"]] = row
        else:
            merged.pop(row["city"], None)
    return list(merged.values())
# STEP 4 ▲ =================================================================


class TravelInput(TypedDict, total=False):
    """Studio 실행 입력 폼이 이 스키마로 그려진다. `{}` 로도 실행된다.

    비워 두면 `read_request` 노드가 `graph/03_CONTRACT.json` 의 값으로 채운다.

    `inject` 는 **실패 재현** 칸이다. 처방 가지 이름을 적으면 수집 직후 그 실패를
    다시 일으킨다 — 예) `{"inject": ["image_dead"]}`. 이미 있는 가지가 켜지는 것을
    보거나, STEP 6 에서 새 가지의 시험지 빨간불을 먼저 볼 때 쓴다. 평소에는 비워 둔다.
    """

    country: str
    days: int
    style: dict
    city_priority: list[str]
    inject: list[str]


class TravelState(TypedDict, total=False):
    # ---- 입력 : read_request 가 채우고 이후 아무도 바꾸지 않는다 ---------------
    country: str
    days: int
    style: dict
    city_priority: list[str]

    # ---- 수집 결과 : 수집 노드가 채운다 ---------------------------------------
    country_intro: dict
    selected_city_names: list[str]

    # STEP 4 ▼ ---------------------------------------------------------------
    #   `operator.add` 가 아니다. 위 `merge_cities` 주석을 보라.
    cities: Annotated[list[dict], merge_cities]
    # STEP 4 ▲ ---------------------------------------------------------------

    #: 수집이 **실패한** 도시. 빈 껍데기를 정상인 척 돌려주지 않기 위한 칸이다.
    #: `collect_city` · `repair_city` 가 fan-out 으로 동시에 쓰므로 reducer 가 필요하다.
    #: 게이트 화면(`② 왜`)이 이것을 읽어 "그 도시는 수집 자체가 안 됐다"를 알린다.
    city_failures: Annotated[list[dict], merge_failures]

    # ---- 판정 : 검사기 노드가 쓰고, 라우터만 읽는다 ---------------------------
    info_verdict: str          # UNKNOWN | PASS | SHORT | ERROR
    info_short_slots: list[str]
    page_verdict: str          # UNKNOWN | PASS | SHORT | ERROR
    page_short_slots: list[str]
    quality_verdict: str       # UNKNOWN | PASS | SHORT | ERROR
    quality_short_slots: list[str]

    # ---- 루프 C : 정성 완성도 (킷 고정) ---------------------------------------
    # ★ **여기에 reducer 를 붙이지 마십시오.**
    #   `cities` 에 `operator.add` 를 붙이는 것을 배운 직후라 카운터에도 붙이는
    #   실수가 잦습니다. 회차 번호는 누적 리스트가 아니라 **단일 정수 덮어쓰기**입니다.
    #   붙이면 2회차에서 값이 1+2=3 이 되어 한 회차를 건너뛰고 나갑니다 (정성 2회만 돕니다).
    #   `check_graph_shape.py` 의 **8번 검사**가 이것을 ERROR 로 잡습니다.
    quality_pass: int              # 지금까지 끝낸 회차 수 (0 → 3)
    quality_passes_required: int   # 3. 계약에서 온다. 노드가 바꾸지 않는다

    # ---- 산출물 : 경로만 담는다. 본문은 파일에 둔다 ---------------------------
    html_path: str
    research_path: str

    # ---- 제어 : 라우터가 상한과 비교한다 --------------------------------------
    loop_a_iter: int
    loop_a_limit: int
    loop_b_iter: int
    loop_b_limit: int
    same_error_count: int
    same_error_limit: int
    last_error_hash: str

    # ---- 사람이 적어 넣는 칸 : human_gate 가 interrupt 로 받는다 --------------
    gate_a_answer: str         # more | proceed | stop
    gate_b_answer: str         # research | rebuild | done
    gate_note: str             # 자유 문장. **라우팅에 쓰지 않는다**

    # ---- 진단 · 처방 가지 (킷 고정) ---------------------------------------------
    #   판정(`*_verdict`)은 검사기 노드가 쓰고, **원인**(`failure_kind`)은 진단 노드가
    #   쓴다. 라우터는 둘 다 읽는다. 처방 가지는 한 번에 하나만 도므로 reducer 가 없다.
    inject: list[str]          # 실패 재현 (입력). 비어 있으면 아무 일도 없다
    failure_kind: str          # "" | 등록된 처방 가지 이름 (registry.py). **라우터가 읽는 칸**
    failure_evidence: list[str]  # 증상 몇 줄. 게이트 화면용 — **라우팅에 쓰지 않는다**
    detour_attempts: dict      # {처방 가지 이름: 이번에 몇 번 돌았나}. 덮어쓰기. 게이트에서 more(A) ·
                               # research · rebuild(B) 를 고를 때만 {} — proceed · done 이면 그대로
    detour_limit: int          # 처방 가지 하나가 사람 없이 돌 수 있는 횟수 (detours.LIMIT)
    detour_verdict: str        # "" | PASS | FAIL — 시험 노드가 쓰고, 검사기 노드가 읽고 비운다

    # STEP 4 ▼ ---------------------------------------------------------------
    history: Annotated[list[str], operator.add]
    # STEP 4 ▲ ---------------------------------------------------------------


class TravelOutput(TypedDict, total=False):
    """Studio 결과 패널에 보일 것만 추린다. 상태 전체를 쏟지 않는다."""

    info_verdict: str
    info_short_slots: list[str]
    page_verdict: str
    page_short_slots: list[str]
    quality_verdict: str
    quality_short_slots: list[str]
    html_path: str
    loop_a_iter: int
    loop_b_iter: int
    quality_pass: int
    gate_a_answer: str
    gate_b_answer: str
    city_failures: list[dict]
    failure_kind: str
    detour_attempts: dict
    history: list[str]


__all__ = ["TravelState", "TravelInput", "TravelOutput",
           "merge_cities", "merge_failures"]
