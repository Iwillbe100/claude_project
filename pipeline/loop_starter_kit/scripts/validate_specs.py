#!/usr/bin/env python3
"""specs/ 문서의 구조를 검사한다.

이 스크립트는 '문서가 규칙대로 쓰였는가'만 본다.
'교육생이 답을 다 했는가'는 check_loop_readiness.py가 본다.

종료 코드
  0  PASS   구조 이상 없음
  1  ERROR  구조가 깨졌음 (파일 없음, 구역 누락, JSON 깨짐 등)

사용법
  python scripts/validate_specs.py
  python scripts/validate_specs.py --step 3
  python scripts/validate_specs.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _use_utf8_output():
    """Windows 콘솔에서 한글이 깨지지 않게 한다."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is None:
        return
    try:
        reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # pragma: no cover
        pass


_use_utf8_output()


# --------------------------------------------------------------------------
# 규칙 정의
# --------------------------------------------------------------------------

STEP_FILES = {
    1: "01_INPUT_AND_STYLE.md",
    2: "02_PAGE_DESIGN.md",
    3: "03_INFORMATION_COUNT.md",
    4: "04_BOUNDARY_TASKS_SAFETY.md",
    5: "05_TEST_AND_VERIFIER.md",
    6: "06_LOOP_ITERATION.md",
    7: "07_EXECUTION_CONTRACT.md",
}

SUPPORT_FILES = ["00_INDEX.md", "00_DECISION_LOG.md", "QUALITY_RUBRIC.md"]

ROOT_FILES = [
    "CLAUDE.md",
    "PROJECT_MEMORY.md",
    "MASTER_SPEC.md",
    "LOOP_CONTRACT.md",
    "USER_REQUEST.md",
]

# 읽는 순서가 곧 구역 번호다. 순서와 이름이 모두 일치해야 한다.
REQUIRED_SECTIONS = [
    "읽기 1 — 이 STEP에서 정하는 것",
    "읽기 2 — 앞에서 물려받은 결정",
    "읽기 3 — 이미 정해 둔 것 (읽고 넘어가기)",
    "읽기 4 — 내가 결정할 질문",
    "읽기 5 — 내 답 적기",
    "읽기 6 — Claude가 정리한 결과",
    "읽기 7 — 이 STEP이 끝나면 무엇이 진행되는가",
    "읽기 8 — 완료 확인과 다음 명령",
]

# 읽기 7에 반드시 있어야 하는 문구. 교육생이 "그래서 뭘 하지?"에서 끊기지 않게 한다.
HANDOFF_KEYS = [
    "지금 코드가 만들어지나",
    "Claude가 실제로 하는 일",
    "바뀌는 파일",
    "내가 지금 실행할 명령",
]

ALLOWED_PRODUCES = ["spec_only", "spec_then_code"]

ALLOWED_STATUS = [
    "DRAFT",
    "IN_PROGRESS",
    "READY_FOR_REVIEW",
    "APPROVED",
    "NEEDS_REVIEW",
    "BLOCKED",
]

MARKERS = ["FIXED", "ANSWERS", "PROJECT", "MACHINE", "STATUS", "EXAMPLE"]

UNANSWERED = "(미작성)"

# 결정 ID는 반드시 백틱으로 감싼다. 이름 자체가 무엇을 정하는지 말해야 한다.
#   좋음: `D-도시수`  `TASK-명소수집`  `TEST-정보량`
#   나쁨: D-008  TASK-01
ID_PATTERNS = {
    "D": re.compile(r"`D-([^`\s]+)`"),
    "TASK": re.compile(r"`TASK-([^`\s]+)`"),
    "TEST": re.compile(r"`TEST-([^`\s]+)`"),
}

SLUG_RE = re.compile(r"^[가-힣A-Za-z0-9]{2,16}$")

ID_SHAPE = "`D-도시수`처럼 한글 2~16자 이름"

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")

REQUIRED_DIRS = [
    "specs",
    "templates",
    "state",
    "evidence",
    "scripts",
    ".claude/skills",
]

REQUIRED_JSON_FILES = [
    "state/loop_state.example.json",
    ".claude/settings.example.json",
]

REQUIRED_SKILLS = ["step-spec-builder", "spec-sync", "loop-run", "evidence-review"]

REQUIRED_TEMPLATES = [
    "EVIDENCE_RECORD.md",
    "FAILURE_REPORT.md",
    "REVERSE_QUESTION.md",
    "FINAL_REPORT.md",
    "QUALITY_PASS.md",
]

# 킷이 소유하는 판정기와 도우미. 하나라도 없으면 루프가 판정될 수 없다.
REQUIRED_SCRIPTS = [
    "_contract.py",
    "check_information_count.py",
    "check_page_contract.py",
    "check_quality_passes.py",
    "verify_all.py",
    "check_loop_readiness.py",
    "validate_specs.py",
    "export_graph_handoff.py",
]

# 검사기를 검사하는 검사기. 이것이 없으면 채점표가 살아 있는지 아무도 모른다.
REQUIRED_SELFTEST = [
    "selftest/run_selftest.py",
    "selftest/world.py",
]


# --------------------------------------------------------------------------
# 도우미
# --------------------------------------------------------------------------


class Report:
    """검사 결과를 모은다."""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.checked = []

    def error(self, where, message):
        self.errors.append((where, message))

    def warn(self, where, message):
        self.warnings.append((where, message))

    def ok(self, what):
        self.checked.append(what)


def read_text(path):
    return path.read_text(encoding="utf-8")


def marker_regions(text, name):
    """마커 BEGIN 과 END 사이의 내용을 모두 돌려준다."""
    pattern = re.compile(
        r"<!--\s*" + name + r":BEGIN\s*-->(.*?)<!--\s*" + name + r":END\s*-->",
        re.DOTALL,
    )
    return pattern.findall(text)


def marker_balanced(text, name):
    begins = len(re.findall(r"<!--\s*" + name + r":BEGIN\s*-->", text))
    ends = len(re.findall(r"<!--\s*" + name + r":END\s*-->", text))
    return begins, ends


def strip_examples(text):
    """예시 영역을 지운다. 예시 값은 실제 결정으로 세지 않는다."""
    return re.sub(
        r"<!--\s*EXAMPLE:BEGIN\s*-->.*?<!--\s*EXAMPLE:END\s*-->",
        "",
        text,
        flags=re.DOTALL,
    )


def extract_json_blocks(chunk):
    """json 코드 블록 안의 문자열을 돌려준다."""
    return re.findall(r"```json\s*(.*?)```", chunk, re.DOTALL)


def get_status(text):
    """(상태값, 오류메시지)를 돌려준다."""
    regions = marker_regions(text, "STATUS")
    if not regions:
        return None, "STATUS 마커 블록이 없습니다"
    found = re.findall(r"^\s*STATUS:\s*([A-Z_]+)\s*$", regions[0], re.MULTILINE)
    if not found:
        return None, "STATUS 블록 안에 'STATUS: 값' 줄이 없습니다"
    if len(found) > 1:
        return None, "STATUS 블록 안에 상태 줄이 2개 이상입니다"
    return found[0], None


def get_machine_json(text, where, report):
    regions = marker_regions(text, "MACHINE")
    if not regions:
        return None
    blocks = extract_json_blocks(regions[0])
    if not blocks:
        if report is not None:
            report.error(where, "MACHINE 블록 안에 json 코드 블록이 없습니다")
        return None
    try:
        return json.loads(blocks[0])
    except json.JSONDecodeError as exc:
        if report is not None:
            report.error(where, "MACHINE JSON 형식 오류: " + str(exc))
        return None


def section_body(text, heading):
    match = re.search(
        r"^##\s+" + re.escape(heading) + r"\s*$(.*?)(?=^##\s|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1) if match else None


def decision_ids(chunk):
    """구역 안에 선언된 결정 ID 목록 (순서 유지, 중복 제거)."""
    found = []
    for name in ID_PATTERNS["D"].findall(chunk or ""):
        full = "D-" + name
        if full not in found:
            found.append(full)
    return found


# --------------------------------------------------------------------------
# 개별 검사
# --------------------------------------------------------------------------


def check_sections(text, where, report):
    headings = [h.strip() for h in re.findall(r"^##\s+(.+?)\s*$", text, re.MULTILINE)]
    position = -1
    for section in REQUIRED_SECTIONS:
        if section not in headings:
            report.error(where, "필수 구역 누락: '## " + section + "'")
            continue
        index = headings.index(section)
        if index < position:
            report.error(where, "읽는 순서가 뒤바뀜: '## " + section + "'")
        position = index


def check_markers(text, where, report):
    for name in MARKERS:
        begins, ends = marker_balanced(text, name)
        if begins != ends:
            report.error(
                where,
                name + " 마커 짝이 맞지 않습니다 (BEGIN "
                + str(begins) + "개 / END " + str(ends) + "개)",
            )
    for name in ("FIXED", "ANSWERS", "PROJECT", "STATUS", "MACHINE"):
        if marker_balanced(text, name)[0] == 0:
            report.error(where, name + " 마커 블록이 없습니다")


def check_decisions(text, where, report):
    """읽기 4의 결정 ID와 기계 판독 블록의 키가 정확히 같아야 한다."""
    regions = marker_regions(text, "FIXED")
    if not regions:
        return []
    declared = decision_ids(regions[0])
    if not declared:
        report.error(where, "읽기 4에 `D-이름` 형식의 결정 ID가 없습니다")
        return []
    if len(declared) > 4:
        report.warn(
            where,
            "결정이 " + str(len(declared)) + "개입니다. STEP당 4개 이하를 권장합니다",
        )

    machine = get_machine_json(text, where, None) or {}
    keys = list((machine.get("decisions") or {}).keys())
    missing = [d for d in declared if d not in keys]
    extra = [k for k in keys if k not in declared]
    if missing:
        report.error(where, "기계 판독 블록에 빠진 결정: " + ", ".join(missing))
    if extra:
        report.error(where, "읽기 4에 없는 결정이 기계 블록에 있음: " + ", ".join(extra))

    answers = marker_regions(text, "ANSWERS")
    if answers:
        body = strip_examples(answers[0])
        not_asked = [d for d in declared if "`" + d + "`" not in body]
        if not_asked:
            report.error(where, "읽기 5에 답 칸이 없는 결정: " + ", ".join(not_asked))

    report.ok(where + ": 결정 " + str(len(declared)) + "개 (" + ", ".join(declared) + ")")
    return declared


def check_answers(text, status, where, report):
    regions = marker_regions(text, "ANSWERS")
    if not regions:
        return 0
    body = strip_examples(regions[0])
    blanks = body.count(UNANSWERED)
    if status == "APPROVED" and blanks:
        report.error(
            where,
            "상태가 APPROVED인데 답하지 않은 칸이 " + str(blanks) + "개 남아 있습니다",
        )
    return blanks


def check_ids(text, where, report):
    body = strip_examples(text)
    for prefix, pattern in ID_PATTERNS.items():
        for suffix in sorted(set(pattern.findall(body))):
            if suffix == "예시":
                report.error(
                    where,
                    prefix + "-예시는 예시 영역(EXAMPLE 마커) 안에서만 쓸 수 있습니다",
                )
                continue
            if not SLUG_RE.match(suffix):
                report.error(
                    where,
                    "ID 이름 규칙 위반: " + prefix + "-" + suffix + " (" + ID_SHAPE + ")",
                )
            elif suffix.isdigit():
                report.error(
                    where,
                    "숫자만 있는 ID는 쓰지 않습니다: " + prefix + "-" + suffix,
                )


def check_status(text, where, report):
    status, message = get_status(text)
    if message:
        report.error(where, message)
        return None
    if status not in ALLOWED_STATUS:
        report.error(
            where,
            "허용되지 않은 상태값: " + str(status)
            + " (허용: " + ", ".join(ALLOWED_STATUS) + ")",
        )
        return None
    return status


def check_handoff(text, where, report):
    """읽기 7이 '다음에 무엇이 진행되는가'를 실제로 답하는지 본다."""
    body = section_body(text, "읽기 7 — 이 STEP이 끝나면 무엇이 진행되는가")
    if body is None:
        return
    for key in HANDOFF_KEYS:
        if key not in body:
            report.error(where, "읽기 7에 '" + key + "' 항목이 없습니다")
    if "specs/" not in body:
        report.error(where, "읽기 7에 바뀌는 파일 경로가 없습니다")


def check_finish(text, where, report):
    """읽기 8에 완료 조건·확인 명령·다음 명령이 모두 있는지 본다."""
    body = section_body(text, "읽기 8 — 완료 확인과 다음 명령")
    if body is None:
        return
    if len(re.findall(r"^\s*-\s*\[[ xX]\]", body, re.MULTILINE)) < 2:
        report.error(where, "읽기 8의 완료 조건 체크리스트가 2개 미만입니다")
    if "validate_specs.py" not in body and "check_loop_readiness.py" not in body:
        report.error(where, "읽기 8에 결정론적 확인 명령이 없습니다")
    if "```" not in body:
        report.error(where, "읽기 8에 다음 명령 코드 블록이 없습니다")


def check_links(text, path, where, report):
    for target in LINK_RE.findall(text):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        clean = target.split("#", 1)[0]
        if not clean:
            continue
        if not (path.parent / clean).exists():
            report.error(where, "링크 대상이 없습니다: " + target)


def check_step_file(root, step, report):
    path = root / "specs" / STEP_FILES[step]
    where = "specs/" + STEP_FILES[step]
    if not path.exists():
        report.error(where, "파일이 없습니다")
        return
    text = read_text(path)

    check_sections(text, where, report)
    check_markers(text, where, report)
    check_decisions(text, where, report)
    status = check_status(text, where, report)
    check_answers(text, status, where, report)
    check_ids(text, where, report)
    check_handoff(text, where, report)
    check_finish(text, where, report)
    check_links(text, path, where, report)

    machine = get_machine_json(text, where, report)
    if machine is None:
        report.error(where, "MACHINE JSON을 읽지 못했습니다")
        return
    if machine.get("step") != step:
        report.error(
            where,
            "MACHINE JSON의 step 값이 " + str(machine.get("step"))
            + "입니다 (기대값 " + str(step) + ")",
        )
    if machine.get("produces") not in ALLOWED_PRODUCES:
        report.error(
            where,
            "produces 값이 잘못됨: " + str(machine.get("produces"))
            + " (허용: " + ", ".join(ALLOWED_PRODUCES) + ")",
        )
    if not isinstance(machine.get("decisions"), dict):
        report.error(where, "MACHINE JSON에 decisions 객체가 없습니다")


def check_markers_light(text, where, report):
    for name in MARKERS:
        begins, ends = marker_balanced(text, name)
        if begins != ends:
            report.error(
                where,
                name + " 마커 짝이 맞지 않습니다 (BEGIN "
                + str(begins) + "개 / END " + str(ends) + "개)",
            )


def check_support_file(root, name, report):
    path = root / "specs" / name
    where = "specs/" + name
    if not path.exists():
        report.error(where, "파일이 없습니다")
        return
    text = read_text(path)
    check_markers_light(text, where, report)
    check_ids(text, where, report)
    check_links(text, path, where, report)


def check_root_file(root, name, report):
    path = root / name
    if not path.exists():
        report.error(name, "파일이 없습니다")
        return
    text = read_text(path)
    check_markers_light(text, name, report)
    check_ids(text, name, report)
    check_links(text, path, name, report)
    if marker_balanced(text, "MACHINE")[0]:
        if get_machine_json(text, name, report) is None:
            report.error(name, "MACHINE JSON을 읽지 못했습니다")


def check_layout(root, report):
    for rel in REQUIRED_DIRS:
        if not (root / rel).is_dir():
            report.error(rel, "폴더가 없습니다")

    for rel in REQUIRED_JSON_FILES:
        path = root / rel
        if not path.exists():
            report.error(rel, "파일이 없습니다")
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            report.error(rel, "JSON 형식 오류: " + str(exc))

    for name in REQUIRED_TEMPLATES:
        if not (root / "templates" / name).exists():
            report.error("templates/" + name, "파일이 없습니다")

    for name in REQUIRED_SCRIPTS + REQUIRED_SELFTEST:
        if not (root / "scripts" / name).exists():
            report.error("scripts/" + name, "파일이 없습니다")

    for skill in REQUIRED_SKILLS:
        rel = ".claude/skills/" + skill + "/SKILL.md"
        path = root / ".claude" / "skills" / skill / "SKILL.md"
        if not path.exists():
            report.error(rel, "파일이 없습니다")
            continue
        text = read_text(path)
        if not text.startswith("---"):
            report.error(rel, "front matter가 없습니다")
            continue
        parts = text.split("---", 2)
        head = parts[1] if len(parts) > 2 else ""
        for key in ("name:", "description:"):
            if key not in head:
                report.error(rel, "front matter에 " + key + " 항목이 없습니다")
        if ("name: " + skill) not in head:
            report.error(rel, "front matter의 name이 폴더 이름과 다릅니다")
    report.ok("폴더/파일 골격 확인")


# --------------------------------------------------------------------------
# 실행
# --------------------------------------------------------------------------


def run(root, steps):
    report = Report()
    check_layout(root, report)
    for name in SUPPORT_FILES:
        check_support_file(root, name, report)
    for name in ROOT_FILES:
        check_root_file(root, name, report)
    for step in steps:
        check_step_file(root, step, report)
    return report


def print_report(report, steps):
    line = "=" * 62
    print(line)
    print(" 명세 구조 검사 (validate_specs.py)")
    print(line)
    print(" 검사한 STEP : " + ", ".join(str(s) for s in steps))
    print("")

    for item in report.checked:
        print("   - " + item)
    if report.checked:
        print("")

    if report.warnings:
        print(" [주의]")
        for where, message in report.warnings:
            print("   " + where + ": " + message)
        print("")

    if report.errors:
        print(" [FAIL] 구조 오류 " + str(len(report.errors)) + "건")
        for where, message in report.errors:
            print("   - " + where + ": " + message)
        print("")
        print(" 이 오류는 교육생의 미입력이 아니라 '문서 구조가 깨진 것'입니다.")
    else:
        print(" [PASS] 문서 구조에 이상이 없습니다.")
        print("")
        #  ★ STEP 1~6 을 하나씩 확인하는 중이면 다음 일은 다음 STEP 이다. 준비도 검사는 STEP 7 까지
        #    APPROVED 여야 READY 를 내므로, 그 전에 안내하면 exit 2(NOT_READY)만 보게 된다.
        if len(steps) == 1 and steps[0] < 7:
            print(f" 다음 단계: STEP {steps[0] + 1} 진행해줘   (준비도 검사는 STEP 7 까지 끝낸 뒤)")
        else:
            print(" 다음 단계: python scripts/check_loop_readiness.py")
    print(line)


def main():
    parser = argparse.ArgumentParser(description="specs 문서 구조 검사")
    parser.add_argument("--step", type=int, help="특정 STEP만 검사 (1~7)")
    parser.add_argument("--root", default=None, help="스타터킷 폴더 경로")
    parser.add_argument("--json", action="store_true", help="결과를 JSON으로 출력")
    args = parser.parse_args()

    root = Path(args.root) if args.root else Path(__file__).resolve().parent.parent

    if args.step is not None:
        if args.step not in STEP_FILES:
            print("[ERROR] STEP 번호는 1~7 사이여야 합니다: " + str(args.step))
            return 1
        steps = [args.step]
    else:
        steps = sorted(STEP_FILES)

    report = run(root, steps)

    if args.json:
        payload = {
            "result": "PASS" if not report.errors else "ERROR",
            "checked_steps": steps,
            "errors": [{"where": w, "message": m} for w, m in report.errors],
            "warnings": [{"where": w, "message": m} for w, m in report.warnings],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_report(report, steps)

    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
