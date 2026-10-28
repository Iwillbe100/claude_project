---
name: graph-spec-builder
description: STEP 1~5 명세를 질문·답변으로 채우고, 권장값이면 코드가 이미 그 모양인지 확인만 하고, 다른 값을 골랐을 때만 그 STEP이 지정한 코드 한 곳을 고친다(STEP 2 는 코드 변경 없음). "STEP 3 진행해줘", "다음 STEP 진행", "STEP 명세 작성" 같은 요청에서 사용한다. 각 STEP의 결정 2~3개만 묻는다.
user-invocable: true
argument-hint: "[STEP 번호]"
---

# graph-spec-builder — STEP 진행자

## 활성화 조건

교육생이 특정 STEP 을 진행하자고 할 때. 번호가 없으면 아직 `APPROVED` 가 아닌
가장 앞 STEP 을 제안한다.

---

## 절대 규칙 9가지

1. **`읽기 4`(`FIXED` 마커) 안의 질문 문장을 절대 고치거나 지우지 않는다.**
2. **질문을 새로 추가하지 않는다.** 결정은 STEP당 2~3개, 전체 **13개로 고정**이다.
   (STEP 6 처방 가지 추가(조건부)에는 결정이 없다 — 13개 그대로다.)
3. `읽기 3`(이미 정해 둔 것)은 **질문하지 않는다.** 요약해서 알려 주고 넘어간다.
4. **그 STEP 이 지정한 파일 한 곳만 고친다.** 다른 파일을 "겸사겸사" 고치지 않는다.
5. **검사 스크립트를 만들거나 고치지 않는다.** `scripts/` 는 킷 소유다.
   (예외인 처방 가지 시험지 `scripts/detour_tests/test_<이름>.py` 는 STEP 6(조건부)에서
   `graph-detour-builder` 가 다룬다. 이 스킬에서는 만들지 않는다.)
6. **`graph/03_CONTRACT.json` 을 절대 고치지 않는다.** 고치면 루프판과 비교가 깨진다.
7. **STEP 4에서 reducer 를 먼저 알려 주지 않는다.** 아래 "STEP 4 특별 절차"를 따른다.
8. 필수 결정이 비어 있으면 `STATUS` 를 `APPROVED` 로 바꾸지 않는다.
9. 답을 다 받은 뒤에는 **반드시 `읽기 7`을 읽어 준다.**

---

## STEP별 코드 변경 대상 (이것 말고는 건드리지 않는다)

**★ 킷은 완성된 상태로 배포된다.** 코드는 이미 돌아간다. 그러므로 각 STEP 이 하는
일은 "빈칸을 채워 넣기"가 아니라 **읽기 → 결정 → 장부 기록 → 검사기 확인** 이다.
**권장값을 고르면 코드 변경이 없다.** 다른 값을 골랐을 때만 아래 파일을 고친다.

| STEP | 문서 | 다른 값을 골랐을 때 고치는 곳 | 확인 |
| --- | --- | --- | --- |
| 1 | `specs/01_STATE_SCHEMA.md` | `travel_graph/state.py` 필드 목록 | `check_graph_readiness.py` |
| 2 | `specs/02_NODE_BOUNDARY.md` | **없음** (읽고 승인만) | — |
| 3 | `specs/03_EDGE_CONDITION.md` | `edges.py` 의 `STEP 3 ▼▼▼` ~ `▲▲▲` 안 **해당 함수만** (`킷 고정 ▼` 구간 제외) | `check_graph_shape.py` |
| 4 | `specs/04_PARALLEL.md` | `state.py` reducer 3줄 (함수 2개 + `operator.add`). 권장값이면 읽기 1 에서 뗀 reducer 를 되붙이면 끝 | `check_graph_shape.py` 3번 |
| 5 | `specs/05_CHECKPOINT.md` | `nodes.py` 게이트 2개 | `check_graph_readiness.py` → `READY` (exit 0) |

> ⚠ **구간을 통째로 갈아 끼우지 않는다.** `STEP 3` 구간에는 `fan_out_repairs` 가
> 함께 들어 있고, `route_after_gate_b` 에는 루프 C 를 여는 **킷 고정 분기**가 있다.
> `route_after_info` · `route_after_page` 맨 앞에는 진단이 고른 원인을 판정보다 먼저 보는
> **처방 가지 분기**(`킷 고정 ▼` ~ `▲`)가 있다. 통째 교체는 이것들을 조용히 지운다 —
> 정성 분기를 지우면 `check_graph_shape.py` 12행이 전부 PASS 다 — 회귀 테스트만 잡는다.
> 처방 가지 분기를 지우면 11번(처방 가지 계약)이 빨간불을 낸다 — 진단 뒤 라우터가 `failure_kind` ·
> `detour_limit` 을 읽는지 본다. `킷 고정 ▼` ~ `▲` 안은 권장값이 아닌 답을
> 골랐을 때도 건드리지 않는다.

> **STEP 1 에서 필드를 고를 때도 진단 · 처방 가지 칸 6개는 킷 고정이다** — `inject` ·
> `failure_kind` · `failure_evidence` · `detour_attempts` · `detour_limit` · `detour_verdict`.
> 지우면 라우터가 원인을 못 읽는다. `check_graph_readiness.py` 가 `diagnose_fields` 묶음(뒤의 5개)과
> `input_schema` 묶음(`inject`)으로 지킨다.

> **"먼저 실패를 보여 주기"는 이제 되돌려 보는 방식이다.** 킷이 완성본이므로,
> STEP 4 는 reducer 를 잠깐 떼어 검사기가 무엇을 말하는지 보게 한 뒤 되돌린다.

---

## 실행 순서

1. `CLAUDE.md` · `PROJECT_MEMORY.md` · `graph/01_HANDOFF.md` · 해당 STEP 문서를 읽는다.
2. 앞 STEP 이 `APPROVED` 인지 확인한다. 아니면 알리고 계속할지 묻는다.
3. 이 STEP 의 목적을 **3줄 이내**로 설명한다.
4. `읽기 3` 을 **요약해서 먼저** 알려 준다. "여기는 고민 안 하셔도 됩니다"를 분명히 한다.
5. `읽기 4` 의 질문을 **한 번에 2~3개** 제시한다. A/B/C 와 권장값, 그리고
   **각 선택지가 무엇을 망치는지**를 함께 준다.
6. 답이 오면 `읽기 5`(`ANSWERS`) 에 적는다.
7. `읽기 6`(`PROJECT` + `MACHINE`) 을 **실제 값**으로 채운다. 선택지 기호(A/B/C)가 아니다.
8. **`읽기 6` 의 코드와 위 표의 파일을 맞춘다.**
   - 권장값이면 파일이 **이미 그 모양인지 확인만** 한다. `읽기 6` 의 코드는 발췌 · 축약이라
     (예: STEP 3 은 `fan_out_repairs` 가 빠져 있고, STEP 5 는 history 줄을 줄였다) **파일에 덮어 붙이지 않는다.**
   - 다른 값을 골랐으면 **해당 함수만** 그 값에 맞게 고치고, **왜 그렇게 되는지 한 줄로 설명**한다. 창작하지 않는다.
9. `specs/00_DECISION_LOG.md` 1번 표를 갱신한다.
10. 뒤 STEP 의 `읽기 2` 표와 `inherited` 블록을 갱신한다.
11. `STATUS: APPROVED` 로 바꾸고 검사를 돌린다.

    ```bash
    python scripts/validate_specs.py --step N
    python scripts/check_graph_shape.py          # STEP 3·4 뒤에는 반드시
    ```

    `--step N` 을 빼지 않는다. 인자 없이 돌리면 STEP 6 까지 보는데, STEP 6 은 조건부(로그에 처방 가지
    후보가 있을 때만)라 하지 않았으면 SHORT(exit 2)로 남는다 — 정상이다. STEP 5 뒤 실행 준비는
    `check_graph_readiness.py` 의 `READY` 로 판정한다 (STEP 6 을 요구하지 않는다).
12. `읽기 7` 을 그대로 읽어 준다.

---

## ★ STEP 4 특별 절차 — 순서를 바꾸지 않는다

```text
0  킷은 완성본이라 그냥 돌리면 오류가 안 난다. state.py 에서 history 의 reducer 를 잠깐 뗀다
       history: Annotated[list[str], operator.add]   →   history: list[str]
1  "먼저 한 번 돌려 보시죠" 라고 말하고 아래를 실행하게 한다
       python scripts/run_once.py --mode replay --auto stop
2  InvalidUpdateError 가 난다. **그 메시지를 그대로 보여 준다.**
       At key 'history': Can receive only one value per step.
       Use an Annotated key to handle multiple values.
3  "왜 이럴까요?" 를 묻는다. 답은 "같은 걸음에 두 노드가 같은 칸에 썼기 때문"
4  그제서야 읽기 4 의 질문을 낸다
5  뗀 reducer 를 되붙이고 다시 돌린다. 이번엔 막힘 없이 게이트 B 까지 돈다
       python scripts/run_once.py --mode replay --auto proceed
```

> `specs/04_PARALLEL.md` 읽기 1 은 `cities` 의 reducer 를 떼어 `check_graph_shape.py` 3번과
> `At key 'cities'` 를 보여 준다. 어느 쪽을 떼도 되지만 **반드시 되붙이고** 3번이 OK 인지 확인한다.

> 확인 실행에서 게이트 B 에 `done` 을 주지 않는다 (`--auto proceed,done` 금지). `done` 은 정성 3회를
> 시작하고, 정성은 `replay` 에서도 `claude -p` 로 실제 판정을 한다 (6~12분). `run_once.py` 는 답이
> 없으면 그 게이트에서 끝내므로 `--auto proceed` 면 게이트 B 에서 멈춘다.

**reducer 를 먼저 알려 주면 왜 필요한지 몸으로 겪지 못한다.**

`G-병렬충돌` 은 `operator.add` 가 정답이 아니다. `repair_city` 가 같은 도시를
다시 돌려주므로 `add` 면 중복이 쌓인다. `city_failures` 는 한 발 더 가서
**고쳐진 줄이 지워져야** 하므로 단순 upsert 도 답이 아니다. 교육생이 A(add)를 고르면 **그 사실을 알려 주고**
직접 다시 고르게 한다. 답을 대신 바꾸지 않는다.

---

## 질문할 때의 형식

```text
STEP 3 은 "라우터가 무엇을 보고 다음 노드를 고를지" 를 정합니다.
루프의 if 문이 여기로 옵니다. 배선은 이미 다 돼 있으니 조건만 정하시면 됩니다.

이미 정해 둔 것 (고민 X)
  - 읽고 고칠 수 있는 라우터는 4개이고, 그 매핑은 build.py 에 배선돼 있습니다
    (route_after_info · route_after_gate_a · route_after_page · route_after_gate_b)
  - 나머지 라우터 둘 — route_after_quality(루프 C) · route_after_detour(처방 가지 시험 뒤) — 는
    **킷 고정**입니다. 결정이 늘지 않습니다
  - 네 라우터 안의 처방 가지 분기와 게이트 B 의 정성 분기도 `킷 고정 ▼` 구간입니다.
    라우터는 원인(진단이 쓴 failure_kind)을 먼저, 판정을 다음에, 상한은 탈출구로 봅니다
  - 실패 라우팅 7종은 루프 킷에서 그대로 가져옵니다 (일부는 이제 진단 → 처방 가지로 실제 배선됨)

질문 ① G-라우터판단 — 라우터가 무엇을 보고 고를까요?
  A 자유 문장을 직접 본다        → "더 모으지 말고 진행"에서 '더'가 걸린다
  B 허용값이 정해진 필드만 본다   ← 권장
  C LLM에게 노드 이름을 고르게    → 같은 입력에 다른 경로가 나온다

질문 ② G-상한처리 — 상한에 걸리면?
  A 그냥 멈춘다                  → 못 채운 칸이 있는 채로 조용히 끝난다
  B 게이트로 보내 사람이 정한다    ← 권장
  C 상한 없이 계속 돈다           → 무한 루프
```

- 한 번에 질문을 쏟아붓지 않는다.
- 답하기 어려워하면 **예시를 하나** 보여 준다.
- "그냥 권장값으로 해 주세요" 라고 하면 그렇게 하되, **왜 그게 권장인지 한 줄**은 말한다.

---

## 끝나면 넘기는 곳

| 상황 | 다음 |
| --- | --- |
| STEP 1~4 완료 | 다음 STEP (`graph-spec-builder` 재호출) |
| STEP 5 완료 | `graph-run` |
| 이미 승인된 결정을 바꾸자고 함 | `spec-sync` |
| STEP 6 (처방 가지 추가 — **조건부 · 실행 뒤 · 로그에 후보가 있을 때만**) | `graph-detour-builder`. 이 스킬은 STEP 1~5 만 다룬다 |

> **STEP 6 은 이 스킬이 진행하지 않는다.** 결정이 없고(13개 그대로), 실행을 본 뒤 실패 기록
> 보고서(`failure_report.py`)의 ③ · ③-2 에 처방 가지 후보가 있을 때만 하기 때문이다.
> **STEP 6 은 필수가 아니다** — STEP 5 승인 뒤 실행하고, 후보가 없으면 거기서 끝난다.
> "STEP 6 진행해줘" 가 오면 STEP 5 가 `APPROVED` 이고 그래프를 한 번 돌려 봤는지 확인한 뒤
> `graph-detour-builder` 로 넘긴다 (후보가 있는지는 그 스킬이 보고서로 확인한다).
