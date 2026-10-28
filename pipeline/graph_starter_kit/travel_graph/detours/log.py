"""실패 기록 — `evidence/failures/<thread_id>.jsonl`. **실행마다 한 파일, 한 줄에 한 사건.**

진단 노드(`diagnose_*`)와 시험 노드(`test_*`)가 한 줄씩 남긴다. 이 기록이 STEP 6 의
재료다 — 교육생은 여기서 "내 그래프에서 무엇이 터졌나"를 읽고, 강사는 여러 교육생의
파일을 모아 **어떤 실패가 반복되는지** 센다 (`python scripts/failure_report.py`).

    한 번은 일화, 세 번은 패턴.   서로 다른 실행 3곳 이상에서 같은 실패(③ 같은 줄 · ③-2 같은 원인)가 나오면 킷의 처방 가지 후보다.

★ 왜 `evidence/runs/` 가 아닌가. 정성 판정기(`check_quality_passes.py`)와
  `quality.py` 는 `evidence/runs/` 의 **이름순 마지막 폴더**를 "이번 실행"으로 읽는다.
  진단 노드가 거기에 폴더를 만들면 루프 C 가 엉뚱한 폴더를 읽고 멈춘다.
  그래서 실패 기록은 옆 폴더에 따로 둔다.

★ 이 파일은 **그래프를 절대 죽이지 않는다.** 기록은 관찰 장치다. 디스크가 막혀도
  삼키고 넘어간다. (`tracing.py` 와 같은 규칙)

★ 똑같은 사건이 두 번 기록되지 않게 한다. Studio 에서 fork 하면 같은 노드가 같은
  걸음 번호로 다시 돌 수 있다 — 내용까지 같을 때만 거르고, 다른 갈래는 남긴다.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = ROOT / "evidence" / "failures"


def folder() -> Path:
    """기록 폴더. 회귀 테스트는 `GRAPH_FAILURE_LOG_DIR` 로 임시 폴더를 쓴다."""
    override = os.environ.get("GRAPH_FAILURE_LOG_DIR", "").strip()
    return Path(override) if override else DEFAULT_DIR


def thread_of(config) -> str:
    """이 실행의 thread_id. Studio 는 UUID 를, `run_once.py` 는 `run1` 같은 이름을 준다."""
    try:
        value = ((config or {}).get("configurable") or {}).get("thread_id")
    except Exception:                                           # noqa: BLE001
        value = None
    return str(value or "local")


def step_of(config):
    try:
        return ((config or {}).get("metadata") or {}).get("langgraph_step")
    except Exception:                                           # noqa: BLE001
        return None


def path_for(thread: str) -> Path:
    """thread_id → 파일 이름. 영문 · 숫자가 아닌 글자가 섞이면 지문 8자를 붙인다 —
    한글 이름 둘(`첫실행` · `두번째`)이 같은 `_.jsonl` 로 합쳐지지 않게."""
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", thread)[:80].strip("_") or "run"
    if safe != thread:
        safe += "-" + hashlib.sha1(thread.encode("utf-8")).hexdigest()[:8]
    return folder() / (safe + ".jsonl")


def _fingerprint(step, row: dict) -> str:
    """같은 걸음 · 같은 노드 · **같은 내용**이면 같은 지문. 시각(`at`)은 빼고 본다."""
    body = json.dumps({"step": step, **row}, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(body.encode("utf-8")).hexdigest()[:12]


def write(config, row: dict) -> str:
    """한 줄을 덧붙인다. 돌려주는 것: 기록한 파일의 상대 경로 (실패하면 빈 문자열).

    ★ 중복은 **내용까지 같을 때만** 거른다. 걸음 번호와 노드 이름만 보면, Studio 에서
      fork 해 다른 답을 고른 갈래(걸음 번호는 같고 내용은 다르다)가 통째로 사라진다.
    """
    try:
        thread = thread_of(config)
        step = step_of(config)
        path = path_for(thread)
        mark = _fingerprint(step, row)
        record = {"at": datetime.now().replace(microsecond=0).isoformat(),
                  "thread": thread, "step": step, **row, "mark": mark}
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    old = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if old.get("mark") == mark:
                    return _rel(path)                           # 똑같은 사건 — 이미 적었다
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return _rel(path)
    except Exception:                                           # noqa: BLE001
        return ""


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


__all__ = ["folder", "thread_of", "path_for", "write"]
