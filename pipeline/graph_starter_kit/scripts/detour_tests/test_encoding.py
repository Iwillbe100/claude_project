#!/usr/bin/env python3
"""처방 가지 시험지 — 글자가 깨짐 (인코딩). **킷 소유.**

**진단(`diagnose_info`)도 이 시험지로 하고, 합격(`test_encoding`)도 이 시험지로 판정한다.**
같은 종이로 보므로 "진단은 문제라는데 시험은 합격"인 틈이 생기지 않는다.

보는 것 — `output/research_data.json`

    E0  파일이 UTF-8 로 읽히는가
    E1  깨진 글자 '�'(U+FFFD)   바이트가 이미 사라졌다. 되읽기로는 되살릴 수 없다
    E2  모지바케                 UTF-8 바이트를 cp1252·latin-1 로 잘못 읽은 글자
                                 예) '한국' → 'í•œêµ­'   (되읽으면 원래 글자가 나온다)
    E3  주소에 ASCII 가 아닌 글자  url · source_url 에 'Hội_An' 같은 글자나 공백
                                 요청을 보내는 순간 UnicodeEncodeError 가 난다

★ 루프 골격의 검사기(`check_information_count.py`)는 이 넷을 보지 않는다. 글자 **수**를
  세므로 깨진 글자도 한 글자로 센다. 그래서 판정이 PASS 여도 이 시험지는 불합격일 수
  있다 — 진단 노드가 판정과 **따로** 증상을 보는 이유다.

종료 코드  0 합격 · 2 불합격(증상 있음) · 1 깨짐
사용법     python scripts/detour_tests/test_encoding.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import URL_KEYS, Result, finish, main_for, read_research, walk_strings  # noqa: E402

#: cp1252 로 읽힌 바이트가 되는 글자들. 이 글자가 **둘 이상 붙어** 나오고, 그 덩어리를
#: 바이트로 되돌려 UTF-8 로 읽으면 말이 되는 글자가 나오면 → 모지바케다.
_CP1252_HIGH = ("\u0080-ÿŒœŠšŸŽžƒˆ˜"
                "–—‘’‚“”„†‡•…"
                "‰‹›€™")
_RUN = re.compile("[" + _CP1252_HIGH + "]{2,}")


def _as_bytes(run: str):
    """글자 덩어리를 '잘못 읽히기 전의 바이트'로. cp1252 에 없는 자리는 latin-1 로."""
    out = bytearray()
    for ch in run:
        try:
            out += ch.encode("cp1252")
        except UnicodeEncodeError:
            if ord(ch) < 256:
                out.append(ord(ch))
            else:
                return None
    return bytes(out)


#: 되읽은 결과가 **말이 되는 글자**인가. 한글 · 라틴 악센트 · 베트남어 성조 · 일반 구두점.
_PLAIN_OK = re.compile("^[\x00-\x7fÀ-ɏ̀-ͯḀ-ỿ -⁯"
                       "ᄀ-ᇿ㄰-㆏가-힣]+$")
#: 한자 · 가나 · 키릴 · 태국 문자는 **두 글자 이상** 나올 때만 믿는다. 한 글자짜리는 정상 글의
#: 악센트 + 구두점(`é…”` → `酔`)이 우연히 UTF-8 로 읽힌 것일 때가 많다.
_WIDE_OK = re.compile("^[\x00-\x7f -⁯　-ヿ一-鿿Ѐ-ӿ"
                      "฀-๿]+$")


def decode_run(run: str):
    """모지바케 덩어리면 **원래 글자**를, 아니면 None. 시험지와 고치는 코드가 같이 쓴다.

    정상 글은 걸리지 않는다 — 그 글자들을 바이트로 되돌리면 UTF-8 로 읽히지 않거나
    (베트남어 성조 · 프랑스어 악센트), 읽혀도 말이 안 되는 글자(`É·` → `ɷ`)가 나온다.
    """
    raw = _as_bytes(run)
    if raw is None:
        return None
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if decoded == run or not any(ord(c) > 127 for c in decoded):
        return None
    if _PLAIN_OK.match(decoded) or (len(decoded) >= 2 and _WIDE_OK.match(decoded)):
        return decoded
    return None


def mojibake_runs(text: str) -> list:
    """모지바케 덩어리 목록."""
    return [m.group(0) for m in _RUN.finditer(text) if decode_run(m.group(0))]


def unmojibake(text: str) -> str:
    """모지바케 덩어리만 원래 글자로 되읽는다. 멀쩡한 글자는 건드리지 않는다."""
    return _RUN.sub(lambda m: decode_run(m.group(0)) or m.group(0), text)


def run(root=None) -> Result:
    """처방 가지 시험지 — 인코딩 (깨진 글자 · 모지바케 · 비ASCII 주소)"""
    result = Result("처방 가지 시험지 — 인코딩 (test_encoding)")
    data, problem = read_research(root)
    if data is None:
        if "UTF-8" in problem:
            result.row("E0 파일이 UTF-8 로 읽힘", "예", "아니오", False)
            result.note_short(problem)
        else:
            result.note_broken(problem)
        return result
    result.row("E0 파일이 UTF-8 로 읽힘", "예", "예", True)

    broken, moji, urls = [], [], []
    for label, key, value in walk_strings(data):
        if key in URL_KEYS:
            if value and (not value.isascii() or any(c.isspace() for c in value.strip())
                          or value != value.strip()):
                urls.append(label + ": 주소에 ASCII 가 아닌 글자·공백 — " + value[:70])
            continue
        if "�" in value:
            broken.append(label + ": 깨진 글자 '�' — " + value[:40].replace("\n", " "))
        runs = mojibake_runs(value)
        if runs:
            moji.append(label + ": 모지바케 '" + runs[0][:16] + "' — " + value[:40].replace("\n", " "))

    finish(result, "E1 깨진 글자(�)", broken)
    finish(result, "E2 모지바케", moji)
    finish(result, "E3 ASCII 가 아닌 주소", urls)
    return result


if __name__ == "__main__":
    sys.exit(main_for(run))
