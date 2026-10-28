#!/usr/bin/env python3
"""최종 검증 명령 — 루프의 종료 스위치.

루프는 셋이다. 순서가 정해져 있다.

  루프 A  정보량 충족      정보를 명세한 개수만큼 모았는가
     |    (먼저 끝나야 함)
     v
  루프 B  페이지 완성      그 정보로 페이지 구성안을 채웠는가
     |    (먼저 끝나야 함)
     v
  루프 C  정성 완성도      규율 10가지로 3회 점검하고 고쳤는가

앞 루프가 끝나기 전에는 뒤 루프를 보지 않는다.
없는 정보로 페이지를 만들면 껍데기만 나오고,
껍데기를 놓고 정성을 따지면 3회를 거기서 다 쓴다.

  --skip-quality   루프 C 안에서 쓰는 재검증 모드.
                   정성 수정이 루프 A/B 를 깨뜨렸는지만 본다.
                   (루프 C 가 자기 자신을 검사하는 순환을 막는다)

종료 코드
  0  SUCCESS  세 루프 모두 통과
  1  ERROR    명세나 파일이 깨졌다 (사람이 고쳐야 한다)
  2  SHORT    아직 덜 됐다 (루프가 더 돌면 된다)

사용법
  python scripts/verify_all.py
  python scripts/verify_all.py --skip-quality
  python scripts/verify_all.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_information_count as loop_a  # noqa: E402
import check_page_contract as loop_b  # noqa: E402
import check_quality_passes as loop_c  # noqa: E402
from _contract import print_result, use_utf8_output  # noqa: E402

use_utf8_output()

LINE = "=" * 66


def main():
    parser = argparse.ArgumentParser(description="최종 검증 — 루프 A와 B와 C")
    parser.add_argument("--root", default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--skip-quality", action="store_true",
        help="루프 C 를 보지 않는다. 정성 회차 중 되돌아감을 확인할 때 쓴다",
    )
    args = parser.parse_args()

    result_a = loop_a.run(args.root)
    result_b = None
    result_c = None

    if result_a.verdict == "PASS":
        result_b = loop_b.run(args.root)
        if result_b.verdict == "PASS" and not args.skip_quality:
            result_c = loop_c.run(args.root)

    if args.json:
        payload = {
            "loop_a": result_a.to_dict(),
            "loop_b": result_b.to_dict() if result_b else None,
            "loop_c": result_c.to_dict() if result_c else None,
            "skip_quality": args.skip_quality,
            "verdict": _verdict(result_a, result_b, result_c, args.skip_quality),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return _code(result_a, result_b, result_c, args.skip_quality)

    print_result(result_a, show_rows=(result_a.verdict != "PASS"))
    print("")

    if result_b is None:
        _skipped("루프 B 판정 — 건너뜀",
                 "루프 A(정보량)가 아직 끝나지 않았습니다.",
                 "없는 정보로 페이지를 만들면 껍데기만 나오므로 루프 B는 보지 않습니다.",
                 "먼저 할 일: 위 루프 A 판정을 통과시킵니다 (부족이면 부족한 곳만 다시 모읍니다).")
    else:
        print_result(result_b, show_rows=(result_b.verdict != "PASS"))
    print("")

    if args.skip_quality:
        _skipped("루프 C 판정 — 건너뜀 (--skip-quality)",
                 "정성 회차 중의 되돌아감 확인 모드입니다.",
                 "루프 A와 B가 여전히 통과하는지만 보았습니다.",
                 "이 결과를 passN.json 의 verify_after 에 적습니다.")
    elif result_c is None:
        _skipped("루프 C 판정 — 건너뜀",
                 "루프 B(페이지)가 아직 끝나지 않았습니다.",
                 "껍데기를 놓고 정성을 따지면 3회를 거기서 다 씁니다.",
                 "먼저 할 일: 루프 B 판정을 통과시킵니다 (부족이면 부족한 칸만 고칩니다).")
    else:
        print_result(result_c, show_rows=(result_c.verdict != "PASS"))

    print("")
    verdict = _verdict(result_a, result_b, result_c, args.skip_quality)
    print(LINE)
    print(" 최종 판정: " + verdict)
    print(LINE)
    if verdict == "SUCCESS":
        if args.skip_quality:
            print(" 루프 A 통과 · 루프 B 통과 (루프 C는 보지 않음)")
            print(" 다음: 이 종료 코드를 이번 정성 회차 기록에 남깁니다.")
        else:
            print(" 루프 A 통과 · 루프 B 통과 · 루프 C 통과")
            print(" 다음: 사람이 output/travel_site.html 을 브라우저로 열어 확인합니다.")
    elif verdict == "ERROR":
        broken = " ".join(
            result_a.broken
            + (result_b.broken if result_b else [])
            + (result_c.broken if result_c else [])
        )
        if "채우지 않은 값" in broken or "채워지지 않았습니다" in broken:
            print(" 아직 명세가 끝나지 않았습니다. 깨진 것이 아닙니다.")
            print(" 다음: STEP 7까지 끝내고 python scripts/check_loop_readiness.py 로 READY를 확인하세요.")
        else:
            print(" 파일이나 명세가 깨졌습니다. 루프를 더 돌려도 해결되지 않습니다.")
            print(" 다음: HITL — 사람에게 넘깁니다.")
    else:
        which = _which(result_a, result_b, result_c)
        print(" " + which + "가 아직 기준에 못 미칩니다.")
        print(" 다음: 위 목록에서 부족으로 표시된 곳만 고칩니다.")
    print(LINE)
    return _code(result_a, result_b, result_c, args.skip_quality)


def _skipped(title, *lines):
    print(LINE)
    print(" " + title)
    print(LINE)
    for line in lines:
        print(" " + line)
    print(LINE)


def _which(result_a, result_b, result_c):
    if result_a.verdict != "PASS":
        return "루프 A"
    if result_b is None or result_b.verdict != "PASS":
        return "루프 B"
    return "루프 C"


def _verdict(result_a, result_b, result_c, skip_quality=False):
    parts = [result_a, result_b] + ([] if skip_quality else [result_c])
    if any(p is not None and p.verdict == "ERROR" for p in parts):
        return "ERROR"
    if any(p is None or p.verdict != "PASS" for p in parts):
        return "SHORT"
    return "SUCCESS"


def _code(result_a, result_b, result_c, skip_quality=False):
    return {"SUCCESS": 0, "ERROR": 1, "SHORT": 2}[
        _verdict(result_a, result_b, result_c, skip_quality)
    ]


if __name__ == "__main__":
    sys.exit(main())
