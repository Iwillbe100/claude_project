"""처방 가지 — 이미지 주소가 죽어 있음. **루프 A · 결정론** (live 에서는 실제로 열어 본다).

증상  시험지 `scripts/detour_tests/test_image_dead.py` 가 가려낸다
    열어 봤더니 HTTP 404 · 계약이 금지한 주소 형태(upload.wikimedia.org) · 이미지가 아닌 페이지

출생 · 실측 근거  루프 킷 실행 로그 — 킷에 든 예시 인계본 `graph/04_RUN_EVIDENCE.md` 1-b
    이미지 11장이 전부 죽었다. 사진은 실재했고, 모델이 `upload.wikimedia.org/…/thumb/8/8c/…`
    주소 속 **해시 두 글자**(`8/8c`)를 지어냈다. 올바른 값은 `c/c5` — 파일 이름에서 파생되는
    값이라 모델이 알아낼 방법이 없다. 같은 프롬프트로 다시 모으면 또 지어낸다 — 그래서 이
    문제는 재수집(LLM)이 아니라 **정해진 절차**로 고친다.

고치는 법 — 시도할수록 세진다
    1회째  (a) Commons 주소(upload.wikimedia.org · /wiki/File:)면 파일 이름만 뽑아 **해시가 필요
               없는 권장 형태** `Special:FilePath/<파일명>?width=1024` 로 다시 쓴다 — 실측에서 통한 고칠 법
           (b) 인계본(루프 결과)의 **같은 나라 · 같은 도시 · 같은 관광지** 자리에 살아 있는
               사진이 있으면 그것으로 바꾼다
           live 에서는 바꾼 주소를 **실제로 열어 보고** verified 를 새로 적는다
           (모델의 자기보고를 믿지 않는다 — `research.verify_asset`). replay 는 네트워크를 쓰지
           않으므로, 다시 쓴 주소가 인계본의 **같은 파일**이면 인계본의 확인 기록을 쓴다.
    2회째  (live 전용) 파일 이름의 **뜻 있는 낱말**로 Commons 를 검색해, 제목에 그 낱말이 든
           실제 파일로 바꾼다 (IMG · DSC 같은 카메라 이름은 낱말로 치지 않는다). 검색으로 바꾼
           것은 `verified.by = "detour-search"` 로 표시한다 — 그 관광지 사진이 맞는지는 사람이 본다.

실패 재현 (`inject`) — 첫 도시에
    두 번째 관광지(없으면 첫 관광지) 사진 주소를 **실측 모양 그대로** 바꾼다 —
    `upload.wikimedia.org/…/thumb/8/8c/<실제 파일>/1280px-<실제 파일>` + 404 기록.
    파일은 실재하고 해시 두 글자만 지어낸 주소다. (첫 관광지는 encoding 재현이 쓰므로 비켜 둔다)
"""
from __future__ import annotations

import copy
import json
import re
import urllib.parse
import urllib.request

from travel_graph import contract, research

KIND = "image_dead"
INJECT_AT = "city"
HOWTO = ("정해진 절차(주소 형태 바로잡기 · 인계본 사진 · 검색)로도 살아 있는 사진을 못 찾았습니다. "
         "`more` 를 고르면 재수집이 note 대로 다시 찾습니다 — "
         "'Commons 에서 실제로 확인한 파일 이름만 써라'고 적으십시오")

FILEPATH = "https://commons.wikimedia.org/wiki/Special:FilePath/"
WIDTH = "1024"
_IMAGE_EXT = (".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".tif", ".tiff")

#: 파일 이름에 흔한데 **뜻이 없는** 낱말. 검색어로 쓰면 아무 사진이나 걸린다.
_GENERIC = frozenset({"img", "dsc", "dscn", "dcim", "photo", "image", "file", "pic", "picture",
                      "jpg", "jpeg", "png", "gif", "svg", "webp", "the", "and", "of", "px"})


# --------------------------------------------------------------------------- #
# 무엇이 죽었나 — 시험지와 같은 기준 (계약의 asset_rule)
# --------------------------------------------------------------------------- #


def _rule() -> dict:
    return (contract.counts() or {}).get("asset_rule") or {}


def is_dead(asset: dict) -> bool:
    """시험지(`test_image_dead.symptom`)와 **같은 기준**. 둘이 다르면 고칠 것 없이 떨어진다."""
    if not isinstance(asset, dict) or not str(asset.get("url") or "").strip():
        return False                                            # 안 모은 칸 — 재수집의 몫
    rule = _rule()
    url = str(asset.get("url")).strip()
    if any(b and b in url for b in (rule.get("banned_url_substrings") or [])):
        return True                                             # D2 손으로 만든 주소 형태
    verified = asset.get("verified")
    if not isinstance(verified, dict):
        return False                                            # 아직 열어 보지 않음
    error = str(verified.get("error") or "")
    if "네트워크로 닿지 못했습니다" in error:
        return False                                            # 환경 문제 — 처방 가지 대상이 아니다
    allowed = rule.get("allowed_status") or [200]
    status = verified.get("status")
    if error or (status is not None and status not in allowed):
        return True                                             # D1 열었더니 실패
    prefix = rule.get("content_type_prefix") or ""
    return bool(prefix) and status in allowed and not str(
        verified.get("content_type") or "").startswith(prefix)  # D3 이미지가 아님


def _alive(asset) -> bool:
    return (isinstance(asset, dict) and isinstance(asset.get("verified"), dict)
            and not is_dead(asset) and bool(str(asset.get("url") or "").strip())
            and asset["verified"].get("status") in (_rule().get("allowed_status") or [200]))


# --------------------------------------------------------------------------- #
# 주소 다루기
# --------------------------------------------------------------------------- #


def _is_commons(url: str) -> bool:
    host = urllib.parse.urlsplit(str(url or "").strip()).netloc.lower()
    return host == "wikimedia.org" or host.endswith(".wikimedia.org")


def filename_of(url: str) -> str:
    """Commons 주소에서 **파일 이름**만 뽑는다. Commons 가 아니거나 못 뽑으면 빈 문자열.

        …/wikipedia/commons/8/8c/Moraine_Lake.jpg                       (원본 · 해시 경로)
        …/wikipedia/commons/thumb/8/8c/Moraine_Lake.jpg/1280px-….jpg      (썸네일)
        https://commons.wikimedia.org/wiki/File:Moraine_Lake.jpg          (설명 페이지)
        https://commons.wikimedia.org/wiki/Special:FilePath/Moraine_Lake.jpg?width=1024

    ★ Commons 가 아닌 주소(여행사 사이트 등)의 파일 이름을 Commons 에 붙이면 **같은 이름의
      엉뚱한 사진**이 열릴 수 있다. 그래서 Commons 주소일 때만 뽑는다.
    """
    if not _is_commons(url):
        return ""
    parts = urllib.parse.urlsplit(str(url or "").strip())
    path = urllib.parse.unquote(parts.path)
    for marker in ("/Special:FilePath/", "/wiki/File:", "/wiki/Image:"):
        if marker in path:
            return path.split(marker, 1)[1].split("/")[0]
    segments = [s for s in path.split("/") if s]
    if "thumb" in segments:
        i = segments.index("thumb")
        if len(segments) > i + 3:
            return segments[i + 3]
    if segments and segments[-1].lower().endswith(_IMAGE_EXT):
        return segments[-1]
    return ""


def canonical(name: str) -> str:
    """해시가 필요 없는 권장 형태. 계약의 `recommended_form` 과 같다."""
    return FILEPATH + urllib.parse.quote(name.replace(" ", "_"), safe="()_-.,") + "?width=" + WIDTH


def _same_file(url_a: str, url_b: str) -> bool:
    a, b = filename_of(url_a), filename_of(url_b)
    return bool(a) and a.replace(" ", "_").casefold() == b.replace(" ", "_").casefold()


def _words(name: str) -> list:
    stem = re.sub(r"\.[A-Za-z0-9]+$", "", name)
    return [w for w in re.split(r"[\s_\-,()'.]+", stem)
            if len(w) >= 3 and not w.isdigit() and w.casefold() not in _GENERIC]


def _search_commons(name: str) -> list:
    """(live 전용) 파일 이름의 **뜻 있는 낱말**로 Commons 파일을 검색한다.

    돌려주는 것: 제목에 그 낱말이 **하나 이상 든** 파일 이름만. 낱말이 없으면 검색하지 않는다
    (`IMG_4008.jpg` 로 검색하면 `IMG 0001.JPG` 같은 아무 사진이나 걸린다).
    """
    words = _words(name)
    if not words:
        return []
    query = urllib.parse.urlencode({
        "action": "query", "list": "search", "srnamespace": "6", "srlimit": "5",
        "format": "json", "srsearch": " ".join(words)[:120] + " filetype:bitmap"})
    request = urllib.request.Request(
        "https://commons.wikimedia.org/w/api.php?" + query,
        headers={"User-Agent": "graph-starter-kit/1.0 (LangGraph course; image detour)"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            hits = json.loads(response.read().decode("utf-8")).get("query", {}).get("search", [])
    except Exception:                                           # noqa: BLE001
        return []
    keys = {w.casefold() for w in words}
    names = [str(h.get("title", "")).split(":", 1)[-1] for h in hits if h.get("title")]
    return [n for n in names if keys & {w.casefold() for w in _words(n)}]


# --------------------------------------------------------------------------- #
# 이미지 자리 — (이름표, 부모 dict, 열쇠, 인계본의 같은 자리)
# --------------------------------------------------------------------------- #


def _d(value) -> dict:
    return value if isinstance(value, dict) else {}


def _l(value) -> list:
    return value if isinstance(value, list) else []


def _places(data: dict):
    """★ 인계본의 "같은 자리"는 **같은 나라**일 때만 쓴다. 나라가 다르면 국기 칸에 베트남
      국기가, 관광지 칸에 다른 나라 사진이 들어간다."""
    base = contract.baseline()
    same_country = str(base.get("country") or "") == str(data.get("country") or "")
    base_intro = _d(base.get("country_intro")) if same_country else {}
    for slot, node in _d(data.get("country_intro")).items():
        if isinstance(node, dict) and isinstance(node.get("asset"), dict):
            original = _d(base_intro.get(slot)).get("asset")
            yield f"국가 소개/{slot}", node, "asset", original
    base_cities = ({c.get("name"): c for c in _l(base.get("cities")) if isinstance(c, dict)}
                   if same_country else {})
    for city in _l(data.get("cities")):
        if not isinstance(city, dict):
            continue
        base_spots = {s.get("name"): s for s in _l(_d(base_cities.get(city.get("name"))).get("spots"))
                      if isinstance(s, dict)}
        for spot in _l(city.get("spots")):
            if isinstance(spot, dict) and isinstance(spot.get("image"), dict):
                original = (base_spots.get(spot.get("name")) or {}).get("image")
                yield f"{city.get('name')}/{spot.get('name')} 이미지", spot, "image", original


def _try(candidate: dict, mode: str) -> dict | None:
    """주소를 바꾼 후보를 **실제로 열어 본다** (live). replay 는 열어 볼 수 없으므로 None."""
    if mode != "live":
        return None
    checked = research.verify_asset(candidate)
    return checked if _alive(checked) else None


# --------------------------------------------------------------------------- #
# 처방 가지의 두 함수
# --------------------------------------------------------------------------- #


def fix(data: dict, *, attempt: int, mode: str) -> dict:
    fixed, unfixed = [], []
    for label, parent, key, original in _places(data):
        asset = parent[key]
        if not is_dead(asset):
            continue
        url = str(asset.get("url") or "")
        name = filename_of(url)
        done = None

        # (a) Commons 인데 해시가 든 주소 → 해시가 필요 없는 권장 형태로 다시 쓰고 확인한다
        if name and not url.startswith(FILEPATH):
            rewritten = {**asset, "url": canonical(name)}
            done = _try(rewritten, mode)
            if done is None and mode != "live" and _alive(original) and _same_file(
                    rewritten["url"], original.get("url")):
                done = copy.deepcopy(original)                  # replay — 같은 파일의 확인 기록
            if done:
                fixed.append(f"{label}: 해시가 든 주소를 권장 형태로 바로잡았습니다 "
                             f"(Special:FilePath/{name[:40]})")

        # (b) 인계본(루프 결과)의 같은 자리에 살아 있는 사진
        if done is None and _alive(original):
            done = copy.deepcopy(original)
            fixed.append(f"{label}: 인계본의 살아 있는 사진으로 바꿨습니다")

        # (c) 2회째 · live — 뜻 있는 낱말로 Commons 검색
        if done is None and attempt >= 2 and mode == "live" and name:
            for found in _search_commons(name):
                done = _try({**asset, "url": canonical(found)}, mode)
                if done:
                    done["verified"] = {**done.get("verified", {}), "by": "detour-search"}
                    fixed.append(f"{label}: Commons 검색으로 실제 파일을 찾았습니다 "
                                 f"({found[:40]}) — 그 관광지 사진이 맞는지 사람이 확인")
                    break

        if done is None:
            why = ("replay 는 네트워크를 쓰지 않아 새 주소를 열어 볼 수 없습니다"
                   if mode != "live" else "살아 있는 후보를 찾지 못했습니다")
            unfixed.append(f"{label}: {why}")
            continue
        done.setdefault("alt", asset.get("alt"))
        parent[key] = done
    return {"fixed": fixed, "unfixed": unfixed}


def inject(city: dict) -> str:
    """사진 주소를 **실측 모양 그대로** 바꾼다 — 해시 두 글자(8/8c)를 지어낸 upload 주소 + 404."""
    spots = city.get("spots")
    if not isinstance(spots, list):
        return ""
    with_image = [s for s in spots if isinstance(s, dict) and isinstance(s.get("image"), dict)
                  and s["image"].get("url")]
    if not with_image:
        return ""
    spot = with_image[1] if len(with_image) > 1 else with_image[0]
    image = spot["image"]
    name = filename_of(image["url"]) or "Photo.jpg"
    quoted = urllib.parse.quote(name.replace(" ", "_"), safe="()_-.,")
    image["url"] = ("https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/"
                    + quoted + "/1280px-" + quoted)
    #  `research.verify_asset` 가 404 에서 남기는 기록과 **글자 하나 다르지 않게** 적는다.
    image["verified"] = {
        "status": 404, "content_type": "", "checked_at": "",
        "error": "HTTP 404 (주소 형식이 아니라 **파일명**이 틀렸습니다. Commons 에 그 파일이 없습니다)"}
    return (f"{city.get('name')}/{spot.get('name')} 사진 주소를 해시 두 글자(8/8c)를 지어낸 "
            f"upload 주소로 (404 — 실측 모양)")
