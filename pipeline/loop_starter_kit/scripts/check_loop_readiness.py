#!/usr/bin/env python3
"""루프를 시작해도 되는지 검사한다.

두 가지를 확실히 구분한다.

  NOT_READY : 아직 교육생이 답하지 않은 것이 있다.  -> 정상. 오류가 아니다.
  ERROR     : 파일이 없거나 형식이 깨졌다.          -> 고쳐야 한다.

종료 코드
  0  READY      루프를 시작해도 된다
  1  ERROR      구조가 깨졌다
  2  NOT_READY  아직 준비되지 않았다 (초기 스타터킷의 정상 상태)

사용법
  python scripts/check_loop_readiness.py
  python scripts/check_loop_readiness.py --json
  python scripts/check_loop_readiness.py --lock      READY일 때 보호 파일 해시를 기록
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_specs as vs  # noqa: E402


def _use_utf8_output():
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is None:
        return
    try:
        reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # pragma: no cover
        pass


_use_utf8_output()


# --------------------------------------------------------------------------
# 준비 조건 정의
# --------------------------------------------------------------------------

FAILURE_TYPES = [
    "CODE_ERROR",
    "TEST_ERROR",
    "SPEC_CONFLICT",
    "ENVIRONMENT_ERROR",
    "PERMISSION_ERROR",
    "INFORMATION_INSUFFICIENT",
    "UNKNOWN_ERROR",
]

NEXT_ACTIONS = ["RETRY", "RESEARCH", "REVISE_SPEC", "HITL", "STOP"]

# 작업이 반드시 하나 이상 있어야 하는 루프 (교육생이 D-작업목록으로 정한다)
LOOP_IDS = ["A", "B"]
# 값으로 쓸 수 있는 루프. C(정성 완성도)는 킷이 고정으로 넣는 루프다.
ALLOWED_LOOP_IDS = ["A", "B", "C"]

# 숫자로 확정되어야 하는 결정 (STEP 번호, 결정 ID)
NUMERIC_DECISIONS = [
    (2, "D-취향설명분량"),
    (3, "D-도시수"),
    (3, "D-명소수"),
    (3, "D-소개근거수"),
    (3, "D-일정근거수"),
    (6, "D-정보루프반복"),
    (6, "D-페이지루프반복"),
    (6, "D-무진전기준"),
    (7, "D-최대반복"),
]

# 각 루프를 판정하는 테스트가 들어 있는 결정
LOOP_TESTS = [("A", 5, "D-정보량테스트"), ("B", 5, "D-페이지테스트")]

PROTECTED_GLOBS = [
    "specs/*.md",
    "scripts/**/*.py",
    "templates/*.md",
    "CLAUDE.md",
    "MASTER_SPEC.md",
    "LOOP_CONTRACT.md",
]

LOCK_PATH = "state/spec_lock.json"

# 채워야 할 빈칸 표시. 설명 문장이 아니라 PROJECT / MACHINE 영역 안만 센다.
BLANK_MARK = "(미정)"
FILLABLE_MARKERS = ("PROJECT", "MACHINE")


# --------------------------------------------------------------------------
# 도우미
# --------------------------------------------------------------------------


class Checklist:
    """준비 항목을 모은다."""

    def __init__(self):
        self.items = []  # (이름, 통과여부, 설명)
        self.errors = []  # 구조 오류 (ERROR)

    def add(self, name, passed, detail=""):
        self.items.append((name, bool(passed), detail))

    def error(self, where, message):
        self.errors.append((where, message))

    @property
    def missing(self):
        return [item for item in self.items if not item[1]]

    @property
    def ready(self):
        return not self.errors and not self.missing


def is_filled(value):
    """값이 실제로 채워졌는가."""
    if value is None:
        return False
    if isinstance(value, str):
        stripped = value.strip()
        return stripped != "" and stripped not in ("(미작성)", BLANK_MARK)
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def decision(steps, step, name):
    return (steps.get(step, {}).get("machine", {}).get("decisions") or {}).get(name)


def fixed(steps, step, name):
    return (steps.get(step, {}).get("machine", {}).get("fixed") or {}).get(name)


def inherited(steps, step, name):
    """앞 STEP에서 물려받아 채워 넣어야 하는 값."""
    return (steps.get(step, {}).get("machine", {}).get("inherited") or {}).get(name)


def load_steps(root, checklist):
    """STEP 문서에서 상태, 결정 목록, 기계 판독 블록을 읽는다."""
    data = {}
    for step, filename in sorted(vs.STEP_FILES.items()):
        path = root / "specs" / filename
        where = "specs/" + filename
        if not path.exists():
            checklist.error(where, "파일이 없습니다")
            continue
        text = path.read_text(encoding="utf-8")
        status, message = vs.get_status(text)
        if message:
            checklist.error(where, message)

        answers = vs.marker_regions(text, "ANSWERS")
        blanks = vs.strip_examples(answers[0]).count(vs.UNANSWERED) if answers else 0

        declared = []
        fixed_regions = vs.marker_regions(text, "FIXED")
        if fixed_regions:
            declared = vs.decision_ids(fixed_regions[0])

        machine = None
        regions = vs.marker_regions(text, "MACHINE")
        if regions:
            blocks = vs.extract_json_blocks(regions[0])
            if blocks:
                try:
                    machine = json.loads(blocks[0])
                except json.JSONDecodeError as exc:
                    checklist.error(where, "MACHINE JSON 형식 오류: " + str(exc))
            else:
                checklist.error(where, "MACHINE 블록 안에 json 코드 블록이 없습니다")
        else:
            checklist.error(where, "MACHINE 마커 블록이 없습니다")

        data[step] = {
            "file": where,
            "status": status,
            "blanks": blanks,
            "declared": declared,
            "machine": machine or {},
        }
    return data


def fillable_text(path):
    """PROJECT / MACHINE 영역만 이어 붙인다.

    설명 문장에 들어 있는 '(미정)' 이라는 낱말까지 세면
    교육생이 고칠 수 없는 곳을 고치라고 하게 된다. 그래서 채우는 영역만 본다.
    """
    text = vs.strip_examples(path.read_text(encoding="utf-8"))
    chunks = []
    for name in FILLABLE_MARKERS:
        chunks.extend(vs.marker_regions(text, name))
    return "\n".join(chunks), text


def find_nulls(node, path=""):
    """검사 계약 안에 아직 채우지 않은 null 이 있는지 찾는다."""
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            found.extend(find_nulls(value, path + "." + str(key) if path else str(key)))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(find_nulls(value, path + "[" + str(index) + "]"))
    elif node is None:
        found.append(path)
    return found


# --------------------------------------------------------------------------
# 개별 준비 검사
# --------------------------------------------------------------------------


def check_steps_approved(steps, checklist):
    not_approved = [
        str(step) for step, info in sorted(steps.items())
        if info["status"] != "APPROVED"
    ]
    checklist.add(
        "STEP 1~7 승인 완료",
        not not_approved,
        "미승인 STEP: " + ", ".join(not_approved) if not_approved else "",
    )


def check_no_blanks(steps, checklist):
    remaining = [
        str(step) + "번(" + str(info["blanks"]) + "칸)"
        for step, info in sorted(steps.items())
        if info["blanks"] > 0
    ]
    total = sum(info["blanks"] for info in steps.values())
    checklist.add(
        "내 답 적기 칸에 미작성 없음",
        total == 0,
        "남은 미작성: " + ", ".join(remaining) if remaining else "",
    )


def check_decisions_filled(steps, checklist):
    """읽기 4에 선언된 결정이 모두 값으로 채워졌는가."""
    empty = []
    total = 0
    for step, info in sorted(steps.items()):
        values = info["machine"].get("decisions") or {}
        for name in info["declared"]:
            total += 1
            if not is_filled(values.get(name)):
                empty.append("STEP " + str(step) + " " + name)

    for step, name in NUMERIC_DECISIONS:
        value = decision(steps, step, name)
        if value is not None and not isinstance(value, int):
            empty.append("STEP " + str(step) + " " + name + " 값은 숫자여야 합니다")
        elif isinstance(value, int) and value <= 0:
            empty.append("STEP " + str(step) + " " + name + " 값은 1 이상이어야 합니다")

    checklist.add(
        "결정 " + str(total) + "개가 모두 값으로 확정됨",
        not empty,
        "남은 결정 " + str(len(empty)) + "개 (예: " + ", ".join(empty[:3]) + ")"
        if empty
        else "",
    )


def check_travel_input(steps, checklist):
    """루프가 시작하려면 국가·일수·스타일 세 가지가 반드시 있어야 한다."""
    problems = []
    value = decision(steps, 1, "D-여행입력")
    if not isinstance(value, dict):
        problems.append("국가·일수·스타일이 아직 정해지지 않았습니다")
    else:
        if not is_filled(value.get("country")):
            problems.append("국가가 없습니다")
        days = value.get("days")
        if not isinstance(days, int) or days <= 0:
            problems.append("여행 일수가 1 이상의 숫자가 아닙니다")

    if not is_filled(decision(steps, 1, "D-취향분류")):
        problems.append("스타일 갈래가 없습니다")
    if not is_filled(decision(steps, 1, "D-도시선정기준")):
        problems.append("도시 선정 우선순위가 없습니다")

    request = steps.get(1, {}).get("machine", {}).get("fixed", {}).get("request_file")
    if not is_filled(request):
        problems.append("스타일을 적는 파일 경로가 없습니다")

    checklist.add(
        "필수 입력 3종 확정 (국가 · 일수 · 스타일)",
        not problems,
        "; ".join(problems[:3]) if problems else "",
    )


def check_loop_tasks(steps, checklist):
    """작업이 두 루프에 나뉘어 있고, 루프마다 판정기가 붙었는가."""
    problems = []
    tasks = decision(steps, 4, "D-작업목록") or []

    if not isinstance(tasks, list) or not tasks:
        checklist.add("작업이 두 루프에 나뉘고 판정기가 붙음", False, "작업 목록이 비어 있습니다")
        return

    by_loop = {loop: [] for loop in ALLOWED_LOOP_IDS}
    for task in tasks:
        if not isinstance(task, dict) or not isinstance(task.get("id"), str):
            problems.append("작업 항목 형식 오류: " + str(task))
            continue
        task_id = task["id"]
        if not task_id.startswith("TASK-") or not vs.SLUG_RE.match(task_id[5:]):
            problems.append("작업 ID 이름 규칙 위반: " + task_id)
            continue
        loop = task.get("loop")
        if loop not in ALLOWED_LOOP_IDS:
            problems.append(task_id + " 의 loop 값이 A · B · C 가 아닙니다: " + str(loop))
            continue
        if not is_filled(task.get("goal")):
            problems.append(task_id + " 에 목표가 없습니다")
        if not is_filled(task.get("files")):
            problems.append(task_id + " 에 채우는 파일이 없습니다")
        by_loop[loop].append(task_id)

    for loop in LOOP_IDS:
        if not by_loop[loop]:
            problems.append("루프 " + loop + " 에 작업이 하나도 없습니다")

    for loop, step, name in LOOP_TESTS:
        test = decision(steps, step, name)
        if not isinstance(test, dict):
            problems.append(name + " 이 아직 정해지지 않았습니다")
            continue
        test_id = test.get("id")
        if not isinstance(test_id, str) or not test_id.startswith("TEST-") \
                or not vs.SLUG_RE.match(test_id[5:]):
            problems.append("테스트 ID 이름 규칙 위반: " + str(test_id))
        if test.get("loop") != loop:
            problems.append(str(test_id) + " 가 가리키는 루프가 " + loop + " 가 아닙니다")
        if not is_filled(test.get("command")):
            problems.append(str(test_id) + " 에 실행 명령이 없습니다")
        if not is_filled(test.get("strictness")):
            problems.append(str(test_id) + " 에 깐깐함 등급이 없습니다")

    detail = "; ".join(problems[:3]) if problems else (
        "루프 A " + str(len(by_loop["A"])) + "개 · 루프 B " + str(len(by_loop["B"])) + "개"
    )
    checklist.add("작업이 두 루프에 나뉘고 판정기가 붙음", not problems, detail)


def check_stop_rules(steps, checklist):
    """멈출 줄 아는 루프인가. 숫자와 라우팅이 모두 확정되어야 한다."""
    problems = []

    for step, name in (
        (6, "D-정보루프반복"),
        (6, "D-페이지루프반복"),
        (6, "D-무진전기준"),
        (7, "D-최대반복"),
    ):
        value = decision(steps, step, name)
        if not isinstance(value, int) or value <= 0:
            problems.append(name + " 값이 1 이상의 숫자가 아닙니다")

    routing = fixed(steps, 6, "failure_routing") or {}
    if not isinstance(routing, dict):
        problems.append("실패 라우팅 표가 객체가 아닙니다")
    else:
        for failure in FAILURE_TYPES:
            action = routing.get(failure)
            if action not in NEXT_ACTIONS:
                problems.append(failure + " 의 다음 행동이 잘못됨: " + str(action))

    if not is_filled(decision(steps, 4, "D-사람확인지점")):
        problems.append("되물음을 띄울 지점이 없습니다")
    if not is_filled(fixed(steps, 6, "limit_reached_action")):
        problems.append("상한에 걸렸을 때의 행동이 없습니다")
    if not is_filled(fixed(steps, 7, "termination_states")):
        problems.append("종료 상태 이름 목록이 없습니다")

    checklist.add(
        "루프별 상한 · 되물음 · 종료 규칙 확정",
        not problems,
        "; ".join(problems[:3]) if problems else "",
    )


def check_run_command(steps, checklist):
    """무엇을 실행하고 무엇이 되면 성공인가."""
    problems = []

    verifier5 = decision(steps, 5, "D-최종검증명령")
    verifier7 = inherited(steps, 7, "final_verifier_command")
    if not is_filled(verifier5):
        problems.append("STEP 5에 최종 검증 명령이 없습니다")
    if not is_filled(verifier7):
        problems.append("STEP 7이 STEP 5의 검증 명령을 아직 물려받지 못했습니다")
    elif is_filled(verifier5) and verifier5 != verifier7:
        problems.append("STEP 5와 STEP 7의 최종 검증 명령이 다릅니다")
    if not is_filled(decision(steps, 7, "D-성공조건")):
        problems.append("성공 조건이 없습니다")
    if not is_filled(inherited(steps, 7, "first_task")):
        problems.append("첫 작업이 아직 정해지지 않았습니다")

    checklist.add(
        "실행 명령과 성공 조건 확정",
        not problems,
        "; ".join(problems[:3]) if problems else "",
    )


def check_guardrail(steps, checklist):
    """무엇을 못 건드리게 하고, 증거를 어디에 남기는가."""
    problems = []

    if not is_filled(decision(steps, 4, "D-수정금지파일")):
        problems.append("수정 금지 파일 목록이 없습니다")
    if not is_filled(fixed(steps, 4, "editable_paths")):
        problems.append("수정 가능 경로가 없습니다")
    if not is_filled(fixed(steps, 4, "evidence_dir")):
        problems.append("증거 폴더 경로가 없습니다")
    if not is_filled(fixed(steps, 4, "evidence_per_iteration")):
        problems.append("반복마다 남길 증거 항목이 없습니다")
    if not is_filled(fixed(steps, 4, "never_store")):
        problems.append("절대 저장하지 않을 항목이 없습니다")
    if not is_filled(fixed(steps, 4, "reverse_question_fields")):
        problems.append("되물음에 넣을 항목이 없습니다")
    if not is_filled(fixed(steps, 2, "output_file")):
        problems.append("최종 산출물 경로가 없습니다")
    if not is_filled(fixed(steps, 3, "data_file")):
        problems.append("정보를 담을 파일 경로가 없습니다")

    protected = decision(steps, 4, "D-수정금지파일")
    if isinstance(protected, list):
        joined = " ".join(str(p) for p in protected)
        for must in ("specs", "scripts"):
            if must not in joined:
                problems.append("수정 금지 목록에 " + must + "/** 가 없습니다")

    checklist.add(
        "보호 범위와 증거 위치 확정",
        not problems,
        "; ".join(problems[:3]) if problems else "",
    )



def read_contract(root):
    """MASTER_SPEC 의 검사 계약을 그대로 읽는다. 없거나 깨졌으면 None."""
    path = root / "MASTER_SPEC.md"
    if not path.exists():
        return None
    text = vs.strip_examples(path.read_text(encoding="utf-8"))
    region = re.search(
        r"<!--\s*MACHINE:BEGIN\s*-->(.*?)<!--\s*MACHINE:END\s*-->", text, re.DOTALL
    )
    block = re.search(r"```json\s*(.*?)```", region.group(1), re.DOTALL) if region else None
    if block is None:
        return None
    try:
        return json.loads(block.group(1))
    except json.JSONDecodeError:
        return None


def check_quality_loop(root, checklist):
    """루프 C(정성 완성도)의 계약이 갖춰졌는가.

    이 루프는 킷 고정이라 교육생이 답하지 않는다. 그래서 결정 21개가 늘어나지 않는다.
    다만 계약이 갖춰져 있지 않으면 루프 C 판정기가 아무것도 볼 수 없으므로 여기서 확인한다.
    """
    problems = []
    payload = read_contract(root) or {}
    quality = payload.get("quality_contract")
    loops = payload.get("loops") or {}
    rules = []
    passes = None

    if not isinstance(quality, dict) or not quality:
        problems.append("quality_contract 가 없습니다")
    else:
        passes = quality.get("passes")
        rules = quality.get("rules") or []
        if not isinstance(passes, int) or passes < 1:
            problems.append("정성 회차 수가 1 이상의 숫자가 아닙니다")
        if not rules:
            problems.append("정성 규율 목록이 비어 있습니다")

        focus = quality.get("pass_focus") or {}
        for number in range(1, (passes if isinstance(passes, int) else 0) + 1):
            picked = focus.get(str(number))
            if not picked:
                problems.append(str(number) + "회차의 렌즈가 없습니다")
                continue
            unknown = [r for r in picked if r not in rules]
            if unknown:
                problems.append(
                    str(number) + "회차 렌즈에 규율 목록에 없는 것이 있습니다: " + unknown[0]
                )

        if not quality.get("watch_files"):
            problems.append("정성 회차가 지켜볼 파일 목록이 없습니다")
        if not quality.get("regression_command"):
            problems.append("정성 회차의 되돌아감 확인 명령이 없습니다")

        rubric_rel = quality.get("rubric_file") or ""
        rubric = (root / rubric_rel) if rubric_rel else None
        if rubric is None or not rubric.exists():
            problems.append("규율 문서가 없습니다: " + str(rubric_rel))
        else:
            body = rubric.read_text(encoding="utf-8")
            missing = [r for r in rules if r not in body]
            if missing:
                problems.append("규율 문서에 설명이 없는 규율: " + ", ".join(missing[:3]))

        template_rel = quality.get("record_template") or ""
        if template_rel and not (root / template_rel).exists():
            problems.append("정성 기록 양식이 없습니다: " + template_rel)

    loop_c = loops.get("C")
    if not isinstance(loop_c, dict):
        problems.append("loops.C (정성 완성도) 가 없습니다")
    else:
        if loop_c.get("limit") != passes:
            problems.append("loops.C.limit 과 quality_contract.passes 가 다릅니다")
        if "check_quality_passes" not in str(loop_c.get("verifier") or ""):
            problems.append("loops.C 의 판정기가 check_quality_passes.py 가 아닙니다")

    detail = "; ".join(problems[:3]) if problems else (
        "규율 " + str(len(rules)) + "개 · " + str(passes) + "회 고정"
    )
    checklist.add("루프 C(정성 완성도) 계약 준비", not problems, detail)

def check_aggregates(root, checklist):
    problems = []
    for name in ("MASTER_SPEC.md", "LOOP_CONTRACT.md"):
        path = root / name
        if not path.exists():
            checklist.error(name, "파일이 없습니다")
            continue
        fill_area, whole = fillable_text(path)
        count = fill_area.count(BLANK_MARK)
        if "상태: 미완성" in whole:
            problems.append(name + " 가 아직 미완성으로 표시되어 있습니다")
        if count:
            problems.append(name + " 의 채우는 칸에 빈칸이 " + str(count) + "곳 남아 있습니다")

    contract_path = root / "MASTER_SPEC.md"
    if contract_path.exists():
        text = vs.strip_examples(contract_path.read_text(encoding="utf-8"))
        region = re.search(
            r"<!--\s*MACHINE:BEGIN\s*-->(.*?)<!--\s*MACHINE:END\s*-->", text, re.DOTALL
        )
        block = re.search(r"```json\s*(.*?)```", region.group(1), re.DOTALL) if region else None
        if block is None:
            checklist.error("MASTER_SPEC.md", "검사 계약 json 블록을 찾지 못했습니다")
        else:
            try:
                payload = json.loads(block.group(1))
            except json.JSONDecodeError as exc:
                checklist.error("MASTER_SPEC.md", "검사 계약 JSON 형식 오류: " + str(exc))
            else:
                nulls = []
                for key in ("request", "count_contract", "page_contract",
                            "quality_contract", "loops", "options"):
                    nulls.extend(find_nulls(payload.get(key), key))
                if nulls:
                    problems.append(
                        "검사 계약에 아직 채우지 않은 값 " + str(len(nulls))
                        + "개 (예: " + ", ".join(nulls[:3]) + ")"
                    )

    state = root / "state" / "loop_state.json"
    if not state.exists():
        problems.append("state/loop_state.json 이 아직 없습니다")
    else:
        try:
            json.loads(state.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            checklist.error("state/loop_state.json", "JSON 형식 오류: " + str(exc))

    checklist.add(
        "MASTER_SPEC / LOOP_CONTRACT / loop_state 준비",
        not problems,
        "; ".join(problems[:3]) if problems else "",
    )


# --------------------------------------------------------------------------
# 보호 파일 잠금
# --------------------------------------------------------------------------


def collect_protected(root):
    found = {}
    for pattern in PROTECTED_GLOBS:
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                rel = path.relative_to(root).as_posix()
                found[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


def write_lock(root):
    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "files": collect_protected(root),
    }
    path = root / LOCK_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return path, len(payload["files"])


def verify_lock(root, checklist):
    path = root / LOCK_PATH
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        checklist.error(LOCK_PATH, "JSON 형식 오류: " + str(exc))
        return None

    recorded = payload.get("files", {})
    current = collect_protected(root)
    changed = [name for name, digest in recorded.items()
               if current.get(name) != digest]
    removed = [name for name in recorded if name not in current]
    for name in removed:
        checklist.error(name, "잠금된 보호 파일이 사라졌습니다")
    for name in changed:
        if name not in removed:
            checklist.error(name, "잠금 이후 보호 파일이 바뀌었습니다"
                            " — 사람이 바뀐 내용을 확인한 뒤 state/spec_lock.json 을 지우고 다시 잠급니다")
    return len(recorded)


# --------------------------------------------------------------------------
# 실행
# --------------------------------------------------------------------------


def check_verifier_integrity(root, checklist):
    """루프를 시작하기 전에 **검사기가 무결한지** 먼저 본다.

    검사기가 약해진 것은 검사기가 알려 주지 않는다. 계약에 선택지 문구를 적었더니
    검사행 6개가 사라졌는데 판정은 PASS 였던 일이 실제로 있었다. 그래서
    "빈칸이 다 찼는가"보다 먼저 "채점표가 살아 있는가"를 확인한다. 1초면 끝난다.
    """
    script = Path(root) / "scripts" / "selftest" / "run_selftest.py"
    if not script.exists():
        checklist.error("scripts/selftest/run_selftest.py", "파일이 없습니다")
        return
    try:
        proc = subprocess.run(
            [sys.executable, str(script)], cwd=str(root), shell=False,
            capture_output=True, timeout=180,
        )
    except Exception as exc:  # noqa: BLE001
        checklist.add("검사기 셀프테스트", False, "돌리지 못했습니다: " + str(exc)[:60])
        return
    if proc.returncode == 0:
        checklist.add("검사기 셀프테스트", True, "모든 검사행이 살아 있음")
        return
    tail = (proc.stdout or b"").decode("utf-8", "replace").strip().splitlines()
    dead = [line.strip(" -") for line in tail if line.strip().startswith("- ")]
    checklist.error(
        "scripts/selftest",
        "죽은 검사행이 있습니다: " + (", ".join(dead[:3]) or "run_selftest.py 를 직접 돌려 보십시오")
        + " — 결과물이 아니라 검사기를 고쳐야 합니다")


def evaluate(root, checklist):
    """준비 항목을 모두 검사한다. 돌려주는 값 = 검증한 잠금의 파일 수 (잠금이 없으면 None)."""
    check_verifier_integrity(root, checklist)

    structure = vs.run(root, sorted(vs.STEP_FILES))
    for where, message in structure.errors:
        checklist.error(where, message)

    steps = load_steps(root, checklist)
    if not steps:
        return None

    check_steps_approved(steps, checklist)
    check_no_blanks(steps, checklist)
    check_decisions_filled(steps, checklist)
    check_travel_input(steps, checklist)
    check_loop_tasks(steps, checklist)
    check_stop_rules(steps, checklist)
    check_run_command(steps, checklist)
    check_guardrail(steps, checklist)
    check_aggregates(root, checklist)
    check_quality_loop(root, checklist)
    return verify_lock(root, checklist)


def verdict(checklist):
    if checklist.errors:
        return "ERROR", 1
    if checklist.missing:
        return "NOT_READY", 2
    return "READY", 0


def print_report(checklist, result, locked=None):
    """locked = 이미 있는 잠금에 기록된 파일 수 (없으면 None). READY 면 그 잠금은 검증을 통과한 것이다."""
    line = "=" * 62
    print(line)
    print(" 루프 준비도 검사 (check_loop_readiness.py)")
    print(line)
    print(" 결과: " + result)
    print("")

    for name, passed, detail in checklist.items:
        mark = "[OK]  " if passed else "[--]  "
        print(" " + mark + name)
        if detail:
            print("        " + detail)
    print("")

    if result == "ERROR":
        print(" [ERROR] 구조가 깨졌습니다. 이것은 미입력이 아니라 고쳐야 할 문제입니다.")
        for where, message in checklist.errors:
            print("   - " + where + ": " + message)
        print("")
        print(" 조치: python scripts/validate_specs.py 로 자세히 확인하세요.")
    elif result == "NOT_READY":
        print(" [NOT_READY] 아직 루프를 시작할 수 없습니다.")
        print(" 처음 스타터킷 상태에서는 이것이 정상입니다. 오류가 아닙니다.")
        print("")
        print(" 남은 항목:")
        for item in checklist.missing:
            name, detail = item[0], item[2]
            print("   - " + name + (" : " + detail if detail else ""))
        print("")
        print(" 조치: Claude Code에서 'STEP N 진행해줘' 라고 말해 이어서 답하세요.")
        print("       (N = 아직 승인되지 않은 첫 STEP. 처음이면 STEP 1)")
    else:
        print(" [READY] 루프를 시작해도 됩니다.")
        print("")
        if locked:
            #  잠금이 이미 있고 해시가 그대로다(바뀌었으면 위에서 ERROR). 다시 --lock 하면
            #  해시는 같고 created_at 만 덮어쓰므로 안내하지 않는다.
            print(" 잠금 확인됨 (" + str(locked) + "개 · 변경 없음) — 다음: 루프를 실행해줘")
            print("   Claude Code에서 '루프를 실행해줘' 또는 /loop-run   (다시 --lock 하지 않아도 됩니다)")
        else:
            print(" 다음 단계:")
            print("   1) python scripts/check_loop_readiness.py --lock   보호 파일 잠금")
            print("   2) Claude Code에서 '루프를 실행해줘' 또는 /loop-run")
    print(line)


def main():
    parser = argparse.ArgumentParser(description="루프 준비도 검사")
    parser.add_argument("--root", default=None, help="스타터킷 폴더 경로")
    parser.add_argument("--json", action="store_true", help="결과를 JSON으로 출력")
    parser.add_argument(
        "--lock",
        action="store_true",
        help="READY일 때 보호 파일 해시를 state/spec_lock.json에 기록",
    )
    args = parser.parse_args()

    #  resolve(): 상대 경로 --root 이면 셀프테스트(cwd=root)가 스크립트를 못 찾는다
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent

    checklist = Checklist()
    locked = evaluate(root, checklist)
    result, code = verdict(checklist)

    if args.lock:
        if result != "READY":
            print("[거부] 준비 상태가 " + result + "이므로 잠글 수 없습니다.")
            print("       먼저 python scripts/check_loop_readiness.py 로 남은 항목을 채우세요.")
            return code
        path, count = write_lock(root)
        print("[LOCK] 보호 파일 " + str(count) + "개의 해시를 기록했습니다.")
        print("       " + path.as_posix())
        return 0

    if args.json:
        payload = {
            "result": result,
            "checks": [
                {"name": n, "passed": p, "detail": d} for n, p, d in checklist.items
            ],
            "errors": [{"where": w, "message": m} for w, m in checklist.errors],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_report(checklist, result, locked)

    return code


if __name__ == "__main__":
    sys.exit(main())
