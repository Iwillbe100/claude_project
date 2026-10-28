# STEP 3 — 조건⑥ 간선 조건

> **한 줄 목적:** 라우터가 **무엇을 보고** 다음 노드를 고를지 정한다.
> **내가 결정할 것: 2개** · **코드 변경: 권장값이면 없음** (다른 값을 고르면 `travel_graph/edges.py` 의 STEP 3 라우터 4개 중 **그 함수만**)
> (라우터는 모두 6개 + fan-out 2개입니다. 나머지 2개(`route_after_quality` · `route_after_detour`)와
> 4개 안의 **처방 가지 분기 · 정성 분기**는 `킷 고정 ▼` 이라 고치지 않습니다)

| 이전 | 다음 | 문서 규칙 | 결정 장부 |
| --- | --- | --- | --- |
| [STEP 2 — 노드 경계](02_NODE_BOUNDARY.md) | [STEP 4 — 병렬](04_PARALLEL.md) | [00_INDEX](00_INDEX.md) | [00_DECISION_LOG](00_DECISION_LOG.md) |

---

## 읽기 1 — 이 STEP에서 정하는 것

**루프의 조건⑥ '반복 규칙'이 여기로 옵니다.** 라우팅이 **코드에서 데이터로** 바뀝니다.

```text
루프          if exit_code == 2: 다시 돌린다        ← if 문이 코드 안에
그래프        info_verdict 를 읽고 노드 이름을 고른다  ← 조건이 상태 값
              failure_kind(진단이 쓴 원인)를 먼저 본다  ← 처방 가지 분기 (킷 고정 · 아래 2-b)
```

### 먼저 지금 상태를 눈으로 보십시오

```bash
python scripts/check_graph_shape.py
```

**`PASS` 가 나옵니다. 정상입니다.** 킷은 **완성된 상태**로 배포됩니다 —
그래야 인계본이 실제로 그래프로 확장되는 모습을 바로 볼 수 있습니다.

**그러면 이 STEP 에서 뭘 하나.** 세 가지입니다.

```text
① 읽는다   지금 라우터가 왜 이 조건인지. 조건마다 막는 실패가 다르다
② 정한다   `G-라우터판단` · `G-상한처리` 두 결정을 장부에 적는다
③ 확인한다 고른 값이 코드와 맞는지 검사기로 확인한다
```

권장값을 고르면 코드는 그대로입니다. **다른 값을 고르면 그때 코드를 고칩니다** —
어디를 고치는지는 아래 6번에 있습니다. 무엇을 고르든 마지막에 같은 검사기를 돌려
통과를 확인합니다. **통과가 안 되면 검사기가 아니라 코드를 고칩니다.**

---

## 읽기 2 — 앞에서 물려받은 결정

<!-- PROJECT:BEGIN -->

| 물려받은 것 | 값 | 어디서 |
| --- | --- | --- |
| 판정 필드 | A — 남긴다 (`*_verdict`) | `G-판정필드` |
| 검사기 노드화 | A — 노드로 넣는다 | `G-검사기노드화` |
| 상한 | A 3바퀴 · B 3바퀴 · 같은 오류 2회 | `graph/03_CONTRACT.json` |

<!-- PROJECT:END -->

---

## 읽기 3 — 이미 정해 둔 것 (읽고 넘어가기)

### (1) 라우터는 작업을 하지 않는다 (고정)

```text
라우터가 하는 일     상태를 읽는다 → 문자열 하나를 돌려준다. 끝.
라우터가 안 하는 일   파일 쓰기 · 검사기 실행 · 상태 변경 · LLM 호출
```

상태를 바꾸고 싶으면 **노드로 만듭니다.**
원인을 가리는 일(처방 가지 시험지를 풀어 보기)도 라우터가 아니라 **진단 노드**(`diagnose_info` ·
`diagnose_page`)가 합니다. 라우터는 진단이 상태에 적어 둔 `failure_kind` 를 **읽기만** 합니다.

### (2) 라우터 6개 + fan-out 2개, 그 매핑 (고정 — `build.py` 에 이미 배선됨)

그래프는 세 겹입니다 — **루프 골격 14**(노드 14개) · 검사기 바로 뒤의 **진단**(노드 2개) · 진단에서만
갈라지는 **규칙 처방 가지**(등록부 한 줄 = 노드 2개). 라우터가 붙는 자리도 그에 맞춰 바뀌었습니다 —
`route_after_info` · `route_after_page` 는 이제 검사기가 아니라 **진단 노드 뒤**에 붙습니다.

```python
add_conditional_edges("select_cities", fan_out_cities, ["collect_city"])   # fan-out ①
add_edge("check_information", "diagnose_info")                          # ★ 정적 하나 — 판정 다음에 원인
add_conditional_edges("diagnose_info", route_after_info,                # fan-out ②
    {"repair": "repair_city", "repair_country": "repair_country",
     "gate": "human_gate_a",
     **{d.kind: d.fix_node for d in detours.of_loop("A")}})             # ▷ encoding   → fix_encoding
                                                                        #   image_dead → fix_image_dead
add_conditional_edges("human_gate_a", route_after_gate_a,               # fan-out ②
    {"repair": "repair_city", "repair_country": "repair_country",
     "build": "build_page", "stop": END})
add_edge("check_page", "diagnose_page")                                 # ★ 정적 하나
add_conditional_edges("diagnose_page", route_after_page,
    {"retry": "build_page", "gate": "human_gate_b",
     **{d.kind: d.fix_node for d in detours.of_loop("B")}})             # ▷ image_spec → fix_image_spec
add_conditional_edges("human_gate_b", route_after_gate_b,
    {"research": "check_information", "rebuild": "rebuilder",
     "quality": "quality_pass", "done": END})
add_conditional_edges("check_quality", route_after_quality,          # ★ 킷 고정
    {"again": "quality_pass", "build": "build_page",
     "gate": "human_gate_b", "halt": END})
for d in detours.ALL:                                                   # ▷ 처방 가지마다 같은 모양 · ★ 킷 고정
    add_edge(d.fix_node, d.test_node)                                   #   fix_<이름> → test_<이름>
    add_conditional_edges(d.test_node, route_after_detour,
        {"back": d.home, "retry": d.fix_node, "gate": d.gate})
    #   루프 A (encoding · image_dead)  back → check_information · gate → human_gate_a
    #   루프 B (image_spec)             back → check_page        · gate → human_gate_b
```

| 라우터 | 어디 뒤 | 돌려주는 값 | 누가 |
| --- | --- | --- | --- |
| `route_after_info` | `diagnose_info` | 처방 가지 이름(`encoding` · `image_dead`) · `Send`(`repair_city` ×N · `repair_country` ×0\|1) · `gate` | STEP 3 (처방 가지 분기는 킷 고정) |
| `route_after_gate_a` | `human_gate_a` | `Send` · `build` · `stop` | STEP 3 |
| `route_after_page` | `diagnose_page` | 처방 가지 이름(`image_spec`) · `retry` · `gate` | STEP 3 (처방 가지 분기는 킷 고정) |
| `route_after_gate_b` | `human_gate_b` | `research` · `rebuild` · `quality` · `done` | STEP 3 (정성 분기는 킷 고정) |
| `route_after_quality` | `check_quality` | `again` · `build` · `gate` · `halt` | 킷 고정 |
| `route_after_detour` | `test_<이름>` (셋이 같이 씀) | `back`(→ 그 루프의 검사기) · `retry`(→ 같은 fix) · `gate`(→ 그 루프의 게이트) | 킷 고정 |
| `fan_out_cities` | `select_cities` | `Send("collect_city")` × 도시 수 (`inject` 는 첫 도시에만 싣는다) | 킷 고정 |
| `fan_out_repairs` | (라우터 안에서 부름) | `Send("repair_city")` × 다친 도시 · `Send("repair_country")` × 0\|1 | STEP 3 구간 |

함수는 라우터 6개 + fan-out 2개지만 조건부 분기(배선)는 9개입니다 — `fan_out_repairs` 는
라우터 안에서 불려 배선이 따로 없고, `route_after_detour` 하나는 시험 노드 셋에 붙기 때문입니다.

**검사기 → 진단은 정적 간선 하나입니다.** 검사기에 조건부 간선까지 같이 달면 두 갈래가
**동시에** 돕니다 (정적 간선은 if/else 가 아니다 — STEP 4 읽기 3 (1) 과 같은 함정). 그래서 검사기 뒤에는
진단 하나만 두고, 갈림은 진단 뒤에서만 일어납니다. `check_graph_shape.py` 11번 검사가
이 모양을 봅니다.

**처방 가지 키는 등록부에서 옵니다.** `travel_graph/detours/registry.py` 에 한 줄을 적으면
`build.py` 의 매핑과 `edges.ALLOWED` 가 **함께** 늘어납니다 — 그래서 10번 검사가 어긋나지
않습니다. STEP 3 에서는 처방 가지를 늘리지 않습니다. 가지를 더하는 것은 실행 뒤, 로그에 후보가
있을 때만 하는 STEP 6 (조건부)입니다 ([06_DETOUR](06_DETOUR.md)).

**라우터가 매핑에 없는 값을 돌려주면 런타임에 `KeyError`** 입니다.
`check_graph_shape.py` 4번 검사가 이걸 미리 잡습니다.

**선언한 표(`edges.ALLOWED`)와 배선이 어긋나면** 10번 검사가 잡습니다. 10번은 이제 표에
**없는** 라우터(`fan_*` 빼고)도 불일치로 봅니다 — 새 라우터를 달고 표에 안 적으면 빨간불입니다.
처방 가지의 모양(진단에서만 갈라짐 · `fix → test` 정적 하나 · 시험 뒤 `back` · `retry` · `gate` ·
처방 가지 노드가 판정 · 바퀴 · 게이트 칸을 쓰지 않음 · 시험지가 `travel_graph` 를 import 하지 않음)은
11번 **처방 가지 계약**이 봅니다.

**두 라우터는 문자열 대신 `Send` 목록을 돌려줄 수 있습니다.** `route_after_info` 와
`route_after_gate_a` 가 그렇습니다. 그 목록에는 `repair_city` 와 `repair_country` 가
**섞여 나갑니다** — 도시와 국가를 한 걸음에 나란히 고칩니다. `Send` 는 매핑을 거치지
않고 LangGraph 가 직접 처리하므로 `ALLOWED` 표에는 문자열만 적습니다.
매핑에 `repair_city` · `repair_country` 를 적어 두는 이유는
**그림과 구조 검사기가 그 간선을 볼 수 있게** 하기 위해서입니다.

**게이트 B 의 `research` 는 재수집 노드로 바로 가지 않습니다.** `check_information`
으로 보내 다시 센 뒤, (진단 A 를 거쳐) `route_after_info` 가 다친 도시만 고르게 합니다 —
"어느 도시를 고칠까"를 정하는 곳을 하나로 둡니다.

**다섯 번째 라우터(`route_after_quality`)는 교육생이 고치지 않습니다.** 루프 C 의 값은 전부 킷 고정이라
결정이 늘어나지 않습니다. `route_after_gate_b` 의 아래쪽 카운터 분기도 마찬가지입니다 —
고칠 곳은 위쪽 **문장 해석** 부분뿐입니다.

**여섯 번째 라우터(`route_after_detour`)도 교육생이 고치지 않습니다.** 모든 처방 가지가 같은
모양이라 라우터도 하나를 같이 씁니다. `route_after_info` · `route_after_page` 맨 위의
**처방 가지 분기**도 `킷 고정 ▼` 표시 안에 있습니다 — STEP 3 구간을 고쳐도 그 분기는 그대로 둡니다.

### (2-b) ★ 원인을 먼저, 판정을 다음에, 상한은 탈출구로 (고정)

라우터는 **두 칸을 나란히** 읽습니다.

```text
판정  info_verdict · page_verdict   검사기 노드가 쓴다    "기준을 채웠나"
원인  failure_kind                  진단 노드가 쓴다      "무엇이 터졌나 — 정해진 고칠 법이 있나"
```

`route_after_info` · `route_after_page` 는 이 순서로 봅니다.

```text
① 원인   failure_kind 가 이 루프의 처방 가지이고 한도가 남았다   → 처방 가지 이름 (fix_<이름>)  ← 킷 고정 ▼
② 판정   SHORT 가 아니다 (PASS · ERROR)                          → gate
③ 상한   바퀴를 다 썼다 · 같은 오류가 반복된다                   → gate                         ← 탈출구
④ 그 밖  다친 것만 다시                                          → A: Send(repair_*) · B: retry
```

**왜 원인이 판정보다 먼저인가.** 처방 가지가 보는 결함 중에는 **검사기가 세지 않는 것**이
있습니다. 깨진 글자(`encoding`)는 칸이 채워져 있으니 개수로는 멀쩡하고, 원본 크기
사진(`image_spec`)은 검사기가 사진이 "있는가"만 보므로 통과합니다. 판정을 먼저 보면
PASS 에서 곧장 게이트로 가고, **이 결함은 한 번도 고쳐지지 않습니다.** 그래서 판정이
**PASS 여도** 진단이 처방 가지를 골랐고 처방 한도가 남았으면 그쪽으로 갑니다.
검사기가 세는 결함이라도(`image_dead` — 죽은 사진 주소) 정해진 고칠 법이 있으면 먼저
씁니다. 재수집(LLM)에 맡기면 같은 식으로 주소를 또 지어냅니다.

**그래도 무한히 돌지 않습니다.** 처방 가지마다 처방 한도(`detour_limit` = 2)가 있고, 한도를 다 쓴
가지는 진단이 고르지 않으며 라우터도 ① 을 건너뜁니다. 시험 뒤의 `route_after_detour` 도
같은 모양입니다 — 합격(`back`)을 먼저, 한도 안이면 `retry`, 한도 끝이면 `gate`.

**처방 가지는 바퀴를 쓰지 않습니다.** 합격하고 검사기로 돌아온 방문은 `loop_a_iter` ·
`loop_b_iter` 로 세지 않고 `same_error_count` 도 올리지 않습니다 (history 에
"(처방 가지에서 복귀 — 바퀴를 쓰지 않음)"). 그래야 ③ 의 상한이 루프 킷과 같은 뜻 —
검사 횟수(첫 수집 1, 재수집 · 재생성마다 +1) — 으로 남습니다.

`failure_kind` 도 `G-라우터판단` B 를 따릅니다 — 등록부의 이름만 들어가는 **허용값이 닫힌
칸**입니다. 진단이 함께 남기는 증상 문장(`failure_evidence`)은 사람에게 보여 주는 글이라
라우팅에 쓰지 않습니다.

> ① 을 지우면 처방 가지가 **한 번도 켜지지 않는데** 배선(매핑)은 그대로라 4 · 10번은 통과합니다.
> 그래서 **11번(처방 가지 계약)** 이 따로 봅니다 — 진단 뒤 라우터가 `failure_kind` 와 `detour_limit` 을
> 읽는가. (`route_after_gate_b` 의 정성 분기는 12행이 전부 통과하고 회귀 테스트만 잡습니다.)

### (3) ★ LLM·사람의 자유 문장을 제어에 쓰지 마세요 (고정)

```python
# 위험 — 이렇게 쓰면 안 된다 (G-라우터판단 A)
note = state.get("gate_note")          # 사람이 쓴 자유 문장
if "더" in note:
    return "research"
#  "더 모으지 말고 그냥 진행" 이라고 쓰면 '더'가 걸려 재수집으로 갑니다.

# 안전 — 킷은 이렇게 되어 있다 (G-라우터판단 B · 권장)
answer = state.get("gate_a_answer")    # 허용값이 정해진 필드
if answer == "more":
    return fan_out_repairs(state) or "build"   # 다친 도시만. 없으면 헛바퀴 대신 진행
```

> 검사기는 라우터의 **소스 텍스트**를 봅니다. 그래서 `gate_note` 라는 이름을
> **주석에 적어도** 5번 검사에 걸립니다. 실수가 아니라 의도된 엄격함입니다.
> 진단이 남기는 증상 문장 `failure_evidence` 도 같은 목록에 있습니다 — 라우터가 읽는
> 원인 칸은 `failure_kind` 하나뿐입니다.

> **그래프 엔지니어링은 자율성을 주되, 이동 가능한 경로와 통과 조건을
> 검증 가능하게 제한하는 기술입니다.**

라우팅 키(`action`)와 자유 문장(`note`)을 **분리**하는 일은 `nodes.normalize_gate()` 가
이미 하고 있습니다. 라우터는 정규화된 `gate_*_answer` 만 보면 됩니다.

### (3-b) ★ 종료 조건에는 두 모양이 있습니다 (고정)

루프 A·B 와 루프 C 는 **닫히는 방식이 다릅니다.** 라우터도 그래서 다르게 생겼습니다.

```text
통과선 루프 (A · B)      검사기가 통과할 때까지 돈다
    verdict 를 먼저 보고, 상한은 **탈출구**로 본다   (처방 가지로 갈 원인은 그보다 앞 — 2-b)
    if verdict == "PASS":            return "gate"
    if iter >= limit:                return "gate"      ← 탈출구
    if verdict == "SHORT":           return "retry"

고정 예산 루프 (C)       정해진 3회를 채울 때까지 돈다
    카운터를 **정상 경로**로 본다.  상한이 아니라 목표다
    if pass_no >= passes_required:   return "gate"      ← 목표 달성
    return "again"                                      ← 아직 남았다
```

| | 루프 A·B 의 상한 | 루프 C 의 3회 |
| --- | --- | --- |
| 뜻 | **최대** — 여기까지만 돈다 | **최소이자 최대** — 꼭 3번 돈다 |
| 통과 조건 | 검사기 exit 0 | 3회를 규율대로 기록 |
| 라우터가 보는 것 | `*_verdict` + `*_limit` | **`*_pass` + `*_passes_required`** |

`check_graph_shape.py` 에 검사가 두 개 늘어난 것이 이 때문입니다.

```text
7번  순환에 종료 조건이 하나라도 있는가        (기존)
9번  고정 예산 순환이 **카운터와 그 상한을 함께** 읽는가   (신규)
```

`verdict` 만 보는 라우터로 고정 예산 순환을 닫으려 하면 7번은 통과하고 9번이 잡습니다.

**처방 가지의 순환은 통과선 모양입니다.** `fix ↔ test` 재시도와 `진단 → fix → test → 검사기`
복귀는 `detour_verdict` 를 먼저 보고 `detour_limit` 을 탈출구로 봅니다 — 루프 A·B 와 같습니다.
그래서 모양은 여전히 둘이고, 검사가 이렇게 나눠 봅니다.

```text
7번       처방 가지 순환도 본다. detour_limit 이 종료 조건 목록에 들어 있다.
          edges.py 에 없는 라우터는 소스를 못 읽으므로 "상한 없음"으로 본다
11번 (g)  시험 뒤 라우터가 detour_limit 을 **실제로** 읽는가
11번 (h)  진단 뒤 라우터가 failure_kind · detour_limit 을 읽는가 (`킷 고정 ▼` 분기가 살아 있나)
          (7번은 'PASS' 글자만 있어도 종료 조건으로 치므로 처방 한도는 여기서 따로 본다)
```

구조 검사는 이제 **검사행 12개**(1~11 + 6b)입니다. 11번 **처방 가지 계약**은 끝에 덧붙인 것이라
기존 번호는 그대로입니다.

### (4) 실패 라우팅 7종 — 루프에서 그대로 이식 (고정)

```text
CODE_ERROR               → RETRY        그 노드만 다시
INFORMATION_INSUFFICIENT → RESEARCH     부족한 칸만 다시
SPEC_CONFLICT            → REVISE_SPEC  그래프 밖으로 (사람이 명세를 고침)
TEST_ERROR               → HITL         human_gate 로
ENVIRONMENT_ERROR        → HITL
PERMISSION_ERROR         → HITL
UNKNOWN_ERROR            → STOP         END 로 직행
```

이 표는 **루프 킷에서 이미 고정된 것**입니다. 다시 정하지 않습니다.
그래프에서는 `ERROR` 판정이 곧 `HITL` 이므로 게이트로 보냅니다.

**이 표의 일부가 이제 실제 배선입니다.** 루프에서는 7종이 문서(분류표)로만 있었고,
실제로는 모든 실패를 "한 바퀴 더"로 뭉쳐 처리했습니다. 그래프에서는 다음 행동마다
간선이 있습니다.

```text
RETRY        route_after_page 의 retry (build_page) · route_after_detour 의 retry (같은 fix_<이름>)
RESEARCH     route_after_info 의 Send (repair_city · repair_country — 부족한 칸만)
HITL         각 라우터의 gate (ERROR · 상한 · 처방 한도 끝)
STOP         route_after_gate_a 의 stop · route_after_quality 의 halt → END
REVISE_SPEC  간선 없음 — 그래프 밖 (사람이 명세를 고친다)
```

**두 축을 구분합니다 — `failure_type`(7종)과 `failure_kind`(처방 가지 이름).**

| | `failure_type` 7종 | `failure_kind` |
| --- | --- | --- |
| 무엇 | 루프에서 이식한 **넓은** 분류 — 그대로 둔다 | 진단 노드가 쓰는 **더 좁은** 분류 |
| 값 | 위 표의 7개 | `""` 또는 등록된 처방 가지 이름 |
| 어디에 | 문서 · 분류표 (상태 칸이 아니다) | 상태 칸 — **라우터가 읽는 원인 칸** |
| 누가 늘리나 | 늘리지 않는다 (고정) | 등록부 한 줄 (STEP 6 · 조건부 — 로그에 후보가 있을 때만) |

| `failure_kind` | 넓게 보면 (`failure_type`) | 왜 처방 가지인가 (어디서 태어났나) |
| --- | --- | --- |
| `image_dead` | INFORMATION_INSUFFICIENT 중 "정보는 있는데 주소가 틀림" | 재수집(LLM)은 같은 식으로 주소를 지어낸다 — 정해진 절차로 고친다 (루프 킷 실행 로그: 해시 두 글자를 지어내 11장 전부 죽음) |
| `encoding` | CODE_ERROR / ENVIRONMENT_ERROR 쪽 (파이프가 글자를 망침) | 검사기가 세지 않는 결함 — 판정 PASS 여도 있다 (원인과 고칠 법이 이미 알려진 실패 축: Windows cp949 · 현지 글자 파일명 — 로그 실측 전에 미리 구축) |
| `image_spec` | CODE_ERROR (화면 규격) | 검사기는 사진이 "있는가"만 본다 (실습생 게이트 입력: 원본 크기 사진이 서랍을 뚫음) |

넓은 고칠 법(예: `RESEARCH` — 재수집(LLM)) 안에 **정해진 좁은 고칠 법**(예: `image_dead` 처방 가지)이
있으면 좁은 것을 먼저 씁니다. 그것이 (2-b) 의 "원인을 먼저" 입니다.

---

## 읽기 4 — 내가 결정할 질문

<!-- FIXED:BEGIN -->

| 결정 ID | 질문 | 이 값이 바꾸는 것 |
| --- | --- | --- |
| `G-라우터판단` | 라우터가 **무엇을** 보고 고르나? | 제어의 재현성 |
| `G-상한처리` | 상한에 걸리면 어떻게 하나? | 무한 루프가 나는지 |

**쉬운 선택지**

| 결정 ID | A | B | C | 권장 |
| --- | --- | --- | --- | --- |
| `G-라우터판단` | 자유 문장을 직접 본다 | **허용값이 정해진 필드만 본다** | LLM에게 노드 이름을 고르게 | **B** |
| `G-상한처리` | 그냥 멈춘다 (END) | **게이트로 보내 사람이 정한다** | 상한 없이 계속 돈다 | **B** |

```text
G-라우터판단 A → 제어 흐름이 문장 해석에 좌우된다. check_graph_shape 5번이 잡는다
G-라우터판단 C → 제어 흐름이 확률적이 된다. 같은 입력에 다른 경로가 나온다
G-상한처리   A → 못 채운 칸이 있는 채로 조용히 끝난다. 가장 나쁜 실패다
G-상한처리   C → 무한 루프. check_graph_shape 7번이 ERROR 로 잡는다
```

> `G-상한처리` B가 왜 좋은가 — **상한에 걸린 것은 실패가 아니라 판단이 필요한 상황**입니다.
> 인터넷에 없는 사진은 세 바퀴를 더 돌아도 없습니다. 그때 "넘어갈지"를 정하는 것은 사람입니다.

<!-- FIXED:END -->

---

## 읽기 5 — 내 답 적기

<!-- ANSWERS:BEGIN -->

### `G-라우터판단`
- 고른 것: B (허용값이 정해진 필드만 본다)
- 이유: 라우터가 gate_a_answer·*_verdict·failure_kind 같은 닫힌 값만 읽어야 같은 입력에 같은 경로가 나온다. 권장값 그대로.

### `G-상한처리`
- 고른 것: B (게이트로 보내 사람이 정한다)
- 이유: 상한에 걸린 것은 실패가 아니라 판단이 필요한 상황이다. 조용히 끝내거나 무한히 돌지 않는다. 권장값 그대로.

<!-- ANSWERS:END -->

---

## 읽기 6 — Claude가 정리한 결과

<!-- PROJECT:BEGIN -->

| 결정 ID | 확정 값 | 고른 이유 | 승인 시각 |
| --- | --- | --- | --- |
| `G-라우터판단` | B — 허용값이 정해진 필드만 본다 | 문장 해석에 제어가 좌우되지 않고 같은 입력에 같은 경로가 나온다 | 2026-10-23 |
| `G-상한처리` | B — 게이트로 보내 사람이 정한다 | 상한에 걸린 것은 판단이 필요한 상황이다 | 2026-10-23 |

**권장값을 골랐다면 코드는 이미 이 모양입니다.** 아래는 붙여 넣으라는 뜻이 아니라
**지금 파일에 무엇이 있는지**를 옮겨 적은 것입니다. 다른 값을 골랐을 때만 고칩니다.

> ⚠ **아래 발췌에는 `fan_out_repairs` 가 빠져 있습니다.** 그 함수도 `STEP 3 ▼▼▼` ~
> `▲▲▲` 구간 안에 있고 두 라우터가 그것을 부릅니다. 구간을 통째로 갈아 끼우면
> 재수집이 사라지므로, **고칠 때는 해당 함수만** 손대십시오.
> **처방 가지 분기(`킷 고정 ▼` ~ `▲`)는 발췌에 넣어 두었습니다.** 어떤 값을 골라도 그 분기는
> 그대로 둡니다. 그것이 쓰는 `detours` 임포트와 `_tries` 는 구간 위쪽에 있습니다.
(권장값 B·B 기준. 다른 값을 골랐으면 Claude 가 그 값에 맞게 고쳐 씁니다.)

```python
def route_after_info(state) -> str:
    """진단 A(diagnose_info) 뒤. **원인 → 판정 → 상한 → 무진전** 순서로 본다."""
    # ---- 킷 고정 ▼ 처방 가지 — 진단이 고른 원인이 있으면 **판정보다 먼저** --------
    kind = state.get("failure_kind") or ""
    if kind in detours.kinds("A") and _tries(state, kind) < (state.get("detour_limit") or 0):
        return kind                                      # fix_<이름> 으로
    # ---- 킷 고정 ▲ ---------------------------------------------------------

    if state.get("info_verdict") != "SHORT":
        return "gate"                                    # 사람에게 넘긴다 (PASS · ERROR)
    if (state.get("loop_a_iter") or 0) >= (state.get("loop_a_limit") or 0):
        return "gate"                                    # 상한 도달
    if (state.get("same_error_count") or 0) >= (state.get("same_error_limit") or 0):
        return "gate"                                    # 제자리걸음
    return fan_out_repairs(state) or "gate"              # 다친 도시만 Send


def route_after_gate_a(state) -> str:
    """게이트 A 뒤. **허용값이 정해진 필드만** 본다. 문장은 보지 않는다."""
    answer = state.get("gate_a_answer")
    if answer == "stop":
        return "stop"
    if answer == "more":
        return fan_out_repairs(state) or "build"         # 고칠 데가 없으면 진행
    return "build"                                       # proceed (권장)


def route_after_page(state) -> str:
    """진단 B(diagnose_page) 뒤. A와 같은 순서."""
    # ---- 킷 고정 ▼ 처방 가지 — 진단이 고른 원인이 있으면 **판정보다 먼저** --------
    kind = state.get("failure_kind") or ""
    if kind in detours.kinds("B") and _tries(state, kind) < (state.get("detour_limit") or 0):
        return kind
    # ---- 킷 고정 ▲ ---------------------------------------------------------

    if state.get("page_verdict") != "SHORT":
        return "gate"
    if (state.get("loop_b_iter") or 0) >= (state.get("loop_b_limit") or 0):
        return "gate"
    return "retry"                                       # 페이지만 다시 만든다


def route_after_gate_b(state) -> str:
    """게이트 B 뒤. 사람이 그래프의 어느 지점으로 되돌릴지 고른다."""
    answer = state.get("gate_b_answer")
    if answer == "research":
        return "research"          # check_information 으로. 거기서 다친 도시만 고른다
    if answer == "rebuild":
        return "rebuild"           # rebuilder 로. note 에 적은 지시대로 고친다

    # ---- 킷 고정 ▼ 게이트 B 는 두 번 섭니다. **이 분기를 지우지 마십시오** ------
    #   정성 3회 전  →  "quality" 로 보내 루프 C 를 시작한다
    #   정성 3회 후  →  "done" 으로 끝낸다
    #
    #   지우면 라우터가 "quality" 를 영영 못 돌려주고 `quality_pass` ·
    #   `check_quality` 가 **한 번도 실행되지 않습니다.** 배선은 그대로라
    #   `check_graph_shape.py` 도 통과합니다 — 검사기가 못 잡는 종류입니다.
    if state.get("quality_pass", 0) >= state.get("quality_passes_required", 3):
        return "done"
    return "quality"
    # ---- 킷 고정 ▲ ---------------------------------------------------------
```

<!-- MACHINE:BEGIN -->
```json
{
  "step": 3,
  "produces": "travel_graph/edges.py",
  "decisions": {
    "G-라우터판단": "B",
    "G-상한처리": "B"
  },
  "fixed": {
    "routers": {
      "fan_out_cities": {"->": "collect_city (Send · 고른 도시 전부)"},
      "fan_out_repairs": {"->": "repair_city (Send · 지적된 도시만) + repair_country (Send · 0 또는 1)"},
      "route_after_info": {"repair": "repair_city", "repair_country": "repair_country",
                          "gate": "human_gate_a",
                          "encoding": "fix_encoding", "image_dead": "fix_image_dead"},
      "route_after_gate_a": {"repair": "repair_city", "repair_country": "repair_country",
                            "build": "build_page", "stop": "END"},
      "route_after_page": {"retry": "build_page", "gate": "human_gate_b",
                           "image_spec": "fix_image_spec"},
      "route_after_gate_b": {"research": "check_information", "rebuild": "rebuilder",
                             "quality": "quality_pass", "done": "END"},
      "route_after_quality": {"again": "quality_pass", "build": "build_page",
                              "gate": "human_gate_b", "halt": "END"},
      "route_after_detour": {"back": "그 루프의 검사기 (A: check_information · B: check_page)",
                             "retry": "같은 fix_<이름>",
                             "gate": "그 루프의 게이트 (A: human_gate_a · B: human_gate_b)"}
    },
    "router_attached_to": {
      "fan_out_cities": "select_cities",
      "route_after_info": "diagnose_info",
      "route_after_gate_a": "human_gate_a",
      "route_after_page": "diagnose_page",
      "route_after_gate_b": "human_gate_b",
      "route_after_quality": "check_quality",
      "route_after_detour": "test_encoding · test_image_dead · test_image_spec (등록된 처방 가지마다)"
    },
    "router_count": "라우터 6개 + fan-out 2개 · 조건부 분기(배선) 9개",
    "student_routers": ["route_after_info", "route_after_gate_a", "route_after_page", "route_after_gate_b"],
    "kit_fixed_parts": "route_after_quality · route_after_detour 전체, route_after_info · route_after_page 맨 위의 처방 가지 분기, route_after_gate_b 의 정성 분기",
    "static_checker_to_diagnose": ["check_information -> diagnose_info", "check_page -> diagnose_page"],
    "detour_keys_source": "처방 가지 이름 키는 travel_graph/detours/registry.py 에서 온다 (루프 A → route_after_info, 루프 B → route_after_page)",
    "detour_limit": "처방 한도 2 (travel_graph/detours/__init__.py 의 LIMIT). 사람이 more · research · rebuild 를 고르면 처방 가지 횟수가 0 으로",
    "router_order": "원인을 먼저(failure_kind · 한도 안), 판정을 다음에, 상한은 탈출구로",
    "allowed_source_of_truth": "travel_graph/edges.py 의 ALLOWED (처방 가지 이름은 등록부에서 읽어 배선과 함께 늘어난다). check_graph_shape 10번이 배선과 맞춰 본다 — ALLOWED 에 없는 라우터(fan_* 빼고)도 불일치로 잡는다",
    "router_rule": "라우터는 상태를 읽고 문자열 하나 또는 Send 목록을 돌려준다. 작업하지 않는다",
    "failure_routing": {
      "CODE_ERROR": "RETRY",
      "INFORMATION_INSUFFICIENT": "RESEARCH",
      "SPEC_CONFLICT": "REVISE_SPEC",
      "TEST_ERROR": "HITL",
      "ENVIRONMENT_ERROR": "HITL",
      "PERMISSION_ERROR": "HITL",
      "UNKNOWN_ERROR": "STOP"
    },
    "failure_kind_axis": {
      "what": "진단 노드가 쓰는 더 좁은 분류. 값은 \"\" 또는 등록된 처방 가지 이름. failure_type 7종은 그대로 둔다",
      "image_dead": "INFORMATION_INSUFFICIENT 중 정보는 있는데 주소가 틀림",
      "encoding": "CODE_ERROR / ENVIRONMENT_ERROR 쪽 (파이프가 글자를 망침)",
      "image_spec": "CODE_ERROR (화면 규격)"
    },
    "forbidden": "자유 문장(gate_note · failure_evidence)을 라우팅에 쓰지 않는다"
  },
  "inherited": {
    "loop_a_limit": 3,
    "loop_b_limit": 3,
    "same_error_limit": 2
  }
}
```
<!-- MACHINE:END -->

<!-- PROJECT:END -->

---

## 읽기 7 — 이 STEP이 끝나면 무엇이 진행되는가

| 항목 | 내용 |
| --- | --- |
| **지금 코드가 만들어지나?** | **권장값(B · B)이면 아니오** — `travel_graph/edges.py` 는 이미 그 모양입니다. 다른 값을 고르면 `STEP 3 ▼▼▼` 구간의 **해당 함수만** 바뀝니다 (그 안의 처방 가지 분기 · 정성 분기와 `route_after_quality` · `route_after_detour` 는 그대로). |
| **Claude가 하는 일** | ① 답 2개 기록 → ② (다른 값을 골랐을 때만) `edges.py` 의 해당 함수 수정 — 구간을 통째로 갈아 끼우지 않는다 → ③ 구조 검사 재실행 |
| **바뀌는 파일** | `specs/03_EDGE_CONDITION.md` · `specs/00_DECISION_LOG.md` · (다른 값을 골랐을 때만) `travel_graph/edges.py` |
| **바뀐 것을 확인하는 법** | `python scripts/check_graph_shape.py` → **검사행 12개 전부 PASS** — 라우터를 보는 4 · 5 · 7 · 10 · 11번이 이 STEP 의 몫입니다. 다른 값을 골랐으면 고친 뒤에도 PASS 인지 봅니다 |

---

## 읽기 8 — 완료 확인과 다음 명령

- [ ] 라우터가 `gate_note`(자유 문장)를 보지 않는다
- [ ] 순환에 참여하는 라우터가 상한(`loop_*_limit`)을 읽는다
- [ ] 라우터가 돌려주는 값이 전부 매핑 안에 있다
- [ ] `check_graph_shape.py` 의 4·5·7·10·11번이 `OK` 다 (3번 reducer 는 STEP 4 에서 다룬다)
- [ ] `route_after_info` · `route_after_page` 맨 위의 처방 가지 분기(`킷 고정 ▼`)가 그대로 있다
- [ ] 상태가 `APPROVED`다

```bash
python scripts/check_graph_shape.py
python scripts/validate_specs.py --step 3
```

<!-- STATUS:BEGIN -->
STATUS: APPROVED
<!-- STATUS:END -->

```text
STEP 4 진행해줘
```
