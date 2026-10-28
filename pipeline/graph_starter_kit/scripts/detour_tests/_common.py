"""처방 가지 시험지 공용 도구. **킷 소유.**

시험지는 이 파일과 `scripts/_contract.py` 만 쓴다. **고치는 코드(`travel_graph/`)를
import 하지 않는다** — 고치는 쪽이 채점표를 만들면 자기 오해를 스스로 통과시킨다.
(검사기와 같은 규칙이다. CLAUDE.md 6절)

시험지 한 장의 모양

    def run(root=None) -> Result      # 검사기와 같은 Result — verdict · short
    if __name__ == "__main__":
        sys.exit(main_for(run))       # 혼자서도 돈다:  python scripts/detour_tests/test_<kind>.py

    종료 코드  0 합격(PASS) · 2 불합격(SHORT, 증상이 있다) · 1 깨짐(ERROR)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _contract import (  # noqa: E402
    Result,
    asset_problems,
    load_contract_json,
    print_result,
    use_utf8_output,
)

RESEARCH = "output/research_data.json"
HTML = "output/travel_site.html"

#: 주소가 들어 있는 칸 이름. 이 칸은 '글'이 아니라 '주소'로 본다.
URL_KEYS = ("url", "source_url")

#: 증상 줄을 몇 개까지 적나. 나머지는 개수만 적는다 (게이트 화면이 목록에 묻히지 않게).
SHOW = 12


def root_of(root) -> Path:
    return Path(root) if root else ROOT


def read_research(root):
    """`(data, 문제문장)`. 파일이 없거나 UTF-8 이 아니거나 JSON 이 아니면 문장을 돌려준다."""
    path = root_of(root) / RESEARCH
    if not path.exists():
        return None, RESEARCH + " 이 없습니다 (check_information 이 먼저 돌아야 합니다)"
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        return None, (RESEARCH + " 이 UTF-8 로 읽히지 않습니다 ("
                      + str(exc.start) + "번째 바이트) — 다른 코드페이지로 저장됐습니다")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, RESEARCH + " 이 JSON 이 아닙니다 (" + str(exc.lineno) + "번째 줄)"
    if not isinstance(data, dict):
        return None, RESEARCH + " 의 맨 바깥이 {…} 가 아닙니다"
    return data, ""


def read_html(root):
    path = root_of(root) / HTML
    if not path.exists():
        return None, HTML + " 이 없습니다 (build_page 가 먼저 돌아야 합니다)"
    try:
        return path.read_bytes().decode("utf-8-sig"), ""
    except UnicodeDecodeError as exc:
        return None, HTML + " 이 UTF-8 로 읽히지 않습니다 (" + str(exc.start) + "번째 바이트)"


def asset_rule(root) -> dict:
    try:
        spec = load_contract_json(root_of(root))
    except Exception:                                           # noqa: BLE001
        return {}
    return ((spec or {}).get("count_contract") or {}).get("asset_rule") or {}


def _part(node, key):
    """경로 한 조각을 사람이 읽는 이름으로. 이름이 있는 항목은 이름으로 부른다."""
    if isinstance(key, int):
        if isinstance(node, dict) and str(node.get("name") or "").strip():
            return str(node["name"]).strip()
        return "[" + str(key) + "]"
    return str(key)


def label_of(parts) -> str:
    """`("cities","하노이","spots","문묘","items","[0]","text")` → `하노이/문묘/items[0]/text`"""
    out = []
    for piece in parts:
        if piece in ("cities", "spots"):
            continue
        if piece == "country_intro":
            out.append("국가 소개")
            continue
        if piece.startswith("[") and out:
            out[-1] += piece
            continue
        out.append(piece)
    return "/".join(out)


def walk_strings(node, parts=()):
    """모든 문자열 칸을 `(사람용 경로, 칸 이름, 값)` 으로 내놓는다."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key.startswith("_"):
                continue                                        # _comment 같은 설명 칸
            yield from walk_strings(value, parts + (str(key),))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk_strings(value, parts + (_part(value, index),))
    elif isinstance(node, str):
        yield label_of(parts), (parts[-1] if parts else ""), node


def assets(data):
    """이미지 자리를 전부 `(이름표, 자산 dict)` 로 내놓는다. 검사기와 같은 자리를 본다.

        국가 소개   country_intro[<칸>]["asset"]     (국기이미지 · 대표이미지)
        관광지      cities[i].spots[j]["image"]
    """
    intro = data.get("country_intro") if isinstance(data.get("country_intro"), dict) else {}
    for slot, node in intro.items():
        if isinstance(node, dict) and isinstance(node.get("asset"), dict):
            yield "국가 소개/" + str(slot), node["asset"]
    for city in data.get("cities") or []:
        if not isinstance(city, dict):
            continue
        for spot in city.get("spots") or []:
            if isinstance(spot, dict) and isinstance(spot.get("image"), dict):
                yield (str(city.get("name") or "?") + "/" + str(spot.get("name") or "?")
                       + " 이미지"), spot["image"]


def finish(result, summary: str, lines: list) -> None:
    """요약 한 줄 + 증상 줄들. 증상이 없으면 요약 줄만 통과로 남는다."""
    result.row(summary, 0, len(lines), not lines)
    for line in lines[:SHOW]:
        result.note_short(line)
    if len(lines) > SHOW:
        result.note_short("… 외 " + str(len(lines) - SHOW) + "곳")


def main_for(run) -> int:
    use_utf8_output()
    parser = argparse.ArgumentParser(description=(run.__doc__ or "").strip().splitlines()[0]
                                     if run.__doc__ else "처방 가지 시험지")
    parser.add_argument("--root", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run(args.root)
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print_result(result)
    return result.exit_code


__all__ = ["Result", "asset_problems", "root_of", "read_research", "read_html", "asset_rule",
           "walk_strings", "assets", "finish", "main_for", "URL_KEYS", "SHOW"]
