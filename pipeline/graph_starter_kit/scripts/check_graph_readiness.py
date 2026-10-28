#!/usr/bin/env python3
"""시작해도 되는지 본다. **킷 소유 — 수정 금지.**

킷을 받자마자, 그리고 STEP 을 하나 끝낼 때마다 이것을 돌린다.
**처음 실행하면 `NOT_READY`(exit 2) 가 나온다. 오류가 아니다** — 아직 STEP 을
하나도 안 했기 때문이다. 루프 킷의 `check_loop_readiness.py` 와 같은 역할이다.

종료 코드
  0  READY      다 갖췄다. `langgraph dev` 를 켜도 된다
  1  ERROR      환경이나 인계본이 깨졌다 — 사람이 고쳐야 한다
  2  NOT_READY  아직 STEP 이 남았다 (정상적인 진행 중 상태)

사용법
  python scripts/check_graph_readiness.py
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _contract import use_utf8_output  # noqa: E402

use_utf8_output()

ROOT = Path(__file__).resolve().parent.parent
LINE = "=" * 66

HANDOFF_FILES = [
    "00_START_HERE.md", "01_HANDOFF.md", "02_USER_REQUEST.md",
    "03_CONTRACT.json", "04_RUN_EVIDENCE.md", "05_STATE_SEED.json",
    "research_data.json",
]

STEP_FILES = {
    1: "specs/01_STATE_SCHEMA.md",
    2: "specs/02_NODE_BOUNDARY.md",
    3: "specs/03_EDGE_CONDITION.md",
    4: "specs/04_PARALLEL.md",
    5: "specs/05_CHECKPOINT.md",
}

#: 루프 C(정성 완성도)가 함께 왔는지. 이 셋은 루프 킷에서 **그대로 복사**한 것이며
#: 교육생이 정하는 값이 하나도 없다. 하나라도 없으면 개정 전 킷이라는 뜻이다.
LOOP_C_FILES = [
    "scripts/check_quality_passes.py",
    "specs/QUALITY_RUBRIC.md",
    "templates/QUALITY_PASS.md",
]

# --------------------------------------------------------------------------
# STEP 이 실제로 코드에 반영됐는가
#
# 예전에는 소스에 그 문자열이 들어 있는지만 봤다. 그래서
#     # loop_a_limit
#     # Annotated[list[dict], merge_cities]
#     # interrupt(
# 주석 세 줄이면 STEP 3·4·5 가 전부 "반영됨" 이었다. 문서만 APPROVED 로 바꿔 두고
# 코드를 안 고치는 사고를 막으려고 만든 검사가, 주석 한 줄로 넘어간 것이다.
#
# 지금은 AST 로 본다. **주석은 AST 에 남지 않으므로 저절로 걸러진다.**
# --------------------------------------------------------------------------


def source_tree(rel: str):
    """그 파일을 구문 트리로 읽는다. 없거나 깨졌으면 None."""
    path = ROOT / rel
    if not path.exists():
        return None
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return None


def router_reads_limit(tree) -> bool:
    """STEP 3 — 라우터가 상한 필드를 코드로 읽는가."""
    if tree is None:
        return False
    limits = ("loop_a_limit", "loop_b_limit", "same_error_limit")
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or not fn.name.startswith("route_"):
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Constant) and node.value in limits:
                return True
    return False


def cities_has_reducer(tree) -> bool:
    """STEP 4 — cities 필드에 Annotated 가 붙었는가."""
    if tree is None:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.AnnAssign) or not isinstance(node.target, ast.Name):
            continue
        if node.target.id != "cities":
            continue
        ann = node.annotation
        if isinstance(ann, ast.Subscript) and isinstance(ann.value, ast.Name) \
                and ann.value.id == "Annotated":
            return True
    return False


def gate_calls_interrupt(tree) -> bool:
    """STEP 5 — 게이트 노드가 interrupt() 를 실제로 부르는가."""
    if tree is None:
        return False
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or not fn.name.startswith("human_gate"):
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id == "interrupt":
                return True
    return False


def state_fields(tree) -> set:
    """TravelState 가 선언한 필드 이름."""
    if tree is None:
        return set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "TravelState":
            return {
                item.target.id for item in node.body
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
            }
    return set()


CODE_MARKS = {
    3: ("travel_graph/edges.py", router_reads_limit, "라우터가 상한을 읽는다"),
    4: ("travel_graph/state.py", cities_has_reducer, "cities 에 reducer 가 붙었다"),
    5: ("travel_graph/nodes.py", gate_calls_interrupt, "게이트가 사람에게 묻는다"),
}

#: STEP 1 명세가 "이 필드들은 있어야 한다"고 못 박아 둔 묶음.
#: 진행 표시가 아니라 **회귀 방지**다 — 필드를 지우면 노드가 조용히 빈 값을 읽는다.
#: `diagnose_fields` 는 진단 · 처방 가지 칸 (킷 고정). 지우면 라우터가 원인을 못 읽는다.
STATE_FIELD_GROUPS = ("input_schema", "verdict_fields", "control_fields",
                      "path_only_fields", "reducer_pending", "diagnose_fields")


def status_of(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    match = re.search(r"<!--\s*STATUS:BEGIN\s*-->(.*?)<!--\s*STATUS:END\s*-->",
                      path.read_text(encoding="utf-8"), re.DOTALL)
    if not match:
        return "NO_STATUS"
    found = re.search(r"STATUS:\s*(\w+)", match.group(1))
    return found.group(1) if found else "NO_STATUS"


def main():
    parser = argparse.ArgumentParser(description="그래프 실습 준비도 점검")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    rows = []
    blocking = []
    pending = []

    # 1) 인계본
    missing = [f for f in HANDOFF_FILES if not (ROOT / "graph" / f).exists()]
    rows.append(("인계본 graph/ 7개", "있음" if not missing else f"{len(missing)}개 없음", not missing))
    if missing:
        blocking.append("graph/ 에 " + ", ".join(missing) + " 이(가) 없습니다. "
                        "루프 킷의 output/graph/ 를 통째로 복사하십시오")

    # 2) 계약이 온전한가 (quality_contract 포함 — 없으면 개정 전 인계본이다)
    try:
        from _contract import load_spec
        spec = load_spec(str(ROOT))
        passes = (spec.get("quality_contract") or {}).get("passes")
        rows.append(("검사 계약 03_CONTRACT.json", f"온전 · 정성 {passes}회", True))
    except Exception as exc:  # noqa: BLE001
        rows.append(("검사 계약 03_CONTRACT.json", "깨짐", False))
        blocking.append(str(exc))

    # 2a) 계약과 자료가 **같은 루프**에서 왔는가
    #     루프 A 를 못 돌려 research_data.json 없이 6개만 덮어쓰면, 계약(내 나라 · 일수)과
    #     replay 자료(예시 베트남)가 섞인다. 그래프는 돌지만 페이지와 판정이 엉뚱해진다.
    try:
        contract_json = json.loads((ROOT / "graph" / "03_CONTRACT.json").read_text(encoding="utf-8"))
        research_json = json.loads((ROOT / "graph" / "research_data.json").read_text(encoding="utf-8"))
        want = (contract_json.get("request") or {})
        #  루프 킷 명세는 국가 · 일수를 `request` 안에 적는다(`research_data.request`).
        #  최상위 `country` · `days` 가 없으면 거기서 읽는다 (travel_graph/contract.py baseline() 과 같은 규칙).
        got = research_json.get("request") if isinstance(research_json.get("request"), dict) else {}
        pair = [(want.get("country"), research_json.get("country") or got.get("country")),
                (want.get("days"), research_json.get("days") or got.get("days"))]
        same = all(a == b for a, b in pair)
    except Exception:  # noqa: BLE001 — 파일이 없거나 깨진 것은 위 두 행이 이미 잡는다
        same, pair = True, []
    if pair:
        rows.append(("인계본 짝 — 계약 = 자료", "같은 루프" if same else "섞임", same))
    if not same:
        blocking.append(
            "03_CONTRACT.json({} {}일)과 research_data.json({} {}일)이 다른 루프에서 왔습니다. "
            "내 인계본에 research_data.json 이 없었다면 킷의 예시 인계본(graph/ 7개)으로 진행하십시오 "
            "— 이미 덮어썼다면 받은 킷 zip 에서 graph/ 를 다시 꺼냅니다".format(pair[0][0], pair[1][0], pair[0][1], pair[1][1]))

    # 2b) 루프 C 파일이 함께 왔는가
    missing_c = [f for f in LOOP_C_FILES if not (ROOT / f).exists()]
    rows.append(("루프 C 파일 3개", "있음" if not missing_c else f"{len(missing_c)}개 없음",
                 not missing_c))
    if missing_c:
        blocking.append(
            "루프 C(정성 완성도) 파일이 없습니다: " + ", ".join(missing_c)
            + ". 루프 킷에서 그대로 복사하십시오 (수정 금지)")

    # 2c) 검사기가 무결한가 — 빈칸을 세기 전에 채점표부터 본다
    #     검사기가 약해진 것은 검사기가 알려 주지 않는다. 1초면 끝난다.
    selftest = ROOT / "scripts" / "selftest" / "run_selftest.py"
    if not selftest.exists():
        rows.append(("검사기 셀프테스트", "파일 없음", False))
        blocking.append("scripts/selftest/run_selftest.py 가 없습니다 (루프 킷에서 복사)")
    else:
        try:
            proc = subprocess.run(
                [sys.executable, str(selftest)], cwd=str(ROOT), shell=False,
                capture_output=True, timeout=180)
            ok = proc.returncode == 0
        except Exception as exc:  # noqa: BLE001
            ok, proc = False, None
            blocking.append("셀프테스트를 돌리지 못했습니다: " + str(exc)[:80])
        rows.append(("검사기 셀프테스트", "모든 검사행 살아 있음" if ok else "죽은 행 있음", ok))
        if proc is not None and not ok:
            blocking.append(
                "검사기에 죽은 검사행이 있습니다. `python scripts/selftest/run_selftest.py` 를"
                " 직접 돌려 보십시오 — 결과물이 아니라 검사기를 고쳐야 합니다")

    # 3) 환경
    py_ok = sys.version_info[:2] == (3, 12)
    rows.append(("Python 3.12", ".".join(map(str, sys.version_info[:3])), py_ok))
    if not py_ok:
        blocking.append("Python 3.12 가 아닙니다. settings/SETUP.md STEP 1~2 를 보십시오")

    try:
        import langgraph  # noqa: F401
        rows.append(("langgraph 임포트", "OK", True))
    except Exception:  # noqa: BLE001
        rows.append(("langgraph 임포트", "실패", False))
        blocking.append("langgraph 가 없습니다. settings/SETUP.md STEP 4 를 보십시오")

    env_ok = (ROOT / ".env").exists()
    rows.append((".env 연결", "있음" if env_ok else "없음", env_ok))
    if not env_ok:
        blocking.append(".env 가 없습니다. settings/SETUP.md STEP 5 를 보십시오")
    tracing = (os.environ.get("LANGSMITH_TRACING") or "").lower() in ("1", "true", "yes", "on")
    rows.append(("LANGSMITH_TRACING (셸)", "true" if tracing else "미설정(그래프는 .env 로 읽음)", True))

    # 4) STEP 진행 상태
    todo_steps = []   # 아직 끝나지 않은 STEP 번호 — '다음 명령' 은 그중 가장 앞 번호를 찍는다
    for number, rel in STEP_FILES.items():
        state = status_of(ROOT / rel)
        ok = state == "APPROVED"
        rows.append((f"STEP {number} {Path(rel).stem}", state, ok))
        if not ok:
            pending.append(f"STEP {number} 가 아직 {state} 입니다")
            todo_steps.append(number)

    # 5) 코드에 실제로 반영됐는가 (주석이 아니라 구문 트리로 본다)
    for number, (rel, probe, what) in CODE_MARKS.items():
        found = probe(source_tree(rel))
        rows.append((f"STEP {number} 코드 반영 — {what}", "반영됨" if found else "아직", found))
        if not found:
            pending.append(f"STEP {number} 의 코드 변경이 {rel} 에 아직 없습니다")
            todo_steps.append(number)   # 문서는 APPROVED 인데 코드 반영만 빠진 경우

    # 5b) 명세가 요구한 상태 필드가 지워지지 않았는가 (회귀 방지)
    try:
        from _contract import load_machine_json
        fixed = (load_machine_json(ROOT / STEP_FILES[1]).get("fixed") or {})
    except Exception:  # noqa: BLE001
        fixed = {}
    needed = []
    for group in STATE_FIELD_GROUPS:
        needed.extend(fixed.get(group) or [])
    if needed:
        have = state_fields(source_tree("travel_graph/state.py"))
        gone = [name for name in needed if name not in have]
        rows.append(("state.py 필드 — 명세가 요구한 것",
                     f"{len(needed) - len(gone)}/{len(needed)}", not gone))
        if gone:
            blocking.append(
                "travel_graph/state.py 에 명세가 요구한 필드가 없습니다: "
                + ", ".join(gone[:6])
                + " — 노드가 그 칸을 조용히 빈 값으로 읽게 됩니다")

    verdict = "ERROR" if blocking else ("NOT_READY" if pending else "READY")
    code = {"READY": 0, "ERROR": 1, "NOT_READY": 2}[verdict]

    if args.json:
        print(json.dumps({
            "verdict": verdict,
            "rows": [{"name": n, "value": v, "ok": o} for n, v, o in rows],
            "blocking": blocking, "pending": pending,
        }, ensure_ascii=False, indent=2))
        return code

    print(LINE)
    print(" 그래프 실습 준비도")
    print(LINE)
    for name, value, ok in rows:
        print("  [{}] {:<38}{}".format("OK" if ok else "  ", name[:38], value))
    print("")
    if blocking:
        print(" [ERROR] 먼저 고쳐야 합니다.")
        for item in blocking:
            print("   - " + item)
    elif pending:
        print(f" [NOT_READY] 남은 일 {len(pending)}가지 — **오류가 아닙니다.**")
        for item in pending[:8]:
            print("   - " + item)
        print("")
        print(f" 다음 명령:  STEP {min(todo_steps, default=1)} 진행해줘")
    else:
        print(" [READY] 다 갖췄습니다.")
        print("")
        print(" 다음 명령:  langgraph dev --no-reload --port 2024")
    print(LINE)
    return code


if __name__ == "__main__":
    sys.exit(main())
