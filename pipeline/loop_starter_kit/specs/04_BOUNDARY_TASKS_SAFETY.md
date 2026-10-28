# STEP 4 — 경계·작업·안전

> **한 줄 목적:** 일을 **루프 세 개**로 나누고, 각 루프가 할 일과 못 건드릴 선을 정한다.
> (내가 작업을 나누는 것은 **앞 두 루프**뿐입니다. 세 번째는 킷 고정입니다.)
> **내가 결정할 것: 3개** · **코드 생성: 없음 (명세 문서만 바뀜)**

| 이전 | 다음 | 문서 규칙 | 결정 장부 |
| --- | --- | --- | --- |
| [STEP 3 — 정보량 카운트](03_INFORMATION_COUNT.md) | [STEP 5 — 테스트와 검증](05_TEST_AND_VERIFIER.md) | [00_INDEX](00_INDEX.md) | [00_DECISION_LOG](00_DECISION_LOG.md) |

---

## 읽기 1 — 이 STEP에서 정하는 것

원래 세 개였던 STEP(시스템 경계 · 구현 단위 · 안전장치)을 **하나로 합쳤습니다.**
세 가지가 사실 같은 질문이기 때문입니다 — **"AI에게 어디까지 맡기고, 어디서 내가 끼어드나?"**

```text
어디까지 맡기나   →  작업 목록      (무엇을 하는가)
어디는 못 건드리나 →  수정 금지 파일  (무엇을 못 하는가)
어디서 끼어드나   →  사람 확인 지점  (언제 나를 부르는가)
```

---

## 읽기 2 — 앞에서 물려받은 결정

<!-- PROJECT:BEGIN -->

| 물려받은 것 | 값 | 어디서 |
| --- | --- | --- |
| 조사량 숫자 | 도시 1 · 명소 1×3=3곳 · 소개근거 3 · 일정근거 2 | `D-도시수` `D-명소수` `D-소개근거수` `D-일정근거수` |
| 화면 배치 | 기능1 accordion · 기능2 drawer · 기능3 accordion | `D-페이지구성` |

<!-- PROJECT:END -->

---

## 읽기 3 — 이미 정해 둔 것 (읽고 넘어가기)

### (1) 루프는 셋이다. 순서도 고정이다

```text
   루프 A 정보량 충족  →  루프 B 페이지 완성  →  루프 C 정성 완성도
   ──────────────────    ──────────────────    ──────────────────
   명세한 개수만큼         화면 칸을 빠짐없이      규율 10가지로 3회
   모았는가               채웠는가               점검하고 고쳤는가
        └─ 먼저 끝나야 함 ─┴─ 먼저 끝나야 함 ─────┘

   왜 순서를 강제하나?
     없는 정보로 화면을 만들면 껍데기만 나온다.
     껍데기를 놓고 정성을 따지면 3회를 거기서 다 쓴다.
```

**앞 두 루프와 세 번째 루프는 성격이 다릅니다.**

| | 루프 A · B | 루프 C |
| --- | --- | --- |
| 무엇으로 끝나나 | **검사기가 통과할 때까지** | **정해진 3회를 돌면** |
| 상한의 뜻 | 최대 (더 못 돈다) | **최소이자 최대** (꼭 3번 돈다) |
| 판정하는 것 | 결과물의 개수와 칸 | **절차를 지켰는가** |
| 누가 정하나 | 교육생 (`D-정보루프반복` 등) | **킷 고정** |

> 정성은 "몇 점 이상이면 통과"로 닫을 수 없습니다. 글을 쓴 쪽이 자기 글에 점수를 주기 때문입니다.
> 그래서 **회차 수로 닫습니다.** 자세한 것은 STEP 6에 있습니다.

### (2) 누가 무엇을 하나 (고정)

| 일 | 담당 | 이유 |
| --- | --- | --- |
| 자연어에서 스타일 읽기 · 검색어 만들기 · 요약 · 글쓰기 | **LLM** | 뜻을 알아야 하는 일 |
| 실패 원인 분류 | **LLM** | 판단이 필요 |
| **개수 세기 · 칸 존재 확인 · 종료 코드 판정** | **CODE** | 흔들리면 안 되는 일 |
| **명세 변경 승인 · 루프 사이 되물음 답하기 · 최종 확인** | **HUMAN** | 책임이 따르는 일 |

### (3) 고칠 수 있는 곳 (고정)

```text
USER_REQUEST.md   내가 쓴 여행 스타일
PROJECT_MEMORY.md 승인된 결정 · 되물음 답(7번) · 실행 기록(6번)
output/**         결과물 (research_data.json, travel_site.html)
src/**            수집·생성 도우미 코드
state/**          진행 상태
evidence/runs/**  실행 증거
```

### (4) 기억을 세 곳에 나눈다 (고정)

| 파일 | 담는 것 | 바뀌는 때 |
| --- | --- | --- |
| `CLAUDE.md` | 변하지 않는 규칙 | 거의 안 바뀜 |
| `PROJECT_MEMORY.md` | 승인된 결정과 이유 | 결정이 확정될 때 |
| `state/loop_state.json` | 지금 몇 바퀴째인가 | 매 반복 |

### (5) 증거와 금지 (고정)

```text
evidence/runs/<run_id>/
  run_manifest.json   events.jsonl   test_results/   changes/
  final_report.md (끝났을 때)  failure_report.md (멈췄을 때)

반복마다 남기는 것
  실행한 명령 / 종료 코드 / 실패 유형 / 오류 지문 / 바꾼 파일 / 다음 행동 / 로그 경로

절대 남기지 않는 것
  API 키 · 토큰 · 개인정보 · 모델의 비공개 사고 과정 전체
```

### (6) 실패 유형 7가지 (고정)

```text
CODE_ERROR   TEST_ERROR   SPEC_CONFLICT   ENVIRONMENT_ERROR
PERMISSION_ERROR   INFORMATION_INSUFFICIENT   UNKNOWN_ERROR
```

### (7) 나를 부를 때 쓰는 형식 (고정) — "되물음"

루프는 혼자 판단하지 않고 **선택지를 주고 물어봅니다.**

```text
[되물음] 루프 A가 끝났습니다.
  채운 것   : 28 / 30 칸
  못 채운 것 : 후에 황제릉 사진 · 다낭 일정 근거 1건
  고르세요
   [1] 부족한 2칸만 다시 모은다              (약 3분 더)
   [2] 부족한 채로 루프 B로 넘어간다          ← 대개 이쪽을 고릅니다
   [3] 여기서 멈춘다
```

> **왜 [2]가 권장인가?** 아무리 찾아도 없는 정보는 계속 없습니다.
> 예를 들어 작은 관광지는 쓸 만한 사진이 인터넷에 아예 없기도 합니다.
> 그럴 때 루프를 계속 돌리면 **시간만 쓰고 결과는 같습니다.**

---

## 읽기 4 — 내가 결정할 질문

<!-- FIXED:BEGIN -->

| 결정 ID | 질문 | 이 값이 바꾸는 것 |
| --- | --- | --- |
| `D-작업목록` | 루프 A·B 를 **몇 개 작업**으로 쪼개나? | 첫 바퀴가 차례로 도는 순서 · 다음 바퀴에 다시 하는 단위 (지적된 칸의 작업만) |
| `D-수정금지파일` | AI가 **절대 못 고칠 것**은? | 명세에 선언하는 보호 범위 (`--lock`은 킷 고정 28개를 잠근다 · `specs`·`scripts`가 빠지면 준비도 검사가 막는다) |
| `D-사람확인지점` | **언제** 되물음을 띄우나? | 내가 끼어드는 횟수 |

**쉬운 선택지**

| 결정 ID | A | B | C | 권장 |
| --- | --- | --- | --- | --- |
| `D-작업목록` | 아래 권장 7개 그대로 | 5개로 합치기 | 직접 정의 | **A** |
| `D-수정금지파일` | `specs/**` `scripts/**` | A + `templates/**` `CLAUDE.md` | B + `MASTER_SPEC.md` `LOOP_CONTRACT.md` | **C** |
| `D-사람확인지점` | 루프 A 끝 + 루프 B 끝 + 루프 C 끝 | A + 정보량이 부족할 때마다 | 맨 마지막 한 번만 | **A** |

**권장 작업 7개**

| 루프 | 작업 ID | 하는 일 | 채우는 곳 |
| --- | --- | --- | --- |
| A | `TASK-입력읽기` | 국가·일수·스타일을 읽어 담기 | `research_data.request` |
| A | `TASK-국가정보` | 기능1 칸 전부 채우기 | `research_data.country_intro` |
| A | `TASK-도시선정` | 우선순위대로 도시 고르고 이유 적기 | `research_data.cities[].name` |
| A | `TASK-명소수집` | 관광지 · 근거 · 사진 · 취향 설명 | `research_data.cities[].spots` |
| A | `TASK-일정수집` | 일정 근거 모으고 일자별 계획 짜기 | `research_data.cities[].itinerary` |
| B | `TASK-페이지생성` | 단일 HTML 만들기 | `output/travel_site.html` |
| B | `TASK-기능점검` | 눌리는 연결 붙이고 빠진 칸 채우기 | `output/travel_site.html` |

> `D-수정금지파일`에서 C를 고르면, AI가 **기준을 낮춰서 통과하는** 길이 전부 막힙니다.
> 검사 스크립트(`scripts/**`)도 명세(`specs/**`)도 못 고치니, **통과하려면 진짜로 만드는 수밖에 없습니다.**

**루프 C의 작업은 킷이 고정으로 넣습니다 (고르지 않습니다)**

| 루프 | 작업 ID | 하는 일 | 채우는 곳 |
| --- | --- | --- | --- |
| C | `TASK-정성점검` | 규율 10가지로 점검하고 고친다 (3회) | `output/**` · `evidence/runs/<run_id>/quality/` |

> 그래서 **결정은 여전히 21개입니다.** 루프 C에서 고를 것이 없기 때문입니다.
> 규율은 `QUALITY_RUBRIC.md`, 회차 기록 양식은 `templates/QUALITY_PASS.md` 에 있습니다.

<!-- FIXED:END -->

---

## 읽기 5 — 내 답 적기

<!-- ANSWERS:BEGIN -->


### `D-작업목록`
- 고른 것: A (권장 7개 그대로)
- 직접 쓰고 싶다면:

(이 칸에 있던 여행 정보 메모는 spec-sync 로 STEP 1·`USER_REQUEST.md` 에 옮겼습니다)

### `D-수정금지파일`
- 고른 것: C (`specs/**` `scripts/**` `templates/**` `CLAUDE.md` `MASTER_SPEC.md` `LOOP_CONTRACT.md`)
- 직접 쓰고 싶다면:

### `D-사람확인지점`
- 고른 것: A (루프 A 끝 + 루프 B 끝 + 루프 C 끝)
- 직접 쓰고 싶다면:

<!-- ANSWERS:END -->

---

## 읽기 6 — Claude가 정리한 결과

<!-- PROJECT:BEGIN -->

| 루프 | 작업 ID | 목표 | 채우는 파일 | 완료 기준 |
| --- | --- | --- | --- | --- |
| A | `TASK-입력읽기` | 국가·일수·스타일을 읽어 담기 | `research_data.request` | request 칸이 채워짐 |
| A | `TASK-국가정보` | 기능1 칸 전부 채우기 | `research_data.country_intro` | 다건 4항목 × 3건, 단건·조건부·자산 충족 |
| A | `TASK-도시선정` | 우선순위(내 취향 → 유명도 → 교통)대로 도시 고르고 이유 적기 | `research_data.cities[].name` | 도시 1개(오사카)와 why_selected |
| A | `TASK-명소수집` | 관광지 · 근거 · 사진 · 취향 설명 | `research_data.cities[].spots` | 도시당 3곳, 취향 설명 15줄 이상 |
| A | `TASK-일정수집` | 일정 근거 모으고 일자별 계획 짜기 | `research_data.cities[].itinerary` | 도시마다 4일치, 일정 근거 2건 |
| B | `TASK-페이지생성` | 단일 HTML 만들기 | `output/travel_site.html` | 기능 1·2·3 구조 생성 |
| B | `TASK-기능점검` | 눌리는 연결 붙이고 빠진 칸 채우기 | `output/travel_site.html` | 루프 B 검사기 통과 |

| 결정 ID | 확정 값 | 고른 이유 | 승인 시각 |
| --- | --- | --- | --- |
| `D-작업목록` | 권장 7개 (루프 A 5개 · 루프 B 2개) | 권장값. 부족한 칸의 작업만 다시 돌리기 좋음 | 2026-10-23 |
| `D-수정금지파일` | `specs/**` `scripts/**` `templates/**` `CLAUDE.md` `MASTER_SPEC.md` `LOOP_CONTRACT.md` | 권장값 C. 기준을 낮춰 통과하는 길을 전부 막음 | 2026-10-23 |
| `D-사람확인지점` | 루프 A 끝 · 루프 B 끝 · 루프 C 끝 | 권장값 | 2026-10-23 |

<!-- MACHINE:BEGIN -->
```json
{
  "step": 4,
  "produces": "spec_only",
  "decisions": {
    "D-작업목록": [
      {"id": "TASK-입력읽기", "loop": "A", "goal": "국가·일수·스타일 읽어 담기", "files": ["output/research_data.json"]},
      {"id": "TASK-국가정보", "loop": "A", "goal": "기능1 칸 전부 채우기", "files": ["output/research_data.json"]},
      {"id": "TASK-도시선정", "loop": "A", "goal": "우선순위대로 도시 고르고 이유 적기", "files": ["output/research_data.json"]},
      {"id": "TASK-명소수집", "loop": "A", "goal": "관광지·근거·사진·취향 설명 모으기", "files": ["output/research_data.json"]},
      {"id": "TASK-일정수집", "loop": "A", "goal": "일정 근거 모으고 일자별 계획 짜기", "files": ["output/research_data.json"]},
      {"id": "TASK-페이지생성", "loop": "B", "goal": "단일 HTML 만들기", "files": ["output/travel_site.html"]},
      {"id": "TASK-기능점검", "loop": "B", "goal": "눌리는 연결 붙이고 빠진 칸 채우기", "files": ["output/travel_site.html"]}
    ],
    "D-수정금지파일": ["specs/**", "scripts/**", "templates/**", "CLAUDE.md", "MASTER_SPEC.md", "LOOP_CONTRACT.md"],
    "D-사람확인지점": ["루프 A 끝", "루프 B 끝", "루프 C 끝"]
  },
  "fixed": {
    "loops": [
      {"id": "A", "name": "정보량 충족", "order": 1,
       "verifier": "python scripts/check_information_count.py"},
      {"id": "B", "name": "페이지 완성", "order": 2,
       "verifier": "python scripts/check_page_contract.py"},
      {"id": "C", "name": "정성 완성도", "order": 3, "owner": "킷 고정",
       "verifier": "python scripts/check_quality_passes.py"}
    ],
    "loop_order_rule": "앞 루프가 통과하기 전에는 뒤 루프를 판정하지 않는다",
    "quality_task": {"id": "TASK-정성점검", "loop": "C", "owner": "킷 고정",
                     "goal": "규율 10가지로 3회 점검하고 고친다",
                     "files": ["output/travel_site.html", "output/research_data.json",
                               "evidence/runs/<run_id>/quality/"]},
    "editable_paths": ["USER_REQUEST.md", "PROJECT_MEMORY.md", "output/**", "src/**", "state/**", "evidence/runs/**"],
    "role_matrix": {
      "LLM": ["스타일 읽기", "검색어 생성", "요약", "글쓰기", "실패 원인 분류"],
      "CODE": ["개수 세기", "칸 존재 확인", "종료 코드 판정"],
      "HUMAN": ["명세 변경 승인", "루프 사이 되물음 답하기", "최종 확인"]
    },
    "memory_files": ["CLAUDE.md", "PROJECT_MEMORY.md", "state/loop_state.json"],
    "evidence_dir": "evidence/runs/<run_id>/",
    "evidence_per_iteration": [
      "명령", "종료 코드", "실패 유형", "오류 지문",
      "바꾼 파일", "다음 행동", "로그 경로"
    ],
    "never_store": ["API 키", "토큰", "개인정보", "모델의 비공개 사고 과정 전체"],
    "reverse_question_fields": ["채운 것", "못 채운 것", "선택지 2~3개와 각각의 결과"],
    "failure_types": [
      "CODE_ERROR", "TEST_ERROR", "SPEC_CONFLICT", "ENVIRONMENT_ERROR",
      "PERMISSION_ERROR", "INFORMATION_INSUFFICIENT", "UNKNOWN_ERROR"
    ]
  },
  "inherited": {
    "city_count": 1,
    "spots_per_city": 3,
    "page_layout": {"feature1": "accordion", "feature2": "drawer", "feature3": "accordion"}
  }
}
```
<!-- MACHINE:END -->

<!-- EXAMPLE:BEGIN -->
> **[작성 예시 — 실제 결정이 아닙니다]**
>
> ```json
> "D-작업목록": [
>   {"id": "TASK-입력읽기", "loop": "A", "goal": "국가·일수·스타일 담기",
>    "files": ["output/research_data.json"]}
> ],
> "D-사람확인지점": ["루프 A 끝", "루프 B 끝", "루프 C 끝"]
> ```
<!-- EXAMPLE:END -->

<!-- PROJECT:END -->

---

## 읽기 7 — 이 STEP이 끝나면 무엇이 진행되는가

| 항목 | 내용 |
| --- | --- |
| **지금 코드가 만들어지나?** | **아니오.** 작업 이름과 순서만 정합니다. |
| **Claude가 실제로 하는 일** | ① 작업을 루프별로 정리 → ② 읽기 6의 작업표 채우기 → ③ 결정 장부에 추가 → ④ STEP 5·6·7의 물려받은 값 갱신 |
| **바뀌는 파일** | `specs/04_BOUNDARY_TASKS_SAFETY.md` · `specs/00_DECISION_LOG.md` · `PROJECT_MEMORY.md` · `specs/05_TEST_AND_VERIFIER.md` · `specs/06_LOOP_ITERATION.md` · `specs/07_EXECUTION_CONTRACT.md` |
| **내가 지금 실행할 명령** | Claude Code에 `STEP 4 진행해줘` → 질문에 답 → `python scripts/validate_specs.py --step 4` |

---

## 읽기 8 — 완료 확인과 다음 명령

- [ ] 모든 작업에 `loop` 가 `A` 또는 `B`로 적혀 있다
- [ ] 루프 A와 루프 B에 작업이 각각 1개 이상 있다
- [ ] 루프 C(정성 완성도)는 **킷 고정**이라 내가 고를 것이 없다는 것을 확인했다
- [ ] 수정 금지 목록에 `specs/**` 와 `scripts/**` 가 들어 있다
- [ ] 되물음을 띄울 지점이 정해졌다
- [ ] 상태가 `APPROVED`다

```bash
python scripts/validate_specs.py --step 4
```

<!-- STATUS:BEGIN -->
STATUS: APPROVED
<!-- STATUS:END -->

```text
STEP 5 진행해줘
```
