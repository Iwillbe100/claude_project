#!/usr/bin/env python3
"""LangSmith 노드별 실시간 추적 실증용 최소 그래프.

목적은 딱 하나다. "그래프를 한 번 돌렸을 때 노드마다 span 이 만들어져
LangSmith 에 실시간으로 올라가는가"를 증명하는 것. LLM 을 호출하지 않으므로
토큰 비용이 0 이고, 결과가 결정적이라 몇 번을 돌려도 같은 값이 나온다.

  ingest  ->  analyze  ->  report

이 파일은 두 가지 방식으로 쓰인다.
  1) 직접 실행  : python settings/smoke/smoke_graph.py
                  터미널에 노드별 상태 변화가 실시간으로 찍힌다.
  2) Agent Server: langgraph dev  (settings/smoke/langgraph.json 이 이 파일을 가리킨다)
                  Studio 화면에서 노드 그래프와 각 노드의 입출력을 눈으로 본다.

모듈 수준 `graph` 는 langgraph.json 이 참조하므로 이름을 바꾸지 말 것.
임포트만으로는 아무 부작용도 일어나지 않는다(파일 생성/네트워크 호출 없음).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import TypedDict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

# settings/smoke/smoke_graph.py -> parents[0]=smoke, [1]=settings, [2]=PROJECT_ROOT
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# LangGraph 를 임포트하기 전에 .env 를 올려야 트레이서가 켜진 상태로 초기화된다.
try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env", override=False)
except Exception:  # noqa: BLE001 - dotenv 가 없어도 그래프 자체는 돌아야 한다
    pass

from langgraph.config import get_stream_writer  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402

NODE_DELAY_SEC = 0.4  # 실시간 진행을 눈으로 확인할 수 있게 일부러 둔 지연

SAMPLE_LOG = """2026-09-04 09:00:01 INFO  service started
2026-09-04 09:00:05 WARN  cache miss ratio 0.42
2026-09-04 09:00:09 ERROR upstream timeout after 3000ms
2026-09-04 09:00:11 info  heartbeat ok
2026-09-04 09:00:14 ERROR upstream timeout after 3000ms
not-a-log-line
2026-09-04 09:00:20 DEBUG connection pool size 8"""


class SmokeState(TypedDict, total=False):
    """그래프가 노드를 지나며 채워 나가는 상태."""

    raw: str
    lines: list[str]
    invalid: int
    counts: dict[str, int]
    report: str


def _emit(event: str, **fields) -> None:
    """LangGraph custom 스트림으로 진행 상황을 흘린다.

    그래프 실행 컨텍스트 밖(단위 테스트 등)에서는 writer 가 없으므로 조용히 무시한다.
    """
    try:
        writer = get_stream_writer()
    except Exception:  # noqa: BLE001
        return
    if writer:
        writer({"event": event, **fields})


# --------------------------------------------------------------------------- #
# 노드 1 : 원문을 줄 단위로 쪼갠다
# --------------------------------------------------------------------------- #
def ingest(state: SmokeState) -> SmokeState:
    _emit("ingest:start")
    time.sleep(NODE_DELAY_SEC)
    raw = state.get("raw") or SAMPLE_LOG
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    _emit("ingest:done", line_count=len(lines))
    return {"raw": raw, "lines": lines}


# --------------------------------------------------------------------------- #
# 노드 2 : 로그 레벨을 집계한다 (대소문자 무시)
# --------------------------------------------------------------------------- #
def analyze(state: SmokeState) -> SmokeState:
    _emit("analyze:start", line_count=len(state.get("lines", [])))
    time.sleep(NODE_DELAY_SEC)
    levels = ("DEBUG", "INFO", "WARN", "ERROR")
    counts = {lv: 0 for lv in levels}
    invalid = 0
    for line in state.get("lines", []):
        parts = line.split()
        level = parts[2].upper() if len(parts) >= 3 else ""
        if level in counts:
            counts[level] += 1
        else:
            invalid += 1
    _emit("analyze:done", counts=counts, invalid=invalid)
    return {"counts": counts, "invalid": invalid}


# --------------------------------------------------------------------------- #
# 노드 3 : 사람이 읽을 요약을 만든다
# --------------------------------------------------------------------------- #
def report(state: SmokeState) -> SmokeState:
    _emit("report:start")
    time.sleep(NODE_DELAY_SEC)
    counts = state.get("counts", {})
    total = len(state.get("lines", []))
    body = ", ".join(f"{k}={v}" for k, v in counts.items())
    text = f"총 {total}줄 / {body} / 형식오류={state.get('invalid', 0)}"
    _emit("report:done", report=text)
    return {"report": text}


def build_graph() -> StateGraph:
    """노드/엣지 정의. Studio 와 CLI 가 같은 그래프를 쓰도록 한 곳에만 둔다."""
    g = StateGraph(SmokeState)
    g.add_node("ingest", ingest)
    g.add_node("analyze", analyze)
    g.add_node("report", report)
    g.add_edge(START, "ingest")
    g.add_edge("ingest", "analyze")
    g.add_edge("analyze", "report")
    g.add_edge("report", END)
    return g


# langgraph.json 이 참조하는 심볼. 체크포인터는 붙이지 않는다
# (Agent Server 가 스레드/런 영속화를 직접 담당하기 때문).
graph = build_graph().compile(name="smoke")

__all__ = ["graph", "build_graph", "SmokeState"]


# --------------------------------------------------------------------------- #
# 직접 실행 : 노드별 상태를 실시간으로 출력하고 LangSmith 트레이스 링크를 안내한다
# --------------------------------------------------------------------------- #
def _mask(v: str) -> str:
    v = (v or "").strip()
    if not v:
        return "(비어 있음)"
    for p in ("lsv2_pt_", "lsv2_sk_", "ls__"):
        if v.startswith(p):
            return f"{p}**** ({len(v)}자)"
    return f"{v[:2]}**** ({len(v)}자)"


def _short(value, limit: int = 70) -> str:
    """터미널 한 줄을 넘기지 않게 값을 줄인다(상태 변화만 보이면 되므로)."""
    text = repr(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _run_cli() -> int:
    import os

    tracing = os.environ.get("LANGSMITH_TRACING", "").strip().lower() in {"1", "true", "yes", "on"}
    project = os.environ.get("LANGSMITH_PROJECT", "default")

    print("=" * 78)
    print(" LangSmith 노드별 추적 스모크 테스트")
    print("=" * 78)
    print(f" LANGSMITH_TRACING = {os.environ.get('LANGSMITH_TRACING', '(없음)')}")
    print(f" LANGSMITH_PROJECT = {project}")
    print(f" LANGSMITH_API_KEY = {_mask(os.environ.get('LANGSMITH_API_KEY', ''))}")
    print("-" * 78)

    if not tracing:
        print(" [WARN] 트레이싱이 꺼져 있습니다. 그래프는 돌지만 LangSmith 에는 아무것도")
        print("        올라가지 않습니다. .env 의 LANGSMITH_TRACING 을 true 로 바꾸십시오.")
        print("-" * 78)

    run_tree = None
    ctx = None
    if tracing:
        try:
            from langsmith import trace as ls_trace

            ctx = ls_trace(name="smoke_run", run_type="chain", project_name=project)
            run_tree = ctx.__enter__()
        except Exception as exc:  # noqa: BLE001 - 추적 실패가 스모크를 깨뜨리면 안 된다
            print(f" [WARN] 트레이스 컨텍스트 생성 실패: {exc.__class__.__name__}")
            ctx = None

    started = time.time()
    final: dict = {}
    try:
        for mode, chunk in graph.stream({"raw": SAMPLE_LOG}, stream_mode=["updates", "custom"]):
            elapsed = time.time() - started
            if mode == "custom" or not isinstance(chunk, dict):
                print(f" [{elapsed:6.2f}s] custom   {chunk}")
            else:
                for node, payload in chunk.items():
                    if not isinstance(payload, dict):
                        print(f" [{elapsed:6.2f}s] NODE OK  {node:<8} -> {_short(payload)}")
                        continue
                    keys = ", ".join(f"{k}={_short(payload[k])}" for k in list(payload)[:3])
                    print(f" [{elapsed:6.2f}s] NODE OK  {node:<8} -> {keys}")
                    final.update(payload)
    except Exception as exc:  # noqa: BLE001
        print(f"\n [FAIL] 그래프 실행 중 예외: {exc.__class__.__name__}: {exc}")
        if ctx is not None:
            try:
                ctx.__exit__(*sys.exc_info())
            except Exception:  # noqa: BLE001
                pass
        print("\nSMOKE_TRACE: FAIL")
        return 1

    if ctx is not None:
        try:
            if run_tree is not None:
                run_tree.end(outputs={"report": final.get("report", "")})
            ctx.__exit__(None, None, None)
        except Exception:  # noqa: BLE001
            pass

    print("-" * 78)
    print(f" 최종 결과 : {final.get('report', '(없음)')}")

    if tracing:
        url = None
        try:
            from langsmith import Client

            client = Client()
            try:
                client.flush()
            except Exception:  # noqa: BLE001
                pass
            if run_tree is not None:
                # get_run_url() 은 2027-01-31 이후 제거 예정이지만, 대체 API
                # (client.runs.get_url)는 async 인 데다 project_id/trace_id 를
                # 직접 넘겨야 해서 스모크 테스트에는 과하다. 경고만 눌러 둔다.
                import warnings

                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", DeprecationWarning)
                    url = client.get_run_url(run=run_tree)
        except Exception:  # noqa: BLE001
            url = None
        print("-" * 78)
        if url:
            print(f" 트레이스 : {url}")
        else:
            print(f" 트레이스 : https://smith.langchain.com/  ->  프로젝트 '{project}' 에서 확인")
        print(" 열어 보면 smoke_run 아래에 ingest / analyze / report 가 각각")
        print(" 별도 span 으로 쌓여 있어야 합니다. (전송에 몇 초 걸릴 수 있습니다)")

    print("\nSMOKE_TRACE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_cli())
