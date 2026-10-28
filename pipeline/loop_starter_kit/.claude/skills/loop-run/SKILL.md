---
name: loop-run
description: AORR 실행 루프 세 개를 돌린다. "루프를 실행해줘", "구현 시작해줘", "정보 모아줘", "페이지 만들어줘", "정성 점검해줘", "루프 이어서 돌려줘" 같은 요청에서 사용한다. 루프 A(정보량) → 루프 B(페이지) → 루프 C(정성 3회) 순서로 돈다.
user-invocable: true
argument-hint: "[이어서 / A / B]"
---

# loop-run — AORR 실행 루프 세 개

## 활성화 조건

- STEP 7이 `APPROVED`이고 준비도가 `READY`인 상태에서 구현을 요청할 때
- `/loop-run` 직접 호출
- 중단된 루프를 이어서 실행할 때

명세가 아직 완성되지 않았다면 이 Skill이 아니라 `step-spec-builder`를 쓴다.

---

## 시작 게이트 (반드시 먼저)

```bash
python scripts/check_loop_readiness.py
```

이 명령이 **판정기 셀프테스트를 먼저 돌린다.** 채점표가 살아 있는지 확인하지 않고
채점을 시작하지 않기 위해서다. 결과에 `검사기 셀프테스트` 행이 `[OK]` 여야 한다.

| 결과 | 행동 |
| --- | --- |
| `READY` (exit 0) | 출력이 `잠금 확인됨 (N개 · 변경 없음)` 이면 그대로 루프 시작 (다시 잠그지 않는다). 잠금이 없으면 `--lock`으로 보호 파일을 잠그고 루프 시작 |
| `NOT_READY` (exit 2) | **구현하지 않는다.** 남은 항목을 보여 주고 `step-spec-builder`로 안내한다 |
| `ERROR` (exit 1) | **구현하지 않는다.** 깨진 파일을 보고하고 사람에게 넘긴다 |

---

## 절대 규칙

1. **검사 스크립트를 만들지도, 고치지도 않는다.** `scripts/` 안의 판정기는 이미 완성되어 있다.
2. **루프 A가 통과하기 전에는 루프 B를 시작하지 않는다.**
3. **첫 바퀴는 그 루프의 작업 목록을 순서대로 한 번씩** 돌린 뒤 판정기를 한 번 돌린다. **다음 바퀴부터는 부족으로 지적된 칸의 작업만** 다시 한다. 지적되지 않은 칸은 손대지 않는다.
4. 검사기를 먼저 실행한다. **실패 증거 없이 수정하지 않는다.**
5. `RESEARCH`일 때는 **부족한 칸만** 다시 모은다. 전부 다시 하지 않는다.
6. 보호 파일(`specs/**`, `scripts/**`, `templates/**`, `CLAUDE.md`, `MASTER_SPEC.md`, `LOOP_CONTRACT.md`)을 수정하지 않는다.
7. 기준을 낮추고 싶으면 **명세를 바꾼다.** 그것은 `spec-sync`의 일이고 사람의 승인이 필요하다.
8. 최종 검증 명령이 통과하지 않은 상태에서 완료를 선언하지 않는다.
9. 무한 재시도하지 않는다. 상한을 넘으면 **되물음**을 띄운다.
10. **못 채운 칸을 숨기지 않는다.** 넘어가더라도 보고서에 그대로 적는다.
11. **루프 C는 정확히 3회 돈다.** 줄이지도 늘리지도 않는다. 결과가 좋아 보여도 3회를 채운다.
12. **정성 수정이 루프 A·B를 깨뜨리면 그 회차 수정을 되돌린다.** 회차 끝마다 반드시 확인한다.

---

## 실행 순서

전체 그림은 `specs/00_DECISION_LOG.md`의 **5번 루프 구조도**에 있다. 막히면 그것을 먼저 본다.

```text
5-1   큰 그림 — 처음부터 끝까지
5-1b  한 바퀴 안에서 무슨 일이 (루프 A·B 는 같은 모양)
5-1c  루프 C만 모양이 다르다 — 통과선이 없는 루프
5-2   실패하면 어디로 가나
```

### 0) 준비

- `CLAUDE.md` → `PROJECT_MEMORY.md` → `MASTER_SPEC.md` → `LOOP_CONTRACT.md` → `USER_REQUEST.md` 순으로 읽는다.
- `state/loop_state.json`이 없으면 `state/loop_state.example.json`을 복사해 만든다.
- `evidence/runs/<run_id>/`를 만든다. `run_id`는 시각 기반(예: `2026-09-05T14-20-05`).
- `run_manifest.json`에 시작 시각·국가·일수·검사 계약 요약을 기록한다.
  시작 시각은 **`started_at` 키에 ISO 시각**(예: `2026-09-05T14:20:05`)으로 적는다 (`evidence/README.md` 2번 형식).
- `state/loop_state.json`을 갱신할 때마다 **`updated_at`에 ISO 시각**을 적는다.
  인계본이 `started_at` → `updated_at`으로 루프판 전체 시간을 잰다.

### 1) 빨간불 확인 (RED)

```bash
python scripts/verify_all.py
```

`output/`이 비어 있으므로 **반드시 `SHORT`(exit 2)** 가 나온다. 이것이 출발점이다.
여기서 바로 `PASS`가 나오면 명세가 비어 있다는 뜻이므로 멈추고 확인한다.
`events.jsonl`에 남길 때는 **`iteration: 0`** · `failure_type: null` 로 적는다 — 반복이 아니라 출발점이라
바퀴로 세지 않고, 인계본도 실패로 세지 않는다.

### 2) 루프 A — 정보량 충족

작업 순서는 `LOOP_CONTRACT.md`의 루프 A 목록을 따른다.
**첫 바퀴는 아래 작업을 순서대로 한 번씩 모두 한 뒤 판정기를 한 번 돌린다.** 판정기는 `research_data.json`
전체를 보므로 작업 하나마다 판정하지 않는다 (첫 수집이 끝나기 전의 판정은 SHORT 가 정해져 있다).
다음 바퀴부터는 **부족으로 지적된 칸의 작업만** 다시 한다.

| 작업 | 하는 일 |
| --- | --- |
| `TASK-입력읽기` | `USER_REQUEST.md`에서 국가·일수·스타일을 읽어 `research_data.request`에 담는다 |
| `TASK-국가정보` | 매력·역사·문화·주의사항(다건) · 국가상태(조건부) · 항공권·환율·교통(단건) · 국기·대표 이미지(자산) |
| `TASK-도시선정` | `D-도시선정기준` 순서대로 도시를 고르고 `why_selected`에 이유를 적는다 |
| `TASK-명소수집` | 도시마다 관광지 · 근거 · 사진 · 상세 소개 · 취향 설명 |
| `TASK-일정수집` | 도시마다 일정 근거를 모으고 일자별 계획을 짠다 |

**정보를 모을 때**

- 웹 검색을 쓴다. 출처 등급을 따지지 않는다. 블로그·카페도 내용이 좋으면 쓴다.
- `다건` 항목은 **서로 다른 출처 2곳 이상**에서 모은다.
- **글자 수 하한은 `MASTER_SPEC.md`의 `count_contract.min_chars`에서 읽는다.**
  하한은 최소일 뿐 목표가 아니다. **기준을 넘겼다고 문장을 끊지 않는다.**
- **같은 문장을 복사해 칸을 채우지 않는다.** 번호만 바꿔 복제하면 `dedup` 검사에 걸린다.
  쓸 말이 없으면 줄 수를 채우지 말고 **조사를 더 한다.**
- 취향 설명(`preference_note`)은 **줄 단위**로 쓰고, 줄마다 계약의 최소 글자 수를 넘긴다.
  "A 관광지에는 사진 스팟 xxx가 있습니다" / "B의 박물관 yyy는 취향이 아니라 뺐습니다" 처럼
  **넣은 이유와 뺀 이유를 함께** 적는다.

**이미지 — 주소를 기억으로 쓰지 않는다 (가장 자주 깨지는 곳)**

```text
1  검색이나 조회로 실제 파일명을 얻는다
2  주소를 만든다   https://commons.wikimedia.org/wiki/Special:FilePath/<파일명>?width=1024
3  실제로 열어 본다 (status / content_type 확인)
4  image.verified 에 status · content_type · checked_at 을 적는다

금지  upload.wikimedia.org/...  (thumb·원본 모두. 검사기는 이 글자가 든 주소를 전부 막는다)
      특히 .../thumb/<알 수 없는 두 글자>/... 의 두 글자는 파일명 해시에서 나온 값이라 만들어 낼 수 없다.
      실제로 이 형태로 11장을 적었다가 전부 죽은 주소였던 적이 있다.
```

**일정 — 도시마다 따로, 시간 단위로**

```text
도시마다  여행 일수만큼의 일정을 각각 짠다. 도시들을 합쳐서 일수를 세지 않는다.
하루     계약의 blocks_per_day_min 개 이상. start 와 end 는 HH:MM.
블록     kind 는 명소 · 식사 · 이동 · 휴식 중 하나.
         kind 가 명소이면 spot 은 그 도시에서 실제로 조사한 관광지여야 한다.
         시간은 앞뒤가 겹치지 않고 이어져야 한다.
         why 에는 왜 이 시간에 여기인지를 적는다.
```

> 도시별 일정이 서로 **이름만 바꾼 같은 글**이면 유사도 검사에 걸린다.
> 그 도시에서만 가능한 내용을 쓴다.

**판정**

```bash
python scripts/check_information_count.py
```

| 결과 | 행동 |
| --- | --- |
| exit 0 | 되물음 → 루프 B로 |
| exit 2 | `INFORMATION_INSUFFICIENT` → `RESEARCH` — **부족으로 표시된 칸만** 다시 |
| exit 1 | `HITL` — 명세나 파일이 깨졌다 |

### 3) 루프 A 끝 — 되물음

`templates/REVERSE_QUESTION.md` 형식으로 사람에게 묻는다. 답은 `PROJECT_MEMORY.md` 7번에 남긴다
(`specs/**`는 잠겨 있어 결정 장부에 쓰지 않는다).
못 채운 칸 0 으로 통과했으면 **'통과했을 때' 양식** — `[2] 다음 루프로 넘어간다 ← 권장`, `HALT_*` 안내를 붙이지 않는다.
부족이 남았으면 **'부족이 남았을 때' 양식**을 쓴다. 루프 B 끝 되물음도 같다.

### 4) 루프 B — 페이지 완성

작업 순서는 `LOOP_CONTRACT.md`의 루프 B 목록을 따른다. 바퀴의 뜻은 루프 A 와 같다 —
첫 바퀴는 작업을 순서대로 한 번씩, 다음 바퀴부터는 지적된 칸만 고친다.

| 작업 | 하는 일 |
| --- | --- |
| `TASK-페이지생성` | `research_data.json`을 읽어 `output/travel_site.html` 뼈대와 내용을 만든다 |
| `TASK-기능점검` | 아코디언 · 우측 툴바 · 관광지 상세 · 뒤로 가기를 클릭 핸들러로 잇고, 빠진 칸을 채운다 |

**검사기는 이름표의 존재만 보지 않는다. 세 가지를 더 본다.**

```text
어디에 있는가   도시 칸·관광지·상세·취향 설명·뒤로 가기는 툴바 안
                (도시 단추는 기능2 구역 안인지만 본다 — 툴바 밖 배치는 계약이지만 검사하지 않는다)
처음에 닫혔는가  툴바 · 관광지 상세 · 아코디언 패널   (hidden · display:none · CSS 클래스)
코드로 이었는가  주석이나 쓰이지 않는 문자열은 통과하지 않는다.
                querySelector · closest · getElementById 안에서 그 이름표를 써야 한다
```

> 이 세 가지가 없던 때에는 **전부 펼쳐진 평면 문서에 빈 껍데기 툴바 하나**가
> 만점을 받았다. 자세한 계약은 `specs/02_PAGE_DESIGN.md` 읽기 3에 있다.

`output/travel_site.html` **파일 하나**를 만든다.

- CSS와 JavaScript를 그 파일 **안에** 넣는다. 바깥 파일을 만들지 않는다.
- `STEP 2`의 이름표(`data-*`)를 **그대로** 쓴다. 이름표를 바꾸면 검사기가 못 찾는다.
- 기능3은 **도시마다** 일정을 담는다. `data-day` 칸은 그 도시의 아코디언 패널 **안에** 둔다.
  하루 안에는 `data-block="HH:MM-HH:MM"` 을 계약이 정한 개수 이상 넣는다.
- 기능1 헤더 5개에 정보 슬롯 8개를 넣는다. 대응은 `page_contract.header_slots`에 있다.
  `국가상태`에 모은 것이 없으면 **"확인했으나 특별한 내용 없음"**이라고 적는다. 빈 칸으로 두지 않는다.
- 내용은 `research_data.json`에서 가져온다. **새로 지어내지 않는다.**
- 이미지는 `onerror`로 대체 박스를 띄운다.
- 아코디언 · 우측 툴바 · 관광지 상세 · 뒤로 가기를 **클릭 핸들러로 연결**한다.

**판정**

```bash
python scripts/check_page_contract.py
```

| 결과 | 행동 |
| --- | --- |
| exit 0 | 되물음 → 루프 C로 |
| exit 2 | `CODE_ERROR` → `RETRY` — **부족으로 표시된 칸만** 고친다 |
| exit 1 | `HITL` |

### 5) 루프 C — 정성 완성도 (정확히 3회)

여기서부터는 **세는 것으로 잡히지 않는 결함**을 다룬다.
규율은 `specs/QUALITY_RUBRIC.md` 10가지, 기록 양식은 `templates/QUALITY_PASS.md`.

> 루프 A·B를 되물음에서 **부족한 채 넘겼다면** `verify_all.py --skip-quality`가 exit 0이 될 수 없어
> 회차마다 수정을 되돌리게 된다. 그때는 루프 C를 시작하지 말고 되물음으로 알린 뒤 `HALT_*`로 끝낸다.

**한 회차의 절차 (그대로 따른다)**

```text
1  파일 해시를 적는다                      snapshot_before
2  규율 10개를 전부 판정한다                이번 회차의 렌즈부터 고친다
3  output/** 만 고친다                     명세와 검사기는 건드리지 않는다
4  python scripts/verify_all.py --skip-quality
      exit 0 이 아니면 이 회차 수정을 되돌린다
5  파일 해시를 다시 적는다                  snapshot_after
6  evidence/runs/<run_id>/quality/passN.json 에 기록
```

**회차마다 렌즈가 다르다** (계약의 `pass_focus`. 10개는 매번 전부 판정한다)

| 회차 | 렌즈 | 초점 |
| --- | --- | --- |
| 1 | 내용이 실한가 | 반복 · 취향 연결 · 뺀 이유 · 상세 3요소 |
| 2 | 실행 가능하고 사실인가 | 일정 현실성 · 근거 일치 · 도시 차별화 · 실용 누락 |
| 3 | 독자 관점에서 완결인가 | 동행 반영 · 계약 무결 + 앞 회차가 되돌아가지 않았는지 |

**정직하게 적는다**

```text
위반이라 적었으면 반드시 고친다.          적어 놓고 넘어가면 판정기가 잡는다
위반이면 where 에 자리를 적는다.          "-" 로 비우면 판정기가 잡는다
고칠 것이 없으면 applied_fix 를 비운다.    그때는 파일 해시가 그대로여야 한다
고친 척하면 해시가 바뀌어서 걸린다.
verify_after 는 실제로 돌린 결과를 적는다.  마지막 회차는 판정기가 직접 다시 돌려 맞춰 본다
```

> **3회 내내 수정이 0건이면 판정기가 `SHORT` 를 낸다.** 정말 흠이 없는 것과
> 보지 않고 넘어간 것을 기록만으로는 구분할 수 없기 때문이다. 그때는 실패가
> 아니라 **되물음**을 띄운다 — "한 회차를 다시 돈다 / 이대로 확정한다".
> "이대로 확정"을 고르면 `verify_all.py` 는 계속 exit 2(SHORT)이므로 `SUCCESS` 가 될 수 없다.
> 4회차를 돌지 말고 `HALT_NEEDS_HUMAN` 으로 끝낸다. 답은 `PROJECT_MEMORY.md` 7번에
> "정성 수정 0건 — 사람 확정"으로 남기고 `evidence-review` 로 넘긴다.

**해시 만드는 법**

```bash
python -c "import hashlib;print('sha256:'+hashlib.sha256(open('output/travel_site.html','rb').read()).hexdigest())"
```

**판정**

```bash
python scripts/check_quality_passes.py
```

| 결과 | 행동 |
| --- | --- |
| exit 0 | 되물음 → 최종 검증 |
| exit 2 | 남은 회차를 돈다 (실패가 아니라 진행 중이다). `next_action`은 `QUALITY`. 3회를 다 돌고 수정이 0건이면 → 되물음 (다시 돈다 / 확정 = `HALT_NEEDS_HUMAN`) |
| exit 1 | `HITL` — 기록이 깨졌다 |

> **3회를 다 돌기 전에 마치지 않는다.** 결과가 좋아 보여도 3회를 채운다.
> 반대로 3회를 넘겨 계속 다듬지도 않는다. 예산은 3회다.

### 6) 최종 검증

```bash
python scripts/verify_all.py
```

세 루프를 순서대로 본다. exit 0이면 성공 종료 — `events.jsonl`에 `next_action: DONE` 으로 한 줄 남긴다.
그 밖이면 2) · 4) · 5)로 돌아간다.

### 7) 그래프 인계본 (종료 뒤 언제나)

```bash
python scripts/export_graph_handoff.py
```

`output/graph/` 에 다음 강의로 넘길 것들이 모인다. `SUCCESS` 가 아니어도 만든다 —
**끝까지 못 간 실행일수록 실측에 남는 것이 많다.** exit 2 는 "인계본은 만들었지만
루프가 아직 안 끝났다"는 뜻이며(파일·기록이 빠졌거나, 다 있어도 `verify_all` 판정이 `SUCCESS` 가 아니다 —
`00_START_HERE.md` 상태가 '미완성'), 그대로 `evidence-review` 로 넘긴다.

---

## 실패 유형과 다음 행동 (고정)

| 실패 유형 | 다음 행동 |
| --- | --- |
| `CODE_ERROR` | `RETRY` — 최소 수정 |
| `TEST_ERROR` | `HITL` — 검사기를 마음대로 고치지 않는다 |
| `SPEC_CONFLICT` | `REVISE_SPEC` — 명세부터 고친다 |
| `ENVIRONMENT_ERROR` | `HITL` |
| `PERMISSION_ERROR` | `HITL` |
| `INFORMATION_INSUFFICIENT` | `RESEARCH` — 부족한 칸만 |
| `UNKNOWN_ERROR` | `STOP` |

```text
오류 지문 = sha256(검사기 이름 + 실패 유형 + 오류 첫 줄)
같은 지문이 D-무진전기준만큼 반복 = 진전 없음 → 되물음
```

**`HITL`이 나오면 무엇을 하나**

1. 고치려 들지 않는다. 그 자리에서 멈춘다.
2. `templates/REVERSE_QUESTION.md` 형식으로 **선택지 2~3개**를 만들어 사람에게 묻는다.
3. 사람의 답을 `PROJECT_MEMORY.md` 7번(되물음에서 내가 고른 답)에 남긴다. `specs/**`는 잠겨 있으므로 쓰지 않는다.
4. 답이 "계속"이면 그 지점부터 이어서 돈다. "명세를 바꾸자"면 `spec-sync`로 넘긴다.
   "멈춘다"면 `evidence-review`로 넘겨 보고서를 만든다.

**`REVISE_SPEC`이 나오면 무엇을 하나**

명세를 직접 고치지 않는다. `spec-sync`로 넘긴다.
명세가 바뀌면 잠금과 어긋나 준비도 검사가 `ERROR`를 내고, `ERROR`일 때는 `--lock`도 거부된다.
그래서 **사람이 `state/spec_lock.json`을 지운 뒤** 고치고 → `READY` 확인 → `--lock`을 다시 걸어야 루프를 이어갈 수 있다.

---

## 상한에 걸렸을 때 — 멈추지 말고 되물음

```text
[되물음] 루프 A를 3바퀴 돌았지만 2칸을 못 채웠습니다.
  못 채운 것 : 후에 황제릉 사진 · 다낭 일정 근거 1건
  같은 오류가 2번 반복되었습니다
  고르세요
   [1] 한 바퀴만 더 돈다
   [2] 부족한 채로 루프 B로 넘어간다   ← 권장
   [3] 여기서 멈춘다
```

같은 오류가 반복됐다면 **[2]를 권한다.** 인터넷에 없는 정보는 더 돌아도 없다.

---

## 종료 판정

| 조건 | 종료 상태 |
| --- | --- |
| 성공 조건 충족 | `SUCCESS` |
| 같은 오류 지문이 상한만큼 반복되고 사람이 멈춤을 고름 | `HALT_NO_PROGRESS` |
| 정보를 끝내 못 채우고 사람이 멈춤을 고름 | `HALT_RESEARCH_GAP` |
| 명세끼리 어긋남 | `HALT_SPEC_CONFLICT` |
| 권한 부족 · 보호 파일 필요 | `HALT_PERMISSION` |
| 실행 환경 문제 | `HALT_ENVIRONMENT` |
| 사람 결정 필요 | `HALT_NEEDS_HUMAN` |

종료되면 `evidence-review` Skill로 넘겨 보고서를 만든다.

---

## 매 반복 기록

`evidence/runs/<run_id>/events.jsonl`에 한 줄씩 추가한다.

```json
{"iteration":3,"loop":"A","task_id":"TASK-명소수집",
 "command":"python scripts/check_information_count.py","exit_code":2,
 "failure_type":"INFORMATION_INSUFFICIENT","error_hash":"sha256:...",
 "short_slots":["다낭/한강다리 이미지"],"changed_files":["output/research_data.json"],
 "next_action":"RESEARCH","log_path":"test_results/iter03.txt"}
```

`state/loop_state.json`도 함께 갱신한다.

`next_action`은 실패 라우팅 값(`RETRY` · `RESEARCH` · `REVISE_SPEC` · `HITL` · `STOP`) 말고 세 가지가 더 있다.
**되물음을 띄운 반복은 통과든 상한이든 `REVERSE_QUESTION`**, 루프 C가 남은 회차를 도는 반복은 `QUALITY`,
최종 검증(`verify_all.py` exit 0)으로 정상 종료한 줄은 `DONE`으로 적는다. 이 셋은 실패가 아니다.
인계본(`export_graph_handoff.py`)은 `REVERSE_QUESTION` · `HITL` 줄 수를 **사람 호출 횟수**로 세고,
`failure_type` 이 적혔거나 다음 행동이 실패 라우팅이면서 검사기가 통과하지 않은 줄만 **실패**로 센다
(출발점 RED 줄 `iteration: 0` 은 세지 않는다).

기록하지 않는 것: API 키, 토큰, 개인정보, 모델의 비공개 사고 과정 전체.

---

## 보고 형식

```text
루프 종료
상태      : SUCCESS
루프 A    : 3바퀴  exit 0
루프 B    : 2바퀴  exit 0
루프 C    : 3/3회  exit 0
최종 명령 : python scripts/verify_all.py  exit 0
채운 칸   : 42 / 42
못 채운 칸: 없음
정성 수정 : 1회차 복제 21줄 교체 · 2회차 일정 시간 재배치 · 3회차 고칠 것 없음
바꾼 파일 : output/research_data.json, output/travel_site.html
증거      : evidence/runs/2026-09-05T14-20-05/
다음      : output/travel_site.html 을 브라우저로 열어 확인해 주세요
           사진이 그 관광지가 맞는지는 기계가 볼 수 없습니다
```

`SUCCESS`가 아니면 성공했다고 쓰지 않는다.
**못 채운 칸이 있으면 반드시 목록으로 적는다.**
