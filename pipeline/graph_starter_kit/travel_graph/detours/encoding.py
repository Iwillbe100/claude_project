"""처방 가지 — 글자가 깨짐 (인코딩). **루프 A · 결정론.**

증상  시험지 `scripts/detour_tests/test_encoding.py` 가 가려낸다
    모지바케       '한국' 이 'í•œêµ­' 로 — UTF-8 바이트를 cp1252 로 잘못 읽었다
    깨진 글자      '�' — 바이트가 이미 사라졌다
    비ASCII 주소   'Special:FilePath/Hội_An.jpg' — 요청을 보내는 순간 UnicodeEncodeError

출생 — 알려진 실패 축. 원인과 고칠 법이 이미 알려져 있어 **로그 실측 전에** 미리 구축했다.

어디서 오나 (Windows 에서 특히)
    cp949 콘솔 · cp949 로 저장된 파일 · 웹 글을 잘못 옮겨 적은 모델 응답 ·
    모델이 파일 이름을 현지 글자 그대로 적은 주소

고치는 법 — 시도할수록 세진다
    1회째  모지바케를 되읽어 원래 글자로 되돌린다
           주소는 퍼센트 인코딩한다 (`research._ascii_url` — 이 킷이 이미 요청할 때 쓰는 함수)
           '�' 가 든 칸은 인계본(루프 결과)의 **같은 칸**이 멀쩡하면 그 값으로 되돌린다
    2회째  그래도 '�' 가 남은 칸은 **비운다.** 빈 칸은 루프 골격의 검사기가 '부족'으로 잡고
           재수집(`repair_city`)이 다시 채운다. 깨진 글자를 지우고 조용히 넘어가는 것이
           가장 나쁜 실패다 — 비워서 루프 골격에 넘긴다

실패 재현 (`inject`) — 첫 도시에
    첫 관광지의 상세 글을 모지바케로, 그 사진 주소를 현지 글자 그대로(비ASCII)로 바꾼다
"""
from __future__ import annotations

import copy
import urllib.parse

from travel_graph import contract, research

KIND = "encoding"
INJECT_AT = "city"
HOWTO = ("글자가 깨진 칸이 남았습니다. 되읽기로 되살릴 수 없는 글자('�')는 원문에서 다시 "
         "옮겨 적어야 합니다 — `more` 를 고르면 재수집이 그 칸을 다시 채웁니다")

URL_KEYS = ("url", "source_url")

# --------------------------------------------------------------------------- #
# 글자 되읽기 — **시험지의 판정 함수를 그대로 쓴다**
# --------------------------------------------------------------------------- #
#
#   무엇이 모지바케인가는 시험지(`scripts/detour_tests/test_encoding.py` 의 `decode_run`)가
#   정한다. 고치는 쪽이 판정을 따로 두면 "시험지는 멀쩡하다는데 fix 가 고친다"(정상 글을
#   망가뜨린다) 또는 그 반대가 생긴다. 고치는 쪽이 채점표를 **불러 쓰는** 것은 괜찮다 —
#   거꾸로(시험지가 고치는 코드를 import)는 판정 독립이 무너져 11번 검사가 막는다.


def unmojibake(text: str) -> str:
    """모지바케 덩어리만 원래 글자로 되읽는다. 판정은 시험지의 `decode_run` 이 한다."""
    from travel_graph import detours
    return detours.test_module(KIND).unmojibake(text)


def mojibake(text: str) -> str:
    """정상 글을 **일부러** 모지바케로 만든다 (실패 재현용). Windows 에서 흔한 모양 그대로."""
    out = []
    for byte in text.encode("utf-8"):
        try:
            out.append(bytes([byte]).decode("cp1252"))
        except UnicodeDecodeError:
            out.append(chr(byte))
    return "".join(out)


def _bad_url(url: str) -> bool:
    return bool(url) and (not url.isascii() or url != url.strip()
                          or any(c.isspace() for c in url.strip()))


# --------------------------------------------------------------------------- #
# 칸 순회 — 제자리에서 고치려면 (부모, 열쇠) 가 필요하다
# --------------------------------------------------------------------------- #


def _slots(node, path=()):
    """문자열 칸을 `(부모, 열쇠, 경로)` 로 내놓는다. 경로는 인계본에서 같은 칸을 찾는 데 쓴다."""
    if isinstance(node, dict):
        for key in list(node):
            if str(key).startswith("_"):
                continue
            value = node[key]
            if isinstance(value, str):
                yield node, key, path + (key,)
            else:
                yield from _slots(value, path + (key,))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            step = (("name", value.get("name")) if isinstance(value, dict) and value.get("name")
                    else index)
            if isinstance(value, str):
                yield node, index, path + (step,)
            else:
                yield from _slots(value, path + (step,))


def _find(node, path):
    """인계본에서 같은 칸을 찾는다. 이름이 있는 항목은 **이름으로** 찾는다 (순서가 달라도).

    ★ 이름 없는 목록(근거 `items` · 일정 `days`)은 **순번으로 맞추지 않는다** — 항목 구성이
      다르면 엉뚱한 근거 문장이 들어가 `source_url` 과 어긋난다. 그런 칸은 되돌리지 않고
      2회째에 비워 재수집에 넘긴다.
    """
    for step in path:
        if isinstance(step, tuple) and isinstance(node, list):
            node = next((x for x in node if isinstance(x, dict) and x.get("name") == step[1]), None)
        elif isinstance(step, int):
            return None
        elif isinstance(node, dict):
            node = node.get(step)
        else:
            return None
        if node is None:
            return None
    return node


def _label(path) -> str:
    parts = []
    for step in path:
        if step in ("cities", "spots"):
            continue
        if isinstance(step, tuple):
            parts.append(str(step[1]))
        elif isinstance(step, int):
            parts[-1:] = [(parts[-1] if parts else "") + f"[{step}]"]
        else:
            parts.append("국가 소개" if step == "country_intro" else str(step))
    return "/".join(parts)


# --------------------------------------------------------------------------- #
# 처방 가지의 두 함수
# --------------------------------------------------------------------------- #


def fix(data: dict, *, attempt: int, mode: str) -> dict:
    """`data`(country_intro · cities)를 **그 자리에서** 고친다."""
    fixed, unfixed = [], []
    base = contract.baseline()
    if str(base.get("country") or "") != str(data.get("country") or ""):
        base = {}                               # 나라가 다르면 인계본의 "같은 칸"은 없다
    for parent, key, path in list(_slots(data)):
        value = parent[key]
        label = _label(path)
        if key in URL_KEYS:
            if _bad_url(value):
                parent[key] = research._ascii_url(value.strip())
                (fixed if parent[key].isascii() else unfixed).append(
                    label + ": 주소를 퍼센트 인코딩했습니다")
            continue
        repaired = unmojibake(value)
        if repaired != value:
            parent[key] = value = repaired
            fixed.append(label + ": 모지바케를 원래 글자로 되읽었습니다")
        if "�" not in value:
            continue
        original = _find(base, path)
        if isinstance(original, str) and original and "�" not in original:
            parent[key] = copy.deepcopy(original)
            fixed.append(label + ": 되살릴 수 없는 글자 — 인계본의 같은 칸으로 되돌렸습니다")
        elif attempt >= 2:
            parent[key] = ""
            fixed.append(label + ": 되살릴 수 없는 글자 — 칸을 비웠습니다 (재수집이 다시 채웁니다)")
        else:
            unfixed.append(label + ": 되살릴 수 없는 글자 '�' — 인계본에도 같은 칸이 없습니다")
    return {"fixed": fixed, "unfixed": unfixed}


def inject(city: dict) -> str:
    """첫 관광지의 상세 글을 모지바케로, 사진 주소를 현지 글자 그대로 바꾼다."""
    spots = city.get("spots")
    if not isinstance(spots, list):
        return ""
    spot = next((s for s in spots if isinstance(s, dict) and s.get("detail")), None)
    if not isinstance(spot, dict):
        return ""
    spot["detail"] = mojibake(str(spot["detail"]))
    image = spot.get("image")
    moved = False
    if isinstance(image, dict) and image.get("url"):
        before = str(image["url"])
        image["url"] = urllib.parse.unquote(before)
        moved = image["url"] != before and not image["url"].isascii()
    return (f"{city.get('name')}/{spot.get('name')} 상세를 모지바케로"
            + (" · 사진 주소를 비ASCII 로" if moved else ""))
