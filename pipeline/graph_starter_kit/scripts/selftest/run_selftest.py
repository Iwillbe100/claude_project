#!/usr/bin/env python3
"""**검사기를 검사한다.** 킷 소유 — 수정 금지.

루프 킷 `specs/05_TEST_AND_VERIFIER.md` 는 이렇게 적어 두었다.

    처음부터 통과하는 검사기는 아무것도 검사하지 않는 것입니다.

그런데 그 원칙을 **산출물에만** 적용하고 검사기 자신에는 적용하지 않았다.
그래서 검사기가 조용히 약해진 것을 아무도 몰랐다. 실제로 겪은 일이다 —

    계약에 배치를 선택지 문구("우측 툴바")로 적었더니 검사행 6개가 사라졌는데
    판정은 그대로 PASS 였다. 결과물이 아니라 **검사기가 약해진** 것이다.

이 파일은 검사행마다 **그 행을 반드시 빨간불로 만드는 최소 입력**을 갖는다.
그리고 "실패했다"가 아니라 **"의도한 그 행에서 실패했다"**를 본다.
다른 이유로 실패하면 그 검사행은 여전히 죽어 있는 것이기 때문이다.

종료 코드
  0  PASS  모든 검사행이 살아 있다
  1  FAIL  죽은 검사행이 있다 — 검사기를 고쳐야 한다

사용법
  python scripts/selftest/run_selftest.py
  python scripts/selftest/run_selftest.py --keep     임시 폴더를 남긴다
  python scripts/selftest/run_selftest.py --only 툴바
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
ROOT = SCRIPTS.parent

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCRIPTS))

import world  # noqa: E402

from _contract import ContractError  # noqa: E402

import check_information_count as loop_a  # noqa: E402
import check_page_contract as loop_b  # noqa: E402
import check_quality_passes as loop_c  # noqa: E402

CHECKERS = {"count": loop_a, "page": loop_b, "quality": loop_c}
LINE = "=" * 72


# --------------------------------------------------------------------------
# 세계를 조금씩 망가뜨리는 손
# --------------------------------------------------------------------------


def edit_contract(root: Path, change):
    """계약을 고친다. 두 킷의 형식에 **둘 다** 써서 어느 로더든 같은 것을 읽게 한다."""
    path = root / "graph" / "03_CONTRACT.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    path.write_text(payload + "\n", encoding="utf-8")
    (root / "MASTER_SPEC.md").write_text(
        world.MASTER_SPEC_TEMPLATE.format(payload=payload), encoding="utf-8")


def edit_page(root: Path, change):
    path = root / "output" / "travel_site.html"
    path.write_text(change(path.read_text(encoding="utf-8")), encoding="utf-8")


def edit_research(root: Path, change):
    path = root / "output" / "research_data.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def edit_quality(root: Path, change):
    path = (root / "evidence" / "runs" / "2026-01-01T00-00-00"
            / "quality" / "pass1.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def copy_scripts(root: Path):
    """임시 폴더에서도 재검증 명령이 실제로 돌 수 있게 검사기를 복사한다."""
    target = root / "scripts"
    target.mkdir(exist_ok=True)
    for item in SCRIPTS.glob("*.py"):
        shutil.copy2(item, target / item.name)


# --------------------------------------------------------------------------
# 검사행마다 하나씩 — 이 입력은 **반드시** 그 행을 빨간불로 만들어야 한다
# --------------------------------------------------------------------------

CASES = [
    # ---- 계약이 성립하는가 (여기서 걸리면 ERROR 다. 루프를 더 돌려도 안 된다) ----
    {
        "name": "계약: 배치를 선택지 문구로 적음",
        "why": "'우측 툴바' 라고 적으면 예전에는 툴바 검사가 통째로 사라졌다",
        "checker": "page", "expect_error": "허용값이 아닙니다",
        "mutate": lambda root: edit_contract(
            root, lambda d: d["page_contract"]["feature2"].__setitem__("layout", "우측 툴바")),
    },
    {
        "name": "계약: 기준 칸을 통째로 지움",
        "why": "지우면 검사기가 자기 안의 기본값으로 조용히 되돌아갔다",
        "checker": "count", "expect_error": "칸이 없습니다",
        "mutate": lambda root: edit_contract(
            root, lambda d: d["count_contract"].pop("min_chars")),
    },
    {
        "name": "계약: 하한을 0 으로 내림",
        "why": "0 이면 무엇이든 통과한다. 검사를 끈 것과 같다",
        "checker": "count", "expect_error": "1 이상이어야",
        "mutate": lambda root: edit_contract(
            root, lambda d: d["count_contract"]["min_chars"].__setitem__("evidence_item", 0)),
    },
    {
        "name": "계약: 툴바 없는 배치인데 뒤로 가기를 요구",
        "why": "돌아갈 곳이 없는 단추를 요구하는 계약은 만들 수 없는 화면이다",
        "checker": "page", "expect_error": "back_button",
        "mutate": lambda root: edit_contract(
            root, lambda d: d["page_contract"]["feature2"].__setitem__("layout", "accordion")),
    },

    # ---- 선택지 C (툴바 없이 셋 다 아코디언) 에서만 드러나는 것 ----
    #  이 세 가지는 예전에 **전부 통과했다.** 클릭 연결 검사가 `drawer` 조건 안에
    #  묶여 있었고, 기능2 아코디언의 초기 닫힘은 아무도 보지 않았기 때문이다.
    #  루프 킷은 사람이 HTML 을 직접 쓰므로 여기서 통과하면 그대로 완성품이 된다.
    {
        "name": "선택지C 화면: 도시를 여는 코드가 없다",
        "why": "단추는 있는데 눌러도 아무 일이 없는 페이지가 만점을 받았다",
        "checker": "page", "world_layout": "accordion",
        "expect_row": "도시 단추 연결",
        "mutate": lambda root: edit_page(
            root, lambda t: t.replace("e.target.closest('button[data-city]')", "null")
                             .replace("document.querySelectorAll('[data-city-panel]')",
                                      "[]")),
    },
    {
        "name": "선택지C 화면: 관광지 상세를 여는 코드가 없다",
        "why": "같은 이유로 상세 열기 검사도 툴바 세계에서만 돌았다",
        "checker": "page", "world_layout": "accordion",
        "expect_row": "관광지 누르면 상세 열기 연결",
        "mutate": lambda root: edit_page(
            root, lambda t: t.replace("e.target.closest('button[data-spot]')", "null")
                             .replace("'[data-spot-detail=\"' + spot.getAttribute('data-spot') + '\"]'",
                                      "'#none'")),
    },
    {
        "name": "선택지C 화면: 도시 칸이 처음부터 펼쳐져 있다",
        "why": "전부 펼쳐 놓은 평면 문서가 아코디언으로 통과했다",
        "checker": "page", "world_layout": "accordion",
        "expect_row": "도시 칸 초기 닫힘",
        "mutate": lambda root: edit_page(
            root, lambda t: t.replace(".acc-panel{display:none}", ".acc-panel{display:block}")),
    },

    # ---- 루프 B: 화면의 구조 ----
    {
        "name": "화면: 우측 툴바가 없다",
        "why": "이름표만 어딘가 있으면 통과하던 자리",
        "checker": "page", "expect_row": "기능2 우측 툴바",
        "mutate": lambda root: edit_page(
            root, lambda t: t.replace('<aside id="city-drawer" hidden>', "<div>")
                             .replace("</div></aside></section>", "</div></div></section>")),
    },
    {
        "name": "화면: 툴바가 기능2 구역 밖에 있다",
        "why": "빈 껍데기를 문서 끝에 붙여 놓고 통과한 적이 있다",
        "checker": "page", "expect_row": "기능2 우측 툴바",
        "mutate": lambda root: edit_page(
            root, lambda t: t.replace('<aside id="city-drawer" hidden>', '<div hidden>')
                             .replace("</div></aside></section>", "</div></div></section>")
                             .replace("</body>", '<aside id="city-drawer" hidden></aside></body>')),
    },
    {
        "name": "화면: 관광지 단추가 툴바 밖에 있다",
        "why": "전역 검색이라 어디에 있든 통과했다",
        "checker": "page", "expect_row": "관광지 단추",
        "mutate": lambda root: edit_page(
            root, lambda t: t.replace('<button data-spot="테스트명소">테스트명소</button>', "")
                             .replace("</body>",
                                      '<button data-spot="테스트명소">테스트명소</button></body>')),
    },
    {
        "name": "화면: 전부 펼쳐져 있다 (아코디언이 아니다)",
        "why": "헤더만 얹은 목차와 아코디언을 이름표로는 구분할 수 없다",
        "checker": "page", "expect_row": "아코디언 초기 닫힘",
        "mutate": lambda root: edit_page(
            root, lambda t: t.replace(".acc-panel{display:none}", ".acc-panel{display:block}")),
    },
    {
        "name": "화면: 툴바가 처음부터 열려 있다",
        "why": "닫혀 있다가 눌러서 열리는 것이 툴바의 정의다",
        "checker": "page", "expect_row": "툴바 초기 닫힘",
        "mutate": lambda root: edit_page(
            root, lambda t: t.replace('<aside id="city-drawer" hidden>',
                                      '<aside id="city-drawer">')),
    },
    {
        "name": "화면: 관광지 상세가 처음부터 펼쳐져 있다",
        "why": "단추가 장식이 된다",
        "checker": "page", "expect_row": "관광지 상세 초기 닫힘",
        "mutate": lambda root: edit_page(
            root, lambda t: t.replace('data-spot-detail="테스트명소" hidden',
                                      'data-spot-detail="테스트명소"')),
    },
    {
        "name": "화면: 자바스크립트가 주석뿐이다",
        "why": "주석 한 줄로 동작 연결 다섯 항목이 전부 통과한 적이 있다",
        "checker": "page", "expect_row": "도시 누르면 툴바 열기 연결",
        "mutate": lambda root: edit_page(
            root, lambda t: t[:t.index("<script>")]
            + "<script>/* acc-header data-city data-spot data-back city-drawer */"
              "document.addEventListener('click', function(){});</script></body></html>"),
    },
    {
        "name": "화면: 바깥 CDN 스크립트를 건다",
        "why": "https 로 시작하면 통과시켰다. 파일 하나 계약이 깨진다",
        "checker": "page", "expect_row": "단일 HTML 파일",
        "mutate": lambda root: edit_page(
            root, lambda t: t.replace(
                "</body>", '<script src="https://cdn.example.test/x.js"></script></body>')),
    },

    # ---- 루프 A: 모은 내용 ----
    {
        "name": "수집: 조건부 칸을 checked=false 로 둔다",
        "why": "예전에는 checked 라는 **키가 있기만** 하면 통과했다",
        "checker": "count", "expect_row": "국가상태",
        "mutate": lambda root: edit_research(
            root, lambda d: d["country_intro"]["국가상태"].__setitem__("checked", False)),
    },
    {
        "name": "수집: 근거 글이 하한보다 짧다",
        "why": "분량 하한이 실제로 물리는지 본다",
        "checker": "count", "expect_row": "기능1 매력",
        "mutate": lambda root: edit_research(
            root, lambda d: d["country_intro"]["매력"]["items"][0].__setitem__("text", "짧음")),
    },
    {
        "name": "수집: 이미지 확인 기록이 없다",
        "why": "주소만 적고 열어 보지 않은 것을 잡는다",
        "checker": "count", "expect_row": "국기이미지",
        "mutate": lambda root: edit_research(
            root, lambda d: d["country_intro"]["국기이미지"]["asset"].pop("verified")),
    },

    # ---- 루프 C: 정성 절차 ----
    {
        "name": "정성: 전부 OK 로 적고 한 군데도 안 고친다",
        "why": "흠이 없어서 OK 인지 보지 않고 OK 인지 기록으로는 같다",
        "checker": "quality", "expect_row": "총 수정",
        "mutate": lambda root: edit_quality(root, _no_fixes),
    },
    {
        "name": "정성: 위반이라 적고 어디인지는 안 적는다",
        "why": "자리를 못 대면 고칠 수도, 나중에 확인할 수도 없다",
        "checker": "quality", "expect_row": "위반 위치 적음",
        "mutate": lambda root: edit_quality(root, _blank_where),
    },
    {
        "name": "정성: 재검증 종료 코드를 0 이라고 적어 둔다",
        "why": "적힌 숫자를 아무도 확인하지 않았다. 이제 직접 돌려 맞춰 본다",
        "checker": "quality", "expect_row": "재검증 실측",
        "mutate": lambda root: _fake_regression(root),
    },
]


def _no_fixes(record):
    for row in record["rules"]:
        row["verdict"] = "OK"
        row["where"] = "-"
    record["applied_fix"] = []
    record["snapshot_after"] = dict(record["snapshot_before"])


def _blank_where(record):
    for row in record["rules"]:
        if row["verdict"] == "VIOLATION":
            row["where"] = "-"


def _fake_regression(root: Path):
    """기록은 exit 0 인데 실제로 돌리면 그렇지 않은 상태를 만든다.

    감시 파일(해시)은 건드리지 않고 **계약만** 어긋나게 해서, 이 한 가지
    이유로만 재검증이 실패하게 한다.
    """
    copy_scripts(root)
    edit_contract(root, lambda d: d["count_contract"]["cities"].__setitem__("city_count", 2))


# --------------------------------------------------------------------------
# 실행
# --------------------------------------------------------------------------


def run_checker(name, root):
    """(판정, 행 목록, 오류 메시지)."""
    try:
        result = CHECKERS[name].run(str(root))
    except ContractError as exc:      # 로더 밖으로 새는 경우까지 감싼다
        return "ERROR", [], str(exc)
    return result.verdict, result.rows, " / ".join(result.broken)


def failed_rows(rows, needle):
    return [name for name, _t, _a, passed in rows if needle in name and not passed]


def check_baseline(tmp, report):
    root = tmp / "baseline"
    root.mkdir()
    world.build(root)
    for name in ("count", "page", "quality"):
        verdict, rows, broken = run_checker(name, root)
        ok = verdict == "PASS"
        report.append((ok, "기준선 " + name, "PASS" if ok else verdict + " · " + broken[:80]))

    #  ★ 선택지 C 세계도 **합격 세계여야 한다.** 이 기준선이 없으면 아래 선택지 C
    #    사례들이 "원래 통과 못 하는 세계라서 실패한 것"과 구별되지 않는다.
    root_c = tmp / "baseline_c"
    root_c.mkdir()
    world.build(root_c, "accordion")
    verdict, rows, broken = run_checker("page", root_c)
    ok = verdict == "PASS"
    report.append((ok, "기준선 page (선택지 C · 툴바 없음)",
                   "PASS" if ok else verdict + " · " + broken[:80]))


def check_case(tmp, case, index, report):
    root = tmp / ("case%02d" % index)
    root.mkdir()
    #  세계의 배치를 사례마다 고를 수 있다. 적지 않으면 툴바 세계다.
    world.build(root, case.get("world_layout", "drawer"))
    case["mutate"](root)

    verdict, rows, broken = run_checker(case["checker"], root)

    if "expect_error" in case:
        ok = verdict == "ERROR" and case["expect_error"] in broken
        detail = ("ERROR 로 잡음" if ok else
                  "기대: ERROR + '" + case["expect_error"] + "' / 실제: "
                  + verdict + " · " + (broken[:70] or "메시지 없음"))
    else:
        hits = failed_rows(rows, case["expect_row"])
        ok = bool(hits)
        detail = ("'" + hits[0] + "' 빨간불" if ok else
                  "기대: '" + case["expect_row"] + "' 행이 실패 / 실제: "
                  + verdict + " · 그 이름의 실패 행이 없음")
    report.append((ok, case["name"], detail))


def main():
    parser = argparse.ArgumentParser(description="검사기 셀프테스트")
    parser.add_argument("--keep", action="store_true", help="임시 폴더를 남긴다")
    parser.add_argument("--only", default=None, help="이름에 이 말이 든 것만 돌린다")
    args = parser.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="selftest_"))
    report = []
    try:
        if not args.only:
            check_baseline(tmp, report)
        for index, case in enumerate(CASES):
            if args.only and args.only not in case["name"]:
                continue
            check_case(tmp, case, index, report)
    finally:
        if args.keep:
            print(" 임시 폴더: " + str(tmp))
        else:
            shutil.rmtree(tmp, ignore_errors=True)

    print(LINE)
    print(" 검사기 셀프테스트 — 각 검사행이 실제로 물리는가")
    print(LINE)
    for ok, name, detail in report:
        print("  [{}] {:<40} {}".format("OK" if ok else "죽음", name[:40], detail[:60]))

    dead = [name for ok, name, _d in report if not ok]
    print("")
    if dead:
        print(" [FAIL] 죽은 검사행 " + str(len(dead)) + "곳")
        for name in dead:
            print("   - " + name)
        print("")
        print(" 이것은 결과물의 문제가 아니라 **검사기의 문제**입니다.")
        print(" 그 입력이 통과한다면, 같은 실수가 실제 실행에서도 통과합니다.")
    else:
        print(" [PASS] " + str(len(report)) + "개 항목 — 모든 검사행이 살아 있습니다.")
    print(LINE)
    return 1 if dead else 0


if __name__ == "__main__":
    sys.exit(main())
