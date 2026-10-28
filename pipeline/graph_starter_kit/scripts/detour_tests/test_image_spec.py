#!/usr/bin/env python3
"""처방 가지 시험지 — 사진이 화면 규격에 안 맞음. **킷 소유.**

**진단(`diagnose_page`)도 이 시험지로 하고, 합격(`test_image_spec`)도 이 시험지로 판정한다.**

보는 것 — `output/travel_site.html` (사람이 브라우저로 보는 바로 그 파일)

    S1  사진을 화면용 크기로 받는가   Special:FilePath 주소에 width= 가 있고 1280 이하인가
                                    없으면 **원본을 통째로** 받는다 (한 장에 수~수십 MB)
    S2  사진 틀이 정해져 있는가       관광지 사진(.spot-img)은 비율(aspect-ratio)과
                                    자르기(object-fit)를, 국기(.flag) · 대표 사진(.hero)은
                                    높이 상한(max-height)을 갖는가
                                    없으면 세로 사진 한 장이 서랍을 뚫고 길어진다
    S3  사진이 가려져 있지 않은가     사진 class 가 display:none · visibility:hidden 이 아닌가

★ 루프 골격의 검사기(`check_page_contract.py`)는 사진이 **있는가**(src · alt · 주소 일치)만
  본다. 크기 · 틀 · 가려짐은 보지 않는다. 그래서 판정이 PASS 여도 이 시험지는 불합격일
  수 있다. 교육생이 실제로 적어 낸 말이 이것이었다 — *"이미지 규격이 안 맞음"*.

종료 코드  0 합격 · 2 불합격(증상 있음) · 1 깨짐
사용법     python scripts/detour_tests/test_image_spec.py
"""
from __future__ import annotations

import re
import sys
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import Result, finish, main_for, read_html  # noqa: E402

#: 화면용으로 받는 사진의 최대 폭. 계약의 권장 형태는 `?width=1024` 다.
MAX_WIDTH = 1280

#: 사진 class 마다 CSS 에 있어야 하는 속성. **하나라도 있으면** 그 조건은 통과다.
FRAME_RULES = {
    "spot-img": (("aspect-ratio",), ("object-fit",)),
    "flag": (("max-height",),),
    "hero": (("max-height",),),
}

_CSS_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")


class _Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.images = []
        self.css = []
        self._in_style = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "img":
            self.images.append(attrs)
        elif tag == "style":
            self._in_style = True

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "style":
            self._in_style = False

    def handle_data(self, data):
        if self._in_style:
            self.css.append(data)


def _label(attrs: dict) -> str:
    if attrs.get("data-spot-image"):
        return "관광지 사진 [" + attrs["data-spot-image"] + "]"
    role = attrs.get("data-role") or ""
    return {"flag": "국기", "hero": "대표 사진"}.get(role, "사진 (" + (attrs.get("class") or "?") + ")")


def width_of(src: str):
    """Special:FilePath 주소의 width 값. 없으면 None, 숫자가 아니면 -1."""
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(src).query)
    values = query.get("width") or []
    if not values:
        return None
    try:
        return int(values[0])
    except ValueError:
        return -1


def css_rules(css_text: str) -> list:
    """`[(선택자, {속성: 값})]` — 평평하게 읽는다 (@media 안쪽도 같은 규칙으로 본다)."""
    rules = []
    for selector, body in _CSS_RULE.findall(css_text):
        props = {}
        for decl in body.split(";"):
            if ":" in decl:
                name, value = decl.split(":", 1)
                props[name.strip().lower()] = value.strip().lower()
        rules.append((selector.strip(), props))
    return rules


def _has_class(selector: str, cls: str) -> bool:
    return re.search(r"\." + re.escape(cls) + r"(?![\w-])", selector) is not None


def run(root=None) -> Result:
    """처방 가지 시험지 — 사진 화면 규격 (크기 · 틀 · 가려짐)"""
    result = Result("처방 가지 시험지 — 사진 화면 규격 (test_image_spec)")
    html, problem = read_html(root)
    if html is None:
        result.note_broken(problem)
        return result
    page = _Page()
    page.feed(html)
    rules = css_rules("\n".join(page.css))

    # S1 — 원본 크기로 받는 사진
    heavy = []
    for attrs in page.images:
        src = (attrs.get("src") or "").strip()
        if "Special:FilePath" not in src:
            continue                                            # 폭을 붙일 수 없는 주소는 보지 않는다
        width = width_of(src)
        if width is None:
            heavy.append(_label(attrs) + ": 주소에 width 가 없습니다 — 원본을 통째로 받습니다")
        elif width < 1 or width > MAX_WIDTH:
            heavy.append(_label(attrs) + f": width={width} — 화면용은 {MAX_WIDTH} 이하입니다")
    finish(result, "S1 원본 크기로 받는 사진", heavy)

    # S2 — 사진 틀
    used = {cls for attrs in page.images for cls in (attrs.get("class") or "").split()}
    loose = []
    for cls, needs in FRAME_RULES.items():
        if cls not in used:
            continue
        props = {}
        for selector, body in rules:
            if _has_class(selector, cls):
                props.update(body)
        for options in needs:
            if not any(name in props for name in options):
                loose.append(f".{cls}: CSS 에 {' 또는 '.join(options)} 가 없습니다 — 사진 틀이 없습니다")
    finish(result, "S2 틀이 없는 사진", loose)

    # S3 — 가려진 사진
    hidden = []
    for selector, body in rules:
        if body.get("display") == "none" or body.get("visibility") == "hidden":
            for cls in used:
                if _has_class(selector, cls) and not re.search(r"\[hidden\]|:not", selector):
                    hidden.append(f".{cls}: '{selector[:40]}' 가 사진을 가립니다")
    finish(result, "S3 가려진 사진", hidden)
    return result


if __name__ == "__main__":
    sys.exit(main_for(run))
