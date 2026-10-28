"""인계본을 읽는 곳. **킷 소유 — 수정 금지.**

노드도, 검사기도, 여기서만 계약을 읽는다. 계약이 두 군데에 있으면
루프판과 그래프판이 조용히 갈라진다.

  graph/03_CONTRACT.json   개수 계약 · 화면 계약 · 상한  (검사 기준)
  graph/research_data.json 루프가 모은 정보 원본        (replay 자료 · 비교 기준선)
  graph/02_USER_REQUEST.md 취향 원문                    (LLM 노드 프롬프트에 붙는다)
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

#: travel_graph/contract.py -> parents[0]=travel_graph, [1]=PROJECT_ROOT
ROOT = Path(__file__).resolve().parents[1]

HANDOFF_DIR = ROOT / "graph"
CONTRACT_FILE = HANDOFF_DIR / "03_CONTRACT.json"
BASELINE_FILE = HANDOFF_DIR / "research_data.json"
REQUEST_FILE = HANDOFF_DIR / "02_USER_REQUEST.md"
SEED_FILE = HANDOFF_DIR / "05_STATE_SEED.json"

OUTPUT_DIR = ROOT / "output"
RESEARCH_OUT = OUTPUT_DIR / "research_data.json"
HTML_OUT = OUTPUT_DIR / "travel_site.html"


class HandoffMissing(RuntimeError):
    """인계본이 없다. 루프 킷의 output/graph/ 를 graph/ 에 복사해야 한다."""


def _read_json(path: Path):
    if not path.exists():
        raise HandoffMissing(
            f"{path.relative_to(ROOT)} 이 없습니다. 루프 킷에서 "
            "`python scripts/export_graph_handoff.py` 로 만든 output/graph/ 폴더를 "
            "이 킷의 graph/ 에 통째로 복사하십시오."
        )
    return json.loads(path.read_text(encoding="utf-8-sig"))


@lru_cache(maxsize=1)
def contract() -> dict:
    """graph/03_CONTRACT.json — 이 킷의 유일한 기준 출처."""
    return _read_json(CONTRACT_FILE)


@lru_cache(maxsize=1)
def baseline() -> dict:
    """graph/research_data.json — 루프가 모은 원본. 절대 덮어쓰지 않는다.

    루프 킷 명세는 국가 · 일수를 `request` 안에 적는다(`research_data.request`).
    최상위 `country` · `days` 가 없으면 `request` 에서 채워 **읽는다** — 파일은 그대로 둔다.
    그래야 인계본을 어느 모양으로 받아도 "같은 나라인가"를 바르게 잰다
    (`detours/image_dead.py` · `detours/encoding.py` · `scripts/check_graph_readiness.py`).
    """
    data = _read_json(BASELINE_FILE)
    if isinstance(data, dict):
        req = data.get("request") if isinstance(data.get("request"), dict) else {}
        for key in ("country", "days"):
            if not data.get(key) and req.get(key):
                data[key] = req[key]
    return data


@lru_cache(maxsize=1)
def user_request() -> str:
    """취향 원문. 요약본으로는 15줄짜리 취향 설명이 안 나온다."""
    if not REQUEST_FILE.exists():
        return ""
    return REQUEST_FILE.read_text(encoding="utf-8")


def counts() -> dict:
    return contract().get("count_contract") or {}


def page_rules() -> dict:
    return contract().get("page_contract") or {}


def limits() -> dict:
    """상한 5종. 상태 시드가 비어 있을 때 노드가 쓰는 기본값이다.

    **`quality_passes_required` 만 뜻이 다르다.** 루프 A·B 의 상한은 "여기까지만
    돈다"는 최대값이지만, 루프 C 의 3회는 **최소이자 최대**다. 통과선이 아니라
    고정 예산이므로 라우터도 이 값을 다르게 읽는다 (`route_after_quality`).

    ★ `max_iterations` 는 **여기서 읽기만 하고 그래프가 강제하지 않는다.** 루프
      킷의 결정(`D-최대반복`)을 인계본에 기록으로 남기는 값이다. 안쪽 루프는
      `loop_a_limit`·`loop_b_limit`·`quality_passes_required` 가 각각 막고,
      **바깥 루프는 게이트 B 에서 사람이 소유한다** — 사람이 "한 번 더" 를 고르는
      횟수에 코드가 상한을 두지 않는 것이 이 그래프의 설계다. 전역 상한이 필요하면
      상태에 카운터를 하나 더 두고 `route_after_gate_b` 가 읽어야 하는데, 그것은
      "사람이 바깥 루프를 소유한다"는 약속을 바꾸는 일이라 함부로 넣지 않는다.
    """
    loops = contract().get("loops") or {}
    options = contract().get("options") or {}
    quality = contract().get("quality_contract") or {}
    return {
        "loop_a_limit": (loops.get("A") or {}).get("limit") or 3,
        "loop_b_limit": (loops.get("B") or {}).get("limit") or 3,
        "same_error_limit": options.get("same_error_limit") or 2,
        "max_iterations": options.get("max_iterations") or 10,
        "quality_passes_required": quality.get("passes") or (loops.get("C") or {}).get("limit") or 3,
    }


def request_defaults() -> dict:
    """Studio 입력이 비어 있을 때 쓸 기본 요청. 인계본에서 읽는다."""
    return contract().get("request") or {}


def read_research() -> dict:
    """방금 쓴 수집 결과를 되읽는다. `rebuilder` 가 고친 데이터를 상태로 되올릴 때 쓴다."""
    if not RESEARCH_OUT.exists():
        return {}
    try:
        data = json.loads(RESEARCH_OUT.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def write_research(data: dict) -> Path:
    """수집 결과를 검사기가 읽는 자리에 쓴다. 이 경로는 루프 킷과 같다."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESEARCH_OUT.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return RESEARCH_OUT
