# STEP 4 — 병렬 (루프에 없던 조건)

> **한 줄 목적:** 어디를 **나란히** 돌리고, 같은 칸에 동시에 쓸 때 **어떻게 합칠지** 정한다.
> **내가 결정할 것: 2개** · **코드 변경: 권장값이면 떼었다 되붙이면 끝** (reducer 3 · 함수 2)
> (`cities` · `city_failures` · `history` — 다른 값을 고르면 `travel_graph/state.py` 의 그 reducer)

| 이전 | 다음 | 문서 규칙 | 결정 장부 |
| --- | --- | --- | --- |
| [STEP 3 — 간선 조건](03_EDGE_CONDITION.md) | [STEP 5 — 체크포인트](05_CHECKPOINT.md) | [00_INDEX](00_INDEX.md) | [00_DECISION_LOG](00_DECISION_LOG.md) |

---

## 읽기 1 — 이 STEP에서 정하는 것

**루프에는 없던 조건입니다.** 그래프로 옮기는 가장 큰 이유이기도 합니다.

```text
루프          도시 3개를 순서대로 조사한다.  7분 + 5분 + 4분 = 16분
그래프        도시 3개를 나란히 조사한다.    max(7, 5, 4)    = 7분
```

### ★ reducer 를 떼어 보고 무슨 일이 생기는지 먼저 보십시오

킷은 **완성된 상태**로 배포되므로 그냥 돌리면 통과합니다. 그래서 이 STEP 은
**일부러 망가뜨려 보는 것**으로 시작합니다. `state.py` 에서 `cities` 의
`Annotated[..., merge_cities]` 를 잠깐 `list[dict]` 로 바꾸고 돌려 보십시오.

```bash
python scripts/check_graph_shape.py
```

```text
3 reducer 없는 병렬 쓰기        목표 0 / 실제 1   부족
  - `collect_city` 가 병렬로 돌면서 `cities` 에 씁니다 (fan-out(Send) — 도시 수만큼
    동시에 쓴다). state.py 에서 `Annotated[..., reducer]` 를 붙이십시오
```

같은 상태로 그래프를 돌려 보면 검사기 말대로 **실행 중에 멈춥니다.**

```bash
python scripts/run_once.py --mode replay --auto stop
```

```text
langgraph.errors.InvalidUpdateError: At key 'cities': Can receive only one value per step. Use an Annotated key to handle multiple values.
```

(강의 슬라이드는 `history` 의 reducer 를 떼서 같은 것을 보여 줍니다 — 그때는 `At key 'history'` 입니다.)

**되돌린 뒤** 아래를 읽으십시오. reducer 가 왜 필요한지는 설명보다 이 한 줄이 빠릅니다.
`city_failures` 로도 똑같이 해 보면 검사기가 같은 말을 합니다.

---

## 읽기 2 — 앞에서 물려받은 결정

<!-- PROJECT:BEGIN -->

| 물려받은 것 | 값 | 어디서 |
| --- | --- | --- |
| 상태 필드 목록 | B — 판정에 필요한 것 + 제어 필드 (칸 35개) | `G-상태범위` |
| 노드 개수 | B — 킷 매핑 (루프 골격 14 + 진단 2 + 처방 가지 6 = 22) | `G-노드개수` |
| 도시 수 | 2 (오사카 · 고베) (= 병렬 폭) | `graph/03_CONTRACT.json` `count_contract.cities.city_count` |

<!-- PROJECT:END -->

---

## 읽기 3 — 이미 정해 둔 것 (읽고 넘어가기)

### (1) ★ 정적 간선 여러 개 = 병렬입니다 (if/else 아님) — 최다 함정

```python
builder.add_edge("read_request", "collect_country")
builder.add_edge("read_request", "select_cities")
# → 둘 다 다음 걸음에서 **실행됩니다.** 하나만 고르는 게 아닙니다.
```

둘 중 하나만 고르려면 **반드시** `add_conditional_edges()` 를 씁니다.

### (2) 합류(fan-in)는 리스트로 씁니다 (고정)

```python
# 맞다 — 둘 다 끝난 뒤 한 번만 돈다
builder.add_edge(["collect_country", "collect_city"], "check_information")

# 틀리다 — 각각이 따로 방아쇠가 되어 뒤쪽 사슬이 통째로 두 번 돈다
builder.add_edge("collect_country", "check_information")
builder.add_edge("collect_city",    "check_information")
```

### (3) 도시 수가 실행 중에 정해질 때는 `Send` (고정)

```python
def fan_out_cities(state):
    return [Send("collect_city", {"city": name, ...})
            for name in state["selected_city_names"]]

builder.add_conditional_edges("select_cities", fan_out_cities, ["collect_city"])
```

각 `collect_city` 는 **자기 도시 하나만** 받아 처리하고, 리스트 한 칸을 돌려줍니다.

```python
def collect_city(payload):
    return {"cities": [city]}     # 합치는 일은 reducer 가 한다
```

### (4) 어디를 병렬로 할 수 있나 (고정)

| 나란히 돌 수 있는 것 | 왜 | 주의 |
| --- | --- | --- |
| `collect_country` 와 `select_cities` | 서로의 결과를 안 본다 | **다른 필드**에 쓴다 → reducer 불필요 |
| `collect_city` × 3도시 (fan-out ①) | 도시끼리 독립 | **같은 `cities` 필드** → reducer 필수 |
| `repair_city` × 다친 도시 (fan-out ②) | 같은 이유 | `cities` · `city_failures` 둘 다 → reducer 필수 |
| `repair_country` × 0 또는 1 (fan-out ②) | 도시와 무관 | 갈래가 **하나뿐** → `country_intro` 에 reducer 불필요 |

### (4-a) ★ fan-out 이 두 군데입니다 (고정)

```text
fan_out_cities    select_cities 뒤   고른 도시를 **전부** 보낸다        첫 수집
fan_out_repairs   diagnose_info 뒤(검사기 A → 진단 A 다음) · human_gate_a 뒤
                                     검사기가 **지적한 도시만** 보낸다   재수집
```

둘 다 `Send` 지만 **갈래 폭을 정하는 기준이 다릅니다.** 재수집에서 지적이 없는
도시는 호출조차 되지 않습니다. 한 노드로 합치면 지적 없는 도시가 첫 수집 프롬프트로
떨어져 통째로 다시 뽑힙니다.

**fan-out ② 는 도시와 국가를 함께 갈라 보냅니다.** 다만 갈래 폭이 다릅니다 —
도시는 다친 수만큼, 국가는 **0 또는 1**. 그래서 같은 fan-out 인데도 reducer 필요
여부가 갈립니다.

```text
cities         repair_city 가 N개 동시에 쓴다      → reducer 필수
city_failures  같음                                → reducer 필수
country_intro  repair_country 하나만 쓴다          → **필요 없다**
```

**"fan-out 이면 무조건 reducer" 가 아닙니다.** 겹치는지를 보는 것입니다 —
한 걸음에 그 키를 쓰는 노드가 둘 이상일 때만 필요합니다.

**병렬로 못 하는 것**

```text
build_page              모든 수집이 끝나야 한다              (입력이 다 모여야 해서)
select_cities 이전      병렬 폭(도시 수)을 아직 모른다
quality_pass            ★ 앞 회차의 출력이 자기 입력이라서   (다른 이유다)
fix_<이름> (처방 가지)  ★ 한 번에 한 원인. 고친 데이터 위에서 다음 원인을 본다   (4-c)
```

### (4-b) ★ 정성 회차는 병렬 금지입니다 (고정)

`build_page` 와 `quality_pass` 는 **둘 다 병렬이 안 되지만 이유가 다릅니다.**
이 차이를 아는 것이 병렬 판단의 핵심입니다.

```text
build_page     "입력이 다 모여야 해서" 못 한다      → fan-in 으로 해결
quality_pass   "내 앞 회차의 출력이 내 입력이라서"  → **순환**으로만 해결
```

```text
잘못  add_edge("check_page", "quality_pass_1")
      add_edge("check_page", "quality_pass_2")
      add_edge("check_page", "quality_pass_3")
      → 정적 간선 3개 = 병렬. 셋이 같은 파일을 동시에 고친다.

맞음  quality_pass ──▶ check_quality ──회차 < 3──▶ quality_pass   (순환 · 순차)
```

회차 N 의 `snapshot_before` 는 회차 N-1 의 `snapshot_after` 와 **같아야 하고**
판정기가 그 해시 사슬을 확인합니다. 병렬로 돌리면 반드시
"앞 회차와 이어짐: 끊김" 으로 SHORT 가 납니다.

> 그리고 이 경우에는 **reducer 가 답이 아닙니다.** `quality_pass` 는 회차 카운터이므로
> `Annotated` 를 붙이면 2회차에 값이 1+2=3 이 되어 한 회차를 건너뛰고 나갑니다 (정성 2회만 돈다). `check_graph_shape.py` 3번 검사는
> 겹친 키가 카운터일 때 "reducer 를 붙이라"가 아니라 **"순환으로 바꾸라"** 고 말합니다.

### (4-c) ★ 규칙 처방 가지는 병렬이 아닙니다 — 한 번에 한 원인 (고정)

진단 노드가 증상을 여럿 찾아도 처방 가지는 **하나씩** 탑니다. 등록부
(`travel_graph/detours/registry.py`)에 적힌 순서가 곧 우선순위이고, 진단은 불합격인 첫
가지(처방 한도가 남은 것) **하나만** `failure_kind` 에 적습니다. 그것을 고치고 검사기로 돌아온
뒤, 진단이 다시 보고 다음 것을 고릅니다 (아래는 루프 A 에 증상이 둘일 때).

```text
diagnose_info ─encoding─▶ fix_encoding ▶ test_encoding ─back─▶ check_information
  ▶ diagnose_info ─image_dead─▶ fix_image_dead ▶ test_image_dead ─back─▶ check_information ...
```

```text
Send 없음      라우터는 처방 가지 이름 **문자열 하나**를 돌려준다 → fix 노드 하나만 돈다
reducer 없음   처방 가지 칸(failure_kind · detour_attempts · detour_verdict …)은
               한 걸음에 쓰는 노드가 하나뿐이다 → 덮어쓰기
```

**왜 나란히 돌리지 않나.** 처방 가지의 fix 노드는 `cities` **목록 전체**를 돌려줍니다.
`merge_cities` 는 도시 이름으로 **통째로 갈아 끼우므로**, 두 가지가 같은 도시를 한 걸음에
고치면 뒤에 온 결과가 앞의 수정을 지웁니다 — 인코딩 가지가 되살린 글자를 이미지 가지가
옛 글자로 되돌리는 식입니다. 그리고 두 번째 원인은 첫 번째를 고친 **데이터 위에서** 다시 봐야
정확합니다. 앞의 출력이 뒤의 입력이라는 점에서 정성 회차(4-b)와 같은 이유입니다.

**목록 전체를 돌려줘도 도시가 늘지 않는 것은 `merge_cities` 덕분입니다.** 이름이 같으면
갈아 끼우므로 도시는 3개 그대로입니다. `operator.add` 였다면 처방 가지가 한 번 돌 때마다 도시가
6개가 됩니다 — `G-병렬충돌` C 가 여기서도 값을 합니다. `country_intro` 는 그 걸음에 쓰는
노드가 fix 하나뿐이라 여전히 reducer 가 필요 없습니다.

### (5) reducer 가 하는 일 (고정)

```text
기본 동작        같은 필드에 두 값이 한 걸음에 오면 → InvalidUpdateError 로 멈춘다
Annotated 붙이면  그 함수가 둘을 합친다.  R(기존, 새것) → 합친 것
```

**"겹치는 필드에만" 붙입니다.** 병렬이어도 서로 다른 필드에 쓰면 필요 없습니다.
`check_graph_shape.py` 3번 검사가 겹치는 곳만 정확히 짚어 줍니다.

---

## 읽기 4 — 내가 결정할 질문

<!-- FIXED:BEGIN -->

| 결정 ID | 질문 | 이 값이 바꾸는 것 |
| --- | --- | --- |
| `G-병렬범위` | 어디까지 나란히 돌리나? | 전체 실행 시간 |
| `G-병렬충돌` | 같은 필드에 동시에 쓸 때 어떻게 합치나? | 결과가 맞는지 |

**쉬운 선택지**

| 결정 ID | A | B | C | 권장 |
| --- | --- | --- | --- | --- |
| `G-병렬범위` | 안 한다 (순차) | **도시별 (+ 국가정보와 도시선정)** | 도시 + 관광지별 | **B** |
| `G-병렬충돌` | `operator.add` (이어 붙임) | 필드를 도시별로 쪼갠다 | **이름 기준 upsert reducer** | **C** |

### `G-병렬충돌` 은 조금 생각해야 합니다

```text
필드           누가 쓰나                              add 로 충분한가
history        노드마다 한 줄씩 더한다                  예 — 계속 쌓이는 게 맞다
cities         ① collect_city 병렬 3개가 처음 쓴다      예
               ② repair_city 가 같은 도시를 다시 쓴다   **아니오 — 중복이 쌓인다**
city_failures  ①② 둘 다 쓴다. 고쳐지면 **지워져야** 한다 **아니오 — 실패가 영영 남는다**
```

`repair_city` 는 부족한 칸을 채운 **같은 도시**를 다시 돌려줍니다.
`operator.add` 면 `[하노이, 다낭, 호이안, 하노이, 다낭, 호이안]` 이 되어
`check_information` 이 "도시 6개"로 셉니다.

`city_failures` 는 한 발 더 갑니다. **단순 upsert 로도 부족합니다** — 한 번 실패한
도시가 재수집에 성공하면 그 줄이 **사라져야** 게이트 화면이 거짓말을 하지 않습니다.
그래서 `merge_failures` 는 `why` 가 빈 줄이 오면 기존 줄을 지웁니다.
**성공을 "기록이 사라지는 것"으로 표현합니다.**

```text
A(operator.add)  처음엔 맞다. 재수집 한 번이면 도시가 6개가 된다
B(필드 분리)      cities_하노이 / cities_다낭 ... 도시 수가 실행 중에 정해지므로 불가능
C(upsert)        처음에는 이어 붙고, 같은 이름이 오면 갈아 끼운다  ← 이 그래프에 맞다
```

> **`history` 는 A, `cities` 는 C, `city_failures` 는 C + 삭제.**
> 한 그래프 안에서 필드마다 reducer 가 다를 수 있습니다.

<!-- FIXED:END -->

---

## 읽기 5 — 내 답 적기

<!-- ANSWERS:BEGIN -->

### `G-병렬범위`
- 고른 것: B (도시별 + 국가정보와 도시선정)
- 이유: 도시끼리 서로의 결과를 안 보므로 독립이고, 전체 시간이 도시 합계가 아니라 가장 긴 도시 하나 수준이 된다. 권장값 그대로.

### `G-병렬충돌`
- 고른 것: C (이름 기준 upsert reducer)
- 이유: repair_city 가 같은 도시를 다시 돌려주므로 add 면 도시가 중복된다. cities 는 upsert, city_failures 는 upsert + 성공 시 삭제, history 는 이어 붙임. 권장값 그대로.

### 실패를 먼저 봤습니까?
- `run_once.py` 가 낸 오류 메시지 첫 줄: `langgraph.errors.InvalidUpdateError: At key 'history': Can receive only one value per step. Use an Annotated key to handle multiple values.` (history 의 reducer 를 뗐을 때 · 교육생 설명: 같은 걸음에 두 노드가 같은 칸에 썼기 때문)

<!-- ANSWERS:END -->

---

## 읽기 6 — Claude가 정리한 결과

<!-- PROJECT:BEGIN -->

| 결정 ID | 확정 값 | 고른 이유 | 승인 시각 |
| --- | --- | --- | --- |
| `G-병렬범위` | B — 도시별 (+ 국가정보와 도시선정) | 도시끼리 독립이라 안전하게 나란히 돌릴 수 있다 | 2026-10-23 |
| `G-병렬충돌` | C — 이름 기준 upsert reducer | 재수집이 같은 도시를 다시 줘서 add 면 중복이 쌓인다 | 2026-10-23 |

**권장값을 골랐다면 `state.py` 는 이미 이 모양입니다.** 아래는 붙여 넣으라는 뜻이
아니라 **지금 무엇이 있는지**를 옮겨 적은 것입니다.

> ⚠ **여기 적힌 것은 `cities` 와 `history` 둘뿐입니다.** 실제로는 `city_failures` 에도
> reducer 가 붙어 있고, 그것은 `merge_cities` 와 규칙이 다릅니다 (성공하면 줄이
> **지워져야** 하므로 단순 upsert 가 아닙니다). 바로 아래 `city_failures` 절을 보십시오.

```python
# ① 파일 위쪽 — reducer 함수
import operator


def merge_cities(old: list, new: list) -> list:
    """도시 이름을 키로 upsert. 같은 이름이면 **새 것으로 교체**한다.

    `collect_city` 는 fan-out 으로 [도시1개] 를 돌려주고,
    `repair_city` 는 고친 [그 도시 1개] 를 돌려준다. 둘 다 이 reducer 를 지난다.
    순서를 지키려고 dict 가 아니라 리스트를 유지한다 (파이썬 dict 는 삽입 순서 보존).
    """
    merged = {}
    for city in list(old or []) + list(new or []):
        if isinstance(city, dict) and (city.get("name") or "").strip():
            merged[city["name"].strip()] = city
    return list(merged.values())


# ② TravelState 안 — 병렬 3개 + 재수집이 같은 필드에 쓴다
    cities: Annotated[list[dict], merge_cities]

# ③ TravelState 안 — 여러 노드가 한 걸음에 한 줄씩 더한다
    history: Annotated[list[str], operator.add]
```

#### `city_failures` 의 reducer — 규칙이 다릅니다

```python
def merge_failures(old: list, new: list) -> list:
    """도시별 실패 기록 upsert. **`why` 가 비면 그 줄을 지운다** (= 이번엔 성공)."""
    merged = {}
    for row in list(old or []) + list(new or []):
        if not isinstance(row, dict) or not row.get("city"):
            continue
        if (row.get("why") or "").strip():
            merged[row["city"]] = row
        else:
            merged.pop(row["city"], None)
    return list(merged.values())


    city_failures: Annotated[list[dict], merge_failures]
```

**성공을 "기록이 사라지는 것"으로 표현합니다.** 단순 upsert 면 한 번 터진 도시가
고쳐진 뒤에도 게이트 화면에 실패로 계속 남아 사람이 잘못 판단합니다.

**확인**

```bash
python scripts/check_graph_shape.py     # 3번 검사 OK → 12개 검사행 전부 PASS
python scripts/run_once.py --mode replay --auto proceed   # 게이트 A 통과 → 게이트 B 에서 스스로 멈춘다
python scripts/verify_all.py --skip-quality               # 구조 · 루프 A · 루프 B 만 (exit 0)
```

게이트 B 에 `done` 을 주지 않습니다 (`--auto proceed,done` 금지). `done` 은 정성 3회를 시작하고,
정성은 `replay` 에서도 `claude -p` 로 실제 판정을 합니다 (6~12분). STEP 4 확인 실행에서 정성 3회를
돌리지 않습니다 — reducer 가 맞는지는 루프 A 의 병렬 수집 · 재수집에서 이미 드러납니다.

<!-- MACHINE:BEGIN -->
```json
{
  "step": 4,
  "produces": "travel_graph/state.py",
  "decisions": {
    "G-병렬범위": "B",
    "G-병렬충돌": "C"
  },
  "fixed": {
    "parallel_points": [
      "read_request -> {collect_country, select_cities}  정적 간선 2개",
      "select_cities -Send-> collect_city x N            동적 fan-out",
      "diagnose_info · human_gate_a -Send-> repair_city x 다친 도시 + repair_country x 0|1   재수집 fan-out (fan_out_repairs)"
    ],
    "fan_in": "add_edge([\"collect_country\", \"collect_city\"], \"check_information\")",
    "reducers": {"cities": "merge_cities (upsert)", "city_failures": "merge_failures (upsert · why 가 비면 삭제)",
                 "history": "operator.add"},
    "no_reducer_needed": ["country_intro", "selected_city_names"],
    "detours": "순차 — 한 번에 한 원인(failure_kind 하나). Send 없음 · reducer 추가 없음 (처방 가지 칸은 덮어쓰기). fix_detour 는 cities 전체를 돌려주고 merge_cities 가 이름으로 갈아 끼운다",
    "rule": "겹치는 필드에만 reducer 를 붙인다. 병렬이어도 다른 필드면 필요 없다",
    "observed_error": "InvalidUpdateError: Can receive only one value per step"
  },
  "inherited": {
    "city_count": 2
  }
}
```
<!-- MACHINE:END -->

<!-- PROJECT:END -->

---

## 읽기 7 — 이 STEP이 끝나면 무엇이 진행되는가

| 항목 | 내용 |
| --- | --- |
| **지금 코드가 만들어지나?** | **권장값이면 이미 붙어 있습니다** — 읽기 1 에서 뗀 reducer 를 되붙이면 끝입니다. 세 필드(`cities` · `city_failures` · `history`)에 붙고, 함수는 두 개(`merge_cities` · `merge_failures`), `history` 는 `operator.add` 입니다. 다른 값을 고르면 이 세 곳을 고칩니다. |
| **Claude가 하는 일** | ① 답 2개 기록 → ② 뗀 reducer 를 되붙였는지 확인 (다른 값을 골랐으면 `state.py` 세 곳 수정) → ③ 구조 검사 + 1회 실행 |
| **바뀌는 파일** | `specs/04_PARALLEL.md` · `specs/00_DECISION_LOG.md` · `travel_graph/state.py` |
| **바뀐 것을 확인하는 법** | 그래프가 **게이트 B 까지 막힘 없이 돕니다** (`run_once.py --mode replay --auto proceed`). `verify_all.py --skip-quality` 가 `exit 0` 이 됩니다 — 정성(루프 C)은 Studio 실행에서 돕니다. |

> 킷은 완성본이라 게이트가 이미 있습니다. `--auto proceed` 가 게이트 A 에 답하고, 게이트 B 에서는
> 답이 없어 스스로 멈춥니다 (`human_gate_b 에서 답 없이 끝냄`). 게이트는 STEP 5 에서 읽고 정합니다.

---

## 읽기 8 — 완료 확인과 다음 명령

- [ ] `InvalidUpdateError` 를 **직접 봤다**
- [ ] `cities` 에 upsert reducer 가, `history` 에 `operator.add` 가 붙었다
- [ ] `check_graph_shape.py` 가 **검사행 12개 전부 OK** 다
- [ ] `run_once.py --mode replay --auto proceed` 가 오류 없이 게이트 B 까지 돈다
- [ ] 상태가 `APPROVED`다

```bash
python scripts/check_graph_shape.py
python scripts/verify_all.py --skip-quality
python scripts/validate_specs.py --step 4
```

<!-- STATUS:BEGIN -->
STATUS: APPROVED
<!-- STATUS:END -->

```text
STEP 5 진행해줘
```
