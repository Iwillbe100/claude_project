"""그래프 배선 — **킷 제공. 교육생은 이 파일을 고치지 않습니다.**

그래프는 세 겹이다. **루프 골격**은 그대로 두고, 알아본 실패에만 **규칙 처방 가지**를 연다.

    ① 루프 골격 (노드 14개)     루프 A 모은다 → 게이트 A → 루프 B 만든다 → 게이트 B → 루프 C 다듬는다
    ② 진단 (노드 2개)      검사기 바로 뒤. **판정**(기준을 채웠나) 다음에 **원인**(무엇이 터졌나)
    ③ 처방 가지 (등록부 1줄 = 노드 2개)   진단이 가려낸 문제만 · 고치고 → 시험 보고 → 검사기로 복귀

배선도 (★ = 사람 · ◇ = 진단 · ▷ = 처방 가지)

    START → read_request → { collect_country , select_cities }        ← 정적 간선 2개 = 병렬
                            select_cities -Send-> collect_city × N     ← fan-out ① 고른 도시 전부
    { collect_country , collect_city × N } → check_information        ← fan-in
    check_information → ◇diagnose_info
    ◇diagnose_info -route_after_info-> { ▷fix_<A 처방 가지> ,             ← 원인이 먼저
                                         repair_city × 다친 도시 ,      ← fan-out ② 지적된 것만
                                         repair_country × 0 또는 1 ,
                                         ★human_gate_a }
    { repair_city , repair_country } → check_information               ← 안쪽 루프 A
    ★human_gate_a -route_after_gate_a-> { repair_* , build_page , END } ← 바깥 루프 A
    build_page → check_page → ◇diagnose_page
    ◇diagnose_page -route_after_page-> { ▷fix_<B 처방 가지> , build_page , ★human_gate_b }
    ★human_gate_b -route_after_gate_b-> { check_information , rebuilder ,
                                          quality_pass , END }         ← 바깥 루프 B
    rebuilder → check_page
    quality_pass → check_quality -route_after_quality-> { quality_pass , build_page ,
                                                         ★human_gate_b , END }  ← 고정 예산 순환

    ▷ 처방 가지 하나 (모두 같은 모양)
      fix_<이름> → test_<이름> -route_after_detour-> { back  → 그 루프의 검사기 (같은 자로 다시 잰다)
                                                      retry → fix_<이름>      (한 번 더)
                                                      gate  → 그 루프의 게이트 (사람에게) }

**처방 가지는 등록부(`travel_graph/detours/registry.py`)를 읽어 붙인다.** 한 줄 등록하면
노드 두 개와 간선 세 갈래가 **같은 모양으로** 생긴다. 모양이 하나라 틀릴 곳이 없다.
`check_graph_shape.py` 11번 검사(처방 가지 계약)가 그 모양을 확인한다.

**처방 가지는 수집 노드로 돌아가지 않는다.** 합류가 `add_edge(["collect_country",
"collect_city"], ...)` 라 한쪽만 다시 돌면 합류가 영영 기다린다. 검사기로 돌아간다.

**fan-out 이 두 군데입니다.** ① 첫 수집은 고른 도시를 **전부** 보내고, ② 재수집은
검사기가 **지적한 것만** 보냅니다. 둘 다 `Send` 지만 갈래 폭을 정하는 기준이 다릅니다.

**게이트 B 의 `research` 는 재수집 노드로 바로 가지 않습니다.** `check_information`
으로 갑니다 — "어느 도시를 고칠까"를 정하는 곳을 하나로 두기 위해서입니다.

**정적 간선 여러 개는 if/else 가 아니라 병렬입니다.** 가장 흔한 함정이라 여기에
다시 적어 둡니다. 둘 중 하나만 고르려면 반드시 `add_conditional_edges` 를 씁니다.
검사기 → 진단이 **정적 간선 하나**인 것도 그래서입니다. 검사기에 조건부 간선까지
달면 두 갈래가 동시에 돈다.

**`quality_pass` 는 순환으로만 세 번 돕니다.** 정적 간선 세 개로 늘어놓으면 병렬이
되어 세 회차가 같은 파일을 동시에 고치고, 해시 사슬이 끊겨 판정기가 SHORT 를 냅니다.

체크포인터는 **붙이지 않습니다.** `langgraph dev`(Agent Server)가 스레드 영속화를
직접 담당하기 때문입니다. 여기서 하나를 몰래 구우면 그것과 싸우는 일이 됩니다.
순수 파이썬 · pytest 로 `interrupt` 를 돌릴 때만 `compile_graph(InMemorySaver())`.
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from travel_graph import detours, edges, nodes
from travel_graph.state import TravelInput, TravelOutput, TravelState

#: 루프 골격 — 루프 킷의 작업이 옮겨 온 노드와 루프에 없던 노드. **이 14개는 늘지도 줄지도 않는다.**
SPINE = (
    "read_request", "collect_country", "select_cities", "collect_city",
    "check_information", "repair_city", "repair_country", "human_gate_a",
    "build_page", "check_page", "human_gate_b", "rebuilder",
    "quality_pass", "check_quality",
)

#: 진단 — 검사기 바로 뒤. 처방 가지는 **여기서만** 갈라진다.
DIAGNOSE = ("diagnose_info", "diagnose_page")


def build() -> StateGraph:
    g = StateGraph(TravelState, input_schema=TravelInput, output_schema=TravelOutput)

    # ── ① 루프 골격 14개 ───────────────────────────────────────────────────────
    g.add_node("read_request", nodes.read_request)
    g.add_node("collect_country", nodes.collect_country)
    g.add_node("select_cities", nodes.select_cities)
    g.add_node("collect_city", nodes.collect_city)
    g.add_node("check_information", nodes.check_information)
    g.add_node("repair_city", nodes.repair_city)
    g.add_node("repair_country", nodes.repair_country)
    g.add_node("human_gate_a", nodes.human_gate_a)
    g.add_node("build_page", nodes.build_page)
    g.add_node("check_page", nodes.check_page)
    g.add_node("human_gate_b", nodes.human_gate_b)
    g.add_node("rebuilder", nodes.rebuilder)
    g.add_node("quality_pass", nodes.quality_pass)
    g.add_node("check_quality", nodes.check_quality)

    # ── ② 진단 2개 ───────────────────────────────────────────────────────
    g.add_node("diagnose_info", nodes.diagnose_info)
    g.add_node("diagnose_page", nodes.diagnose_page)

    # ── ③ 처방 가지 — 등록부 한 줄마다 노드 두 개 ──────────────────────────────
    for d in detours.ALL:
        g.add_node(d.fix_node, nodes.fix_detour)
        g.add_node(d.test_node, nodes.test_detour)

    g.add_edge(START, "read_request")

    # 정적 간선 2개 → 둘 다 실행된다 (하나를 고르는 게 아니다)
    g.add_edge("read_request", "collect_country")
    g.add_edge("read_request", "select_cities")

    # 도시 수만큼 갈라진다. 갈래 폭은 실행 중에 정해진다.
    g.add_conditional_edges("select_cities", edges.fan_out_cities, ["collect_city"])

    # 합류(fan-in). **리스트로 넘겨야** 둘 다 끝난 뒤 한 번만 돈다.
    #   add_edge("collect_country", "check_information")   두 줄로 나눠 쓰면
    #   add_edge("collect_city",    "check_information")   각각이 따로 방아쇠가 되어
    #                                                       뒤쪽 사슬이 통째로 두 번 돈다.
    g.add_edge(["collect_country", "collect_city"], "check_information")

    #  ★ 검사기 → 진단은 **정적 간선 하나**. 판정 다음에 원인을 가린다.
    g.add_edge("check_information", "diagnose_info")

    #  ★ 두 번째 fan-out. 라우터가 `Send` 목록을 돌려주면 그것이 그대로 실행되고,
    #    문자열을 돌려주면 아래 매핑에서 다음 노드를 찾는다. 매핑에 `repair_city` 를
    #    적어 두는 이유는 **그림과 구조 검사기가 이 간선을 볼 수 있게** 하기 위해서다.
    #    처방 가지 이름은 등록부에서 온다 — 루프 A 처방 가지마다 `이름 → fix_<이름>` 한 줄.
    g.add_conditional_edges(
        "diagnose_info", edges.route_after_info,
        {"repair": "repair_city", "repair_country": "repair_country",
         "gate": "human_gate_a",
         **{d.kind: d.fix_node for d in detours.of_loop("A")}},
    )
    g.add_edge("repair_city", "check_information")
    g.add_edge("repair_country", "check_information")

    g.add_conditional_edges(
        "human_gate_a", edges.route_after_gate_a,
        {"repair": "repair_city", "repair_country": "repair_country",
         "build": "build_page", "stop": END},
    )

    g.add_edge("build_page", "check_page")
    g.add_edge("check_page", "diagnose_page")
    g.add_conditional_edges(
        "diagnose_page", edges.route_after_page,
        {"retry": "build_page", "gate": "human_gate_b",
         **{d.kind: d.fix_node for d in detours.of_loop("B")}},
    )

    #  ★ `research` 는 재수집 노드로 바로 가지 않고 `check_information` 으로 간다.
    #    거기서 다시 세면 `route_after_info` 가 다친 도시만 골라 보낸다 —
    #    "어느 도시를 고칠까"를 정하는 곳을 하나로 둔다.
    #  ★ `rebuild` 는 `build_page`(결정론 렌더러)가 아니라 `rebuilder` 로 간다.
    #    사람의 지시문을 받을 수 있는 노드는 그쪽뿐이다.
    g.add_conditional_edges(
        "human_gate_b", edges.route_after_gate_b,
        {"research": "check_information", "rebuild": "rebuilder",
         "quality": "quality_pass", "done": END},
    )
    g.add_edge("rebuilder", "check_page")

    # 루프 C — 고정 예산 순환. **정적 간선으로 늘어놓지 않는다** (병렬이 되면 깨진다)
    g.add_edge("quality_pass", "check_quality")
    g.add_conditional_edges(
        "check_quality", edges.route_after_quality,
        {"again": "quality_pass", "build": "build_page",
         "gate": "human_gate_b", "halt": END},
    )

    # ── ③ 처방 가지 배선 — **모든 처방 가지가 같은 모양** ───────────────────────────
    #    fix → test 는 정적 간선. test 뒤에는 세 갈래뿐이다.
    #    back 은 **그 루프의 검사기**로 간다 — 같은 검사기로 다시 재야 판정 독립이 선다.
    for d in detours.ALL:
        g.add_edge(d.fix_node, d.test_node)
        g.add_conditional_edges(
            d.test_node, edges.route_after_detour,
            {"back": d.home, "retry": d.fix_node, "gate": d.gate},
        )
    return g


def compile_graph(checkpointer: Any = None):
    """두 진입점이 함께 쓰는 유일한 컴파일 지점.

    | 실행 경로 | 체크포인터 | `interrupt` |
    | --- | --- | --- |
    | `langgraph dev` (Studio) | 넘기지 않는다. Agent Server 가 제공 | 정상 동작 |
    | 순수 파이썬 · pytest | `InMemorySaver()` 를 **반드시** 주입 | 없으면 실패 |
    """
    builder = build()
    if checkpointer is not None:
        return builder.compile(checkpointer=checkpointer, name="travel")
    return builder.compile(name="travel")


#: `langgraph.json` 이 가리키는 심볼. 이름을 바꾸지 마십시오.
graph = compile_graph()

__all__ = ["graph", "build", "compile_graph", "SPINE", "DIAGNOSE"]
