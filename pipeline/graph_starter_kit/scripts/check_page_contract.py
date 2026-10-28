#!/usr/bin/env python3
"""루프 B(페이지 완성 루프)의 판정기.

STEP 2에서 그린 페이지 구성안이 실제 HTML 안에 그대로 들어갔는지 본다.
그리고 루프 A가 모은 내용이 실제로 화면에 쓰였는지 대조한다.

  MASTER_SPEC.md  page_contract   --+
  output/research_data.json       --+-->  대조  -->  종료 코드
  output/travel_site.html         --+

검사 강도는 명세의 page_contract.strictness 가 정한다.

  요소존재  필요한 칸이 있는가
  동작연결  클릭하면 열리고 닫히는 연결이 있는가   (요소존재 포함)
  내용대조  모은 내용이 실제로 그 칸에 들어갔는가   (동작연결 포함)

이 스크립트도 글자 수를 직접 갖지 않는다.
아코디언 한 칸의 최소 분량은 **계약에서 계산한다** —
"그 헤더에 들어갈 근거 개수 x 근거 1건의 최소 글자 수".
그래서 D-소개근거수를 올리면 화면 검사도 저절로 깐깐해진다.

종료 코드
  0  PASS   페이지 구성안을 전부 만족했다
  1  ERROR  명세나 HTML이 깨졌다 (사람이 고쳐야 한다)
  2  SHORT  아직 덜 만들었다 (루프가 더 돌면 된다)

사용법
  python scripts/check_page_contract.py
  python scripts/check_page_contract.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _contract import (  # noqa: E402
    TIME_RANGE_RE,
    ContractError,
    Result,
    duplicate_lines,
    load_research,
    load_spec,
    print_result,
    rule,
    unique_ratio,
    use_utf8_output,
)

use_utf8_output()

VOID_TAGS = {"img", "br", "hr", "input", "meta", "link", "source", "area", "col"}
SKIP_TEXT_TAGS = {"script", "style"}

# 속성값을 감싸는 따옴표. 큰따옴표와 작은따옴표를 모두 허용한다.
QUOTE_CHARS = "[" + chr(34) + chr(39) + "]"

# 이런 말이 남아 있으면 아직 채우다 만 것이다.
PLACEHOLDERS = ["(미정)", "(미작성)", "TODO", "lorem ipsum", "placeholder", "준비 중"]


# --------------------------------------------------------------------------
# 아주 작은 HTML 읽기 도구
# --------------------------------------------------------------------------


class Node:
    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = attrs
        self.children = []
        self.text_parts = []

    def text(self):
        if self.tag in SKIP_TEXT_TAGS:
            return ""
        parts = list(self.text_parts)
        for child in self.children:
            piece = child.text()
            if piece:
                parts.append(piece)
        return " ".join(parts)

    def descendants(self):
        for child in self.children:
            yield child
            for deeper in child.descendants():
                yield deeper


class Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {})
        self.stack = [self.root]
        self.nodes = []

    def _open(self, tag, attrs, self_closing):
        node = Node(tag, {k: (v if v is not None else "") for k, v in attrs})
        self.stack[-1].children.append(node)
        self.nodes.append(node)
        if not self_closing and tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_starttag(self, tag, attrs):
        self._open(tag, attrs, False)

    def handle_startendtag(self, tag, attrs):
        self._open(tag, attrs, True)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        if data.strip():
            self.stack[-1].text_parts.append(data.strip())


def parse_html(text):
    builder = Builder()
    builder.feed(text)
    builder.close()
    return builder


def find(nodes, tag=None, **attrs):
    out = []
    for node in nodes:
        if tag and node.tag != tag:
            continue
        ok = True
        for key, want in attrs.items():
            key = key.replace("_", "-")
            have = node.attrs.get(key)
            if want is True:
                if have is None:
                    ok = False
                    break
            elif have != want:
                ok = False
                break
        if ok:
            out.append(node)
    return out


def first(nodes, tag=None, **attrs):
    found = find(nodes, tag, **attrs)
    return found[0] if found else None


def has_class(node, name):
    return name in (node.attrs.get("class") or "").split()


def lines_of(node):
    """한 칸 안의 <p> 와 <li> 를 줄로 본다."""
    return [
        child.text().strip() for child in node.descendants()
        if child.tag in ("p", "li") and child.text().strip()
    ]


# --------------------------------------------------------------------------
# 처음에 닫혀 있는가 · 코드가 실제로 그 이름표를 찾는가
#
# 이 두 가지가 없으면 "이름표가 있는가"만 보게 된다. 실제로 그래서
# **전부 펼쳐진 평면 문서에 빈 껍데기 <div id="city-drawer"> 하나**가
# 만점으로 통과한 적이 있다. 아래 도우미들이 그 구멍을 메운다.
# --------------------------------------------------------------------------

#: 이번 판정에서 쓰는 화면 정보. run() 이 시작할 때 채운다.
#: (검사기는 한 번에 하나만 돈다. verify_all 도 순서대로 부른다)
_SCREEN = {"hidden_classes": set()}

_CSS_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")

# 주석은 코드가 아니다. 다만 `https://` 의 `//` 까지 지우면 멀쩡한 코드가 사라지므로
# 앞 글자가 `:` 나 `/` 이면 주석으로 보지 않는다.
_JS_LINE_COMMENT = re.compile(r"(?<![:/])//[^\n]*")
_JS_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)

#: 이름표가 **DOM 질의 안에서** 쓰였는지 보기 위한 앞머리.
#: 문자열이 파일 어딘가에 있는 것과, 그 요소를 실제로 찾는 것은 다르다.
_QUERY = (r"(?:closest|querySelector(?:All)?|getElementById"
          r"|getElementsBy\w+|getAttribute|matches|dataset)")


def hidden_classes(text):
    """단일 파일 안의 <style> 에서 '기본이 닫힘'인 클래스 이름을 모은다.

    아코디언 패널은 hidden 속성이 아니라 CSS 클래스로 닫아 두는 것이 보통이다.
    속성만 보면 정상인 화면을 "열려 있다"고 잘못 잡는다.
    `.acc-panel.open{display:block}` 처럼 여는 규칙은 본문에 display:none 이
    없으므로 저절로 걸러진다.
    """
    css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", text, re.DOTALL | re.I))
    found = set()
    for selector, body in _CSS_RULE_RE.findall(css):
        flat = body.replace(" ", "").lower()
        if "display:none" not in flat and "visibility:hidden" not in flat:
            continue
        found.update(re.findall(r"\.([A-Za-z_][\w-]*)", selector))
    return found


def is_closed(node):
    """이 칸이 처음에 닫혀 있는가. 열고 닫는 배치의 최소 증거다."""
    if node is None:
        return False
    if "hidden" in node.attrs:
        return True
    style = (node.attrs.get("style") or "").replace(" ", "").lower()
    if "display:none" in style or "visibility:hidden" in style:
        return True
    names = (node.attrs.get("class") or "").split()
    return any(name in _SCREEN["hidden_classes"] for name in names)


def closed_count(nodes):
    return sum(1 for node in nodes if is_closed(node))


def script_code(text):
    """<script> 안의 코드만 모으고 **주석을 지운다.**

    지우지 않으면 `/* acc-header data-city data-spot data-back */` 한 줄로
    동작 연결 검사가 전부 통과한다. 실제로 그렇게 통과한 적이 있다.
    문자열 리터럴은 지우지 않는다 — `getElementById('city-drawer')` 처럼
    선택자 자체가 문자열이기 때문이다.
    """
    code = "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", text, re.DOTALL | re.I))
    code = _JS_BLOCK_COMMENT.sub(" ", code)
    return _JS_LINE_COMMENT.sub(" ", code)


def query_uses(code, needle):
    """그 이름표가 DOM 질의 안에서 쓰였는가. 뒤에 글자가 이어지면 다른 이름표다."""
    pattern = _QUERY + r"\s*\([^)]{0,160}?" + re.escape(needle) + r"(?![\w-])"
    return re.search(pattern, code) is not None


# --------------------------------------------------------------------------
# 화면 칸의 최소 분량을 계약에서 계산한다
# --------------------------------------------------------------------------


class Limits:
    """검사기가 숫자를 갖지 않기 위한 계산기.

    아코디언 한 칸에 들어갈 글이 몇 자여야 하는지를 스크립트가 정하면,
    D-소개근거수를 올려도 화면 검사는 그대로다. 그래서 계약에서 계산한다.
    """

    def __init__(self, spec):
        counts = spec["count_contract"]
        page = spec["page_contract"]
        self.intro = counts.get("country_intro") or {}
        self.header_slots = (page.get("feature1") or {}).get("header_slots") or {}
        self.item_min = rule(counts, "min_chars", "evidence_item", default=60)
        self.detail_min = rule(counts, "min_chars", "spot_detail", default=300)
        self.note_line_min = rule(counts, "min_chars", "preference_note_line", default=30)
        self.floor = rule(page, "min_chars", "panel_floor", default=60)
        self.conditional = rule(page, "min_chars", "conditional_slot_chars", default=20)
        self.unique_ratio = rule(counts, "dedup", "min_unique_line_ratio", default=0.9)
        self.banned = rule(counts, "asset_rule", "banned_url_substrings", default=[])
        self.itinerary = counts.get("itinerary") or {}
        # 계약에 값이 없으면 여행 일수로 되돌아간다. 0 이면 무엇이든 통과해 버리기 때문이다.
        self.days_per_city = (self.itinerary.get("days_per_city")
                              or (spec.get("request") or {}).get("days") or 0)

    def panel(self, header):
        """이 헤더의 칸이 담아야 할 최소 글자 수."""
        total = 0
        for slot in self.header_slots.get(header, [header]):
            spec_rule = self.intro.get(slot) or {}
            kind = spec_rule.get("kind")
            if kind == "자산":
                continue
            if kind == "조건부":
                total += self.conditional
            else:
                total += (spec_rule.get("target") or 1) * self.item_min
        return max(self.floor, total)


# --------------------------------------------------------------------------
# 배치 종류별 검사 (아코디언 / 툴바 / 탭)
# --------------------------------------------------------------------------


def check_accordion(result, nodes, area, keys, level, limits=None):
    """헤더를 누르면 아래가 펼쳐지는 배치.

    패널이 **처음에 닫혀 있는지**까지 본다. 전부 펼쳐 놓고 헤더만 얹으면
    아코디언이 아니라 그냥 목차다. 이름표만으로는 그 둘을 구분할 수 없다.
    """
    panels = []
    for key in keys:
        header = None
        panel = None
        for node in nodes:
            if node.attrs.get("data-acc") != area or node.attrs.get("data-key") != key:
                continue
            if node.tag == "button" or has_class(node, "acc-header"):
                header = node
            elif has_class(node, "acc-panel"):
                panel = node
        result.row(area + " 헤더 [" + key + "]", "있음", "있음" if header else "없음", bool(header))
        result.row(area + " 패널 [" + key + "]", "있음", "있음" if panel else "없음", bool(panel))
        if panel is not None:
            panels.append(panel)
        if panel and level >= 3 and limits is not None:
            need = limits.panel(key)
            length = len(panel.text())
            result.row(
                area + " 패널 내용 [" + key + "]",
                str(need) + "자", str(length) + "자", length >= need,
            )

    if panels and level >= 2:
        closed = closed_count(panels)
        result.row(area + " 아코디언 초기 닫힘", len(panels), closed, closed == len(panels))
        if closed != len(panels):
            result.note_short(
                area + ": 아코디언 패널 " + str(len(panels) - closed) + "칸이 처음부터"
                " 펼쳐져 있습니다. hidden 속성 · style=\"display:none\" · CSS 클래스"
                " 중 하나로 닫아 두고 헤더 클릭으로 엽니다"
            )


def check_tabs(result, nodes, area, keys, level, limits=None):
    """옆으로 늘어선 단추를 누르면 내용이 바뀌는 배치.

    탭은 **한 칸만 보인다.** 전부 보이면 탭이 아니라 그냥 나열이다.
    """
    panels = []
    for key in keys:
        button = first(nodes, "button", data_tab=key)
        panel = first(nodes, data_tab_panel=key)
        result.row(area + " 탭 단추 [" + key + "]", "있음", "있음" if button else "없음", bool(button))
        result.row(area + " 탭 내용 [" + key + "]", "있음", "있음" if panel else "없음", bool(panel))
        if panel is not None:
            panels.append(panel)
        if panel and level >= 3 and limits is not None:
            need = limits.panel(key)
            length = len(panel.text())
            result.row(
                area + " 탭 내용 길이 [" + key + "]",
                str(need) + "자", str(length) + "자", length >= need,
            )

    if len(panels) > 1 and level >= 2:
        closed = closed_count(panels)
        need = len(panels) - 1
        result.row(area + " 탭 한 칸만 보임", str(need) + "칸 닫힘", closed, closed >= need)
        if closed < need:
            result.note_short(
                area + ": 탭 내용이 " + str(len(panels) - closed) + "칸 동시에 보입니다."
                " 한 칸만 남기고 닫아 둡니다"
            )


def area_panel(nodes, area, key, layout):
    """그 구역, 그 키의 내용 칸 하나를 찾는다 (도시별로 범위를 좁히기 위해)."""
    if layout == "tabs":
        return first(nodes, data_tab_panel=key)
    for node in nodes:
        if node.attrs.get("data-acc") == area and node.attrs.get("data-key") == key \
                and has_class(node, "acc-panel"):
            return node
    return None


# --------------------------------------------------------------------------
# 기능별 검사
# --------------------------------------------------------------------------


def image_ok(result, label, node, limits, level, expect_url=None):
    """이미지는 있는가만 보지 않는다. 주소 형태와 모은 주소와의 일치까지 본다."""
    src = (node.attrs.get("src") or "").strip() if node else ""
    alt = (node.attrs.get("alt") or "").strip() if node else ""
    ok = bool(src and alt)
    result.row(label, "주소+대체문구", "있음" if ok else "없음", ok)
    if not ok or level < 3:
        return
    for banned in limits.banned:
        if banned and banned in src:
            result.row(label + " 주소 형태", "허용", "금지형", False)
            result.note_short(label + ": 손으로 만들 수 없는 주소 형태입니다 (" + banned + ")")
            break
    if expect_url and not (expect_url in src or src in expect_url):
        result.row(label + " 주소 일치", "같음", "다름", False)
        result.note_short(label + ": 모은 주소와 화면의 주소가 다릅니다")


def check_feature1(result, nodes, rules, level, limits, intro_assets):
    section = first(nodes, "section", id="feature1")
    result.row("기능1 구역", "있음", "있음" if section else "없음", bool(section))
    if not section:
        return

    if rules.get("flag_image"):
        image_ok(result, "기능1 국기 이미지(좌측 상단)", first(nodes, "img", data_role="flag"),
                 limits, level, intro_assets.get("국기이미지"))
    if rules.get("hero_image"):
        image_ok(result, "기능1 대표 이미지(우측 상단)", first(nodes, "img", data_role="hero"),
                 limits, level, intro_assets.get("대표이미지"))

    keys = rules.get("headers") or []
    if rules.get("layout") == "tabs":
        check_tabs(result, nodes, "feature1", keys, level, limits)
    else:
        check_accordion(result, nodes, "feature1", keys, level, limits)


def check_note_quality(result, name, note, limits):
    """취향 설명은 줄 수만 세면 같은 문장을 복사해 채운다."""
    lines = lines_of(note)
    thin = [ln for ln in lines if len(ln) < limits.note_line_min]
    result.row("취향 설명 짧은 줄 [" + name + "]", "0줄", len(thin), not thin)
    ratio = unique_ratio(lines)
    result.row(
        "취향 설명 고유 줄 [" + name + "]",
        str(int(limits.unique_ratio * 100)) + "%",
        str(int(ratio * 100)) + "%",
        ratio >= limits.unique_ratio,
    )
    for text, count in duplicate_lines(lines)[:2]:
        result.note_short(
            "취향 설명 [" + name + "]에 같은 문장이 " + str(count)
            + "번 복사되어 있습니다 — " + text[:24]
        )


def check_feature2(result, nodes, rules, level, cities, limits):
    """도시와 관광지. **어디에 있는가**까지 본다.

    예전에는 이름표를 화면 전체에서 찾았다. 그래서 툴바 밖에 흩어 놓아도,
    아니 툴바가 빈 껍데기여도 통과했다. 기능3이 이미 "도시 칸 안으로 범위를
    좁혀서" 세고 있었는데 기능2만 그러지 않았다 — 그 불일치를 없앤다.

      도시 단추    여는 쪽이므로 툴바 **밖**(계약) — 검사는 기능2 구역 안까지만
      도시 칸      열리는 쪽이므로 툴바 **안**
      관광지·상세·취향 설명·뒤로 가기   전부 툴바 **안**
    """
    section = first(nodes, "section", id="feature2")
    result.row("기능2 구역", "있음", "있음" if section else "없음", bool(section))
    if not section:
        return

    inside = list(section.descendants())
    trigger_scope = inside      # 단추가 있어야 하는 범위
    panel_scope = inside        # 내용이 있어야 하는 범위
    where = ""

    if rules.get("layout") == "drawer":
        drawer = first(inside, "aside", id="city-drawer")
        result.row("기능2 우측 툴바 (구역 안 aside)", "있음",
                   "있음" if drawer else "없음", bool(drawer))
        if drawer is None:
            result.note_short(
                "우측 툴바가 없습니다. <aside id=\"city-drawer\"> 를"
                " <section id=\"feature2\"> 안에 둡니다"
            )
        else:
            panel_scope = list(drawer.descendants())
            where = " (툴바 안)"
            if level >= 2:
                closed = is_closed(drawer)
                result.row("툴바 초기 닫힘", "닫힘", "닫힘" if closed else "열림", closed)
                if not closed:
                    result.note_short(
                        "우측 툴바가 처음부터 열려 있습니다. 닫아 두고 도시 단추로 엽니다"
                    )

    min_lines = rules.get("preference_note_min_lines", 0)
    details = []
    city_panels = []

    for city in cities:
        name = city["name"]
        button = first(trigger_scope, "button", data_city=name)
        result.row("도시 단추 [" + name + "]", "있음", "있음" if button else "없음", bool(button))
        panel = first(panel_scope, data_city_panel=name)
        result.row("도시 칸 [" + name + "]" + where, "있음",
                   "있음" if panel else "없음", bool(panel))
        if panel is not None:
            city_panels.append(panel)

        for spot in city["spots"]:
            spot_name = spot["name"]
            spot_button = first(panel_scope, "button", data_spot=spot_name)
            result.row(
                "관광지 단추 [" + spot_name + "]" + where, "있음",
                "있음" if spot_button else "없음", bool(spot_button),
            )
            if rules.get("spot_images"):
                image_ok(result, "관광지 사진 [" + spot_name + "]",
                         first(panel_scope, "img", data_spot_image=spot_name),
                         limits, level, spot.get("image_url"))
            if rules.get("spot_detail"):
                detail = first(panel_scope, data_spot_detail=spot_name)
                if detail is not None:
                    details.append(detail)
                length = len(detail.text()) if detail else 0
                need = limits.detail_min if level >= 3 else 1
                result.row(
                    "관광지 상세 [" + spot_name + "]",
                    (str(need) + "자") if level >= 3 else "있음",
                    str(length) + "자",
                    length >= need,
                )

        note = first(panel_scope, data_preference_note=name)
        if note is None:
            result.row("취향 설명 [" + name + "]" + where, str(min_lines) + "줄", "없음", False)
        else:
            lines = lines_of(note)
            result.row(
                "취향 설명 줄 수 [" + name + "]", min_lines, len(lines), len(lines) >= min_lines,
            )
            if level >= 3 and lines:
                check_note_quality(result, name, note, limits)

    # 상세는 눌러야 열린다. 처음부터 다 펼쳐져 있으면 단추가 장식이다.
    if details and level >= 2:
        closed = closed_count(details)
        result.row("관광지 상세 초기 닫힘", len(details), closed, closed == len(details))
        if closed != len(details):
            result.note_short(
                "관광지 상세 " + str(len(details) - closed) + "칸이 처음부터 펼쳐져"
                " 있습니다. 닫아 두고 관광지 단추로 엽니다"
            )

    #  ★ 툴바가 아니면 **도시 칸 자체가** 열고 닫히는 칸이다. 툴바일 때는 툴바 하나가
    #    닫혀 있으면 되고 그것은 위에서 이미 봤다. 아코디언일 때 이 검사가 없어서,
    #    도시 칸을 전부 펼쳐 놓은 평면 문서가 아코디언으로 통과했다 — 기능1·기능3 은
    #    `check_accordion` 이 같은 것을 보는데 기능2 만 아무도 보지 않았다.
    if city_panels and level >= 2 and rules.get("layout") != "drawer":
        closed = closed_count(city_panels)
        result.row("도시 칸 초기 닫힘", len(city_panels), closed, closed == len(city_panels))
        if closed != len(city_panels):
            result.note_short(
                "도시 칸 " + str(len(city_panels) - closed) + "칸이 처음부터 펼쳐져"
                " 있습니다. hidden 속성 · style=\"display:none\" · CSS 클래스 중"
                " 하나로 닫아 두고 도시 단추로 엽니다"
            )

    if rules.get("back_button"):
        backs = find(panel_scope, "button", data_back=True)
        result.row("뒤로 가기 단추" + where, "1개 이상", len(backs), len(backs) >= 1)


def check_feature3(result, nodes, rules, level, cities, limits):
    """일정은 도시마다 따로 완결되어야 한다.

    전체 일자 수를 한 번에 세면 한 도시에 몰아 넣은 일정도 통과한다.
    이 페이지는 며칠을 어떻게 돌까가 아니라 어느 도시로 갈까를 돕는 것이므로
    도시 칸 안으로 범위를 좁혀 도시마다 센다.
    """
    section = first(nodes, "section", id="feature3")
    result.row("기능3 구역", "있음", "있음" if section else "없음", bool(section))
    if not section:
        return

    layout = rules.get("layout")
    keys = [c["name"] for c in cities]
    if layout == "tabs":
        check_tabs(result, nodes, "feature3", keys, level, None)
    else:
        check_accordion(result, nodes, "feature3", keys, level, None)

    days_needed = limits.days_per_city
    blocks_min = limits.itinerary.get("blocks_per_day_min", 1)

    for name in keys:
        panel = area_panel(nodes, "feature3", name, layout)
        if panel is None:
            result.row("일자별 칸 [" + name + "]", days_needed, "칸 없음", False)
            continue
        days = [n for n in panel.descendants() if n.attrs.get("data-day") is not None]
        result.row("일자별 칸 [" + name + "]", days_needed, len(days), len(days) >= days_needed)

        if level < 3:
            continue
        for day in days:
            label = "시간 블록 [" + name + " " + (day.attrs.get("data-day") or "?") + "일차]"
            blocks = [n for n in day.descendants() if n.attrs.get("data-block") is not None]
            result.row(label, blocks_min, len(blocks), len(blocks) >= blocks_min)
            bad = [b for b in blocks
                   if not TIME_RANGE_RE.search(b.attrs.get("data-block") or "")]
            if bad:
                result.row(label + " 형식", "HH:MM-HH:MM", "어긋남 " + str(len(bad)), False)
                result.note_short(
                    label + ": data-block 값이 HH:MM-HH:MM 이 아닙니다 ("
                    + (bad[0].attrs.get("data-block") or "빈 값") + ")"
                )


def check_behaviour(result, text, rules_list):
    """클릭하면 열리고 닫히는 연결이 **코드로** 있는가.

    예전에는 script 본문에 이름표 글자가 들어 있기만 하면 통과였다.
    그래서 `/* acc-header data-city data-spot data-back */` 주석 한 줄로
    다섯 항목이 전부 OK 가 됐다. 지금은 두 가지를 더 본다.

      주석을 지운다              주석은 코드가 아니다
      DOM 질의 안에서 쓰였는가    문자열이 어딘가 있는 것과 그 요소를 찾는 것은 다르다
    """
    code = script_code(text)
    if not code.strip():
        result.note_short("화면을 움직이는 script 블록이 없습니다 (주석만으로는 안 됩니다)")
        return

    #: (검사 이름, 이 중 하나라도 DOM 질의 안에서 쓰이면 통과)
    needs = []
    layouts = {r.get("layout") for r in rules_list}
    if "accordion" in layouts:
        needs.append(("아코디언 열고 닫기", ["acc-header", "acc-panel"]))
    if "tabs" in layouts:
        needs.append(("탭 바꾸기", ["data-tab", "data-tab-panel"]))

    #  ★ 도시를 눌러 열고 관광지를 눌러 상세를 여는 것은 **배치와 무관한 약속**이다.
    #    예전에는 이 두 줄이 `drawer` 조건 안에 있었다. 그래서 기능2를 아코디언으로
    #    고르면 검사가 통째로 사라져, 도시·관광지를 여는 코드가 **하나도 없어도**
    #    통과했다 — 단추는 있는데 눌러도 아무 일이 없는 페이지가 만점을 받았다.
    #    요소가 있는가(위 check_feature2)와 눌러서 열리는가(여기)는 다른 검사다.
    needs.append(("도시 단추", ["data-city", "data-city-panel"]))
    if any(r.get("spot_detail") for r in rules_list):
        needs.append(("관광지 누르면 상세 열기", ["data-spot", "data-spot-detail"]))

    #  툴바와 뒤로 가기는 계약이 그렇게 정했을 때만 본다. 뒤로 가기는 배치가 아니라
    #  `back_button` 이 정한다 — 툴바 없이 뒤로 가기를 요구하면 계약 단계에서 막힌다.
    if "drawer" in layouts:
        needs.append(("도시 누르면 툴바 열기", ["city-drawer"]))
    if any(r.get("back_button") for r in rules_list):
        needs.append(("뒤로 가기", ["data-back"]))

    has_click = "addEventListener" in code and "click" in code
    result.row("클릭 연결 코드", "있음", "있음" if has_click else "없음", has_click)
    if not has_click:
        result.note_short("addEventListener 로 click 을 받는 코드가 없습니다")

    for label, needles in needs:
        found = any(query_uses(code, needle) for needle in needles)
        result.row(label + " 연결", "있음", "있음" if found else "없음", found)
        if not found:
            result.note_short(
                label + ": " + " 또는 ".join(needles) + " 를 querySelector · closest ·"
                " getElementById 같은 DOM 질의로 찾는 코드가 없습니다"
                " (문자열만 적어 두는 것으로는 통과하지 않습니다)"
            )


def check_content_match(result, text, cities, sources):
    """루프 A가 모은 내용이 실제로 화면에 쓰였는가. 껍데기 통과를 막는 검사다."""
    lowered = text.lower()
    for word in PLACEHOLDERS:
        if word.lower() in lowered:
            result.note_short("아직 채우다 만 표시가 남아 있습니다: " + word)

    for city in cities:
        if city["name"] not in text:
            result.note_short("도시 이름이 화면에 없습니다: " + city["name"])
        for spot in city["spots"]:
            if spot["name"] not in text:
                result.note_short("관광지 이름이 화면에 없습니다: " + spot["name"])

    missing = [url for url in sources if url and url not in text]
    result.row(
        "모은 출처가 화면에 걸림", len(sources), len(sources) - len(missing), not missing,
    )
    for url in missing[:5]:
        result.note_short("출처 링크가 화면에 없습니다: " + url)


# --------------------------------------------------------------------------
# 실행
# --------------------------------------------------------------------------


def _as_list(value):
    return value if isinstance(value, list) else []


def _as_dict(value):
    return value if isinstance(value, dict) else {}


def collect_from_research(data):
    """검사에 필요한 최소 정보만 뽑는다."""
    cities = []
    sources = []
    intro_assets = {}

    def take(node):
        for item in _as_list(_as_dict(node).get("items")):
            if isinstance(item, dict) and item.get("source_url"):
                sources.append(item["source_url"].strip())

    for name, slot in _as_dict(data.get("country_intro")).items():
        take(slot)
        asset = _as_dict(_as_dict(slot).get("asset"))
        if asset.get("url"):
            intro_assets[name] = asset["url"].strip()

    for city in _as_list(data.get("cities")):
        if not isinstance(city, dict) or not city.get("name"):
            continue
        spots = []
        for spot in _as_list(city.get("spots")):
            if not isinstance(spot, dict) or not spot.get("name"):
                continue
            take(spot)
            image = _as_dict(spot.get("image"))
            spots.append({
                "name": spot["name"].strip(),
                "image_url": (image.get("url") or "").strip(),
            })
        take(city.get("itinerary"))
        cities.append({"name": city["name"].strip(), "spots": spots})

    seen = []
    for url in sources:
        if url not in seen:
            seen.append(url)
    return cities, seen, intro_assets


LEVELS = {"요소존재": 1, "동작연결": 2, "내용대조": 3}


def run(root=None):
    result = Result("루프 B 판정 — 페이지 구성안대로 만들어졌는가")
    try:
        spec = load_spec(root)
        data = load_research(root)
    except ContractError as exc:
        result.note_broken(str(exc))
        return result

    page = spec["page_contract"]
    level = LEVELS.get(page.get("strictness"), 3)
    limits = Limits(spec)

    base = Path(root) if root else Path(__file__).resolve().parent.parent
    target = base / page.get("output_file", "output/travel_site.html")
    if not target.exists():
        result.note_short(target.name + " 이 아직 없습니다 (페이지 생성 전 정상 상태)")
        return result

    text = target.read_text(encoding="utf-8", errors="replace")
    # 이 화면에서 '기본이 닫힘'인 클래스를 먼저 모은다. 아래 검사들이 이것을 본다.
    _SCREEN["hidden_classes"] = hidden_classes(text)

    if page.get("single_file", True):
        # 바깥 주소든 상대 경로든 **바깥 파일은 바깥 파일이다.**
        # 예전에는 https:// 로 시작하는 script 를 통과시켰다. CDN 한 줄이면
        # 화면이 인터넷에 기대게 되고 그 순간 "파일 하나" 계약이 깨진다.
        outside_css = re.findall(
            "<link[^>]+rel\\s*=\\s*" + QUOTE_CHARS + "?stylesheet", text, re.I)
        outside_js = re.findall(r"<script[^>]*\ssrc\s*=", text, re.I)
        result.row("단일 HTML 파일", "외부 파일 0", len(outside_css) + len(outside_js),
                   not outside_css and not outside_js)
        for tag in (outside_css + outside_js)[:2]:
            result.note_short("바깥 파일을 참조합니다: " + tag.strip()[:60])

    if data is None:
        result.note_short("output/research_data.json 이 없어 내용 대조를 할 수 없습니다")
        cities, sources, intro_assets = [], [], {}
    else:
        cities, sources, intro_assets = collect_from_research(data)

    tree = parse_html(text)
    nodes = tree.nodes

    f1 = page.get("feature1") or {}
    f2 = page.get("feature2") or {}
    f3 = page.get("feature3") or {}

    check_feature1(result, nodes, f1, level, limits, intro_assets)
    check_feature2(result, nodes, f2, level, cities, limits)
    check_feature3(result, nodes, f3, level, cities, limits)

    if level >= 2:
        check_behaviour(result, text, [f1, f2, f3])
    if level >= 3 and cities:
        check_content_match(result, text, cities, sources)

    return result


def main():
    parser = argparse.ArgumentParser(description="루프 B — 페이지 구성안 충족 검사")
    parser.add_argument("--root", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run(args.root)
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print_result(result)
        if result.verdict == "SHORT":
            print(" 다음 행동: RETRY — 위에서 부족으로 표시된 칸만 고칩니다.")
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
