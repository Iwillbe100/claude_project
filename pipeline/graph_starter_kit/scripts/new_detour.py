#!/usr/bin/env python3
"""새 처방 가지의 **세 조각**을 한 번에 만든다. STEP 6 에서 쓴다. **킷 소유.**

    python scripts/new_detour.py <이름> --loop A --title "사진 설명이 영어로 나옴"
    python scripts/new_detour.py <이름> --loop B --title "…" --dry-run      무엇이 생기는지만 본다

만드는 것 (이름이 곧 자리다)

    travel_graph/detours/registry.py        한 줄 추가     무엇을 · 어느 루프에서
    travel_graph/detours/<이름>.py          고치는 법       fix() · inject()  — 빈 틀
    scripts/detour_tests/test_<이름>.py     시험지          run()             — 빈 틀

만든 직후에도 그래프는 **그대로 돈다.** 빈 시험지는 늘 합격이라 진단이 이 처방 가지를
고르지 않고, 빈 fix 는 아무것도 바꾸지 않는다. 그다음 순서가 STEP 6 이다.

    1  시험지를 먼저 채운다    실패를 재현하고(--inject) 불합격이 나는지 본다 ← 빨간불 먼저
    2  고치는 법을 채운다      같은 시험지가 합격을 내는지 본다               ← 초록불
    3  그래프를 다시 돌린다    Studio 에서 새 가지에 불이 들어오는지 본다

★ 노드는 **이 명령으로만** 늘린다. 루프 골격 14개 · 진단 2개는 그대로다.
  `check_graph_shape.py` 11번 검사(처방 가지 계약)가 그 약속을 확인한다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from _contract import use_utf8_output  # noqa: E402

use_utf8_output()

REGISTRY = ROOT / "travel_graph" / "detours" / "registry.py"
MODULE_TEMPLATE = ROOT / "travel_graph" / "detours" / "_template.py"
TEST_TEMPLATE = ROOT / "scripts" / "detour_tests" / "_template_test.py.tmpl"
LINE = "=" * 66


def main() -> int:
    parser = argparse.ArgumentParser(description="새 처방 가지의 세 조각을 만든다")
    parser.add_argument("kind", help="영문 소문자 · 숫자 · 밑줄. 노드 이름이 됩니다 (fix_<이름> · test_<이름>)")
    parser.add_argument("--loop", required=True, choices=["A", "B"],
                        help="A = 정보량(check_information 뒤) · B = 페이지(check_page 뒤)")
    parser.add_argument("--title", required=True, help="게이트 화면에 뜨는 한국어 이름")
    parser.add_argument("--dry-run", action="store_true", help="파일을 만들지 않고 보여 주기만")
    args = parser.parse_args()

    from travel_graph import detours

    #  제목은 코드 속 문자열로 들어간다. 따옴표 · 역슬래시 · 줄바꿈은 빼거나 바꾼다
    #  (역슬래시 하나가 registry.py 를 깨뜨려 그래프 전체가 안 뜬다).
    kind = args.kind.strip()
    title = re.sub(r"[\\\r\n\t]+", " ", args.title).replace('"', "'").strip()
    problems = []
    if not re.match(r"^[a-z][a-z0-9_]*$", kind):
        problems.append("이름은 영문 소문자로 시작하고 소문자 · 숫자 · 밑줄만 씁니다")
    if kind in detours.RESERVED:
        problems.append(f"'{kind}' 는 라우터가 이미 쓰는 이름입니다")
    if detours.get(kind) is not None:
        problems.append(f"'{kind}' 는 이미 등록돼 있습니다")
    module_path = REGISTRY.parent / (kind + ".py")
    test_path = TEST_TEMPLATE.parent / ("test_" + kind + ".py")
    for path in (module_path, test_path):
        if path.exists():
            problems.append(f"{path.relative_to(ROOT).as_posix()} 이 이미 있습니다")
    if not title:
        problems.append("--title 이 비어 있습니다")
    if problems:
        print(LINE)
        print(" 새 처방 가지를 만들지 못했습니다")
        print(LINE)
        for item in problems:
            print("  x " + item)
        return 1

    fill = {
        "{KIND}": kind, "{TITLE}": title, "{LOOP}": args.loop,
        "{DIAGNOSE}": "diagnose_info" if args.loop == "A" else "diagnose_page",
        "{TARGET}": "output/research_data.json" if args.loop == "A" else "output/travel_site.html",
        "{READER}": "read_research" if args.loop == "A" else "read_html",
        "{READ_VAR}": "data" if args.loop == "A" else "html",
    }

    def render(template: Path) -> str:
        text = template.read_text(encoding="utf-8")
        for key, value in fill.items():
            text = text.replace(key, value)
        return text

    module_text = render(MODULE_TEMPLATE)
    if args.loop == "B":
        #  ★ 루프 B 는 **국가 소개**에서 실패를 재현한다. replay 의 루프 A 재수집이 도시를 인계본 통째로
        #    되돌리므로, 도시에서 재현한 실패는 루프 B 에 닿기 전에 지워진다 (image_spec 과 같은 이유).
        module_text = module_text.replace(
            'INJECT_AT = "city"                  # "city"(첫 도시) 또는 "country"(국가 소개)',
            'INJECT_AT = "country"               # 루프 B 는 국가 소개에서 재현한다 — 도시에서 재현하면 루프 A 재수집이 지운다')
    module_text = module_text.replace(
        "★ 이 파일은 `python scripts/new_detour.py` 가 복사해 쓰는 **틀**이다. 직접 등록하지 않는다.\n"
        f"  복사본은 `travel_graph/detours/<kind>.py` 가 되고, `{kind}` 같은 자리가 채워진다.\n\n", "")
    test_text = render(TEST_TEMPLATE).replace(
        "★ 이 파일은 `python scripts/new_detour.py` 가 복사해 쓰는 **틀**이다. 직접 쓰지 않는다.\n\n", "")
    entry = ('    {"kind": ' + json.dumps(kind) + ', "loop": ' + json.dumps(args.loop)
             + ', "title": ' + json.dumps(title, ensure_ascii=False) + '},\n')

    registry = REGISTRY.read_text(encoding="utf-8")
    marker = "DETOURS = ("
    start = registry.find(marker)
    close = registry.find("\n)", start)
    if start < 0 or close < 0:
        print(" x registry.py 에서 DETOURS = ( … ) 를 찾지 못했습니다. 손으로 한 줄 추가하십시오:")
        print("   " + entry.strip())
        return 1
    head = registry[:close].rstrip()
    if head and head[-1] not in ",(":
        head += ","                                     # 앞줄에 쉼표가 없으면 붙인다
    new_registry = head + "\n" + entry + registry[close + 1:]

    print(LINE)
    print(f" 새 처방 가지 — {kind} (루프 {args.loop}) · {title}" + ("   [미리 보기]" if args.dry_run else ""))
    print(LINE)
    print(f"  + {REGISTRY.relative_to(ROOT).as_posix()}   {entry.strip()}")
    print(f"  + {module_path.relative_to(ROOT).as_posix()}")
    print(f"  + {test_path.relative_to(ROOT).as_posix()}")
    print(f"  = 그래프에 노드 두 개가 생깁니다: fix_{kind} · test_{kind}")
    home = "check_information" if args.loop == "A" else "check_page"
    gate = "human_gate_a" if args.loop == "A" else "human_gate_b"
    print(f"    {fill['{DIAGNOSE}']} ─{kind}→ fix_{kind} → test_{kind}")
    print(f"        합격 → {home} (검사기로 복귀) · 불합격 → 한 번 더 · 한도 → {gate}")
    if args.dry_run:
        print(LINE)
        return 0

    module_path.write_text(module_text, encoding="utf-8")
    test_path.write_text(test_text, encoding="utf-8")
    REGISTRY.write_text(new_registry, encoding="utf-8")

    print(LINE)
    print(" 다음 순서 (STEP 6)")
    print(f"  0  python scripts/check_graph_shape.py            11번 처방 가지 계약이 OK 인지")
    print(f"  1  {test_path.relative_to(ROOT).as_posix()} 의 TODO 를 채운다   ← 시험지 먼저")
    print(f"     {module_path.relative_to(ROOT).as_posix()} 의 inject() 로 그 실패를 재현하고")
    auto = "--auto stop" if args.loop == "A" else "--auto proceed"
    print(f"     python scripts/run_once.py --mode replay --inject {kind} {auto}")
    print(f"        → 진단이 {kind} 를 고르고 test FAIL · 한 번 더 · 게이트에서 멈춘다 (빨간불)")
    print(f"  2  {module_path.relative_to(ROOT).as_posix()} 의 fix() 를 채운다")
    print(f"     같은 명령으로 test_{kind} 가 PASS · 검사기로 복귀하는지 본다 (초록불)")
    print(f"  3  python scripts/selftest/run_graph_regression.py   기존 경로가 안 깨졌는지")
    print(f"     python scripts/run_once.py --mode replay {auto}   inject 없이 — '처방 가지 : 타지 않음' (오탐 없음)")
    print(LINE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
