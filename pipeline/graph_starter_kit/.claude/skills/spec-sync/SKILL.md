---
name: spec-sync
description: 이미 승인된 결정을 바꿀 때 영향 범위를 계산하고 문서와 코드를 함께 동기화한다. "G-병렬충돌을 바꾸고 싶어", "라우터 조건을 다시 정하자", "STEP 3 결정을 수정" 같은 요청에서 사용한다.
user-invocable: true
argument-hint: "[결정 ID]"
---

# spec-sync — 결정 변경 동기화

## 활성화 조건

이미 `APPROVED` 인 STEP 의 결정을 바꾸자고 할 때. 아직 `DRAFT` 면
`graph-spec-builder` 로 넘긴다 (그냥 채우면 되기 때문).

---

## 절대 규칙 5가지

1. **승인된 결정을 조용히 덮어쓰지 않는다.** 이전 값·새 값·이유·영향 범위를 먼저 보여 준다.
2. **`graph/03_CONTRACT.json` 은 어떤 경우에도 바꾸지 않는다.** 계약을 바꾸면
   루프판과 같은 자로 잴 수 없다. 계약을 바꾸고 싶다면 **루프 킷으로 돌아가야 한다.**
3. 문서만 고치고 코드를 안 고치는 일이 없게 한다. 반대도 마찬가지다.
4. 바꾼 뒤에는 **반드시 검사를 다시 돌린다.**
5. 영향받는 뒤 STEP 의 `STATUS` 를 `NEEDS_REVIEW` 로 바꾼다.

---

## 영향 범위표

| 바꾸는 결정 | 같이 바뀌는 것 | 다시 돌릴 검사 |
| --- | --- | --- |
| `G-상태범위` `G-원본보관` `G-판정필드` | `state.py` · STEP 2·3·4 의 물려받은 값 (`G-상태범위` → STEP 2·4, `G-판정필드` → STEP 2·3 의 `읽기 2` · `inherited`) (진단 · 처방 가지 칸 6개는 킷 고정 — 지우지 않는다) | `check_graph_shape.py` · `check_graph_readiness.py` (`diagnose_fields`) |
| `G-노드개수` `G-검사기노드화` `G-실행주체` | (문서만) · STEP 3·4 물려받은 값 (`G-검사기노드화` → STEP 3 · `G-노드개수` → STEP 4). 루프 골격 14 · 진단 2 는 그대로 | `validate_specs.py --step 2` · `check_graph_shape.py` **11번** |
| `G-라우터판단` `G-상한처리` | `edges.py` 의 STEP 3 라우터 4개 (라우터 6개 중 고칠 수 있는 것). `route_after_quality` · `route_after_detour` 와 네 라우터 안의 `킷 고정 ▼` 구간(처방 가지 분기 · 정성 분기)은 그대로 둔다 · STEP 5 물려받은 값 (`G-라우터판단` · `G-상한처리`) | `check_graph_shape.py` **4·5·7·9·10·11번** |
| `G-병렬범위` `G-병렬충돌` | `state.py` reducer | `check_graph_shape.py` **3번** + `run_once.py --mode replay --auto proceed` |
| `G-체크포인터` `G-게이트위치` `G-게이트선택지` | `nodes.py` 게이트 2개 (게이트의 처방 한도 되살리기 — `more` · `research` · `rebuild` 에서 `detour_attempts` → `{}` — 는 지우지 않는다) | `check_graph_readiness.py` + `run_once.py --mode replay --auto proceed` |

`run_once.py` 확인 실행에서 게이트 B 에 `done` 을 주지 않는다 — 정성 3회(`claude -p`, 6~12분)가
시작된다. `--auto proceed` 면 게이트 A 에 답하고 게이트 B 에서 스스로 멈춘다.

---

## 실행 순서

1. 무엇을 왜 바꾸려는지 듣는다.
2. **이전 값 / 새 값 / 영향 범위**를 위 표로 보여 주고 확인을 받는다.
3. 확인받으면:
   - 해당 STEP 문서의 `ANSWERS` · `PROJECT` · `MACHINE` 갱신
   - 위 표의 코드 파일 수정
   - `specs/00_DECISION_LOG.md` 1번 표의 확정 값을 새 값으로 고치고, 5-1 표(결정을 바꾼 기록)에
     이전 값 · 새 값 · 이유 · 다시 볼 STEP 을 남김
   - 영향받는 뒤 STEP 의 `STATUS` 를 `NEEDS_REVIEW` 로
4. 검사를 다시 돌린다. 명세 형식은 바꾼 STEP 과 `NEEDS_REVIEW` 로 돌린 STEP 마다
   `python scripts/validate_specs.py --step N` 으로 본다 — 인자 없이 돌리면 STEP 6 까지 보는데,
   STEP 6 은 조건부라 하지 않았으면 SHORT(exit 2)로 남는다 (정상).
5. 원래 있던 곳으로 돌아간다 (`graph-spec-builder` · `graph-run` · `graph-detour-builder`).

---

## 자주 나오는 요청과 답

| 요청 | 답 |
| --- | --- |
| "관광지를 5곳으로 늘리고 싶어요" | **계약 변경입니다.** 루프 킷의 STEP 3 을 고치고 인계본을 다시 뽑아야 합니다 |
| "검사가 너무 깐깐해요" | 같은 이유로 계약 변경입니다. 검사기를 고치는 것은 채점표를 고치는 것입니다 |
| "노드를 더 쪼개고 싶어요" | **루프 골격 14는 고정입니다.** 같은 실패가 로그에 반복됐다면(보고서 ③ · ③-2 의 후보) STEP 6 (조건부)에서 **규칙 처방 가지로 뺍니다** — 진단 노드에서 갈라져 규칙대로 고치고(fix) → 같은 시험지로 다시 재고(test) → 검사기로 돌아오는 길입니다 (`graph-detour-builder`). 후보가 없으면 노드를 늘리지 않습니다. 결정이 바뀌는 일이 아니라서 이 스킬의 몫이 아닙니다 |
| "처방 한도를 2회에서 늘리고 싶어요" | 결정이 아닙니다. 처방 한도(`detour_limit`)는 킷 고정입니다 (`travel_graph/detours/__init__.py` 의 `LIMIT`). 한도를 다 쓰면 게이트에서 사람이 `more` · `research` · `rebuild` 로 새로 채웁니다 |
| "게이트를 하나로 합치고 싶어요" | 가능합니다. 다만 어느 루프에서 왔는지를 상태에 적어야 라우터가 판단할 수 있습니다 |
