# STEP 5 — 체크포인트와 사람 개입 (루프에 없던 조건)

> **한 줄 목적:** 그래프를 **어디서 멈추고**, 사람에게 **무엇을 보여 주고**, 답을 **어디에 적을지** 정한다.
> **내가 결정할 것: 3개** · **코드 변경: 권장값이면 없음** (다른 값을 고르면 `travel_graph/nodes.py` 의 게이트 2개)
>
> 킷은 완성된 상태로 배포됩니다. 이 STEP 은 **읽고 · 정하고 · 확인**합니다.

| 이전 | 다음 | 문서 규칙 | 결정 장부 |
| --- | --- | --- | --- |
| [STEP 4 — 병렬](04_PARALLEL.md) | **Studio 실행** ([GRAPH_CONTRACT](../GRAPH_CONTRACT.md)) → [STEP 6 — 처방 가지 추가 (조건부)](06_DETOUR.md) | [00_INDEX](00_INDEX.md) | [00_DECISION_LOG](00_DECISION_LOG.md) |

---

## 읽기 1 — 이 STEP에서 정하는 것

**루프에는 없던 조건입니다.** 정확히는 — 루프에도 **되물음**이 있었지만,
그것은 사람이 터미널을 보고 있었기에 가능했습니다.

```text
루프          [되물음] 이 뜨면 사람이 터미널에 답을 친다. 프로세스는 살아 있다.
그래프        그래프가 **멈춘다.** 상태를 어딘가 저장해 두고, 사람이 답하면 거기서 이어 돈다.
```

그래서 두 가지가 필요합니다.

```text
interrupt()      "여기서 멈추고 이걸 물어봐"
체크포인터        멈춰 있는 동안 상태를 들고 있는 것
```

**체크포인터가 없으면 `interrupt` 는 동작하지 않습니다.** 저장할 곳이 없기 때문입니다.

---

## 읽기 2 — 앞에서 물려받은 결정

<!-- PROJECT:BEGIN -->

| 물려받은 것 | 값 | 어디서 |
| --- | --- | --- |
| 라우터 판단 근거 | B — 허용값이 정해진 필드만 본다 | `G-라우터판단` |
| 상한 처리 | B — 게이트로 보내 사람이 정한다 | `G-상한처리` |
| 게이트 노드 | `human_gate_a` · `human_gate_b` | STEP 2 |

<!-- PROJECT:END -->

---

## 읽기 3 — 이미 정해 둔 것 (읽고 넘어가기)

### (1) ★ 체크포인터는 **붙이지 않습니다** (고정) — 헷갈리기 쉬운 지점

```python
graph = build().compile(name="travel")     # 체크포인터 인자 없음
```

| 실행 경로 | 체크포인터 | 왜 |
| --- | --- | --- |
| **`langgraph dev` (Studio)** | **넘기지 않는다** | Agent Server 가 스레드 영속화를 **직접** 담당한다 |
| 순수 파이썬 · pytest | `InMemorySaver()` 를 **반드시** 주입 | 없으면 `interrupt` 가 실패한다 |

여기서 몰래 하나를 구우면 Agent Server 것과 싸웁니다. 그래서
`compile_graph(checkpointer=None)` 이 **명시적 옵트인**으로 되어 있습니다.

> **설치할 라이브러리가 따로 없습니다.** `langgraph-checkpoint`(InMemorySaver)와
> `langgraph-api` + `langgraph-runtime-inmem`(Studio 영속화)가 `requirements.lock.txt`
> 에 이미 들어 있습니다. `langgraph-checkpoint-sqlite` 는 **설치하지 마십시오** —
> 강사 환경과 달라지고, 이 실습에서 쓰지 않습니다.

### (2) `thread_id` 가 "한 번의 실행"입니다 (고정)

```text
thread_id = "vietnam-5d-run1"     같은 값으로 다시 부르면 **이어서** 돈다
                                  새 값으로 부르면 처음부터 돈다
```

Studio 화면 왼쪽의 스레드 목록이 이것입니다. 게이트에서 멈춘 스레드를
내일 열어도 그 자리에서 이어집니다.

### (3) ★ `interrupt` 앞은 멱등해야 합니다 (고정)

```python
def human_gate_a(state):
    payload = gate_a_payload(state)   # ① interrupt 앞 — 재개 때마다 **다시 실행된다**
    answer = interrupt(payload)       # ② 여기서 멈춘다
    return {...}                      # ③ interrupt 뒤 — 정확히 한 번만 실행된다
```

**재개하면 이 함수는 첫 줄부터 다시 실행됩니다.** 노드 중간에서 이어지지 않습니다.
그래서 `interrupt` 앞에는 **부작용이 없는 코드만** 둡니다 (파일 쓰기·카운터 증가 금지).

**진단 · 처방 가지가 들어와도 이 규칙은 그대로입니다.** `diagnose_*` · `fix_<이름>` · `test_<이름>` 은
`interrupt` 를 부르지 않는 노드라 재개할 때 다시 실행되지 않습니다. 게이트가 `② 왜` 에 처방 가지
줄을 만드는 일도 상태만 읽으므로 `interrupt` 앞에 있어도 안전합니다. 진단 · 시험 노드가 남기는
실패 기록(`evidence/failures/<thread_id>.jsonl`)은 **같은 걸음 · 같은 내용이면 한 번만** 적힙니다 — Studio
에서 fork 해 같은 노드가 같은 걸음 번호로 다시 돌아도 똑같은 줄은 겹치지 않고, 다른 답을 고른 갈래(내용이
다름)는 따로 남습니다.

### (3-b) ★ 정성 회차 안에서는 멈추지 않습니다 (고정)

`quality_pass` 노드는 회차 시작 전에 파일 해시를 찍고, 고치고, 다시 찍고, 기록을 씁니다.
**그 중간에서 `interrupt` 로 멈추면 안 됩니다.**

```text
quality_pass 2회차 도중  →  interrupt  →  사람이 파일을 직접 고침  →  재개
                                              ↑
                              snapshot_before 가 이미 과거의 값이다
```

그래서 이 킷은 두 방식 중 **A** 를 씁니다.

| 방식 | 내용 | 채택 |
| --- | --- | --- |
| **A** | `quality_pass` 안에서는 `interrupt` 를 걸지 않는다. 회차 **사이**(게이트 B)에서만 건다 | **★ 채택** |
| B | 재개할 때 `snapshot_before` 를 다시 찍고, 그 회차만 사슬 검사를 건너뛴다 | 검사가 약해짐 |

**정성 회차는 원자적으로 끝나야 기록이 정직해집니다.**
그리고 `quality_pass` 는 **파일 쓰기를 끝낸 뒤에** 반환합니다 — `check_quality` 는
상태가 아니라 **디스크**를 읽기 때문입니다. `build_page` 와 같은 원칙입니다.

**처방 가지도 이 사슬을 건드리지 않습니다.** 정성이 **한 회차라도** 돈 뒤(`quality_pass > 0`)에는
`diagnose_page` 가 루프 B 처방 가지를 고르지 않습니다. 가지가 화면 파일을 고치면 해시 사슬이
끊겨 루프 C 가 멈추기 때문입니다. 증상은 버리지 않고 "(정성 회차 중 — 파일 해시 사슬을 지키려고
미룸)" 으로 `failure_evidence` 에 남깁니다 — 게이트 B 가 정성 3회를 채우기 전에 다시 서면 `② 왜`
맨 앞에 `처방 가지를 미룸 — <title> (정성 회차 중)` 으로 뜹니다. 실패 기록(jsonl)에는 `"failure_kind": ""` ·
`"decision": "루프 골격 그대로"` 와 증상(`symptoms` 의 `why`)이 남습니다 — 실패가 아닙니다. 게이트 B 에서
`research` · `rebuild` 를 고르면 정성 회차가 0 이 되므로 그때부터 다시 처방 가지를 탈 수 있습니다.

### (3-c) 게이트 B 는 두 번 섭니다 (고정)

```text
정성 3회 전   done  →  "정성 점검을 시작한다"      →  quality_pass
정성 3회 후   done  →  "확정하고 끝낸다"          →  END
```

무엇을 묻고 있는지는 게이트 화면의 `① 지금` 줄에 적힌 `정성 n/3` 으로 구분합니다.
`research` 나 `rebuild` 를 고르면 결과물이 다시 만들어져 정성 수정이 사라지므로,
그때 **회차 카운터가 0으로 되돌아갑니다.** 처방 한도(`detour_attempts`)도 함께 비웁니다 (아래 6).

### (3-d) 세 정지 지점이 같은 5키 화면을 씁니다 (고정)

```text
① 지금    한 줄 요약        판정 · 진행 · 부족 개수
② 왜      원인 묶음         목록이 아니라 **요약**이다
③ 권장    상황에서 계산     고정 문구로 두면 틀린 권장을 하게 된다
④ 고르기  선택지            고르면 무슨 일이 일어나는지까지
⑤ 답      입력 형태 그대로  {"action": "...", "note": "..."}
```

`nodes.gate_payload()` 하나가 세 화면을 만들고, 다른 것은 **원인 규칙표**(`_CAUSE_A`
`_CAUSE_B` `_CAUSE_C`)·선택지·권장 계산 셋뿐입니다. `classify()` 가 규칙표를 인자로
받으므로 같은 함수를 게이트 세 곳이 쓰고, 진단 노드 두 곳(`diagnose_info` · `diagnose_page`)도
실패 기록에 원인 묶음을 남길 때 같은 함수를 씁니다 — 게이트 화면과 실패 기록이 **같은 말로**
원인을 부릅니다.

**원본 부족 목록은 주지 않습니다.** 요약을 만들어 놓고 원본도 보여 주면 요약을 읽지
않습니다. 원본이 필요하면 `research_path` 가 가리키는 파일을 엽니다.

**수집이 실패한 도시는 `② 왜` 에 따로 뜹니다.** 빈 도시는 검사기가 `관광지 수 3/0`
한 줄만 내므로 "좀 모자라네"로 읽히지만, 실제로는 그 도시를 아예 못 모은 것이라
판단이 완전히 달라집니다.

**처방 가지가 못 고친 것은 `② 왜` 맨 앞에 뜹니다** (`nodes._detour_lines`). 줄은 세 종류입니다.

```text
처방 가지가 못 고침 — <title>                처방 한도를 다 쓰고 게이트로 넘어왔거나, 한도를 이미 다 써서
                                             진단이 건너뛴 증상 (예: "처방 가지가 못 고침 — 이미지 주소가 죽어 있음")
처방 가지 시험지가 깨짐 — <title>            시험지가 실행 중에 멈췄다 — 증상이 아니라 판정을 못 한 것
처방 가지를 미룸 — <title> (정성 회차 중)    정성이 시작된 뒤라 루프 B 처방 가지를 미뤘다 (위 3-b)
```

정해진 절차로도 안 됐다는 것은 사람이 가장 먼저 알아야 할 사실입니다. `③ 권장` 도 줄 종류에
맞춰 계산합니다 (`_recommend_a` · `_recommend_b`) — `처방 가지가 못 고침` 이면 게이트 A 는 부족이
남았으면 `more`, 없으면 `proceed`, 게이트 B 는 `done` 에 "'고치려면' 칸을 따르십시오 (데이터로
고칠 수 있으면 rebuild · research, 화면 코드 문제면 보고서에 남기고 done)" 를 붙입니다.
`처방 가지 시험지가 깨짐` 이면 `proceed`(A) · `done`(B), `처방 가지를 미룸` 이면 `done` 입니다. 한 가지의
이유를 다른 가지에 붙이지 않습니다 — 구체적인 고칠 법은 `고치려면` 칸(그 가지의 `HOWTO`)에
있습니다. 정성 3회 뒤의 게이트 C 에는 처방 가지 줄을 싣지 않습니다 — 그때의 관심사는 정성입니다.

### (4) 순환은 조건부 간선으로 만듭니다 (고정)

LangGraph 공식 권고: *"Do not loop interrupt calls. Use conditional edges to loop instead."*
게이트에서 `more` 를 고르면 `repair_city` · `repair_country` 로 **간선을 타고** 되돌아갑니다 (지적된 것만).
같은 노드 안에서 `interrupt` 를 반복 호출하지 않습니다.
처방 가지의 재시도(`fix ↔ test`)도 같습니다 — `route_after_detour` 의 `retry` 간선으로 돌고,
처방 한도가 끝나면 `gate` 간선을 타고 게이트로 옵니다.

### (5) 되물음 양식은 루프 킷과 같습니다 (고정)

```text
[되물음] (어느 루프)가 끝났습니다 / 상한에 걸렸습니다.
  채운 것    : N / M 칸
  못 채운 것 : (목록과 이유)
  고르세요
   [1] 부족한 칸만 다시 모은다
   [2] 부족한 채로 다음으로 넘어간다   ← 권장
   [3] 여기서 멈춘다
```

**선택지 없이 "도와주세요"라고 쓰지 않습니다.** 못 채운 칸을 숨기지 않습니다.

### (6) ★ 처방 가지가 처방 한도를 다 쓰면 — 새 정지 지점은 없습니다 (고정)

```text
처방 한도 끝      test_<이름> ─gate─▶ 그 루프의 게이트
                    루프 A 처방 가지 (encoding · image_dead)  → human_gate_a
                    루프 B 처방 가지 (image_spec)             → human_gate_b
```

처방 가지는 **새 게이트 노드를 만들지 않고** 그 루프에 원래 있던 게이트로 넘깁니다. 그래서
`G-게이트위치` B 의 **"루프 A 끝 + 루프 B 끝 (2곳)"** 은 그대로 참입니다. 실패 재현(inject) 없는
기본 실행의 정지는 3번(A · B · C) 그대로이고, 처방 가지가 처방 한도를 다 쓴 실행에서는 게이트에
서는 횟수가 늘 수 있습니다 — 한도 끝으로 선 게이트에서 `more` · `research` · `rebuild` 를 고르면 같은
게이트에 한 번 더 서기 때문입니다 (그런 정지 하나마다 +1. 루프 A 처방 가지는 재수집 전에 일찍 서므로
대개 이렇게 됩니다). 그때는 보고서의 "게이트" 줄과 "사람 호출"에 그대로 적습니다.
`run_once.py` 의 `--auto` 답도 그만큼 하나씩 밀립니다 — 답이 모자라면 그 게이트에서 끝납니다.

**사람이 "한 번 더"를 고르면 처방 한도가 새로 채워집니다.**

```text
게이트 A  more               → detour_attempts = {}
게이트 B  research · rebuild → detour_attempts = {} · failure_kind = "" · detour_verdict = ""
                               (정성 회차 · 안쪽 바퀴를 0 으로 되돌리는 바로 그 자리)
그 밖     proceed · stop · done → 그대로 둔다
```

되살릴 때는 history 에 한 줄씩 남깁니다 — `human_gate_a: 처방 한도를 새로 채웁니다` ·
`human_gate_b: 처방 한도를 새로 채웁니다`. 사람이 자기 답이 무엇을 되돌렸는지 볼 수 있어야
합니다 (게이트 B 는 그 앞에 `되돌아가므로 정성 회차를 0 으로 되돌립니다` · `안쪽 바퀴를 0 으로
되돌립니다 (…)` 도 남깁니다).

안전한 이유는 안쪽 바퀴를 되돌릴 때와 같습니다 — **바깥 루프는 사람이 소유합니다.** 사람이
재수집 · 재생성을 명시적으로 골랐고, 그 뒤 데이터가 바뀌므로 처방 가지가 다시 설 수 있어야
합니다. 되돌리지 않으면 한도를 이미 쓴 가지는 데이터가 바뀐 뒤에도 **영영 켜지지 않습니다.**
처방 한도(`detour_limit`)는 2 입니다 (`travel_graph/detours/__init__.py` 의 `LIMIT`).

---

## 읽기 4 — 내가 결정할 질문

<!-- FIXED:BEGIN -->

| 결정 ID | 질문 | 이 값이 바꾸는 것 |
| --- | --- | --- |
| `G-체크포인터` | 상태를 무엇으로 저장하나? | `interrupt` 가 도는지 |
| `G-게이트위치` | 어디서 멈추나? | 사람을 몇 번 부르는지 |
| `G-게이트선택지` | 사람에게 무엇을 보여 주나? | 사람이 제대로 판단할 수 있는지 |

**쉬운 선택지**

| 결정 ID | A | B | C | 권장 |
| --- | --- | --- | --- | --- |
| `G-체크포인터` | **Agent Server 것을 쓴다 (compile 에 안 붙임)** | SQLite 파일 | 저장 안 함 | **A** |
| `G-게이트위치` | 루프 A 끝만 | **루프 A 끝 + 루프 B 끝 (2곳)** | 노드마다 | **B** |
| `G-게이트선택지` | 자유 문장으로 받는다 | **선택지 + 현황 + 권장을 함께 보여 준다** | 예/아니오 | **B** |

```text
G-체크포인터 B → Studio 것과 싸운다. requirements 에 없는 패키지도 필요하다
G-체크포인터 C → interrupt 가 아예 동작하지 않는다. 저장할 곳이 없다
G-게이트위치 C → 노드마다 물으면 자동화의 의미가 없다
G-게이트선택지 A → 라우팅이 문장 해석에 좌우된다 (STEP 3에서 이미 막았다)
```

### `G-게이트선택지` — 두 게이트의 선택지가 다릅니다

| 게이트 | 언제 | 선택지 | 어디로 가나 |
| --- | --- | --- | --- |
| **A** 정보량 | 루프 A가 끝났을 때 | `more` **지적된 도시만** 더 모은다 | `repair_city` (Send) |
| | | `proceed` 부족해도 진행 **← 권장** | `build_page` |
| | | `stop` 여기서 멈춘다 | `END` |
| **B** 페이지 | 루프 B가 끝났을 때 | `research` 정보가 모자란다 | `check_information` (다시 세고 다친 도시만) |
| | | `rebuild` **`note` 에 적은 지시대로** 고친다 | `rebuilder` |
| | | `done` 정성 3회를 시작한다 **← 대개 이쪽** | `quality_pass` |
| **C** 정성 | 정성 3회가 끝났을 때 | `research` · `rebuild` · `done` 확정 | 위와 같음 / `END` |

> **게이트 B의 `research` 가 이 그래프의 진짜 이득입니다.** 루프에서는 "페이지 단계에서
> 정보 수집 단계로 되돌아가기"가 없었습니다. 그래프에서는 간선 하나입니다.

<!-- FIXED:END -->

---

## 읽기 5 — 내 답 적기

<!-- ANSWERS:BEGIN -->

### `G-체크포인터`
- 고른 것: A (Agent Server 것을 쓴다 · compile 에 안 붙임)
- 이유: Studio 의 Agent Server 가 스레드 영속화를 담당하므로 직접 붙이면 싸운다. 추가 설치도 필요 없다. 권장값 그대로.

### `G-게이트위치`
- 고른 것: B (루프 A 끝 + 루프 B 끝, 2곳)
- 이유: 정보를 더 모을지(A)와 정성 점검을 시작·확정할지(B)에서만 사람의 판단이 필요하다. 처방 가지는 새 게이트를 만들지 않고 이 둘로 넘어온다. 권장값 그대로.

### `G-게이트선택지`
- 고른 것: B (선택지 + 현황 + 권장을 함께 보여 준다)
- 이유: 지금·왜·권장·고르기·답 5칸 화면과 {action, note} 입력으로 받아 라우터가 문장 해석에 좌우되지 않는다. 권장값 그대로.

<!-- ANSWERS:END -->

---

## 읽기 6 — Claude가 정리한 결과

<!-- PROJECT:BEGIN -->

| 결정 ID | 확정 값 | 고른 이유 | 승인 시각 |
| --- | --- | --- | --- |
| `G-체크포인터` | A — Agent Server 것을 쓴다 (compile 에 안 붙임) | Studio 가 영속화를 담당하고 설치할 것이 없다 | 2026-10-23 |
| `G-게이트위치` | B — 루프 A 끝 + 루프 B 끝 (2곳) | 판단이 필요한 두 지점에서만 사람을 부른다 | 2026-10-23 |
| `G-게이트선택지` | B — 선택지 + 현황 + 권장 | 사람이 근거를 보고 고르며 라우팅은 닫힌 값만 읽는다 | 2026-10-23 |

**권장값을 골랐다면 `travel_graph/nodes.py` 는 이미 이 모양입니다.** 아래는 붙여 넣으라는 뜻이
아니라 지금 파일의 게이트 세 곳을 **줄여서** 옮겨 적은 것입니다 (그래서 이 코드로 파일을 덮어쓰지
않습니다). 다른 값을 골랐을 때만 이 자리를 고칩니다.

```python
# ① 파일 위쪽 — 임포트
from langgraph.types import interrupt


# ② human_gate_a — interrupt 로 멈추고 사람의 답을 받는다
def human_gate_a(state) -> dict:
    # interrupt 앞은 **멱등해야 한다** (재개할 때 이 함수는 첫 줄부터 다시 실행된다).
    # payload 만드는 일은 부작용이 없으므로 안전하다.
    answer = interrupt(gate_a_payload(state))
    # interrupt 뒤부터는 정확히 한 번만 실행된다.

    decision = normalize_gate(answer, ("more", "proceed", "stop"), "proceed")
    #  ★ `more` 는 사람이 "한 번 더"를 고른 것이다. 바깥 루프는 사람이 소유하므로
    #    처방 한도도 새로 채운다 (킷이 이미 넣어 두었다 — 지우지 않는다. 읽기 3 의 6)
    again = decision["action"] == "more"
    return {
        "gate_a_answer": decision["action"],
        "gate_note": decision["note"],
        "detour_attempts": {} if again else _as_dict(state.get("detour_attempts")),
        "history": [f"human_gate_a: {decision['action']}"]
                   + (["human_gate_a: 처방 한도를 새로 채웁니다"] if again else []),
    }


# ③ human_gate_b 안 — 같은 방식이되 **되돌아갈 때 되돌릴 것이 더 있다**
def human_gate_b(state) -> dict:
    answer = interrupt(gate_b_payload(state))
    decision = normalize_gate(answer, ("research", "rebuild", "done"), "done")

    if decision["action"] in ("research", "rebuild"):
        #  ★ 되돌아가면 결과물이 다시 만들어진다. 정성 회차가 디스크에 남긴 수정이
        #    그때 사라지고 해시 사슬도 끊기므로 **회차를 0 으로** 되돌린다.
        #  ★ **안쪽 바퀴도 0 으로** 되돌린다. 아무도 이것을 안 되돌리면
        #    `check_information` 이 방문할 때마다 `loop_a_iter` 를 올리기만 해서,
        #    루프 A 예산을 이미 쓴 뒤에는 `research` 를 골라도 재수집이 **한 번도**
        #    돌지 않는다. 화면은 "다시 모읍니다"라고 약속한 뒤다.
        #    안전한 이유: 바깥 루프는 **사람이 소유한다.**
        reset = {"loop_a_iter": 0} if decision["action"] == "research" else {"loop_b_iter": 0}
        return {
            "gate_b_answer": decision["action"],
            "gate_note": decision["note"],
            "quality_pass": 0,
            "quality_verdict": "UNKNOWN",
            "same_error_count": 0,
            "last_error_hash": "",
            #  ★ 처방 한도도 새로 채운다 (게이트 A 의 more 와 같다 — 읽기 3 의 6)
            "detour_attempts": {},
            "failure_kind": "",
            "detour_verdict": "",
            **reset,
            #  (킷의 nodes.py 는 "되돌아가므로 정성 회차를 0 으로 되돌립니다" 같은 되돌림 줄과
            #   답 경고 줄도 history 에 남긴다 — 줄이 많을 뿐 되돌리는 값은 이것과 같다)
            "history": [f"human_gate_b: {decision['action']}",
                        "human_gate_b: 처방 한도를 새로 채웁니다"],
        }

    return {
        "gate_b_answer": decision["action"],
        "gate_note": decision["note"],
        "history": [f"human_gate_b: {decision['action']}"],
    }
```

`gate_a_payload` · `gate_b_payload` · `normalize_gate` 는 **킷이 이미 만들어 뒀습니다.**
`normalize_gate` 가 **라우팅 키(`action`)와 자유 문장(`note`)을 분리**합니다.

<!-- MACHINE:BEGIN -->
```json
{
  "step": 5,
  "produces": "travel_graph/nodes.py",
  "decisions": {
    "G-체크포인터": "A",
    "G-게이트위치": "B",
    "G-게이트선택지": "B"
  },
  "fixed": {
    "compile_rule": "Studio 에서는 checkpointer 를 넘기지 않는다. Agent Server 가 담당한다",
    "python_rule": "순수 파이썬·pytest 에서는 InMemorySaver() 를 반드시 주입한다",
    "extra_package_needed": "없음. langgraph-checkpoint / langgraph-api / langgraph-runtime-inmem 이 lock 에 이미 있다",
    "idempotence": "interrupt 앞에는 부작용이 없는 코드만 둔다",
    "idempotence_detours": "진단 · 처방 가지 노드는 interrupt 를 부르지 않는다. 실패 기록은 같은 걸음 · 같은 내용이면 한 번만 적힌다 (내용이 다르면 둘 다 남는다)",
    "loop_rule": "interrupt 를 반복 호출하지 않는다. 조건부 간선으로 되돌아간다",
    "gates": {
      "human_gate_a": {"more": "repair_city · repair_country (Send · 지적된 것만)", "proceed": "build_page", "stop": "END"},
      "human_gate_b": {"research": "check_information", "rebuild": "rebuilder",
                       "done": "quality_pass 또는 END (정성 회차로 갈린다)"},
      "payload_shape": ["① 지금", "② 왜", "③ 권장", "④ 고르기", "⑤ 답"],
      "payload_builder": "nodes.gate_payload — 세 정지 지점이 같은 함수를 쓴다",
      "why_first_row": "② 왜 맨 앞에 '처방 가지가 못 고침 — <title>' (게이트 C 에는 싣지 않는다)",
      "detour_escalation": "처방 가지가 처방 한도를 다 쓰면 그 루프의 게이트로 (A → human_gate_a · B → human_gate_b). 새 게이트 노드 없음 — G-게이트위치 '2곳' 그대로",
      "detour_reset": "more(A) · research · rebuild(B) 를 고르면 detour_attempts 를 {} 로 되돌린다 — 바깥 루프는 사람 소유"
    },
    "quality_guard": "정성이 한 회차라도 돈 뒤에는 루프 B 처방 가지를 타지 않는다 (파일 해시 사슬 보호). 증상은 게이트에 남긴다",
    "thread_id": "한 번의 실행. 같은 값이면 이어서 돈다"
  },
  "inherited": {
    "router_source": "허용값이 정해진 필드 (gate_*_answer · *_verdict · failure_kind)"
  }
}
```
<!-- MACHINE:END -->

<!-- PROJECT:END -->

---

## 읽기 7 — 이 STEP이 끝나면 무엇이 진행되는가

| 항목 | 내용 |
| --- | --- |
| **지금 코드가 만들어지나?** | **권장값이면 아니오** — `travel_graph/nodes.py` 의 게이트 2개에 `interrupt` 가 이미 들어 있습니다. 다른 값을 고르면 게이트 2개를 고칩니다. |
| **Claude가 하는 일** | ① 답 3개 기록 → ② (다른 값을 골랐을 때만) `nodes.py` 게이트 수정 → ③ 준비도 검사 |
| **바뀌는 파일** | `specs/05_CHECKPOINT.md` · `specs/00_DECISION_LOG.md` · (다른 값을 골랐을 때만) `travel_graph/nodes.py` |
| **다음** | `langgraph dev` 로 Studio 에서 돌립니다 → `GRAPH_CONTRACT.md`. 실행 뒤 실패 기록 보고서(`failure_report.py`) ③ · ③-2 에 처방 가지 후보가 있을 때만 STEP 6 (조건부) |

---

## 읽기 8 — 완료 확인과 다음 명령

- [ ] `compile()` 에 체크포인터를 넘기지 **않았다**
- [ ] `interrupt` 앞에 부작용이 있는 코드가 없다
- [ ] 게이트 두 곳의 선택지가 서로 다르다
- [ ] `check_graph_readiness.py` 가 `READY` 다
- [ ] 상태가 `APPROVED`다

```bash
python scripts/check_graph_readiness.py
python scripts/validate_specs.py --step 5
```

> 인자 없이 `validate_specs.py` 를 돌리면 STEP 6 까지 봅니다. **STEP 6 은 조건부**라(로그에 처방 가지
> 후보가 있을 때만) 아직 안 했거나 하지 않을 것이면 STEP 6 줄이 SHORT(exit 2)로 남습니다 — **정상입니다.**
> STEP 1~5 는 `--step N` 으로 하나씩 확인하고, 실행 준비는 `check_graph_readiness.py` 의 `READY` 가 판정합니다
> (준비도 검사는 STEP 6 을 요구하지 않습니다).

<!-- STATUS:BEGIN -->
STATUS: APPROVED
<!-- STATUS:END -->

```text
langgraph dev --no-reload --port 2024
```

이후 절차는 [`GRAPH_CONTRACT.md`](../GRAPH_CONTRACT.md) 에 있습니다.
