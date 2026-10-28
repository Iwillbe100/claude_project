# STEP 1 — 조건① 상태 스키마

> **한 줄 목적:** 노드 사이에 **무엇이 흐를지** 정한다.
> **내가 결정할 것: 3개** · **코드 변경: 권장값이면 없음** (다른 값을 고르면 `travel_graph/state.py` 의 필드 목록)

| 이전 | 다음 | 문서 규칙 | 결정 장부 |
| --- | --- | --- | --- |
| — | [STEP 2 — 노드 경계](02_NODE_BOUNDARY.md) | [00_INDEX](00_INDEX.md) | [00_DECISION_LOG](00_DECISION_LOG.md) |

---

## 읽기 1 — 이 STEP에서 정하는 것

**루프의 조건① '시작 상태'가 여기로 옵니다.** 다만 뜻이 넓어집니다.

```text
루프에서   시작 상태 = "무엇을 입력으로 받나"        국가 · 일수 · 스타일
그래프에서 상태     = "노드 사이에 흐르는 전부"       입력 + 수집물 + 판정 + 원인 + 제어
```

왜 넓어지는가 — **노드는 서로를 모르기 때문**입니다. `check_information` 은
`collect_city` 가 무엇을 했는지 볼 수 없습니다. 상태에 적힌 것만 봅니다.

```text
루프          한 프로세스 안. 변수를 그냥 공유하면 됐다.
그래프        노드가 각자 돈다. 공유하려면 상태에 적어야 한다.
```

---

## 읽기 2 — 앞에서 물려받은 결정

<!-- PROJECT:BEGIN -->

| 물려받은 것 | 값 | 어디서 |
| --- | --- | --- |
| 국가 · 일수 | (인계본에서 읽음) | `graph/03_CONTRACT.json` `request` |
| 개수 계약 | (인계본에서 읽음 — 예시본: 도시 3 · 관광지 3 · 취향 15줄) | `graph/03_CONTRACT.json` `count_contract` |
| 상한 | (인계본에서 읽음 — 예시본: A 3바퀴 · B 3바퀴 · 같은 오류 2회) | `graph/03_CONTRACT.json` `loops` · `options.same_error_limit` |

<!-- PROJECT:END -->

---

## 읽기 3 — 이미 정해 둔 것 (읽고 넘어가기)

### (1) 상태는 매 노드마다 저장된다 (고정)

```text
노드가 끝날 때마다  상태 전체가 직렬화되어 체크포인터에 저장된다
노드를 N번 지나면   상태 크기 × N 번 저장된다
                    (그림의 노드는 22개 · 진단 노드는 검사기 뒤에서 매번 지난다)
```

그래서 **본문을 상태에 넣으면 안 됩니다.** 경로만 넣습니다.

```text
좋은 State                     나쁜 State
  info_verdict     "SHORT"       raw_html        "<html>...30만자..."
  info_short_slots ["이미지"]     everything      {...}
  html_path        "output/..."  temp_result     ...
  loop_a_iter      2             result1, result2
```

### (2) 노드는 **변경분만** 돌려준다 (고정)

```python
def collect_country(state):
    return {"country_intro": intro}      # 이 키만 바뀐다
    # 상태 전체를 돌려주지 않는다. 그럴 필요가 없다.
```

### (3) 킷이 이미 넣어 둔 필드 (고정 — 지우지 마세요)

| 묶음 | 필드 | 누가 쓰나 | 누가 읽나 |
| --- | --- | --- | --- |
| 입력 | `country` `days` `style` `city_priority` | `read_request` | 전부 |
| 수집 | `country_intro` `selected_city_names` `cities` | 수집 노드 | 검사기 · 페이지 |
| 수집 실패 | `city_failures` | 수집 · 재수집 노드 (fan-out 으로 동시에) | 게이트 화면 `② 왜` |
| 판정 | `info_verdict` `info_short_slots` `page_verdict` `page_short_slots` `quality_verdict` `quality_short_slots` | 검사기 노드 | **라우터 전용** |
| 산출물 | `html_path` `research_path` | `build_page` `check_information` | 사람 |
| 제어 | `loop_a_iter` `loop_a_limit` `loop_b_iter` `loop_b_limit` `same_error_count` `same_error_limit` `last_error_hash` | 검사기 노드 | 라우터 |
| **정성** | **`quality_pass` `quality_passes_required`** | `quality_pass` 노드 · `read_request` | `route_after_quality` |
| 사람 | `gate_a_answer` `gate_b_answer` `gate_note` | 게이트 노드 | 라우터 |
| 기록 | `history` | 모든 노드 | 사람 (Studio 화면) |
| **입력 (실패 재현)** | `inject` | 입력 → `read_request` 가 정리 (모르는 이름은 버리고 적는다) | `collect_city`(첫 도시) · `collect_country` |
| **원인** | `failure_kind` | 진단 노드 (`diagnose_info` · `diagnose_page`) | **라우터** · `fix_detour` · `test_detour` |
| 원인 | `failure_evidence` | 진단 노드 · `test_detour` | 게이트 화면 `② 왜` — **라우팅에 쓰지 않는다** |
| **처방 가지 제어** | `detour_attempts` | `fix_detour` (게이트에서 `more` · `research` · `rebuild` 를 고를 때만 `{}` 로 비운다) | 라우터 · 진단 노드 |
| 처방 가지 제어 | `detour_limit` | `read_request` (처방 한도 2회) | 라우터 · 진단 노드 |
| 처방 가지 제어 | `detour_verdict` | `test_detour` (검사기 노드가 읽고 비운다) | `route_after_detour` · `check_information` · `check_page` |

**킷이 넣어 둔 칸은 모두 35개입니다** (루프 C 까지 29개 + 진단 · 처방 가지 6개). 표의 마지막 여섯 칸은
전부 킷 고정이고 reducer 가 없습니다 — 이유는 아래 (3-c) 에 있습니다.

### (3-b) ★ 회차 카운터에는 reducer 를 붙이지 않습니다 (고정)

루프 C(정성 완성도)가 들어오면서 제어 필드 4개가 늘었습니다. **전부 킷 고정**이라
결정할 것은 없지만, 한 가지만 손에 익혀 두어야 합니다.

```python
quality_pass: Annotated[int, operator.add]   # 잘못.  1회차 1 → 2회차 1+2=3 → 한 회차를 건너뛰고 나간다 (정성 2회만 돈다)
quality_pass: int                            # 맞음.  덮어쓰기
```

STEP 4 에서 `cities` 에 reducer 를 붙이는 것을 배우고 나면 **카운터에도 붙이는
실수**가 잦습니다. 회차 번호는 "여러 노드가 동시에 쓰는 값"이 아니라
**한 노드가 순서대로 갱신하는 단일 정수**입니다.

```text
reducer 가 필요한 것    여러 갈래가 같은 칸에 동시에 쓴다          cities · city_failures · history
reducer 를 붙이면 안 되는 것  한 노드가 차례로 덮어쓴다            quality_pass · loop_a_iter
```

`check_graph_shape.py` 의 **8번 검사**가 `*_pass` · `*_iter` · `*_count` 인
정수 필드에 reducer 가 붙었는지 봅니다. 3번 검사(빠진 reducer)로는 못 잡는 실수라
따로 만들었습니다.

### (3-c) ★ 판정 칸과 원인 칸을 나눕니다 — 진단 · 처방 가지 칸 6개 (고정)

검사기 뒤에 **진단 노드**가 섰습니다 (STEP 2 읽기 3 (8)). 그 노드가 쓰는 칸과 규칙 처방 가지가
쓰는 칸 6개가 늘었습니다. **전부 킷 고정**이라 결정할 것은 없지만, 네 가지는 짚고 갑니다.

```text
판정   info_verdict  "PASS"                      검사기 노드가 쓴다   기준을 채웠나
원인   failure_kind  "encoding"                  진단 노드가 쓴다     무엇이 터졌나
                     └ 판정이 PASS 여도 원인이 있을 수 있다 (깨진 글자는 검사기가 세지 않는다)
```

**① 판정과 원인은 다른 칸입니다.** 검사기(루프 킷과 바이트 단위로 같은 파일)는 세기만
합니다. "부족 9곳"은 말해도 "그중 1곳은 죽은 사진 주소"는 말하지 못하고, 고칠 수도
없습니다. 원인은 진단 노드가 시험지를 풀어 **따로** 적고, 라우터가 두 칸을 나란히 읽습니다.
한 칸에 섞으면 판정 칸이 검사기 말고 다른 손도 타게 되어 판정 독립이 흐려집니다.

**② `failure_kind` 는 라우팅에 쓰고, `failure_evidence` 는 쓰지 않습니다.**

```text
failure_kind      ""  또는 등록부(registry.py)에 있는 이름    닫힌 값   → 라우터가 읽는다
failure_evidence  "[image_dead] <어느 사진>: <왜 죽었나>"   자유 문장 → 사람이 읽는다 (게이트 ② 왜)
```

`gate_note` 와 같은 이유입니다 — 제어가 문장 해석에 좌우되면 안 됩니다
(`G-라우터판단` B "허용값이 정해진 필드만 본다"). `check_graph_shape.py` **5번 검사**가
라우터 소스에 `failure_evidence` 가 나오면 잡습니다. 그리고 증상은 **몇 줄만** 담습니다.
전부는 실패 기록 파일(`evidence/failures/<thread_id>.jsonl`)에 둡니다 — (1) 의 "본문을
상태에 넣지 않는다"와 같은 규칙입니다.

**③ `detour_attempts` 는 dict 지만 reducer 없이 통째로 덮어씁니다.**

```python
detour_attempts: dict                          # 맞음.  {처방 가지 이름: 이번에 몇 번 돌았나}
detour_attempts: Annotated[dict, 합치는 함수]    # 잘못.  게이트가 {} 로 비워도 안 비워진다
```

처방 가지는 **한 번에 하나만** 돕니다 — 진단이 하나를 고르고, `fix → test` 는 순차입니다.
같은 걸음에 이 칸을 쓰는 노드가 둘일 수 없으니 합칠 일이 없습니다. `fix_detour` 가 읽은
dict 를 복사해 자기 가지만 +1 하고 **통째로 돌려줍니다.** 여기에 합치는 reducer 를
붙이면, 사람이 게이트에서 `more` · `research` · `rebuild` 를 골라 `{}` 를 돌려줘도 옛 값에
합쳐질 뿐 비워지지 않습니다 — **처방 한도가 새로 차지 않아** 가지가 다시 서지 못합니다.
(3-b) 의 회차 카운터와 같은 종류의 실수입니다. 다만 이름이 `*_count` 가 아니고 dict 라
8번 검사의 이름 규칙에는 걸리지 않습니다 — 그래서 여기에 적어 둡니다.

**④ `detour_verdict` 는 검사기 노드가 읽고 비웁니다.** 시험 노드가 `PASS` 를 적고 검사기로
돌아오면, 검사기는 그 방문을 **바퀴(`loop_a_iter` · `loop_b_iter`)로 세지 않습니다** — 처방 가지는
자기 한도(처방 한도 `detour_limit`)를 따로 갖기 때문입니다. 그리고 곧바로 `""` 로 비웁니다. 비우지
않으면 다음 정상 방문까지 "복귀"로 읽혀 바퀴가 영영 오르지 않고, 상한이 사라집니다.

`inject` 는 **실패 재현(inject)** 입력입니다. 평소에는 비워 둡니다(`[]`). 이미 있는 가지가 켜지는
것을 보거나, 새 가지의 시험지 빨간불을 먼저 볼 때 그 실패를 다시 일으키는 장치입니다 — 등록된
처방 가지 이름을 적으면 수집 직후 그 실패를 다시 일으키고, 진단 노드가 찾아 처방 가지로 보냅니다.
`read_request` 가 모르는 이름을 버리고 **버렸다고 history 에 적습니다**
(`↳ 모르는 inject 이름을 버렸습니다: … (고를 수 있는 것: …)`).

### (4) 입력 스키마와 출력 스키마를 따로 두는 이유 (고정)

```python
StateGraph(TravelState, input_schema=TravelInput, output_schema=TravelOutput)
#                       └ Studio 입력 폼이 이걸로 그려진다 (5칸만 보인다)
#                                              └ 결과 패널에 이것만 나온다 (16칸)
```

상태 전체를 Studio 폼에 그리면 칸이 35개가 됩니다. 실습이 불가능해집니다.

입력 5칸은 `country` · `days` · `style` · `city_priority` · **`inject`** 입니다. 앞의 넷은
비워 두면 `read_request` 가 인계본 값으로 채우고, `inject` 는 평소 비워 둡니다 — `{}` 로
실행하는 것이 기본이고, 그 실패를 재현해 처방 가지가 켜지는 것을 볼 때만 `{"inject": ["image_dead"]}`
처럼 넣습니다. 결과 패널에는 판정 · 바퀴 · 게이트 답과 함께 `failure_kind` · `detour_attempts` 가 나와,
처방 가지가 몇 번 돌았는지 바로 보입니다.

---

## 읽기 4 — 내가 결정할 질문

<!-- FIXED:BEGIN -->

| 결정 ID | 질문 | 이 값이 바꾸는 것 |
| --- | --- | --- |
| `G-상태범위` | 무엇을 상태에 담나? | 저장 용량 · 재개 속도 |
| `G-원본보관` | 수집 **원문**을 어디에 두나? | 상태 크기 |
| `G-판정필드` | 검사 결과를 상태에 남기나? | 라우터가 볼 수 있는지 |

**쉬운 선택지**

| 결정 ID | A | B | C | 권장 |
| --- | --- | --- | --- | --- |
| `G-상태범위` | 판정에 필요한 것만 | **A + 제어 필드** | 수집 원문까지 전부 | **B** |
| `G-원본보관` | 상태 안에 | **파일에 두고 경로만 상태에** | 둘 다 | **B** |
| `G-판정필드` | **남긴다 (`*_verdict`)** | 라우터가 그때그때 검사기를 돌린다 | 안 남긴다 | **A** |

```text
C(전부 담기)를 고르면    상태가 노드 수만큼 곱해져 저장된다. 재개가 느려진다.
A(판정만)를 고르면       상한을 비교할 loop_a_iter 가 없어 라우터가 멈출 줄 모른다.
G-판정필드 B를 고르면    라우터가 부작용을 갖게 된다. 라우터는 경로만 골라야 한다.
```

> 세 개 다 **권장값을 그대로 쓰면 코드가 바뀌지 않습니다.** 그래도 왜 그런지는 짚고 가십시오 —
> STEP 4에서 이 결정이 실제로 발목을 잡습니다.

<!-- FIXED:END -->

---

## 읽기 5 — 내 답 적기

<!-- ANSWERS:BEGIN -->

### `G-상태범위`
- 고른 것: B (판정에 필요한 것 + 제어 필드)
- 이유: 제어 필드(loop_a_iter 등)가 있어야 라우터가 상한에서 멈출 수 있다. 권장값 그대로.

### `G-원본보관`
- 고른 것: B (파일에 두고 경로만 상태에)
- 이유: 상태는 노드마다 통째로 저장되므로 원문을 넣으면 노드 수만큼 곱해진다. 권장값 그대로.

### `G-판정필드`
- 고른 것: A (남긴다 *_verdict)
- 이유: 라우터는 상태의 판정 값만 읽고 경로만 골라야 한다(부작용 없음). 권장값 그대로.

<!-- ANSWERS:END -->

---

## 읽기 6 — Claude가 정리한 결과

<!-- PROJECT:BEGIN -->

| 결정 ID | 확정 값 | 고른 이유 | 승인 시각 |
| --- | --- | --- | --- |
| `G-상태범위` | B — 판정에 필요한 것 + 제어 필드 | 제어 필드가 있어야 라우터가 상한에서 멈춘다 | 2026-10-23 |
| `G-원본보관` | B — 파일에 두고 경로만 상태에 | 상태가 노드 수만큼 곱해져 저장되는 것을 막는다 | 2026-10-23 |
| `G-판정필드` | A — 남긴다 (`*_verdict`) | 라우터가 값만 읽고 경로만 고르게 한다 | 2026-10-23 |

**확정되면 `travel_graph/state.py` 가 이 모양이어야 합니다** (권장값 기준 — 필드 목록은 지금 파일과 같습니다.
`cities` · `city_failures` · `history` 에 이미 붙어 있는 reducer 는 STEP 4 에서 다루므로 여기서는 뺐습니다).

```python
class TravelState(TypedDict, total=False):
    country: str; days: int; style: dict; city_priority: list[str]   # 입력
    country_intro: dict; selected_city_names: list[str]              # 수집
    cities: list[dict]                                               # STEP 4에서 reducer
    city_failures: list[dict]                                        # STEP 4에서 reducer
    info_verdict: str; info_short_slots: list[str]                   # 판정
    page_verdict: str; page_short_slots: list[str]
    quality_verdict: str; quality_short_slots: list[str]
    quality_pass: int; quality_passes_required: int                  # 루프 C (킷 고정)
    html_path: str; research_path: str                               # 경로만. 본문 아님
    loop_a_iter: int; loop_a_limit: int                              # 제어
    loop_b_iter: int; loop_b_limit: int
    same_error_count: int; same_error_limit: int; last_error_hash: str
    gate_a_answer: str; gate_b_answer: str; gate_note: str           # 사람
    inject: list[str]                                                # 실패 재현(inject) (입력 · 평소 [])
    failure_kind: str; failure_evidence: list[str]                   # 원인 — 진단 노드 (킷 고정)
    detour_attempts: dict; detour_limit: int; detour_verdict: str    # 처방 가지 (킷 고정 · reducer 없음)
    history: list[str]                                               # STEP 4에서 reducer
```

칸은 모두 35개입니다. Studio 입력 폼(`TravelInput`)은 이 중 5칸 —
`country` · `days` · `style` · `city_priority` · `inject` — 만 그립니다.
아래 MACHINE 블록에서는 `inject` 가 `input_schema` 에, 나머지 진단 · 처방 가지 칸 다섯이
`diagnose_fields` 에 들어 있습니다. 준비도 검사(`check_graph_readiness.py`)가 두 묶음 모두
`state.py` 에 있는지 봅니다.

<!-- MACHINE:BEGIN -->
```json
{
  "step": 1,
  "produces": "travel_graph/state.py",
  "decisions": {
    "G-상태범위": "B",
    "G-원본보관": "B",
    "G-판정필드": "A"
  },
  "fixed": {
    "input_schema": ["country", "days", "style", "city_priority", "inject"],
    "verdict_fields": ["info_verdict", "info_short_slots", "page_verdict", "page_short_slots",
                       "quality_verdict", "quality_short_slots"],
    "quality_fields": ["quality_pass", "quality_passes_required"],
    "failure_field": ["city_failures"],
    "control_fields": ["loop_a_iter", "loop_a_limit", "loop_b_iter", "loop_b_limit",
                       "same_error_count", "same_error_limit", "last_error_hash"],
    "path_only_fields": ["html_path", "research_path"],
    "reducer_pending": ["cities", "city_failures", "history"],
    "diagnose_fields": ["failure_kind", "failure_evidence", "detour_attempts",
                        "detour_limit", "detour_verdict"],
    "rule": "노드는 변경분만 돌려준다. 상태 전체를 돌려주지 않는다"
  },
  "inherited": {
    "contract_source": "graph/03_CONTRACT.json"
  }
}
```
<!-- MACHINE:END -->

<!-- PROJECT:END -->

---

## 읽기 7 — 이 STEP이 끝나면 무엇이 진행되는가

| 항목 | 내용 |
| --- | --- |
| **지금 코드가 만들어지나?** | **권장값이면 아니오** — `travel_graph/state.py` 의 **필드 목록**을 확정만 합니다. 다른 값을 고르면 필드 목록을 고칩니다. reducer 는 STEP 4 입니다. |
| **Claude가 하는 일** | ① 답 3개 기록 → ② (다른 값을 골랐을 때만) `state.py` 를 답에 맞춤 → ③ 결정 장부에 추가 |
| **바뀌는 파일** | `specs/01_STATE_SCHEMA.md` · `specs/00_DECISION_LOG.md` · (다른 값을 골랐을 때만) `travel_graph/state.py` |
| **지금 그래프가 도나?** | **돕니다.** 킷은 완성본으로 배포되므로 STEP 1 을 권장값으로 끝내도 그래프는 그대로 돕니다. reducer 는 STEP 4 에서 일부러 떼어 보고 되붙입니다. |

---

## 읽기 8 — 완료 확인과 다음 명령

- [ ] 결정 3개가 값으로 정해졌다
- [ ] 수집 원문이 상태가 아니라 파일에 있다
- [ ] `*_verdict` 필드가 상태에 있다 (라우터가 볼 수 있다)
- [ ] 판정 칸(`*_verdict`)과 원인 칸(`failure_kind`)을 왜 나눴는지, `failure_evidence` 를 왜 라우팅에 안 쓰는지 말할 수 있다
- [ ] 상태가 `APPROVED`다

```bash
python scripts/validate_specs.py --step 1
```

<!-- STATUS:BEGIN -->
STATUS: APPROVED
<!-- STATUS:END -->

```text
STEP 2 진행해줘
```
