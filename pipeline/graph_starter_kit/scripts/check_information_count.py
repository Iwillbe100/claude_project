#!/usr/bin/env python3
"""루프 A(정보량 충족 루프)의 판정기.

명세에 3개라고 적혀 있으면 실제로 3개가 저장되어 있어야 한다.

  MASTER_SPEC.md  count_contract  --+
                                    +-->  세어서 비교  -->  종료 코드
  output/research_data.json       --+

세는 것은 네 가지다.

  개수    명세한 만큼 모였는가
  분량    한 칸이 기준 글자 수를 넘는가            기준은 계약에 있다
  중복    같은 문장을 복사해 칸을 채우지 않았는가    기준은 계약에 있다
  유효    이미지 주소를 실제로 열어 본 기록이 있는가

이 스크립트는 글자 수를 직접 갖지 않는다. 전부 계약에서 읽는다.

종료 코드
  0  PASS   명세가 요구한 개수를 전부 채웠다
  1  ERROR  명세나 데이터 파일이 깨졌다 (사람이 고쳐야 한다)
  2  SHORT  아직 덜 모았다 (루프가 더 돌면 된다 = INFORMATION_INSUFFICIENT)

사용법
  python scripts/check_information_count.py
  python scripts/check_information_count.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _contract import (  # noqa: E402
    ContractError,
    Result,
    asset_problems,
    duplicate_lines,
    is_time,
    load_research,
    load_spec,
    print_result,
    rule,
    similarity,
    to_minutes,
    unique_ratio,
    use_utf8_output,
)

use_utf8_output()

# STEP 5의 D-정보량테스트가 고르는 깐깐함 등급.
#   개수만            개수만 센다
#   개수와출처        + 서로 다른 출처를 본다
#   개수와출처와분량  + 분량 · 중복 · 이미지 유효성까지 본다  (권장)
STRICTNESS = {
    "개수만":           {"sources": False, "text": False},
    "개수와출처":       {"sources": True,  "text": False},
    "개수와출처와분량": {"sources": True,  "text": True},
}
DEFAULT_STRICTNESS = "개수와출처와분량"


class Mode:
    """이번 검사에 적용할 깐깐함과 기준값. 전부 명세에서 읽어 채운다."""

    sources = True
    text = True
    min_item = 60
    min_detail = 300
    min_why_selected = 120
    min_note_line = 30
    min_block_why = 40
    unique_ratio = 0.9
    max_similarity = 0.6
    shingle = 8
    asset_rule = {}
    distinct_mode = "url"

    @classmethod
    def apply(cls, contract):
        level = STRICTNESS.get(contract.get("strictness")) or STRICTNESS[DEFAULT_STRICTNESS]
        cls.sources = level["sources"]
        cls.text = level["text"]
        # url  주소가 다르면 다른 출처로 센다 (기본값)
        # host 도메인이 다를 때만 다른 출처로 센다 (같은 사이트의 다른 페이지는 1곳)
        cls.distinct_mode = rule(contract, "distinct_source_mode", default="url")

        chars = contract.get("min_chars") or {}
        cls.min_item = rule(chars, "evidence_item", default=60)
        cls.min_detail = rule(chars, "spot_detail", default=300)
        cls.min_why_selected = rule(chars, "why_selected", default=120)
        cls.min_note_line = rule(chars, "preference_note_line", default=30)
        cls.min_block_why = rule(chars, "itinerary_block_why", default=40)

        dedup = contract.get("dedup") or {}
        cls.unique_ratio = rule(dedup, "min_unique_line_ratio", default=0.9)
        cls.max_similarity = rule(dedup, "max_pair_similarity", default=0.6)
        cls.shingle = rule(dedup, "shingle_size", default=8)

        cls.asset_rule = contract.get("asset_rule") or {}

    @classmethod
    def item_chars(cls):
        return cls.min_item if cls.text else 1


def _as_list(value):
    return value if isinstance(value, list) else []


def _as_dict(value):
    return value if isinstance(value, dict) else {}


def _items(node):
    return _as_list(_as_dict(node).get("items"))


def _valid_items(node):
    """본문이 실제로 있는 근거만 센다."""
    good = []
    for entry in _items(node):
        if not isinstance(entry, dict):
            continue
        if len((entry.get("text") or "").strip()) >= Mode.item_chars():
            good.append(entry)
    return good


def _source_key(url):
    """출처 하나를 무엇으로 셀 것인가. 계약의 distinct_source_mode 가 정한다.

      url   주소가 다르면 다른 출처   같은 사이트의 다른 페이지도 2곳으로 센다
      host  도메인이 다를 때만 다른 출처

    기본값이 url 인 이유가 있다. 루프판 기준선 데이터(루프 킷
    output/research_data.json → 그래프 킷 graph/research_data.json 으로 인계)가
    url 기준으로 모였기 때문이다. 지금 자를 host 로 바꾸면 **이미 측정해 둔
    루프판 기준선이 소급해서 무효가 된다.** 더 깐깐하게 재고 싶으면 계약에서
    host 로 바꾼다 — 스크립트가 아니라 명세가 정한다.
    """
    text = (url or "").strip()
    if Mode.distinct_mode != "host":
        return text
    body = text.split("//", 1)[-1]
    host = body.split("/", 1)[0].split("@")[-1].split(":")[0].lower()
    return host[4:] if host.startswith("www.") else host


def _distinct_sources(items):
    keys = {_source_key(i.get("source_url")) for i in items if i.get("source_url")}
    keys.discard("")
    return len(keys)


def asset_at(node, asset_key):
    """규격에 맞는 자리에서 자산을 꺼낸다. 돌려주는 것: **(자산, 규격 위반 사유)**.

    자산이 어디에 있어야 하는지는 칸마다 다르다. 화면을 그리는 쪽이 그렇게 읽기 때문이다.

        국가 소개   {"asset": {"url": …, "alt": …}}     asset_key="asset"
        관광지      {"url": …, "alt": …}                asset_key=None

    ★ 위반 사유는 그대로 못 채운 칸에 적히고 **재수집 프롬프트로 들어간다.** 그래서
      "틀렸다"가 아니라 **어떻게 고치는지**를 적는다. 모델이 읽고 바로 고칠 수 있어야
      루프가 한 바퀴에 수렴한다.
    """
    if not isinstance(node, dict):
        return None, ""                     # 아예 없는 것은 asset_problems 가 말한다
    if asset_key:
        inner = node.get(asset_key)
        if isinstance(inner, dict):
            return inner, ""
        if node.get("url") or node.get("alt"):
            return None, (asset_key + ' 칸 없이 값을 직접 넣었습니다 — {"'
                          + asset_key + '": {"url": …, "alt": …}} 로 한 겹 감싸십시오')
        return None, ""
    if isinstance(node.get("asset"), dict):
        return None, ('asset 으로 한 겹 싸여 있습니다 — 이 칸은 {"url": …, "alt": …} 를 '
                      "직접 넣습니다 (감싸면 화면에 사진이 그려지지 않습니다)")
    return node, ""


def check_slot(result, label, node, spec_rule, asset_key=None):
    """데이터 특성(kind)에 따라 다르게 센다. 이것이 이 킷의 핵심 개념이다.

    `asset_key` 는 **자산이 어느 자리에 있어야 하는가**다 (`asset_at` 참고).

    ★ 예전에는 `"asset" in node` 를 보고 **두 형태를 모두 통과**시켰다. 그래서 관광지
      이미지를 `{"asset": {...}}` 로 싸서 내도 루프 A 가 PASS 를 냈는데, 화면을 그리는
      쪽은 `image.url` 을 직접 읽으므로 사진이 안 나왔다. **루프 A 는 통과, 루프 B 는
      SHORT** — 재수집은 걸리지 않고 화면은 안 고쳐지는 교착이 실제로 났다.
      규격을 칸마다 고정해 **루프 A 에서 잡히게** 한다. 그러면 부족 문구에 도시 이름이
      앞에 붙어(`다낭/참 조각 박물관 이미지: …`) 그 도시만 재수집으로 돌아간다.
    """
    kind = spec_rule.get("kind")
    target = spec_rule.get("target", 1)

    if kind == "자산":
        asset, wrong_shape = asset_at(node, asset_key)
        if wrong_shape:
            problems = [wrong_shape]
        elif Mode.text:
            problems = asset_problems(asset, Mode.asset_rule)
        else:
            has_url = isinstance(asset, dict) and (asset.get("url") or "").strip()
            problems = [] if has_url else ["url 이 없습니다"]
        result.row(label, "살아 있는 이미지 1", "OK" if not problems else "부족", not problems)
        for message in problems[:2]:
            result.note_short(label + ": " + message)
        return

    if kind == "조건부":
        # 지금 시점에 해당 사실이 없을 수 있다. 다만 확인했다는 표시는 있어야 한다.
        #
        # 예전에는 `"checked" in node` 로 **키가 있는지만** 봤다. 그래서
        # `{"checked": false}` 도, `{"checked": null}` 도 통과했다.
        # 그건 "확인했다"가 아니라 "확인이라는 낱말을 적었다"이다.
        checked = node.get("checked") if isinstance(node, dict) else None
        if checked is not True:
            shown = "없음" if not isinstance(node, dict) or "checked" not in node \
                else repr(checked)
            result.row(label, "checked=true", shown, False)
            result.note_short(
                label + ": 확인했다면 checked 를 true 로 적습니다"
                " (해당 사항이 없어도 '확인함'은 true 입니다)")
            return
        count = len(_valid_items(node))
        result.row(label + " (없으면 0도 통과)", "확인함", str(count) + "건", True)
        return

    items = _valid_items(node)
    count = len(items)

    if kind == "단건":
        # 사실이 하나뿐인 항목. 1건 들어오면 그게 곧 충족이다.
        result.row(label + " (1건이면 충족)", 1, count, count >= 1)
    else:
        # 다건: 개수와 서로 다른 출처를 함께 본다.
        result.row(label, target, count, count >= target)
        need_sources = spec_rule.get("distinct_sources")
        if need_sources and Mode.sources:
            have = _distinct_sources(items)
            result.row(label + " · 서로 다른 출처", need_sources, have, have >= need_sources)

    if Mode.text:
        repeated = duplicate_lines([i.get("text") or "" for i in items])
        if repeated:
            result.row(label + " · 같은 근거 반복", "0건", str(len(repeated)) + "건", False)
            result.note_short(
                label + ": 같은 내용의 근거가 " + str(repeated[0][1]) + "번 들어 있습니다 — "
                + repeated[0][0][:24]
            )


def check_country_intro(result, contract, data):
    rules = contract.get("country_intro") or {}
    node = data.get("country_intro")
    if not isinstance(node, dict):
        result.note_short("기능1: country_intro 를 아직 만들지 않았습니다")
        for label, spec_rule in rules.items():
            result.row("기능1 " + label, spec_rule.get("target", 1), 0, False)
        return
    for label, spec_rule in rules.items():
        #  국가 소개의 자산 칸은 `{"asset": {...}}` 규격이다 (화면도 그렇게 읽는다).
        check_slot(result, "기능1 " + label, node.get(label), spec_rule, asset_key="asset")


def check_preference_note(result, name, note, min_lines):
    """취향 설명은 줄 수만으로는 부족하다. 줄마다 내용이 있어야 한다."""
    lines = [ln.strip() for ln in (note or "").splitlines() if ln.strip()]
    result.row(name + " · 취향 설명 줄 수", min_lines, len(lines), len(lines) >= min_lines)
    if not Mode.text or not lines:
        return

    thin = [ln for ln in lines if len(ln) < Mode.min_note_line]
    result.row(
        name + " · 취향 설명 줄당 " + str(Mode.min_note_line) + "자",
        "짧은 줄 0", len(thin), not thin,
    )
    if thin:
        result.note_short(name + " 취향 설명에 너무 짧은 줄: " + thin[0][:24])

    ratio = unique_ratio(lines)
    result.row(
        name + " · 취향 설명 고유 줄 비율",
        str(int(Mode.unique_ratio * 100)) + "%",
        str(int(ratio * 100)) + "%",
        ratio >= Mode.unique_ratio,
    )
    for text, count in duplicate_lines(lines)[:2]:
        result.note_short(
            name + " 취향 설명에 같은 문장이 " + str(count) + "번 복사되어 있습니다 — " + text[:24]
        )


def check_cross_similarity(result, what, pairs):
    """서로 다른 칸에 같은 글을 베껴 넣지 않았는가."""
    hits = []
    for i in range(len(pairs)):
        for j in range(i + 1, len(pairs)):
            score = similarity(pairs[i][1], pairs[j][1], Mode.shingle)
            if score > Mode.max_similarity:
                hits.append((pairs[i][0], pairs[j][0], score))
    result.row(what + " 서로 베낀 쌍", "0쌍", str(len(hits)) + "쌍", not hits)
    for left, right, score in hits[:3]:
        result.note_short(
            what + "이(가) 거의 같습니다 (" + str(int(score * 100)) + "%): "
            + left + " ↔ " + right
        )


def check_cities(result, contract, data):
    rules = contract.get("cities") or {}
    want_cities = rules.get("city_count", 0)
    want_spots = rules.get("spots_per_city", 0)
    spot_rule = rules.get("evidence_per_spot") or {}
    image_rule = rules.get("image_per_spot") or {}
    min_lines = rules.get("preference_note_min_lines", 0)

    cities = data.get("cities")
    if not isinstance(cities, list):
        result.row("기능2 도시 개수", want_cities, 0, False)
        return

    result.row("기능2 도시 개수", want_cities, len(cities), len(cities) >= want_cities)

    details = []   # 도시를 넘나들며 베낀 글을 잡기 위해 모은다
    notes = []

    for index, city in enumerate(cities):
        if not isinstance(city, dict):
            result.note_broken("cities[" + str(index) + "] 가 객체가 아닙니다")
            continue
        name = (city.get("name") or ("도시" + str(index + 1))).strip()

        why = (city.get("why_selected") or "").strip()
        need_why = Mode.min_why_selected if Mode.text else 1
        result.row(name + " · 선정 이유", str(need_why) + "자",
                   str(len(why)) + "자", len(why) >= need_why)

        spots = _as_list(city.get("spots"))
        result.row(name + " · 관광지 수", want_spots, len(spots), len(spots) >= want_spots)

        for spot in spots:
            if not isinstance(spot, dict):
                result.note_broken(name + " 의 관광지 항목이 객체가 아닙니다")
                continue
            spot_name = (spot.get("name") or "이름없음").strip()
            label = name + "/" + spot_name
            if spot_rule:
                check_slot(result, label + " 근거", spot, spot_rule)
            if image_rule:
                check_slot(result, label + " 이미지", spot.get("image"), image_rule)
            detail = (spot.get("detail") or "").strip()
            need_detail = Mode.min_detail if Mode.text else 1
            result.row(label + " 상세 소개", str(need_detail) + "자",
                       str(len(detail)) + "자", len(detail) >= need_detail)
            details.append((label, detail))

        note = (city.get("preference_note") or "").strip()
        check_preference_note(result, name, note, min_lines)
        notes.append((name, note))

    if Mode.text:
        check_cross_similarity(result, "관광지 상세", details)
        check_cross_similarity(result, "취향 설명", notes)


def check_day_blocks(result, label, blocks, rules, spot_names):
    """하루가 시간 단위로 이어지는가."""
    blocks_min = rules.get("blocks_per_day_min", 1)
    spot_min = rules.get("spot_blocks_per_day_min", 0)
    kinds = rules.get("block_kinds") or []

    result.row(label + " 블록 수", blocks_min, len(blocks), len(blocks) >= blocks_min)
    if not Mode.text:
        return

    spot_blocks = 0
    last_end = None
    bad_time = 0
    for block in blocks:
        if not isinstance(block, dict):
            result.note_broken(label + " 의 블록이 객체가 아닙니다")
            continue
        start = (block.get("start") or "").strip()
        end = (block.get("end") or "").strip()
        if not (is_time(start) and is_time(end)):
            bad_time += 1
            result.note_short(label + ": 시간이 HH:MM 이 아닙니다 (" + start + "~" + end + ")")
            continue
        s, e = to_minutes(start), to_minutes(end)
        if e <= s:
            bad_time += 1
            result.note_short(label + ": 끝 시각이 시작보다 빠릅니다 (" + start + "~" + end + ")")
        elif last_end is not None and s < last_end:
            bad_time += 1
            result.note_short(label + ": 앞 블록과 시간이 겹칩니다 (" + start + " 시작)")
        last_end = max(last_end or 0, e)

        kind = (block.get("kind") or "").strip()
        if kinds and kind not in kinds:
            result.note_short(label + ": 블록 종류가 " + (kind or "비어 있음")
                              + " 입니다 (허용: " + ", ".join(kinds) + ")")
        if kind == "명소":
            spot_blocks += 1
            spot = (block.get("spot") or "").strip()
            if spot and spot not in spot_names:
                result.note_short(
                    label + ": " + spot + " 은(는) 이 도시에서 조사한 관광지가 아닙니다"
                )
            elif not spot:
                result.note_short(label + ": 명소 블록에 관광지 이름이 없습니다")

        why = (block.get("why") or "").strip()
        if len(why) < Mode.min_block_why:
            result.note_short(label + ": 블록에 왜 넣었는지가 "
                              + str(Mode.min_block_why) + "자 미만입니다")

    result.row(label + " 시간 형식", "어긋남 0", bad_time, bad_time == 0)
    if spot_min:
        result.row(label + " 명소 블록", spot_min, spot_blocks, spot_blocks >= spot_min)


def check_itinerary(result, contract, data, fallback_days=0):
    """일정은 도시마다 따로 완결되어야 한다.

    이 페이지는 며칠을 어떻게 돌까가 아니라 어느 도시로 갈까를 돕는다.
    그래서 도시마다 여행 일수만큼의 일정이 각각 있어야 한다.
    도시들을 합쳐서 세면 한 도시에 몰아 넣은 일정도 통과해 버린다.
    """
    rules = contract.get("itinerary") or {}
    evidence_rule = rules.get("evidence_per_city") or {}
    # 계약에 값이 없으면 여행 일수로 되돌아간다. 0 이면 무엇이든 통과해 버리기 때문이다.
    days_needed = rules.get("days_per_city") or fallback_days
    cities = _as_list(data.get("cities"))

    whys = []
    for city in cities:
        if not isinstance(city, dict):
            continue
        name = (city.get("name") or "도시").strip()
        plan = _as_dict(city.get("itinerary"))
        if evidence_rule:
            check_slot(result, "기능3 " + name + " 일정 근거", plan, evidence_rule)

        days = _as_list(plan.get("days"))
        result.row("기능3 " + name + " 일정 일수", days_needed, len(days),
                   len(days) >= days_needed)

        numbers = [d.get("day") for d in days if isinstance(d, dict)]
        missing = [n for n in range(1, days_needed + 1) if n not in numbers]
        if missing:
            result.note_short("기능3 " + name + ": " + str(missing[:5]) + "일차가 비어 있습니다")

        spot_names = set()
        for spot in _as_list(city.get("spots")):
            if isinstance(spot, dict) and spot.get("name"):
                spot_names.add(spot["name"].strip())

        texts = []
        for day in days:
            if not isinstance(day, dict):
                result.note_broken(name + " 일정의 하루 항목이 객체가 아닙니다")
                continue
            blocks = _as_list(day.get("blocks"))
            label = "기능3 " + name + " " + str(day.get("day")) + "일차"
            check_day_blocks(result, label, blocks, rules, spot_names)
            for block in blocks:
                if isinstance(block, dict):
                    texts.append(block.get("why") or "")
        whys.append((name, "\n".join(texts)))

    if Mode.text and len(whys) > 1:
        check_cross_similarity(result, "도시별 일정", whys)


def run(root=None):
    result = Result("루프 A 판정 — 정보량이 명세한 개수만큼 모였는가")
    try:
        spec = load_spec(root)
        data = load_research(root)
    except ContractError as exc:
        result.note_broken(str(exc))
        return result

    if data is None:
        result.note_short("output/research_data.json 이 아직 없습니다 (수집 전 정상 상태)")
        return result
    if not isinstance(data, dict):
        result.note_broken("output/research_data.json 의 최상위가 객체가 아닙니다")
        return result

    contract = spec["count_contract"]
    Mode.apply(contract)

    check_country_intro(result, contract, data)
    check_cities(result, contract, data)
    check_itinerary(result, contract, data, spec["request"].get("days", 0))
    return result


def main():
    parser = argparse.ArgumentParser(description="루프 A — 정보량 충족 검사")
    parser.add_argument("--root", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run(args.root)
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print_result(result)
        if result.verdict == "SHORT":
            print(" 다음 행동: RESEARCH — 위에서 부족으로 표시된 곳만 다시 모읍니다.")
            print("           전부 다시 하지 않습니다.")
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
