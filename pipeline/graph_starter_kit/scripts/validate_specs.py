#!/usr/bin/env python3
"""STEP 명세가 제대로 채워졌는지 본다. **킷 소유 — 수정 금지.**

각 STEP 문서는 8구역 형식을 지킨다. 이 스크립트는 **형식과 빈칸만** 본다.
STEP 1~5 는 결정 13개(3·3·2·2·3)를, STEP 6(처방 가지 추가)은 결정 대신 처방 가지 기록을 본다.
"좋은 결정인가"는 보지 않는다 — 그건 사람의 몫이다.

종료 코드
  0  PASS   형식이 맞고 빈칸이 없다
  1  ERROR  블록이 없거나 JSON 이 깨졌다
  2  SHORT  아직 답하지 않은 결정이 있다 (정상적인 진행 중 상태)

사용법
  python scripts/validate_specs.py
  python scripts/validate_specs.py --step 3
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _contract import ContractError, find_nulls, load_machine_json, use_utf8_output  # noqa: E402

use_utf8_output()

ROOT = Path(__file__).resolve().parent.parent
LINE = "=" * 66

STEPS = {
    1: ("01_STATE_SCHEMA.md", "상태 스키마", 3),
    2: ("02_NODE_BOUNDARY.md", "노드 경계", 3),
    3: ("03_EDGE_CONDITION.md", "간선 조건", 2),
    4: ("04_PARALLEL.md", "병렬", 2),
    5: ("05_CHECKPOINT.md", "체크포인트와 사람 개입", 3),
    #  STEP 6 은 **결정이 없다** (결정은 13개로 고정). 로그에 후보가 있을 때만 한다 — 하면
    #  "되풀이된 실패 하나"를 처방 가지로
    #  만든 기록(`detour`)을 채운다. 실행 **뒤**의 확장 트랙이라 준비도 검사는 보지 않는다.
    6: ("06_DETOUR.md", "처방 가지 추가 (조건부 · 실행 뒤)", 0),
}

#: 결정 말고 **빈칸이 없어야 하는 블록**. STEP 6 은 처방 가지 기록을 채워야 끝난다.
EXTRA_REQUIRED = {6: ("detour",)}

REQUIRED_BLOCKS = ("FIXED", "ANSWERS", "MACHINE", "STATUS")


def detour_record_gaps(detour: dict) -> list:
    """STEP 6 기록이 **말이 되는가**. 빈칸이 아니라는 것만으로는 부족하다 —
    등록되지 않은 이름 · 빈 문자열 · 빨간불 없이 적은 초록불은 기록이 아니다."""
    gaps = []
    try:
        sys.path.insert(0, str(ROOT))
        from travel_graph.detours.registry import DETOURS
        kinds = {row.get("kind") for row in DETOURS}
    except Exception:  # noqa: BLE001
        kinds = set()
    kind = detour.get("kind")
    if kind is not None and kinds and kind not in kinds:
        gaps.append(f"`detour.kind` '{kind}' 가 registry.py 에 없습니다 (new_detour.py 로 만들었나요?)")
    if detour.get("loop") is not None and detour.get("loop") not in ("A", "B"):
        gaps.append("`detour.loop` 는 'A' 또는 'B' 입니다")
    for key, value in detour.items():
        if isinstance(value, str) and not value.strip():
            gaps.append(f"`detour.{key}` 가 빈 문자열입니다")
    red, green = str(detour.get("red_seen") or ""), str(detour.get("green_seen") or "")
    if detour.get("red_seen") is not None and "FAIL" not in red:
        gaps.append("`detour.red_seen` 에 빨간불 줄(`test_…: FAIL …`)을 그대로 옮겨 적으십시오")
    if detour.get("green_seen") is not None and "PASS" not in green:
        gaps.append("`detour.green_seen` 에 초록불 줄(`test_…: PASS … (검사기로 복귀)`)을 옮겨 적으십시오")
    return gaps


def check_step(number: int):
    filename, title, want = STEPS[number]
    path = ROOT / "specs" / filename
    problems, pending = [], []

    if not path.exists():
        return f"STEP {number} {title}", "ERROR", [f"{filename} 이 없습니다"], []

    text = path.read_text(encoding="utf-8")
    for block in REQUIRED_BLOCKS:
        if f"<!-- {block}:BEGIN -->" not in text:
            problems.append(f"{block} 블록이 없습니다 (문서 형식이 깨졌습니다)")

    try:
        machine = load_machine_json(path)
    except ContractError as exc:
        return f"STEP {number} {title}", "ERROR", problems + [str(exc)], []

    decisions = machine.get("decisions") or {}
    if len(decisions) != want:
        problems.append(f"결정이 {want}개여야 하는데 {len(decisions)}개입니다")
    for key in find_nulls(decisions):
        pending.append(f"`{key}` 가 아직 (미정) 입니다")
    for extra in EXTRA_REQUIRED.get(number, ()):
        if not isinstance(machine.get(extra), dict):
            problems.append(f"MACHINE 에 `{extra}` 블록이 없습니다")
            continue
        for key in find_nulls(machine[extra]):
            pending.append(f"`{extra}.{key}` 가 아직 비어 있습니다")
    if number == 6 and isinstance(machine.get("detour"), dict):
        pending.extend(detour_record_gaps(machine["detour"]))

    status = "NO_STATUS"
    block = re.search(r"<!--\s*STATUS:BEGIN\s*-->(.*?)<!--\s*STATUS:END\s*-->",
                      text, re.DOTALL)
    if block:
        found = re.search(r"STATUS:\s*(\w+)", block.group(1))
        if found:
            status = found.group(1)
    if status not in ("DRAFT", "APPROVED", "NEEDS_REVIEW"):
        problems.append(f"STATUS 값이 이상합니다: {status}")
    elif status != "APPROVED" and not pending:
        pending.append("결정은 다 찼는데 STATUS 가 아직 APPROVED 가 아닙니다")

    verdict = "ERROR" if problems else ("SHORT" if pending else "PASS")
    return f"STEP {number} {title}  [{status}]", verdict, problems, pending


def main():
    parser = argparse.ArgumentParser(description="STEP 명세 검사")
    parser.add_argument("--step", type=int, default=None, choices=sorted(STEPS))
    args = parser.parse_args()

    targets = [args.step] if args.step else sorted(STEPS)
    worst = "PASS"

    print(LINE)
    print(" STEP 명세 검사")
    print(LINE)
    for number in targets:
        label, verdict, problems, pending = check_step(number)
        mark = {"PASS": "OK", "SHORT": "덜참", "ERROR": "깨짐"}[verdict]
        print(f"  [{mark:<4}] {label}")
        for item in problems:
            print("          x " + item)
        for item in pending[:4]:
            print("          - " + item)
        if verdict == "ERROR":
            worst = "ERROR"
        elif verdict == "SHORT" and worst != "ERROR":
            worst = "SHORT"

    print("")
    print(" 판정: " + worst)
    if worst == "SHORT":
        print(" (아직 덜 채운 것이 있습니다. 오류가 아닙니다.)")
    print(LINE)
    return {"PASS": 0, "ERROR": 1, "SHORT": 2}[worst]


if __name__ == "__main__":
    sys.exit(main())
