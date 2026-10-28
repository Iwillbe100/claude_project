# STEP 7 — 실행 계약

> **한 줄 목적:** 무엇이 되면 **끝**인지 정하고, 흩어진 결정을 한곳에 모은다.
> **내가 결정할 것: 2개** · **코드 생성: 이 STEP이 끝난 다음 명령부터**

| 이전 | 다음 | 문서 규칙 | 결정 장부 |
| --- | --- | --- | --- |
| [STEP 6 — 반복 방법](06_LOOP_ITERATION.md) | (마지막 STEP) | [00_INDEX](00_INDEX.md) | [00_DECISION_LOG](00_DECISION_LOG.md) |

---

## 읽기 1 — 이 STEP에서 정하는 것

마지막 STEP입니다. 여기서 두 가지가 일어납니다.

```text
1  "무엇이 되면 끝인가" 를 정한다
2  STEP 1~6의 결정을 MASTER_SPEC.md 와 LOOP_CONTRACT.md 에 모은다
       ↓
   그때부터 검사 스크립트가 숫자를 읽을 수 있게 된다
       ↓
3  결정 장부 5번에 루프 구조도를 확정 값으로 다시 그린다
       ↓
   내가 고른 21개가 어떤 루프가 됐는지 그림으로 확인한다
       ↓
   루프를 돌릴 수 있다
```

---

## 읽기 2 — 앞에서 물려받은 결정

<!-- PROJECT:BEGIN -->

| 물려받은 것 | 값 | 어디서 |
| --- | --- | --- |
| 국가 · 여행 일수 | 일본(오사카) · 4일 | `D-여행입력` |
| 카운트 계약 | 도시 1 · 명소 3 · 소개근거 3 · 일정근거 2 (관광지 3곳 · 이미지 5장) | STEP 3 |
| 화면 계약 | 기능1 accordion · 기능2 drawer · 기능3 accordion · 취향 설명 15줄 이상 | STEP 2 |
| 첫 작업 | `TASK-입력읽기` | `D-작업목록`의 루프 A 첫 항목 |
| 최종 검증 명령 | `python scripts/verify_all.py` | `D-최종검증명령` |
| 루프별 상한 | 루프 A 3바퀴 · 루프 B 3바퀴 · 같은 오류 2회 (루프 C는 3회 고정) | STEP 6 |

<!-- PROJECT:END -->

---

## 읽기 3 — 이미 정해 둔 것 (읽고 넘어가기)

### (1) 루프를 시작하는 순서 (고정)

```text
1  python scripts/check_loop_readiness.py          →  READY 인가?
2  python scripts/check_loop_readiness.py --lock   →  보호 파일 해시 잠금
3  Claude Code 에서  "루프를 실행해줘"
```

### (2) 첫 작업은 고정이다

```text
루프 A 의 첫 작업이 언제나 먼저입니다.
정보가 없으면 화면을 만들 수 없기 때문입니다. 고를 것이 없습니다.
```

### (2b) 최종 검증 명령은 루프 A·B·C를 모두 본다 (고정)

```text
python scripts/verify_all.py
   ├─ 루프 A  정보량        통과해야 다음을 본다
   ├─ 루프 B  페이지        통과해야 다음을 본다
   └─ 루프 C  정성 3회      3회를 규율대로 돌아야 통과
```

그래서 `D-성공조건`에서 **A(exit 0)만 골라도 정성 3회가 자동으로 포함됩니다.**
종료 스위치 하나만 보면 되도록 루프 C를 그 안에 넣었기 때문입니다.

> 종료 상태는 여전히 **7가지**입니다. 정성 회차가 덜 끝난 것은 `SHORT`(진행 중)이고,
> 사람이 거기서 멈추기로 하면 `HALT_NEEDS_HUMAN` 입니다. 새 상태를 만들지 않습니다.

### (3) 종료 상태 7가지 (고정)

```text
SUCCESS             최종 검증 명령 통과
HALT_NEEDS_HUMAN    사람의 결정이 필요
HALT_NO_PROGRESS    같은 오류가 반복
HALT_SPEC_CONFLICT  명세끼리 어긋남
HALT_PERMISSION     권한 없음
HALT_RESEARCH_GAP   정보를 끝내 못 채움
HALT_ENVIRONMENT    실행 환경 문제
```

### (4) 끝나면 보고할 것 (고정)

```text
상태 / 루프별 반복 횟수 / 최종 명령과 종료 코드
채운 칸과 못 채운 칸 / 바뀐 파일 / 증거 위치 / 사람이 할 일
```

### (5) 끝나면 인계본을 만든다 (고정)

```bash
python scripts/export_graph_handoff.py
```

`output/graph/` 에 다음 강의(그래프)로 넘길 것들이 모입니다.
**결정 21개와 실측을 사람이 읽는 형태로 뽑는 것**이지, 새 결정을 만드는 것이 아닙니다.
고를 것이 없으므로 질문하지 않습니다.

---

## 읽기 4 — 내가 결정할 질문

<!-- FIXED:BEGIN -->

| 결정 ID | 질문 | 이 값이 바꾸는 것 |
| --- | --- | --- |
| `D-성공조건` | 무엇이 되면 **끝**인가? | 루프가 멈추는 지점 |
| `D-최대반복` | 루프 A·B 를 합쳐 최대 **몇 번** 도나? | 시간과 비용의 상한 |

**쉬운 선택지**

| 결정 ID | A | B | C | 권장 |
| --- | --- | --- | --- | --- |
| `D-성공조건` | 최종 검증 명령 exit 0 | A + **사람이 브라우저로 열어 확인** | B + 정보량 100% 충족 | **B** |
| `D-최대반복` | 10번 | 15번 | 20번 | **A** |

```text
D-성공조건 = A   기계만 통과하면 끝 (정보량 + 페이지 + 정성 3회). 눈으로는 안 본다.
D-성공조건 = B   위에 더해 내가 브라우저로 한 번 본다.   ← 권장
D-성공조건 = C   B 와 같다. exit 0 이 이미 정보량 100%(루프 A 모든 행 PASS)를 뜻한다.
```

> 주의: 어느 것을 골라도 **exit 0 은 정보량 100%를 뜻합니다.** 인터넷에 없는 사진 한 장이 있으면 A·B 도 SUCCESS 가 되지 않고, 되물음 [2]를 거쳐 `HALT_*` 로 끝납니다.

<div></div>

> **B를 권하는 이유가 하나 더 늘었습니다.** 기계는 이미지가 열리는지를 *기록으로* 확인하지
> 직접 보지는 않습니다. 사진이 그 관광지가 맞는지는 **끝까지 사람의 눈**입니다.

<!-- FIXED:END -->

---

## 읽기 5 — 내 답 적기

<!-- ANSWERS:BEGIN -->

### `D-성공조건`
- 고른 것: B (exit 0 + 사람이 브라우저로 열어 확인)
- 직접 쓰고 싶다면:

### `D-최대반복`
- 고른 것: A (10번)
- 직접 쓰고 싶다면:

<!-- ANSWERS:END -->

---

## 읽기 6 — Claude가 정리한 결과

<!-- PROJECT:BEGIN -->

| 결정 ID | 확정 값 | 고른 이유 | 승인 시각 |
| --- | --- | --- | --- |
| `D-성공조건` | `python scripts/verify_all.py` exit 0 + 사람이 브라우저로 열어 확인 | 권장값. 사진이 그 관광지가 맞는지는 사람의 눈으로만 확인 가능 | 2026-10-23 |
| `D-최대반복` | 루프 A·B 합쳐 10번 | 권장값. 루프별 상한(3+3)에 여유를 둔 전체 상한 | 2026-10-23 |

**모아 넣은 곳**

| 파일 | 무엇이 들어갔나 | 상태 |
| --- | --- | --- |
| `MASTER_SPEC.md` | 결정 21개 · 카운트 계약 · 화면 계약 | 채움 (`null` 없음) |
| `LOOP_CONTRACT.md` | 루프별 작업 순서 · 상한 · 되물음 지점 | 채움 |
| `state/loop_state.json` | 시작 상태 | 생성 |
| `specs/00_DECISION_LOG.md` 5번 | 확정 값이 들어간 루프 구조도 | 다시 그림 (`상한 A 3 · B 3바퀴`) |

<!-- MACHINE:BEGIN -->
```json
{
  "step": 7,
  "produces": "spec_then_code",
  "decisions": {
    "D-성공조건": "python scripts/verify_all.py exit 0 + 사람이 브라우저로 열어 확인",
    "D-최대반복": 10
  },
  "fixed": {
    "start_sequence": [
      "python scripts/check_loop_readiness.py",
      "python scripts/check_loop_readiness.py --lock",
      "루프를 실행해줘"
    ],
    "first_loop": "A",
    "loop_order": ["A", "B", "C"],
    "final_verifier_covers": ["루프 A 정보량", "루프 B 페이지", "루프 C 정성 3회"],
    "quality_passes": 3,
    "termination_states": [
      "SUCCESS", "HALT_NEEDS_HUMAN", "HALT_NO_PROGRESS", "HALT_SPEC_CONFLICT",
      "HALT_PERMISSION", "HALT_RESEARCH_GAP", "HALT_ENVIRONMENT"
    ],
    "report_fields": [
      "상태", "루프별 반복 횟수", "최종 명령과 종료 코드",
      "채운 칸과 못 채운 칸", "바뀐 파일", "증거 위치", "사람이 할 일"
    ],
    "aggregate_files": ["MASTER_SPEC.md", "LOOP_CONTRACT.md", "state/loop_state.json"],
    "loop_diagram": "specs/00_DECISION_LOG.md 의 5번. 확정 값으로 다시 그린다"
  },
  "inherited": {
    "final_verifier_command": "python scripts/verify_all.py",
    "first_task": "TASK-입력읽기",
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
| **지금 코드가 만들어지나?** | **아직 아니오.** 다만 이 STEP이 끝나면 **다음 명령부터** 만들어집니다. |
| **Claude가 실제로 하는 일** | ① 결정 2개 확정 → ② `MASTER_SPEC.md`에 결정 21개·카운트 계약·화면 계약 채우기 → ③ `LOOP_CONTRACT.md`에 실행 절차 옮기기 → ④ `state/loop_state.json` 만들기 → ⑤ **결정 장부 5번의 루프 구조도를 확정 값으로 다시 그리기** |
| **바뀌는 파일** | `specs/07_EXECUTION_CONTRACT.md` · `specs/00_DECISION_LOG.md`(결정 21개 + **5번 구조도**) · `PROJECT_MEMORY.md` · `MASTER_SPEC.md` · `LOOP_CONTRACT.md` · `state/loop_state.json` |
| **내가 지금 실행할 명령** | `python scripts/check_loop_readiness.py` → `READY` 확인 → `--lock` → `루프를 실행해줘` |

---

## 읽기 8 — 완료 확인과 다음 명령

- [ ] 성공 조건이 문장으로 적혀 있다
- [ ] 최종 검증 명령이 **세 루프**를 본다는 것을 확인했다
- [ ] 최대 반복이 숫자다
- [ ] `MASTER_SPEC.md`에 `(미정)`이 남아 있지 않다
- [ ] `LOOP_CONTRACT.md`에 `(미정)`이 남아 있지 않다
- [ ] 결정 장부 5번 구조도의 `__` 자리에 **실제 숫자**가 들어갔다
- [ ] 구조도가 내가 고른 작업 목록·상한과 맞는다
- [ ] `python scripts/check_loop_readiness.py` → `READY` (exit 0)
- [ ] 상태가 `APPROVED`다

```bash
python scripts/check_loop_readiness.py
python scripts/check_loop_readiness.py --lock
```

<!-- STATUS:BEGIN -->
STATUS: APPROVED
<!-- STATUS:END -->

```text
루프를 실행해줘
```
