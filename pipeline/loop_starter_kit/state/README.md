# state/ — 지금 어디까지 왔는가

이 폴더는 **현재 실행 상태**를 담습니다. 대화가 끊기거나 요약되어도 이 파일을 읽으면 이어서 진행할 수 있습니다.

---

## 1. 기억을 세 곳으로 나누는 이유

| 파일 | 담는 것 | 바뀌는 빈도 |
| --- | --- | --- |
| `CLAUDE.md` | 변하지 않는 실행 규칙 | 거의 안 바뀜 |
| `PROJECT_MEMORY.md` | 사람이 승인한 결정과 이유 | 결정할 때마다 |
| `state/loop_state.json` | 지금 몇 번째 반복인지, 무엇이 실패했는지 | 매 반복마다 |

한 파일에 다 넣으면 규칙과 현재 상황을 구분할 수 없게 됩니다.

---

## 2. 파일 목록

| 파일 | 설명 |
| --- | --- |
| `loop_state.example.json` | **예시 스키마.** 그대로 두고 복사해서 씁니다 |
| `loop_state.json` | 실제 상태. STEP 7에서 만들어집니다 (없으면 준비도 검사가 `READY`가 되지 않습니다) |
| `spec_lock.json` | 보호 파일 해시 기록. `check_loop_readiness.py --lock`으로 만듭니다 |

`loop_state.json`과 `spec_lock.json`은 처음에는 없습니다. 없는 게 정상입니다.

---

## 3. 필드 설명

| 필드 | 뜻 | 누가 채우는가 |
| --- | --- | --- |
| `project_status` | `DESIGNING`(명세 중) / `RUNNING`(루프 중) / `DONE` / `HALTED` | Claude(`loop-run`) |
| `current_step` | 지금 작업 중인 STEP 번호 (1~7) | Claude |
| `approved_steps` | 승인 완료된 STEP 번호 목록 | Claude |
| `current_loop` | 지금 도는 루프 (`A` 정보량 / `B` 페이지 / `C` 정성) | Claude(`loop-run`) |
| `loops.A` `loops.B` `loops.C` | 루프별 반복 횟수 · 상한 · 판정기 · 마지막 종료 코드 | Claude(`loop-run`) |
| `quality_pass` `quality_focus` | 지금 몇 회차이고 이번 회차의 렌즈는 무엇인가 | Claude(`loop-run`) |
| `current_task_id` | 지금 손대는 TASK | Claude(`loop-run`) |
| `total_iteration` | 루프 A·B를 합쳐 몇 번 돌았는가 (루프 C의 3회는 따로 셉니다) | Claude(`loop-run`) |
| `max_iterations` | 전체 상한 (`D-최대반복`) | 사람 |
| `last_error_hash` | 마지막 오류 지문 | Claude(`loop-run`) |
| `same_error_count` | 같은 지문이 몇 번 반복됐는가 | Claude(`loop-run`) |
| `same_error_limit` | 몇 번이면 손을 떼는가 (`D-무진전기준`) | 사람 |
| `failure_type` | 7가지 실패 유형 중 하나 | Claude가 분류·기록 |
| `next_action` | 실패 라우팅 `RETRY`/`RESEARCH`/`REVISE_SPEC`/`HITL`/`STOP` · 되물음을 띄우면(통과든 상한이든) `REVERSE_QUESTION` · 루프 C 남은 회차면 `QUALITY` · 최종 검증(`verify_all.py` exit 0)으로 정상 종료하면 `DONE` (뒤의 셋은 실패가 아니다) | Claude가 결정·기록 |
| `reverse_question_pending` | 되물음을 띄우고 답을 기다리는 중인가 | Claude(`loop-run`) |
| `final_status` | `SUCCESS` 또는 `HALT_*` | Claude(`loop-run`) |
| `termination_reason` | 왜 끝났는가 한 줄 | Claude(`loop-run`) |
| `updated_at` | 마지막 갱신 시각 (ISO 시각. 인계본이 루프판 전체 시간을 여기서 잰다) | Claude(`loop-run`) — 갱신할 때마다 적는다 |

> 이 파일을 쓰는 스크립트는 없습니다. `Claude(loop-run)` 칸의 값은 검사기 종료 코드와 규칙에서 기계적으로 정해지는 값을
> `loop-run` 이 옮겨 적는 것입니다 (`check_loop_readiness.py` 는 파일이 있는지와 JSON 형식만 보고, `export_graph_handoff.py` 는 읽기만 합니다).

---


## 4. 시작하는 법

STEP 7에서 `step-spec-builder` Skill이 만듭니다. 준비도 검사가 이 파일을 보므로 루프보다 먼저 있어야 합니다.
직접 만들고 싶다면 복사하세요.

```bash
cp state/loop_state.example.json state/loop_state.json
```

---

## 5. 주의

- 예시 파일(`loop_state.example.json`)은 **수정하지 않습니다.** 비교 기준으로 남겨 둡니다.
- 상태 파일에 API 키나 개인정보를 넣지 않습니다.
- 값을 손으로 고쳐서 성공 상태로 만들지 않습니다. 성공은 `scripts/verify_all.py`의 종료 코드가 판정합니다.
