"""노드 — **루프 골격 14개 + 진단 2개 + 규칙 처방 가지 공용 2개.**
**상태를 읽고 변경분을 돌려주는 것 말고는 아무 일도 하지 않는다.**

    ΔS = f(S)      노드가 변경분을 만든다        ← 이 파일
    S' = R(S, ΔS)  reducer 가 합친다             ← state.py
    v' = g(S')     라우터가 다음 노드를 고른다     ← edges.py

**노드는 LLM이 아니다.** 이 파일 안에 네 종류가 섞여 있다.

    결정론 코드   read_request · check_information · check_page · check_quality · build_page
                 diagnose_info · diagnose_page · fix_detour · test_detour
    LLM 호출     collect_country · select_cities · collect_city ·
                 repair_city · repair_country · rebuilder · quality_pass
    사람         human_gate_a · human_gate_b  (게이트 B 는 두 번 선다)

**그림에 보이는 노드는 22개**다. 루프 골격 14 · 진단 2 · 처방 가지 3개 × (fix · test).
처방 가지 노드 6개는 함수 두 개(`fix_detour` · `test_detour`)를 나눠 쓴다 — 모든 처방 가지가
같은 모양이라 함수도 같다. 어느 가지인지는 진단이 적어 둔 `failure_kind` 로 안다.
fix = 처방(규칙대로 고친다) · test = 재검(같은 시험지로 다시 잰다). 둘 다 LLM 을 부르지 않는다.

판정(`check_*`)을 LLM 에 맡기지 않는 것이 루프 킷의 핵심 교훈이었고, 그래프에서도
그대로다. **세는 일에 판단이 끼면 안 된다.**

`quality_pass` 만 예외처럼 보이지만 아니다. 그 노드는 **글을 고치는 쪽**이고,
판정은 옆의 `check_quality` 가 한다. 그리고 `check_quality` 가 보는 것은
품질이 아니라 **절차**다 — 3회를 규율대로 돌았는가, 위반이라 적은 것을 실제로
고쳤는가, 파일 해시가 그에 맞게 바뀌었는가.

`rebuilder` 도 예외가 아니다. 사람의 지시문을 읽고 **수정안을 내는 쪽**이 LLM 이고,
그 수정안을 적용하고 되돌아감을 확인하는 일은 `quality.apply_fixes` 가 결정론으로 한다.

게이트 두 노드는 `interrupt` 로 **멈춘다.** 세 정지 지점이 같은 5키 화면을 쓴다
(`gate_payload`). 자세한 규칙은 CLAUDE.md 10절에 있다.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import re
import sys

from langgraph.types import interrupt

from travel_graph import contract, detours, edges, page, quality, research
from travel_graph.detours import log as failure_log

# --------------------------------------------------------------------------- #
# 검사기 불러오기 — 루프 킷 파일을 그대로 쓴다
# --------------------------------------------------------------------------- #

_CHECKERS: dict = {}


def _checker(name: str):
    """`scripts/<name>.py` 를 불러 온다. **루프 킷과 바이트 단위로 같은 파일**이다.

    검사기를 그래프 안으로 베껴 오지 않는 이유: 베끼는 순간 두 판을 같은 자로
    잴 수 없게 된다. 파일을 그대로 두고 불러 쓴다.
    """
    if name in _CHECKERS:
        return _CHECKERS[name]
    path = contract.ROOT / "scripts" / (name + ".py")
    spec = importlib.util.spec_from_file_location("kit_" + name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"검사기를 불러오지 못했습니다: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _CHECKERS[name] = module
    return module


def _error_hash(checker: str, verdict: str, shorts) -> str:
    """오류 지문. 같은 지문이 반복되면 아무 진전이 없다는 뜻이다.

    ★ **부족 목록 전체**를 본다. 예전에는 `shorts[0]` 하나만 봤는데, 국가 소개가
      먼저 검사되므로 `기능1` 한 줄이 남아 있으면 도시 쪽이 4곳 → 3곳 → 2곳으로
      줄어도 지문이 그대로였다. 진전이 있는데 "진전 없음"으로 읽혀 조기 종료했다.

    ★ **부족이 없으면 빈 지문**을 돌려준다. 예전에는 PASS 에서도 지문이 생겨
      두 바퀴 연속 PASS 면 `같은 오류 반복 1/2` 가 떴다. 라우팅은 SHORT 일 때만
      이 값을 보므로 동작은 멀쩡했지만, **사람이 판단하는 화면에 거짓이 떴다.**
    """
    rows = sorted(str(x) for x in (shorts or []))
    if not rows:
        return ""
    raw = checker + "|" + str(verdict) + "|" + "\n".join(rows)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _as_list(value):
    return value if isinstance(value, list) else []


def _as_dict(value):
    return value if isinstance(value, dict) else {}


# --------------------------------------------------------------------------- #
# 1. read_request — 결정론
# --------------------------------------------------------------------------- #


def read_request(state) -> dict:
    """요청서를 읽어 상태의 입력 칸과 제어 칸을 채운다.

    Studio 입력이 비어 있어도 돌아야 하므로, 빈 칸은 인계본의 값으로 메운다.
    **여기서 채운 뒤에는 아무 노드도 이 값을 바꾸지 않는다.**
    """
    defaults = contract.request_defaults()
    lim = contract.limits()
    #  실패 재현(inject). 모르는 이름은 버리고 **버렸다고 적는다** — 조용히 무시하면
    #  "재현했는데 왜 처방 가지가 안 켜지지"를 사람이 겪는다.
    planted, unknown = detours.parse_inject(state.get("inject"))
    trail = [f"read_request: {state.get('country') or defaults.get('country')} "
             f"· 실행 모드 {research.mode()}"]
    if planted:
        trail.append(f"  ↳ ⚠ 실패 재현(inject) 예약: {', '.join(planted)} "
                     "— 수집 직후 그 실패를 다시 일으키고, 진단 노드가 찾아 처방 가지로 보냅니다")
    if unknown:
        trail.append(f"  ↳ 모르는 inject 이름을 버렸습니다: {', '.join(unknown)} "
                     f"(고를 수 있는 것: {', '.join(d.kind for d in detours.ALL)})")
    return {
        "country": state.get("country") or defaults.get("country"),
        "days": state.get("days") or defaults.get("days"),
        "style": state.get("style") or defaults.get("style") or {},
        "city_priority": state.get("city_priority") or defaults.get("city_priority") or [],
        "info_verdict": "UNKNOWN",
        "page_verdict": "UNKNOWN",
        "quality_verdict": "UNKNOWN",
        "loop_a_iter": 0,
        "loop_b_iter": 0,
        "quality_pass": 0,
        "same_error_count": 0,
        "last_error_hash": "",
        "loop_a_limit": lim["loop_a_limit"],
        "loop_b_limit": lim["loop_b_limit"],
        "same_error_limit": lim["same_error_limit"],
        "quality_passes_required": lim["quality_passes_required"],
        "inject": planted,
        "failure_kind": "",
        "failure_evidence": [],
        "detour_attempts": {},
        "detour_limit": detours.LIMIT,
        "detour_verdict": "",
        "history": trail,
    }


# --------------------------------------------------------------------------- #
# 2. collect_country — LLM · select_cities 와 나란히 돈다
# --------------------------------------------------------------------------- #


def collect_country(state) -> dict:
    """국가 소개 **첫 수집.** 고치는 일은 `repair_country` 가 맡는다."""
    intro, note, failure = research.collect_country_intro(state)
    #  실패 재현(inject). 비어 있으면 아무 일도 없다.
    planted = detours.inject("country", intro, state.get("inject"))
    #  변경분은 언제나 `return {...}` 리터럴로 돌려준다. 변수에 담았다가 내보내면
    #  `check_graph_shape.py` 가 무슨 키에 쓰는지 못 보고 그 노드를 건너뛴다 (6b).
    #  실패사유가 비어 있으면 `merge_failures` 가 그 줄을 지운다 — 조건문이 필요 없다.
    return {
        "country_intro": intro,
        "city_failures": [{"city": "(국가 소개)", "why": failure}],
        "history": [note] + planted,
    }


# --------------------------------------------------------------------------- #
# 3. select_cities — LLM · 여기서 정해진 개수가 병렬 폭이 된다
# --------------------------------------------------------------------------- #


def select_cities(state) -> dict:
    names, note = research.select_city_names(state)
    return {"selected_city_names": names, "history": [note]}


# --------------------------------------------------------------------------- #
# 4. collect_city — LLM · ★ 도시별로 병렬 실행된다
# --------------------------------------------------------------------------- #


def collect_city(payload) -> dict:
    """`Send` 가 넘긴 **도시 하나**만 처리한다.

    다른 도시의 결과를 보지 않는다. 그래서 나란히 돌 수 있다.
    돌려주는 것은 리스트 한 칸짜리 — 합치는 일은 reducer 가 한다.

    ★ 실패를 **빈 껍데기로 감추지 않는다.** `research.collect_one_city` 가 실패사유를
      함께 돌려주므로 그것을 `city_failures` 에 남긴다. 성공하면 빈 사유를 보내
      reducer 가 그 줄을 지운다 (성공 = 기록이 사라지는 것).
    """
    city_name = payload.get("city") or ""
    city, note, failure = research.collect_one_city(city_name, payload)
    #  실패 재현(inject). `fan_out_cities` 가 **첫 도시에만** 실어 보낸다.
    planted = detours.inject("city", city, payload.get("inject"))
    return {
        "cities": [city],
        "city_failures": [{"city": city_name, "why": failure}],
        "history": [note] + planted,
    }


# --------------------------------------------------------------------------- #
# 5. check_information — 결정론 검사기 A
# --------------------------------------------------------------------------- #


def _materialize(state) -> str:
    """상태에 모인 것을 검사기가 읽는 파일로 떨군다.

    검사기는 그래프를 모른다. `output/research_data.json` 만 본다.
    **판정 독립**(루프의 조건⑤)을 그대로 지키기 위한 다리다.
    """
    data = {
        "country": state.get("country"),
        "days": state.get("days"),
        "country_intro": _as_dict(state.get("country_intro")),
        "cities": _as_list(state.get("cities")),
    }
    path = contract.write_research(data)
    return str(path.relative_to(contract.ROOT)).replace("\\", "/")


def check_information(state) -> dict:
    """세어서 판정을 **상태에 쓴다.** 이것이 검사기가 노드가 되어야 하는 이유다.

    간선이 조건을 보려면 그 값이 상태에 있어야 한다.

    ★ **처방 가지에서 돌아온 방문은 바퀴로 세지 않는다.** 바퀴(`loop_a_iter`)는 검사
      횟수다(첫 수집 1, 재수집마다 +1). 처방 가지는 자기 한도(처방 한도 `detour_limit`)를 따로 갖는다. 이것을 세면 가지가
      한 번 돌 때마다 재수집 기회가 하나씩 사라진다 — 두 번이면 재수집이 한 번도 못 돈다.
      같은 이유로 '같은 오류 반복'(`same_error_count`)도 올리지 않는다.
    """
    research_path = _materialize(state)
    result = _checker("check_information_count").run(str(contract.ROOT))

    shorts = list(result.short)
    verdict = result.verdict
    back = state.get("detour_verdict") == "PASS"          # 처방 가지에서 합격하고 돌아왔다
    if back:
        #  지문은 새로 적되(다음 재수집 바퀴가 **처방 가지 뒤** 상태와 비교되게), 반복 횟수와
        #  바퀴는 그대로 둔다 — 처방 가지는 재수집이 아니다.
        fingerprint = _error_hash("check_information_count", verdict, shorts)
        same = state.get("same_error_count", 0)
        iteration = state.get("loop_a_iter", 0)
    else:
        fingerprint = _error_hash("check_information_count", verdict, shorts)
        same = state.get("same_error_count", 0)
        same = same + 1 if fingerprint and fingerprint == state.get("last_error_hash") else 0
        iteration = state.get("loop_a_iter", 0) + 1
    return {
        "info_verdict": verdict,
        "info_short_slots": shorts,
        "research_path": research_path,
        "loop_a_iter": iteration,
        "last_error_hash": fingerprint,
        "same_error_count": same,
        "detour_verdict": "",
        "history": [f"check_information: {verdict} · 부족 {len(shorts)}곳 · {iteration}바퀴"
                    + (" (처방 가지에서 복귀 — 바퀴를 쓰지 않음)" if back else "")],
    }


# --------------------------------------------------------------------------- #
# 5b. diagnose_info — 결정론 진단 A · **판정 다음에 원인을 가린다**
# --------------------------------------------------------------------------- #


def _diagnose(loop: str, state, *, hold: str = "") -> tuple:
    """그 루프의 시험지를 **등록 순서대로** 풀어 처방 가지 하나를 고른다.

    돌려주는 것: (고른 가지 이름 또는 "", 게이트용 증상 줄, 기록용 증상 표).

    ★ 처방 한도를 다 쓴 가지는 건너뛰고 다음 것을 본다. 건너뛴 증상은 버리지 않고
      증상 줄에 남긴다 — 사람이 게이트에서 "처방 가지가 못 고친 것"을 봐야 한다.
    ★ `hold` 가 있으면 가지를 고르지 않는다 (예: 정성 회차 중). 증상은 남긴다.
    """
    limit = state.get("detour_limit") or 0
    tried = _as_dict(state.get("detour_attempts"))
    kind, evidence, table = "", [], {}
    for d, result, crashed in detours.probe(loop, contract.ROOT):
        lines = [crashed] if crashed else list(result.short)
        entry = {"count": _symptom_count(lines), "lines": lines[:8]}
        if crashed:
            #  ★ 시험지가 터진 것은 **증상이 아니다.** 처방 가지는 돌지도 않았다 — 따로 적는다.
            entry["why"] = "시험지가 멈춤"
            evidence.append(f"[{d.kind}] 시험지가 멈춤 — {crashed}")
        elif not kind and not hold and int(tried.get(d.kind) or 0) < limit:
            kind = d.kind
            evidence = [f"[{d.kind}] {line}" for line in lines[:6]] + evidence
        else:
            why = hold or f"처방 한도 {tried.get(d.kind, 0)}/{limit} 를 다 썼습니다"
            entry["why"] = why
            evidence.append(f"[{d.kind}] 처방 가지를 타지 않음 ({why}) — {_first_symptom(lines)}")
        table[d.kind] = entry
    return kind, evidence, table


def _first_symptom(lines) -> str:
    """요약 줄(`…: 목표 0 / 실제 N`)을 건너뛴 첫 증상 줄."""
    for line in lines:
        if not re.search(r": 목표 0 / 실제 \d+$", str(line)):
            return str(line)
    return str(lines[0]) if lines else ""


def _log_diagnosis(config, node: str, loop: str, state, shorts, rules, kind, table) -> str:
    """실패 기록 한 줄. STEP 6 후보를 가리는 재료다 (`scripts/failure_report.py`).

    ③  '그 밖'(규칙표에 없는 부족) · 수집 실패 · 가지가 못 맡은 증상 → 아직 가지가 없는 실패
    ③-2 가지 없이(`failure_kind` 빈칸) SHORT 로 남은 `causes` → **재수집(LLM)이 맡은 원인.**
        같은 원인이 여러 바퀴 · 여러 실행에 되풀이되면 처방 가지 후보다. 그래서 바퀴 번호
        (`loop_iter`)를 함께 적는다 — 처방 가지에서 돌아온 방문은 같은 바퀴라 한 번만 센다.
    """
    causes = classify(shorts, rules)
    return failure_log.write(config, {
        "node": node, "loop": loop, "mode": research.mode(),
        "verdict": state.get("info_verdict" if loop == "A" else "page_verdict"),
        "inject": _as_list(state.get("inject")),                # 재현 실행은 보고서가 후보로 세지 않는다
        "loop_iter": state.get("loop_a_iter" if loop == "A" else "loop_b_iter"),
        "loop_limit": state.get("loop_a_limit" if loop == "A" else "loop_b_limit"),
        "same_error": state.get("same_error_count") if loop == "A" else None,
        "failure_kind": kind,
        "decision": (f"처방 가지 fix_{kind}" if kind else "루프 골격 그대로"),
        "symptoms": table,
        "causes": [{"원인": c["원인"], "몇 곳": c["몇 곳"], "예": c["예"]} for c in causes],
        "unmatched": [s for s in (str(x) for x in shorts)
                      if not any(needle in s for needle, _n, _h in rules)][:10],
        "city_failures": [r for r in _as_list(state.get("city_failures"))
                          if isinstance(r, dict) and (r.get("why") or "").strip()],
    })


def _symptom_count(lines) -> int:
    """시험지의 요약 줄(`…: 목표 0 / 실제 N`)에서 증상 수를 모은다. 없으면 줄 수."""
    total = 0
    for line in lines:
        match = re.search(r": 목표 0 / 실제 (\d+)$", str(line))
        if match:
            total += int(match.group(1))
    return total or len(lines)


def _diagnosis_line(node: str, kind: str, table: dict, state) -> str:
    if kind:
        count = table.get(kind, {}).get("count", 0)
        tries = int(_as_dict(state.get("detour_attempts")).get(kind) or 0)
        title = getattr(detours.get(kind), "title", kind)
        return (f"{node}: ▷ {title} — 증상 {count}곳 "
                f"→ 처방 가지 fix_{kind} ({tries + 1}/{state.get('detour_limit')}회째)")
    if table:
        parts = [f"{k}: {v.get('why', '')}" for k, v in table.items()]
        broken = [k for k, v in table.items() if v.get("why") == "시험지가 멈춤"]
        head = ("시험지가 멈춘 처방 가지가 있음 — 시험지를 고치십시오" if broken
                else "증상은 있지만 처방 가지를 타지 않음")
        return f"{node}: {head} ({' · '.join(parts)}) → 루프 골격 그대로"
    return f"{node}: 처방 가지 대상 없음 → 루프 골격 그대로"


def diagnose_info(state, config=None) -> dict:
    """진단 A — 검사기 A 가 **판정**(기준을 채웠나)을 쓴 뒤, 이 노드가 **원인**을 가린다.

        check_information   "SHORT · 부족 9곳"         세는 일    (루프 킷과 같은 검사기)
        diagnose_info       "이 중 죽은 사진 주소 1곳"  가리는 일  (처방 가지 시험지)

    ★ 판정이 PASS 여도 돈다. 깨진 글자 · 비ASCII 주소는 검사기가 세지 않는 결함이다.
    ★ 결정론이다. 시험지를 풀어 볼 뿐 LLM 을 부르지 않는다.
    ★ 실패 기록(`evidence/failures/<thread>.jsonl`)에 한 줄 남긴다 — STEP 6 후보를 가리는 재료.
    """
    kind, evidence, table = _diagnose("A", state)
    shorts = _as_list(state.get("info_short_slots"))
    _log_diagnosis(config, "diagnose_info", "A", state, shorts, _CAUSE_A, kind, table)
    return {
        "failure_kind": kind,
        "failure_evidence": evidence,
        "history": [_diagnosis_line("diagnose_info", kind, table, state)],
    }


# --------------------------------------------------------------------------- #
# 6. repair_city — LLM · ★ **지적된 도시만** 병렬로 다시 돈다
# --------------------------------------------------------------------------- #


def repair_city(payload) -> dict:
    """`Send` 가 넘긴 **다친 도시 하나**만 고친다.

    ★ 예전에는 `research` 노드 하나가 안에서 **모든 도시**를 다시 불렀다. 다낭만
      터져도 하노이·호이안이 `collect_one_city` 로 들어갔고, 그 도시들은 지적이
      없어서 재수집 분기를 못 타고 **첫 수집 프롬프트로 떨어졌다.** 멀쩡한 도시를
      통째로 다시 뽑은 것이다. 부족한 칸이 줄지 않던 큰 이유가 이것이었다.

      지금은 라우터(`edges.fan_out_repairs`)가 다친 도시만 고른다. 손대지 않은
      도시는 **호출 자체가 일어나지 않는다.**

    ★ 첫 수집과 같은 fan-out 자리다. 그래서 `cities` 에 reducer 가 필요하고,
      그 reducer 는 `operator.add` 가 아니라 **이름으로 덮어쓰는 upsert** 여야 한다.
      되돌아오는 간선이 있는 그래프에서 reducer 는 멱등해야 한다.
    """
    city_name = payload.get("city") or ""
    city, note, failure = research.repair_one_city(
        city_name, payload, _as_list(payload.get("shorts")))
    return {
        "cities": [city],
        "city_failures": [{"city": city_name, "why": failure}],
        "history": [note],
    }


# --------------------------------------------------------------------------- #
# 6b. repair_country — LLM · ★ 국가 소개의 **지적된 칸만** 다시 돈다
# --------------------------------------------------------------------------- #


def repair_country(payload) -> dict:
    """`Send` 가 넘긴 **국가 소개 지적 목록**만 고친다.

    ★ 왜 뒤늦게 생겼나. 국가 소개는 "2,677자라 잘릴 위험이 없으니 1회차에 실패할
      이유가 거의 없다"는 이유로 재수집에서 빠져 있었다. 그 근거는 **분량 실패만**
      배제한다. 실제로 터진 것은 **수집 부족**이었고 — 근거 15건을 한 번에 요구하는데
      모델이 얇게 내고 스스로 끝냈다 — 그 실패 방식은 분량과 아무 상관이 없다.
      되먹임이 없으니 부족이 그대로 최종 보고서까지 갔다.

    ★ `repair_city` 와 **같은 규격**이다. 지적된 칸만, patch 로, 지난 결과 위에.
      전체를 다시 뽑게 하면 멀쩡하던 `매력` 3건이 사라지고 부족이 오히려 는다.

    ★ **fan-out 이지만 갈래가 하나다.** 국가는 하나뿐이라 `Send` 도 하나만 나간다.
      그래서 `country_intro` 는 한 걸음에 쓰는 노드가 하나뿐이고 **reducer 가
      필요 없다.** 도시(`cities`)와 다른 점이다 — 그쪽은 도시 수만큼 동시에 쓴다.
    """
    intro, note, failure = research.repair_country_intro(
        payload, _as_list(payload.get("shorts")))
    trail = [note]
    if failure:
        trail.append("  \u21b3 국가 소개 재수집 실패: " + failure[:120])
    return {
        "country_intro": intro,
        #  ★ 성공하면 **실패 기록을 지운다.** `collect_country` 가 남긴
        #    `(국가 소개)` 줄을 여기서 거두지 않으면 `merge_failures` 가 지울 기회를
        #    영영 못 얻는다. 고쳐진 뒤에도 게이트가 "그 도시를 아예 못 모았습니다"를
        #    권장으로 띄우게 된다 — 틀린 권장은 없느니만 못하다.
        "city_failures": [{"city": "(국가 소개)", "why": failure}],
        "history": trail,
    }


# --------------------------------------------------------------------------- #
# 6c. 규칙 처방 가지 — fix_<이름> · test_<이름> 이 **함께 쓰는** 두 함수 (킷 고정)
# --------------------------------------------------------------------------- #
#
#   diagnose_* ─<이름>─▶ fix_<이름> ─▶ test_<이름> ─┬ back  → check_*       (검사기로 복귀)
#                        (fix_detour)  (test_detour)  ├ retry → fix_<이름>    (한 번 더)
#                                                     └ gate  → human_gate_* (사람에게)
#
#   모든 처방 가지가 같은 모양이라 함수도 같다. 어느 가지인지는 진단이 적어 둔
#   `failure_kind` 로 안다 — 가지는 한 번에 하나만 돌기 때문에 헷갈릴 일이 없다.
#
#   ★ 처방 가지가 쓸 수 있는 칸은 **정해져 있다** — 데이터(`cities` · `country_intro`)와
#     가지 칸(`detour_*` · `failure_evidence`). 판정 · 바퀴 · 게이트 칸은 쓰지 않는다.
#     아래 두 함수의 `return {...}` 이 그 약속이다. `check_graph_shape.py` 11번 검사가 본다.


def fix_detour(state, config=None) -> dict:
    """처방 가지의 **고치는** 칸(처방). 결정론이다 — 같은 입력이면 같은 결과가 나온다.

    ★ 데이터를 고친 뒤 **상태로 돌려준다.** `build_page` · `check_information` 은 파일이
      아니라 상태에서 다시 만든다 — 파일만 고치면 다음 걸음에 덮어써진다 (`rebuilder` 와
      같은 이유 · 같은 고칠 법).
    ★ 시험지가 볼 수 있게 파일에도 쓴다. 루프 B 처방 가지는 화면(HTML)도 다시 그린다.
    """
    kind = state.get("failure_kind") or ""
    d = detours.get(kind)
    tries = dict(_as_dict(state.get("detour_attempts")))
    attempt = int(tries.get(kind) or 0) + 1
    tries[kind] = attempt
    data = {
        "country": state.get("country"),
        "days": state.get("days"),
        "country_intro": copy.deepcopy(_as_dict(state.get("country_intro"))),
        "cities": copy.deepcopy(_as_list(state.get("cities"))),
    }
    if d is None:
        outcome = {"fixed": [], "unfixed": [f"등록되지 않은 처방 가지입니다: '{kind}'"]}
    else:
        outcome = detours.fix(kind, data, attempt=attempt, mode=research.mode())
        contract.write_research(data)
        if d.loop == "B":
            page.write(data)                                    # 화면을 다시 그린다
    trail = [f"fix_{kind}: {attempt}/{state.get('detour_limit')}회째 · "
             f"고침 {len(outcome['fixed'])}곳 · 못 고침 {len(outcome['unfixed'])}곳"]
    trail += ["  ↳ " + line for line in outcome["fixed"][:3]]
    trail += ["  ↳ 못 고침: " + line for line in outcome["unfixed"][:3]]
    return {
        "cities": data["cities"],
        "country_intro": data["country_intro"],
        "detour_attempts": tries,
        "history": trail,
    }


def test_detour(state, config=None) -> dict:
    """처방 가지의 **시험** 칸(재검). 진단 때 푼 **같은 시험지**를 다시 푼다.

    합격이면 루프 골격의 검사기로 돌아간다(`route_after_detour` → back). 거기서 루프 킷과
    같은 검사기로 다시 잰다 — 이 시험지는 "그 문제가 사라졌나"만 보기 때문이다.
    """
    kind = state.get("failure_kind") or ""
    d = detours.get(kind)
    try:
        result = detours.run_test(kind, contract.ROOT)
        passed = result.verdict == "PASS"
        lines = list(result.short)
    except Exception as exc:                                    # noqa: BLE001
        passed, lines = False, [f"시험지가 멈춤 — test_{kind}.py 가 실행 중에 멈췄습니다 — "
                                f"{type(exc).__name__}: {str(exc)[:120]}"]
    tries = int(_as_dict(state.get("detour_attempts")).get(kind) or 0)
    limit = state.get("detour_limit") or 0
    where = (d.home if passed else (d.fix_node if tries < limit else d.gate)) if d else "?"
    failure_log.write(config, {
        "node": "test_" + kind, "loop": getattr(d, "loop", "?"), "mode": research.mode(),
        "inject": _as_list(state.get("inject")),
        "failure_kind": kind, "detour_verdict": "PASS" if passed else "FAIL",
        "attempt": tries, "limit": limit, "next": where, "evidence": lines[:8],
    })
    return {
        "detour_verdict": "PASS" if passed else "FAIL",
        "failure_evidence": [] if passed else [f"[{kind}] {line}" for line in lines[:8]],
        "history": [f"test_{kind}: {'PASS' if passed else 'FAIL'} · {tries}/{limit}회 "
                    f"→ {where}" + (" (검사기로 복귀)" if passed else "")],
    }


# --------------------------------------------------------------------------- #
# 7. human_gate_a — 사람 · 외부 루프 A
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# 게이트 공통 — **세 정지 지점이 같은 모양으로 묻는다**
# --------------------------------------------------------------------------- #
#
#   ① 지금    한 줄 요약        판정 · 진행 · 부족 개수
#   ② 왜      원인 묶음         목록이 아니라 **요약**이다
#   ③ 권장    상황에서 계산     고정 문구로 두면 틀린 권장을 하게 된다
#   ④ 고르기  선택지            고르면 무슨 일이 일어나는지까지
#   ⑤ 답      입력 형태 그대로  무엇을 채워야 하는지 보이게
#
# 예전 게이트 A 는 키가 10개였고 `원인`(요약)과 `못 채운 칸`(원본 10줄)을 함께
# 줬다. 요약을 만들어 놓고 원본도 보여 주면 요약을 읽지 않는다. 원본이 필요하면
# `research_path` 파일을 열면 된다.

#: 게이트 A(정보량) 원인 규칙. **좁은 것부터** 놓는다 — 앞에서부터 먼저 맞는 하나로
#: 분류하므로, `목표` 같은 넓은 말이 앞에 오면 이미지 부족이 '개수 모자람'으로
#: 잘못 묶여 "고칠 곳이 하나"라는 사실이 화면에서 사라진다.
_CAUSE_A = (
    ("이미지 주소가 열리지 않았습니다", "이미지 주소가 죽어 있음",
     "정보가 없어서가 아니라 주소가 틀려서입니다. `지시문` 에 "
     "`영문 파일명을 우선 쓰고 Commons 에서 실제로 확인한 것만 쓰라`고 적으면 잘 붙습니다"),
    ("살아 있는 이미지", "이미지 주소가 죽어 있음",
     "정보가 없어서가 아니라 주소가 틀려서입니다. `지시문` 에 고칠 방향을 적으십시오"),
    #  ★ 해시가 든 upload 주소 — 실측(8/8c)의 모양. 규칙이 없으면 '그 밖'으로 떨어져 실패 기록
    #    보고서에 "아직 처방 가지가 없는 실패"로 뜬다. 실제로는 image_dead 처방 가지가 맡는다.
    ("손으로 만들 수 없는 주소 형태", "이미지 주소가 죽어 있음",
     "해시가 든 upload 주소입니다 — 진단이 image_dead 처방 가지로 보내 권장 형태로 바로잡습니다"),
    ("verified", "이미지를 아직 안 모음",
     "그 칸에 image 자체가 없습니다. 한 바퀴 더 돌리면 채워질 가능성이 높습니다"),
    #  ★ 주소 · 대체문구가 **비어 있는** 줄. 규칙이 없으면 '그 밖'으로 떨어져 실패 기록
    #    보고서에 매번 "새 처방 가지 후보"로 뜬다 — replay 1회차가 일부러 비우는 칸이다.
    ("url 이 없습니다", "이미지를 아직 안 모음",
     "그 칸에 사진 주소가 없습니다. 재수집이 채웁니다 (죽은 주소와는 다릅니다)"),
    ("alt 가 없습니다", "이미지를 아직 안 모음",
     "그 칸에 사진 설명(alt)이 없습니다. 재수집이 채웁니다"),
    ("같은 근거 반복", "같은 근거를 복제함",
     "`이미 있는 것과 다른 출처로 찾으라`고 지시하십시오"),
    #  ★ **"개수가 모자람"보다 반드시 앞에 온다.** 이 줄에도 `목표 2 / 실제 1` 이
    #    붙어 있어서 뒤에 두면 개수 문제로 묶이고, 고칠 법이 정반대가 된다 —
    #    "더 찾아라"가 아니라 "**다른 출처로** 찾아라"다. 같은 출처에서 한 건을
    #    더 얹으면 건수는 늘어도 이 검사는 그대로 실패한다.
    ("· 서로 다른 출처", "출처가 겹침 (건수가 아니라 **출처**가 문제)",
     "건수를 늘리는 게 아닙니다. 이미 쓴 것과 **도메인이 다른** 곳에서 찾아 "
     "기존 항목 하나를 갈아 끼우십시오"),
    ("왜 넣었는지", "설명이 하한보다 짧음",
     "지적된 날의 블록을 **하나도 빼지 말고 전부** 다시 쓰게 하십시오"),
    #  ★ 이미지·중복·출처 규칙보다 **뒤에** 둔다. `기능1 국기이미지` 는 국가 칸이지만
    #    고칠 방법은 이미지 문제와 같다 — 먼저 두면 그 사실이 화면에서 사라진다.
    ("기능1: country_intro", "국가 소개를 아직 못 만듦",
     "칸이 비어 있는 게 아니라 **통째로 없습니다.** 첫 수집이 실패했을 수 있습니다. "
     "`history` 의 `collect_country:` 줄에 폴백이 찍혔는지 보십시오"),
    ("기능1 환율", "국가 소개 — **변동값**이라 출처를 못 붙임",
     "값은 아는데 **인용할 자리**를 못 찾는 종류입니다. `⑤ 답` 의 `note` 에 "
     "`조회한 날짜를 함께 적고, 값을 고시하는 곳을 출처로 써라`고 적으십시오. "
     "그래도 안 붙으면 몇 바퀴를 더 돌려도 같습니다"),
    ("기능1 항공권가격", "국가 소개 — **변동값**이라 출처를 못 붙임",
     "환율과 같은 종류입니다. 날짜와 조회처를 함께 적게 하십시오"),
    ("기능1", "국가 소개 — 근거가 모자람",
     "`more` 로 채워집니다. `repair_country` 가 **지적된 칸만** patch 로 고칩니다. "
     "칸마다 계약이 정한 건수가 필요하니 `한 번의 검색으로 여러 건을 다 채우려 하지 말고 칸마다 "
     "따로 찾으라`고 적으면 잘 붙습니다"),
    ("목표", "개수가 모자람",
     "실제로 더 찾아야 합니다. 한 바퀴 더 돌릴 값어치가 있습니다"),
)

#: 게이트 B(페이지) 원인 규칙.
_CAUSE_B = (
    ("초기 닫힘", "처음에 닫혀 있어야 하는데 펼쳐져 있음",
     "아코디언·툴바·관광지 상세는 처음에 닫혀 있어야 합니다. 데이터가 아니라 "
     "화면 문제이므로 `rebuild` 쪽입니다"),
    ("addEventListener", "클릭을 코드로 잇지 않음",
     "이름표만 있고 동작이 없습니다. 주석이나 쓰이지 않는 문자열은 통과하지 않습니다"),
    ("script 블록", "클릭을 코드로 잇지 않음",
     "화면을 움직이는 script 가 없습니다"),
    ("클릭 연결", "클릭을 코드로 잇지 않음", "핸들러를 연결하십시오"),
    ("화면에 없습니다", "모은 내용이 화면에 안 그려짐",
     "데이터는 있는데 페이지가 그리지 않았습니다. `rebuild` 로 화면만 다시 만들면 됩니다"),
    ("채우다 만 표시", "자리표시자가 남아 있음",
     "TODO·(작성 예정) 같은 표시가 화면에 남았습니다"),
    ("바깥 파일", "단일 HTML 규약 위반",
     "CSS·JS 를 그 파일 **안에** 넣어야 합니다"),
    ("단일 HTML", "단일 HTML 규약 위반", "파일 하나로 만들어야 합니다"),
    ("구역", "이름표 배치가 계약과 다름",
     "도시 단추는 툴바 밖, 도시 칸·관광지·상세·뒤로 가기는 툴바 안입니다"),
    ("툴바", "이름표 배치가 계약과 다름", "배치 계약을 다시 보십시오"),
    ("목표", "화면 칸이 모자람",
     "대개 수집이 덜 된 것입니다. 화면이 아니라 데이터 문제이면 `research` 쪽입니다"),
)

#: 게이트 C(정성) 원인 규칙.
_CAUSE_C = (
    ("실행 폴더가 없습니다", "정성 점검을 아직 시작하지 않음",
     "정상 상태입니다. `done` 을 고르면 3회를 시작합니다"),
    ("정성 기록 폴더", "회차 기록이 남지 않음",
     "회차가 돌긴 했는데 기록이 없습니다. 판정 자체가 막혔을 수 있습니다"),
    ("마지막 회차 = 지금 파일", "해시 사슬이 끊김",
     "회차 뒤에 파일이 바뀌었습니다. `rebuild` 를 고르면 회차가 0으로 되돌아갑니다"),
    ("되돌", "수정이 계약을 깨뜨려 되돌아감",
     "그 회차 수정이 루프 A·B 를 깨서 자동으로 되돌려졌습니다"),
    ("위반", "위반이라 적고 고치지 않음",
     "판정자가 위반이라 적었는데 fix 가 없습니다"),
)


def classify(shorts, rules) -> list:
    """못 채운 칸을 **원인별로 묶는다.** LLM 이 아니라 문자열 매칭 — 결정론이다.

    ★ 왜 이 칸이 필요한가. 실측에서 못 채운 칸 40곳 중 27곳이 **이미지 한 종류**에서
      나왔다. 목록만 보면 "마흔 군데가 부족하다"로 읽히지만 실제로는 **고칠 곳이
      한 종류**다. 사람이 선택지를 고르려면 그 사실을 알아야 한다 — 목록 열 줄이
      아니라 이 요약이 판단 재료다.

    ★ 규칙표를 **인자로 받는다.** 그래서 게이트 세 곳이 같은 함수를 쓴다.
    """
    buckets: dict = {}
    #  ★ 사진이 **아예 없는** 칸은 검사기가 세 줄을 낸다 — `목표 살아 있는 이미지 1 / 실제
    #    부족` · `url 이 없습니다` · `alt 가 없습니다`. 첫 줄만 보면 "주소가 죽음"으로 묶여,
    #    같은 사진 한 장이 두 원인으로 갈라지고 권장까지 어긋난다. 같은 칸에 `url 이 없습니다`
    #    가 있으면 그 칸의 "살아 있는 이미지" 줄도 **아직 안 모음**으로 센다.
    empty_rule = next((r for r in rules if r[0] == "url 이 없습니다"), None)
    empty_slots = {str(x).split(": ", 1)[0] for x in _as_list(shorts)
                   if "url 이 없습니다" in str(x)}
    for line in _as_list(shorts):
        text = str(line)
        if (empty_rule and "살아 있는 이미지" in text
                and text.split(": ", 1)[0] in empty_slots):
            _, name, howto = empty_rule
            buckets.setdefault(name, {"수": 0, "조치": howto, "예": text})["수"] += 1
            continue
        for needle, name, howto in rules:
            if needle in text:
                buckets.setdefault(name, {"수": 0, "조치": howto, "예": text})["수"] += 1
                break
        else:
            buckets.setdefault("그 밖", {"수": 0, "조치": "목록을 직접 보십시오",
                                        "예": text})["수"] += 1
    total = len(_as_list(shorts)) or 1
    return [{"원인": name, "몇 곳": f"{d['수']} / {total}", "고치려면": d["조치"],
             "예": d["예"][:90]}
            for name, d in sorted(buckets.items(), key=lambda kv: -kv[1]["수"])]


def _orphan_lines(state) -> list:
    """**어느 재수집 노드로도 못 가는 부족.** 고칠 수 없다는 사실을 숨기지 않는다.

    ★ 왜 필요한가. `more` 를 골라도 보낼 곳이 없으면 라우터가 조용히 `build` 로
      떨어뜨린다. 사람은 "더 모으라고 했는데 왜 페이지가 나왔지"를 겪는다.
      화면이 먼저 "이건 재수집으로 못 고칩니다"라고 말해야 한다.
    """
    lines = edges.orphan_shorts(state)
    if not lines:
        return []
    return [{"원인": "재수집으로 못 고치는 부족",
             "몇 곳": f"{len(lines)} / {len(_as_list(state.get('info_short_slots')))}",
             "고치려면": "도시 이름도 `기능1` 도 없는 줄이라 보낼 재수집 노드가 "
                      "없습니다. `more` 를 골라도 이 칸은 그대로입니다 — "
                      "`proceed` 로 넘기고 보고서에 남기거나, 사람이 직접 고칩니다",
             "예": lines[0][:110]}]


def _failure_lines(state) -> list:
    """수집 자체가 실패한 도시. **부족 목록에는 거의 안 잡히는 종류다.**

    빈 도시는 검사기가 `관광지 수 3/0` 한 줄만 내므로 "좀 모자라네"로 읽힌다.
    실제로는 그 도시를 아예 못 모은 것이라 판단이 완전히 달라진다.
    """
    out = []
    for row in _as_list(state.get("city_failures")):
        if isinstance(row, dict) and (row.get("why") or "").strip():
            out.append({"원인": f"{row.get('city')} — 수집 실패",
                        "몇 곳": "도시 1곳 통째",
                        "고치려면": "부족이 아니라 파이프가 터진 것입니다. "
                                 "인계본에 없는 도시이거나 응답이 잘렸습니다",
                        "예": str(row.get("why"))[:120]})
    return out


def _detour_lines(state) -> list:
    """**처방 가지가 못 고친 것 · 처방 가지를 타지 않은 증상.** 게이트 화면 맨 앞에 둔다.

    ★ 처방 가지는 "정해진 절차로 고칠 수 있는 문제"만 맡는다. 그 절차로도 안 됐다는 것은
      사람이 알아야 하는 사실이다 — 조용히 넘기면 가장 나쁜 실패다. 증상 줄은 진단 ·
      시험 노드가 `failure_evidence` 에 `[이름] …` 모양으로 남긴다.
    """
    evidence = [str(x) for x in _as_list(state.get("failure_evidence")) if str(x).strip()]
    kinds = []
    for line in evidence:
        match = re.match(r"\[(\w+)\]", line)
        if match and match.group(1) not in kinds:
            kinds.append(match.group(1))
    rows = []
    for kind in kinds:
        mine = [x for x in evidence if x.startswith("[" + kind + "]")]
        bare = [x[len(kind) + 3:] for x in mine]
        d = detours.get(kind)
        title = d.title if d else kind
        if any(x.startswith("시험지가 멈춤") for x in bare):
            #  시험지 자체가 터졌다 — 판정을 못 한 것이지 증상이 있는 것이 아니다.
            rows.append({"원인": "처방 가지 시험지가 깨짐 — " + title,
                         "몇 곳": "시험지 오류",
                         "고치려면": (f"`python scripts/detour_tests/test_{kind}.py` 를 혼자 돌려 오류 "
                                  f"줄을 고치십시오 (STEP 6). 그래프는 그대로 진행해도 됩니다"),
                         "예": mine[0][:110]})
        elif any(x.startswith("처방 가지를 타지 않음 (정성") for x in bare):
            rows.append({"원인": "처방 가지를 미룸 — " + title + " (정성 회차 중)",
                         "몇 곳": f"{_symptom_count(bare)}곳",
                         "고치려면": ("정성이 시작된 뒤라 파일 해시 사슬을 지키려고 미뤘습니다. "
                                  "`research` · `rebuild` 를 고르면 정성이 0 으로 돌아가고 처방 가지가 다시 섭니다"),
                         "예": mine[0][:110]})
        else:
            rows.append({"원인": "처방 가지가 못 고침 — " + title,
                         "몇 곳": f"{_symptom_count(bare)}곳",
                         "고치려면": (detours.howto(kind)
                                  or "실패 기록(evidence/failures/)을 열어 무엇이 남았는지 보십시오"),
                         "예": mine[0][:110]})
    return rows


def gate_payload(*, 지금, shorts, rules, choices, 권장, 답, state=None, detour=True) -> dict:
    """세 게이트가 공유하는 화면. **키 순서가 곧 읽는 순서다.**"""
    #  ★ 처방 가지가 못 고친 것 · 고아 부족(어느 재수집 노드로도 못 가는 것)을 **맨 앞에**
    #    둔다. "더 모으면 되는 부족"과 "고칠 방법이 없는 부족"은 판단이 완전히 다르다.
    causes = ((_detour_lines(state or {}) if detour else [])
              + _orphan_lines(state or {}) + _failure_lines(state or {})
              + classify(shorts, rules))
    return {
        "① 지금": 지금,
        "② 왜": causes or ["없음"],
        "③ 권장": 권장,
        "④ 고르기": choices,
        "⑤ 답": 답,
    }


# --------------------------------------------------------------------------- #
# 7. human_gate_a — 사람 · 외부 루프 A
# --------------------------------------------------------------------------- #


#: 원인별로 **그대로 붙여 넣을 수 있는 지시문**. 게이트 `⑤ 답` 의 `note` 에 제안된다.
#
#  ★ 왜 필요한가. 사람이 `more` 를 고르는데 지시문이 비어 있으면 재수집 프롬프트가
#    지난 바퀴와 글자 하나 다르지 않다. 같은 결과가 나오는 것이 당연하다.
#    실측에서 그랬다 — `more` 를 눌러도 부족한 칸이 줄지 않았다.
#    그래서 **무엇을 적어야 하는지까지** 화면이 알려 준다.
_NOTE_HINT = (
    ("출처가 겹침", "같은 출처를 두 번 쓰지 마라. 이미 쓴 것과 도메인이 다른 곳에서 "
                  "찾아 기존 항목 하나를 갈아 끼워라"),
    ("변동값", "환율·항공권가격은 조회한 날짜를 본문에 함께 적고, 값을 고시하는 곳"
             "(중앙은행·항공사·검색 결과 화면)을 출처로 써라"),
    ("이미지 주소가 죽어 있음", "이미지는 영문 파일명을 우선 쓰고 Commons 에서 실제로 "
                            "확인한 것만 써라. 확인 못 한 칸은 아예 건드리지 마라"),
    ("같은 근거를 복제함", "이미 있는 것과 다른 출처로 찾아라. 문장만 바꿔 넣지 마라"),
    ("국가 소개 — 근거가 모자람", "국가 소개는 칸마다 계약이 정한 건수가 필요하다. 한 번의 검색으로 "
                              "여러 건을 다 채우려 하지 말고 칸마다 따로 찾아라"),
    ("국가 소개를 아직 못 만듦", "국가 소개를 처음부터 다시 모아라. 칸 이름은 계약에 "
                             "적힌 것을 그대로 써라"),
    ("설명이 하한보다 짧음", "지적된 날의 블록을 하나도 빼지 말고 전부 다시 써라"),
    ("수집 실패", "그 도시를 처음부터 다시 모아라. 안 되면 다른 도시로 바꿔라"),
    ("글자가 깨짐", "깨진 글자가 있는 칸은 원문 사이트에서 다시 옮겨 적어라. "
                  "주소는 퍼센트 인코딩된 ASCII 로만 써라"),
)


def note_hint(causes) -> str:
    """가장 많은 원인에 맞는 지시문을 고른다. **결정론이다** — LLM 이 짓지 않는다."""
    for cause in causes or []:
        name = str(cause.get("원인") or "")
        for needle, hint in _NOTE_HINT:
            if needle in name:
                return hint
    return ""


def _recommend_a(state, shorts, causes) -> str:
    """권장을 **상황에서 계산한다.** 고정 문구로 두면 틀린 권장을 하게 된다.

    실측에서 그랬다. 화면은 `proceed — 인터넷에 없는 정보는 몇 바퀴를 더 돌아도
    없습니다` 를 고정으로 띄웠는데, 실제 원인은 이 킷이 주소를 못 여는 버그였다.
    정보는 인터넷에 **있었다.** 틀린 권장은 없느니만 못하다.
    """
    top = causes[0] if causes else {}
    name = str(top.get("원인") or "")
    #  ★ 처방 가지 줄이 가장 먼저다. 정해진 절차로 안 된 문제라 판단이 다르다.
    if name.startswith("처방 가지 시험지가 깨짐"):
        return ("proceed — 처방 가지 시험지가 깨져 그 문제는 판정을 못 했습니다. 그래프는 그대로 "
                "진행하고, STEP 6 에서 시험지를 고치십시오")
    if name.startswith("처방 가지가 못 고침"):
        if shorts:
            return ("more — 정해진 절차(처방 가지)로 못 고친 문제가 남았습니다. `more` 를 "
                    "고르면 재수집(LLM)이 note 대로 다시 찾고, 처방 한도도 새로 채워집니다")
        return ("proceed — 처방 가지가 정해진 절차로 못 고쳤고 검사기가 세는 부족은 없습니다. "
                "'고치려면' 칸을 보고, 바뀌지 않으면 보고서에 남기고 진행하십시오")
    if not shorts and not _failure_lines(state):
        return "proceed — 못 채운 칸이 없습니다"
    iteration = state.get("loop_a_iter") or 0
    limit = state.get("loop_a_limit") or 0
    #  ★ 수집 실패가 가장 먼저다. 부족이 아니라 파이프가 터진 것이라 판단이 다르다.
    if "수집 실패" in name:
        return ("more — 부족이 아니라 **그 도시를 아예 못 모았습니다.** 인계본에 없는 "
                "도시라 대체 자료도 없습니다. 한 바퀴 더 돌리거나, 다른 도시로 바꿔 "
                "다시 시작하는 편이 낫습니다")
    #  ★ 이 분기가 바퀴 소진보다 **먼저** 온다. 주소가 틀린 것은 "정보가 없는 것"이
    #    아니라 "고칠 수 있는 것"이라, 바퀴를 다 썼더라도 방향을 준 한 바퀴가 값어치가 있다.
    if name == "이미지 주소가 죽어 있음":
        return ("more — 부족의 대부분이 **이미지 주소 한 종류**입니다. 정보가 없어서가 "
                "아니라 주소가 틀려서입니다. `⑤ 답` 의 `note` 에 고칠 방향을 적어 "
                "`more` 를 고르면 한 바퀴에 붙는 경우가 많습니다"
                + ("  (바퀴는 이미 다 썼습니다 — 그래도 방향을 준 한 바퀴는 다릅니다)"
                   if limit and iteration >= limit else ""))
    if "변동값" in name:
        return ("proceed — 남은 것이 **환율·항공권가격**입니다. 값이 계속 바뀌어 "
                "인용할 자리를 찾기 어려운 종류라, 지시문 없이 더 돌리면 같은 결과입니다. "
                "굳이 한 바퀴를 쓴다면 `⑤ 답` 의 `note` 를 **반드시** 채우십시오"
                + ("" if limit and iteration >= limit else " (바퀴는 남아 있습니다)"))
    if "출처가 겹침" in name:
        return ("more — 정보가 없어서가 아니라 **출처가 겹쳐서**입니다. `note` 에 "
                "`다른 도메인에서 찾아 갈아 끼워라`를 적으면 한 바퀴에 붙는 경우가 많습니다"
                + ("  (바퀴는 다 썼지만 방향을 준 한 바퀴는 다릅니다)"
                   if limit and iteration >= limit else ""))
    if name.startswith("국가 소개"):
        if limit and iteration >= limit:
            return ("proceed — 남은 것이 **국가 소개**인데 바퀴를 다 썼습니다. "
                    "남은 칸은 최종 보고서에 그대로 남습니다")
        return ("more — 남은 것이 **국가 소개**입니다. `repair_country` 가 지적된 칸만 "
                "고치므로 한 바퀴가 짧습니다. `note` 를 채우면 확률이 크게 오릅니다")
    if limit and iteration >= limit:
        return "proceed — 정해진 바퀴를 다 썼습니다. 남은 칸은 최종 보고서에 그대로 남습니다"
    return "more — 아직 바퀴가 남았고, 남은 원인은 더 찾으면 채워지는 종류입니다"


def gate_a_payload(state) -> dict:
    shorts = _as_list(state.get("info_short_slots"))
    causes = (_detour_lines(state) + _orphan_lines(state) + _failure_lines(state)
              + classify(shorts, _CAUSE_A))
    hurt = {row.get("city") for row in _as_list(state.get("city_failures"))
            if isinstance(row, dict) and (row.get("why") or "").strip()}
    #  ★ `more` 가 **실제로 무엇을 부를지**를 그대로 적는다. 라우터가 고르는 기준
    #    (`edges.fan_out_repairs`)과 같은 규칙으로 계산한다 — 화면과 동작이 어긋나면
    #    사람이 "more 를 눌렀는데 국가는 안 돌더라"를 겪는다.
    named = {n for n in _as_list(state.get("selected_city_names"))
             if any(edges.belongs_to(line, str(n)) for line in shorts)}
    #  ★ `hurt`(실패 기록)를 그대로 합치지 않는다. `(국가 소개)` 처럼 도시가 아닌
    #    항목이 섞여 있는데, `fan_out_repairs` 는 `selected_city_names` 만 순회하므로
    #    화면이 부르겠다고 적은 곳을 라우터가 안 부르는 일이 생긴다.
    real = {str(n) for n in _as_list(state.get("selected_city_names"))}
    targets = sorted(named | (hurt & real))
    country_short = any("기능1" in str(line) for line in shorts)
    hint = note_hint(causes)
    return gate_payload(
        지금=(f"루프 A(정보량) · {state.get('info_verdict')} · "
            f"{state.get('loop_a_iter')}/{state.get('loop_a_limit')}바퀴 · "
            f"못 채운 칸 {len(shorts)}곳 · 같은 오류 반복 "
            f"{state.get('same_error_count')}/{state.get('same_error_limit')}"),
        shorts=shorts, rules=_CAUSE_A, state=state,
        권장=_recommend_a(state, shorts, causes),
        choices={
            "more": ("지적된 것만 다시 모읍니다"
                     + (f" · 도시: {', '.join(targets)}" if targets else "")
                     + (" · 국가 소개" if country_short else "")
                     + " — 지적이 없는 곳은 호출조차 하지 않습니다"),
            "proceed": "부족해도 페이지를 만듭니다 (못 채운 칸은 보고서에 남습니다)",
            "stop": "여기서 멈춥니다 (END)",
        },
        답={"action": "more | proceed | stop",
            "note": (hint or "(비워도 됩니다. 적으면 재수집 프롬프트에 "
                             "**검사기 지적보다 우선해서** 실립니다)")},
    )


def human_gate_a(state) -> dict:
    """★ STEP 5 — 여기서 그래프가 **멈춘다.** 사람이 답할 때까지 진행하지 않는다."""
    answer = interrupt(gate_a_payload(state))
    decision = normalize_gate(answer, ("more", "proceed", "stop"), "proceed")
    trail = [f"human_gate_a: {decision['action']}"]
    if decision["warning"]:
        trail.append("human_gate_a: " + decision["warning"])
    #  ★ `more` 는 사람이 "한 번 더"를 고른 것이다. 바깥 루프는 사람이 소유하므로
    #    처방 한도도 새로 채운다 — 재수집이 데이터를 바꾼 뒤 처방 가지가 다시 설 수 있게.
    again = decision["action"] == "more"
    if again:
        trail.append("human_gate_a: 처방 한도를 새로 채웁니다")
    return {
        "gate_a_answer": decision["action"],
        "gate_note": decision["note"],
        "detour_attempts": {} if again else _as_dict(state.get("detour_attempts")),
        "history": trail,
    }


# --------------------------------------------------------------------------- #
# 8. build_page — 결정론 · 모든 수집이 끝난 뒤 한 번만
# --------------------------------------------------------------------------- #


def build_page(state) -> dict:
    data = {
        "country": state.get("country"),
        "days": state.get("days"),
        "country_intro": _as_dict(state.get("country_intro")),
        "cities": _as_list(state.get("cities")),
    }
    contract.write_research(data)
    path = page.write(data)
    return {"html_path": path, "history": [f"build_page: {path}"]}


# --------------------------------------------------------------------------- #
# 9. check_page — 결정론 검사기 B
# --------------------------------------------------------------------------- #


def check_page(state) -> dict:
    """화면을 재서 판정을 상태에 쓴다. 처방 가지에서 돌아온 방문은 바퀴로 세지 않는다
    (`check_information` 과 같은 이유)."""
    result = _checker("check_page_contract").run(str(contract.ROOT))
    shorts = list(result.short)
    verdict = result.verdict
    back = state.get("detour_verdict") == "PASS"          # 처방 가지에서 합격하고 돌아왔다
    iteration = state.get("loop_b_iter", 0) + (0 if back else 1)
    return {
        "page_verdict": verdict,
        "page_short_slots": shorts,
        "loop_b_iter": iteration,
        "detour_verdict": "",
        "history": [f"check_page: {verdict} · 부족 {len(shorts)}곳 · {iteration}바퀴"
                    + (" (처방 가지에서 복귀 — 바퀴를 쓰지 않음)" if back else "")],
    }


# --------------------------------------------------------------------------- #
# 9b. diagnose_page — 결정론 진단 B
# --------------------------------------------------------------------------- #


def diagnose_page(state, config=None) -> dict:
    """진단 B — 검사기 B 가 판정을 쓴 뒤, **화면**에서 원인을 가린다.

    ★ 판정이 PASS 여도 돈다. 검사기는 사진이 **있는가**만 보고, 크기 · 틀은 보지 않는다.
    ★ **정성이 시작된 뒤에는 처방 가지를 타지 않는다.** 정성 3회는 파일 해시로 사슬을
      잇는데, 그 사이나 그 뒤에 처방 가지가 파일을 고치면 사슬이 끊겨 루프 C 가 멈춘다.
      증상은 남겨서 게이트에서 보여 준다. (게이트 B 에서 research · rebuild 를 고르면
      정성 회차가 0 으로 돌아가므로 그때부터 다시 처방 가지를 탈 수 있다.)
    """
    busy = (state.get("quality_pass") or 0) > 0             # 정성이 한 회차라도 돌았다
    kind, evidence, table = _diagnose(
        "B", state, hold="정성 회차 중 — 파일 해시 사슬을 지키려고 미룸" if busy else "")
    shorts = _as_list(state.get("page_short_slots"))
    _log_diagnosis(config, "diagnose_page", "B", state, shorts, _CAUSE_B, kind, table)
    return {
        "failure_kind": kind,
        "failure_evidence": evidence,
        "history": [_diagnosis_line("diagnose_page", kind, table, state)],
    }


# --------------------------------------------------------------------------- #
# 10. human_gate_b — 사람 · 외부 루프 B
# --------------------------------------------------------------------------- #


def _recommend_b(state, shorts, causes, finished) -> str:
    if finished:
        #  ★ 정성 3회를 돌았다고 끝난 것이 아니다. 판정기가 SHORT 면 done 은 SHORT 인 채로
        #    끝난다 — "확정합니다" 를 권하면 교육생이 실패를 성공으로 읽는다.
        if state.get("quality_verdict") == "PASS":
            return "done — 정성 3회를 채웠습니다. 이대로 확정합니다"
        return ("rebuild — 정성 3회 기록이 아직 SHORT 입니다(② 왜). `note` 에 그 위반을 고치라고 "
                "적어 rebuild 하면 고친 뒤 정성 3회를 처음부터 다시 돕니다. done 을 고르면 "
                "verify_all 이 SHORT(exit 2)인 채로 끝납니다")
    top = str((causes[0] if causes else {}).get("원인") or "")
    if top.startswith("처방 가지 시험지가 깨짐"):
        return ("done — 처방 가지 시험지가 깨져 그 문제는 판정을 못 했습니다. 그래프는 그대로 "
                "진행하고, STEP 6 에서 시험지를 고치십시오")
    if top.startswith("처방 가지를 미룸"):
        return ("done — 정성 회차 중이라 처방 가지를 미뤘습니다. done 이면 정성을 이어 가고, "
                "research · rebuild 를 고르면 정성이 0 으로 돌아가며 처방 가지가 다시 섭니다")
    if top.startswith("처방 가지가 못 고침"):
        return ("done — 처방 가지가 정해진 절차로 못 고쳤습니다. '고치려면' 칸을 따르십시오 "
                "(데이터로 고칠 수 있으면 rebuild · research, 화면 코드 문제면 보고서에 남기고 done)")
    #  ★ "화면 칸이 모자람" 을 **"화면" 검사보다 먼저** 본다. 이름에 `화면` 이 들어 있어서
    #    뒤에 두면 rebuild("데이터가 아니라 화면 문제")로 떨어진다 — 같은 화면의 ② 는
    #    "대개 수집이 덜 된 것"이라고 말하는데 ③ 이 정반대를 권하게 된다.
    if "화면 칸이 모자람" in top:
        if state.get("info_verdict") == "SHORT":
            #  루프 A 가 못 채운 채로 넘어온 칸이 화면에도 빈 것이다. 게이트 A 에서 사람이
            #  이미 "부족해도 페이지를 만든다"를 골랐다 — 같은 질문을 다시 권하지 않는다.
            return ("done — 루프 A 에서 못 채우고 넘긴 칸이 화면에도 비어 있는 것입니다. "
                    "보고서에 남습니다 (다시 모아 보려면 research)")
        return "research — 화면이 아니라 **수집이 덜 된** 것입니다"
    if "화면" in top or "닫혀" in top or "클릭" in top or "이름표" in top:
        return "rebuild — 데이터가 아니라 **화면** 문제입니다. 지시문을 적어 rebuild 하십시오"
    return "done — 정성 점검 3회를 시작합니다 (못 채운 칸은 보고서에 남습니다)"


def gate_b_payload(state) -> dict:
    """루프 B 뒤와 정성 3회 뒤에 **두 번 선다.** 무엇을 묻는지는 `정성 회차` 로 구분한다."""
    done_n = state.get("quality_pass", 0)
    need = state.get("quality_passes_required", 3)
    finished = done_n >= need
    #  두 번째로 설 때는 정성 판정 결과를 보여 준다 — 그때의 관심사는 페이지가 아니다.
    shorts = (_as_list(state.get("quality_short_slots")) if finished
              else _as_list(state.get("page_short_slots")))
    rules = _CAUSE_C if finished else _CAUSE_B
    #  두 번째로 설 때(정성 3회 뒤)는 처방 가지 증상을 싣지 않는다 — 그때의 관심사는 정성이다.
    causes = (([] if finished else _detour_lines(state)) + classify(shorts, rules))
    verdict = state.get("quality_verdict") if finished else state.get("page_verdict")
    return gate_payload(
        detour=not finished,
        지금=(f"{'정성 3회 완료' if finished else '루프 B(페이지)'} · {verdict} · "
            f"{state.get('loop_b_iter')}/{state.get('loop_b_limit')}바퀴 · "
            f"정성 {done_n}/{need}회 · 못 채운 칸 {len(shorts)}곳\n"
            f"결과물: {state.get('html_path')}  ← 브라우저로 열어 보고 정하십시오"),
        shorts=shorts, rules=rules, state=state,
        권장=_recommend_b(state, shorts, causes, finished),
        choices={
            "research": "정보가 모자랍니다 → 지적된 도시만 다시 모읍니다 "
                        "(정성 회차가 0으로 되돌아갑니다)",
            "rebuild": "화면이 모자랍니다 → **`note` 에 적은 지시대로** 결과물을 고칩니다 "
                       "(rebuilder. 정성 회차가 0으로 되돌아갑니다)",
            "done": ("정성 점검 3회를 시작합니다  ← 대개 이쪽" if not finished
                     else "이대로 확정하고 끝냅니다 (END)  ← 대개 이쪽"),
        },
        답={"action": "research | rebuild | done",
            "note": "(rebuild 를 고르면 **반드시 적으십시오.** 이 문장이 수정 지시가 "
                    "됩니다. 예: 도시 단추를 누르면 그 도시 칸만 열리게 하고 나머지는 "
                    "닫아라 / 계약을 낮추는 요구는 거부됩니다)"},
    )


def human_gate_b(state) -> dict:
    """★ STEP 5 — 두 번째 정지 지점. 게이트 B 는 **두 번 선다.**"""
    answer = interrupt(gate_b_payload(state))
    decision = normalize_gate(answer, ("research", "rebuild", "done"), "done")
    trail = [f"human_gate_b: {decision['action']}"]
    if decision["warning"]:
        trail.append("human_gate_b: " + decision["warning"])

    if decision["action"] in ("research", "rebuild"):
        # ★ 되돌아가면 결과물이 다시 만들어진다. 정성 회차가 디스크에 남긴 수정은
        #   그때 사라지고 회차 기록의 해시 사슬도 끊긴다. 그래서 회차를 0 으로
        #   되돌린다 — 카운터는 **덮어쓰기**다.
        trail.append("human_gate_b: 되돌아가므로 정성 회차를 0 으로 되돌립니다")
        #  ★ **안쪽 바퀴 수도 되돌린다.** 아무도 이것을 0 으로 돌리지 않으면
        #    `check_information` 이 방문할 때마다 `loop_a_iter` 를 올리기만 해서,
        #    루프 A 예산을 이미 쓴 뒤에 게이트 B 에서 `research` 를 골라도
        #    `route_after_info` 가 곧바로 `gate` 로 보낸다 — 재수집이 **한 번도**
        #    돌지 않는다. 화면은 "지적된 도시만 다시 모읍니다"라고 약속한 뒤였다.
        #
        #    되돌리는 것이 안전한 이유: 바깥 루프는 **사람이 소유한다.** 여기까지
        #    온 것은 사람이 한 번 더 돌리라고 명시적으로 고른 결과다.
        reset = {"loop_a_iter": 0} if decision["action"] == "research" else {"loop_b_iter": 0}
        trail.append(f"human_gate_b: 안쪽 바퀴를 0 으로 되돌립니다 ({list(reset)[0]})")
        trail.append("human_gate_b: 처방 한도를 새로 채웁니다")
        #  ★ 처방 한도도 새로 채운다. 사람이 "한 번 더"를 골랐으므로 (게이트 A 의 more 와 같다).
        return {
            "gate_b_answer": decision["action"],
            "gate_note": decision["note"],
            "quality_pass": 0,
            "quality_verdict": "UNKNOWN",
            "same_error_count": 0,
            "last_error_hash": "",
            "detour_attempts": {},
            "failure_kind": "",
            "detour_verdict": "",
            **reset,
            "history": trail,
        }

    return {
        "gate_b_answer": decision["action"],
        "gate_note": decision["note"],
        "history": trail,
    }


# --------------------------------------------------------------------------- #
# 10b. rebuilder — LLM + 결정론 · **사람의 지시문을 실제로 소비하는 자리**
# --------------------------------------------------------------------------- #


def rebuilder(state) -> dict:
    """게이트 B 에서 사람이 적은 `note` 대로 결과물을 고친다.

    ★ **HTML 을 직접 고치지 않는다.** `output/research_data.json` 을 고치고
      화면을 다시 만든다. HTML 만 손대면 `build_page` 가 다시 도는 순간 날아간다.

    ★ 그리고 고친 데이터를 **상태에도 돌려준다.** `build_page` 는 파일이 아니라
      **상태**에서 페이지를 만들기 때문이다. 이 반환이 없으면 다음 `build_page` 가
      옛 상태로 덮어써서 rebuild 가 통째로 사라진다.

    ★ `quality_pass` 와 같은 규격이다 — 판정은 LLM, 적용은 결정론(`apply_fixes`),
      fix 하나마다 `verify_all --skip-quality` 로 되돌아감을 확인한다.
      **계약을 낮추는 지시는 거부된다.**
    """
    note = str(state.get("gate_note") or "")
    outcome = quality.rebuild_from_note(note)
    applied, skipped = outcome["applied"], outcome["skipped"]

    trail = [f"rebuilder: 지시 '{outcome['asked'][:40]}' · "
             f"적용 {len(applied)}건 · 못 함 {len(skipped)}건"]
    for fix in skipped[:3]:
        trail.append(f"  ↳ 적용 못 함: {fix.get('what') or fix.get('path')} · {fix.get('why')}")
    if outcome["why"]:
        trail.append(f"  ↳ 따르지 않음: {outcome['why'][:160]}")

    #  고친 데이터를 상태로 되올린다. 이것이 rebuild 를 휘발시키지 않는 유일한 길이다.
    #  적용이 0건이면 파일이 안 바뀌었으므로 상태의 값을 그대로 되돌려준다.
    data = contract.read_research() if applied else {}
    return {
        "cities": _as_list(data.get("cities")) or _as_list(state.get("cities")),
        "country_intro": (_as_dict(data.get("country_intro"))
                          or _as_dict(state.get("country_intro"))),
        "history": trail,
    }


# --------------------------------------------------------------------------- #
# 11. quality_pass — LLM + 결정론 · ★ 루프 C 한 회차 (순차 3회)
# --------------------------------------------------------------------------- #


def quality_pass(state) -> dict:
    """정성 점검 한 회차. **절대 병렬로 돌리지 않는다.**

    회차 N 의 `snapshot_before` 는 회차 N-1 의 `snapshot_after` 와 같아야 하고,
    판정기가 그 사슬을 확인한다. `build_page` 가 병렬 불가인 이유(입력이 다 모여야
    해서)와는 **다른 이유**다 — 여기서는 **앞 회차의 출력이 자기 입력**이다.

    판정을 못 하면 조용히 통과시키지 않는다. 기록을 남기고 카운터를 올리지 않아
    `check_quality` 가 `ERROR` 를 내고 그래프가 멈춘다.
    """
    number = state.get("quality_pass", 0) + 1
    try:
        outcome = quality.run_one_pass(number)
    except quality.QualityBlocked as exc:
        quality.write_blocked(str(exc))
        return {"history": [f"quality_pass {number}: 판정 불가 — {exc}"]}

    trail = [f"quality_pass {number}/{state.get('quality_passes_required', 3)}: "
             f"위반 {len(outcome['violations'])}건 · 수정 {len(outcome['applied'])}건 · "
             f"되돌아감 확인 exit {outcome['exit_code']} · {outcome['record']}"]
    #  못 고친 것을 숨기지 않는다. 판정기는 "위반이라 적고 고치지 않았습니다"만
    #  말해 주므로, 왜 못 고쳤는지는 여기서 남겨야 사람이 판단할 수 있다.
    for fix in outcome["skipped"][:3]:
        trail.append(f"  ↳ 적용 못 함: {fix.get('rule')} · {fix.get('why')}")
    if outcome["unfixed"]:
        trail.append(f"  ↳ 고치지 못한 위반: {', '.join(outcome['unfixed'])}")
    #  ★ **고친 데이터를 상태로 되올린다.** `quality.apply_fixes` 는 디스크의
    #    `output/research_data.json` 만 고치는데, `build_page` 는 파일이 아니라
    #    **상태**에서 페이지를 만든다. 이 반환이 없으면 `check_quality → build` 로
    #    되돌아가는 순간 정성 수정이 통째로 사라지고, 회차 해시 사슬도 끊어져
    #    루프 C 가 영원히 SHORT 를 낸다. `rebuilder` 와 같은 이유·같은 고칠 법이다.
    data = contract.read_research()
    return {
        "quality_pass": number,
        "cities": _as_list(data.get("cities")) or _as_list(state.get("cities")),
        "country_intro": (_as_dict(data.get("country_intro"))
                          or _as_dict(state.get("country_intro"))),
        "history": trail,
    }


# --------------------------------------------------------------------------- #
# 12. check_quality — 결정론 검사기 C · **품질이 아니라 절차를 본다**
# --------------------------------------------------------------------------- #


def check_quality(state) -> dict:
    """루프 C 판정을 상태에 쓴다. 검사기 A·B 와 같은 이유로 노드가 된다.

    다른 점은 **무엇으로 닫히는가**다. 루프 A·B 는 `verdict` 가 PASS 가 되면 닫히고,
    루프 C 는 회차 카운터가 3에 닿으면 닫힌다. 그래서 라우터도 다르게 생겼다.
    """
    blocked = quality.blocked_reason()
    if blocked:
        return {
            "quality_verdict": "ERROR",
            "quality_short_slots": [blocked],
            "history": [f"check_quality: ERROR · {blocked}"],
        }
    result = _checker("check_quality_passes").run(str(contract.ROOT))
    shorts = list(result.short)
    return {
        "quality_verdict": result.verdict,
        "quality_short_slots": shorts,
        "history": [f"check_quality: {result.verdict} · 미이행 {len(shorts)}곳 · "
                    f"{state.get('quality_pass', 0)}/"
                    f"{state.get('quality_passes_required', 3)}회"],
    }


# --------------------------------------------------------------------------- #
# 사람의 자유 입력을 라우팅 가능한 값으로 정규화
# --------------------------------------------------------------------------- #


def _split_answer(text: str, allowed: tuple) -> tuple:
    """`"more 이미지를 다시 확인해라"` 를 (`more`, `이미지를 다시 확인해라`) 로 나눈다.

    ★ 예전에는 문자열 전체를 `note` 로 그대로 넣었다. 그래서 사람이 `more` 만 쳐도
      `note` 가 `"more"` 가 되어, 재수집 프롬프트에 **"검사기 지적보다 우선한다"**
      는 딱지를 달고 `more` 라는 낱말이 지시로 주입됐다.
    """
    body = (text or "").strip()
    for value in allowed:
        low = body.lower()
        if low == value:
            return value, ""
        if low.startswith(value) and (len(body) == len(value) or body[len(value)] in " \t:,-"):
            return value, body[len(value):].lstrip(" \t:,-").strip()
    return "", body


#: 게이트들이 쓰는 라우팅 낱말 **전부**. 어느 게이트의 것이든 지시문이 아니다.
_ROUTING_WORDS = ("more", "proceed", "stop", "research", "rebuild", "done")


def _stray_routing_word(note: str, allowed: tuple) -> str:
    """`note` 가 **다른 게이트의 낱말 하나**뿐인가. 맞으면 그 낱말을 돌려준다.

    게이트 B 에서 `stop` 을 치는 일이 실제로 있다 — 게이트 A 에서 본 낱말이기
    때문이다. 그 낱말은 이 게이트의 허용값이 아니라서 `note` 로 떨어지는데, 아래의
    "방향을 적었으면 한 바퀴 더" 규칙이 그것을 **재수집**으로 읽었다. 사람은
    멈추라고 했는데 그래프는 몇 분짜리 한 바퀴를 더 돌고, `stop` 이라는 낱말이
    *"검사기 지적보다 우선하는 지시"* 딱지를 달고 재수집 프롬프트에 실렸다.
    """
    word = (note or "").strip().strip(".,!?").lower()
    if word and word in _ROUTING_WORDS and word not in allowed:
        return word
    return ""


def _decide_gate(action: str, note: str, allowed: tuple, fallback: str) -> dict:
    """**판정 규칙은 여기 한 곳에만 둔다.**

    예전에는 문자열 갈래와 dict 갈래가 각자 판정했고, 문자열 갈래에만 아래 세 번째
    규칙이 있었다. 그래서 Studio 의 resume 폼(dict 를 보낸다)으로 `action` 을 비우고
    `note` 에만 "…재수집하라" 를 적으면 게이트 B 가 조용히 `done`(확정 종료)으로
    갔다 — 같은 뜻을 문자열로 치면 재수집으로 갔는데. **입력 경로에 따라 정반대**였다.
    """
    if action:
        #  ★ 라우팅 낱말은 `note` 에서 **떼어 낸다.** 붙여 두면 `more` 라는 말이
        #    "검사기 지적보다 우선하는 지시"로 재수집 프롬프트에 실린다.
        return {"action": action, "note": note, "warning": ""}

    stray = _stray_routing_word(note, allowed)
    if stray:
        #  ★ 다른 게이트의 낱말이다. 이 게이트에서는 뜻이 없으므로 **지시문으로 읽지
        #    않는다.** 뜻을 넘겨짚어 비싼 한 바퀴를 더 돌리는 대신 기본값으로 가고,
        #    무슨 일이 있었는지 회차 기록에 남겨 사람이 다시 고를 수 있게 한다.
        #    `note` 를 비우는 것이 핵심이다 — 남겨 두면 그 낱말이 프롬프트에 실린다.
        return {"action": fallback, "note": "",
                "warning": ("'" + stray + "' 는 이 게이트의 답이 아닙니다"
                            " (고를 수 있는 것: " + " · ".join(allowed) + ")."
                            " 기본값 '" + fallback + "' 로 진행했습니다")}

    #  ★ 허용값 없이 문장만 온 경우. 예전에는 `fallback`(=proceed) 으로 떨어뜨리고
    #    문장은 살려 뒀는데, 그러면 **사람이 고칠 방향을 적었는데 페이지를 만들어**
    #    버린다. 방향을 적었다는 것은 더 돌리겠다는 뜻이므로 첫 허용값으로 읽는다.
    if note and allowed:
        return {"action": allowed[0], "note": note, "warning": ""}
    return {"action": fallback, "note": note, "warning": ""}


def normalize_gate(answer, allowed: tuple, fallback: str) -> dict:
    """**라우팅 키와 자유 문장을 분리한다.**

    자유 문장만 받으면 라우팅이 문장 해석에 좌우된다. 그래서 `action` 은 허용값
    안에서만 받고, 하고 싶은 말은 `note` 로 따로 받아 다음 프롬프트에 붙인다.
    Studio 가 단순 텍스트 폼을 그리는 경우(문자열이 그대로 오는 경우)까지 흡수한다.

    이 함수가 하는 일은 **어떤 모양으로 왔든 (action, note) 두 조각으로 만드는 것**
    뿐이다. 판정은 전부 `_decide_gate` 가 한다. 돌려주는 것은 `action` · `note` ·
    `warning`(사람에게 보일 한 줄, 없으면 빈 문자열).
    """
    if isinstance(answer, str):
        action, note = _split_answer(answer, allowed)
    elif isinstance(answer, dict):
        #  ★ `or ""` 가 필요하다. JSON 의 null 은 `answer.get("action", "")` 을
        #    통과해 `str(None)` → `"None"` 이 되고, 그 글자가 지시문으로 실린다.
        raw = str(answer.get("action") or "").strip()
        action, spill = _split_answer(raw, allowed)
        note = str(answer.get("note") or "").strip() or spill
    else:
        return {"action": fallback, "note": "", "warning": ""}
    return _decide_gate(action, note, allowed, fallback)
