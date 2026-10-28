#!/usr/bin/env python3
"""최종 검증 스위치. **킷 소유 — 수정 금지.**

네 개를 **순서대로** 본다. 앞이 깨지면 뒤를 보지 않는다.

  1  구조     check_graph_shape.py       그래프가 애초에 성립하는가   ← 그래프 킷 신규
  2  정보량   check_information_count.py 명세한 개수만큼 모였는가     ← 루프 킷과 동일
  3  페이지   check_page_contract.py     화면 칸을 빠짐없이 채웠는가  ← 루프 킷과 동일
  4  정성     check_quality_passes.py    규율 10가지로 3회 점검했는가 ← 루프 킷과 동일

2·3·4번은 루프 킷 파일과 **바이트 단위로 같다.** 그래서 루프판과 그래프판의 숫자를
같은 표에 올릴 수 있다. 이것이 이 실습의 결론이다.

처방 가지 시험지(`scripts/detour_tests/test_*.py`)는 **여기에 넣지 않는다.** 그것은 그래프
안에서 "그 문제가 사라졌나"를 보는 종이고, 여기는 루프판과 **같은 자**로 재는 자리다.
처방 가지가 고친 결과도 결국 이 네 검사기를 통과해야 한다 — 처방 가지가 합격하면 루프 골격의
검사기로 돌아오는 이유가 그것이다. (1번 구조 검사는 처방 가지 계약까지 본다 · 검사행 12개)

  --skip-quality   `quality_pass` 노드가 회차 끝에 부르는 재검증 모드.
                   정성 수정이 구조·루프 A·B 를 깨뜨렸는지만 본다.
                   (루프 C 가 자기 자신을 검사하는 순환을 막는다)

종료 코드
  0  SUCCESS  넷 다 통과
  1  ERROR    구조나 명세가 깨졌다 — 사람이 고쳐야 한다
  2  SHORT    아직 덜 됐다 — 그래프가 더 돌거나 사람이 게이트에서 정해야 한다

사용법
  python scripts/verify_all.py
  python scripts/verify_all.py --skip-quality
  python scripts/verify_all.py --json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _contract import print_result, use_utf8_output  # noqa: E402

use_utf8_output()

ROOT = Path(__file__).resolve().parent.parent
LINE = "=" * 66

STAGES = [
    ("구조", "check_graph_shape", "그래프가 애초에 성립하는가", "그래프 킷 신규"),
    ("정보량", "check_information_count", "명세한 개수만큼 모였는가", "루프 킷과 동일"),
    ("페이지", "check_page_contract", "화면 칸을 빠짐없이 채웠는가", "루프 킷과 동일"),
    ("정성", "check_quality_passes", "규율 10가지로 3회 점검했는가", "루프 킷과 동일"),
]

#: `--skip-quality` 로 건너뛰는 단계.
QUALITY_STAGE = "check_quality_passes"


def load(name: str):
    spec = importlib.util.spec_from_file_location("stage_" + name, ROOT / "scripts" / (name + ".py"))
    if spec is None or spec.loader is None:
        raise RuntimeError("검사기를 불러오지 못했습니다: " + name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description="최종 검증 — 구조 → 정보량 → 페이지 → 정성")
    parser.add_argument("--root", default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--quiet", action="store_true", help="표를 접고 판정만 본다")
    parser.add_argument(
        "--skip-quality", action="store_true",
        help="루프 C 를 보지 않는다. 정성 회차 안에서 되돌아감을 확인할 때 쓴다",
    )
    parser.add_argument(
        "--continue-on-error", action="store_true",
        help="앞 단계가 깨져도 나머지를 마저 본다 (진단용. 최종 판정은 그대로다)",
    )
    args = parser.parse_args()

    root = args.root or str(ROOT)
    report = {"stages": [], "skip_quality": args.skip_quality, "verdict": "PASS"}

    for label, module_name, what, origin in STAGES:
        if args.skip_quality and module_name == QUALITY_STAGE:
            report["stages"].append({
                "stage": label, "checker": module_name + ".py", "origin": origin,
                "verdict": "SKIPPED", "short": [], "broken": [],
            })
            if not args.json:
                print("")
                print(LINE)
                print(f" [{label}] 건너뜀 (--skip-quality)")
                print(LINE)
                print(" 정성 회차 안에서 부르는 재검증 모드입니다.")
                print(" 구조·루프 A·B 가 여전히 통과하는지만 보았습니다.")
                print(" 이 종료 코드를 passN.json 의 verify_after 에 적습니다.")
            continue

        result = load(module_name).run(root)
        report["stages"].append({
            "stage": label, "checker": module_name + ".py", "origin": origin,
            "verdict": result.verdict, "short": result.short, "broken": result.broken,
        })
        if not args.json:
            print("")
            print(LINE)
            print(f" [{label}] {what}   ({module_name}.py · {origin})")
            print(LINE)
            print_result(result, show_rows=not args.quiet)
        # 앞이 깨지면 뒤를 보지 않는 것이 기본이다 — 없는 정보로 만든 화면에
        # 정성을 따지면 3회를 거기서 다 쓴다. 다만 **왜 깨졌는지 찾을 때**는
        # 한 번에 다 보는 편이 빠르므로 진단 스위치를 둔다. 최종 판정은 같다.
        if result.verdict == "ERROR":
            report["verdict"] = "ERROR"
            if not args.continue_on_error:
                break
        elif result.verdict == "SHORT":
            if report["verdict"] != "ERROR":
                report["verdict"] = "SHORT"
            if not args.continue_on_error:
                break

    code = {"PASS": 0, "ERROR": 1, "SHORT": 2}[report["verdict"]]
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return code

    print("")
    print(LINE)
    status = {"PASS": "SUCCESS", "ERROR": "ERROR", "SHORT": "SHORT"}[report["verdict"]]
    print(f" 최종: {status}   (exit {code})")
    print(LINE)
    if report["verdict"] == "PASS":
        if args.skip_quality:
            print(" 구조 · 루프 A · 루프 B 통과 (루프 C는 보지 않음).")
            print(" 다음: 이 종료 코드를 이번 정성 회차 기록에 남깁니다.")
        else:
            print(" 루프판과 **같은 검사기**로 통과했습니다. 이제 두 판의 숫자를 비교하십시오.")
            print("   루프판 기준선 = graph/04_RUN_EVIDENCE.md 의 「루프판 기준선」 절"
                  " (킷 예시본 6번 · 직접 뽑은 인계본 8번)")
    elif report["verdict"] == "SHORT":
        print(" 아직 덜 됐습니다. 그래프를 더 돌리거나 게이트에서 방향을 정하십시오.")
        print(" 정성 단계가 SHORT 면 남은 회차를 돌리면 됩니다 (3회 고정).")
    else:
        print(" 구조나 명세가 깨졌습니다. 그래프를 더 돌려도 해결되지 않습니다.")
    return code


if __name__ == "__main__":
    sys.exit(main())
