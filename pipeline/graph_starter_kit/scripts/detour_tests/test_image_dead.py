#!/usr/bin/env python3
"""처방 가지 시험지 — 이미지 주소가 죽어 있음. **킷 소유.**

**진단(`diagnose_info`)도 이 시험지로 하고, 합격(`test_image_dead`)도 이 시험지로 판정한다.**

보는 것 — `output/research_data.json` 의 이미지 자리 전부 (국기 · 대표 사진 · 관광지 사진)

    D1  열어 봤는데 실패한 기록     verified 에 HTTP 404 같은 오류가 남아 있다
    D2  손으로 만든 주소 형태       계약이 금지한 형태 (upload.wikimedia.org …)
    D3  열렸는데 이미지가 아님      content_type 이 image/ 가 아니다 (파일 설명 페이지 주소 등)

보지 않는 것 — 이 처방 가지의 몫이 아니다

    아직 안 모은 칸     url 이나 verified 가 없다   → 루프 골격의 재수집(repair_city)이 채운다
    네트워크 문제       '네트워크로 닿지 못했습니다'  → 환경 문제. 사람이 본다

★ 실측 근거 (킷에 든 예시 인계본 `graph/04_RUN_EVIDENCE.md` 1-b): 이미지 11장이 전부 죽었다(404 10장 · 400 1장). 사진은
  실재했고, 모델이 주소 속 해시 두 글자(`8/8c`)를 지어냈다. 이런 결함은 LLM 이 다시
  찾아도 같은 식으로 지어낸다 — 그래서 **정해진 절차로 고치는 처방 가지**를 둔다.

★ 판정 문구는 루프 골격의 검사기와 **같은 함수**(`_contract.asset_problems`)에서 나온다.
  같은 계약(`graph/03_CONTRACT.json` 의 asset_rule)을 같은 말로 읽는다.

종료 코드  0 합격 · 2 불합격(증상 있음) · 1 깨짐
사용법     python scripts/detour_tests/test_image_dead.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import Result, asset_problems, asset_rule, assets, finish, main_for, read_research  # noqa: E402

_DEAD = "이미지 주소가 열리지 않았습니다"
_BANNED = "손으로 만들 수 없는 주소 형태"
_NOT_IMAGE = "verified.content_type"
_NETWORK = "네트워크로 닿지 못했습니다"


def symptom(asset: dict, rule: dict) -> str:
    """이 자산이 **죽은 주소**면 이유 한 줄, 아니면 빈 문자열."""
    url = str(asset.get("url") or "").strip()
    if not url:
        return ""                                               # 안 모은 칸 — 재수집의 몫
    problems = asset_problems(asset, rule)
    for line in problems:
        if line.startswith(_BANNED):
            return line
    verified = asset.get("verified")
    if not isinstance(verified, dict):
        return ""                                               # 아직 열어 보지 않음 — 재수집의 몫
    for line in problems:
        if line.startswith(_DEAD):
            return "" if _NETWORK in line else line             # 네트워크는 환경 문제
    #  D3 는 **열렸는데**(허용 상태) 이미지가 아닐 때만 — 상태가 비어 있는 기록은 "아직 안 모음"이다.
    if verified.get("status") in (rule.get("allowed_status") or [200]):
        for line in problems:
            if line.startswith(_NOT_IMAGE):
                return line
    return ""


def run(root=None) -> Result:
    """처방 가지 시험지 — 죽은 이미지 주소 (404 · 금지된 주소 형태 · 이미지가 아닌 주소)"""
    result = Result("처방 가지 시험지 — 죽은 이미지 주소 (test_image_dead)")
    data, problem = read_research(root)
    if data is None:
        result.note_broken(problem)
        return result
    rule = asset_rule(root)
    dead = []
    for label, asset in assets(data):
        why = symptom(asset, rule)
        if why:
            dead.append(label + ": " + why)
    finish(result, "죽은 이미지 주소", dead)
    return result


if __name__ == "__main__":
    sys.exit(main_for(run))
