# STEP 5 — 테스트와 검증

> **한 줄 목적:** 루프마다 **채점 기준**을 붙인다. 채점표는 AI가 못 고친다.
> (깐깐함을 고르는 것은 **앞 두 루프**뿐입니다. 루프 C의 판정기는 킷 고정입니다.)
> **내가 결정할 것: 3개** · **코드 생성: 없음 (검사 스크립트는 킷에 이미 있음)**

| 이전 | 다음 | 문서 규칙 | 결정 장부 |
| --- | --- | --- | --- |
| [STEP 4 — 경계·작업·안전](04_BOUNDARY_TASKS_SAFETY.md) | [STEP 6 — 반복 방법](06_LOOP_ITERATION.md) | [00_INDEX](00_INDEX.md) | [00_DECISION_LOG](00_DECISION_LOG.md) |

---

## 읽기 1 — 이 STEP에서 정하는 것

```text
Claude "다 됐습니다"          →  근거 아님
검사기 종료 코드 0            →  근거임
```

**그런데 검사기를 AI가 직접 만들면 어떻게 될까요?**

```text
AI가 만든 검사기  "칸이 3개 이상이면 통과"
AI가 만든 결과물  "칸 3개"
                 → 통과!  그런데 명세는 원래 13칸을 요구했다.
```

이것이 실제로 일어난 실패입니다. **시험지를 만든 사람이 시험을 보면 안 됩니다.**
그래서 이 킷은 검사기를 **미리 만들어서 잠가 두었습니다.**

---

## 읽기 2 — 앞에서 물려받은 결정

<!-- PROJECT:BEGIN -->

| 물려받은 것 | 값 | 어디서 |
| --- | --- | --- |
| 조사량 숫자 | 도시 1 · 명소 1×3=3곳 · 소개근거 3 · 일정근거 2 | STEP 3 |
| 화면 배치 | 기능1 accordion · 기능2 drawer · 기능3 accordion | `D-페이지구성` |
| 작업 목록 (루프별) | A: 입력읽기·국가정보·도시선정·명소수집·일정수집 / B: 페이지생성·기능점검 | `D-작업목록` |

<!-- PROJECT:END -->

---

## 읽기 3 — 이미 정해 둔 것 (읽고 넘어가기)

### (1) 검사기는 킷이 제공한다 (고정)

| 루프 | 검사기 | 무엇을 보나 |
| --- | --- | --- |
| A | `scripts/check_information_count.py` | 명세한 개수·분량·중복·이미지 유효성 |
| B | `scripts/check_page_contract.py` | STEP 2의 화면 그림대로 만들어졌는가 |
| C | `scripts/check_quality_passes.py` | 정성 점검을 규율대로 3회 돌았는가 |
| 셋 다 | `scripts/verify_all.py` | A → B → C 순서로, 앞이 통과했을 때만 뒤를 본다 |

```text
scripts/**  는 수정 금지 목록에 들어갑니다.
   →  AI는 채점 기준을 낮출 방법이 없습니다.
   →  통과하려면 진짜로 만드는 수밖에 없습니다.
```

### (2) 검사기는 명세에서 숫자를 읽는다 (고정)

```text
MASTER_SPEC.md  count_contract { "city_count": 3, … }
        │  읽음
        ▼
scripts/check_information_count.py     ← 숫자를 스스로 갖지 않는다
```

숫자를 바꾸고 싶으면 **명세를 바꿉니다.** 스크립트는 건드리지 않습니다.

### (3) 종료 코드 3가지 (고정)

| 코드 | 이름 | 뜻 | 다음 행동 |
| --- | --- | --- | --- |
| `0` | PASS | 기준을 다 채움 | 다음 루프로 |
| `1` | ERROR | 파일·명세가 깨짐 | **사람에게** — 더 돌려도 안 됨 |
| `2` | SHORT | 아직 덜 됨 | 루프가 더 돈다 |

> `1`과 `2`를 구분하는 것이 중요합니다. `2`는 정상적인 진행 중 상태입니다.

### (4) 첫 실행은 반드시 실패한다 (고정)

`output/` 이 비어 있으므로 처음 돌리면 무조건 `SHORT`가 나옵니다.
**이게 정상이고, 이게 TDD의 빨간불(RED)입니다.** 처음부터 통과하는 검사기는 아무것도 검사하지 않는 것입니다.

**그런데 이 원칙은 검사기 자신에게도 적용됩니다 (고정).**

```text
scripts/selftest/run_selftest.py

  검사행마다 그 행을 반드시 빨간불로 만드는 최소 입력을 하나씩 갖는다
  "실패했다" 가 아니라 "의도한 그 행에서 실패했다" 를 본다
```

빈 `output/` 으로 `SHORT` 가 나는 것은 "검사기가 늘 초록불은 아니다"까지만
말해 줍니다. **검사행 하나하나가 실제로 물리는지**는 말해 주지 않습니다.
실제로 계약에 배치를 선택지 문구로 적었더니 검사행 6개가 조용히 사라졌는데
판정은 `PASS` 였습니다. 결과물이 아니라 **검사기가 약해진** 것이고,
검사기가 약해진 것은 검사기가 알려 주지 않습니다.

`check_loop_readiness.py` 가 루프 시작 전에 이것을 자동으로 돌립니다.

### (5) 검사기가 보지 않는 것 (고정)

```text
화면이 예쁜가            사람 몫
정보가 사실인가          사람 몫  ← 마지막에 눈으로 확인하세요
글이 얼마나 좋은가        아무도 점수를 매기지 않는다   ← 아래를 보세요
```

### (6) 루프 C는 품질에 점수를 매기지 않는다 (고정)

"글이 자연스러운가"를 검사기가 볼 수 없다면, 왜 루프 C가 있을까요?

```text
품질에 점수를 매기면   글을 쓴 쪽이 자기 글에 점수를 준다   -> 조건⑤ 붕괴
그래서 점수를 안 매긴다. 대신 절차를 판정한다.

  본다        3회를 다 돌았는가
  본다        회차마다 규율 10개를 전부 판정했는가
  본다        위반이라 적은 것을 실제로 고쳤는가
  본다        고쳤다면 파일 해시가 실제로 바뀌었는가
  본다        회차 끝마다 루프 A·B가 여전히 통과하는가
  본다        위반이면 어디(where)인지 적었는가
  본다        3회 합쳐 고친 것이 1건 이상인가 (0건이면 SHORT → 되물음)
  보지 않는다  글이 좋아졌는가
```

> **"품질을 채점하지 않고 절차를 채점한다."** 이래야 판정이 100% 결정론적이고,
> 그러면서도 "점검했다고 말만 하고 넘어가는 것"이 막힙니다.
> 규율 10가지는 `QUALITY_RUBRIC.md` 에 있고, **내가 고르지 않습니다.**

---

## 읽기 4 — 내가 결정할 질문

<!-- FIXED:BEGIN -->

| 결정 ID | 질문 | 이 값이 바꾸는 것 |
| --- | --- | --- |
| `D-정보량테스트` | 루프 A를 **얼마나 깐깐하게** 보나? | 정보가 얇아도 통과하는지 |
| `D-페이지테스트` | 루프 B를 **얼마나 깐깐하게** 보나? | 껍데기만 만들어도 통과하는지 |
| `D-최종검증명령` | 전부 끝났는지 볼 **한 줄 명령**은? | 루프의 종료 스위치 |

**쉬운 선택지**

| 결정 ID | A | B | C | 권장 |
| --- | --- | --- | --- | --- |
| `D-정보량테스트` | 개수만 센다 | 개수 + 서로 다른 출처 | B + **분량 · 중복 · 이미지 유효성** | **C** |
| `D-페이지테스트` | 칸이 있는가 | A + 눌리는 연결이 있는가 | B + **모은 내용이 실제로 그 칸에 들어갔는가** | **C** |
| `D-최종검증명령` | `python scripts/verify_all.py` | 세 검사기를 따로 실행 | 직접 지정 | **A** |

**A를 고르면 이런 일이 생깁니다**

```text
D-정보량테스트 = A   근거 항목에 "좋음" 한 글자만 있어도 1건으로 셉니다.
D-페이지테스트 = A   글자 한 자만 든 <div data-spot-detail="…">가</div> 만 있어도 통과합니다.
                    → 화면은 완성으로 보이지만 내용이 거의 없습니다.
```

> **C를 권합니다.** 루프가 몇 바퀴 더 돌지만, **껍데기가 통과하는 길이 막힙니다.**

**C가 실제로 여는 검사 (글자 수는 명세에서 읽습니다)**

```text
분량   근거 1건 · 관광지 상세 · 도시 선정 이유 · 취향 설명 줄
중복   취향 설명의 고유 줄 비율 · 상세끼리 · 도시별 일정끼리의 유사도
자산   이미지를 실제로 열어 본 기록이 있는가 · 지어낼 수 있는 주소 형태가 아닌가
```

> 숫자는 `MASTER_SPEC.md`의 `count_contract` 에 있습니다. **스크립트에는 없습니다.**
> 그래서 STEP 3에서 근거 개수를 올리면 화면 검사의 최소 분량도 **저절로** 올라갑니다.

<!-- FIXED:END -->

---

## 읽기 5 — 내 답 적기

<!-- ANSWERS:BEGIN -->

### `D-정보량테스트`
- 고른 것: C
- 직접 쓰고 싶다면:

### `D-페이지테스트`
- 고른 것: C
- 직접 쓰고 싶다면:

### `D-최종검증명령`
- 고른 것: A
- 직접 쓰고 싶다면:

<!-- ANSWERS:END -->

---

## 읽기 6 — Claude가 정리한 결과

<!-- PROJECT:BEGIN -->

| 테스트 ID | 검사하는 루프 | 깐깐함 | 실행 명령 |
| --- | --- | --- | --- |
| `TEST-정보량` | A | 개수와출처와분량 | `python scripts/check_information_count.py` |
| `TEST-페이지` | B | 내용대조 | `python scripts/check_page_contract.py` |

| 결정 ID | 확정 값 | 고른 이유 | 승인 시각 |
| --- | --- | --- | --- |
| `D-정보량테스트` | 개수와출처와분량 (개수 + 서로 다른 출처 + 분량·중복·이미지 유효성) | 권장값. 껍데기만 채운 결과가 통과하는 길을 막음 | 2026-10-23 |
| `D-페이지테스트` | 내용대조 (칸 + 누르는 연결 + 내용 대조) | 권장값. 모은 내용이 실제 칸에 들어갔는지까지 봄 | 2026-10-23 |
| `D-최종검증명령` | `python scripts/verify_all.py` | 권장값. A → B → C 순서를 스크립트가 강제 | 2026-10-23 |

<!-- MACHINE:BEGIN -->
```json
{
  "step": 5,
  "produces": "spec_only",
  "decisions": {
    "D-정보량테스트": {"id": "TEST-정보량", "loop": "A", "strictness": "개수와출처와분량",
                       "command": "python scripts/check_information_count.py"},
    "D-페이지테스트": {"id": "TEST-페이지", "loop": "B", "strictness": "내용대조",
                       "command": "python scripts/check_page_contract.py"},
    "D-최종검증명령": "python scripts/verify_all.py"
  },
  "fixed": {
    "pass_exit_code": 0,
    "exit_codes": {"0": "PASS", "1": "ERROR", "2": "SHORT"},
    "verifiers": {
      "A": "scripts/check_information_count.py",
      "B": "scripts/check_page_contract.py",
      "C": "scripts/check_quality_passes.py",
      "all": "scripts/verify_all.py"
    },
    "quality_verifier_owner": "킷 고정. 교육생이 깐깐함을 고르지 않는다",
    "quality_judges": "품질 점수가 아니라 절차(3회 · 규율 10개 · 실제 수정 · 되돌아감 없음)",
    "regression_mode": "python scripts/verify_all.py --skip-quality",
    "verifier_owner": "킷. scripts/** 는 수정 금지",
    "threshold_source": "MASTER_SPEC.md 의 count_contract · page_contract",
    "first_run_must_fail": true,
    "not_checked": ["글이 자연스러운가", "화면이 예쁜가", "정보가 사실인가"],
    "tests": [
      {"id": "TEST-정보량", "loop": "A"},
      {"id": "TEST-페이지", "loop": "B"}
    ]
  },
  "inherited": {
    "count_contract": {"city_count": 1, "spots_per_city": 3, "intro_evidence": 3, "itinerary_evidence": 2},
    "page_layout": {"feature1": "accordion", "feature2": "drawer", "feature3": "accordion"},
    "task_loops": {"A": ["TASK-입력읽기", "TASK-국가정보", "TASK-도시선정", "TASK-명소수집", "TASK-일정수집"], "B": ["TASK-페이지생성", "TASK-기능점검"]}
  }
}
```
<!-- MACHINE:END -->

<!-- EXAMPLE:BEGIN -->
> **[작성 예시 — 실제 결정이 아닙니다]**
>
> ```json
> "D-정보량테스트": {"id": "TEST-정보량", "loop": "A", "strictness": "개수와출처와분량",
>                    "command": "python scripts/check_information_count.py"},
> "D-페이지테스트": {"id": "TEST-페이지", "loop": "B", "strictness": "내용대조",
>                    "command": "python scripts/check_page_contract.py"},
> "D-최종검증명령": "python scripts/verify_all.py"
> ```
<!-- EXAMPLE:END -->

<!-- PROJECT:END -->

---

## 읽기 7 — 이 STEP이 끝나면 무엇이 진행되는가

| 항목 | 내용 |
| --- | --- |
| **지금 코드가 만들어지나?** | **아니오.** 검사 스크립트는 킷에 이미 있습니다. 깐깐함만 정합니다. |
| **Claude가 실제로 하는 일** | ① 깐깐함 등급을 값으로 확정 → ② 테스트표 채우기 → ③ 결정 장부에 추가 → ④ STEP 6·7의 물려받은 값 갱신 |
| **바뀌는 파일** | `specs/05_TEST_AND_VERIFIER.md` · `specs/00_DECISION_LOG.md` · `PROJECT_MEMORY.md` · `specs/06_LOOP_ITERATION.md` · `specs/07_EXECUTION_CONTRACT.md` |
| **내가 지금 실행할 명령** | Claude Code에 `STEP 5 진행해줘` → 질문에 답 → `python scripts/validate_specs.py --step 5` |

---

## 읽기 8 — 완료 확인과 다음 명령

- [ ] 루프 A·B에 테스트가 하나씩 붙었다
- [ ] 깐깐함 등급이 값으로 적혀 있다 (`A` 같은 기호가 아니라)
- [ ] 최종 검증 명령이 한 줄로 정해졌다
- [ ] 검사 스크립트를 **고치지 않았다**
- [ ] 루프 C의 판정기는 **깐깐함을 고르지 않는다**는 것을 확인했다
- [ ] 상태가 `APPROVED`다

```bash
python scripts/validate_specs.py --step 5
```

<!-- STATUS:BEGIN -->
STATUS: APPROVED
<!-- STATUS:END -->

```text
STEP 6 진행해줘
```
