# -*- coding: utf-8 -*-
"""그래프 회귀 테스트 — **검사기가 못 보는 것을 본다.** 킷 소유.

`check_graph_shape.py` 는 **구조**만 본다 — 도달 가능한가, reducer 가 붙었나,
`ALLOWED` 와 배선이 맞나. 정적 분석이라 **돌렸을 때 무슨 일이 일어나는지**는 못 본다.

    예) `route_after_gate_b` 에서 정성 회차 분기를 지우면 `quality_pass` 가 한 번도
        실행되지 않는다. 배선은 그대로라 `check_graph_shape.py` 는 **전부 통과**한다.
        이 파일이 그것을 잡는다.

세 도구의 분업

    check_graph_shape.py        구조가 성립하는가      정적
    selftest/run_selftest.py    검사기가 살아 있는가    채점표를 채점
    selftest/run_graph_regression.py  돌렸을 때 맞게 도는가  동적  ← 이 파일

이 파일이 지키는 여섯 가지

    ① 배선이 실제로 타는가        게이트에 멈추는가 · 되돌이 간선이 실행되는가
    ② fan-out 이 좁게 도는가      다친 것만 부르는가 · 재수집이 멱등한가
    ③ 화면이 거짓말을 안 하는가   게이트가 적은 대상과 라우터가 부르는 대상이 같은가
    ④ 잡은 결함이 안 돌아오는가   과거에 실측으로 확인된 defect 마다 재현 테스트
    ⑤ 처방 가지가 제자리에서만 나는가  inject 없으면 가지 0회 · 재현하면 진단 → fix → test →
                                  검사기로 복귀 · 한도면 사람에게 · 구조 검사 11번이 살아 있는가
    ⑥ 재수집 뒤 검사기가 죽지 않는가  patch 가 칸의 형을 못 바꾼다 · 바뀐 사진만 다시 연다 ·
                                  실패 기록 보고서 ③-2 가 재수집이 반복해서 맡은 원인을 센다

**`claude -p` 를 한 번도 부르지 않는다** (replay 고정). 약 10~15초면 끝나고 (처방 가지 재현 실행과
T15 의 킷 복사본 변이 9종이 대부분이다), `verify_all.py` 는 이 파일을 부르지 않는다 —
실습 경로와 분리돼 있다. 교육생이 STEP 6 에서 처방 가지를 더하면 T14 가 그 처방 가지도 돌려 보므로
검사 수가 는다 (킷 기본 240개 · 처방 가지 하나에 +11).

사용법
  python scripts/selftest/run_graph_regression.py       0 통과 / 1 실패
"""
import io, json, os, sys, copy
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
os.environ["GRAPH_MODE"] = "replay"
os.environ["GRAPH_TRACE_CLAUDE"] = "0"
#  실패 기록(evidence/failures/)도 교육생 것을 건드리지 않는다. 임시 폴더에 쓰고 끝나면 지운다.
import tempfile, shutil
_FAIL_DIR = Path(tempfile.mkdtemp(prefix="regress_failures_"))
os.environ["GRAPH_FAILURE_LOG_DIR"] = str(_FAIL_DIR)

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command, Send
from travel_graph import contract
from travel_graph.build import compile_graph
from travel_graph import nodes, edges
import inspect

#  ★ **교육생의 `output/` 을 건드리지 않는다.** T1 이 그래프를 실제로 돌리므로
#    `research_data.json` 과 `travel_site.html` 이 테스트 자료로 덮인다.
#
#    경로를 다른 곳으로 돌리는 방법은 **쓸 수 없다.** 검사기(`check_*.py`)는 별도
#    스크립트라 자기 루트에서 `output/` 을 직접 읽는다 — 그래프만 딴 데 쓰게 하면
#    검사기가 옛 파일을 보고 엉뚱한 판정을 낸다. 그래서 **원본을 옆에 치워 두고,
#    끝나면 그대로 되돌려 놓는다.**
_KEEP = {}
for _p in (contract.RESEARCH_OUT, contract.HTML_OUT):
    if _p.exists():
        _KEEP[_p] = _p.read_bytes()


def _restore():
    """원본을 되돌린다. 테스트가 만든 파일은 원본이 없었으면 지운다."""
    for _p in (contract.RESEARCH_OUT, contract.HTML_OUT):
        if _p in _KEEP:
            _p.write_bytes(_KEEP[_p])
        elif _p.exists():
            _p.unlink()
    shutil.rmtree(_FAIL_DIR, ignore_errors=True)


import atexit
atexit.register(_restore)

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"  [{'OK ' if ok else '실패'}] {name}" + (f"\n         {detail}" if detail else ""))


def run_to_gate(graph, config, payload):
    """다음 interrupt 까지 돌리고 (멈춘 노드, payload, 상태) 를 준다."""
    seen = []
    for chunk in graph.stream(payload, config=config, stream_mode="updates"):
        for node, upd in (chunk or {}).items():
            if node == "__interrupt__":
                return seen, upd[0].value, graph.get_state(config).values
            seen.append(node)
    return seen, None, graph.get_state(config).values


print("=" * 74)
print(" T1  replay 한 판 — 루프 A 가 돌고 게이트 A 에서 멈추는가")
print("=" * 74)
graph = compile_graph(InMemorySaver())
cfg = {"configurable": {"thread_id": "t1"}, "recursion_limit": 80}
seen, gate_a, state = run_to_gate(graph, cfg, {})
print("  방문:", " → ".join(seen))
check("게이트 A 에서 멈춘다", gate_a is not None)
check("repair_city 가 돌았다 (1회차 부족 → 재수집)", "repair_city" in seen)
check("루프 A 가 PASS 로 닫혔다", state.get("info_verdict") == "PASS",
      f"verdict={state.get('info_verdict')} 부족={len(state.get('info_short_slots') or [])}곳")

print()
print("=" * 74)
print(" T2  ★ 조건부 fan-out — 다친 도시만 부르는가")
print("=" * 74)
st = {"selected_city_names": ["하노이", "다낭", "호이안"],
      "info_short_slots": ["다낭/한강다리 이미지: 목표 살아 있는 이미지 1 / 실제 부족",
                           "기능1 매력: 목표 3 / 실제 2"],
      "city_failures": [], "cities": [{"name": n} for n in ("하노이", "다낭", "호이안")]}
st["country_intro"] = {"매력": {"items": [{"text": "a"}, {"text": "b"}]}}
sends = edges.fan_out_repairs(st)
cities = [x.arg["city"] for x in sends if x.node == "repair_city"]
countries = [x for x in sends if x.node == "repair_country"]
check("다낭만 Send 된다 (하노이·호이안은 호출조차 안 됨)", cities == ["다낭"], f"보낸 곳={cities}")
check("그 도시 몫의 지적만 실린다",
      [x for x in sends if x.node == "repair_city"][0].arg["shorts"]
      == [st["info_short_slots"][0]])
check("도시 payload 에 국가 지적(기능1)이 섞이지 않는다",
      all("기능1" not in line
          for x in sends if x.node == "repair_city"
          for line in x.arg["shorts"]))
check("★ 국가 소개도 같은 fan-out 으로 갈라진다", len(countries) == 1,
      f"repair_country Send {len(countries)}개")
check("국가 payload 에는 기능1 지적만 실린다",
      countries[0].arg["shorts"] == ["기능1 매력: 목표 3 / 실제 2"])
check("국가 payload 가 지난 회차 결과를 함께 싣는다",
      countries[0].arg["country_intro"] == st["country_intro"])

st_nc = dict(st, info_short_slots=["다낭/한강다리 이미지: 목표 살아 있는 이미지 1 / 실제 부족"])
check("기능1 지적이 없으면 국가는 Send 되지 않는다",
      all(x.node != "repair_country" for x in edges.fan_out_repairs(st_nc)))

st_only = dict(st, info_short_slots=["기능1 환율: 목표 1 / 실제 0"])
only = edges.fan_out_repairs(st_only)
check("국가만 부족하면 국가 하나만 Send 된다",
      [x.node for x in only] == ["repair_country"], f"보낸 곳={[x.node for x in only]}")

st2 = dict(st, city_failures=[{"city": "호이안", "why": "응답이 잘렸습니다"}])
check("수집 실패 도시도 재수집 대상이 된다",
      sorted(x.arg["city"] for x in edges.fan_out_repairs(st2)
             if x.node == "repair_city") == ["다낭", "호이안"])

st3 = dict(st, info_short_slots=[], city_failures=[])
check("지적이 없으면 아무도 안 부른다", edges.fan_out_repairs(st3) == [])
check("그때 라우터는 게이트로 보낸다",
      edges.route_after_info(dict(st3, info_verdict="SHORT", loop_a_iter=1,
                                  loop_a_limit=3, same_error_count=0,
                                  same_error_limit=2)) == "gate")

print()
print("=" * 74)
print(" T3  reducer 멱등 — 재수집해도 도시가 늘지 않는가")
print("=" * 74)
cities = state.get("cities") or []
names = [c.get("name") for c in cities]
_WANT_CITIES = (contract.counts().get("cities") or {}).get("city_count") or 3
check(f"도시가 {_WANT_CITIES}개 그대로다 (operator.add 였다면 {_WANT_CITIES * 2}개)", len(cities) == _WANT_CITIES, f"{names}")
check("이름이 중복되지 않는다", len(names) == len(set(names)))

print()
print("=" * 74)
print(" T4  ★ 실패 노출 — 인계본에 없는 도시를 골랐을 때")
print("=" * 74)
from travel_graph import research as R
city, note, fail = R.collect_one_city("후에", {"country": "베트남", "days": 5})
check("빈 껍데기를 정상인 척 돌려주지 않는다", bool(fail), f"실패사유={fail[:60]}")
fake = {"city_failures": [{"city": "후에", "why": fail}], "info_short_slots": [],
        "info_verdict": "SHORT", "loop_a_iter": 3, "loop_a_limit": 3,
        "same_error_count": 0, "same_error_limit": 2, "selected_city_names": ["후에"]}
pay = nodes.gate_a_payload(fake)
wh = json.dumps(pay["② 왜"], ensure_ascii=False)
check("게이트 ② 왜 에 '수집 실패' 로 뜬다", "수집 실패" in wh)
check("권장이 '부족'이 아니라 '못 모았다'로 바뀐다", "못 모았습니다" in pay["③ 권장"],
      pay["③ 권장"][:70])

print()
print("=" * 74)
print(" T5  게이트 3곳이 같은 5키 모양인가")
print("=" * 74)
KEYS = ["① 지금", "② 왜", "③ 권장", "④ 고르기", "⑤ 답"]
a = nodes.gate_a_payload(state)
b = nodes.gate_b_payload(dict(state, quality_pass=0, page_verdict="SHORT",
                              page_short_slots=["기능2 우측 툴바 (구역 안 aside): 목표 1 / 실제 0",
                                                "툴바 초기 닫힘: 목표 닫힘 / 실제 열림"],
                              html_path="output/travel_site.html"))
c = nodes.gate_b_payload(dict(state, quality_pass=3, quality_verdict="SHORT",
                              quality_short_slots=["마지막 회차 = 지금 파일: 목표 같음 / 실제 다름"],
                              html_path="output/travel_site.html"))
for label, p in (("A", a), ("B", b), ("C", c)):
    check(f"게이트 {label} 키 5개 · 순서 동일", list(p.keys()) == KEYS, str(list(p.keys())))
check("게이트 A 에 원본 목록이 없다 (요약만)", "못 채운 칸" not in a)
check("게이트 B 원인이 분류된다", b["② 왜"] != ["없음"] and "원인" in b["② 왜"][0],
      json.dumps(b["② 왜"][0], ensure_ascii=False)[:90])
check("게이트 C 원인이 분류된다", c["② 왜"] != ["없음"] and "원인" in c["② 왜"][0],
      json.dumps(c["② 왜"][0], ensure_ascii=False)[:90])
check("게이트 B 에 rebuild 선택지가 있고 지시문을 요구한다",
      "rebuild" in b["④ 고르기"] and "note" in b["⑤ 답"])
check("게이트 B 두 번째는 정성 결과를 보여 준다", "정성 3회 완료" in c["① 지금"])

print()
print("=" * 74)
print(" T6  국가 소개 부족을 게이트가 어떻게 안내하는가")
print("=" * 74)
_base = {"info_short_slots": ["기능1 매력: 목표 3 / 실제 2",
                              "기능1 역사 · 서로 다른 출처: 목표 2 / 실제 1"],
         "info_verdict": "SHORT", "loop_a_iter": 1, "loop_a_limit": 3,
         "same_error_count": 0, "same_error_limit": 2, "city_failures": []}
p = nodes.gate_a_payload(_base)
_why = json.dumps(p["② 왜"], ensure_ascii=False)
check("② 왜 가 국가 소개로 묶어 보여 준다", "국가 소개" in _why, _why[:90])
check("② 왜 가 더 이상 '재수집 대상이 아님' 이라고 하지 않는다",
      "재수집 대상이 아님" not in _why)
check("고치는 방법에 repair_country 가 안내된다", "repair_country" in _why)
check("바퀴가 남았으면 권장이 more 다", p["③ 권장"].startswith("more"), p["③ 권장"][:70])

p_done = nodes.gate_a_payload(dict(_base, loop_a_iter=3))
check("바퀴를 다 썼으면 권장이 proceed 로 바뀐다",
      p_done["③ 권장"].startswith("proceed"), p_done["③ 권장"][:70])

#  ★ 국가 칸이라도 **이미지 문제는 이미지로** 분류돼야 한다 —
#    기능1 규칙을 이미지 규칙보다 앞에 두면 이 사실이 화면에서 사라진다.
p_img = nodes.gate_a_payload(dict(
    _base, info_short_slots=["기능1 국기이미지: 목표 살아 있는 이미지 1 / 실제 부족"]))
check("국가 이미지 부족은 '이미지 주소가 죽어 있음' 으로 분류된다",
      "이미지 주소가 죽어 있음" in json.dumps(p_img["② 왜"], ensure_ascii=False),
      json.dumps(p_img["② 왜"][0], ensure_ascii=False)[:90])

print()
print("=" * 74)
print(" T7'  게이트 A 의 more — **라우터 단위로** 확인 (부족이 남아 있을 때)")
print("=" * 74)
hurt = {"gate_a_answer": "more",
        "selected_city_names": ["하노이", "다낭", "호이안"],
        "info_short_slots": ["다낭/한강다리 이미지: 목표 살아 있는 이미지 1 / 실제 부족"],
        "city_failures": [], "cities": [{"name": n} for n in ("하노이", "다낭", "호이안")]}
out = edges.route_after_gate_a(hurt)
check("more + 부족 있음 → Send 목록을 돌려준다",
      isinstance(out, list) and out and isinstance(out[0], Send),
      f"{[s.arg['city'] for s in out] if isinstance(out, list) else out}")
check("다친 도시만 간다", [s.arg["city"] for s in out] == ["다낭"])
check("사람의 지시문이 payload 에 실린다",
      edges.route_after_gate_a(dict(hurt, gate_note="영문 파일명으로"))[0].arg["gate_note"]
      == "영문 파일명으로")

clean = dict(hurt, info_short_slots=[])
check("more + 부족 없음 → build 로 간다 (헛바퀴를 돌지 않는다)",
      edges.route_after_gate_a(clean) == "build")
check("stop 은 stop 으로", edges.route_after_gate_a(dict(hurt, gate_a_answer="stop")) == "stop")
check("proceed 는 build 로", edges.route_after_gate_a(dict(hurt, gate_a_answer="proceed")) == "build")

print()
print("=" * 74)
print(" T7''  자유 문장이 경로를 바꾸지 못하는가 (검사 5 의 실제 동작)")
print("=" * 74)
trap = dict(clean, gate_a_answer="proceed", gate_note="더 모으지 말고 그냥 진행해")
check("'더' 가 들어간 문장에도 재수집으로 새지 않는다",
      edges.route_after_gate_a(trap) == "build")
trap2 = dict(clean, gate_a_answer="proceed", gate_note="멈춰야 할 것 같기도 하고")
check("'멈' 이 들어가도 stop 으로 새지 않는다", edges.route_after_gate_a(trap2) == "build")

print()
print("=" * 74)
print(" T8'  게이트 A(proceed) → 페이지 → 게이트 B 가 서는가")
print("=" * 74)
g = compile_graph(InMemorySaver())
cfg = {"configurable": {"thread_id": "t8b"}, "recursion_limit": 80}
seen1, gate_a, st1 = run_to_gate(g, cfg, {})
check("첫 정지는 게이트 A 다", gate_a is not None and "루프 A" in str(gate_a["① 지금"]),
      str(gate_a["① 지금"])[:70] if gate_a else "")

seen2, gate_b, st2 = run_to_gate(g, cfg, Command(resume={"action": "proceed", "note": ""}))
print("  방문:", " → ".join(seen2))
check("둘째 정지는 게이트 B 다",
      gate_b is not None and "루프 B" in str(gate_b["① 지금"]),
      str(gate_b["① 지금"]).split("\n")[0][:70] if gate_b else "(안 섰음)")
check("페이지가 만들어졌다", bool(st2.get("html_path")), str(st2.get("html_path")))
check("게이트 B 도 5키다",
      list(gate_b.keys()) == ["① 지금", "② 왜", "③ 권장", "④ 고르기", "⑤ 답"] if gate_b else False)
if gate_b:
    print("\n  ── 게이트 B 실제 화면 ──")
    print(json.dumps(gate_b, ensure_ascii=False, indent=2)[:1100])

print()
print("=" * 74)
print(" T9  게이트 B 에서 research 를 고르면 check_information 으로 되돌아가는가")
print("=" * 74)
seen3, gate3, st3 = run_to_gate(g, cfg, Command(resume={"action": "research", "note": "다낭 근거가 부족해 보인다"}))
print("  방문:", " → ".join(seen3))
check("check_information 을 다시 거친다", "check_information" in seen3)
check("정성 회차가 0 으로 되돌아갔다", st3.get("quality_pass") == 0)
check(f"도시는 여전히 {_WANT_CITIES}개다", len(st3.get("cities") or []) == _WANT_CITIES,
      f"{[c.get('name') for c in (st3.get('cities') or [])]}")
check("다시 게이트가 선다", gate3 is not None,
      str(gate3["① 지금"]).split("\n")[0][:70] if gate3 else "")

print()
print("=" * 74)
print(" T10  rebuilder 경로 — 배선과 노드 규격")
print("=" * 74)
from travel_graph.build import build
b = build()
d = b.compile().get_graph()
pairs = {(e.source, e.target) for e in d.edges}
check("human_gate_b → rebuilder 간선이 있다", ("human_gate_b", "rebuilder") in pairs)
check("rebuilder → check_page 로 이어진다", ("rebuilder", "check_page") in pairs)
check("human_gate_b → build_page 직행이 없다 (rebuild 는 rebuilder 로)",
      ("human_gate_b", "build_page") not in pairs)
check("rebuild 라우팅이 rebuild 를 돌려준다",
      edges.route_after_gate_b({"gate_b_answer": "rebuild"}) == "rebuild")
check("research 라우팅이 research 를 돌려준다",
      edges.route_after_gate_b({"gate_b_answer": "research"}) == "research")

import inspect
src = inspect.getsource(nodes.rebuilder)
check("rebuilder 가 HTML 을 직접 쓰지 않는다",
      "travel_site.html" not in src and "page.write" not in src)
check("rebuilder 가 고친 데이터를 상태로 되올린다",
      '"cities"' in src and "read_research" in src)
check("rebuilder 가 quality.apply_fixes 경로를 쓴다",
      "rebuild_from_note" in src)

print()
print("=" * 74)
print(" T11  ★ 국가 소개 재수집 — 배선 · 경로 파서 · 노드 규격")
print("=" * 74)
from travel_graph import research
from travel_graph.build import build as _build

_g = _build().compile()
_edges = {(a, b) for a, b, *_ in
          [(e.source, e.target) for e in _g.get_graph().edges]}
#  ★ 진단 노드가 생긴 뒤로 재수집은 **진단을 거쳐** 갈라진다 (검사기 → 진단 → 재수집).
check("check_information → diagnose_info → repair_country 간선이 있다",
      ("check_information", "diagnose_info") in _edges
      and ("diagnose_info", "repair_country") in _edges)
check("human_gate_a → repair_country 간선이 있다",
      ("human_gate_a", "repair_country") in _edges)
check("repair_country → check_information 으로 되돌아간다",
      ("repair_country", "check_information") in _edges)
from travel_graph.build import SPINE as _SPINE
check("루프 골격 노드 14개가 그대로 있다", len(_SPINE) == 14
      and set(_SPINE) <= set(_g.get_graph().nodes),
      f"NODES {len(_g.get_graph().nodes)}")

#  경로 파서 — 한글 키를 못 읽으면 patch 가 전부 조용히 거부된다
check("경로 파서가 한글 키를 읽는다",
      research._path_parts("매력.items[2]") == ["매력", "items", 2])
check("경로 파서가 영문 키도 그대로 읽는다",
      research._path_parts("spots[1].image") == ["spots", 1, "image"])
check("경로 파서가 엉뚱한 경로는 거부한다", research._path_parts("9bad") == [])
_fixed, _skip = research.apply_patches(
    {"매력": {"items": [{"text": "a"}]}},
    [{"path": "매력.items[1]", "value": {"text": "b"}}])
check("한글 경로로 근거를 한 칸 추가할 수 있다",
      len(_fixed["매력"]["items"]) == 2 and not _skip, f"거부={_skip}")
_f2, _s2 = research.apply_patches(
    {"매력": {"items": [{"text": "a"}]}},
    [{"path": "매력.items[5]", "value": {"text": "x"}}])
check("건너뛴 인덱스는 거부한다", len(_f2["매력"]["items"]) == 1 and _s2)

#  노드 규격
_out = nodes.repair_country({"country": "베트남",
                             "country_intro": {"매력": {"items": [{"text": "a"}]}},
                             "shorts": ["기능1 매력: 목표 3 / 실제 1"]})
check("repair_country 가 country_intro 를 돌려준다", "country_intro" in _out)
check("repair_country 가 cities 를 건드리지 않는다", "cities" not in _out)
check("repair_country 가 기록을 남긴다",
      any("repair_country" in h for h in _out.get("history", [])),
      str(_out.get("history"))[:90])
_src = inspect.getsource(nodes.repair_country)
check("repair_country 가 research 로 위임한다 (판정을 직접 안 한다)",
      "repair_country_intro" in _src)

#  지적이 없으면 손대지 않는다
_none = nodes.repair_country({"country": "베트남",
                              "country_intro": {"매력": {"items": [{"text": "a"}]}},
                              "shorts": []})
check("지적이 없으면 지난 결과를 그대로 둔다",
      _none["country_intro"] == {"매력": {"items": [{"text": "a"}]}})

#  게이트 A 가 더 이상 "재수집 대상 아님" 이라고 하지 않는다
_gate = nodes.gate_a_payload({
    "info_verdict": "SHORT", "loop_a_iter": 1, "loop_a_limit": 3,
    "same_error_count": 0, "same_error_limit": 2,
    "info_short_slots": ["기능1 매력: 목표 3 / 실제 1",
                         "기능1 환율: 목표 1 / 실제 0"],
    "cities": [], "city_failures": [], "html_path": ""})
_txt = json.dumps(_gate, ensure_ascii=False)
check("게이트가 '재수집 대상이 아님' 이라고 하지 않는다", "재수집 대상이 아님" not in _txt)
check("게이트 권장이 more 다 (바퀴가 남았을 때)",
      _gate["③ 권장"].startswith("more"), _gate["③ 권장"][:70])
check("게이트가 변동값 칸을 따로 알린다", "환율" in _txt)

print()
print("=" * 74)
print(" T12  ★ 원인 분석 · 지시문 제안 · 화면과 라우터 일치")
print("=" * 74)

#  (1) 원인이 갈리는가 — 처방이 서로 다른 것들이 한 통에 묶이면 안 된다
_CASES = {
    "기능1 역사 · 서로 다른 출처: 목표 2 / 실제 1": "출처가 겹침",
    "다낭/한강 근거 · 서로 다른 출처: 목표 2 / 실제 1": "출처가 겹침",
    "기능1 환율 (1건이면 충족): 목표 1 / 실제 0": "변동값",
    "기능1 항공권가격 (1건이면 충족): 목표 1 / 실제 0": "변동값",
    "기능1 매력: 목표 3 / 실제 1": "국가 소개 — 근거가 모자람",
    "기능1: country_intro 를 아직 만들지 않았습니다": "국가 소개를 아직 못 만듦",
    "기능1 국기이미지: 목표 살아 있는 이미지 1 / 실제 부족": "이미지 주소가 죽어 있음",
    "다낭/한강 이미지: 목표 살아 있는 이미지 1 / 실제 부족": "이미지 주소가 죽어 있음",
}
for line, want in _CASES.items():
    got = nodes.classify([line], nodes._CAUSE_A)[0]["원인"]
    check(f"'{line[:34]}…' → {want}", want in got, f"실제={got}")

#  ★ 회귀 방지: 출처 겹침이 '개수가 모자람' 으로 묶이면 처방이 정반대가 된다
check("출처 겹침이 '개수가 모자람' 으로 묶이지 않는다",
      "개수" not in nodes.classify(
          ["기능1 역사 · 서로 다른 출처: 목표 2 / 실제 1"], nodes._CAUSE_A)[0]["원인"])

#  (2) 원인마다 붙여 넣을 지시문이 나오는가
for line in _CASES:
    causes = nodes.classify([line], nodes._CAUSE_A)
    check(f"지시문 제안이 있다 — {causes[0]['원인'][:26]}",
          len(nodes.note_hint(causes)) > 10, nodes.note_hint(causes)[:60])

#  (3) 게이트 화면이 라우터와 **같은 곳**을 가리키는가
def _agree(shorts, label):
    st = {"info_verdict": "SHORT", "loop_a_iter": 1, "loop_a_limit": 3,
          "same_error_count": 0, "same_error_limit": 2,
          "selected_city_names": ["하노이", "다낭", "호이안"],
          "cities": [{"name": n} for n in ("하노이", "다낭", "호이안")],
          "city_failures": [], "country_intro": {"역사": {"items": [{"text": "a"}]}},
          "info_short_slots": shorts}
    screen = nodes.gate_a_payload(st)["④ 고르기"]["more"]
    sends = edges.fan_out_repairs(st)
    cities = sorted(x.arg["city"] for x in sends if x.node == "repair_city")
    country = any(x.node == "repair_country" for x in sends)
    ok_city = all(c in screen for c in cities)
    ok_ctry = (("국가 소개" in screen) == country)
    check(f"화면과 라우터가 일치 — {label}", ok_city and ok_ctry,
          f"화면={screen[:70]} / 라우터={cities}+{'국가' if country else '-'}")

_agree(["기능1 매력: 목표 3 / 실제 1"], "국가만 부족")
_agree(["다낭/한강 이미지: 목표 살아 있는 이미지 1 / 실제 부족"], "도시만 부족")
_agree(["기능1 매력: 목표 3 / 실제 1",
        "다낭/한강 이미지: 목표 살아 있는 이미지 1 / 실제 부족"], "둘 다 부족")

#  (4) 사람의 지시문이 국가 재수집 프롬프트까지 닿는가
_cap = {}
_real = research._claude_run
def _fake(prompt, *, tools, max_turns, label):
    _cap["p"] = prompt
    return {"patches": []}, {}
research._claude_run = _fake
_prev_mode = os.environ.get("GRAPH_MODE")
os.environ["GRAPH_MODE"] = "live"
try:
    research.repair_country_intro(
        {"country": "베트남", "gate_a_answer": "more",
         "gate_note": "칸마다 따로 찾아라",
         "country_intro": {"역사": {"items": [{"text": "a"}]}}},
        ["기능1 역사 · 서로 다른 출처: 목표 2 / 실제 1"])
finally:
    research._claude_run = _real
    if _prev_mode is None:
        os.environ.pop("GRAPH_MODE", None)
    else:
        os.environ["GRAPH_MODE"] = _prev_mode
_p = _cap.get("p", "")
check("지시문이 재수집 프롬프트에 실린다", "칸마다 따로 찾아라" in _p)
check("지시문이 '검사기 지적보다 우선' 으로 실린다", "검사기 지적보다 우선" in _p)
check("검사기 지적도 함께 실린다", "기능1 역사 · 서로 다른 출처" in _p)
_WANT_CHARM = ((contract.counts().get("country_intro") or {}).get("매력") or {}).get("target")
check("계약 하한이 실린다", f"매력 {_WANT_CHARM}건" in _p)
check("지난 회차 결과가 읽기용으로 실린다", "다시 적지 마십시오" in _p)
check("한글 경로 예시가 실린다", "매력.items[3]" in _p)

print()
print("=" * 74)
print(" T13  ★ 독립 감사가 잡아낸 결함 — 회귀 방지")
print("=" * 74)

#  (1) patch 가 조상 경로를 통째로 지우지 못한다
_city = {"name": "다낭", "spots": [{"name": "a"}, {"name": "b"}, {"name": "c"}],
         "itinerary": {"days": [1, 2, 3]}}
for _p in ("spots", "itinerary"):
    _f, _sk = research.apply_patches(_city, [{"path": _p, "value": [] if _p == "spots" else {}}])
    check(f"patch 로 `{_p}` 를 통째로 못 지운다",
          len(_f["spots"]) == 3 and len(_f["itinerary"]["days"]) == 3 and _sk,
          f"거부={_sk}")
_f, _sk = research.apply_patches({"spots": [{"image": {"url": "old", "alt": "a"}}]},
                                 [{"path": "spots[0].image",
                                   "value": {"url": "new", "alt": "b"}}])
check("정당한 통째 교체(이미지)는 여전히 된다",
      _f["spots"][0]["image"]["url"] == "new" and not _sk)
_f, _sk = research.apply_patches({"매력": {"items": [{"t": 1}]}},
                                 [{"path": "매력.items[1]", "value": {"t": 2}}])
check("근거 한 칸 추가는 여전히 된다", len(_f["매력"]["items"]) == 2 and not _sk)

#  (2) value 없는 patch 는 null 로 덮어쓰지 않는다
_f, _sk = research.apply_patches({"spots": [{"detail": "긴 설명"}]},
                                 [{"path": "spots[0].detail"}])
check("value 가 없는 patch 는 거부된다",
      _f["spots"][0]["detail"] == "긴 설명" and _sk, f"거부={_sk}")

#  (3) 도시 이름은 Send 가 준 것으로 고정된다 (재수집 고아 방지)
_norm = research._normalize_spots({"name": "Da Nang", "spots": []}, "다낭")
check("모델이 이름을 바꿔 써도 Send 의 이름을 쓴다", _norm["name"] == "다낭",
      f"실제={_norm['name']}")

#  (4) 부분 문자열 도시명이 교차 배정되지 않는다
_st = {"selected_city_names": ["하노이", "하노이시"],
       "cities": [{"name": "하노이"}, {"name": "하노이시"}], "city_failures": [],
       "info_short_slots": ["하노이시/롱비엔 다리 이미지: url 이 없습니다"]}
_t = [x.arg["city"] for x in edges.fan_out_repairs(_st) if x.node == "repair_city"]
check("`하노이시` 부족이 `하노이` 에게 가지 않는다", _t == ["하노이시"], f"보낸 곳={_t}")
check("belongs_to 가 토큰 경계를 본다",
      edges.belongs_to("하노이/롱비엔: x", "하노이")
      and not edges.belongs_to("하노이시/롱비엔: x", "하노이"))

#  (5) repair_country 가 실패 기록을 거둔다
_out = nodes.repair_country({"country": "베트남",
                             "country_intro": {"매력": {"items": [{"text": "a"}]}},
                             "shorts": ["기능1 매력: 목표 3 / 실제 1"]})
check("repair_country 가 city_failures 를 돌려준다", "city_failures" in _out)
_rows = nodes.merge_failures([{"city": "(국가 소개)", "why": "live 실패"}],
                             _out["city_failures"]) if hasattr(nodes, "merge_failures") else None
from travel_graph.state import merge_failures as _mf
check("성공하면 (국가 소개) 실패 줄이 사라진다",
      _mf([{"city": "(국가 소개)", "why": "live 실패"}], _out["city_failures"]) == [],
      str(_mf([{"city": "(국가 소개)", "why": "live 실패"}], _out["city_failures"])))

#  (6) 게이트 B 로 되돌아가면 안쪽 바퀴가 0 으로 (research/rebuild 가 죽지 않게)
import travel_graph.nodes as _N
_real_int = _N.interrupt
try:
    _N.interrupt = lambda payload: {"action": "research", "note": ""}
    _g = _N.human_gate_b({"quality_pass": 2, "quality_passes_required": 3,
                          "loop_a_iter": 3, "loop_b_iter": 3, "loop_a_limit": 3,
                          "loop_b_limit": 3, "page_verdict": "PASS",
                          "page_short_slots": [], "quality_short_slots": [],
                          "html_path": "x", "cities": [], "city_failures": []})
finally:
    _N.interrupt = _real_int
check("게이트 B 의 research 가 loop_a_iter 를 0 으로 되돌린다",
      _g.get("loop_a_iter") == 0, str({k: v for k, v in _g.items() if k != "history"}))
check("정성 회차도 0 으로 되돌린다", _g.get("quality_pass") == 0)
_st_exhausted = {"info_verdict": "SHORT", "loop_a_iter": 0, "loop_a_limit": 3,
                 "same_error_count": 0, "same_error_limit": 2,
                 "selected_city_names": ["다낭"], "cities": [{"name": "다낭"}],
                 "city_failures": [], "info_short_slots": ["다낭/한강 이미지: url 이 없습니다"]}
check("되돌린 뒤에는 재수집이 실제로 돈다",
      edges.route_after_info(_st_exhausted) != "gate")

#  (7) quality_pass 가 고친 데이터를 상태로 되올린다
_qsrc = inspect.getsource(nodes.quality_pass)
check("quality_pass 가 cities 를 상태로 되올린다", '"cities"' in _qsrc)
check("quality_pass 가 country_intro 도 되올린다", '"country_intro"' in _qsrc)

#  (8) 오류 지문이 전체 부족을 보고, PASS 면 비어 있다
check("부족이 줄면 지문이 바뀐다",
      nodes._error_hash("c", "SHORT", ["a", "b", "c"]) != nodes._error_hash("c", "SHORT", ["a", "b"]))
check("PASS 면 지문이 비어 있다 (거짓 '같은 오류 반복' 방지)",
      nodes._error_hash("c", "PASS", []) == "")

#  (9) normalize_gate 가 라우팅 낱말을 note 로 흘리지 않는다
for _a, _act, _note in [("more", "more", ""),
                        ("more 이미지를 다시 확인해라", "more", "이미지를 다시 확인해라"),
                        ("이미지를 다시 확인해라", "more", "이미지를 다시 확인해라"),
                        ({"action": "more"}, "more", "")]:
    _d = nodes.normalize_gate(_a, ("more", "proceed", "stop"), "proceed")
    check(f"normalize_gate({str(_a)[:26]}) → {_act}/{_note[:14]!r}",
          _d["action"] == _act and _d["note"] == _note, str(_d))

#  (9b) 문자열로 치든 dict 로 오든 **같은 판정**이 나온다.
#       Studio 의 resume 폼은 dict 를 보낸다. 예전에는 dict 갈래에만 "지시문만
#       왔으면 한 바퀴 더" 규칙이 없어서, `action` 을 비우고 `note` 에만 적으면
#       게이트 B 가 조용히 `done`(확정 종료)으로 갔다 — 입력 경로에 따라 정반대였다.
_GB = ("research", "rebuild", "done")
for _a in [{"action": "", "note": "a,b,c 이미지 규격이 안 맞음 재수집하라"},
           {"action": None, "note": "재수집하라"},
           {"action": "reserch", "note": "재수집"},
           "a,b,c 이미지 규격이 안 맞음 재수집하라"]:
    _d = nodes.normalize_gate(_a, _GB, "done")
    check(f"게이트B 지시문 {str(_a)[:30]} → research",
          _d["action"] == "research", str(_d))

#  (9c) 다른 게이트의 낱말을 "한 바퀴 더" 로 읽지 않는다.
#       게이트 B 에 `stop` 을 치면 허용값이 아니라 `note` 로 떨어졌고,
#       위 규칙이 그것을 **재수집**으로 읽었다. 멈춰라는 말이 한 바퀴 더가 됐다.
for _word, _allowed, _fb in [("stop", _GB, "done"), ("proceed", _GB, "done"),
                             ("done", ("more", "proceed", "stop"), "proceed")]:
    _d = nodes.normalize_gate(_word, _allowed, _fb)
    check(f"'{_word}' 는 {_allowed[0]} 로 새지 않는다",
          _d["action"] == _fb and _d["note"] == "" and bool(_d["warning"]), str(_d))

#  (10) 고칠 수 없는 부족을 게이트가 숨기지 않는다
_orph = {"info_verdict": "SHORT", "loop_a_iter": 1, "loop_a_limit": 3,
         "same_error_count": 0, "same_error_limit": 2,
         "selected_city_names": ["하노이", "다낭"], "cities": [], "city_failures": [],
         "info_short_slots": ["기능2 도시 개수: 목표 3 / 실제 2"]}
check("재수집으로 못 가는 부족을 ② 왜 가 맨 앞에 알린다",
      nodes.gate_a_payload(_orph)["② 왜"][0]["원인"] == "재수집으로 못 고치는 부족",
      str(nodes.gate_a_payload(_orph)["② 왜"][0]["원인"]))

#  (11) (국가 소개) 가 more 대상 목록에 새지 않는다
_leak = dict(_orph, city_failures=[{"city": "(국가 소개)", "why": "live 실패"}],
             info_short_slots=["다낭/한강 이미지: url 이 없습니다"])
check("(국가 소개) 가 more 대상에 표시되지 않는다",
      "(국가 소개)" not in nodes.gate_a_payload(_leak)["④ 고르기"]["more"])

#  (12) ★ 검사기가 못 보는 것 — 루프 C 를 여는 분기가 살아 있는가
#      route_after_gate_b 에서 카운터 분기를 지우면 quality_pass 가 한 번도
#      실행되지 않는데 check_graph_shape 12개는 전부 통과한다.
_rgb = inspect.getsource(edges.route_after_gate_b)
check("route_after_gate_b 가 quality 를 돌려줄 수 있다", '"quality"' in _rgb)
check("정성 3회 전이면 quality 로 간다",
      edges.route_after_gate_b({"gate_b_answer": "done", "quality_pass": 0,
                                "quality_passes_required": 3}) == "quality")
check("정성 3회 뒤면 done 으로 간다",
      edges.route_after_gate_b({"gate_b_answer": "done", "quality_pass": 3,
                                "quality_passes_required": 3}) == "done")
check("quality 가 ALLOWED 에 선언돼 있다",
      "quality" in edges.ALLOWED["route_after_gate_b"])

print()
print("=" * 74)
print(" T14  ★ 진단 · 처방 가지 — 루프 골격 14개는 그대로, 처방 가지는 문제 난 곳에서만")
print("=" * 74)
from travel_graph import detours
from travel_graph.build import SPINE, DIAGNOSE, build as _b14

_gg = _b14().compile().get_graph()
_names = set(_gg.nodes) - {"__start__", "__end__"}
_pairs = {(e.source, e.target) for e in _gg.edges}
_DET = {n for d in detours.ALL for n in (d.fix_node, d.test_node)}
check("노드 = 루프 골격 14 + 진단 2 + 처방 가지 fix·test",
      _names == set(SPINE) | set(DIAGNOSE) | _DET,
      str(sorted(_names ^ (set(SPINE) | set(DIAGNOSE) | _DET))))
check("노드 수 = 루프 골격 14 + 진단 2 + 2 × 등록 처방 가지 (킷 기본 22)",
      len(_names) == 14 + 2 + 2 * len(detours.ALL), f"{len(_names)}개 · 처방 가지 {len(detours.ALL)}개")
check("check_information → diagnose_info", ("check_information", "diagnose_info") in _pairs)
check("check_page → diagnose_page", ("check_page", "diagnose_page") in _pairs)
for d in detours.ALL:
    check(f"[{d.kind}] {d.diagnose} → {d.fix_node} → {d.test_node}",
          (d.diagnose, d.fix_node) in _pairs and (d.fix_node, d.test_node) in _pairs)
    check(f"[{d.kind}] 합격 → {d.home} · 불합격 → {d.fix_node} 또는 {d.gate}",
          {(d.test_node, d.home), (d.test_node, d.fix_node), (d.test_node, d.gate)} <= _pairs)
    check(f"[{d.kind}] 처방 가지는 진단에서만 갈라진다",
          {s for s, t in _pairs if t == d.fix_node} <= {d.diagnose, d.test_node})

#  ALLOWED 는 **출처마다** 배선과 같아야 한다 (시험 노드 셋이 라우터 하나를 같이 쓴다)
for _src, _grp in _b14().branches.items():
    for _rn, _br in _grp.items():
        if _rn.startswith("fan_"):
            continue
        check(f"ALLOWED[{_rn}] == 배선 @ {_src}",
              set(edges.ALLOWED.get(_rn, ())) == set(_br.ends or {}),
              f"선언={sorted(edges.ALLOWED.get(_rn, ()))} 배선={sorted(_br.ends or {})}")

#  라우터 단위 — 원인이 판정보다 먼저, 한도가 탈출구
_r = edges.route_after_info
check("원인이 처방 가지면 판정이 PASS 여도 그쪽으로 간다",
      _r({"info_verdict": "PASS", "failure_kind": "encoding", "detour_limit": 2,
          "detour_attempts": {}}) == "encoding")
check("한도를 다 쓴 처방 가지는 타지 않는다 (PASS → gate)",
      _r({"info_verdict": "PASS", "failure_kind": "encoding", "detour_limit": 2,
          "detour_attempts": {"encoding": 2}}) == "gate")
check("루프 B 처방 가지 이름은 루프 A 라우터가 받지 않는다",
      _r({"info_verdict": "PASS", "failure_kind": "image_spec", "detour_limit": 2}) == "gate")
_rd = edges.route_after_detour
check("시험 합격 → back", _rd({"detour_verdict": "PASS", "failure_kind": "encoding"}) == "back")
check("시험 불합격 · 한도 안 → retry",
      _rd({"detour_verdict": "FAIL", "failure_kind": "encoding", "detour_limit": 2,
           "detour_attempts": {"encoding": 1}}) == "retry")
check("시험 불합격 · 한도 끝 → gate",
      _rd({"detour_verdict": "FAIL", "failure_kind": "encoding", "detour_limit": 2,
           "detour_attempts": {"encoding": 2}}) == "gate")


def _after(seen, node):
    i = seen.index(node)
    return seen[i + 1] if i + 1 < len(seen) else None


def _log_rows(node=None, thread=None):
    rows = []
    for f in _FAIL_DIR.glob("*.jsonl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if (node is None or row.get("node") == node) and (thread is None or row.get("thread") == thread):
                    rows.append(row)
    return rows


#  inject 없음 — 루프 골격 그대로
_g0 = compile_graph(InMemorySaver())
_c0 = {"configurable": {"thread_id": "t14-clean"}, "recursion_limit": 150}
_s0, _gate0, _st0 = run_to_gate(_g0, _c0, {})
check("inject 가 없으면 처방 가지를 한 번도 타지 않는다", not (set(_s0) & _DET), str(set(_s0) & _DET))
check("inject 가 없어도 진단은 돈다 (판정 다음에 원인)", "diagnose_info" in _s0)
check("첫 정지는 human_gate_a", tuple(_g0.get_state(_c0).next) == ("human_gate_a",))
check("진단이 실패 기록을 남긴다", bool(_log_rows("diagnose_info", "t14-clean")))
_clean_iter = _st0.get("loop_a_iter")
#  ★ 루프 B 까지 간다 — 루프 B 처방 가지의 오탐은 게이트 A 에서 멈추면 영영 안 보인다.
_s0b, _gate0b, _st0b = run_to_gate(_g0, _c0, Command(resume={"action": "proceed", "note": ""}))
check("inject 가 없으면 루프 B 에서도 처방 가지를 한 번도 타지 않는다 (오탐 없음)",
      "diagnose_page" in _s0b and not (set(_s0b) & _DET), " → ".join(_s0b))
check("inject 없이 두 번째 정지는 human_gate_b", tuple(_g0.get_state(_c0).next) == ("human_gate_b",))

#  처방 가지마다 — 재현하면 진단 → fix → test → 검사기로 복귀
for d in detours.ALL:
    _gk = compile_graph(InMemorySaver())
    _ck = {"configurable": {"thread_id": f"t14-{d.kind}"}, "recursion_limit": 150}
    _sk, _gk_gate, _stk = run_to_gate(_gk, _ck, {"inject": [d.kind]})
    if d.loop == "B":
        _more, _gk_gate, _stk = run_to_gate(_gk, _ck, Command(resume={"action": "proceed", "note": ""}))
        _sk = _sk + _more
    print(f"  [{d.kind}] 방문:", " → ".join(_sk[-9:]))
    _order = all(n in _sk for n in (d.diagnose, d.fix_node, d.test_node)) and \
        _sk.index(d.diagnose) < _sk.index(d.fix_node) < _sk.index(d.test_node)
    check(f"[{d.kind}] 재현하면 {d.diagnose} → {d.fix_node} → {d.test_node}", _order)
    check(f"[{d.kind}] 시험에 한 번에 합격하고 {d.home} 로 돌아간다",
          d.test_node in _sk and _sk.count(d.test_node) == 1 and _after(_sk, d.test_node) == d.home)
    check(f"[{d.kind}] 합격 기록이 실패 기록에 남는다",
          any(r.get("detour_verdict") == "PASS" for r in _log_rows(d.test_node, f"t14-{d.kind}")))
    check(f"[{d.kind}] 게이트에 섰을 때 처방 가지 칸이 비어 있다",
          not _stk.get("failure_kind") and not _stk.get("failure_evidence"),
          str((_stk.get("failure_kind"), _stk.get("failure_evidence"))))
    if d.loop == "A":
        check(f"[{d.kind}] 처방 가지는 바퀴를 쓰지 않는다 (inject 없을 때와 같은 {_clean_iter}바퀴)",
              _stk.get("loop_a_iter") == _clean_iter, f"loop_a_iter={_stk.get('loop_a_iter')}")
    else:
        check(f"[{d.kind}] 처방 가지는 바퀴를 쓰지 않는다 (loop_b_iter 1)",
              _stk.get("loop_b_iter") == 1, f"loop_b_iter={_stk.get('loop_b_iter')}")
    check(f"[{d.kind}] 처방 가지가 고친 뒤 시험지가 합격이다",
          detours.run_test(d.kind).verdict == "PASS")

#  한도 — 계속 떨어지면 사람에게 (시험지를 일부러 떨어뜨린다)
_orig_run_test = detours.run_test
_Fake = detours.test_module("encoding").Result


def _always_fail(kind, root=None):
    if kind == "image_dead":
        _r = _Fake("fake")
        _r.note_short("죽은 이미지 주소: 목표 0 / 실제 1")
        _r.note_short("하노이/가짜 이미지: 이미지 주소가 열리지 않았습니다 — 일부러 떨어뜨림")
        return _r
    return _orig_run_test(kind, root)


detours.run_test = _always_fail
try:
    _gx = compile_graph(InMemorySaver())
    _cx = {"configurable": {"thread_id": "t14-exhaust"}, "recursion_limit": 150}
    _sx, _gatex, _stx = run_to_gate(_gx, _cx, {})
    check("계속 떨어지면 한도(2회)만큼만 돈다", _sx.count("test_image_dead") == 2,
          " → ".join(_sx))
    check("한도를 다 쓰면 게이트 A 에서 멈춘다", tuple(_gx.get_state(_cx).next) == ("human_gate_a",))
    _why = (_gatex or {}).get("② 왜") or [{}]
    check("게이트 ② 왜 맨 앞에 '처방 가지가 못 고침'이 뜬다",
          str(_why[0].get("원인", "")).startswith("처방 가지가 못 고침"), str(_why[0]))
    check("그 게이트도 5키 화면이다",
          list((_gatex or {}).keys()) == ["① 지금", "② 왜", "③ 권장", "④ 고르기", "⑤ 답"])
    _sy, _gatey, _sty = run_to_gate(_gx, _cx, Command(resume={"action": "more", "note": ""}))
    check("게이트 A 에서 more 를 고르면 처방 한도가 새로 채워진다",
          any("처방 한도를 새로 채웁니다" in h for h in _sty.get("history", []))
          and _sy.count("test_image_dead") == 2, " → ".join(_sy))
finally:
    detours.run_test = _orig_run_test

#  정성이 시작된 뒤에는 처방 가지를 타지 않는다 (해시 사슬 보호)
detours.run_test = lambda kind, root=None: (_always_fail("image_dead") if kind == "image_spec"
                                            else _orig_run_test(kind, root))
try:
    _busy = nodes.diagnose_page({"quality_pass": 1, "detour_limit": 2, "detour_attempts": {}})
    _idle = nodes.diagnose_page({"quality_pass": 0, "detour_limit": 2, "detour_attempts": {}})
    check("정성 회차 중이면 증상이 있어도 처방 가지를 고르지 않는다",
          _busy["failure_kind"] == "" and any("정성" in x for x in _busy["failure_evidence"]),
          str(_busy))
    check("정성 전이면 같은 증상으로 처방 가지를 고른다", _idle["failure_kind"] == "image_spec")
finally:
    detours.run_test = _orig_run_test

#  게이트 B 의 research · rebuild 는 처방 한도도 되돌린다 (바깥 루프는 사람 소유)
_saved_interrupt = nodes.interrupt
nodes.interrupt = lambda payload: {"action": "research", "note": ""}
try:
    _hb = nodes.human_gate_b({"quality_pass": 0, "quality_passes_required": 3,
                              "detour_attempts": {"image_spec": 2}, "failure_kind": "image_spec"})
    check("게이트 B research 는 처방 한도를 0 으로", _hb.get("detour_attempts") == {}
          and _hb.get("failure_kind") == "")
finally:
    nodes.interrupt = _saved_interrupt

#  시험지는 고치는 코드를 import 하지 않는다 (판정 독립)
for d in detours.ALL:
    _src = d.test_path.read_text(encoding="utf-8")
    check(f"[{d.kind}] 시험지가 travel_graph 를 import 하지 않는다",
          "import travel_graph" not in _src and "from travel_graph" not in _src)

#  시험지는 멀쩡한 인계본에 합격한다 — 오탐이 없어야 기본 실행에서 처방 가지가 안 켜진다
_ok_enc = detours.test_module("encoding")
check("정상 베트남어 · 프랑스어 악센트는 모지바케가 아니다",
      not _ok_enc.mojibake_runs("Hội An · Chùa Cầu · Musée Cham · Đà Nẵng · naïve café"))
from travel_graph.detours import encoding as _enc
check("모지바케를 만들고 되읽으면 원문이 나온다",
      _enc.unmojibake(_enc.mojibake("호안끼엠 호수는 하노이의 중심")) == "호안끼엠 호수는 하노이의 중심")
check("모지바케는 시험지가 잡는다", bool(_ok_enc.mojibake_runs(_enc.mojibake("하노이"))))

#  리뷰에서 재현된 오탐 — 악센트 뒤에 구두점이 붙은 정상 글. 잡지도 고치지도 않아야 한다.
for _txt in ("CAFÉ·BAR 거리", "“Cà phê…”", "café…”", "PHÔ–", "Đà Nẵng — Hội An"):
    check(f"정상 글 {_txt!r} 은 모지바케가 아니다 · fix 가 건드리지 않는다",
          not _ok_enc.mojibake_runs(_txt) and _enc.unmojibake(_txt) == _txt)
check("일본어 모지바케도 되읽는다 (두 글자 이상)", _enc.unmojibake(_enc.mojibake("東京駅")) == "東京駅")

#  image_dead — Commons 가 아닌 주소 · 다른 나라 · 카메라 파일명
from travel_graph.detours import image_dead as _dead
check("Commons 가 아닌 주소에서는 파일 이름을 뽑지 않는다 (엉뚱한 Commons 사진 방지)",
      _dead.filename_of("https://vietnam.travel/photos/IMG_4008.jpg") == "")
check("카메라 파일명(IMG_4008)은 검색 낱말이 없다", _dead._words("IMG_4008.jpg") == [])
_other = {"country": "일본", "country_intro": {"국기이미지": {"asset": {
    "url": _dead.canonical("Flag_of_Japan_2019.svg"), "alt": "일본 국기",
    "verified": {"status": 404, "content_type": "", "checked_at": "", "error": "HTTP 404"}}}},
    "cities": []}
_out = _dead.fix(_other, attempt=1, mode="replay")
check("다른 나라면 인계본(베트남) 사진을 쓰지 않는다",
      "Vietnam" not in _other["country_intro"]["국기이미지"]["asset"]["url"] and not _out["fixed"],
      str(_out))
_city = copy.deepcopy(contract.baseline()["cities"][0])
_note = _dead.inject(_city)
_url = _city["spots"][1]["image"]["url"]
check("image_dead 재현은 실측 모양 그대로 — upload 주소 · 해시 8/8c · 404",
      "upload.wikimedia.org" in _url and "/thumb/8/8c/" in _url and "8/8c" in _note, _url)
_fixed = _dead.fix({"country": "베트남", "country_intro": {}, "cities": [_city]}, attempt=1, mode="replay")
check("image_dead 1회째는 실측의 처방(해시 없는 권장 형태)으로 고친다",
      any("권장 형태로 바로잡았습니다" in x for x in _fixed["fixed"])
      and _city["spots"][1]["image"]["url"].startswith(_dead.FILEPATH), str(_fixed))

#  교육생 코드가 터져도 그래프는 죽지 않는다
_mod = _dead
_orig_fix = _mod.fix
_mod.fix = lambda data, *, attempt, mode: {}["no_such_key"]
try:
    _crash = detours.fix("image_dead", {"cities": []}, attempt=1, mode="replay")
    check("fix() 가 예외를 내면 '못 고침' 으로 적고 넘어간다 (그래프를 죽이지 않는다)",
          _crash["fixed"] == [] and "멈췄습니다" in _crash["unfixed"][0], str(_crash))
finally:
    _mod.fix = _orig_fix

#  실패 기록 파일 이름 — 한글 thread 둘이 한 파일로 합쳐지지 않는다
from travel_graph.detours import log as _log
check("한글 thread 이름 둘은 다른 파일에 적힌다", _log.path_for("첫실행") != _log.path_for("두번째"))


print()
print("=" * 74)
print(" T15  ★ 구조 검사 11번(처방 가지 계약)이 살아 있는가 — 킷 복사본을 일부러 망가뜨린다")
print("=" * 74)
import subprocess as _sp

_MUTATIONS = [
    ("처방 가지 라우터가 한도를 안 읽는다", "travel_graph/edges.py",
     '    if _tries(state, state.get("failure_kind") or "") < (state.get("detour_limit") or 0):\n        return "retry"',
     '    if state.get("failure_kind"):\n        return "retry"'),
    ("합격하면 수집 노드로 돌아간다", "travel_graph/build.py",
     '{"back": d.home, "retry": d.fix_node, "gate": d.gate}',
     '{"back": "collect_city", "retry": d.fix_node, "gate": d.gate}'),
    ("등록 안 된 노드를 끼워 넣는다", "travel_graph/build.py",
     '    g.add_node("diagnose_page", nodes.diagnose_page)\n',
     '    g.add_node("diagnose_page", nodes.diagnose_page)\n'
     '    g.add_node("fix_everything", nodes.build_page)\n'
     '    g.add_edge("fix_everything", "check_page")\n'
     '    g.add_edge("human_gate_b", "fix_everything")\n'),
    ("처방 가지가 판정 칸에 쓴다", "travel_graph/nodes.py",
     '        "detour_attempts": tries,\n        "history": trail,',
     '        "detour_attempts": tries,\n        "info_verdict": "PASS",\n        "history": trail,'),
    ("검사기에 조건부 간선을 같이 단다", "travel_graph/build.py",
     '    g.add_edge("check_page", "diagnose_page")\n',
     '    g.add_edge("check_page", "diagnose_page")\n'
     '    g.add_conditional_edges("check_page", edges.route_after_page, {"retry": "build_page", '
     '"gate": "human_gate_b", "image_spec": "fix_image_spec"})\n'),
    ("시험지가 고치는 코드를 import 한다", "scripts/detour_tests/test_encoding.py",
     "import re\nimport sys\n", "import re\nimport sys\nimport travel_graph  # noqa\n"),
    #  ★ 배선(매핑)은 남고 라우터만 처방 가지를 안 돌려준다 — 4 · 10번은 통과하는 종류다.
    #  ★ 검사 대상(build.SPINE)을 기준으로 삼으면 여기에 이름만 더 적어도 통과한다.
    ("루프 골격 목록(SPINE)에 이름을 하나 더 적는다", "travel_graph/build.py",
     '    "quality_pass", "check_quality",\n)',
     '    "quality_pass", "check_quality", "fix_everything",\n)'),
    #  ★ 주석 속 글자로는 한도를 읽은 것으로 치지 않는다.
    ("시험 뒤 라우터의 한도를 주석으로만 남긴다", "travel_graph/edges.py",
     '    if _tries(state, state.get("failure_kind") or "") < (state.get("detour_limit") or 0):\n'
     '        return "retry"',
     '    return "retry"   # detour_limit 은 나중에'),
    ("라우터의 `킷 고정 ▼` 처방 가지 분기를 지운다", "travel_graph/edges.py",
     '    kind = state.get("failure_kind") or ""\n'
     '    if kind in detours.kinds("A") and _tries(state, kind) < (state.get("detour_limit") or 0):\n'
     '        return kind\n',
     ""),
]
for _name, _rel, _old, _new in _MUTATIONS:
    _tmp = Path(tempfile.mkdtemp(prefix="regress_mut_"))
    try:
        for _part in ("travel_graph", "scripts", "graph"):
            shutil.copytree(ROOT / _part, _tmp / _part,
                            ignore=shutil.ignore_patterns("__pycache__"))
        _target = _tmp / _rel
        _text = _target.read_text(encoding="utf-8")
        if _text.count(_old) != 1:
            check(f"변이 '{_name}' 를 심을 자리가 있다", False, _rel)
            continue
        _target.write_text(_text.replace(_old, _new), encoding="utf-8")
        _out = _sp.run([sys.executable, str(_tmp / "scripts" / "check_graph_shape.py"), "--json"],
                       capture_output=True, text=True, encoding="utf-8", cwd=_tmp)
        _red = [r["name"].split()[0] for r in json.loads(_out.stdout)["rows"] if not r["passed"]]
        check(f"'{_name}' → 11번 빨간불", "11" in _red, f"빨간불 {_red}")
    finally:
        shutil.rmtree(_tmp, ignore_errors=True)

print()
print("=" * 74)
print(" T16  ★ 재수집 뒤 검사기가 죽지 않는가 · 보고서 ③-2 (재수집이 반복해서 맡은 원인)")
print("=" * 74)
from travel_graph import research

#  K1 — 재수집 patch 가 칸의 형을 바꾸면 다음 걸음의 check_information 이 `.strip()` 에서 죽는다.
_k1 = copy.deepcopy(contract.baseline()["cities"][0])
_k1_fixed, _k1_skip = research.apply_patches(_k1, [
    {"path": "preference_note", "value": ["목록으로", "보낸 취향"]},
    {"path": "why_selected", "value": {"text": "객체로 보낸 이유"}},
    {"path": "spots[0].detail", "value": "글자는 글자로 — 이 patch 는 붙는다"}])
check("글자 칸에 목록 · 객체를 보내면 '형이 다릅니다' 로 거부한다",
      sum("형이 다릅니다" in s for s in _k1_skip) == 2 and isinstance(_k1_fixed["preference_note"], str)
      and isinstance(_k1_fixed["why_selected"], str), str(_k1_skip))
check("같은 형의 patch 는 그대로 붙는다", _k1_fixed["spots"][0]["detail"].startswith("글자는 글자로"))
_k1_state = {"country": contract.baseline().get("country"), "days": contract.baseline().get("days"),
             "country_intro": contract.baseline().get("country_intro"),
             "cities": [_k1_fixed] + copy.deepcopy(contract.baseline()["cities"][1:]),
             "loop_a_iter": 1, "same_error_count": 0, "last_error_hash": ""}
try:
    _k1_out = nodes.check_information(_k1_state)
    check("거부한 뒤의 check_information 은 예외 없이 판정한다",
          _k1_out.get("info_verdict") in ("PASS", "SHORT"), str(_k1_out.get("info_verdict")))
except Exception as _exc:                                           # noqa: BLE001
    check("거부한 뒤의 check_information 은 예외 없이 판정한다", False, f"{type(_exc).__name__}: {_exc}")

#  재수집 뒤 사진은 **바뀐 것만** 다시 연다 (한 장에 20초까지 — 가장 느린 갈래가 다음 걸음을 늦춘다)
_opened = []
_saved = (research.verify_asset, research._claude_run, research.mode)
_new_url = "https://commons.wikimedia.org/wiki/Special:FilePath/Hoan_Kiem_Lake.jpg?width=1024"
research.verify_asset = lambda a: (_opened.append(a.get("url")),
                                   dict(a, verified={"status": 200, "content_type": "image/jpeg",
                                                     "checked_at": "t"}))[1]
research._claude_run = lambda prompt, **kw: ({"patches": [{"path": "spots[1].image.url", "value": _new_url}]},
                                             {"searches": 1})
research.mode = lambda: "live"
try:
    _rc = copy.deepcopy(contract.baseline()["cities"][0])
    _rc_name = _rc["name"]
    _rc_out, _rc_note, _rc_fail = research.repair_one_city(
        _rc_name, {"cities": [_rc], "country": "베트남"}, [f"{_rc_name}/x 이미지: 목표 살아 있는 이미지 1 / 실제 부족"])
    check("재수집 뒤 주소가 바뀐 사진 한 장만 다시 연다", _opened == [_new_url], str(_opened))
    check("바꾼 사진에는 새 확인 기록이 붙는다",
          _rc_out["spots"][1]["image"].get("verified", {}).get("status") == 200 and not _rc_fail)
finally:
    research.verify_asset, research._claude_run, research.mode = _saved
check("주소가 글자가 아니면 비우고 사유를 적는다 (검사기가 멈추지 않게)",
      research.verify_asset({"url": ["a"], "alt": "x"})["url"] == ""
      and "글자가 아니었습니다" in research.verify_asset({"url": 3})["verified"]["error"])

#  진단 기록에 바퀴 번호가 남는다 — ③-2 가 "같은 원인이 몇 바퀴 남았나"를 센다
_t14_rows = _log_rows("diagnose_info", "t14-clean")
check("진단 기록에 loop_iter · inject · 새 어휘(루프 골격 그대로)가 남는다",
      bool(_t14_rows) and all("loop_iter" in r and r.get("inject") == [] for r in _t14_rows)
      and all(r.get("decision") == "루프 골격 그대로" for r in _t14_rows), str(_t14_rows[:1]))

import importlib.util as _ilu
_fr_spec = _ilu.spec_from_file_location("kit_failure_report", ROOT / "scripts" / "failure_report.py")
_fr = _ilu.module_from_spec(_fr_spec)
_fr_spec.loader.exec_module(_fr)


def _diag(run, loop_iter, cause, places, mode="live", kind="", verdict="SHORT"):
    return {"thread": run, "node": "diagnose_info", "loop": "A", "mode": mode, "verdict": verdict,
            "loop_iter": loop_iter, "failure_kind": kind,
            "causes": [{"원인": cause, "몇 곳": f"{places} / 9", "예": f"하노이/문묘: {cause}"}],
            "unmatched": [], "city_failures": [], "symptoms": {}}


def _write_runs(folder, runs):
    for name, rows in runs.items():
        (folder / (name + ".jsonl")).write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


_rep = Path(tempfile.mkdtemp(prefix="regress_report_"))
try:
    #  run-a (live) — 같은 원인이 1 · 2 · 3바퀴에 남았다. 2바퀴에는 처방 가지 복귀 방문(같은 바퀴)이 한 줄 더.
    #  run-b (live) — 한 바퀴만.  run-c (replay) — 세지 않는다.
    _write_runs(_rep, {
        "run-a": [_diag("run-a", 1, "개수가 모자람", 5), _diag("run-a", 2, "개수가 모자람", 3),
                  _diag("run-a", 2, "개수가 모자람", 3), _diag("run-a", 3, "개수가 모자람", 2),
                  _diag("run-a", 3, "그 밖", 1)],
        "run-b": [_diag("run-b", 1, "출처가 겹침 (건수가 아니라 **출처**가 문제)", 1),
                  _diag("run-b", 2, "", 0, verdict="PASS")],
        "run-c": [_diag("run-c", 1, "이미지를 아직 안 모음", 9, mode="replay")],
    })
    _sum = _fr.summarize(_fr.files_from([str(_rep)], False))
    _by = {(c["loop"], c["cause"]): c for c in _sum["repeated_causes"]}
    _many = _by.get(("A", "개수가 모자람"), {})
    check("③-2 — 한 실행에서 여러 바퀴 남은 원인은 후보 (복귀 방문은 같은 바퀴로 한 번만)",
          _many.get("max_rounds") == 3 and _many.get("runs") == 1 and _many.get("candidate") is True,
          str(_many))
    _once = _by.get(("A", "출처가 겹침 (건수가 아니라 **출처**가 문제)"), {})
    check("③-2 — 한 번만 나온 원인은 후보가 아니다 (재수집이 맡으면 된다)",
          _once.get("max_rounds") == 1 and _once.get("candidate") is False, str(_once))
    check("③-2 — '그 밖' 은 ③ 이 보여 주므로 빼고 · replay 줄은 세지 않는다",
          ("A", "그 밖") not in _by and ("A", "이미지를 아직 안 모음") not in _by
          and _sum["replay_rows_skipped"] == 1, str(sorted(_by)))
    check("③-2 후보가 있으면 STEP 6 을 권한다", _sum["step6"] is True)
    _out = _sp.run([sys.executable, str(ROOT / "scripts" / "failure_report.py"), str(_rep)],
                   capture_output=True, text=True, encoding="utf-8")
    check("보고서 화면에 ③-2 와 조건부 '다음:' 줄이 뜬다",
          "③-2 재수집(LLM)이 반복해서 맡은 원인" in _out.stdout and " 다음: " in _out.stdout, _out.stdout[-400:])
    shutil.rmtree(_rep, ignore_errors=True)
    _rep.mkdir()
    _write_runs(_rep, {"run-d": [_diag("run-d", 1, "개수가 모자람", 4),
                                 _diag("run-d", 2, "", 0, verdict="PASS")]})
    _out = _sp.run([sys.executable, str(ROOT / "scripts" / "failure_report.py"), str(_rep)],
                   capture_output=True, text=True, encoding="utf-8")
    check("후보가 없으면 'STEP 6 은 하지 않아도 됩니다' · '다음:' 줄이 없다",
          "STEP 6 은 하지 않아도 됩니다" in _out.stdout and " 다음: " not in _out.stdout, _out.stdout[-400:])
    #  ③ — 규칙표 밖 부족이 **한 번**이면 일화(STEP 6 아님), 두 바퀴에 되풀이되면 후보
    shutil.rmtree(_rep, ignore_errors=True)
    _rep.mkdir()
    _odd = dict(_diag("run-e", 1, "개수가 모자람", 1), unmatched=["기능2 도시 개수: 목표 3 / 실제 2"])
    _write_runs(_rep, {"run-e": [_odd]})
    _sum = _fr.summarize(_fr.files_from([str(_rep)], False))
    _out = _sp.run([sys.executable, str(ROOT / "scripts" / "failure_report.py"), str(_rep)],
                   capture_output=True, text=True, encoding="utf-8")
    check("③ — 한 번 나온 실패는 [일화] · STEP 6 을 권하지 않는다",
          [c["verdict"] for c in _sum["candidates"]] == ["일화"] and _sum["step6"] is False
          and "일화" in _out.stdout and " 다음: " not in _out.stdout, _out.stdout[-400:])
    _write_runs(_rep, {"run-e": [_odd, dict(_odd, loop_iter=2)]})
    _sum = _fr.summarize(_fr.files_from([str(_rep)], False))
    check("③ — 같은 줄이 두 번 나오면 [후보] · STEP 6 을 권한다",
          [c["verdict"] for c in _sum["candidates"]] == ["후보"] and _sum["step6"] is True, str(_sum["candidates"]))
    #  재현(inject) 실행은 일부러 일으킨 실패 — ③ · ③-2 후보로 세지 않는다 (① 에는 뜬다)
    _write_runs(_rep, {"run-e": [dict(_odd, inject=["image_dead"]), dict(_odd, loop_iter=2, inject=["image_dead"])]})
    _sum = _fr.summarize(_fr.files_from([str(_rep)], False))
    check("재현(inject) 실행의 실패는 ③ · ③-2 후보가 아니다",
          not _sum["candidates"] and not _sum["repeated_causes"] and _sum["step6"] is False
          and _sum["inject_runs_skipped"] == ["run-e"], str(_sum["candidates"]))
finally:
    shutil.rmtree(_rep, ignore_errors=True)

#  정성 — 위반이라 적고 fix 가 없으면 같은 회차에서 보완한다 (live 리허설에서 실제로 난 일)
from travel_graph import quality as _q
_jd = [{"id": "Q-근거일치", "verdict": "VIOLATION", "where": "a", "note": "n"},
       {"id": "Q-실용누락", "verdict": "VIOLATION", "where": "b", "note": "n"},
       {"id": "Q-반복금지", "verdict": "OK", "where": "-", "note": ""}]
_uf = _q._unfixed(_jd, [{"rule": "Q-근거일치"}])
_jd2, _fx = _q.merge_followup(_jd, _uf, {
    "rules": [{"id": "Q-실용누락", "verdict": "OK", "note": "다시 보니 있음"},
              {"id": "Q-반복금지", "verdict": "VIOLATION"}],
    "fixes": [{"rule": "Q-실용누락", "path": "p", "value": "v"}, {"rule": "Q-딴것", "path": "p", "value": "v"}]})
check("정성 보완 — fix 없는 위반만 다시 묻고, 요청한 규율의 fix 만 받는다",
      _uf == ["Q-실용누락"] and [f["rule"] for f in _fx] == ["Q-실용누락"], str((_uf, _fx)))
check("정성 보완 — '위반 아님' 재판정은 처음 판정을 note 에 남기고, 요청 밖 규율은 바꾸지 않는다",
      [r["verdict"] for r in _jd2] == ["VIOLATION", "OK", "OK"] and "처음 판정(VIOLATION" in _jd2[1]["note"],
      str(_jd2))
check("정성 3회 뒤 판정이 SHORT 면 게이트 C 는 '확정'을 권하지 않는다",
      nodes._recommend_b({"quality_verdict": "SHORT"}, [], [], True).startswith("rebuild")
      and nodes._recommend_b({"quality_verdict": "PASS"}, [], [], True).startswith("done"))

print()
print("=" * 74)
print(f" 결과  통과 {len(PASS)} · 실패 {len(FAIL)}")
if FAIL:
    for f in FAIL:
        print("   실패:", f)
print("=" * 74)
_restore()
sys.exit(1 if FAIL else 0)
