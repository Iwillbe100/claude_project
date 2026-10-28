"""처방 가지 — 사진이 화면 규격에 안 맞음. **루프 B · 결정론.**

증상  시험지 `scripts/detour_tests/test_image_spec.py` 가 **화면(HTML)** 에서 가려낸다
    S1  사진 주소에 width 가 없거나 1280 보다 크다 → 원본(한 장에 수~수십 MB)을 통째로 받는다
    S2  CSS 에 사진 틀(비율 · 높이 상한)이 없다      → 세로 사진이 서랍을 뚫고 길어진다
    S3  사진 class 가 CSS 로 가려져 있다

출생 — 실습생이 게이트에서 적은 지적 "이미지 규격이 안 맞음" (원본 크기 사진 · 검사기는 못 본다).

어디서 오나
    live 에서 모델이 `Special:FilePath/<파일>` 만 적고 `?width=` 를 빼먹는다.
    루프 골격의 검사기는 사진이 **있는가**만 보므로 통과시킨다. 사람은 브라우저를 열고서야 안다.

고치는 법
    1회째  모든 사진 주소의 width 를 계약의 권장값(1024)으로 맞춘다. **데이터를 고친다** —
           HTML 만 고치면 다음 `build_page` 가 덮어쓴다 (`rebuilder` 와 같은 이유).
           live 에서는 바꾼 주소를 다시 열어 verified 를 새로 적는다.
    S2 · S3 은 데이터가 아니라 **화면 코드(page.py)** 의 문제라 이 처방 가지가 못 고친다
           → 시험에 떨어지고 사람(게이트 B)에게 간다. 보고서에 남긴다.

실패 재현 (`inject`) — 국가 소개에
    대표 사진 주소에서 width 를 떼어 원본 크기로 만든다.
    ★ 왜 도시가 아니라 대표 사진인가. replay 의 루프 A 는 1회차 부족을 채울 때 도시를
      인계본 통째로 되돌린다 — 도시에서 재현한 실패는 루프 B 에 닿기 전에 지워진다.
      국가 소개는 루프 A 에서 건드리지 않으므로 루프 B 까지 살아서 간다.
"""
from __future__ import annotations

import urllib.parse

from travel_graph import research

KIND = "image_spec"
INJECT_AT = "country"
HOWTO = ("사진 틀(CSS)이 없거나 사진이 가려져 있습니다. 데이터가 아니라 화면 코드(page.py) 문제라 "
         "처방 가지도 rebuild 도 못 고칩니다 — `done` 으로 넘기고 보고서에 남기십시오")

WIDTH = 1024
MAX_WIDTH = 1280


def _width(url: str):
    values = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("width") or []
    try:
        return int(values[0]) if values else None
    except ValueError:
        return -1


def with_width(url: str, width: int = WIDTH) -> str:
    """주소의 다른 부분은 **한 글자도** 건드리지 않고 width 만 맞춘다."""
    parts = urllib.parse.urlsplit(url)
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
             if k != "width"]
    query.append(("width", str(width)))
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


def _assets(data: dict):
    intro = data.get("country_intro")
    for slot, node in (intro.items() if isinstance(intro, dict) else ()):
        if isinstance(node, dict) and isinstance(node.get("asset"), dict):
            yield f"국가 소개/{slot}", node, "asset"
    for city in data.get("cities") or []:
        if not isinstance(city, dict):
            continue
        for spot in city.get("spots") or []:
            if isinstance(spot, dict) and isinstance(spot.get("image"), dict):
                yield f"{city.get('name')}/{spot.get('name')} 이미지", spot, "image"


def fix(data: dict, *, attempt: int, mode: str) -> dict:
    """모든 사진 주소의 width 를 맞춘다. 몇 번째 시도인지(`attempt`)와 상관없이 같은 일을 한다."""
    del attempt                                                 # 결정론 — 다시 해도 같다
    fixed, unfixed = [], []
    for label, parent, key in _assets(data):
        asset = parent[key]
        url = str(asset.get("url") or "").strip()
        if "Special:FilePath" not in url:
            continue
        width = _width(url)
        if width is not None and 1 <= width <= MAX_WIDTH:
            continue
        asset = {**asset, "url": with_width(url)}
        if mode == "live":
            asset = research.verify_asset(asset)                # 바꾼 주소를 실제로 열어 본다
        parent[key] = asset
        fixed.append(f"{label}: 원본 크기 → width={WIDTH} 로 맞췄습니다")
    if not fixed:
        unfixed.append("데이터에서 고칠 사진 주소가 없습니다 — 남은 증상은 화면 코드(CSS) 쪽입니다")
    return {"fixed": fixed, "unfixed": unfixed}


def inject(intro: dict) -> str:
    """대표 사진 주소에서 width 를 떼어 원본 크기로 만든다."""
    node = intro.get("대표이미지")
    if not isinstance(node, dict):
        return ""
    asset = node.get("asset")
    if not isinstance(asset, dict) or not asset.get("url"):
        return ""
    before = str(asset["url"])
    parts = urllib.parse.urlsplit(before)
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if k != "width"]
    asset["url"] = urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))
    if asset["url"] == before:
        return ""                                               # 떼어 낼 width 가 없었다
    return "국가 소개/대표이미지 주소에서 width 를 떼어 원본 크기로"
