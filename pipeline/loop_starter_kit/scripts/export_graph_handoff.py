#!/usr/bin/env python3
"""그래프 킷으로 넘길 인계 폴더를 만든다.

루프를 다 돌리고 나면, 그 결과를 다음 실습(그래프)으로 넘겨야 한다.
이때 MASTER_SPEC.md 의 검사 계약을 통째로 복사해 붙여넣는 것은 좋지 않다.
그래프를 '설계'하는 데 필요한 것과 그래프 결과를 '채점'하는 데 필요한 것이
서로 다르기 때문이다.

  설계에 필요한 것   노드 · 간선 · 상태 · 종료 조건 · 실제로 일어난 일
  채점에 필요한 것   검사 계약 (숫자와 이름표)

그래서 이 스크립트는 둘을 나누어 output/graph/ 에 넣는다.

  00_START_HERE.md     무엇을 어떤 순서로 쓰는가
  01_HANDOFF.md        ★ 그래프 설계용. 이것만 붙여넣으면 된다
  02_USER_REQUEST.md   취향 원문 (요약본으로는 15줄 설명이 안 나온다)
  03_CONTRACT.json     검사 계약. 그래프 결과를 같은 기준으로 채점한다
  04_RUN_EVIDENCE.md   실측. 어디에 구멍이 났는지 = 처방 가지 후보가 어디인지
  05_STATE_SEED.json   그래프 초기 상태(참고). graph.invoke() 에 넣어도 되지만 입력 5칸만 쓰인다
  research_data.json   루프가 모은 정보 원본 사본 (최상위 country · days 가 없으면
                       request 에서 채워 넣는다 — 그래프 킷이 최상위에서 읽는다)

종료 코드
  0  만들었다
  1  명세가 깨져서 만들 수 없다 (사람이 고쳐야 한다)
  2  만들었지만 루프가 아직 안 끝났다 (인계본에 '미완성'으로 표시했다)
     = 파일·기록이 빠졌거나, 파일이 다 있어도 verify_all 판정이 SUCCESS 가 아니다
       (루프 A · B · C 중 PASS 가 아닌 것이 있다 — 아래 overall_verdict)

사용법
  python scripts/export_graph_handoff.py
  python scripts/export_graph_handoff.py --run-id 2026-09-05T14-20-05
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _contract import (  # noqa: E402
    ContractError,
    check_contract_shape,
    load_machine_json,
    load_research,
    find_nulls,
    use_utf8_output,
)

use_utf8_output()

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = "output/graph"
LINE = "=" * 66

# 루프의 작업 8개가 그래프에서 무엇이 되는가.
# 이 표가 이 스크립트의 핵심이다. 1:1 로 옮기지 않는다는 것이 요점이다.
TASK_TO_NODE = [
    ("TASK-입력읽기", "read_request", "노드",
     "요청서를 읽어 상태의 입력 칸을 채운다"),
    ("TASK-국가정보", "collect_country", "노드 · 병렬",
     "도시와 무관하므로 도시 선정과 나란히 돌 수 있다"),
    ("TASK-도시선정", "select_cities", "노드",
     "여기서 도시 수가 정해져야 뒤쪽 병렬 폭이 결정된다"),
    ("TASK-명소수집", "collect_city", "노드 · 도시별 병렬",
     "도시끼리 서로의 결과를 안 보므로 fan-out 가능"),
    ("TASK-일정수집", "collect_city 에 합침", "-",
     "같은 도시의 명소만 참조한다. 책임도 재시도 전략도 같으므로 노드를 나누지 "
     "않는다. 다만 한 응답에 다 담으면 분량이 잘리므로 **노드 안에서 호출만** "
     "두 번 한다 (명소 -> 일정). 노드 경계와 호출 단위는 다른 문제다"),
    ("TASK-페이지생성", "build_page", "노드",
     "모든 수집이 끝난 뒤 한 번만 돈다"),
    ("TASK-기능점검", "(간선)", "노드가 아니다",
     "check_page -> diagnose_page -> build_page 로 되돌아가는 간선(진단 B 뒤 "
     "route_after_page 의 retry)이 이 일을 대신한다"),
    ("TASK-정성점검", "quality_pass", "노드 · 순차 3회",
     "회차 번호가 상태에 있어야 라우터가 셀 수 있다. 앞 회차의 출력이 자기 입력이라 "
     "**병렬이 아니라 순환**으로만 돈다"),
]

# 루프에서는 노드가 아니었는데 그래프에서는 노드가 되는 것들
NEW_NODES = [
    ("check_information", "검사기 A",
     "라우터가 읽을 판정 값을 상태에 써야 하므로 노드가 된다"),
    ("check_page", "검사기 B",
     "같은 이유. 판정이 상태에 남아야 간선이 조건을 볼 수 있다"),
    ("human_gate_a", "되물음 ①",
     "interrupt 로 멈추고 사람의 답을 상태에 받아 적는다"),
    ("human_gate_b", "되물음 ②",
     "같은 이유. 선택지가 달라서 노드를 따로 둔다. 정성 3회 전후로 **두 번 선다**"),
    ("check_quality", "검사기 C",
     "품질이 아니라 절차(3회를 규율대로 돌았는가)를 판정해 상태에 쓴다"),
    ("repair_city", "RESEARCH 행동 (루프 안의 분기)",
     "재수집도 fan-out 이다. 검사기가 지적한 도시만 Send 로 받는다. 첫 수집과 "
     "한 노드로 두면 지적 없는 도시가 첫 수집으로 떨어져 통째로 다시 뽑힌다"),
    ("rebuilder", "없음",
     "사람이 게이트에 적은 지시문을 실제로 소비하는 자리. build_page 는 결정론 "
     "렌더러라 지시문을 받을 데가 없다"),
    ("repair_country", "RESEARCH 행동",
     "국가 소개도 지적된 칸만 patch 로 고친다. 도시와 같은 fan-out 을 탄다. "
     "수집 노드로 되돌아가면 합류가 다른 갈래를 영영 기다려 조용히 멈추므로 "
     "재수집은 반드시 별도 노드여야 한다"),
    ("diagnose_info", "없음 (루프는 모든 실패를 '한 바퀴 더'로 뭉쳤다)",
     "검사기 A 바로 뒤. **판정**(기준을 채웠나) 다음에 **원인**(무엇이 터졌나)을 "
     "가려 `failure_kind` 를 상태에 쓴다. 그래야 라우터가 처방 가지를 고를 수 있다. "
     "판정이 PASS 여도 돈다 · 결정론"),
    ("diagnose_page", "없음",
     "검사기 B 바로 뒤. 같은 이유. 검사기는 사진이 '있는가'만 보므로 화면 규격 "
     "같은 결함은 진단이 따로 잡는다"),
]

# 위 NEW_NODES 중 **진단 노드**. 나머지는 루프 골격이다 (루프 골격 14 = 작업에서 온 6 + 새로 생긴 8).
DIAGNOSE_NODES = ("diagnose_info", "diagnose_page")

# 규칙 처방 가지 — 진단 노드에서만 갈라진다. **한 줄 = 처방 가지 하나 = 노드 두 개**
# (fix_<kind> 고치는 법 -> test_<kind> 시험지). 합격하면 그 루프의 검사기로 돌아간다.
#
# ★ 이것은 그래프 킷 **기본 3개의 사본**이다. 진짜 목록은 그래프 킷의
#   travel_graph/detours/registry.py 에 있고, 교육생은 실패 기록에 후보가 있을 때만
#   STEP 6 에서 한 줄씩 늘린다.
#   이 스크립트는 루프 킷에 있어 그 파일을 import 할 수 없으므로 그림과 설명용으로만
#   쓴다. 그래프 킷의 기본 처방 가지가 바뀌면 여기도 같이 고친다.
#   순서 = 등록 순서 = 진단 우선순위.
DETOURS = [
    {"kind": "encoding", "loop": "A", "title": "글자가 깨짐 (인코딩)",
     "fix": "fix_encoding", "test": "test_encoding",
     "returns_to": "check_information", "gate": "human_gate_a",
     "sees": "깨진 글자 · 모지바케 · 비ASCII 주소"},
    {"kind": "image_dead", "loop": "A", "title": "이미지 주소가 죽어 있음",
     "fix": "fix_image_dead", "test": "test_image_dead",
     "returns_to": "check_information", "gate": "human_gate_a",
     "sees": "열었더니 404 · 금지된 주소 형태 · 이미지가 아닌 페이지"},
    {"kind": "image_spec", "loop": "B", "title": "사진이 화면 규격에 안 맞음",
     "fix": "fix_image_spec", "test": "test_image_spec",
     "returns_to": "check_page", "gate": "human_gate_b",
     "sees": "원본 통째(width 없음) · 사진 틀 CSS 없음 · 가려진 사진"},
]

# 처방 한도 — 처방 가지 하나가 사람의 판단 없이 돌 수 있는 횟수
# (그래프 킷 travel_graph/detours/__init__.py 의 LIMIT)
DETOUR_LIMIT = 2

# events.jsonl 의 next_action 값 (LOOP_CONTRACT.md 7번 · state/README.md 3번).
#   실패 라우팅 5가지만 '실패'로 읽는다. 아래 셋은 정상 진행이다.
FAILURE_ROUTES = ("RETRY", "RESEARCH", "REVISE_SPEC", "HITL", "STOP")
PROGRESS_ACTIONS = ("REVERSE_QUESTION", "QUALITY", "DONE")  # 되물음 · 루프 C 남은 회차 · 최종 검증 통과

# 실측에서 보이는 구멍 -> 그래프에서 하는 일 (고정 규칙)
HOLE_RULES = [
    ("한 노드 안에서 특정 항목만 반복 실패",
     "처방 가지로 뺀다 — 진단 노드 뒤 fix -> test (루프 골격은 그대로)",
     "실패 단위와 재시도 단위를 같게 만든다"),
    ("매번 노드 전체가 다시 돈다",
     "노드 앞에 체크포인트를 둔다",
     "이미 채운 칸을 다시 모으지 않는다"),
    ("노드 하나가 유난히 오래 걸린다",
     "서로 안 건드리면 병렬로 쪼갠다",
     "같은 상태 필드에 쓰면 reducer 가 필요하다"),
    ("실패는 뒤 노드에서 터지는데 원인은 앞 노드",
     "앞 노드에 출력 검증을 붙인다",
     "틀린 값이 뒤로 흘러가지 않게 한다"),
    ("사람이 되물음에 매번 같은 답을 한다",
     "그 판단을 간선 조건으로 승격한다",
     "사람을 부르는 횟수를 줄인다"),
    ("셀 수 없는 결함이 남는다",
     "고정 예산 순환으로 닫는다",
     "판정 독립을 지키며 끝낸다"),
    ("검사기가 못 보는 결함이 있다 (판정은 PASS)",
     "진단 시험지를 만든다 — 진단과 합격을 같은 시험지로 본다",
     "계약은 그대로 두고 원인을 잡는다"),
]


# --------------------------------------------------------------------------
# 읽기
# --------------------------------------------------------------------------


def read_json(path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def latest_run_dir(root, run_id=None):
    runs = root / "evidence" / "runs"
    if not runs.is_dir():
        return None
    if run_id:
        target = runs / run_id
        return target if target.is_dir() else None
    dirs = sorted([p for p in runs.iterdir() if p.is_dir()])
    return dirs[-1] if dirs else None


def read_events(run_dir):
    """events.jsonl 을 한 줄씩 읽는다. 깨진 줄은 건너뛴다."""
    if run_dir is None:
        return []
    path = run_dir / "events.jsonl"
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return [e for e in events if isinstance(e, dict)]


def is_failure(event):
    """이 사건이 '실패'인가. 04_RUN_EVIDENCE 의 2 · 3 · 4 · 5 · 7번이 **모두 이 한 규칙**으로 센다.

      실패     failure_type 이 적힌 줄
               또는 next_action 이 실패 라우팅(RETRY · RESEARCH · REVISE_SPEC · HITL · STOP)이고
               검사기가 통과하지 않은 줄 (exit_code 가 0 이 아니다 — 명령을 못 돌린 null 포함)
      실패 아님 iteration 0 — 출발점(첫 빨간불 RED 확인). 반드시 SHORT 가 나오는 줄이다
               next_action 이 REVERSE_QUESTION · QUALITY · DONE · null — 정상 진행
                 (루프 C 회차의 exit 2 는 QUALITY 다. 남은 회차 때문이지 실패가 아니다)
               exit_code 0 — 통과한 줄은 라우팅 값이 적혀 있어도 실패가 아니다

    exit_code 만 보면 안 된다. 루프 C 와 RED 의 exit 2 는 '진행 중'이라는 뜻이다.
    """
    if event.get("iteration") in (0, "0"):
        return False
    if event.get("failure_type"):
        return True
    return (event.get("next_action") in FAILURE_ROUTES
            and event.get("exit_code") not in (0, "0"))


def read_shortfalls(root):
    """검사기를 직접 돌려 아직 못 채운 칸을 받아 온다."""
    try:
        import check_information_count as loop_a
        import check_page_contract as loop_b
    except Exception as exc:  # pragma: no cover
        return None, None, "검사기를 불러오지 못했습니다: " + str(exc)

    try:
        result_a = loop_a.run(str(root))
    except ContractError as exc:
        return None, None, str(exc)
    #  run() 은 계약 오류를 예외로 올리지 않고 ERROR 결과로 돌려준다 — 여기서 걸러
    #  '못 채운 칸 없음'으로 읽히지 않게 한다.
    if result_a.verdict == "ERROR":
        return result_a, None, " / ".join(result_a.broken) or "검사기 A 가 ERROR 로 끝났습니다"

    result_b = None
    if result_a.verdict == "PASS":
        try:
            result_b = loop_b.run(str(root))
        except ContractError as exc:
            return result_a, None, str(exc)
    return result_a, result_b, None


def read_quality(root, run_dir):
    """루프 C 판정. 기준선의 `verify_all` 칸을 **실제로 돌린 결과**로 적으려고 부른다."""
    try:
        import check_quality_passes as loop_c
        return loop_c.run(str(root), run_dir.name if run_dir else None)
    except Exception:  # noqa: BLE001 — 기준선 한 칸 때문에 인계본을 못 만들면 안 된다
        return None


def overall_verdict(result_a, result_b, result_c):
    """세 판정기 결과를 verify_all.py 와 같은 뜻으로 하나로 합친다 -> (종료 코드, ["A PASS", ...]).

    앞 루프가 PASS 가 아니면 뒤 루프를 돌리지 않으므로(read_shortfalls · read_quality)
    판정이 셋이 안 되면 SUCCESS 가 아니다. 04_RUN_EVIDENCE 8번 기준선과 종료 코드(0/2)가
    **같은 값**을 쓴다.
    """
    verdicts = []
    for name, result in (("A", result_a), ("B", result_b), ("C", result_c)):
        if result is not None:
            verdicts.append("{} {}".format(name, result.verdict))
    worst = "PASS"
    for part in verdicts:
        if part.endswith("ERROR"):
            worst = "ERROR"
            break
        if not part.endswith("PASS"):
            worst = "SHORT"
            break
    if len(verdicts) < 3 and worst == "PASS":
        worst = "SHORT"
    return {"PASS": 0, "ERROR": 1, "SHORT": 2}[worst], verdicts


# --------------------------------------------------------------------------
# 작은 도우미
# --------------------------------------------------------------------------


def as_dict(value):
    return value if isinstance(value, dict) else {}


def as_list(value):
    return value if isinstance(value, list) else []


def unknown(value, mark="(미확인)"):
    if value is None or value == "" or value == []:
        return mark
    return value


def city_names(data):
    names = []
    for city in as_list(as_dict(data).get("cities")):
        name = (as_dict(city).get("name") or "").strip()
        if name:
            names.append(name)
    return names


def safe_id(prefix, index):
    """머메이드 노드 아이디. 한글 이름은 아이디로 못 쓰므로 번호를 붙인다."""
    return prefix + str(index)


# --------------------------------------------------------------------------
# 01_HANDOFF.md
# --------------------------------------------------------------------------


def build_mermaid(cities, limits):
    """이번 실행의 도시 수에 맞춰 그래프 모양을 그린다."""
    n = len(cities) if cities else 0
    fan = cities if cities else ["도시1", "도시2", "도시3"]
    note = "" if cities else "  %% 도시가 아직 안 정해져 예시 3개로 그렸습니다"

    lines = ["flowchart TD"]
    if note:
        lines.append(note)

    #  루프 골격 노드 이름 -> 이 그림의 id. 처방 가지가 돌아가는 곳(검사기)과 넘기는 곳(게이트).
    spine_id = {"check_information": "CI", "check_page": "CP",
                "human_gate_a": "HG", "human_gate_b": "HG2"}
    router_id = {"A": "RA", "B": "RP"}

    def add_detours(loop):
        """루프 `loop` 의 처방 가지를 그린다. 진단 뒤 라우터에서만 갈라진다.

        ★ 처방 가지마다 **id 를 따로 쓴다** (FX1 · TX1 · RD1 · DT1 …). 세 시험 노드가
          `route_after_detour` 함수 하나를 같이 쓰지만, 그림에서 한 id 로 그리면
          mermaid 가 셋을 한 칸으로 합쳐 어느 시험이 어느 검사기로 돌아가는지
          안 보인다 (아래 route_after_page 주석과 같은 이유).
        """
        for index, d in enumerate(DETOURS, start=1):
            if d["loop"] != loop:
                continue
            box, fx, tx, rd = (safe_id("DT", index), safe_id("FX", index),
                               safe_id("TX", index), safe_id("RD", index))
            lines.append("")
            lines.append('    subgraph {}["▷ 처방 가지 {} · {}"]'.format(
                box, d["kind"], d["title"]))
            lines.append("        direction TB")
            lines.append('        {}["{}<br/>고치는 법"]'.format(fx, d["fix"]))
            lines.append('        {}["{}<br/>시험지"]'.format(tx, d["test"]))
            lines.append('        {}{{"route_after_detour"}}'.format(rd))
            lines.append("    end")
            lines.append('    {} -.->|"원인 = {}<br/>판정보다 먼저 · 한도 {}회 안"| {}'.format(
                router_id[loop], d["kind"], DETOUR_LIMIT, fx))
            lines.append("    {} --> {}".format(fx, tx))
            lines.append("    {} --> {}".format(tx, rd))
            lines.append('    {} -->|"back · 합격 → 검사기로 복귀<br/>바퀴를 쓰지 않음"| {}'.format(
                rd, spine_id[d["returns_to"]]))
            lines.append('    {} -->|"retry · 불합격 · 한도 안"| {}'.format(rd, fx))
            lines.append('    {} -->|"gate · 한도 끝"| {}'.format(rd, spine_id[d["gate"]]))
        lines.append("")

    lines.append('    START([START]) --> N1["read_request"]')
    lines.append('    N1 --> N2["collect_country"]')
    lines.append('    N1 --> N3["select_cities"]')
    lines.append("")
    lines.append('    subgraph FAN["도시별 병렬 · reducer 필요 (fan-out ①)"]')
    lines.append("        direction TB")
    for index, name in enumerate(fan, start=1):
        sid = safe_id("S", index)
        #  노드는 하나다. 그 안에서 claude 를 두 번 부른다 (명소 / 일정) —
        #  한 응답에 다 담으면 계약 분량이 잘림 임계에 붙기 때문이다.
        lines.append('        {}["collect_city<br/>{}<br/>(명소 → 일정, 호출 2회)"]'.format(
            sid, name))
    lines.append("    end")
    lines.append("")
    for index, name in enumerate(fan, start=1):
        lines.append("    N3 -.Send.-> {}".format(safe_id("S", index)))
        lines.append("    {} --> CI".format(safe_id("S", index)))
    lines.append("    N2 --> CI")
    lines.append("")
    lines.append('    CI["check_information<br/>판정을 상태에 쓴다"]')
    #  ★ 검사기 → 진단은 정적 간선 하나. 판정 다음에 원인을 가린다.
    lines.append('    CI --> DI["diagnose_info<br/>원인을 상태에 쓴다 (failure_kind)"]')
    lines.append('    DI --> RA{"route_after_info"}')
    add_detours("A")
    lines.append(
        '    RA -.->|"SHORT · {} 바퀴 미만<br/>Send × 지적된 도시만 (fan-out ②)"| '
        'RE["repair_city<br/>patch 로 고친다"]'.format(unknown(limits.get("A"), "상한")))
    lines.append(
        '    RA -.->|"SHORT · 기능1 부족이면<br/>Send × 국가 소개 (fan-out ②)"| '
        'RQ["repair_country<br/>patch 로 고친다"]')
    lines.append('    RA -->|"PASS · 상한 도달 · ERROR"| HG')
    lines.append("    RE --> CI")
    lines.append("    RQ --> CI")
    lines.append("")
    lines.append('    HG{{"human_gate_a<br/>되물음 · interrupt"}}')
    lines.append('    HG -.->|"more · Send × 지적된 도시만"| RE')
    lines.append('    HG -.->|"more · Send × 국가 소개"| RQ')
    lines.append('    HG -->|"proceed · 권장"| BP')
    lines.append('    HG -->|"stop"| GAP([HALT_RESEARCH_GAP])')
    lines.append("")
    lines.append('    BP["build_page<br/>travel_site.html"]')
    lines.append("    BP --> CP")
    lines.append('    CP["check_page<br/>판정을 상태에 쓴다"]')
    #  ★ 라우터와 노드에 **같은 id 를 쓰지 않는다.** mermaid 는 같은 id 를 한 노드로
    #    합쳐 버려서 route_after_page 와 rebuilder 가 한 칸이 된 그림이 나온다.
    lines.append('    CP --> DP["diagnose_page<br/>원인을 상태에 쓴다 (failure_kind)"]')
    lines.append('    DP --> RP{"route_after_page"}')
    add_detours("B")
    lines.append('    RP -->|"SHORT · {} 바퀴 미만"| BP'.format(
        unknown(limits.get("B"), "상한")))
    lines.append('    RP -->|"PASS · 상한 도달 · ERROR"| HG2')
    lines.append('    HG2{{"human_gate_b<br/>브라우저로 확인 · 두 번 선다"}}')
    lines.append('    HG2 -->|"research"| CI')
    lines.append('    HG2 -->|"rebuild"| RBD["rebuilder<br/>사람의 지시문대로 고친다"]')
    lines.append('    RBD --> CP')
    lines.append('    HG2 -->|"quality · 정성 3회 전"| QP')
    lines.append('    HG2 -->|"done · 정성 3회 뒤"| DONE([SUCCESS])')
    lines.append("")
    lines.append('    QP["quality_pass<br/>규율 10가지로 점검하고 고친다"]')
    lines.append("    QP --> CQ")
    lines.append('    CQ["check_quality<br/>절차를 판정해 상태에 쓴다"]')
    lines.append('    CQ --> RC{"route_after_quality"}')
    lines.append('    RC -->|"회차 < {}"| QP'.format(unknown(limits.get("C"), "3")))
    lines.append('    RC -->|"되돌아감 발생"| BP')
    lines.append('    RC -->|"{}회 완료 -> 사람 확인"| HG2'.format(
        unknown(limits.get("C"), "3")))
    lines.append('    RC -->|"판정 불가 · 기록 깨짐"| HALT([HALT_NEEDS_HUMAN])')
    return "\n".join(lines), n


def build_handoff(spec, limits, opts, cities, gaps):
    counts = as_dict(spec.get("count_contract"))
    request = as_dict(spec.get("request"))
    cities_rule = as_dict(counts.get("cities"))
    itinerary_rule = as_dict(counts.get("itinerary"))

    mermaid, city_n = build_mermaid(cities, limits)

    country = unknown(request.get("country"))
    days = unknown(request.get("days"))
    city_count = unknown(cities_rule.get("city_count"))
    spots = unknown(cities_rule.get("spots_per_city"))
    note_lines = unknown(cities_rule.get("preference_note_min_lines"))
    ev_spot = unknown(as_dict(cities_rule.get("evidence_per_spot")).get("target"))
    ev_city = unknown(as_dict(itinerary_rule.get("evidence_per_city")).get("target"))

    out = []
    add = out.append

    add("# 그래프 인계본 — {} {}일".format(country, days))
    add("")
    add("**이 파일 하나로 그래프를 설계할 수 있습니다.**")
    add("루프 킷을 끝까지 돌린 결과에서 기계가 뽑았습니다. 손으로 고치지 마세요 —")
    add("결정이 바뀌면 `python scripts/export_graph_handoff.py` 를 다시 돌리면 됩니다.")
    add("")
    add("---")
    add("")

    # 1
    add("## 1. 목표")
    add("")
    add("```text")
    add("{} {}일 여행 정보 웹페이지 하나(단일 HTML)를 만든다.".format(country, days))
    add("도시 {}개 · 도시마다 관광지 {}곳 · 취향 설명 {}줄".format(
        city_count, spots, note_lines))
    add("일정은 도시마다 따로 {}일 — 어느 도시로 갈지 고르기 위한 페이지다".format(
        unknown(itinerary_rule.get("days_per_city"))))
    add("```")
    add("")
    add("취향 원문은 `02_USER_REQUEST.md` 에 있습니다. **요약본으로는 {}줄짜리".format(note_lines))
    add("취향 설명이 안 나옵니다.** 그 파일을 반드시 같이 넘기세요.")
    add("")

    # 2
    add("## 2. 루프에서 그대로 가져오는 것 (건드리지 마세요)")
    add("")
    add("| 루프의 조건 | 그래프에서 | 어디에 있나 |")
    add("| --- | --- | --- |")
    add("| 관측 표면 (화면 이름표) | **그대로** | `03_CONTRACT.json` 의 `page_contract` |")
    add("| 충족 기준 (개수 계약) | **그대로** | `03_CONTRACT.json` 의 `count_contract` |")
    add("| 판정 독립 (검사기가 밖에) | **그대로** | `scripts/check_*.py` — 루프 킷 파일과 바이트 단위로 같음 |")
    add("| 종료 선언 (성공 조건) | **그대로** | 아래 6번 |")
    add("")
    add("> 이 넷을 바꾸면 루프판과 그래프판을 **같은 자로 잴 수 없게 됩니다.**")
    add("> 실습의 요점이 '같은 계약, 다른 실행 구조'이므로 계약은 고정입니다.")
    add("")

    # 3
    _become = [r for r in TASK_TO_NODE if r[2] != "노드가 아니다" and "합침" not in r[1]]
    _not_node = len(TASK_TO_NODE) - len(_become)
    _spine_new = [r for r in NEW_NODES if r[0] not in DIAGNOSE_NODES]
    _diag = [r for r in NEW_NODES if r[0] in DIAGNOSE_NODES]
    _spine = len(_become) + len(_spine_new)
    _detour_nodes = 2 * len(DETOURS)
    add("## 3. 노드 — 루프의 작업 {}개가 어떻게 옮겨지나".format(len(TASK_TO_NODE)))
    add("")
    add("**작업 8개**는 루프 킷 `specs/04_BOUNDARY_TASKS_SAFETY.md` 의 **권장 작업 7개**(`D-작업목록` A)에 "
        "킷이 고정으로 넣는 `TASK-정성점검` 을 더한 수입니다. 그래프 킷은 이 권장 목록을 기준으로 대응을 고정해 두었으므로 "
        "루프에서 B(5개로 합치기)나 C(직접 정의)를 골랐어도 아래 표는 같습니다.")
    add("")
    add("**1:1로 옮기지 않습니다.** {}개는 노드가 아니게 되고, {}개가 새로 생겨 "
        "**루프 골격 {} + {} = {}개**가 됩니다.".format(
            _not_node, len(_spine_new), len(_become), len(_spine_new), _spine))
    add("여기에 검사기 바로 뒤 **진단 노드 {}개**가 붙어 **루프 골격 {} + 진단 {}** 입니다.".format(
        len(_diag), _spine, len(_diag)))
    add("규칙 처방 가지(등록부 한 줄 = 노드 2개)는 진단 노드에서만 갈라지므로 따로 셉니다 — "
        "킷 기본 {}개를 더하면 Studio 그림에는 **{} + {} + {}×2 = {}개**가 보입니다.".format(
            len(DETOURS), _spine, len(_diag), len(DETOURS),
            _spine + len(_diag) + _detour_nodes))
    add("")
    add("| 루프 작업 | 그래프에서 | 종류 | 왜 |")
    add("| --- | --- | --- | --- |")
    for task, node, kind, why in TASK_TO_NODE:
        add("| `{}` | `{}` | {} | {} |".format(task, node, kind, why))
    add("")
    add("### 루프에는 없던 노드 {}개 (루프 골격 {} · 진단 {})".format(
        len(NEW_NODES), len(_spine_new), len(_diag)))
    add("")
    add("| 노드 | 루프에서는 | 왜 노드가 되나 |")
    add("| --- | --- | --- |")
    for node, was, why in NEW_NODES:
        add("| `{}` | {} | {} |".format(node, was, why))
    add("")
    add("```text")
    add("루프에서 검사기는 '돌려 보고 종료 코드를 읽는 것'이었다.")
    add("그래프에서 검사기는 '판정 값을 상태에 쓰는 노드'다.")
    add("간선이 조건을 보려면 그 값이 상태에 있어야 하기 때문이다.")
    add("진단은 그 바로 뒤에서 '원인 값을 상태에 쓰는 노드'다.")
    add("라우터는 판정(기준을 채웠나)과 원인(무엇이 터졌나)을 나란히 읽는다.")
    add("```")
    add("")
    add("### 규칙 처방 가지 — 진단 노드에서만 갈라진다 (킷 기본 {}개)".format(len(DETOURS)))
    add("")
    add("루프는 모든 실패를 '한 바퀴 더'로 뭉쳐 처리했습니다. 그래프에서는 **정해진 고칠 법이")
    add("있는 실패만** 처방 가지로 보내고, 나머지는 재수집(LLM)이 맡습니다. 모든 처방 가지가")
    add("같은 모양입니다.")
    add("")
    add("```text")
    add(" check_* ─▶ ◇diagnose_* ─┬─ (처방 가지 대상 없음) ────────────▶ 루프 골격 그대로")
    add("                         └─ <이름> ─▶ fix_<이름> ─▶ test_<이름> ─┬ 합격           → check_*   (검사기로 복귀 · 바퀴 안 씀)")
    add("                                                                ├ 불합격 · 한도 안 → fix_<이름> (한 번 더)")
    add("                                                                └ 불합격 · 한도 끝 → ★human_gate_* (사람)")
    add("```")
    add("")
    add("| 처방 가지 | 루프 | 시험지가 보는 것 | 노드 | 합격하면 | 한도 끝나면 |")
    add("| --- | --- | --- | --- | --- | --- |")
    for d in DETOURS:
        add("| `{}` {} | {} | {} | `{}` → `{}` | `{}` | `{}` |".format(
            d["kind"], d["title"], d["loop"], d["sees"], d["fix"], d["test"],
            d["returns_to"], d["gate"]))
    add("")
    add("**실제 목록은 그래프 킷의 `travel_graph/detours/registry.py` 입니다.** 이 표는 킷 기본")
    add("{}개의 사본이라, 그래프 킷 STEP 6 에서 처방 가지를 더하면 달라집니다. 등록 순서가 곧".format(
        len(DETOURS)))
    add("진단 우선순위입니다.")
    add("")
    add("**노드는 처방 가지로만 늘립니다.** 루프 골격 {}개와 진단 {}개는 잠겨 있습니다. 처방 가지는".format(
        _spine, len(_diag)))
    add("판정 · 바퀴 · 게이트 칸을 쓰지 않고, 합격하면 수집 노드가 아니라 **그 루프의 검사기**로")
    add("돌아옵니다 — 수집 노드로 돌아가면 합류가 영영 기다립니다. 진단과 합격은 **같은 시험지**로")
    add("보고, 시험지는 고치는 코드를 import 하지 않습니다 (판정 독립).")
    add("")

    # 4
    add("## 4. 상태 스키마")
    add("")
    add("```python")
    add("from typing import Annotated, TypedDict")
    add("import operator")
    add("")
    add("class TravelState(TypedDict):")
    add("    # 입력 — 노드가 바꾸지 않는다")
    add("    country: str")
    add("    days: int")
    add("    style: dict")
    add("    city_priority: list[str]")
    add("")
    add("    # 수집 결과 — 노드가 채운다")
    add("    country_intro: dict")
    add("    cities: Annotated[list[dict], merge_cities]   # 병렬이 쓴다 -> reducer 필수")
    add("                                                  # operator.add 가 아니다 (아래)")
    add("    city_failures: Annotated[list[dict], merge_failures]  # 수집이 실패한 도시")
    add("    selected_city_names: list[str]   # 여기서 병렬 폭이 정해진다")
    add("")
    add("    # 판정 — 검사기 노드가 쓰고, 라우터가 읽는다")
    add('    info_verdict: str          # UNKNOWN | PASS | SHORT | ERROR')
    add("    info_short_slots: list[str]")
    add("    page_verdict: str")
    add("    page_short_slots: list[str]")
    add("    quality_verdict: str")
    add("    quality_short_slots: list[str]")
    add("")
    add("    # 루프 C — 회차 카운터. ★ reducer 를 붙이면 안 된다 (덮어쓰기다)")
    add("    quality_pass: int              # 0 -> 3")
    add("    quality_passes_required: int   # 3. 계약에서 온다")
    add("")
    add("    # 사람이 적어 넣는 칸 — 게이트가 interrupt 로 받는다")
    add("    gate_a_answer: str         # more | proceed | stop")
    add("    gate_b_answer: str         # research | rebuild | done")
    add("    gate_note: str             # 자유 문장. **라우팅에 쓰지 않는다**")
    add("")
    add("    # 산출물 — 경로만. 본문은 파일에 둔다")
    add("    html_path: str")
    add("    research_path: str")
    add("")
    add("    # 제어")
    add("    loop_a_iter: int")
    add("    loop_a_limit: int")
    add("    loop_b_iter: int")
    add("    loop_b_limit: int")
    add("    same_error_count: int")
    add("    same_error_limit: int")
    add("    last_error_hash: str")
    add("")
    add("    # 진단 · 처방 가지 — 킷 고정. 판정은 검사기 노드가, **원인**은 진단 노드가 쓴다")
    add("    #   처방 가지는 한 번에 하나만 돌므로 reducer 가 없다 (전부 덮어쓰기)")
    add("    inject: list[str]            # 실패 재현 (입력). 평소 []")
    add('    failure_kind: str            # "" | 등록된 처방 가지 이름. **라우터가 읽는 원인 칸**')
    add("    failure_evidence: list[str]  # 증상 몇 줄. 게이트 화면용 — **라우팅에 쓰지 않는다**")
    add("    detour_attempts: dict        # {처방 가지 이름: 이번에 몇 번 돌았나}. 게이트에서 more · research · rebuild 를 고를 때만 {}")
    add("    detour_limit: int            # {}. 처방 한도 — 처방 가지 하나가 사람 없이 돌 수 있는 횟수".format(
        DETOUR_LIMIT))
    add('    detour_verdict: str          # "" | PASS | FAIL. 시험 노드가 쓰고 검사기 노드가 읽고 비운다')
    add("")
    add("    history: Annotated[list[str], operator.add]")
    add("```")
    add("")
    add("**진단 · 처방 가지 칸 6개는 킷 고정입니다.** 판정(`*_verdict`)과 원인(`failure_kind`)은")
    add("다른 칸입니다 — 판정은 \"기준을 채웠나\", 원인은 \"무엇이 터졌나 · 정해진 고칠 법이 있나\".")
    add("`failure_evidence` 는 `gate_note` 처럼 자유 문장이라 **라우팅에 쓰지 않습니다.**")
    add("`detour_attempts` 는 회차 카운터와 같은 규칙입니다 — reducer 없이 덮어씁니다.")
    add("")
    add("> ★ **`quality_pass` 에 `operator.add` 를 붙이지 마십시오.** `cities` 에 reducer 를")
    add("> 붙이는 것을 배운 직후라 카운터에도 붙이는 실수가 잦습니다. 회차 번호는 누적")
    add("> 리스트가 아니라 **단일 정수 덮어쓰기**입니다. 붙이면 2회차에서 값이 1+2=3 이 되어")
    add("> 한 회차를 건너뛰고 나갑니다 (정성이 2회만 돈다).")
    add("")
    add("**`cities` 에 reducer 가 없으면 병렬이 깨집니다.** 도시 {}개가 동시에".format(
        city_count))
    add("같은 필드에 쓰는데 기본 동작은 '새 값으로 교체'이므로 마지막 하나만 남습니다.")
    add("")
    #  예시는 이번 실행의 도시 이름 · 수로 계산한다 (도시가 아직 없으면 예시 3개).
    _names = list(cities) if cities else ["도시1", "도시2", "도시3"]
    _dup = _names + [_names[0], "…"]
    add("**그런데 `operator.add` 도 답이 아닙니다.** 재수집 노드가 **같은 도시**를 다시")
    add("돌려주므로 이어 붙이면 `[{}]` 가 되어 검사기가".format(", ".join(_dup)))
    add("\"도시 {}개\" 로 셉니다. **이름을 키로 덮어쓰는 upsert reducer** 를 쓰십시오.".format(
        2 * len(_names)))
    add("되돌아오는 간선이 있는 그래프에서 reducer 는 **멱등**해야 합니다.")
    add("")
    add("```python")
    add("def merge_cities(old, new):")
    add("    merged = {}")
    add("    for city in list(old or []) + list(new or []):")
    add("        merged[city[\"name\"]] = city      # 같은 이름이면 교체")
    add("    return list(merged.values())")
    add("")
    add("cities:  Annotated[list[dict], merge_cities]   # upsert")
    add("city_failures: Annotated[list[dict], merge_failures]  # upsert + 삭제")
    add("history: Annotated[list[str], operator.add]    # 이어 붙임")
    add("```")
    add("")
    add("**`country_intro` 에는 reducer 를 붙이지 않습니다.** 재수집 갈래가 **하나뿐**이라")
    add("한 걸음에 이 키를 쓰는 노드가 둘 이상이 되지 않기 때문입니다.")
    add("**'fan-out 이면 무조건 reducer' 가 아닙니다** — 겹치는지를 보는 것입니다.")
    add("")
    add("**수집이 실패한 도시를 담을 칸도 하나 두십시오.** 빈 껍데기를 정상 결과인 척")
    add("돌려주면 게이트가 아무것도 알리지 못합니다. 부족과 실패는 판단이 다릅니다.")
    add("")
    add("**그 칸의 reducer 는 upsert 로도 부족합니다.** 한 번 실패한 도시가 재수집에")
    add("**성공하면 그 줄이 사라져야** 합니다. 그러지 않으면 고쳐진 뒤에도 게이트")
    add("화면에 실패로 계속 남아 사람이 잘못 판단합니다.")
    add("")
    add("```python")
    add("def merge_failures(old, new):")
    add("    merged = {}")
    add("    for row in list(old or []) + list(new or []):")
    add('        if row.get("why"):                 # 실패 -> 적는다')
    add('            merged[row["city"]] = row')
    add("        else:                              # 이번엔 성공 -> **지운다**")
    add('            merged.pop(row["city"], None)')
    add("    return list(merged.values())")
    add("```")
    add("")
    add("**성공을 '기록이 사라지는 것'으로 표현합니다.**")
    add("")
    add("초기값은 `05_STATE_SEED.json` 에 있습니다. `graph.invoke()` 에 그대로 넣어도 됩니다 — "
        "입력 5칸만 쓰이고 나머지는 read_request 가 채웁니다 (상한은 계약에서 · 처방 한도는 킷 고정값).")
    add("")

    # 5
    _kinds_a = " · ".join("`{}`".format(d["kind"]) for d in DETOURS if d["loop"] == "A")
    _kinds_b = " · ".join("`{}`".format(d["kind"]) for d in DETOURS if d["loop"] == "B")
    add("## 5. 간선 — 라우팅은 코드가 아니라 상태의 값")
    add("")
    add("**라우터는 두 칸을 나란히 읽습니다.** 판정(`info_verdict` · `page_verdict` — 검사기")
    add("노드가 쓴다)과 원인(`failure_kind` — 진단 노드가 쓴다)입니다. 규칙은 **원인을 먼저,")
    add("판정을 다음에, 상한은 탈출구로.**")
    add("")
    add("```python")
    add("def route_after_info(state):                           # diagnose_info 뒤")
    add('    kind = state["failure_kind"]                       # 원인 — 진단 노드가 썼다')
    add('    if kind in DETOURS_A and state["detour_attempts"].get(kind, 0) < state["detour_limit"]:')
    add('        return kind                                    # 처방 가지로 — 판정이 PASS 여도')
    add('    if state["info_verdict"] != "SHORT":')
    add('        return "gate"                                  # PASS 든 ERROR 든 사람에게')
    add('    if state["loop_a_iter"] >= state["loop_a_limit"]:')
    add('        return "gate"                                  # 바퀴를 다 썼다')
    add('    if state["same_error_count"] >= state["same_error_limit"]:')
    add('        return "gate"                                  # 진전이 없다')
    add('    return fan_out_repairs(state) or "gate"            # Send × 지적된 도시만')
    add("```")
    add("")
    add("**돌려주는 값이 세 종류입니다** — 처방 가지 이름(→ `fix_<이름>`), `Send` 목록(재수집),")
    add("문자열(게이트). `ALLOWED` 표에는 **문자열만** 적습니다. `Send` 는 매핑을 거치지 않기 때문입니다.")
    add("이 라우터가 낼 수 있는 문자열은 `gate` · `repair` · `repair_country` 에 **루프 A 처방 가지")
    add("이름**({})을 더한 것입니다 — 매핑에 없는 값을 돌려주면 런타임에 `KeyError` 가 납니다.".format(
        _kinds_a))
    add("처방 가지 이름은 등록부에서 읽으므로 한 줄 등록하면 표와 매핑이 **함께** 늘어납니다.")
    add("")
    add("**판정이 PASS 여도 처방 가지로 갑니다.** 처방 가지가 보는 결함(깨진 글자 · 원본 크기 사진)은")
    add("검사기가 세지 않기 때문입니다. 처방 가지마다 처방 한도(`detour_limit` {}회)가 있어 무한히".format(
        DETOUR_LIMIT))
    add("돌지 않습니다.")
    add("")
    add("**라우터는 문자열 말고 `Send` 목록도 돌려줄 수 있습니다.** 재수집을 `Send` 로")
    add("만들면 지적된 도시만 부르게 됩니다 — 노드 하나가 안에서 전부 부르면 지적이")
    add("없는 도시까지 **첫 수집으로 떨어져** 통째로 다시 뽑힙니다.")
    add("")
    add("**그 `Send` 목록에는 도시와 국가 소개가 섞여 나갑니다.** 한 걸음에 나란히")
    add("고치므로 벽시계 시간이 늘지 않습니다. 갈래 폭만 다릅니다 — 도시는 다친")
    add("수만큼, 국가는 0 또는 1.")
    add("")
    add("**재수집을 수집 노드 재사용으로 만들지 마십시오.** 합류")
    add("(`add_edge([\"collect_country\",\"collect_city\"], \"check_information\")`)에")
    add("되돌이 간선을 걸면 합류가 다른 갈래를 영영 기다립니다. **예외 없이 조용히**")
    add("**멈춥니다** — 최소 재현에서 `['A','B','J1','A']` 로 끝났습니다.")
    add("")
    add("루프에서 쓰던 실패 라우팅 7종은 그대로 옮깁니다.")
    add("")
    add("```text")
    add("CODE_ERROR               -> RETRY        해당 노드만 다시")
    add("INFORMATION_INSUFFICIENT -> RESEARCH     부족한 칸만 다시")
    add("SPEC_CONFLICT            -> REVISE_SPEC  그래프 밖으로 나간다")
    add("TEST_ERROR               -> HITL         human_gate 로")
    add("ENVIRONMENT_ERROR        -> HITL")
    add("PERMISSION_ERROR         -> HITL")
    add("UNKNOWN_ERROR            -> STOP         END 로 직행")
    add("```")
    add("")
    add("**`failure_type`(위 7종)과 `failure_kind`(처방 가지 이름)는 다른 축입니다.** 7종은 루프에서")
    add("이식한 넓은 분류라 그대로 둡니다. `failure_kind` 는 진단 노드가 쓰는 **더 좁은 분류**이고,")
    add("값은 등록된 처방 가지 이름입니다. 킷 기본 처방 가지로 보면:")
    add("")
    add("```text")
    add("failure_kind  넓게 보면 (failure_type)                      왜 처방 가지인가")
    add("image_dead    INFORMATION_INSUFFICIENT — 주소가 틀림        재수집(LLM)은 같은 식으로 주소를 지어낸다")
    add("encoding      CODE_ERROR / ENVIRONMENT_ERROR — 글자가 망가짐  검사기가 세지 않는다 — 판정 PASS 여도 있다")
    add("image_spec    CODE_ERROR — 화면 규격                        검사기는 사진이 '있는가'만 본다")
    add("```")
    add("")
    add("루프에서 문서로만 있던 실패 라우팅 7종이 **일부는 실제 배선(처방 가지)이 됩니다.**")
    add("")
    add("**주의 — 한 노드에서 일반 간선을 여러 개 걸면 if/else 가 아니라 병렬입니다.**")
    add("둘 중 하나만 고르려면 반드시 `add_conditional_edges()` 를 씁니다.")
    add("")
    add("### 라우터 6개 + fan-out 2개 — 전체 목록")
    add("")
    add("```text")
    add("fan_out_cities       select_cities 뒤       Send × 고른 도시 전부      -> collect_city")
    add("fan_out_repairs      (아래 둘이 호출)        Send × **지적된 것만**")
    add("                                            -> repair_city ×N · repair_country ×0|1")
    add("")
    add("route_after_info     diagnose_info 뒤       처방 가지 이름 -> fix_<이름> (판정보다 먼저)")
    add("                                            SHORT·바퀴 남음 -> Send / 그 밖 -> gate_a")
    add("route_after_gate_a   human_gate_a 뒤        more -> Send / proceed -> build / stop -> END")
    add("route_after_page     diagnose_page 뒤       처방 가지 이름 -> fix_<이름> (판정보다 먼저)")
    add("                                            SHORT·바퀴 남음 -> build_page / 그 밖 -> gate_b")
    add("route_after_gate_b   human_gate_b 뒤        research -> check_information")
    add("                                            rebuild  -> rebuilder")
    add("                                            그 밖    -> 정성 3회 전이면 quality_pass, 뒤면 END")
    add("route_after_quality  check_quality 뒤       ★ 카운터를 **정상 경로**로 본다")
    add("route_after_detour   test_<이름> 뒤         back  -> 그 루프의 검사기 (검사기로 복귀 · 바퀴 안 씀)")
    add("                     (처방 가지 공용)       retry -> 같은 fix_<이름> (한 번 더)")
    add("                                            gate  -> 그 루프의 게이트 (한도 끝)")
    add("```")
    add("")
    add("루프 A 처방 가지({})는 `route_after_info` 에서, 루프 B 처방 가지({})는 `route_after_page`".format(
        _kinds_a or "없음", _kinds_b or "없음"))
    add("에서 갈라집니다. STEP 3 에서 읽고 고칠 수 있는 것은 앞의 넷(`route_after_info` ·")
    add("`route_after_gate_a` · `route_after_page` · `route_after_gate_b`)이고, 그 안의 처방 가지 분기와")
    add("게이트 B 의 정성 분기는 킷 고정입니다. `route_after_quality` · `route_after_detour` 는")
    add("통째로 킷 고정입니다.")
    add("")
    add("**루프 A·B 의 라우터와 `route_after_quality` 가 다릅니다.** 루프 A·B 의 상한은 `여기까지만 돈다`는")
    add("최대값이지만, 루프 C 의 3회는 **최소이자 최대**입니다. 통과선이 아니라 고정")
    add("예산이라 `route_after_quality` 는 카운터를 탈출구가 아니라 목표로 읽습니다.")
    add("")
    add("**`route_after_detour` 는 처방 가지가 모두 같이 씁니다.** 어느 가지에서 왔는지는 배선")
    add("(매핑)이 알고, 라우터는 '합격했나 · 몇 번 했나'만 봅니다. 합격하면 **그 루프의 검사기**로")
    add("돌아가 같은 자로 다시 잽니다. 그렇게 돌아온 방문은 바퀴(`loop_a_iter` · `loop_b_iter`)로")
    add("세지 않습니다 — 그래야 루프판과 반복 횟수를 같은 뜻으로 비교할 수 있습니다.")
    add("")
    add("**게이트 B 는 두 번 섭니다.** 그래서 `route_after_gate_b` 의 마지막 분기가")
    add("정성 회차를 봅니다 — 3회 전이면 `quality_pass` 로, 3회 뒤면 `END` 로.")
    add("**이 분기를 지우면 루프 C 가 한 번도 실행되지 않습니다.**")
    add("")

    # 6
    add("## 6. 종료 조건")
    add("")
    add("| 무엇 | 값 |")
    add("| --- | --- |")
    add("| 도시 수 | {} |".format(city_count))
    add("| 도시당 관광지 | {} |".format(spots))
    add("| 관광지당 근거 | {} (서로 다른 출처 2곳) |".format(ev_spot))
    add("| 도시당 일정 근거 | {} |".format(ev_city))
    add("| 도시마다의 일자 수 | {} |".format(
        unknown(itinerary_rule.get("days_per_city"))))
    add("| 하루 시간 블록 | {}개 이상 (HH:MM) |".format(
        unknown(itinerary_rule.get("blocks_per_day_min"))))
    add("| 취향 설명 | {}줄 이상 |".format(note_lines))
    add("| 루프 A 상한 | {}바퀴 |".format(unknown(limits.get("A"))))
    add("| 루프 B 상한 | {}바퀴 |".format(unknown(limits.get("B"))))
    add("| 루프 C 정성 회차 | {}회 고정 (최소이자 최대) |".format(unknown(limits.get("C"))))
    add("| 처방 한도 | 처방 가지마다 {}회 (게이트에서 more · research · rebuild 를 고르면 다시 0) |".format(
        DETOUR_LIMIT))
    add("| 같은 오류 | {}회 |".format(unknown(opts.get("same_error_limit"))))
    add("| 전체 상한 | {}회 (기록용 — 그래프는 강제하지 않음 · 바깥 루프는 게이트에서 사람 소유) |".format(
        unknown(opts.get("max_iterations"))))
    add("| 성공 조건 | {} |".format(unknown(opts.get("success_condition"))))
    add("")
    add("종료 조건이 없는 그래프는 자율 에이전트가 아니라 무한루프입니다.")
    add("위 표에서 **최소 두 가지 이상**을 반드시 라우터에 넣으세요.")
    add("")

    # 7
    add("## 7. 병렬 가능 지점")
    add("")
    add("| 나란히 돌 수 있는 것 | 왜 | 주의 |")
    add("| --- | --- | --- |")
    add("| `collect_country` 와 `select_cities` | 서로의 결과를 안 본다 | 다른 필드에 쓴다 |")
    add("| `collect_city` × {}도시 | 도시끼리 독립 | **같은 `cities` 필드 → reducer** |".format(
        city_count))
    add("| 재수집 × **지적된 도시만** | 같은 이유 | 같은 reducer 를 지난다 → **멱등이어야 한다** |")
    add("")
    add("**병렬로 못 돌리는 것** — `build_page` 는 모든 수집이 끝나야 합니다.")
    add("`select_cities` 전에는 병렬 폭을 모릅니다.")
    add("**처방 가지도 병렬로 돌지 않습니다** — 한 번에 하나씩, 등록 순서(= 진단 우선순위)대로")
    add("탑니다. 그래서 진단 · 처방 가지 칸에는 reducer 가 없습니다.")
    add("")

    # 8
    add("## 8. 사람이 끼어드는 곳 — 정지 지점 3곳")
    add("")
    add("```text")
    add("human_gate_a  루프 A 끝       more / proceed / stop")
    add("human_gate_b  루프 B 끝       research / rebuild / done   <- 정성 3회 **전**")
    add("human_gate_b  정성 3회 끝     research / rebuild / done   <- 노드는 같고 묻는 게 다르다")
    add("(처방 가지)   처방 한도 소진  그 루프의 게이트에 한 번 더 선다 (A -> human_gate_a · B -> human_gate_b)")
    add("```")
    add("")
    add("**처방 가지가 처방 한도(`detour_limit` {}회)를 다 쓰면 그 루프의 게이트에서 한 번 더 설 수".format(
        DETOUR_LIMIT))
    add("있습니다.** 그 실패가 나지 않으면 처방 가지는 켜지지 않고 정지는 3곳 그대로입니다. 한도가 끝나서")
    add("온 게이트는 `② 왜` 맨 앞에 **\"처방 가지가 못 고침 — <제목>\"** 줄을 띄웁니다.")
    add("사람이 `more` · `research` · `rebuild` 를 고르면 처방 한도가 새로 채워집니다 —")
    add("바깥 루프는 사람 소유입니다.")
    add("")
    add("**세 정지 지점이 같은 화면 규격을 씁니다.** 키 순서가 곧 읽는 순서입니다.")
    add("")
    add("```text")
    add("① 지금    어느 루프 · 판정 · 몇 바퀴 · 못 채운 칸 몇 곳")
    add("② 왜      **목록이 아니라 원인별 요약.** 40곳이 실제로는 서너 종류에서 나온다")
    add("③ 권장    지금 상태에서 무엇을 고르는 게 나은지 + 그 이유")
    add("④ 고르기  각 선택지가 **무엇을 하고 무엇을 안 하는지**")
    add("⑤ 답      Studio resume 칸에 그대로 붙여 넣을 JSON")
    add("```")
    add("")
    add("**`② 왜` 가 핵심입니다.** 못 채운 칸을 그냥 나열하면 사람이 판단할 수 없습니다.")
    add("원인별로 묶어 **무엇을 지시해야 하는지**까지 적어야 다음 바퀴가 달라집니다.")
    add("수집이 통째로 실패한 도시는 부족과 구분해 따로 알립니다 — 판단이 다릅니다.")
    add("")
    add("**`⑤ 답` 의 `note` 를 화면이 미리 채워 주십시오.** 원인을 알면 무엇을")
    add("지시해야 하는지도 정해집니다. 비워 두면 재수집 프롬프트가 지난 바퀴와 글자")
    add("하나 다르지 않아 **같은 결과가 나옵니다** — 실측에서 그랬습니다.")
    add("")
    add("**`④ 고르기` 의 `more` 는 라우터와 같은 규칙으로 대상을 계산해 적으십시오.**")
    add("고정 문구로 두면 국가만 부족한데 \"지적된 도시만\"이라고 표시됩니다.")
    add("")
    add("**`서로 다른 출처` 부족은 개수 문제가 아닙니다.** 그 줄에도 `목표 2 / 실제 1`")
    add("이 붙어 있어 개수로 묶기 쉬운데, 같은 출처에서 한 건을 더 얹으면 건수는 늘어도")
    add("검사는 그대로 실패합니다. **다른 도메인에서 찾아 갈아 끼워야** 합니다.")
    add("")
    add("**`rebuild` 를 고르면 `note` 가 곧 수정 지시가 됩니다.** 그 문장을 실제로")
    add("소비하는 노드(`rebuilder`)가 따로 있어야 합니다. 비워 두면 고칠 방향이 없습니다.")
    add("**계약을 낮추라는 지시는 거부합니다.**")
    add("")
    add("LangGraph 에서는 `interrupt` 로 멈추고, 사람의 답을 상태에 적은 뒤 재개합니다.")
    add("**되물음은 그래프 안의 판단이 아니라 그래프 바깥의 결정입니다.**")
    add("")

    # 9
    add("## 9. 이번 실행에서 나온 그래프 모양")
    add("")
    add("```mermaid")
    add(mermaid)
    add("```")
    add("")
    if city_n:
        add("도시 {}개 기준으로 그렸습니다. 도시 수가 바뀌면 병렬 폭이 바뀝니다.".format(city_n))
    else:
        add("**도시가 아직 안 정해져 예시 3개로 그렸습니다.** 루프를 끝까지 돌리면 실제 이름이 들어갑니다.")
    add("")
    add("`▷ 처방 가지` 상자가 규칙 처방 가지입니다. 진단 노드 뒤 라우터에서만 갈라지고, 합격하면 그 루프의")
    add("검사기로 돌아옵니다. 킷 기본 {}개만 그렸습니다 — 진짜 목록은 그래프 킷의".format(len(DETOURS)))
    add("`travel_graph/detours/registry.py` 입니다.")
    add("")

    # 10
    add("## 10. 구멍 → 처방 가지로 빼기 (고정 규칙)")
    add("")
    add("`04_RUN_EVIDENCE.md` 에서 실제로 어디가 부족했는지 보고, 이 표로 옮깁니다.")
    add("")
    add("| 실측에서 보이는 구멍 | 그래프에서 하는 일 | 얻는 것 |")
    add("| --- | --- | --- |")
    for hole, action, gain in HOLE_RULES:
        add("| {} | **{}** | {} |".format(hole, action, gain))
    add("")
    add("**루프 골격과 진단은 잠겨 있습니다.** 새 처방 가지는 그래프 킷 STEP 6(실행 뒤 · 조건부)에서")
    add("`python scripts/new_detour.py <이름> --loop A|B --title \"…\"` 로 세 조각(등록부 한 줄 ·")
    add("고치는 법 모듈 · 시험지)을 만들어 붙입니다. STEP 6 은 그래프 실행의 실패 기록")
    add("(`python scripts/failure_report.py` ③ · ③-2)에 처방 가지 후보가 있을 때만 합니다 — 후보가")
    add("없으면 하지 않습니다. **한 번은 일화, 세 번은 패턴입니다.**")
    add("")

    # 11
    add("## 11. 채점")
    add("")
    add("그래프 킷 안에서 잽니다. 정보량 · 페이지 · 정성 검사기는 **루프 킷 파일과 바이트 단위로")
    add("같고**, 그래프 킷은 맨 앞에 구조 검사 하나를 더합니다.")
    add("")
    add("```bash")
    add("python scripts/verify_all.py                  # 구조 -> 정보량 -> 페이지 -> 정성")
    add("python scripts/verify_all.py --skip-quality   # 정성 회차 안에서 쓰는 재검증 모드")
    add("```")
    add("")
    add("검사기는 결과물이 **어떤 구조로 만들어졌는지 모릅니다.** 계약만 봅니다.")
    add("그래서 루프판과 그래프판을 같은 표에 올려 비교할 수 있습니다 — 루프판 숫자는")
    add("`04_RUN_EVIDENCE.md` 8번(루프판 기준선)에 있습니다. 그래프 결과물을 루프 킷의 `output/` 에")
    add("복사하지 마십시오 — 루프판 결과물을 덮어써 기준선이 사라집니다.")
    add("")

    if gaps:
        add("---")
        add("")
        add("## ⚠ 이 인계본은 미완성입니다")
        add("")
        add("루프가 끝까지 돌지 않아 아래가 비어 있거나 기준에 못 미칩니다.")
        add("")
        for gap in gaps[:20]:
            add("- {}".format(gap))
        if len(gaps) > 20:
            add("- ... 그 밖 {}건".format(len(gaps) - 20))
        add("")
        add("그래프 설계는 이대로도 할 수 있습니다. 다만 **9번 그림의 병렬 폭**과")
        add("**04_RUN_EVIDENCE.md 의 실측**은 루프를 끝까지 돌린 뒤 다시 뽑으세요.")
        add("")

    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# 04_RUN_EVIDENCE.md
# --------------------------------------------------------------------------


def _minutes_between(start, end):
    """ISO 시각 두 개 사이의 분. 못 읽으면 None — 시간을 지어내지 않는다."""
    from datetime import datetime
    try:
        a = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
        b = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
        if (a.tzinfo is None) != (b.tzinfo is None):
            a, b = a.replace(tzinfo=None), b.replace(tzinfo=None)
        minutes = (b - a).total_seconds() / 60
    except (TypeError, ValueError):
        return None
    return round(minutes) if 0 <= minutes < 24 * 60 else None


def build_baseline(state, events, short, result_a, result_b, result_c, run_dir, manifest):
    """`루프판 기준선` 절. 그래프 가이드의 비교표가 이 숫자를 옮겨 적는다.

    ★ 기록에 없는 값은 `(기록 없음 …)` 으로 둔다. 만들어 내지 않는다.
    """
    out = []
    add = out.append
    none = "(기록 없음 — 내 루프 기록에서 옮겨 적는다)"
    loops = as_dict(state.get("loops"))

    def iteration(key):
        value = as_dict(loops.get(key)).get("iteration")
        return value if isinstance(value, int) else None

    quality_dir = run_dir / "quality" if run_dir else None
    passes_done = (len(list(quality_dir.glob("pass*.json")))
                   if quality_dir and quality_dir.is_dir() else 0)
    a, b = iteration("A"), iteration("B")
    c = passes_done                       # 루프 C 는 기록(passN.json)으로 센다 — 아래 `정성 회차` 와 같은 수
    if a is None and b is None:
        loops_line = none
    else:
        loops_line = "{}   (A {} · B {} · C {})".format(
            (a or 0) + (b or 0) + (c or 0), a or 0, b or 0, c or 0)

    minutes = _minutes_between(as_dict(manifest).get("started_at"), state.get("updated_at"))
    time_line = "약 {}분".format(minutes) if minutes is not None else none

    asks = [e for e in events if e.get("next_action") in ("REVERSE_QUESTION", "HITL")]
    asks_line = str(len(asks)) if events else none

    code, verdicts = overall_verdict(result_a, result_b, result_c)

    add("## 8. 루프판 기준선 (그래프판과 비교할 숫자)")
    add("")
    add("그래프 킷 가이드의 **비교표(루프판 vs 그래프판)** 왼쪽 칸을 여기서 옮겨 적습니다.")
    add("")
    add("```text")
    add("반복 횟수            {}".format(loops_line))
    add("전체 시간           {}".format(time_line))
    add("실패 후 재실행 범위   바퀴 전체")
    add("사람 호출 횟수        {}".format(asks_line))
    add("정성 회차            {} / 3".format(passes_done))
    add("verify_all          exit {}   ({})".format(code, " · ".join(verdicts) or "검사기를 못 돌림"))
    #  검사기가 ERROR(계약 미완성 · 데이터 깨짐)면 아무것도 못 잰 것이다 — 0건으로 적지 않는다.
    broken = (result_a is None or result_a.verdict == "ERROR"
              or (result_b is not None and result_b.verdict == "ERROR"))
    add("못 채운 칸           {}".format(none if broken else "{}건".format(len(short))))
    #  '못 채운 칸' = 검사기 short 개수. 계약은 채웠지만 사람이 남긴 아쉬움(되물음 메모)은
    #  검사기가 세지 않으므로 따로 둔다 — 기계가 셀 수 없어 비워 둔다.
    add("계약 밖 아쉬움        {}".format(none))
    add("```")
    add("")
    add("> 시간은 `run_manifest.json` 의 `started_at` → `state/loop_state.json` 의 `updated_at` 입니다.")
    add("> 사람 호출은 `events.jsonl` 에서 다음 행동이 되물음(`REVERSE_QUESTION`) · `HITL` 인 줄 수입니다.")
    add("> 그래프판의 반복 횟수에는 **처방 가지를 세지 않습니다** (처방 가지에서 합격하고 돌아온 방문은")
    add("> 바퀴를 쓰지 않는다). 그래서 이 숫자와 같은 뜻으로 비교됩니다.")
    add("")
    return out


def build_evidence(state, events, result_a, result_b, run_dir, limits,
                   result_c=None, manifest=None):
    out = []
    add = out.append

    add("# 실측 — 이번 실행에서 실제로 일어난 일")
    add("")
    add("**이 파일이 어디에 처방 가지를 둘지의 근거입니다.**")
    add("결정은 '내가 정한 것'이고, 실측은 '현실이 답한 것'입니다.")
    add("결정에서 실측을 계산할 수 없기 때문에 값이 있습니다.")
    add("")
    add("---")
    add("")

    add("## 1. 요약")
    add("")
    if run_dir is None and not events:
        add("```text")
        add("실행 기록이 없습니다. (evidence/runs/ 가 비어 있음)")
        add("루프를 한 번 돌린 뒤 다시 뽑으세요.")
        add("```")
        add("")
    else:
        loops = as_dict(state.get("loops"))
        add("```text")
        add("run_id       : {}".format(run_dir.name if run_dir else "(없음)"))
        add("종료 상태     : {}".format(unknown(state.get("final_status"))))
        add("루프 A 반복   : {} / 상한 {}".format(
            unknown(as_dict(loops.get("A")).get("iteration"), "0"),
            unknown(limits.get("A"))))
        add("루프 B 반복   : {} / 상한 {}".format(
            unknown(as_dict(loops.get("B")).get("iteration"), "0"),
            unknown(limits.get("B"))))
        add("전체 반복     : {}".format(unknown(state.get("total_iteration"), "0")))
        add("기록된 사건   : {}줄".format(len(events)))
        add("```")
        add("")

    add("## 2. 실패 유형 분포")
    add("")
    #  ★ 2~5 · 7번은 **같은 실패 줄(is_failure)** 만 센다. 한 곳은 '실패 없음', 다른 곳은
    #    '3회 실패'로 서로 어긋나지 않게 하려는 것이다.
    failed = [e for e in events if is_failure(e)]
    failures = {}
    tasks = {}
    hashes = {}
    history_slots = {}
    for event in failed:
        ftype = event.get("failure_type") or "(유형 미기록)"
        failures[ftype] = failures.get(ftype, 0) + 1
        task = event.get("task_id") or "(작업 미기록)"
        tasks[task] = tasks.get(task, 0) + 1
        ehash = event.get("error_hash")
        if ehash:
            hashes[ehash] = hashes.get(ehash, 0) + 1
        for slot in as_list(event.get("short_slots")):
            key = str(slot)
            history_slots[key] = history_slots.get(key, 0) + 1

    add("실패로 세는 줄: `failure_type` 이 적혀 있거나, 다음 행동이 실패 라우팅(`RETRY` · `RESEARCH` ·")
    add("`REVISE_SPEC` · `HITL` · `STOP`)이면서 검사기가 통과하지 않은 줄. 되물음(`REVERSE_QUESTION`) ·")
    add("루프 C 남은 회차(`QUALITY`) · 최종 검증 통과(`DONE`) · 출발점 빨간불(`iteration` 0)은 정상 진행이라")
    add("세지 않습니다. **아래 3 · 4 · 5 · 7번도 같은 줄만 봅니다.**")
    add("")
    if failures:
        add("| 실패 유형 | 횟수 |")
        add("| --- | --- |")
        for name, count in sorted(failures.items(), key=lambda x: -x[1]):
            shown = name if name.startswith("(") else "`{}`".format(name)
            add("| {} | {} |".format(shown, count))
        if "(유형 미기록)" in failures:
            add("")
            add("`(유형 미기록)` 은 다음 행동은 실패 라우팅인데 `failure_type` 이 비어 있는 줄입니다 — 기록을 보완하세요.")
    else:
        add("기록된 실패가 없습니다 (사건 {}줄은 모두 정상 진행입니다).".format(len(events)))
    add("")

    add("## 3. 어느 작업이 몇 번 실패했나")
    add("")
    if tasks:
        add("| 작업 | 실패 횟수 | 이게 뜻하는 것 |")
        add("| --- | --- | --- |")
        for name, count in sorted(tasks.items(), key=lambda x: -x[1]):
            hint = "처방 가지 후보" if count >= 2 else "한 번 실패 — 아직 신호 아님"
            shown = name if name == "(작업 미기록)" else "`{}`".format(name)
            add("| {} | {} | {} |".format(shown, count, hint))
        add("")
        add("**2회 이상 실패한 작업은 처방 가지 후보입니다.** 실패가 한곳에 몰린다는 것은")
        add("그 안에 재시도 단위가 다른 일이 섞여 있다는 뜻입니다. 그래프에서는 루프 골격을 그대로")
        add("두고, 그 원인에 정해진 고칠 법이 있으면 **진단 노드 뒤 처방 가지**로 뺍니다.")
        add("고칠 법이 아직 정해지지 않았으면 재수집(LLM)에 둡니다 — 같은 실패가 로그에서 반복되고")
        add("고칠 법이 정해지면 그때 가지로 뺍니다.")
    else:
        add("실패 기록이 없습니다.")
    add("")

    add("## 4. 같은 오류가 반복됐나")
    add("")
    repeated = {h: c for h, c in hashes.items() if c >= 2}
    if repeated:
        add("| 오류 지문 | 횟수 |")
        add("| --- | --- |")
        for ehash, count in sorted(repeated.items(), key=lambda x: -x[1]):
            add("| `{}` | {} |".format(str(ehash)[:24], count))
        add("")
        add("같은 지문이 반복되면 **더 돌려도 진전이 없다**는 뜻입니다.")
        add("그래프에서는 이 조건을 라우터에 직접 넣습니다.")
    else:
        add("같은 지문이 2회 이상 반복된 기록은 없습니다.")
    add("")

    add("## 5. 바퀴를 돌게 만든 칸 (이력)")
    add("")
    if history_slots:
        add("성공으로 끝났어도 **여기 있던 칸들이 루프를 다시 돌게 만들었습니다.**")
        add("마지막에 채워졌다고 해서 쉬웠던 것이 아닙니다. (2번의 실패 줄에 적힌 `short_slots` 만 셉니다)")
        add("")
        add("| 칸 | 몇 바퀴를 유발했나 |")
        add("| --- | --- |")
        for slot, count in sorted(history_slots.items(), key=lambda x: -x[1]):
            add("| {} | {} |".format(slot, count))
        add("")
        add("**2회 이상 나온 칸이 처방 가지 후보 1순위입니다.** 그래프에서는 이런 칸을 재수집(LLM)이")
        add("맡습니다. 같은 원인을 그래프 실행에서도 재수집이 반복해서 맡으면 실패 기록 보고서")
        add("(`python scripts/failure_report.py`) ③-2 에 처방 가지 후보로 뜹니다.")
    else:
        add("기록된 부족 칸이 없습니다.")
    add("")

    add("## 6. 끝내 못 채운 칸")
    add("")
    short = []
    if result_a is not None:
        short.extend(result_a.short)
    if result_b is not None:
        short.extend(result_b.short)
    if short:
        add("```text")
        for item in short[:30]:
            add(item)
        if len(short) > 30:
            add("... 그 밖 {}곳".format(len(short) - 30))
        add("```")
        add("")
        add("**이 목록이 제일 중요합니다.** 여기에 같은 종류가 몰려 있고 그 종류에 정해진")
        add("고칠 법이 있으면, 진단 노드 뒤 **처방 가지**(고치고 → 시험 → 검사기로 복귀)로 빼고")
        add("처방 한도로 재시도를 따로 셉니다.")
    elif result_a is None:
        add("검사기를 돌릴 수 없어 확인하지 못했습니다.")
    elif result_a.verdict == "ERROR" or (result_b is not None and result_b.verdict == "ERROR"):
        add("검사기가 ERROR 로 끝나(명세 미완성 또는 데이터 깨짐) 확인하지 못했습니다.")
    else:
        add("못 채운 칸이 없습니다.")
    add("")

    add("## 7. 그래서 어느 처방 가지가 필요할까 — 자동 제안")
    add("")
    suggestions = suggest_splits(tasks, short, repeated, history_slots)
    if suggestions:
        add("| 근거 | 제안 |")
        add("| --- | --- |")
        for reason, action in suggestions:
            add("| {} | **{}** |".format(reason, action))
        add("")
        add("> 제안일 뿐입니다. **한 번 돌린 실측은 일화이고, 세 번은 패턴입니다.**")
        add("> 나라를 바꿔 두세 번 더 돌린 뒤 같은 자리가 또 비면 그때 확정하세요.")
    else:
        add("아직 처방 가지를 둘 근거가 부족합니다 — 그동안은 재수집(LLM)이 맡습니다. 실행을 더 쌓으세요.")
    add("")

    out.extend(build_baseline(state, events, short, result_a, result_b, result_c,
                              run_dir, manifest))

    return "\n".join(out) + "\n"


def suggest_splits(tasks, short, repeated, history_slots=None):
    """실측에서 고정 규칙으로 제안을 만든다. 없는 근거로 제안하지 않는다.

    지금 남은 부족(short)만 보면 안 된다. 성공으로 끝난 실행은 short 가 비어 있다.
    바퀴를 돌게 만든 이력(history_slots)까지 같이 봐야 마찰이 어디였는지 보인다.

    제안은 **처방 가지 후보**이거나 프롬프트 개선이다. 루프 골격 노드를 새로 만들자는 제안은
    하지 않는다 — 그래프 킷에서 노드는 진단 노드 뒤 처방 가지(STEP 6 · 조건부)로만 늘어난다.

    처방 가지 후보 = **재수집(LLM)이 반복해서 맡은 원인**이다. 같은 입력에 같은 고칠 법이
    있으면 가지로 뺀다. 고칠 법이 아직 없거나 한 번만 나온 원인은 재수집에 둔다
    (그래프 킷 `failure_report.py` 의 ③-2 가 같은 기준으로 센다).
    """
    out = []
    history_slots = history_slots or {}
    evidence = list(short) + [
        s for s, c in history_slots.items() for _ in range(c)
    ]

    def hits(*words):
        return [s for s in evidence if any(w in s for w in words)]

    image_short = hits("이미지", "사진")
    if len(image_short) >= 2:
        out.append((
            "이미지 부족 {}건".format(len(image_short)),
            "image_dead 처방 가지 (그래프 킷에 이미 있다 — 재수집(LLM)이 주소를 반복해서 "
            "지어내 가지로 뺀 것). 주소가 틀려서 못 채운 칸은 "
            "진단 노드가 시험지로 잡고 정해진 절차로 고친다 — 코드가 직접 열어 보고 "
            "verified 를 채운다 (모델의 자기보고를 받지 않는다). 인터넷에 없는 사진은 "
            "처방 가지도 못 만든다 → 재수집(LLM) fan-out 이 그 도시만 다시 부른다",
        ))

    note_short = hits("취향")
    if note_short:
        out.append((
            "취향 설명 부족 {}건".format(len(note_short)),
            "프롬프트 개선 — 취향 설명을 쓰는 호출에 02_USER_REQUEST.md 원문과 "
            "'줄마다 서로 다른 내용' 조건을 싣는다. 그래프에서는 재수집(LLM)이 맡는다. "
            "재수집이 이 원인을 반복해서 맡고(보고서 ③-2) 같은 입력에 같은 고칠 법이 "
            "정해지면 그래프 킷 STEP 6 에서 처방 가지로 뺀다 "
            "(루프 골격 노드는 새로 만들지 않는다)",
        ))

    plan_short = hits("일정", "일자")
    if plan_short:
        out.append((
            "일정 부족 {}건".format(len(plan_short)),
            "일정 호출에 '그 도시에서 조사한 관광지 목록'을 넣어 그 이름만 쓰게 한다. "
            "명소 수집과 일정 수집을 **같은 노드 안에서 순차로** 부르면 자연히 그렇게 된다",
        ))

    for task, count in tasks.items():
        if count >= 2:
            out.append((
                "`{}` — {}회 실패".format(task, count),
                "처방 가지 후보 — 원인이 한 종류로 모이고 같은 입력에 같은 고칠 법이 "
                "있는지 본다. 없으면 재수집(LLM)에 둔다. 성공한 칸을 다시 안 "
                "모으는 장치(재수집 patch · 지적된 것만 Send)는 그래프 킷에 이미 있다",
            ))

    if repeated:
        out.append((
            "같은 오류 지문 반복",
            "route_after_info 가 이미 same_error_count 로 human_gate_a 로 뺀다. "
            "재수집(LLM)이 같은 오류를 반복해서 맡았다는 뜻이다 — "
            "그 지문에 정해진 고칠 법이 있으면 처방 가지 후보",
        ))

    return out


# --------------------------------------------------------------------------
# 나머지 파일
# --------------------------------------------------------------------------


def build_start_here(gaps, city_n, run_id, has_research=True):
    """그래프 킷 `graph/00_START_HERE.md` 를 **대신하는** 파일이다.

    ★ 학생이 이 폴더를 덮어쓰면 킷에 있던 예시본 안내가 사라진다. 그래서 순서 ·
      파일 표 · 금지 사항을 킷 예시본과 **같은 모양**으로 적는다 (다른 것은 맨 위 상자뿐).
    """
    out = []
    add = out.append
    add("# 여기서 시작합니다 — 내 루프 인계본")
    add("")
    add("> 루프 킷의 `export_graph_handoff.py` 가 **내 루프 결과**로 만든 인계본입니다.")
    add(">")
    if has_research:
        add("> 그래프 킷의 `graph/` 폴더에 **7개 파일을 통째로 덮어쓴** 뒤")
        add("> `python scripts/check_graph_readiness.py` 를 한 번 돌리세요.")
    else:
        add("> 이번 인계본은 `research_data.json` 이 빠진 **6개 파일**이라 그래프 킷 `graph/` 에")
        add("> **덮어쓰지 않습니다** (아래 ⚠ 참고).")
    add(">")
    add("> **그래프 구조는 루프 골격 + 진단 + 규칙 처방 가지입니다** (루프 골격 14 + 진단 2 + 처방 가지 3×2 = Studio 그림")
    add("> 22개). 구조는 그래프 킷 문서(`CLAUDE.md` · `specs/`)가 정본이고, 이 인계본이 정본인 것은")
    add("> 루프에서 넘어온 것 — 계약 · 취향 원문 · 실측 — 입니다.")
    if not has_research:
        add(">")
        add("> ⚠ **`research_data.json` 이 없습니다** (루프 A 를 돌리기 전입니다). 그래프는 이 파일로")
        add("> replay 를 돌리므로, **덮어쓰지 말고 킷의 예시 인계본으로 진행하세요.** 이 폴더는 옆에 두고")
        add("> `01_HANDOFF.md` 만 읽습니다. 섞어 쓰면 계약(내 나라·숫자)과 자료(예시)가 어긋납니다.")
        add("> `check_graph_readiness.py` 는 나라·일수가 다를 때만 막고, 개수 차이는 게이트의 SHORT 로 나타납니다.")
    add("")
    add("---")
    add("")
    add("## 이 폴더의 파일 {}개".format(7 if has_research else 6))
    add("")
    add("| 파일 | 언제 쓰나 | 누가 읽나 |")
    add("| --- | --- | --- |")
    add("| `00_START_HERE.md` | 지금 | 사람 |")
    add("| `01_HANDOFF.md` | **그래프를 설계할 때** | 사람 · STEP 1~5 의 `읽기 3` |")
    add("| `02_USER_REQUEST.md` | 취향 원문이 필요할 때 | `collect_city` 노드 |")
    add("| `03_CONTRACT.json` | 결과를 **채점할 때** | `scripts/check_*.py` ★ |")
    add("| `04_RUN_EVIDENCE.md` | **어디서 구멍이 났는지** 볼 때 · 루프판 기준선(8번) | 사람 · STEP 2 · STEP 6 |")
    add("| ↑ 안의 `quality_contract` | **정성 3회**의 규율과 렌즈 | `check_quality_passes.py` · `quality_pass` 노드 |")
    add("| `05_STATE_SEED.json` | 그래프를 **실행할 때** | Studio 입력 칸 |")
    if has_research:
        add("| `research_data.json` | 비교 기준선 · replay 모드 자료 | `travel_graph/research.py` |")
    else:
        add("| `research_data.json` | **(이번 인계본에는 없음 — 루프 A 미실행)** 비교 기준선 · replay 모드 자료 | `travel_graph/research.py` |")
    add("")
    add("---")
    add("")
    add("## 순서")
    add("")
    add("```text")
    add("1  01_HANDOFF.md 를 읽는다        무엇이 그대로고 무엇이 새로 필요한지")
    add("2  STEP 1~5 를 진행한다           결정 13개에 답한다 (코드는 완성본 — 권장값이 아닐 때만 바뀐다)")
    add("3  05_STATE_SEED.json 으로 돌린다  langgraph dev → Studio")
    add("4  같은 검사기로 잰다              python scripts/verify_all.py")
    add("5  STEP 6 — 처방 가지 추가 (조건부 · 실행 뒤)")
    add("                                  failure_report.py ③ · ③-2 에 후보가 있을 때만")
    add("```")
    add("")
    add("**3번과 4번의 숫자를 `04_RUN_EVIDENCE.md` 8번(루프판 기준선)과 비교하는 것이 이 실습의")
    add("결론입니다.** 5번은 실패 기록에 처방 가지 후보가 있을 때만 붙는 확장입니다 — 후보가 없으면")
    add("하지 않습니다. 결정이 없고(결정은 13개 그대로), 루프 골격은 건드리지 않습니다.")
    add("평소 실행에서는 `05_STATE_SEED.json` 의 `inject`(실패 재현)를 비워 둡니다.")
    add("")
    add("---")
    add("")
    add("## 절대 하지 말 것")
    add("")
    add("```text")
    add("03_CONTRACT.json 을 그래프용으로 '개선'하기")
    add("```")
    add("")
    add("계약을 고치는 순간 루프판과 그래프판을 **같은 자로 잴 수 없게 됩니다.**")
    add("이 실습의 요점은 \"같은 계약, 다른 실행 구조\"입니다. 계약은 잠겨 있습니다.")
    add("")
    add("---")
    add("")
    add("## 이번 인계본")
    add("")
    add("```text")
    add("run_id   : {}".format(run_id or "(실행 기록 없음)"))
    add("도시 수   : {}".format(city_n if city_n else "(미확정)"))
    add("상태     : {}".format("미완성 — 아래 참고" if gaps else "완성"))
    add("```")
    add("")
    if gaps:
        add("**미완성 항목**")
        add("")
        for gap in gaps[:10]:
            add("- {}".format(gap))
        if len(gaps) > 10:
            add("- ... 그 밖 {}건".format(len(gaps) - 10))
        add("")
        add("그래프 설계(STEP 1~5 읽기)는 이대로 진행해도 됩니다. 루프를 끝까지 돌린 뒤 다시 뽑으세요.")
        add("")
    return "\n".join(out) + "\n"


def build_state_seed(spec, limits, opts):
    request = as_dict(spec.get("request"))
    return {
        "_comment": "LangGraph 초기 상태. Studio 입력 칸은 5칸(country / days / style / "
                    "city_priority / inject)이며, 앞의 넷만 넣어도(또는 {} 로도) 나머지는 "
                    "read_request 가 채운다. inject 는 평소 비운다 — 실패 재현 칸이다 "
                    "(예: [\"image_dead\"]). 처방 가지 이름을 적으면 수집 직후 그 실패를 다시 "
                    "일으킨다 — 이미 있는 가지가 켜지는 것을 보거나 STEP 6 에서 새 가지의 시험지 "
                    "빨간불을 먼저 볼 때 쓴다. quality_* 는 루프 C(정성 완성도) 제어 칸이며 "
                    "quality_pass 에는 reducer 를 붙이지 않는다 (덮어쓰기 카운터). failure_kind · "
                    "failure_evidence · detour_* 는 진단 · 처방 가지 칸(킷 고정)이며 역시 reducer 가 "
                    "없다. detour_limit 은 처방 한도 — 처방 가지 하나가 사람 없이 돌 수 있는 "
                    "횟수이고, 처방 가지에서 합격하고 돌아온 방문은 바퀴(loop_*_iter)로 세지 않는다. "
                    "입력으로 쓰이는 것은 5칸뿐이다. 나머지 제어 칸은 read_request 가 다시 쓰므로"
                    "(loop_*_limit · same_error_limit · quality_passes_required 는 03_CONTRACT.json 값, "
                    "detour_limit 은 킷 고정값) 여기 값은 참고용이다. max_iterations 는 상태 칸이 없어 "
                    "invoke 때 버려진다 (기록용).",
        "country": request.get("country"),
        "days": request.get("days"),
        "style": request.get("style") or {},
        "city_priority": request.get("city_priority") or [],
        "country_intro": {},
        "cities": [],
        "city_failures": [],
        "info_verdict": "UNKNOWN",
        "info_short_slots": [],
        "page_verdict": "UNKNOWN",
        "page_short_slots": [],
        "quality_short_slots": [],
        "html_path": "",
        "loop_a_iter": 0,
        "loop_a_limit": limits.get("A"),
        "loop_b_iter": 0,
        "loop_b_limit": limits.get("B"),
        "quality_pass": 0,
        "quality_passes_required": limits.get("C"),
        "quality_verdict": "UNKNOWN",
        "same_error_count": 0,
        "same_error_limit": opts.get("same_error_limit"),
        "last_error_hash": "",
        "max_iterations": opts.get("max_iterations"),
        "inject": [],
        "failure_kind": "",
        "failure_evidence": [],
        "detour_attempts": {},
        "detour_limit": DETOUR_LIMIT,
        "detour_verdict": "",
        "history": [],
    }


# --------------------------------------------------------------------------
# 본체
# --------------------------------------------------------------------------


def with_top_country_days(data, spec):
    """research_data 에 최상위 `country` · `days` 가 없으면 채운 사본을 돌려준다.

    루프 킷 명세(specs/03_INFORMATION_COUNT.md)는 국가 · 일수를 `request` 안에 담게 하지만,
    그래프 킷(check_graph_readiness · image_dead · encoding)은 **최상위** `country` · `days` 를
    읽는다. 그래서 인계할 때 최상위가 비어 있으면 `research_data.request` → MASTER_SPEC 의
    `request` 순서로 채워 넣는다. 이미 있으면 그대로 둔다 (원본 객체를 그대로 돌려준다).
    """
    if not isinstance(data, dict):
        return data
    req = as_dict(data.get("request"))
    spec_req = as_dict(spec.get("request"))
    top = {}
    for key in ("country", "days"):
        if data.get(key) not in (None, ""):
            continue
        value = req.get(key)
        if value in (None, ""):
            value = spec_req.get(key)
        if value not in (None, ""):
            top[key] = value
    if not top:
        return data
    merged = dict(top)
    merged.update((k, v) for k, v in data.items() if k not in top)
    return merged


def collect_gaps(spec, data, state, events, root=ROOT):
    """무엇이 아직 안 채워졌는지 모은다. 없는 것을 있다고 쓰지 않기 위해서."""
    gaps = []
    holes = find_nulls(spec, "MASTER_SPEC")
    if holes:
        gaps.append("검사 계약에 미정 값 {}개 ({})".format(
            len(holes), ", ".join(holes[:3])))
    if not data:
        gaps.append("output/research_data.json 이 없습니다 (루프 A 미실행)")
    elif not city_names(data):
        gaps.append("도시가 아직 선정되지 않았습니다")
    if not (root / "output" / "travel_site.html").exists():
        gaps.append("output/travel_site.html 이 없습니다 (루프 B 미실행)")
    if not events:
        gaps.append("evidence/runs/ 에 실행 기록이 없습니다 (실측 없음)")
    if not state:
        gaps.append("state/loop_state.json 이 없습니다")
    return gaps


def main():
    parser = argparse.ArgumentParser(description="그래프 킷 인계 폴더 생성")
    parser.add_argument("--root", default=None)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else ROOT

    print(LINE)
    print(" 그래프 인계본 만들기")
    print(LINE)

    # 1) 검사 계약
    try:
        spec = load_machine_json(root / "MASTER_SPEC.md")
    except ContractError as exc:
        print(" [ERROR] " + str(exc))
        print(" 루프를 더 돌려도 해결되지 않습니다. STEP 7까지 끝내세요.")
        print(LINE)
        return 1

    if not isinstance(spec.get("count_contract"), dict):
        print(" [ERROR] MASTER_SPEC.md 에 count_contract 가 없습니다.")
        print(LINE)
        return 1

    #  계약 모양 오류(허용값 밖 · 0 이하 · 키 삭제)는 루프를 더 돌려도 안 풀린다 → exit 1.
    #  아직 채우지 않은 null 은 건너뛰므로 미완성 명세는 그대로 exit 2 로 인계본을 만든다.
    try:
        check_contract_shape(spec, "MASTER_SPEC.md")
    except ContractError as exc:
        print(" [ERROR] " + str(exc))
        print(" 루프를 더 돌려도 해결되지 않습니다. 계약값을 고친 뒤 다시 뽑으세요.")
        print(LINE)
        return 1

    # 2) 나머지 재료
    try:
        data = load_research(root)
    except ContractError as exc:
        print(" [ERROR] " + str(exc))
        print(LINE)
        return 1

    state = read_json(root / "state" / "loop_state.json", {}) or {}
    run_dir = latest_run_dir(root, args.run_id)
    events = read_events(run_dir)
    result_a, result_b, checker_note = read_shortfalls(root)
    result_c = read_quality(root, run_dir) if result_b is not None else None
    manifest = read_json(run_dir / "run_manifest.json", {}) if run_dir else {}

    limits = {
        "A": (as_dict(as_dict(spec.get("loops")).get("A"))).get("limit"),
        "B": (as_dict(as_dict(spec.get("loops")).get("B"))).get("limit"),
        "C": (as_dict(as_dict(spec.get("loops")).get("C"))).get("limit"),
    }
    opts = as_dict(spec.get("options"))
    cities = city_names(data)
    gaps = collect_gaps(spec, data, state, events, root)
    if checker_note:
        gaps.append("검사기를 돌리지 못했습니다: " + checker_note)
    #  파일이 다 있어도 판정이 SUCCESS 가 아니면 루프는 안 끝난 것이다 (exit 2 · '미완성').
    #  8번 기준선의 `verify_all` 줄과 같은 판정을 쓴다.
    verify_code, verdicts = overall_verdict(result_a, result_b, result_c)
    if verify_code != 0:
        gaps.append("verify_all 판정이 SUCCESS 가 아닙니다 (exit {} · {}) — 루프 A · B · C 가 모두 "
                    "PASS 여야 완성입니다".format(verify_code, " · ".join(verdicts) or "검사기를 못 돌림"))

    # 3) 쓰기
    out_dir = root / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    written = []

    def write(name, text):
        (out_dir / name).write_text(text, encoding="utf-8")
        written.append(name)

    has_research = (root / "output" / "research_data.json").exists()
    write("00_START_HERE.md",
          build_start_here(gaps, len(cities), run_dir.name if run_dir else None,
                           has_research))
    write("01_HANDOFF.md",
          build_handoff(spec, limits, opts, cities, gaps))
    write("04_RUN_EVIDENCE.md",
          build_evidence(state, events, result_a, result_b, run_dir, limits,
                         result_c, manifest))
    write("03_CONTRACT.json", json.dumps({
        "_comment": "루프 킷의 검사 계약. 그래프 결과도 이 기준으로 잰다. 바꾸면 비교가 깨진다.",
        "request": spec.get("request"),
        "count_contract": spec.get("count_contract"),
        "page_contract": spec.get("page_contract"),
        "quality_contract": spec.get("quality_contract"),
        "loops": spec.get("loops"),
        "options": spec.get("options"),
    }, ensure_ascii=False, indent=2) + "\n")
    write("05_STATE_SEED.json",
          json.dumps(build_state_seed(spec, limits, opts),
                     ensure_ascii=False, indent=2) + "\n")

    # 취향 원문은 요약하지 않고 그대로 복사한다
    user_request = root / "USER_REQUEST.md"
    if user_request.exists():
        write("02_USER_REQUEST.md", user_request.read_text(encoding="utf-8"))
    else:
        write("02_USER_REQUEST.md",
              "# 취향 원문 없음\n\nUSER_REQUEST.md 가 없습니다.\n")
        gaps.append("USER_REQUEST.md 가 없습니다")

    research = root / "output" / "research_data.json"
    if research.exists():
        raw = json.loads(research.read_text(encoding="utf-8-sig"))
        normalized = with_top_country_days(raw, spec)
        if normalized is raw:
            shutil.copyfile(research, out_dir / "research_data.json")
        else:
            (out_dir / "research_data.json").write_text(
                json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append("research_data.json")

    # 4) 보고
    print("")
    print(" 만든 곳: {}/".format(OUT_DIR))
    for name in sorted(written):
        size = (out_dir / name).stat().st_size
        print("   {:<24}{:>8} bytes".format(name, size))
    print("")

    if gaps:
        print(" [부족] 루프가 아직 끝나지 않아 {}가지가 비어 있거나 기준에 못 미칩니다.".format(len(gaps)))
        for gap in gaps[:6]:
            print("   - " + gap)
        if len(gaps) > 6:
            print("   ... 그 밖 {}건".format(len(gaps) - 6))
        print("")
        print(" 그래프 설계는 이대로도 됩니다. 루프를 끝까지 돌린 뒤 다시 뽑으세요.")
        if not has_research:
            print(" research_data.json 이 없으니 그래프 킷에 덮어쓰지 마십시오 — 킷의 예시 인계본으로")
            print(" 진행하고, 이 폴더는 옆에 두고 01_HANDOFF.md 만 읽습니다 (00_START_HERE.md 참고).")
        print(LINE)
        return 2

    print(" [완료] 그래프 킷으로 이 폴더를 통째로 옮기세요.")
    print(" 먼저 읽을 것: {}/00_START_HERE.md".format(OUT_DIR))
    print(LINE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
