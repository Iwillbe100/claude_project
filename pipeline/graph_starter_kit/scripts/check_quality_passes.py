#!/usr/bin/env python3
"""루프 C(정성 완성도 루프)의 판정기.

루프 A와 B는 셀 수 있는 것을 본다. 루프 C는 셀 수 없는 것을 다룬다.
그런데 셀 수 없는 것을 어떻게 판정하는가?

  품질에 점수를 매기면    글을 쓴 쪽이 자기 글에 점수를 준다  -> 조건5 붕괴
  3회를 돌았는지만 보면   아무것도 안 고치고 3번 넘어갈 수 있다

그래서 이 판정기는 품질을 채점하지 않고 절차를 채점한다.

  본다        3회를 다 돌았는가
  본다        회차마다 규율 10개를 전부 판정했는가
  본다        위반이면 어디(where)인지 적었는가
  본다        위반이라 적은 것을 실제로 고쳤는가
  본다        3회 합쳐 고친 것이 1건 이상인가 (3회 전부 0건이면 SHORT → 사람이 확인)
  본다        고쳤다면 파일이 실제로 바뀌었는가 (해시로 확인)
  본다        고칠 것이 없다면 파일이 그대로인가 (고친 척을 막는다)
  본다        회차 끝마다 루프 A와 B가 여전히 통과하는가 (되돌아감 방지)
  보지 않는다  글이 좋아졌는가

  MASTER_SPEC.md  quality_contract          --+
  evidence/runs/<run_id>/quality/passN.json  +--> 절차 대조 --> 종료 코드

종료 코드
  0  PASS   3회를 규율대로 다 돌았다
  1  ERROR  기록이 깨졌다 (사람이 고쳐야 한다)
  2  SHORT  아직 덜 돌았다 (루프가 더 돌면 된다)

사용법
  python scripts/check_quality_passes.py
  python scripts/check_quality_passes.py --run-id 2026-09-05T14-20-05
  python scripts/check_quality_passes.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _contract import (  # noqa: E402
    ContractError,
    Result,
    load_spec,
    print_result,
    sha256_file,
    use_utf8_output,
)

use_utf8_output()

VERDICTS = ("OK", "VIOLATION")

#: `where` 칸에 이것만 적혀 있으면 "어디인지 안 적은 것"으로 본다.
BLANK_WHERE = ("", "-", "--", "없음", "해당 없음", "n/a", "N/A", "?")

#: 재검증을 직접 돌릴 때 켜는 표시. 안쪽에서 또 돌지 않게 막는다.
GUARD_ENV = "LOOP_C_REGRESSION_RUNNING"


def rerun_regression(base, command):
    """마지막 회차의 재검증을 **직접 돌려서** 기록된 종료 코드와 맞춰 본다.

    왜 마지막 회차만인가. 앞 회차는 그 뒤로 파일이 바뀌었으므로 지금 돌려도
    그때를 잴 수 없다. 마지막 회차는 `snapshot_after` 가 지금 파일과 같아야
    하고 그것을 바로 위에서 확인하므로, 지금 돌린 결과가 곧 그때의 결과다.

    이 검사가 없으면 `verify_after.exit_code` 는 **기록하는 쪽이 적어 넣은 숫자**다.
    루프 킷에서는 그 기록을 사람이나 모델이 직접 쓰므로, 0 이라고 적기만 하면
    아무도 확인하지 않았다. 실제로 그렇게 통과한 적이 있다.

    되돌이 방지: 부르는 명령은 `--skip-quality` 라 루프 C 를 보지 않는다.
    그래도 환경 변수로 한 번 더 막는다.

    돌릴 수 없으면 None 을 돌려준다 (검사 결과를 만들지 않는다).
    """
    if os.environ.get(GUARD_ENV) == "1":
        return None
    if "--skip-quality" not in (command or ""):
        # 루프 C 자신을 다시 부르는 명령은 돌리지 않는다.
        return None
    parts = (command or "").split()
    if len(parts) < 2:
        return None
    executable = sys.executable if parts[0] in ("python", "python3", "py") else parts[0]
    script = Path(parts[1])
    if not script.is_absolute():
        script = base / script
    if not script.exists():
        return None
    argv = [executable, str(script)] + list(parts[2:])

    env = dict(os.environ)
    env[GUARD_ENV] = "1"
    try:
        proc = subprocess.run(
            argv, cwd=str(base), env=env, shell=False,
            capture_output=True, timeout=300,
        )
    except Exception:  # noqa: BLE001  (환경 문제로 못 돌린 것은 실패가 아니다)
        return None
    return proc.returncode


def latest_run_dir(root, run_id=None):
    runs = root / "evidence" / "runs"
    if not runs.is_dir():
        return None
    if run_id:
        target = runs / run_id
        return target if target.is_dir() else None
    dirs = sorted([p for p in runs.iterdir() if p.is_dir()])
    return dirs[-1] if dirs else None


def read_pass(path, result):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        result.note_broken(path.name + " 의 JSON 형식 오류: " + str(exc))
        return None


def check_rules(result, label, record, wanted):
    """규율 10개를 전부 판정했는가. 위반이라 적었으면 고쳤는가."""
    rows = record.get("rules")
    if not isinstance(rows, list):
        result.row(label + " 규율 판정", str(len(wanted)) + "개", "없음", False)
        return []

    seen = {}
    where = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        rid = (row.get("id") or "").strip()
        verdict = (row.get("verdict") or "").strip()
        if rid:
            seen[rid] = verdict
            where[rid] = str(row.get("where") or "").strip()

    missing = [r for r in wanted if r not in seen]
    result.row(label + " 규율 판정", str(len(wanted)) + "개", str(len(seen)) + "개", not missing)
    for rid in missing[:3]:
        result.note_short(label + ": " + rid + " 을(를) 판정하지 않았습니다")

    bad = [rid for rid, v in seen.items() if v not in VERDICTS]
    if bad:
        result.row(label + " 판정값", "OK/VIOLATION", "어긋남 " + str(len(bad)), False)
        result.note_short(label + ": " + bad[0] + " 의 판정값이 OK 도 VIOLATION 도 아닙니다")

    violations = [rid for rid, v in seen.items() if v == "VIOLATION"]

    # 위반이라 적었으면 **어디인지** 적어야 한다. 자리를 못 대면 고칠 수도 없고,
    # 사람이 나중에 그 판정이 맞았는지 확인할 수도 없다.
    vague = [rid for rid in violations if where.get(rid, "").lower() in BLANK_WHERE]
    if violations:
        result.row(
            label + " 위반 위치 적음", str(len(violations)) + "건",
            str(len(violations) - len(vague)) + "건", not vague,
        )
        for rid in vague[:3]:
            result.note_short(
                label + ": " + rid + " 을(를) 위반이라 적고 where(어디인지)를 비웠습니다")

    return violations


def check_fixes(result, label, record, violations):
    """위반이라 적어 놓고 넘어가지 못하게 한다."""
    fixes = record.get("applied_fix")
    if not isinstance(fixes, list):
        fixes = []
    fixed_rules = {(f.get("rule") or "").strip() for f in fixes if isinstance(f, dict)}

    unfixed = [r for r in violations if r not in fixed_rules]
    result.row(
        label + " 위반 대응", str(len(violations)) + "건",
        str(len(violations) - len(unfixed)) + "건", not unfixed,
    )
    for rid in unfixed[:3]:
        result.note_short(label + ": " + rid + " 을(를) 위반이라 적고 고치지 않았습니다")
    return fixes


def check_snapshot(result, label, record, fixes, watch_files):
    """고쳤다면 파일이 바뀌어야 하고, 안 고쳤다면 그대로여야 한다."""
    before = record.get("snapshot_before")
    after = record.get("snapshot_after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        result.row(label + " 파일 해시 기록", "before/after", "없음", False)
        return None, None

    missing = [f for f in watch_files if f not in before or f not in after]
    result.row(label + " 해시 대상", str(len(watch_files)) + "개",
               str(len(watch_files) - len(missing)) + "개", not missing)
    for name in missing[:2]:
        result.note_short(label + ": " + name + " 의 해시가 기록되지 않았습니다")

    changed = any(before.get(f) != after.get(f) for f in watch_files)
    if fixes:
        result.row(label + " 고친 결과 파일 변화", "바뀜", "바뀜" if changed else "그대로", changed)
        if not changed:
            result.note_short(label + ": 고쳤다고 적었는데 파일 해시가 그대로입니다")
    else:
        result.row(label + " 무수정 회차", "그대로", "바뀜" if changed else "그대로", not changed)
        if changed:
            result.note_short(label + ": 고친 것이 없다는데 파일이 바뀌었습니다")
    return before, after


def check_regression(result, label, record, command, base=None, verify_now=False):
    """정성 개선이 정량 계약을 깨뜨리지 않았는가. 이 검사가 이 루프의 안전핀이다.

    `verify_now` 이면 그 명령을 **실제로 돌려** 기록된 종료 코드와 맞춰 본다.
    마지막 회차에서만 켠다 (그때의 파일 = 지금의 파일이기 때문이다).
    """
    verify = record.get("verify_after")
    if not isinstance(verify, dict):
        result.row(label + " 정량 재검증", "exit 0", "기록 없음", False)
        return
    code = verify.get("exit_code")
    result.row(label + " 정량 재검증", "exit 0", str(code), code == 0)
    if code != 0:
        result.note_short(label + ": 이 회차 끝에 루프 A/B 가 통과하지 않았습니다. 수정을 되돌리세요")
    used = str(verify.get("command") or "")
    if command and command.split()[-1] not in used:
        result.note_short(label + ": 재검증 명령이 계약과 다릅니다 (계약: " + command + ")")

    if not verify_now or base is None:
        return
    actual = rerun_regression(base, command)
    if actual is None:
        return              # 이 자리에서 돌릴 수 없는 환경이다. 없는 결과를 만들지 않는다.
    result.row(
        label + " 재검증 실측", "exit " + str(code), "exit " + str(actual), actual == code,
    )
    if actual != code:
        result.note_short(
            label + ": 기록에는 exit " + str(code) + " 이라고 적혀 있는데 지금 그 명령을"
            " 돌리면 exit " + str(actual) + " 입니다. 적힌 숫자가 아니라 실제로 돌린"
            " 결과를 적습니다"
        )


def run(root=None, run_id=None):
    result = Result("루프 C 판정 — 정성 점검을 규율대로 3회 돌았는가")
    base = Path(root) if root else Path(__file__).resolve().parent.parent

    try:
        spec = load_spec(base)
    except ContractError as exc:
        result.note_broken(str(exc))
        return result

    quality = spec["quality_contract"]
    passes = quality.get("passes", 3)
    wanted = quality.get("rules") or []
    focus_map = quality.get("pass_focus") or {}
    watch_files = quality.get("watch_files") or []
    command = quality.get("regression_command") or ""

    page_file = (spec["page_contract"] or {}).get("output_file", "output/travel_site.html")
    if not (base / page_file).exists():
        result.note_short(
            "아직 페이지가 없습니다. 루프 B 가 끝난 뒤에 정성 점검을 시작합니다 (정상 상태)"
        )
        return result

    run_dir = latest_run_dir(base, run_id)
    if run_dir is None:
        result.note_short("evidence/runs/ 에 실행 폴더가 없습니다 (정성 점검 시작 전 정상 상태)")
        return result

    folder = run_dir / "quality"
    result.row("정성 기록 폴더", "있음", "있음" if folder.is_dir() else "없음", folder.is_dir())
    if not folder.is_dir():
        result.note_short(
            "정성 점검을 아직 시작하지 않았습니다. " + str(passes) + "회를 돌고 "
            + str(quality.get("record_dir", "quality")) + " 에 기록하세요"
        )
        return result

    previous_after = None
    last_after = None
    total_fixes = 0
    all_records = True
    for number in range(1, passes + 1):
        label = str(number) + "회차"
        path = folder / ("pass" + str(number) + ".json")
        if not path.exists():
            result.row(label, "기록 있음", "없음", False)
            result.note_short(label + " 기록이 아직 없습니다: " + path.name)
            previous_after = None
            all_records = False
            continue

        record = read_pass(path, result)
        if record is None:
            continue

        result.row(label, "기록 있음", "있음", True)

        if record.get("pass") != number:
            result.row(label + " 회차 번호", number, record.get("pass"), False)

        want_focus = focus_map.get(str(number)) or []
        have_focus = record.get("focus") or []
        same = list(have_focus) == list(want_focus)
        result.row(label + " 렌즈", "계약과 같음", "같음" if same else "다름", same)
        if not same:
            result.note_short(
                label + ": 이 회차의 렌즈가 계약과 다릅니다 (계약: " + ", ".join(want_focus) + ")"
            )

        violations = check_rules(result, label, record, wanted)
        fixes = check_fixes(result, label, record, violations)
        total_fixes += len(fixes)
        before, after = check_snapshot(result, label, record, fixes, watch_files)
        # 마지막 회차의 재검증만 실제로 다시 돌린다. 앞 회차는 그 뒤로 파일이
        # 바뀌었으므로 지금 돌려도 그때를 재는 것이 아니다.
        check_regression(result, label, record, command,
                         base=base, verify_now=(number == passes))

        if before is not None and previous_after is not None:
            chained = all(previous_after.get(f) == before.get(f) for f in watch_files)
            result.row(label + " 앞 회차와 이어짐", "같음", "같음" if chained else "끊김", chained)
            if not chained:
                result.note_short(
                    label + ": 앞 회차가 끝난 뒤 정성 점검 밖에서 파일이 바뀌었습니다"
                )
        previous_after = after
        last_after = after or last_after

    if last_after:
        now = {f: sha256_file(base / f) for f in watch_files}
        same_now = all(last_after.get(f) == now.get(f) for f in watch_files)
        result.row("마지막 회차 = 지금 파일", "같음", "같음" if same_now else "다름", same_now)
        if not same_now:
            result.note_short(
                "정성 점검이 끝난 뒤 파일이 또 바뀌었습니다. 마지막 회차를 다시 기록하세요"
            )

    # 3회를 다 돌았는데 고친 것이 0건이면 사람에게 넘긴다.
    #
    # 이 판정기는 품질에 점수를 매기지 않는다. 그런데 그 원칙 때문에
    # **"흠이 없어서 OK"** 와 **"보지 않고 OK"** 가 기록상 완전히 같은 모양이 된다.
    # 실제로 3회 내내 수정 0건으로 통과한 실행이 있었다.
    # 기계가 가를 수 없는 자리이므로 통과시키지 않고 되물음으로 보낸다.
    # (루프 킷: 사람이 "이대로 확정"을 고르면 HALT_NEEDS_HUMAN 으로 끝낸다 ·
    #  그래프 킷: human_gate_b 에서 done 을 고르면 END 로 닫힌다 — 막다른 길이 아니다)
    if all_records:
        result.row("정성 " + str(passes) + "회 총 수정", "1건 이상",
                   str(total_fixes) + "건", total_fixes >= 1)
        if total_fixes == 0:
            result.note_short(
                "정성 " + str(passes) + "회 동안 고친 것이 0건입니다. 규율 10개를"
                " 전부 OK 로 적고 넘어간 것과 정말로 흠이 없는 것을 판정기가 구분할 수"
                " 없습니다 — 사람이 확인할 자리입니다"
                " (되물음: 한 회차를 다시 돌린다 / 이대로 확정한다)"
            )

    return result


def main():
    parser = argparse.ArgumentParser(description="루프 C — 정성 점검 3회 이행 검사")
    parser.add_argument("--root", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run(args.root, args.run_id)
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print_result(result)
        if result.verdict == "SHORT":
            print(" 다음 행동: QUALITY — 남은 회차를 돌고 규율대로 기록합니다.")
            print("           규율은 specs/QUALITY_RUBRIC.md, 양식은 templates/QUALITY_PASS.md")
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
