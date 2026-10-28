"""간선 조건 — **루프의 조건⑥ '반복 규칙'이 여기로 옵니다.**

루프에서는 `if` 문이 코드 안에 있었습니다. 그래프에서는 그것이 **데이터를 읽는
라우터 함수**로 나옵니다. 라우터는 상태를 읽고 **다음 노드 이름만** 고릅니다.

    라우터는 작업을 하지 않는다. 상태를 바꾸고 싶으면 노드로 만들어라.

**이 파일은 완성된 상태로 배포됩니다.** 그래프가 바로 돌아야 인계본이 실제로
확장되는 모습을 볼 수 있기 때문입니다. STEP 3 에서 하는 일은 코드를 타이핑하는
것이 아니라 **왜 이 조건인지 읽고, 결정을 장부에 적고, 검사기로 확인하는 것**입니다.

    python scripts/check_graph_shape.py     # 지금 통과합니다. 통과하는 이유를 읽으십시오

바꾸고 싶으면 `STEP 3 ▼▼▼` ~ `▲▲▲` 구간만 고치고 같은 검사기를 다시 돌립니다.

**라우터는 두 칸을 나란히 읽는다.**

    판정  info_verdict · page_verdict   검사기 노드가 쓴다    "기준을 채웠나"
    원인  failure_kind                  진단 노드가 쓴다      "무엇이 터졌나 — 정해진 고칠 법이 있나"

원인이 등록된 처방 가지(`travel_graph/detours/registry.py`)이면 **판정보다 먼저** 그쪽으로
간다. 처방 가지가 보는 결함(깨진 글자 · 원본 크기 사진)은 검사기가 세지 않으므로 판정이
PASS 여도 있을 수 있기 때문이다. 그 분기는 `킷 고정 ▼` 표시 안에 있다.
"""
from __future__ import annotations

import re

from langgraph.types import Send

from travel_graph import detours

#: 검사기가 만든 부족 문구에서 **그 줄이 어느 도시 것인지** 가려낸다.
#
#  ★ 예전에는 `name in line` 이었다. 부분 문자열이라 `하노이시/롱비엔 다리` 가
#    `하노이` 에게도 배정됐고, 엉뚱한 도시의 모델이 자기 JSON 에 없는 경로를
#    고치라는 지시를 받아 patch 가 전부 거부됐다.
#    이름 앞뒤가 **경계**(줄 시작/끝 · 공백 · `/` · `·` · `↔`)일 때만 그 도시 것이다.
_EDGE = r"(?:^|[\s/·↔])"
_EDGE_R = r"(?:$|[\s/·↔:])"


def belongs_to(line: str, name: str) -> bool:
    """`line` 이 도시 `name` 의 부족인가. **부분 문자열이 아니라 토큰**으로 본다."""
    if not name:
        return False
    return re.search(_EDGE + re.escape(name) + _EDGE_R, str(line)) is not None


def orphan_shorts(state) -> list:
    """어느 재수집 노드로도 갈 수 없는 부족. **게이트가 이것을 숨기지 않는다.**

    ★ 재수집 대상은 `도시 이름이 든 줄` 과 `기능1 로 시작하는 줄` 뿐이다.
      둘 다 아닌 부족(예: `기능2 도시 개수: 목표 3 / 실제 2`)은 아무 데도 못 간다.
      예전에는 그것이 화면에 안 나타나 사람이 `more` 를 골랐고, 라우터는 보낼 곳이
      없어 조용히 `build` 로 떨어졌다. **고칠 수 없다는 사실 자체를 알려야 한다.**
    """
    names = [str(n) for n in (state.get("selected_city_names") or [])]
    out = []
    for line in (state.get("info_short_slots") or []):
        text = str(line)
        if "기능1" in text:
            continue
        if any(belongs_to(text, n) for n in names):
            continue
        out.append(text)
    return out


# --------------------------------------------------------------------------- #
# 도시별 fan-out — 킷 제공 (고정)
# --------------------------------------------------------------------------- #


def fan_out_cities(state) -> list:
    """도시 수는 `select_cities` 가 끝나야 압니다. 이런 동적 갈래에는 `Send` 를 씁니다.

    각 `Send` 는 **도시 하나만** 담은 payload 를 만들고, `collect_city` 노드가
    그 하나만 처리합니다. 셋이 나란히 돌고, 결과를 합치는 일은 reducer 가 합니다.

    ★ `inject`(실패 재현)는 **첫 도시에만** 싣는다. 실패가 한 곳에서만 나야
      처방 가지가 무엇을 고쳤는지 눈으로 따라갈 수 있다. `Send` 는 적어 준 칸만
      나르므로, 여기서 빼면 `collect_city` 는 재현할 실패를 모른다.
    """
    names = state.get("selected_city_names") or []
    return [
        Send("collect_city", {
            "city": name,
            "country": state.get("country"),
            "days": state.get("days"),
            "style": state.get("style"),
            "inject": state.get("inject") if index == 0 else [],
        })
        for index, name in enumerate(names)
    ]


def _tries(state, kind) -> int:
    """처방 가지 `kind` 가 사람의 판단 없이 몇 번 돌았나."""
    return int((state.get("detour_attempts") or {}).get(kind) or 0)


# ===========================================================================
# STEP 3 ▼▼▼  네 라우터. **상한을 보고, 자유 문장은 보지 않는다.**
#             (처방 가지 분기는 `킷 고정 ▼` 표시 안에 있다 — 지우지 않는다)
# ===========================================================================


def fan_out_repairs(state) -> list:
    """★ **두 번째 fan-out.** 다친 것만 갈라 보냅니다 — 도시와 국가 소개 둘 다.

    첫 수집(`fan_out_cities`)은 고른 도시를 전부 보내지만, 재수집은 **검사기가
    지적한 것만** 보냅니다. 손대지 않은 도시는 호출조차 되지 않습니다.

    예전에는 `research` 노드 하나가 안에서 모든 도시를 다시 불렀습니다. 다낭만
    터져도 하노이·호이안이 첫 수집 프롬프트로 떨어져 통째로 다시 뽑혔습니다.
    **부족한 칸이 줄지 않던 큰 이유가 이것이었습니다.**

    ★ **국가 소개도 여기서 갈라집니다.** 예전에는 빠져 있었는데, 그 근거가
      "분량이 작아 1회차에 실패할 이유가 없다" 였습니다. 그것은 **잘림**만 배제하지
      **수집 부족**은 배제하지 못합니다. 실제로 부족이 났고, 되먹임이 없어 그대로
      최종 보고서까지 갔습니다. 지금은 도시와 같은 규격으로 고칩니다.

    ★ 갈래 폭이 둘로 다릅니다 — 도시는 **다친 수만큼**, 국가는 **있어야 0 또는 1**.
      그래서 `cities` 는 reducer 가 필수지만 `country_intro` 는 한 걸음에 쓰는
      노드가 하나뿐이라 필요 없습니다.
    """
    shorts = [str(x) for x in (state.get("info_short_slots") or [])]
    failed = {row.get("city") for row in (state.get("city_failures") or [])
              if isinstance(row, dict) and (row.get("why") or "").strip()}
    payloads = []
    for name in (state.get("selected_city_names") or []):
        mine = [line for line in shorts if belongs_to(line, name)]
        if not mine and name not in failed:
            continue                     # 지적도 실패도 없는 도시 → 부르지 않는다
        payloads.append(Send("repair_city", {
            "city": name,
            "shorts": mine,
            "country": state.get("country"),
            "days": state.get("days"),
            "style": state.get("style"),
            #  지난 회차 결과를 실어 보낸다. `repair_one_city` 가 이것을 바탕으로
            #  patch 를 적용한다. 이것이 없으면 고칠 대상이 없어 첫 수집이 된다.
            "cities": state.get("cities"),
            "gate_a_answer": state.get("gate_a_answer"),
            "gate_note": state.get("gate_note"),
        }))

    #  ★ 국가 소개. 검사기의 국가 행은 이름이 `기능1 …` 로 시작한다.
    #    지적이 없으면 Send 자체를 만들지 않는다 — 도시와 같은 규칙이다.
    country_shorts = [line for line in shorts if "기능1" in line]
    if country_shorts:
        payloads.append(Send("repair_country", {
            "country": state.get("country"),
            #  지난 회차 결과. 이것이 없으면 고칠 대상이 없어 첫 수집이 된다.
            "country_intro": state.get("country_intro"),
            "shorts": country_shorts,
            "gate_a_answer": state.get("gate_a_answer"),
            "gate_note": state.get("gate_note"),
        }))
    return payloads


def route_after_info(state):
    """진단 A(`diagnose_info`) 뒤. **원인을 먼저, 판정을 다음에, 상한은 탈출구로 본다.**

    SHORT 이면 재수집으로 돌아가되, 바퀴를 다 썼거나 같은 오류가 반복되면
    사람에게 넘긴다. 상한이 없으면 인터넷에 없는 정보를 영원히 찾는다.

    ★ 돌려주는 값이 세 종류다 — **처방 가지 이름**(`fix_<이름>` 으로), **`Send` 목록**
      (재수집), **문자열**(게이트). `Send` 를 돌려주면 LangGraph 가 그것을 그대로
      실행하고, 문자열이면 `build.py` 의 매핑에서 다음 노드를 찾는다.
    """
    # ---- 킷 고정 ▼ 처방 가지 — 진단이 고른 원인이 있으면 **판정보다 먼저** --------
    #   깨진 글자 · 죽은 사진 주소는 정해진 고칠 법이 있다. 재수집(LLM)보다 먼저
    #   그쪽으로 보낸다. 처방 가지마다 한도(`detour_limit`)가 있어 무한히 돌지 않는다.
    kind = state.get("failure_kind") or ""
    if kind in detours.kinds("A") and _tries(state, kind) < (state.get("detour_limit") or 0):
        return kind
    # ---- 킷 고정 ▲ ---------------------------------------------------------

    if state.get("info_verdict") != "SHORT":
        return "gate"
    if (state.get("loop_a_iter") or 0) >= (state.get("loop_a_limit") or 0):
        return "gate"                                   # 바퀴를 다 썼다
    if (state.get("same_error_count") or 0) >= (state.get("same_error_limit") or 0):
        return "gate"                                   # 진전이 없다
    sends = fan_out_repairs(state)
    return sends or "gate"                              # 고칠 도시가 없으면 사람에게


def route_after_gate_a(state):
    """게이트 A 뒤. **`action` 세 값만 본다.**

    ★ 사람이 적은 **자유 문장은 보지 않는다.** 문장으로 경로를 고르면 "더 모으지
      말고 그냥 진행"이라고 쓴 데서 '더'가 걸려 재수집으로 간다. 그 문장은 경로가
      아니라 **재수집 프롬프트에 실리는 내용**이다 (`research._human_note`).
      `check_graph_shape.py` 5번 검사가 이 규칙을 강제한다 — 그 검사는 라우터의
      소스 텍스트를 보므로, 여기서는 그 필드 이름을 **주석에도 적지 않는다.**
    """
    action = state.get("gate_a_answer")
    if action == "stop":
        return "stop"
    if action == "more":
        sends = fan_out_repairs(state)
        return sends or "build"                         # 고칠 데가 없으면 그냥 진행
    return "build"


def route_after_page(state) -> str:
    """진단 B(`diagnose_page`) 뒤. **원인을 먼저 보고, 상한을 본다.** (루프 A 와 같은 이유)"""
    # ---- 킷 고정 ▼ 처방 가지 — 진단이 고른 원인이 있으면 **판정보다 먼저** --------
    kind = state.get("failure_kind") or ""
    if kind in detours.kinds("B") and _tries(state, kind) < (state.get("detour_limit") or 0):
        return kind
    # ---- 킷 고정 ▲ ---------------------------------------------------------

    if state.get("page_verdict") != "SHORT":
        return "gate"
    if (state.get("loop_b_iter") or 0) >= (state.get("loop_b_limit") or 0):
        return "gate"
    return "retry"


def route_after_gate_b(state) -> str:
    """게이트 B 뒤. **`action` 네 값만 본다.**

    ★ `research` 는 재수집 노드로 바로 가지 않고 **`check_information` 으로** 간다.
      거기서 다시 세면 `route_after_info` 가 다친 도시만 골라 보낸다.
      재수집 진입점을 하나로 두면 "어느 도시를 고칠까"를 한 곳에서만 정하게 된다.

    ★ `rebuild` 는 `build_page` 가 아니라 **`rebuilder`** 로 간다. `build_page` 는
      결정론 렌더러라 사람의 지시문을 받을 데가 없다. 지시문을 실제로 소비하는
      노드가 `rebuilder` 다.
    """
    action = state.get("gate_b_answer")
    if action == "research":
        return "research"
    if action == "rebuild":
        return "rebuild"

    # ---- 킷 고정 ▼ 게이트 B 는 두 번 섭니다 --------------------------------
    #   정성 3회 전  →  루프 C 로 보낸다
    #   정성 3회 후  →  END
    if state.get("quality_pass", 0) >= state.get("quality_passes_required", 3):
        return "done"
    return "quality"
    # ---- 킷 고정 ▲ ---------------------------------------------------------


# ===========================================================================
# STEP 3 ▲▲▲  여기까지가 교육생이 고치는 부분입니다.
# ===========================================================================


# --------------------------------------------------------------------------- #
# 다섯 번째 라우터 — **킷 고정.** 루프 C 는 결정이 늘어나지 않습니다.
# --------------------------------------------------------------------------- #


def route_after_quality(state) -> str:
    """검사기 C 뒤. **앞의 두 라우터와 모양이 다릅니다.**

        route_after_info    verdict 를 먼저 보고, 상한은 탈출구로 본다
        route_after_page    같음
        route_after_quality **카운터를 정상 경로로 본다** — 상한이 아니라 목표다

    루프 A·B 의 상한은 "여기까지만 돈다"는 **최대값**이지만, 루프 C 의 3회는
    **최소이자 최대**입니다. 통과선이 아니라 고정 예산이라 이렇게 생깁니다.
    `check_graph_shape.py` 의 9번 검사가 이 라우터가 카운터와 그 상한을 함께
    읽는지 확인합니다.
    """
    if state.get("quality_verdict") == "ERROR":
        return "halt"                                   # 기록이 깨졌다 · 판정을 못 했다
    if state.get("quality_verdict") == "PASS":
        return "gate"                                   # 3회 완료 → 사람 확인
    if state.get("page_verdict") != "PASS":
        return "build"                                  # 되돌아감 → 페이지부터 다시
    if state.get("quality_pass", 0) >= state.get("quality_passes_required", 3):
        return "gate"                                   # 3회를 돌았는데 기록이 미비
    return "again"                                      # 남은 회차를 돈다


# --------------------------------------------------------------------------- #
# 처방 가지 시험 뒤 — **킷 고정.** 모든 처방 가지가 이 라우터 하나를 같이 쓴다.
# --------------------------------------------------------------------------- #


def route_after_detour(state) -> str:
    """시험 노드(`test_<이름>`) 뒤. **합격이면 그 루프의 검사기로, 불합격이면 한 번 더, 한도면 사람에게.**

        back    합격 → 루프 골격의 검사기 노드로 복귀 (루프 A 는 check_information,
                루프 B 는 check_page). **같은 검사기로 다시 잰다** — 판정 독립
        retry   불합격 · 한도 안 → 같은 fix 노드로 한 번 더 (시도할수록 센 방법을 쓴다)
        gate    불합격 · 한도 끝 → 사람 (그 루프의 게이트)

    어느 처방 가지에서 왔는지는 매핑이 안다 (`build.py` 가 처방 가지마다 매핑을 따로 단다).
    이 라우터는 "합격했나 · 몇 번 했나"만 본다.
    """
    if state.get("detour_verdict") == "PASS":
        return "back"
    if _tries(state, state.get("failure_kind") or "") < (state.get("detour_limit") or 0):
        return "retry"
    return "gate"


#: 라우터가 돌려줄 수 있는 값. `build.py` 의 매핑과 이 표가 어긋나면
#: 런타임에 KeyError 가 납니다. `check_graph_shape.py` 4번 · 10번 검사가 이것을 봅니다.
#: 처방 가지 이름은 등록부(`travel_graph/detours/registry.py`)에서 읽는다 — 한 줄 등록하면
#: 이 표와 `build.py` 의 매핑이 **함께** 늘어난다.
ALLOWED = {
    #  `route_after_info` · `route_after_gate_a` 는 문자열 말고 **`Send` 목록**도
    #  돌려줍니다. `Send` 는 매핑을 거치지 않고 LangGraph 가 직접 처리하므로
    #  이 표에는 문자열만 적습니다.
    "route_after_info": {"gate", "repair", "repair_country", *detours.kinds("A")},
    "route_after_gate_a": {"build", "stop", "repair", "repair_country"},
    "route_after_page": {"retry", "gate", *detours.kinds("B")},
    "route_after_gate_b": {"research", "rebuild", "quality", "done"},
    "route_after_quality": {"halt", "gate", "build", "again"},
    "route_after_detour": {"back", "retry", "gate"},
}
