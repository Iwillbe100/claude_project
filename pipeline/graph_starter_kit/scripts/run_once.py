#!/usr/bin/env python3
"""Studio 없이 터미널에서 그래프를 한 번 돌린다. **킷 소유 — 수정 금지.**

Studio 는 그림이 예쁘지만 켜는 데 시간이 걸린다. STEP 3·4 처럼 **구조가 맞는지만**
빠르게 보고 싶을 때 이것을 쓴다. `interrupt` 가 걸리면 터미널에서 답한다.

  python scripts/run_once.py                         live 모드 (기본)
  python scripts/run_once.py --mode replay           인계본 자료로 수집은 10초 안에
  python scripts/run_once.py --auto proceed,done,done  게이트를 자동으로 답하고 끝까지
  python scripts/run_once.py --mode replay --inject image_dead
                                                     그 실패를 재현해 처방 가지를 켠다 (inject)

**게이트 B는 두 번 선다.** 정성 3회 전에 한 번, 3회 뒤에 한 번. 그래서 `--auto` 에
답을 **세 개** 준다 (`게이트A, 게이트B(정성 시작), 게이트B(확정)`).

`--auto` 는 시연·검증용이다. 실습에서는 답을 직접 입력하십시오.

**답이 없으면 그 게이트에서 끝낸다.** `--auto` 의 답을 다 썼거나, 표준입력이 터미널이
아니면(에이전트 · 파이프 · Windows 의 NUL) 권장값으로 넘어가지 않고 **거기서 멈춘다.**
예전에는 권장값으로 넘어가 게이트 B 에서 `done` → 정성 3회(`claude -p`, 6~12분)까지
들어갔다. 그래서 확인용 실행은 이렇게 짧게 쓴다.

  루프 A 만 보기    --mode replay --auto stop          게이트 A 에서 끝
  루프 B 까지 보기  --mode replay --auto proceed       게이트 A 통과 → 게이트 B 에서 끝

처방 가지가 한도를 다 쓰면 그 루프의 게이트에서 한 번 더 멈출 수 있다 — 그때는 `--auto` 의
답이 하나씩 밀린다.

`--inject` 는 처방 가지 이름(쉼표로 여럿)을 받는다. Studio 에서는 입력 칸에
`{"inject": ["image_dead"]}` 를 넣는 것과 같다. 고를 수 있는 이름은
`travel_graph/detours/registry.py` 에 있다.

> `replay` 라도 **정성 3회는 실제로 `claude -p` 판정을 수행**하므로 6~12분이 더 든다.
> 구조만 빠르게 보고 싶으면 `--auto proceed` 로 돌려 게이트 B 에서 스스로 끝나게 하고
> `python scripts/verify_all.py --skip-quality` 로 확인한다. 게이트 B 에 `stop` 을 적으면
> 멈추지 않는다 — 이 게이트의 답이 아니라서 기본값 `done`(정성 시작)으로 간다.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from _contract import use_utf8_output  # noqa: E402

use_utf8_output()
LINE = "=" * 66


def main():
    parser = argparse.ArgumentParser(description="그래프 한 번 실행")
    parser.add_argument("--mode", choices=["live", "replay"], default=None,
                        help="비우면 GRAPH_MODE 환경변수, 그것도 없으면 live")
    parser.add_argument("--thread", default="",
                        help="thread_id. 비우면 실행마다 새 이름(run-시각) — 실패 기록 파일도 실행마다 따로 생긴다")
    parser.add_argument("--auto", default="",
                        help="게이트 답을 쉼표로 미리 준다 (게이트 B가 두 번 서므로 예: proceed,done,done)")
    parser.add_argument("--inject", default="",
                        help="실패 재현(inject) — 처방 가지 이름을 쉼표로 (예: image_dead,encoding)")
    args = parser.parse_args()

    if args.mode:
        os.environ["GRAPH_MODE"] = args.mode
    #  ★ thread_id 하나가 "한 번의 실행"이다. 늘 같은 이름을 쓰면 실행 둘이 실패 기록
    #    파일 하나(evidence/failures/<thread_id>.jsonl)에 섞인다. 그래서 기본값은 시각이다.
    if not args.thread:
        args.thread = time.strftime("run-%Y%m%d-%H%M%S")

    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import Command

    from travel_graph import research
    from travel_graph.build import compile_graph

    from travel_graph import detours
    from travel_graph.detours import log

    graph = compile_graph(InMemorySaver())
    #  재귀 한도 — 처방 가지 한 번이 걸음 넷(fix · test · 검사기 · 진단)을 더 쓰고, 재시도마다
    #  둘(fix · test)이 는다. 넉넉히 둔다.
    config = {"configurable": {"thread_id": args.thread}, "recursion_limit": 150}
    auto = [a.strip() for a in args.auto.split(",") if a.strip()]
    planted, unknown = detours.parse_inject(args.inject)
    if unknown:
        print(f" 모르는 처방 가지 이름: {', '.join(unknown)}  "
              f"(고를 수 있는 것: {', '.join(d.kind for d in detours.ALL)})")
        return 1

    print(LINE)
    print(f" 그래프 1회 실행 — 모드 {research.mode()} · thread {args.thread}"
          + (f" · 실패 재현 {', '.join(planted)}" if planted else ""))
    print(LINE)

    started = time.time()
    payload = {"inject": planted} if planted else {}
    step = 0
    gates = []
    stopped_at = ""

    while True:
        for chunk in graph.stream(payload, config=config, stream_mode="updates"):
            for node, update in (chunk or {}).items():
                if node == "__interrupt__":
                    continue
                step += 1
                print(f" [{time.time() - started:6.1f}s] {step:2d}  {node}")
                if isinstance(update, dict):
                    for key in ("info_verdict", "page_verdict", "quality_verdict",
                                "quality_pass", "html_path", "failure_kind", "detour_verdict",
                                "gate_a_answer", "gate_b_answer"):
                        if key in update:
                            print(f"              {key} = {update[key]}")
                    if "cities" in update:
                        print(f"              cities += {len(update['cities'])}")

        state = graph.get_state(config)
        if not state.tasks or not any(t.interrupts for t in state.tasks):
            break

        request = [i.value for t in state.tasks for i in t.interrupts][0]
        gates.append(state.next[0] if state.next else "?")
        print("")
        print(LINE)
        print(" ⏸  사람 차례 — 그래프가 멈췄습니다")
        print(LINE)
        for key, value in request.items():
            if isinstance(value, dict):
                print(f" {key}:")
                for k, v in value.items():
                    print(f"    {k:<10}{v}")
            elif isinstance(value, list) and any(isinstance(v, dict) for v in value):
                #  ② 왜 — 원인 묶음. 한 원인에 한 덩어리로 읽히게 찍는다.
                print(f" {key}:")
                for row in value[:6]:
                    if not isinstance(row, dict):
                        print(f"    · {row}")
                        continue
                    print(f"    · {row.get('원인')}  ({row.get('몇 곳')})")
                    if row.get("고치려면"):
                        print(f"        고치려면  {row.get('고치려면')}")
                    if row.get("예"):
                        print(f"        예        {row.get('예')}")
            elif isinstance(value, list):
                print(f" {key}: " + ", ".join(str(v) for v in value[:6]))
            else:
                print(f" {key}: " + str(value).replace("\n", "\n" + " " * (len(key) + 3)))
        print(LINE)

        answer = None
        if auto:
            answer = auto.pop(0)
            print(f" (--auto) → {answer}")
        elif args.auto:
            print(" (--auto) 답을 다 썼습니다 — 이 게이트에서 끝냅니다.")
        elif sys.stdin.isatty():
            try:
                print(" action 하나를 적고, 지시문(note)이 있으면 한 칸 띄고 이어 적습니다.")
                print("   예) more 이미지는 영문 파일명을 우선 쓰고 Commons 에서 확인한 것만 써라")
                answer = input(" 답 > ").strip()
            except EOFError:
                print("")
                print(" 입력이 없습니다 — 이 게이트에서 끝냅니다.")
        else:
            print(" 표준입력이 터미널이 아닙니다 — 권장값으로 넘어가지 않고 이 게이트에서 끝냅니다.")
        if answer is None:
            stopped_at = gates[-1]
            break
        payload = Command(resume={"action": answer, "note": ""})
        print("")

    final = graph.get_state(config).values
    print("")
    print(LINE)
    print(" 끝났습니다")
    print(LINE)
    print(f" 걸린 시간   : {time.time() - started:.1f}초")
    print(f" 루프 A      : {final.get('loop_a_iter')}바퀴  판정 {final.get('info_verdict')}")
    print(f" 루프 B      : {final.get('loop_b_iter')}바퀴  판정 {final.get('page_verdict')}")
    print(f" 루프 C      : {final.get('quality_pass', 0)}/"
          f"{final.get('quality_passes_required', 3)}회  판정 {final.get('quality_verdict')}")
    print(f" 사람 호출   : {len(gates)}회 — " + (" → ".join(gates) or "없음")
          + (f"   ({stopped_at} 에서 답 없이 끝냄)" if stopped_at else ""))
    taken = [h.split(":")[0] for h in (final.get("history") or []) if h.startswith("fix_")]
    log_path = log.path_for(args.thread)          # 한글 이름 · GRAPH_FAILURE_LOG_DIR 도 그대로
    try:
        log_path = log_path.resolve().relative_to(ROOT)
    except ValueError:
        pass
    print(f" 처방 가지   : " + (" → ".join(taken) if taken else "타지 않음")
          + "   (실패 기록: " + log_path.as_posix() + ")")
    print(f" 결과물      : {final.get('html_path') or '(만들지 않음)'}")
    shorts = ((final.get("info_short_slots") or []) + (final.get("page_short_slots") or [])
              + (final.get("quality_short_slots") or []))
    print(f" 못 채운 칸  : {len(shorts)}건" + (" — " + shorts[0] if shorts else ""))
    print("")
    #  ★ 문서가 인용하는 history 줄을 **그대로** 보여 준다 — 검사기 · 진단 · 처방 가지 · 게이트.
    #    Studio 에서는 결과 패널의 `history` 로 같은 줄을 본다. 06_DETOUR 의 빨간불 · 초록불
    #    기록(red_seen · green_seen)은 여기서 옮겨 적는다.
    keep = ("check_information", "check_page", "diagnose_", "fix_", "test_", "human_gate")
    lines, show = [], False
    for line in final.get("history") or []:
        if line.startswith(keep):
            show = True
            lines.append(line)
        elif line.startswith("  ") and show:
            lines.append(line)
        else:
            show = False
    print(" history — 검사기 · 진단 · 처방 가지 · 게이트 줄만")
    for line in lines:
        print("   " + line)
    print("")
    print(" 다음: python scripts/verify_all.py")
    print(LINE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
