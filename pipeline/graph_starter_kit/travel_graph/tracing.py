"""LangSmith 트레이스에 `claude -p` 안쪽을 **보이게** 만드는 곳. **킷 소유 — 수정 금지.**

그래프 노드는 LangGraph 가 알아서 트레이스에 올린다. 그런데 이 킷의 조사·판정은
`claude -p` **서브프로세스**라서, LangSmith 입장에서는 그 상자 안이 비어 있다.
노드가 몇 초 걸렸는지는 보이는데 **무엇을 물었고 무엇을 검색했는지**는 안 보인다.

여기서 그 상자를 연다. 새 패키지는 쓰지 않는다 — `langsmith` 는 이미 lock 에 있다.

    collect_city                             (chain)   ← LangGraph 가 만든다
    ├ claude -p · collect_city[하노이] 명소   (llm)     ← 이 파일이 만든다
    │ ├ 1 WebSearch                          (tool)    질의어 → 검색 결과
    │ ├ 2 WebFetch                           (tool)
    │ └ JSON 블록 추출                        (parser)  마지막 텍스트 → dict
    └ claude -p · collect_city[하노이] 일정   (llm)     (같은 모양 — 한 노드가 두 번 부른다)

## 왜 `@traceable` 이 아니라 `RunTree` 인가

`@traceable` 은 함수 하나를 run 하나로 만든다. 그런데 우리가 그리고 싶은 것은
**한 호출 안의 여러 턴**이다. 턴은 스트림을 읽어야 알 수 있고, 읽는 도중에
자식을 하나씩 열고 닫아야 Studio 를 보는 사람이 **진행되는 것을 실시간으로** 본다.
그래서 트리를 직접 만든다.

## 이 파일의 절대 규칙

**어떤 경우에도 그래프를 죽이지 않는다.** 트레이싱은 관찰 장치이지 실행 경로가
아니다. 부모 run 이 없으면(트레이싱 꺼짐 · 노드 밖에서 호출) 조용히 아무 것도
하지 않고, 전송이 실패해도 삼킨다. 관찰이 안 되는 것과 실행이 죽는 것은
전혀 다른 사고다.

## 끄는 법

    GRAPH_TRACE_CLAUDE=0    이 파일을 통째로 끈다 (노드 트레이스는 그대로 남는다)
    GRAPH_TRACE_TOOLS=0     llm run 만 남기고 턴별 자식은 만들지 않는다
                            (LangSmith 무료 등급에서 run 수를 아끼고 싶을 때)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

#: 도구 결과·프롬프트를 그대로 올리면 트레이스가 무거워지고 화면에서 읽기도 어렵다.
#: 교육 목적에는 앞부분이면 충분하다. 자른 자리는 눈에 보이게 표시한다.
MAX_TEXT = int(os.environ.get("GRAPH_TRACE_MAX_TEXT", "4000"))


def enabled() -> bool:
    return os.environ.get("GRAPH_TRACE_CLAUDE", "1") not in ("0", "false", "False")


def tools_enabled() -> bool:
    return os.environ.get("GRAPH_TRACE_TOOLS", "1") not in ("0", "false", "False")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clip(value, limit: int = MAX_TEXT) -> str:
    """길면 자르고 **자른 사실을 적는다.** 조용히 자르면 없는 줄 안다."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n… (총 {len(text):,}자 중 앞 {limit:,}자만 표시)"


def _parent():
    """지금 실행 중인 LangGraph 노드의 run. 없으면 None.

    ★ 스레드에서 부르면 `None` 이 나온다. 부모를 찾는 통로가 contextvar 인데
      `ThreadPoolExecutor.submit` 은 그것을 옮겨 주지 않기 때문이다.
      예전에 `research` 노드가 스레드로 도시를 동시에 부를 때는 `contextvars.copy_context()`
      로 감싸야 했다. 지금은 재수집이 `Send` fan-out 이라 LangGraph 가 그 일을 대신한다.
      실측: 그냥 submit -> None / copy_context -> 노드 run 을 정확히 잡는다.
    """
    try:
        from langsmith.run_helpers import get_current_run_tree
        return get_current_run_tree()
    except Exception:                                           # noqa: BLE001
        return None


class ClaudeTrace:
    """`claude -p` 한 번을 트레이스 한 그루로 만든다.

    쓰는 쪽은 성공/실패를 신경 쓰지 않는다. 이 객체는 **아무 것도 못 하는 상태**로도
    정상 동작한다 (모든 메서드가 조용히 지나간다).
    """

    def __init__(self, label: str, prompt: str, metadata: dict):
        self.run = None
        self.tools: dict = {}
        self.count = 0
        if not enabled():
            return
        parent = _parent()
        if parent is None:
            return
        try:
            self.run = parent.create_child(
                name=f"claude -p · {label}",
                run_type="llm",
                inputs={"messages": [{"role": "user", "content": _clip(prompt, 20000)}]},
                extra={"metadata": dict(metadata)},
                start_time=_now(),
            )
            self.run.post()
        except Exception:                                       # noqa: BLE001
            self.run = None

    # ---- 턴 ---------------------------------------------------------------

    def tool_start(self, tool_id: str, name: str, tool_input) -> None:
        """도구 호출이 **시작될 때** 자식을 연다. 닫히기 전에 화면에 나타난다."""
        if self.run is None or not tools_enabled():
            return
        self.count += 1
        try:
            child = self.run.create_child(
                name=f"{self.count} {name}",
                run_type="tool",
                inputs=tool_input if isinstance(tool_input, dict) else {"input": _clip(tool_input)},
                start_time=_now(),
            )
            child.post()
            self.tools[tool_id] = child
        except Exception:                                       # noqa: BLE001
            pass

    def tool_end(self, tool_id: str, output, is_error: bool = False) -> None:
        child = self.tools.pop(tool_id, None)
        if child is None:
            return
        try:
            if is_error:
                child.end(error=_clip(output), end_time=_now())
            else:
                child.end(outputs={"결과": _clip(output)}, end_time=_now())
            child.patch()
        except Exception:                                       # noqa: BLE001
            pass

    # ---- 마무리 -----------------------------------------------------------

    def parsed(self, text: str, payload, error: str = "") -> None:
        """마지막 텍스트에서 ```json 블록을 꺼낸 결과를 따로 보여 준다.

        이 킷에서 가장 자주 나는 실패가 "JSON 블록을 찾지 못했습니다" 이다.
        무엇을 받아서 무엇을 꺼냈는지 나란히 두면 원인이 한눈에 보인다.
        """
        if self.run is None or not tools_enabled():
            return
        try:
            child = self.run.create_child(
                name="JSON 블록 추출", run_type="parser",
                inputs={"모델이 낸 마지막 텍스트": _clip(text)},
                start_time=_now(),
            )
            child.post()
            if error:
                child.end(error=error, end_time=_now())
            else:
                child.end(outputs={"꺼낸 값": payload}, end_time=_now())
            child.patch()
        except Exception:                                       # noqa: BLE001
            pass

    def finish(self, *, text: str, payload, metadata: dict) -> None:
        #  ★ 결과 줄이 오기 전에 호출이 끝난 도구 턴을 닫는다. 예전에는 `fail()` 만 닫아서,
        #    성공한 호출에도 열린 tool 자식이 남아 LangSmith 에 **pending run** 이 떠 있었다
        #    ("아직 도는 중인가?"로 읽힌다).
        for tool_id in list(self.tools):
            self.tool_end(tool_id, "(결과 줄이 오기 전에 호출이 끝났습니다)")
        if self.run is None:
            return
        try:
            extra = dict(self.run.extra or {})
            merged = dict(extra.get("metadata") or {})
            merged.update(metadata)
            extra["metadata"] = merged
            self.run.extra = extra
            self.run.end(
                outputs={
                    "choices": [{"message": {"role": "assistant", "content": _clip(text)}}],
                    "결과 JSON": payload,
                    "usage_metadata": {
                        "input_tokens": metadata.get("입력 토큰", 0),
                        "output_tokens": metadata.get("출력 토큰", 0),
                        "total_tokens": (metadata.get("입력 토큰", 0)
                                         + metadata.get("출력 토큰", 0)),
                    },
                },
                end_time=_now(),
            )
            self.run.patch()
        except Exception:                                       # noqa: BLE001
            pass
        finally:
            self.run = None

    def fail(self, reason: str, metadata: dict | None = None) -> None:
        """실패도 **트레이스에 남긴다.** 빨간 run 이 없으면 폴백을 못 알아본다."""
        for tool_id in list(self.tools):
            self.tool_end(tool_id, "(호출이 끝나기 전에 중단되었습니다)", is_error=True)
        if self.run is None:
            return
        try:
            if metadata:
                extra = dict(self.run.extra or {})
                merged = dict(extra.get("metadata") or {})
                merged.update(metadata)
                extra["metadata"] = merged
                self.run.extra = extra
            self.run.end(error=reason, end_time=_now())
            self.run.patch()
        except Exception:                                       # noqa: BLE001
            pass
        finally:
            self.run = None


__all__ = ["ClaudeTrace", "enabled", "tools_enabled"]
