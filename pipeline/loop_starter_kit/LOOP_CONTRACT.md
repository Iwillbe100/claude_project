# LOOP_CONTRACT.md — 루프 실행 계약

이 파일은 **직접 쓰는 문서가 아닙니다.** STEP 7에서 확정된 결정을 실행 절차로 옮겨 적습니다.

---

## 0. 현재 상태

<!-- PROJECT:BEGIN -->

```text
상태: 완성 (STEP 7 승인 · 2026-10-23)
```

루프 실행 전에 `check_loop_readiness.py` 로 `READY` 를 확인하고 `--lock` 으로 잠급니다.

<!-- PROJECT:END -->

---

## 1. 이 파일은 어떻게 만들어지는가

1. STEP 4·5·6·7의 승인된 결정을 읽는다.
2. 아래 3~6번의 빈칸을 실제 값으로 바꾼다.
3. 0번의 "미완성" 표시를 지운다.
4. `python scripts/check_loop_readiness.py`가 `READY`인지 확인한다.

---

## 2. 시작 조건 (전부 만족해야 시작)

- [ ] STEP 1~7 모두 `APPROVED`
- [ ] 결정 21개가 모두 값으로 확정
- [ ] 모든 작업에 `loop` (A 또는 B)가 붙어 있음
- [ ] 루프 A·B에 테스트가 하나씩 붙어 있음 (루프 C의 판정기는 킷 고정)
- [ ] `quality_contract` 가 채워져 있음 (규율 10가지 · 3회)
- [ ] 루프별 상한과 같은 오류 상한이 숫자로 정해짐
- [ ] `MASTER_SPEC.md`의 검사 계약에 `null`이 없음
- [ ] `check_loop_readiness.py` → `READY` (exit 0)
- [ ] `check_loop_readiness.py --lock` 실행 완료

---

## 3. 세 루프의 순서 (고정)

```text
  ┌──────────────────────── 루프 A · 정보량 충족 ─────────────────────────┐
  │  TASK-입력읽기 → TASK-국가정보 → TASK-도시선정                        │
  │  → TASK-명소수집 → TASK-일정수집                                      │
  │                                                                      │
  │  판정: python scripts/check_information_count.py                     │
  │    exit 0  통과 → 되물음 → 루프 B 로                                  │
  │    exit 2  부족 → RESEARCH (부족한 칸만) → 다시 판정                  │
  │    exit 1  깨짐 → HITL                                               │
  └──────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
  ┌──────────────────────── 루프 B · 페이지 완성 ─────────────────────────┐
  │  TASK-페이지생성 → TASK-기능점검                                      │
  │                                                                      │
  │  판정: python scripts/check_page_contract.py                        │
  │    exit 0  통과 → 되물음 → 루프 C 로                                  │
  │    exit 2  부족 → RETRY (부족한 칸만) → 다시 판정                     │
  │    exit 1  깨짐 → HITL                                               │
  └──────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
  ┌──────────────────────── 루프 C · 정성 완성도 ─────────────────────────┐
  │  TASK-정성점검 × 3회 (킷 고정. 줄이지도 늘리지도 않는다)              │
  │    1회차 내용  ·  2회차 실행 가능성  ·  3회차 독자 관점               │
  │                                                                      │
  │  회차마다: 규율 10개 전부 판정 → 고침 → verify_all --skip-quality     │
  │            → passN.json 기록 (판정 · 고친 것 · 파일 해시 · 종료 코드)  │
  │                                                                      │
  │  판정: python scripts/check_quality_passes.py                       │
  │    exit 0  3회 완료 → 되물음 → 사람이 브라우저로 확인 → SUCCESS       │
  │    exit 2  덜 돔  → QUALITY (남은 회차) → 다시 판정                   │
  │            3회 다 돌고 수정이 0건이면 → 되물음                       │
  │            (한 회차 다시 돈다 / 이대로 확정 = HALT_NEEDS_HUMAN)      │
  │    exit 1  깨짐  → HITL                                              │
  └──────────────────────────────────────────────────────────────────────┘
```

**앞 루프가 통과하기 전에는 뒤 루프를 판정하지 않습니다.**
`scripts/verify_all.py`가 이 순서를 강제합니다.

> 루프 C는 **통과선이 아니라 회차로 닫습니다.** 품질에 점수를 매기면
> 글을 쓴 쪽이 자기 글에 점수를 주게 되어 판정 독립이 무너지기 때문입니다.
> 그래서 판정기는 **품질이 아니라 절차**를 봅니다.

---

## 4. 한 반복의 절차 (고정 골격)

```text
0  루프 C 라면 아래 4b 절차를 따른다 (모양이 다르다)
1  state/loop_state.json 을 읽어 지금 어느 루프 · 어느 작업인지 확인
2  Act      첫 바퀴: 그 루프의 작업 목록을 순서대로 한 번씩 돌린다
            다음 바퀴부터: 부족으로 지적된 칸의 작업만 다시 한다 (RESEARCH = 부족한 칸만)
            지적되지 않은 칸은 손대지 않는다
3  Observe  그 루프의 검사기를 한 번 실행하고 종료 코드를 읽는다
4  통과하면 → 되물음 → 다음 루프 (또는 SUCCESS)
5  실패하면 → 오류 지문 계산 → 실패 유형 분류
6  Reason   실패 유형에 따라 다음 행동을 고른다
7  Repeat   최소 수정 → 그 루프의 검사기 → 최종 검증 명령
8  events.jsonl 에 한 줄 기록 + loop_state.json 갱신
9  상한에 걸리면 멈추지 말고 되물음을 띄운다
```

> 판정기는 그 루프의 결과물 **전체**를 한 번에 본다 (루프 A 는 `research_data.json` 전체).
> 그래서 작업 하나마다 판정하지 않는다 — 첫 수집이 끝나기 전의 판정은 SHORT 가 정해져 있다.

### 4b. 루프 C 한 회차의 절차 (고정 골격)

```text
1  파일 해시를 적는다                     snapshot_before
2  규율 10개를 전부 판정한다               이번 회차의 렌즈부터 고친다
3  output/** 만 고친다                    명세와 검사기는 건드리지 않는다
4  python scripts/verify_all.py --skip-quality
     exit 0 이 아니면 이 회차 수정을 되돌린다
5  파일 해시를 다시 적는다                 snapshot_after
6  evidence/runs/<run_id>/quality/passN.json 에 기록
7  3회를 다 돌 때까지 1로 돌아간다
```

```text
고칠 것이 없는 회차도 있다.  그때는 applied_fix 를 비우고 해시를 그대로 둔다.
고친 척하면 해시가 바뀌어서 걸리고, 위반이라 적고 안 고치면 그것도 걸린다.
다만 3회 모두 고친 것이 0건이면 판정기는 SHORT(exit 2)를 낸다 → 되물음으로 사람에게 넘긴다.
```

---

## 5. 실행 값

<!-- PROJECT:BEGIN -->

| 항목 | 값 | 출처 |
| --- | --- | --- |
| 국가 · 여행 일수 | 일본(오사카) · 4일 (11/13~16) | `D-여행입력` |
| 첫 작업 | `TASK-입력읽기` | `D-작업목록` 루프 A 첫 항목 |
| 루프 A 작업 순서 | `TASK-입력읽기` → `TASK-국가정보` → `TASK-도시선정` → `TASK-명소수집` → `TASK-일정수집` | `D-작업목록` |
| 루프 B 작업 순서 | `TASK-페이지생성` → `TASK-기능점검` | `D-작업목록` |
| 루프 A 판정 명령 | `python scripts/check_information_count.py` (개수와출처와분량) | `D-정보량테스트` |
| 루프 B 판정 명령 | `python scripts/check_page_contract.py` (내용대조) | `D-페이지테스트` |
| 루프 C 판정 명령 | `python scripts/check_quality_passes.py` | 킷 고정 |
| 루프 C 회차 | 3회 (최소이자 최대) | 킷 고정 |
| 루프 C 되돌아감 확인 | `python scripts/verify_all.py --skip-quality` | 킷 고정 |
| 정성 규율 | `specs/QUALITY_RUBRIC.md` 10가지 | 킷 고정 |
| 최종 검증 명령 | `python scripts/verify_all.py` | `D-최종검증명령` |
| 성공 조건 | `verify_all.py` exit 0 + 사람이 브라우저로 열어 확인 | `D-성공조건` |
| 루프 A 상한 | 3바퀴 | `D-정보루프반복` |
| 루프 B 상한 | 3바퀴 | `D-페이지루프반복` |
| 같은 오류 상한 | 2회 | `D-무진전기준` |
| 전체 반복 상한 | 10번 (루프 A·B 합계) | `D-최대반복` |
| 되물음 지점 | 루프 A 끝 · B 끝 · C 끝 | `D-사람확인지점` |
| 보호 파일 | `specs/**` `scripts/**` `templates/**` `CLAUDE.md` `MASTER_SPEC.md` `LOOP_CONTRACT.md` | `D-수정금지파일` |

<!-- PROJECT:END -->

---

## 6. 되물음 형식 (고정)

루프가 끝날 때, 그리고 상한에 걸릴 때 이 형식으로 사람에게 묻습니다.
**못 채운 칸이 남았느냐에 따라 모양이 둘입니다.** 전체 양식은 `templates/REVERSE_QUESTION.md`.

```text
통과했을 때 — 판정기 exit 0 · 못 채운 칸 0
[되물음] <어느 루프>가 끝났습니다. 못 채운 칸 없이 통과했습니다.
  채운 것    : M / M 칸
  못 채운 것 : 없음
  고르세요
   [1] 더 손본다                      (판정기로는 할 일이 없다)
   [2] 다음 루프로 넘어간다             ← 권장
   [3] 여기서 멈춘다
```

```text
부족이 남았을 때 — 상한에 걸림 · 아직 SHORT
[되물음] <어느 루프>가 끝났습니다 / 상한에 걸렸습니다.
  채운 것    : N / M 칸
  못 채운 것 : (목록)
  고르세요
   [1] 부족한 칸만 다시 모은다        (예상 시간)
   [2] 부족한 채로 다음으로 넘어간다   ← 대개 권장 · 최종 상태는 SUCCESS 가 아니라 HALT_*
   [3] 여기서 멈춘다
```

`HALT_*` 안내는 부족이 남았을 때만 붙입니다. 루프 C 가 끝났을 때의 되물음은 모양이 다릅니다
(`templates/REVERSE_QUESTION.md` 의 "루프 C에서는 되물음이 다르다").

**답은 `PROJECT_MEMORY.md`의 7번(되물음에서 내가 고른 답) 표에 남깁니다.**
`specs/**`는 `--lock`으로 잠겨 있어 루프 중에는 결정 장부에 쓰지 않습니다.

---

## 7. 실패 유형별 다음 행동 (고정)

| 실패 유형 | 다음 행동 |
| --- | --- |
| `CODE_ERROR` | `RETRY` |
| `TEST_ERROR` | `HITL` |
| `SPEC_CONFLICT` | `REVISE_SPEC` |
| `ENVIRONMENT_ERROR` | `HITL` |
| `PERMISSION_ERROR` | `HITL` |
| `INFORMATION_INSUFFICIENT` | `RESEARCH` |
| `UNKNOWN_ERROR` | `STOP` |

**`next_action` 에 적는 값** — 위 실패 라우팅 5가지(`RETRY` · `RESEARCH` · `REVISE_SPEC` · `HITL` · `STOP`)에 더해,
실패가 아닌 진행 값 셋이 있습니다.

| 값 | 언제 |
| --- | --- |
| `REVERSE_QUESTION` | 되물음을 띄운 줄 (통과든 상한이든) |
| `QUALITY` | 루프 C 가 남은 회차를 도는 줄 (판정기 exit 2 는 진행 중이다) |
| `DONE` | 최종 검증(`verify_all.py` exit 0)으로 정상 종료한 줄 |

인계본(`export_graph_handoff.py`)은 실패 라우팅 5가지(또는 `failure_type` 이 적힌 줄)만 실패로 셉니다 —
검사기가 통과한(exit 0) 줄과 출발점 빨간불(RED · `iteration` 0) 줄은 빼고 셉니다.

---

## 8. 종료 상태

| 상태 | 언제 |
| --- | --- |
| `SUCCESS` | 성공 조건 충족 |
| `HALT_NEEDS_HUMAN` | 사람의 결정이 필요 |
| `HALT_NO_PROGRESS` | 같은 오류 지문이 상한만큼 반복 |
| `HALT_SPEC_CONFLICT` | 명세끼리 어긋남 |
| `HALT_PERMISSION` | 권한 없음 |
| `HALT_RESEARCH_GAP` | 정보를 못 채움 |
| `HALT_ENVIRONMENT` | 실행 환경 문제 |

---

## 9. 증거와 보고

```text
evidence/runs/<run_id>/
  run_manifest.json  events.jsonl  test_results/  changes/
  quality/pass1.json  quality/pass2.json  quality/pass3.json
  failure_report.md (멈췄을 때)   final_report.md (끝났을 때)   reverse_question.md (사람 결정이 필요할 때)
```

남기지 않는 것: API 키 · 토큰 · 개인정보 · 모델의 비공개 사고 과정 전체.

루프가 끝나면 `python scripts/export_graph_handoff.py` 로 `output/graph/` 를 만든다.
다음 강의(그래프)로 넘길 인계본이다. 계약은 그대로 넘기고 실행 구조만 바꾼다.

---

## 10. 확인 명령

```bash
python scripts/check_loop_readiness.py
python scripts/check_loop_readiness.py --lock
python scripts/verify_all.py
python scripts/verify_all.py --skip-quality      # 정성 회차 중에만
```
