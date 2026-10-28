#!/usr/bin/env python3
"""그래프에만 있는 실패를 잡는다 — 검사행 12개. **킷 소유 — 수정 금지.**

루프 킷의 검사기들은 "결과물이 계약을 채웠는가"를 봤다. 이 검사기는 그 앞 단계 —
**"그래프 구조가 애초에 성립하는가"** 를 본다. 실행하지 않고 정적으로 본다.

  루프에는 없던 실패
    도달 불가 노드 · 종료 없는 순환 · reducer 없는 병렬 쓰기 ·
    라우터 반환값 불일치 · 자유 문장 라우팅 · 죽은 상태 필드 · 상한 없는 순환
    회차 카운터에 reducer · 고정 예산 순환이 카운터를 안 봄        ← 8·9 신규
    처방 가지 계약 — 처방 가지는 진단에서만 나고, 검사기로 돌아온다      ← 11 신규

  8·9번은 왜 늘었나
    루프 C(정성 완성도)가 들어오면서 **모양이 다른 순환**이 하나 생겼다.
    루프 A·B 는 "검사기가 통과할 때까지" 도는 통과선 루프지만,
    루프 C 는 "정해진 3회를 채울 때까지" 도는 고정 예산 루프다.
    닫는 것이 verdict 가 아니라 **카운터**라서 1~7번으로는 잡히지 않는다.

  11번은 왜 늘었나
    노드를 늘리는 것을 **문제가 난 지점에서만** 허용했다 (처방 가지). 허용한 만큼 모양을
    잠근다 — 루프 골격 14개 · 진단 2개 · 등록된 처방 가지 노드 말고는 노드가 없어야 하고,
    처방 가지는 진단에서만 갈라져 **그 루프의 검사기로** 돌아와야 한다. 시험지는 고치는
    코드를 import 하지 않는다 (판정 독립). 이 모양이 깨져도 1~10번은 대부분 통과한다.

  검사 방법
    travel_graph.build.build()   노드 · 간선 · 라우터 매핑 · 노드마다 실제로 붙은 함수
    travel_graph.state           Annotated 로 reducer 가 붙었는지
    노드 함수가 있는 소스         각 노드가 무슨 키를 쓰는지 (return {...} 리터럴)
    edges.py 소스                라우터가 무엇을 읽는지
    detours/registry.py          등록된 처방 가지와 그 세 조각 (모듈 · 시험지)

종료 코드 (루프 킷과 동일)
  0  PASS    구조 이상 없음
  1  ERROR   깨졌다 — 사람이 고쳐야 한다
  2  SHORT   경고는 있지만 돌기는 한다

사용법
  python scripts/check_graph_shape.py
  python scripts/check_graph_shape.py --json
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _contract import Result, print_result, use_utf8_output  # noqa: E402

use_utf8_output()

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "travel_graph"

START = "__start__"
END = "__end__"

#: 순환을 끊을 수 있다고 인정하는 근거. 하나도 없으면 무한루프 위험이다.
#: `quality_passes_required` 가 없으면 루프 C 순환이 "종료 조건 없음"으로 오판된다.
TERMINATORS = (
    "loop_a_limit", "loop_b_limit", "same_error_limit", "max_iterations",
    "quality_passes_required", "detour_limit",
    "PASS", "gate_a_answer", "gate_b_answer",
)

#: 회차·바퀴를 세는 칸의 이름 끝. 이런 이름의 int 필드에는 reducer 를 붙이면 안 된다.
#: 카운터는 **누적이 아니라 덮어쓰기**다.
COUNTER_SUFFIXES = ("_pass", "_iter", "_count")

#: 카운터형 종료 조건. (카운터 이름 끝, 그 상한 이름 끝)
COUNTER_PAIRS = (("_pass", "_passes_required"), ("_iter", "_limit"), ("_count", "_limit"))

#: 라우팅에 쓰면 안 되는 자유 문장 필드. 제어가 문장 해석에 좌우된다.
#: `failure_evidence` 는 증상을 사람에게 보여 주는 문장이다 — 라우터는 `failure_kind` 만 본다.
FREE_TEXT_FIELDS = ("gate_note", "failure_evidence")

#: 처방 가지 노드가 **쓰면 안 되는** 칸. 판정 · 바퀴 · 게이트는 루프 골격의 것이다.
#: 처방 가지가 이것을 쓰면 "처방 가지가 스스로 합격 판정을 내리는" 길이 열린다.
SPINE_OWNED = (
    "info_verdict", "info_short_slots", "page_verdict", "page_short_slots",
    "quality_verdict", "quality_short_slots", "loop_a_iter", "loop_b_iter",
    "quality_pass", "same_error_count", "last_error_hash",
    "loop_a_limit", "loop_b_limit", "same_error_limit", "quality_passes_required",
    "detour_limit", "gate_a_answer", "gate_b_answer", "gate_note",
)

#: 코드가 아니라 **사람이** 읽는 칸. 검사 6에서 '죽은 필드'로 보지 않는다.
#: (Studio 화면·최종 보고서·증거 기록에서 쓰인다)
HUMAN_READ_FIELDS = ("history", "research_path", "html_path", "gate_note")


# --------------------------------------------------------------------------
# 소스 읽기
# --------------------------------------------------------------------------


def _tree(name: str) -> ast.Module:
    return ast.parse((PKG / name).read_text(encoding="utf-8"))


def node_to_function(builder) -> dict:
    """노드 이름 → `(소스 파일, 함수 이름)`. **그래프에 실제로 붙은 함수**를 본다.

    ★ 예전에는 `build.py` 의 `add_node("이름", nodes.함수)` 글자를 읽었다. 그러면
      등록부를 읽어 반복문으로 붙이는 처방 가지 노드(`add_node(d.fix_node, …)`)를 **조용히
      건너뛴다** — 3 · 6 · 6b 번이 그 노드를 못 본다. 그래서 그래프에서 노드마다 붙은
      함수를 직접 꺼낸다. 함수를 못 꺼내면(람다 · partial) 빈 이름을 두고 6b 가 알린다.
    """
    import inspect
    mapping = {}
    for name, spec in builder.nodes.items():
        fn = getattr(getattr(spec, "runnable", None), "func", None)
        source, fname = "", ""
        if inspect.isfunction(fn) and fn.__name__ != "<lambda>":
            try:
                source = Path(inspect.getsourcefile(fn) or "").resolve() \
                    .relative_to(PKG.resolve()).as_posix()
            except (TypeError, ValueError):
                source = ""
            fname = fn.__name__
        mapping[name] = (source, fname)
    return mapping


def written_keys(files) -> dict:
    """노드 함수가 `return {...}` 로 돌려주는 상태 키. `(파일, 함수)` → 키 집합."""
    out = {}
    for rel in sorted(set(files)):
        if not rel or not (PKG / rel).exists():
            continue
        for fn in ast.walk(_tree(rel)):
            if not isinstance(fn, ast.FunctionDef):
                continue
            keys = set()
            for stmt in ast.walk(fn):
                if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Dict):
                    for k in stmt.value.keys:
                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                            keys.add(k.value)
            if keys:
                out[(rel, fn.name)] = keys
    return out


def router_sources() -> dict:
    """라우터 함수 이름 → (소스 텍스트, 돌려주는 문자열 리터럴 집합)."""
    text = (PKG / "edges.py").read_text(encoding="utf-8")
    lines = text.splitlines()
    out = {}
    for fn in ast.walk(ast.parse(text)):
        if not isinstance(fn, ast.FunctionDef) or not fn.name.startswith("route_"):
            continue
        body = "\n".join(lines[fn.lineno - 1: (fn.end_lineno or fn.lineno)])
        returns = set()
        for stmt in ast.walk(fn):
            if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant):
                if isinstance(stmt.value.value, str):
                    returns.add(stmt.value.value)
        out[fn.name] = (body, returns)
    return out


def read_keys() -> set:
    """`state.get("키")` · `state["키"]` · `payload.get("키")` 로 읽히는 키."""
    found = set()
    detour_files = sorted(p.relative_to(PKG).as_posix()
                          for p in (PKG / "detours").glob("*.py")
                          if not p.name.startswith("_"))
    for name in ("nodes.py", "edges.py", "page.py", "research.py", *detour_files):
        try:
            tree = _tree(name)
        except SyntaxError:
            #  ★ 교육생이 막 만든 처방 가지 모듈에 문법 오류가 있을 수 있다. 여기서 죽으면
            #    트레이스백만 남는다 — 건너뛰고 11번(처방 가지 계약)이 **어느 줄인지** 알린다.
            continue
        for call in ast.walk(tree):
            if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "get" and call.args
                    and isinstance(call.args[0], ast.Constant)
                    and isinstance(call.args[0].value, str)):
                found.add(call.args[0].value)
            if (isinstance(call, ast.Subscript) and isinstance(call.slice, ast.Constant)
                    and isinstance(call.slice.value, str)):
                found.add(call.slice.value)
    return found


# --------------------------------------------------------------------------
# 그래프 구조
# --------------------------------------------------------------------------


def load_graph():
    from travel_graph.build import build
    from travel_graph.state import TravelState

    builder = build()
    drawn = builder.compile().get_graph()
    edges = [(e.source, e.target, bool(e.conditional)) for e in drawn.edges]
    #  ★ **출처마다** 한 줄씩 둔다. 라우터 이름으로만 모으면 같은 라우터를 여러 노드가
    #    쓸 때(처방 가지 시험 노드들이 `route_after_detour` 하나를 같이 쓴다) 마지막
    #    하나만 남아, 나머지 처방 가지의 순환이 "라우터 없음"으로 보인다.
    branches = []
    for source, group in (builder.branches or {}).items():
        for router_name, branch in group.items():
            branches.append((router_name, source, dict(getattr(branch, "ends", {}) or {})))
    return builder, edges, branches, TravelState


def reducer_fields(state_cls) -> set:
    from typing import Annotated, get_origin, get_type_hints

    hints = get_type_hints(state_cls, include_extras=True)
    return {k for k, v in hints.items() if get_origin(v) is Annotated}


def all_fields(state_cls) -> set:
    from typing import get_type_hints
    return set(get_type_hints(state_cls, include_extras=True).keys())


def counter_fields(state_cls) -> dict:
    """`*_pass` · `*_iter` · `*_count` 인 **int** 필드 → reducer 가 붙었는가.

    이름이 아니라 **타입까지** 본다. `info_short_slots` 같은 list 는 걸리지 않는다.
    """
    from typing import Annotated, get_args, get_origin, get_type_hints

    out = {}
    for name, hint in get_type_hints(state_cls, include_extras=True).items():
        if not name.endswith(COUNTER_SUFFIXES):
            continue
        annotated = get_origin(hint) is Annotated
        base = get_args(hint)[0] if annotated else hint
        if base is int:
            out[name] = annotated
    return out


def successors(edges, node):
    return [t for s, t, _ in edges if s == node]


def find_cycles(edges, nodes):
    """작은 그래프이므로 DFS 로 전부 찾는다."""
    cycles = []
    seen = set()

    def walk(node, path):
        for nxt in successors(edges, node):
            if nxt in path:
                cycle = path[path.index(nxt):] + [nxt]
                key = tuple(sorted(set(cycle)))
                if key not in seen:
                    seen.add(key)
                    cycles.append(cycle)
                continue
            if len(path) < len(nodes) + 1:
                walk(nxt, path + [nxt])

    for start in nodes:
        walk(start, [start])
    return cycles


# --------------------------------------------------------------------------
# 11번 — 처방 가지 계약
# --------------------------------------------------------------------------


def _imports_travel_graph(path: Path) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(a.name.split(".")[0] == "travel_graph"
                                                for a in node.names):
            return True
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "travel_graph":
            return True
    return False


def _module_shape(path: Path) -> list:
    """처방 가지 모듈이 약속한 모양인가 — `fix(data, *, attempt, mode)` · `inject(obj)` · `INJECT_AT`."""
    missing = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return [f"문법 오류 — {exc.lineno}번째 줄: {exc.msg}"]
    except OSError as exc:
        return [f"읽을 수 없습니다 ({type(exc).__name__})"]
    funcs = {fn.name: fn for fn in tree.body if isinstance(fn, ast.FunctionDef)}
    fix = funcs.get("fix")
    if fix is None:
        missing.append("fix(data, *, attempt, mode) 함수가 없습니다")
    else:
        kw = {a.arg for a in fix.args.kwonlyargs}
        if not fix.args.args or not {"attempt", "mode"} <= kw:
            missing.append("fix 의 모양이 fix(data, *, attempt, mode) 가 아닙니다")
    if "inject" not in funcs:
        missing.append("inject(obj) 함수가 없습니다")
    inject_at = None
    for stmt in tree.body:
        if (isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "INJECT_AT"
                                                 for t in stmt.targets)
                and isinstance(stmt.value, ast.Constant)):
            inject_at = stmt.value.value
    if inject_at not in ("city", "country"):
        missing.append("INJECT_AT 이 \"city\" 또는 \"country\" 가 아닙니다")
    return missing


#: 루프 골격 14 · 진단 2 의 **정본 이름**. `build.py` 의 `SPINE` 을 기준으로 삼으면, 거기에 이름을
#: 하나 더 적고 노드를 끼워 넣어도 통과한다 — 검사기가 검사 대상을 기준으로 삼는 꼴이다.
SPINE_NAMES = (
    "read_request", "collect_country", "select_cities", "collect_city",
    "check_information", "repair_city", "repair_country", "human_gate_a",
    "build_page", "check_page", "human_gate_b", "rebuilder",
    "quality_pass", "check_quality",
)
DIAGNOSE_NAMES = ("diagnose_info", "diagnose_page")


def _router_reads(name: str, key: str) -> bool:
    """라우터 `name` 이 **코드에서** 문자열 `key` 를 쓰는가. 주석 · docstring 은 세지 않는다
    (`# detour_limit 은 나중에` 같은 주석으로 통과하지 못하게)."""
    try:
        tree = _tree("edges.py")
    except (OSError, SyntaxError):
        return False
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef) and fn.name == name:
            body = fn.body[1:] if (fn.body and isinstance(fn.body[0], ast.Expr)
                                   and isinstance(getattr(fn.body[0], "value", None), ast.Constant)
                                   and isinstance(fn.body[0].value.value, str)) else fn.body
            return any(isinstance(n, ast.Constant) and n.value == key
                       for stmt in body for n in ast.walk(stmt))
    return False


def _test_shape(path: Path) -> list:
    """시험지가 약속한 모양인가 — 문법이 맞고 `run(root=None)` 이 있다."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return [f"시험지 문법 오류 — {exc.lineno}번째 줄: {exc.msg}"]
    except OSError as exc:
        return [f"시험지를 읽을 수 없습니다 ({type(exc).__name__})"]
    if not any(isinstance(fn, ast.FunctionDef) and fn.name == "run" for fn in tree.body):
        return ["시험지에 run(root=None) 함수가 없습니다"]
    return []


def detour_contract(builder, edges, branches, node_fn, writes) -> list:
    """처방 가지 계약. 돌려주는 것: 문제 문장 목록 (없으면 통과)."""
    try:
        from travel_graph import detours
        from travel_graph.build import DIAGNOSE, SPINE
    except Exception as exc:  # noqa: BLE001
        return [f"처방 가지 등록부를 불러오지 못했습니다: {type(exc).__name__}: {exc}"]

    problems = []
    if tuple(SPINE) != SPINE_NAMES or tuple(DIAGNOSE) != DIAGNOSE_NAMES:
        problems.append("build.py 의 SPINE · DIAGNOSE 가 킷의 루프 골격 14개 · 진단 2개와 다릅니다 — "
                        "루프 골격은 늘지도 줄지도 않습니다. 노드는 처방 가지로만 늘립니다")
    SPINE, DIAGNOSE = SPINE_NAMES, DIAGNOSE_NAMES              # 기준은 검사기가 쥔다
    nodes = set(builder.nodes)
    registered = {}
    for d in detours.ALL:
        registered[d.fix_node] = d
        registered[d.test_node] = d

    # (a) 노드는 루프 골격 · 진단 · 등록된 처방 가지뿐 — "문제가 난 지점에서만" 늘린다
    for name in sorted(nodes - set(SPINE) - set(DIAGNOSE) - set(registered)):
        problems.append(f"`{name}` 은 루프 골격 14개 · 진단 2개 · 등록된 처방 가지 어디에도 없는 노드입니다. "
                        f"노드는 처방 가지로만 늘립니다 (travel_graph/detours/registry.py)")
    for name in sorted((set(SPINE) | set(DIAGNOSE)) - nodes):
        problems.append(f"루프 골격/진단 노드 `{name}` 가 그래프에 없습니다")

    static = {}
    for source, target, conditional in edges:
        if not conditional:
            static.setdefault(source, set()).add(target)
    by_source = {}
    for router_name, source, ends in branches:
        by_source.setdefault(source, []).append((router_name, ends))

    # (b) 검사기 → 진단은 정적 간선 **하나뿐** (조건부 간선을 같이 달면 두 갈래가 동시에 돈다)
    for checker, diagnose in (("check_information", "diagnose_info"), ("check_page", "diagnose_page")):
        outs = {t for s, t, _c in edges if s == checker}
        if outs != {diagnose} or checker in by_source:
            problems.append(f"`{checker}` 뒤에는 `{diagnose}` 로 가는 정적 간선 하나만 있어야 합니다 "
                            f"(지금: {sorted(outs) or '없음'})")
        # (h) 진단 뒤 라우터가 원인(failure_kind)과 한도(detour_limit)를 읽는가 — `킷 고정 ▼` 분기를 지우면 배선(매핑)은
        #      남아 있어 4 · 10번은 통과하는데, 실패를 재현해도 처방 가지가 **영영 안 켜진다.**
        for name, _ends in by_source.get(diagnose, []):
            missing = [k for k in ("failure_kind", "detour_limit") if not _router_reads(name, k)]
            if missing:
                problems.append(f"`{diagnose}` 뒤 라우터 `{name}` 가 {missing} 을 읽지 않습니다 — "
                                f"`킷 고정 ▼` 처방 가지 분기가 지워졌습니다. 실패를 재현해도 처방 가지가 안 켜집니다")

    for d in detours.ALL:
        tag = f"처방 가지 `{d.kind}`"
        # (c) 세 조각이 제자리에 있나
        if d.fix_node not in nodes or d.test_node not in nodes:
            problems.append(f"{tag}: 노드 `{d.fix_node}` · `{d.test_node}` 가 그래프에 없습니다")
            continue
        if not d.module_path.exists():
            problems.append(f"{tag}: 모듈 travel_graph/detours/{d.kind}.py 가 없습니다")
        else:
            for missing in _module_shape(d.module_path):
                problems.append(f"{tag}: 모듈 — {missing}")
        if not d.test_path.exists():
            problems.append(f"{tag}: 시험지 scripts/detour_tests/test_{d.kind}.py 가 없습니다")
        elif _test_shape(d.test_path):
            for missing in _test_shape(d.test_path):
                problems.append(f"{tag}: {missing}")
        # (g) 뒷부분 — 시험지가 travel_graph 를 import 하지 않는가 (시험지 모양 검사와 같은 elif 사슬이라 여기 둔다)
        elif _imports_travel_graph(d.test_path):
            problems.append(f"{tag}: 시험지가 travel_graph 를 import 합니다 — 고치는 코드가 "
                            f"채점표를 만들면 판정 독립이 무너집니다")
        # (d) 진단에서만 갈라진다
        diag_ends = [ends for name, ends in by_source.get(d.diagnose, [])]
        if not any(ends.get(d.kind) == d.fix_node for ends in diag_ends):
            problems.append(f"{tag}: `{d.diagnose}` 의 매핑에 '{d.kind}' → `{d.fix_node}` 가 없습니다")
        feeders = {s for s, t, _c in edges if t == d.fix_node}
        if not feeders <= {d.diagnose, d.test_node}:
            problems.append(f"{tag}: `{d.fix_node}` 로 들어오는 곳은 `{d.diagnose}` 와 "
                            f"`{d.test_node}`(재시도) 뿐이어야 합니다 (지금: {sorted(feeders)})")
        # (e) fix → test 는 정적 간선 하나, test 뒤는 back · retry · gate 세 갈래
        if static.get(d.fix_node) != {d.test_node} or d.fix_node in by_source:
            problems.append(f"{tag}: `{d.fix_node}` 뒤에는 `{d.test_node}` 로 가는 정적 간선 하나만 "
                            f"있어야 합니다")
        want = {"back": d.home, "retry": d.fix_node, "gate": d.gate}
        got = [ends for name, ends in by_source.get(d.test_node, [])]
        if got != [want]:
            problems.append(f"{tag}: `{d.test_node}` 뒤 매핑이 {want} 여야 합니다 "
                            f"(지금: {got}). 합격하면 **그 루프의 검사기**로 돌아와야 "
                            f"같은 검사기로 다시 잽니다")
        # (f) 처방 가지 노드는 루프 골격의 칸(판정 · 바퀴 · 게이트)을 쓰지 않는다
        for node in (d.fix_node, d.test_node):
            owned = sorted(writes.get(node_fn.get(node, ("", "")), set()) & set(SPINE_OWNED))
            if owned:
                problems.append(f"{tag}: `{node}` 가 루프 골격의 칸 {owned} 에 씁니다 — 처방 가지는 "
                                f"데이터와 처방 가지 칸만 씁니다 (판정은 검사기 노드의 몫)")
        # (g) 앞부분 — 시험 뒤 라우터가 detour_limit 을 읽는가 — 7번은 'PASS' 글자만 있어도 상한으로 쳐서 여기서 따로 본다
        for name, _ends in by_source.get(d.test_node, []):
            if not _router_reads(name, "detour_limit"):
                problems.append(f"{tag}: `{d.test_node}` 뒤 라우터 `{name}` 가 `detour_limit` 을 "
                                f"읽지 않습니다 — 불합격이 계속되면 fix ↔ test 를 끝없이 돕니다")
    return problems


# --------------------------------------------------------------------------
# 검사행 12개 (1~11 + 6b)
# --------------------------------------------------------------------------


def run(root=None):
    """루프 킷 검사기와 같은 서명. `root` 는 다른 폴더를 검사할 때만 쓴다."""
    if root and Path(root).resolve() != ROOT:
        globals()["PKG"] = Path(root).resolve() / "travel_graph"
    result = Result("그래프 구조 판정 — 그래프에만 있는 실패 (검사행 12개)")
    try:
        builder, edges, branches, state_cls = load_graph()
    except Exception as exc:  # noqa: BLE001
        result.note_broken(f"그래프를 불러오지 못했습니다: {type(exc).__name__}: {exc}")
        return result

    nodes = [n for n in builder.nodes]
    node_fn = node_to_function(builder)
    writes = written_keys(src for src, _fn in node_fn.values())
    routers = router_sources()
    reducers = reducer_fields(state_cls)
    fields = all_fields(state_cls)

    # 1) 도달 불가 노드 --------------------------------------------------
    reachable, stack = {START}, [START]
    while stack:
        for nxt in successors(edges, stack.pop()):
            if nxt not in reachable:
                reachable.add(nxt)
                stack.append(nxt)
    orphans = [n for n in nodes if n not in reachable]
    result.row("1 도달 불가 노드", 0, len(orphans), not orphans)
    for name in orphans:
        result.note_broken(f"START 에서 갈 수 없는 노드입니다: {name}")

    # 2) 종료 없는 순환 --------------------------------------------------
    can_end, changed = {END}, True
    while changed:
        changed = False
        for source, target, _ in edges:
            if target in can_end and source not in can_end:
                can_end.add(source)
                changed = True
    dead = [n for n in nodes if n in reachable and n not in can_end]
    result.row("2 END 에 못 가는 노드", 0, len(dead), not dead)
    for name in dead:
        result.note_broken(f"END 로 가는 경로가 없습니다 (무한 루프): {name}")

    # 3) reducer 없는 병렬 쓰기 ------------------------------------------
    def keys_of(node_name: str) -> set:
        return {k for k in writes.get(node_fn.get(node_name, ("", "")), set()) if k in fields}

    #: (노드, 키, 왜 겹치는가). **겹치는 키만** 잡는다 — 병렬이어도 서로 다른
    #: 필드에 쓰면 reducer 가 필요 없다.
    clashes = []

    # (a) fan-out : 같은 노드가 N번 돌면서 같은 키에 쓴다 → 전부 겹친다
    fan_targets = set()
    for router_name, _source, ends in branches:
        source_text = routers.get(router_name, ("", set()))[0]
        if "Send(" in source_text or router_name.startswith("fan_"):
            fan_targets.update(ends.values())
    for target in sorted(fan_targets):
        for key in sorted(keys_of(target)):
            clashes.append((target, key, "fan-out(Send) — 도시 수만큼 동시에 쓴다"))

    # (b) 정적 분기 : 형제 노드 둘 이상이 **같은 키**에 쓸 때만
    static_from = {}
    for source, target, conditional in edges:
        if not conditional:
            static_from.setdefault(source, []).append(target)
    for source, targets in sorted(static_from.items()):
        if len(targets) < 2:
            continue
        for key in sorted(set().union(*(keys_of(t) for t in targets))):
            writers = [t for t in targets if key in keys_of(t)]
            if len(writers) >= 2:
                for target in writers:
                    clashes.append((target, key, f"정적 분기({source}) — {len(writers)}개가 같은 키에 쓴다"))

    counters = counter_fields(state_cls)
    unguarded = [(n, k, why) for n, k, why in clashes if k not in reducers]
    result.row("3 reducer 없는 병렬 쓰기", 0, len(unguarded), not unguarded)
    for target, key, why in unguarded:
        if key in counters:
            #  ↳ 여기서 "reducer 를 붙이라"고 안내하면 8번 검사가 잡는 실수로 곧장
            #    몰고 간다. 카운터가 겹쳤다는 것은 **병렬 배치 자체가 틀렸다**는 뜻이다.
            result.note_broken(
                f"`{target}` 가 병렬로 돌면서 **회차 카운터** `{key}` 에 씁니다 ({why}). "
                f"여기에 reducer 를 붙이면 안 됩니다 — 카운터는 덮어쓰기입니다. "
                f"이 노드들을 정적 간선으로 늘어놓지 말고 **순환 하나로** 바꾸십시오 "
                f"(회차는 서로의 결과 위에 쌓이므로 순차여야 합니다)")
        else:
            result.note_broken(
                f"`{target}` 가 병렬로 돌면서 `{key}` 에 씁니다 ({why}). "
                f"state.py 에서 `Annotated[..., reducer]` 를 붙이십시오")

    # 4) 라우터 반환값이 매핑에 없음 --------------------------------------
    mismatched = []
    for router_name, source, ends in branches:
        body, returns = routers.get(router_name, ("", set()))
        if not returns:
            continue
        for value in sorted(returns - set(ends)):
            mismatched.append((f"{router_name}@{source}", value, sorted(ends)))
    result.row("4 라우터 반환값 불일치", 0, len(mismatched), not mismatched)
    for router_name, value, allowed in mismatched:
        result.note_broken(
            f"`{router_name}` 이 '{value}' 를 돌려주는데 매핑에 없습니다 "
            f"(허용: {allowed}). 런타임에 KeyError 가 납니다")

    # 5) 자유 문장으로 라우팅 ---------------------------------------------
    text_routers = []
    used_routers = {name for name, _s, _e in branches}
    for router_name, (body, _) in routers.items():
        if router_name not in used_routers:
            continue
        for field in FREE_TEXT_FIELDS:
            if field in body:
                text_routers.append((router_name, field))
    result.row("5 자유 문장 라우팅", 0, len(text_routers), not text_routers)
    for router_name, field in text_routers:
        result.note_broken(
            f"`{router_name}` 이 자유 문장 `{field}` 를 보고 경로를 고릅니다. "
            f"제어 흐름이 문장 해석에 좌우됩니다 — 허용값이 정해진 필드를 보십시오")

    # 6) 아무도 안 읽는 상태 필드 (SHORT) ---------------------------------
    reads = read_keys()
    written = set()
    for keys in writes.values():
        written |= keys
    dead_fields = sorted(
        f for f in fields
        if f not in reads and f in written and f not in HUMAN_READ_FIELDS)
    result.row("6 아무도 안 읽는 상태 필드", 0, len(dead_fields), not dead_fields)
    for field in dead_fields:
        result.note_short(f"`{field}` 는 쓰기만 하고 아무도 읽지 않습니다 (상태만 무거워집니다)")

    #  ↳ 이 검사기의 사각지대를 스스로 드러낸다. 노드가 `return {...}` 대신
    #    `update = {...}; return update` 로 쓰면 위의 3·6번이 그 노드를 통째로
    #    못 본다 — **조용히 통과**한다.
    #
    #    예전에는 이것을 SHORT 로 알렸다. 그런데 SHORT 는 "아직 덜 됐다,
    #    더 돌면 된다"는 뜻이다. **"검사기가 이 노드를 못 봤다"는 더 돌아도
    #    해결되지 않는다.** 두 상태가 같은 종료 코드를 쓰면 구분이 사라지므로
    #    ERROR 로 올린다.
    opaque = sorted({(fn or f"{node} (함수를 꺼낼 수 없음)")
                     for node, (src, fn) in node_fn.items() if (src, fn) not in writes})
    result.row("6b 검사기가 못 보는 노드", 0, len(opaque), not opaque)
    for fn_name in opaque:
        result.note_broken(
            f"`{fn_name}` 의 반환이 dict 리터럴이 아니어서 어떤 상태 키에 쓰는지 "
            f"이 검사기가 볼 수 없습니다 (3·6번 검사가 이 노드를 건너뜁니다). "
            f"노드는 `return {{...}}` 로 변경분을 돌려주십시오")

    # 7) 상한 검사 없는 순환 ----------------------------------------------
    cycles = find_cycles(edges, [n for n in nodes if n in reachable])
    unbounded = []
    for cycle in cycles:
        routers_on = sorted({
            name for name, source, ends in branches
            if source in cycle and any(t in cycle for t in ends.values())
        })
        if not routers_on:
            unbounded.append((cycle, "라우터가 없습니다"))
            continue
        #  ★ edges.py 에 없는 라우터는 소스를 못 읽는다 → **상한 없음으로 본다.**
        #    못 본 것을 통과로 치면 검사기가 조용히 약해진다.
        if not any(any(t in routers.get(name, ("", set()))[0] for t in TERMINATORS)
                   for name in routers_on):
            unbounded.append((cycle, " · ".join(routers_on)))
    result.row("7 상한 검사 없는 순환", 0, len(unbounded), not unbounded)
    for cycle, why in unbounded:
        result.note_broken(
            f"순환 [{' → '.join(cycle)}] 에 종료 조건이 없습니다 ({why}). "
            f"상한({', '.join(TERMINATORS[:4])}) 중 하나를 라우터가 읽어야 합니다")

    # 8) 회차 카운터에 reducer 가 붙었다 -----------------------------------
    reduced = sorted(name for name, annotated in counters.items() if annotated)
    result.row("8 회차 카운터에 reducer", 0, len(reduced), not reduced)
    for name in reduced:
        result.note_broken(
            f"회차 카운터 `{name}` 에 reducer 가 붙어 있습니다. 카운터는 누적이 아니라 "
            f"덮어쓰기여야 합니다 — 2회차에서 값이 1+2=3 이 되어 한 회차를 건너뛰고 나갑니다 (정성 2회만 돕니다). "
            f"state.py 에서 `Annotated[...]` 를 벗기고 `{name}: int` 로 두십시오")

    # 9) 고정 예산 순환이 카운터를 안 본다 ----------------------------------
    #    통과선 루프(verdict 로 닫는다)와 고정 예산 루프(회차로 닫는다)는 모양이 다르다.
    #    회차로 닫는 순환인데 라우터가 verdict 만 보면, 3회를 채워도 빠져나오지 못한다.
    budget_bad = []
    for cycle in cycles:
        in_cycle = [c for c in counters if c in cycle]      # 노드 이름 = 카운터 이름
        if not in_cycle:
            continue                                        # 고정 예산 순환이 아니다
        routers_on = sorted({
            name for name, source, ends in branches
            if source in cycle and any(t in cycle for t in ends.values())
        })
        body = "\n".join(routers[name][0] for name in routers_on if name in routers)
        for counter in in_cycle:
            paired = False
            for suffix, limit_suffix in COUNTER_PAIRS:
                if not counter.endswith(suffix):
                    continue
                limit = counter[: -len(suffix)] + limit_suffix
                if counter in body and limit in body:
                    paired = True
            if not paired:
                budget_bad.append((cycle, counter, routers_on))
    result.row("9 고정 예산 순환이 카운터를 안 봄", 0, len(budget_bad), not budget_bad)
    for cycle, counter, routers_on in budget_bad:
        result.note_broken(
            f"순환 [{' → '.join(cycle)}] 은 회차로 닫는 고정 예산 루프인데, "
            f"라우터({' · '.join(routers_on) or '없음'})가 `{counter}` 와 그 상한을 "
            f"함께 읽지 않습니다. verdict 만 보면 3회를 채워도 빠져나오지 못합니다")

    # 10) 선언한 허용값과 실제 배선이 어긋난다 ------------------------------
    #     `edges.ALLOWED` 는 "라우터가 돌려줄 수 있는 값"을 사람이 읽으라고 적어 둔
    #     표다. 그런데 아무도 그것을 배선과 맞춰 보지 않으면 표만 낡는다.
    #     실제로 명세(specs/03_EDGE_CONDITION.md)의 라우터 표에서 `quality` 분기가
    #     빠진 채로 오래 있었다. 표를 그대로 따라 고치면 런타임 KeyError 가 난다.
    #     4번 검사는 '코드가 돌려주는 값'을 보지만, 이 검사는 '선언한 표'를 본다.
    declared = {}
    try:
        from travel_graph import edges as _edges_module
        declared = dict(getattr(_edges_module, "ALLOWED", {}) or {})
    except Exception:  # noqa: BLE001
        declared = {}
    drift = []
    for router_name, source, ends in branches:
        if router_name not in declared:
            #  ★ 표에 없는 라우터를 건너뛰면 새 라우터는 영영 대조되지 않는다.
            #    fan-out(`fan_*`)만 예외다 — `Send` 목록만 돌려주므로 허용값 표가 없다.
            if not router_name.startswith("fan_"):
                drift.append((f"{router_name}@{source}", ["(표에 없음)"], sorted(ends)))
            continue
        want = set(declared[router_name])
        have = set(ends)
        if want != have:
            drift.append((f"{router_name}@{source}", sorted(want - have), sorted(have - want)))
    result.row("10 선언 ALLOWED 와 배선 불일치", 0, len(drift), not drift)
    for router_name, only_declared, only_wired in drift:
        result.note_broken(
            f"`{router_name}`: edges.ALLOWED 와 build.py 매핑이 다릅니다 "
            f"(표에만 있음 {only_declared or '없음'} · 배선에만 있음 {only_wired or '없음'}). "
            f"둘 중 하나가 낡았습니다 — 명세의 라우터 표도 함께 보십시오")

    # 11) 처방 가지 계약 ----------------------------------------------------
    #     노드를 늘릴 수 있는 곳은 **문제가 난 지점(진단 노드)뿐**이다. 그 약속을 모양으로
    #     잠근다. 이 모양이 깨져도 1~10번은 대부분 통과한다 — 그래서 따로 본다.
    detour_problems = detour_contract(builder, edges, branches, node_fn, writes)
    result.row("11 처방 가지 계약", 0, len(detour_problems), not detour_problems)
    for problem in detour_problems:
        result.note_broken(problem)

    # 안내 (판정에 영향 없음) ---------------------------------------------
    for source, targets in sorted(static_from.items()):
        if len(targets) >= 2:
            result.row(f"안내 정적 간선 {len(targets)}개 [{source}]", "의도한 병렬",
                       " + ".join(targets), True)
    return result


def main():
    parser = argparse.ArgumentParser(description="그래프 구조 검사")
    parser.add_argument("--root", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run(args.root)
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print_result(result)
        if result.verdict == "ERROR":
            print(" 다음 행동: 구조를 고칩니다. 루프를 더 돌려도 해결되지 않습니다.")
            print("           STEP 3(간선) · STEP 4(병렬) 의 `읽기 6` 을 다시 보십시오.")
            print("           8·9번이 걸렸다면 루프 C(정성) 쪽입니다 — 카운터는 덮어쓰기,")
            print("           순환은 `quality_pass` 와 `quality_passes_required` 를 함께 봅니다.")
            print("           11번이 걸렸다면 처방 가지 쪽입니다 — specs/06_DETOUR.md 의 `읽기 3` 과")
            print("           `python scripts/new_detour.py` 가 만드는 모양을 비교하십시오.")
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
