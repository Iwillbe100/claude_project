# STEP 2 — 조건④ 노드 경계

> **한 줄 목적:** **무엇이 노드가 되고 무엇이 안 되는지** 정한다.
> **내가 결정할 것: 3개** · **코드 변경: 없음** (무엇을 골라도 — 킷이 이미 만든 루프 골격 14 · 진단 2개 · 규칙 처방 가지를 읽고 승인한다)

| 이전 | 다음 | 문서 규칙 | 결정 장부 |
| --- | --- | --- | --- |
| [STEP 1 — 상태 스키마](01_STATE_SCHEMA.md) | [STEP 3 — 간선 조건](03_EDGE_CONDITION.md) | [00_INDEX](00_INDEX.md) | [00_DECISION_LOG](00_DECISION_LOG.md) |

---

## 읽기 1 — 이 STEP에서 정하는 것

**루프의 조건④ '행동 경계'가 여기로 옵니다.**

이 STEP 은 **코드를 만들지 않습니다.** 킷이 만들어 둔 **루프 골격 14**(노드 14개)가 왜 그렇게
쪼개졌는지 읽고 승인하는 자리입니다. 3분이면 끝납니다. **대신 이 3분이 이 실습에서 제일 중요합니다.**

```text
가장 흔한 오해   "루프의 작업 8개 → 그래프의 노드 8개"
실제             작업 8개 → 루프 골격 14(노드 14개) + 간선 1개
```

이 비대칭이 어디서 오는지가 이 STEP 의 전부입니다.

Studio 그림에는 노드가 **22개** 보입니다. 루프 골격 14 곁에 **진단 노드 2개**와 **규칙 처방 가지
노드 6개**(킷 기본 가지 3개 × fix · test)가 붙었기 때문입니다. 루프 골격은 늘지도 줄지도 않고,
노드는 **문제가 난 지점에서만** 늘어납니다 — 읽기 3 의 (8) 에서 봅니다.

---

## 읽기 2 — 앞에서 물려받은 결정

<!-- PROJECT:BEGIN -->

| 물려받은 것 | 값 | 어디서 |
| --- | --- | --- |
| 상태 범위 | B — 판정에 필요한 것 + 제어 필드 | `G-상태범위` |
| 판정 필드 | A — 남긴다 (`*_verdict`) | `G-판정필드` |

<!-- PROJECT:END -->

---

## 읽기 3 — 이미 정해 둔 것 (읽고 넘어가기)

### (1) ★ 작업 8개가 어떻게 옮겨졌나 (고정)

| 루프 작업 | 그래프에서 | 종류 | 왜 |
| --- | --- | --- | --- |
| `TASK-입력읽기` | `read_request` | 노드 | 요청서를 읽어 상태의 입력 칸을 채운다 |
| `TASK-국가정보` | `collect_country` | 노드 · **병렬** | 도시와 무관 → 도시 선정과 나란히 |
| `TASK-도시선정` | `select_cities` | 노드 | 여기서 도시 수가 정해져야 병렬 폭이 결정된다 |
| `TASK-명소수집` | `collect_city` | 노드 · **도시별 병렬** | 도시끼리 서로의 결과를 안 본다 |
| `TASK-일정수집` | `collect_city` **에 합침** | — | 그 도시의 명소만 참조 → 책임이 하나다 |
| `TASK-페이지생성` | `build_page` | 노드 | 모든 수집이 끝난 뒤 한 번만 |
| `TASK-기능점검` | **(간선)** | **노드가 아니다** | `check_page → diagnose_page → build_page` 되돌이 간선(진단 B 뒤 `route_after_page` 의 `retry`)이 대신한다 |
| `TASK-정성점검` | `quality_pass` | 노드 · **순차 3회** | 회차 번호가 상태에 있어야 라우터가 셀 수 있다 |

### (2) ★★ 루프에는 없던 노드 8개 — 이게 핵심입니다

| 노드 | 루프에서는 | 왜 노드가 되나 |
| --- | --- | --- |
| `check_information` | 검사기 A (스크립트) | **라우터가 읽을 판정 값을 상태에 써야 한다** |
| `check_page` | 검사기 B (스크립트) | 같은 이유 |
| `human_gate_a` | 되물음 (사람이 답함) | `interrupt` 로 멈추고 사람의 답을 **상태에 받아 적는다** |
| `human_gate_b` | 되물음 | 같은 이유. **선택지가 달라서** 노드를 따로 둔다 |
| **`check_quality`** | 검사기 C (스크립트) | **품질이 아니라 절차를 판정해 상태에 쓴다** |
| **`repair_city`** | `RESEARCH` 행동 (루프 안의 분기) | **재수집도 fan-out 이다.** 검사기가 지적한 도시만 `Send` 로 받는다 |
| **`rebuilder`** | 없음 | 사람이 게이트에 적은 지시문을 **실제로 소비하는** 자리 |
| **`repair_country`** | `RESEARCH` 행동 | 국가 소개도 **지적된 칸만** patch 로 고친다. 같은 fan-out 을 탄다 |

**셈이 맞는지 확인하십시오.** 작업 8개 중 노드가 되는 것은 6개
(`일정수집` 은 `collect_city` 에 합쳐지고, `기능점검` 은 간선이 됩니다).
거기에 위의 8개를 더해 **6 + 8 = 14개**입니다. 이 14개가 그래프의 **루프 골격 14**입니다.
그림에 보이는 나머지 8개(진단 2 · 처방 가지 6)는 루프 골격이 아니라 곁에 붙은 것이라 (8) 에서 따로 셉니다.

### ★ 왜 재수집이 **수집 노드 재사용**이 아니라 별도 노드인가 (고정)

"`collect_country` 로 되돌아가면 노드를 안 늘려도 되지 않나"가 자연스러운 질문입니다.
**안 됩니다.** 합류 때문입니다.

```text
add_edge(["collect_country", "collect_city"], "check_information")   ← 합류

최소 재현        A ─┐
                 B ─┴→ J ──조건──→ A      (J 에서 A 로만 되돌아감)
실측 결과        ['A', 'B', 'J1', 'A']    ← 거기서 끝. 예외도 없음
```

`A` 로 되돌아가도 합류가 `B` 를 계속 기다려 `J` 가 두 번째로 열리지 않습니다.
**LangGraph 는 예외를 내지 않고 그냥 멈춥니다** — 조용한 정지라 제일 알아채기
어려운 종류입니다. 그래서 재수집은 합류를 우회하는 **별도 노드**여야 합니다.
취향이 아니라 구조 제약입니다.

**`collect_city` 와 `repair_city` 를 왜 나누나.** 하는 일이 다릅니다. 첫 수집은 고른
도시를 **전부** 받고, 재수집은 지적된 도시만 받습니다. 한 노드로 두면 지적이 없는
도시가 들어와도 걸러 낼 데가 없어 **첫 수집으로 떨어집니다** — 멀쩡한 도시를 통째로
다시 뽑느라 부족한 칸이 줄지 않습니다.

**`rebuilder` 를 왜 따로 두나.** `build_page` 는 결정론 렌더러라 사람의 지시문을 받을
데가 없습니다. `rebuilder` 는 HTML 을 직접 고치지 않고 `output/research_data.json` 을
고쳐 화면을 다시 만듭니다 — HTML 만 손대면 다음 `build_page` 에서 날아갑니다.

```text
루프에서 검사기는   "돌려 보고 종료 코드를 읽는 것"
그래프에서 검사기는 "판정 값을 상태에 쓰는 노드"

  왜?  간선이 조건을 보려면 그 값이 상태에 있어야 하기 때문이다.
       라우터는 상태만 본다. 스크립트를 돌릴 수 없다.
```

### (3) 상태전이가 두 종류라서 그렇습니다 (고정)

```text
데이터 상태전이   info_verdict: UNKNOWN → SHORT     ← 노드가 만든다
제어 상태전이     check_information → repair_city   ← 간선이 만든다
```

루프에서는 이 둘이 붙어 있었습니다 (검사기 돌리고 → 종료 코드 보고 → 다음 작업).
그래프에서는 **강제로 분리됩니다.** 그래서 검사기가 노드가 되어야 합니다.

### (4) 노드 분리 기준 7가지 (고정) — 하나라도 다르면 쪼갠다

```text
책임이 다르다
실패했을 때 재시도 전략이 다르다
쓰는 권한이나 도구가 다르다
입출력을 따로 기록해야 한다
이 지점에서 분기해야 한다
이 지점부터 다시 실행할 필요가 있다
사람의 승인이 필요하다
```

반대로 **모든 작은 함수를 노드로 만들면 안 됩니다.**

```text
명소 수집 → 일정 배치     둘 다 "그 도시 하나"에 대한 일이고
                          재시도 전략도 같다 → 한 노드(collect_city)
```

### (5) 노드는 LLM이 아닙니다 (고정)

| 노드 | 실행 주체 | 이유 |
| --- | --- | --- |
| `read_request` | 결정론 코드 | 파일 파싱 |
| `collect_country` `select_cities` `collect_city`<br/>`repair_city` `repair_country` | **LLM (`claude -p`)** | 의미 해석이 필요 |
| `check_information` `check_page` `check_quality` | **결정론 코드** | **세는 일에 판단이 끼면 안 된다** |
| `build_page` | 결정론 코드 | 화면 이름표가 계약으로 고정돼 있다 |
| `quality_pass` `rebuilder` | **LLM + 결정론** | 고칠 곳은 LLM 이 지목, 고치기(`apply_fixes`)·해시·기록은 코드 |
| `human_gate_a` `human_gate_b` | 사람 | |
| `diagnose_info` `diagnose_page` | **결정론 코드** | 시험지를 등록 순서대로 풀어 볼 뿐이다 — **원인을 가리는 일에도 판단이 끼면 안 된다** |
| `fix_<이름>` ×3 (함수 `nodes.fix_detour` 하나) | **결정론 코드** | 정해진 고칠 법이다. LLM 을 부르지 않는다 (`image_dead` 만 live 에서 바꾼 주소를 실제로 열어 보고, 2회째에는 Commons 를 검색한다) |
| `test_<이름>` ×3 (함수 `nodes.test_detour` 하나) | **결정론 코드** | 진단 때와 **같은 시험지**를 다시 푼다 |

> LangGraph 의 강점은 **결정론 코드와 LLM 단계를 한 그래프에 섞을 수 있다는 것**입니다.

### (6) `quality_pass` 는 왜 노드 하나인가 (고정)

정성 점검 3회를 노드 세 개로 만들고 싶어집니다. 그러면 안 됩니다.

```text
잘못  quality_pass_1 · quality_pass_2 · quality_pass_3 을 정적 간선으로 나란히
      → 정적 간선 여러 개는 병렬이다. 셋이 같은 파일을 동시에 고친다.

맞음  quality_pass ──▶ check_quality ──회차 < 3──▶ quality_pass   (순환 · 순차)
```

**세 회차는 서로의 결과 위에 쌓입니다.** 2회차가 보는 파일은 1회차가 고친 뒤의
파일이어야 하고, 판정기가 파일 해시로 그 사슬을 확인합니다.
회차를 구분하는 것은 노드가 아니라 **상태 안의 카운터**입니다.

### (7) `quality_pass` 는 LLM 인데 왜 판정 독립이 안 깨지나 (고정)

```text
quality_pass   글을 **고치는** 쪽.        LLM 이 규율 10개를 보고 고칠 것을 지목한다
check_quality  **판정하는** 쪽.          결정론 코드가 절차를 본다

  판정기가 보는 것 : 3회를 돌았는가 · 규율 10개를 다 판정했는가 ·
                     위반이라 적은 것을 실제로 고쳤는가 · 해시가 그에 맞게 바뀌었는가
  판정기가 안 보는 것 : 글이 좋아졌는가
```

품질에 점수를 매기면 **글을 쓴 쪽이 자기 글에 점수를 주게** 됩니다.
그래서 품질이 아니라 **절차**를 채점합니다. 이것이 루프 C의 설계 핵심입니다.

### (8) 진단 노드와 규칙 처방 가지 — 노드는 문제가 난 지점에서만 늘린다 (고정)

루프 골격 14는 잠급니다. 그 대신 **검사기 바로 뒤에 진단 노드**를 하나씩 세우고,
"정해진 고칠 법이 있는 문제"만 **규칙 처방 가지**로 보냅니다 — fix = 처방(규칙대로 고친다),
test = 재검(같은 시험지로 다시 잰다). 나머지 부족은 재수집(LLM)이 맡습니다.

```text
 check_* ─▶ ◇diagnose_* ─┬─ (처방 가지 대상 없음) ────────────▶ 루프 골격 그대로
                         └─ <이름> ─▶ fix_<이름> ─▶ test_<이름> ─┬ 합격           → check_*   (검사기로 복귀 · 바퀴 안 씀)
                                                                ├ 불합격 · 한도 안 → fix_<이름> (한 번 더)
                                                                └ 불합격 · 한도 끝 → ★human_gate_* (사람)
```

**왜 진단이 노드인가 — 판정과 원인은 다른 일입니다.**

```text
check_information   "SHORT · 부족 9곳"          판정 — 기준을 채웠나   (루프 킷과 같은 검사기)
diagnose_info       "그중 죽은 사진 주소 1곳"    원인 — 무엇이 터졌나   (처방 가지 시험지)
```

검사기는 루프 킷과 바이트 단위로 같은 파일이라 **세기만** 하고, 고칠 수도 없습니다. 원인을
가리려면 처방 가지 시험지를 **돌려야** 하는데, 앞의 "왜 재수집이 별도 노드인가" 절 끝 상자에서 본 대로 라우터는 상태만 볼 뿐
스크립트를 돌릴 수 없습니다. 그래서 시험지를 푸는 노드가 원인(`failure_kind`)을 **상태에 써야** 합니다 —
검사기가 노드가 된 것과 똑같은 이유입니다. 분리 기준 (4) 로 보면 "책임이 다르다" ·
"이 지점에서 분기해야 한다" · "입출력을 따로 기록해야 한다"(실패 기록 `evidence/failures/`)
세 개에 걸립니다. 그리고 진단은 **판정이 PASS 여도 돕니다** — 깨진 글자처럼 검사기가
세지 않는 결함이 있기 때문입니다.

검사기 → 진단은 **정적 간선 하나**입니다. 검사기에 조건부 간선까지 달면 정적 간선과
조건부 간선이 **둘 다** 실행됩니다 (정적 간선은 if/else 가 아닙니다 — STEP 4).
그래서 라우터(`route_after_info` · `route_after_page`)는 검사기가 아니라 **진단 뒤에** 붙습니다.

**왜 처방 가지는 수집 노드가 아니라 검사기로 돌아오나.** 두 가지 이유입니다.

```text
① 합류       collect_* 로 돌아가면 위 ★ 의 최소 재현처럼 합류가 영영 기다린다 — 조용한 정지
② 판정 독립  처방 가지 시험지는 "그 문제가 사라졌나"만 본다. 계약을 채웠나는
             루프 킷과 같은 검사기(check_information · check_page)로 다시 재야 한다
```

`repair_*` 가 `check_information` 으로 돌아오는 것과 같은 모양입니다. 다만 처방 가지에서
**합격하고 돌아온 방문은 바퀴로 세지 않습니다** — 처방 가지는 자기 한도(처방 한도 `detour_limit`,
2회)를 따로 갖기 때문입니다. 세면 가지가 한 번 돌 때마다 재수집 기회가 하나씩 사라집니다.

**왜 재수집(`repair_*`)에 맡기지 않고 따로 길을 내나.** 분리 기준 "실패했을 때 재시도 전략이
다르다"에 걸립니다. 실측에서 모델은 사진 주소 속 해시 두 글자를 지어냈습니다
(킷에 든 예시 인계본 `graph/04_RUN_EVIDENCE.md` 1-b — 이미지 11장 전부 죽음. 루프 킷에서 직접 뽑은
인계본에는 이 절이 없을 수 있습니다). 같은 프롬프트로
다시 모으면(LLM) **같은 식으로 또 지어냅니다.** 이런 문제는 정해진 절차(결정론)로 고쳐야 합니다.
킷 기본 가지 `image_dead` 가 이렇게 태어났습니다 — 루프 킷 실행 로그에서 잡힌 실패를 규칙 노드로
뺀 것입니다. 원인을 모르거나 고칠 법이 정해지지 않은 부족은 아직 재수집(LLM)에 둡니다 — 같은 실패가
로그에서 반복되고 고칠 법이 정해지면 가지로 뺍니다(그래프가 자라는 방향).

**fix · test 노드 6개가 함수 2개를 나눠 씁니다.** 모든 처방 가지가 **같은 모양**이라 함수도
같습니다 (`nodes.fix_detour` · `nodes.test_detour`). 어느 가지인지는 진단이 적어 둔
`failure_kind` 로 압니다 — 처방 가지는 한 번에 하나만 돌기 때문에 헷갈릴 일이 없습니다.
가지마다 달라지는 것은 **세 조각**뿐입니다.

```text
travel_graph/detours/registry.py        한 줄     이름 · 루프(A|B) · 제목    ← 순서 = 진단 우선순위
travel_graph/detours/<이름>.py          fix()     고치는 법(처방) · inject() 실패 재현
scripts/detour_tests/test_<이름>.py     run()     시험지 — 진단도 이것으로, 합격도 이것으로
```

등록부에 한 줄을 쓰면 `build.py` 가 노드 두 개와 간선 셋(back · retry · gate)을 **같은
모양으로** 붙입니다. 처방 가지 노드는 데이터(`cities` · `country_intro`)와 처방 가지 칸만 쓰고,
**판정 · 바퀴 · 게이트 칸은 쓰지 않습니다** — 루프 골격의 것이기 때문입니다.
`check_graph_shape.py` **11번 검사(처방 가지 계약)** 가 이 모양 전부를 봅니다.

**그래서 노드 수는 이렇게 셉니다.**

```text
루프 골격  14   늘지도 줄지도 않는다 (G-노드개수 의 "킷 매핑 (14개)" 가 이것이다)
진단        2   diagnose_info (루프 A · check_information 뒤) · diagnose_page (루프 B · check_page 뒤)
처방 가지   6   fix_encoding → test_encoding · fix_image_dead → test_image_dead (루프 A)
                fix_image_spec → test_image_spec (루프 B)
─────────────
그림       22
```

교육생이 노드를 늘리는 자리는 **STEP 6 (조건부)의 처방 가지 하나뿐**입니다 (등록부 한 줄 = 노드 2개 ·
로그에 후보가 있을 때만). 루프 골격이나 진단에 노드를 더하지 않습니다. "노드를 쪼갠다"가 아니라
**"처방 가지로 뺀다"** 입니다.

---

## 읽기 4 — 내가 결정할 질문

<!-- FIXED:BEGIN -->

| 결정 ID | 질문 | 이 값이 바꾸는 것 |
| --- | --- | --- |
| `G-노드개수` | 노드를 몇 개로 쪼개나? | 그림의 복잡도 · 재시도 단위 |
| `G-검사기노드화` | 검사기를 노드로 넣나? | 라우터가 판정을 볼 수 있는지 |
| `G-실행주체` | 어느 노드를 LLM에 맡기나? | 재현성 |

**쉬운 선택지**

| 결정 ID | A | B | C | 권장 |
| --- | --- | --- | --- | --- |
| `G-노드개수` | 루프와 1:1 (8개) | **킷 매핑 (14개)** | 더 세분 (16개) | **B** |
| `G-검사기노드화` | **노드로 넣는다** | 라우터 안에서 검사기를 호출 | 그래프 밖에서 사람이 | **A** |
| `G-실행주체` | 전부 LLM | **위 (5)번 표대로 섞는다** | 전부 결정론 | **B** |

```text
G-노드개수 A를 고르면       검사기가 노드가 아니게 되어 라우터가 판정을 못 본다
G-노드개수 C를 고르면       책임·재시도 전략이 같은 것을 나누게 된다 (아래 참고)
G-검사기노드화 B를 고르면    라우터가 부작용을 갖는다. 라우터는 경로만 골라야 한다
G-실행주체 A를 고르면       판정까지 LLM이 한다 → AI가 자기 채점표를 통과시킨다
```

> **C(더 세분)를 고르면 안 되는 이유 — 여기가 헷갈리는 자리입니다.**
>
> C 는 `collect_city` 와 `repair_city` 를 각각 **명소 노드 + 일정 노드**로 쪼개
> 16개로 만드는 안입니다. 킷이 14개인 것과 **숫자가 비슷하지만 전혀 다른 이유**입니다.
>
> ```text
> 킷의 14개   research 를 없애고 repair_city · repair_country · rebuilder 를 더한 결과
>             (재수집이 fan-out 이 되었고, 사람의 지시문을 받을 노드가 생겼다)
> C 의 16개   명소와 일정을 노드로 쪼갠 결과
> ```
>
> **킷은 명소와 일정을 노드로 쪼개지 않습니다.** 책임이 하나(그 도시)이고 재시도
> 전략도 같아서 분리 기준 7가지 어디에도 걸리지 않기 때문입니다. 대신 노드 **안에서**
> `claude -p` 를 두 번 부릅니다 — 그것은 노드 경계 문제가 아니라 **한 응답이 감당할
> 분량** 문제입니다. Studio 그림에는 상자 하나로 보입니다.
>
> 노드를 쪼개는 기준과 호출을 나누는 기준은 **다릅니다.** 이 구분이 STEP 2 의 요점입니다.

> **`G-실행주체` A가 왜 위험한지**는 루프 킷에서 이미 겪었습니다.
> 명세는 13칸을 요구했는데 AI가 만든 채점표는 3칸만 셌고, 검사는 통과했습니다.

<!-- FIXED:END -->

---

## 읽기 5 — 내 답 적기

<!-- ANSWERS:BEGIN -->

### `G-노드개수`
- 고른 것: B (킷 매핑 14개)
- 이유: 검사기가 노드여야 라우터가 판정을 볼 수 있고, 재수집이 fan-out 이어야 지적된 도시만 다시 뽑는다. 명소·일정은 책임과 재시도 전략이 같아 한 노드로 둔다. 권장값 그대로.

### `G-검사기노드화`
- 고른 것: A (노드로 넣는다)
- 이유: 라우터는 상태만 읽고 경로만 골라야 하므로 검사 결과를 상태에 쓰는 노드가 필요하다. 권장값 그대로.

### `G-실행주체`
- 고른 것: B (읽기 3의 (5)번 표대로 섞는다)
- 이유: 의미 해석(수집·글쓰기)은 LLM, 세는 일(검사·진단·렌더)은 결정론, 승인은 사람. 판정까지 LLM이 하면 자기 채점표를 통과시킨다. 권장값 그대로.

<!-- ANSWERS:END -->

---

## 읽기 6 — Claude가 정리한 결과

<!-- PROJECT:BEGIN -->

| 결정 ID | 확정 값 | 고른 이유 | 승인 시각 |
| --- | --- | --- | --- |
| `G-노드개수` | B — 킷 매핑 (루프 골격 14개) | 검사기가 노드이고 재수집이 fan-out 이어야 하며, 명소·일정은 책임이 같아 한 노드 | 2026-10-23 |
| `G-검사기노드화` | A — 노드로 넣는다 | 라우터가 상태의 판정 값만 읽고 경로만 고른다 | 2026-10-23 |
| `G-실행주체` | B — (5)번 표대로 섞는다 | 판정에 LLM이 끼면 자기 채점표를 통과시킨다 | 2026-10-23 |

**승인된 루프 골격 14** (노드 14개)

```text
결정론      read_request · check_information · check_page · check_quality · build_page
LLM         collect_country · select_cities · collect_city ·
            repair_city · repair_country
LLM+결정론   quality_pass · rebuilder   (고칠 곳은 LLM 이 지목, 고치기·해시·기록은 코드)
사람         human_gate_a · human_gate_b   (게이트 B 는 두 번 선다)
```

**그리고 곁에 붙은 진단 2개 · 규칙 처방 가지 6개** (킷 고정 · 전부 결정론 — 그림에는 모두 22개)

```text
진단        diagnose_info · diagnose_page            (검사기 바로 뒤 · 정적 간선 하나)
처방 가지   fix_encoding → test_encoding             (루프 A)
            fix_image_dead → test_image_dead         (루프 A)
            fix_image_spec → test_image_spec         (루프 B)
            함수는 nodes.fix_detour · nodes.test_detour 둘을 나눠 쓴다
            합격하면 그 루프의 검사기로 복귀 · 처방 한도(2회)를 다 쓰면 그 루프의 게이트로
```

**`collect_city` 와 `repair_city` 를 왜 나눴나** — 하는 일이 다르기 때문입니다.
첫 수집은 고른 도시를 **전부** 받고, 재수집은 검사기가 **지적한 도시만** 받습니다.
한 노드로 두면 지적이 없는 도시가 들어와도 걸러 낼 데가 없어 **첫 수집으로 떨어집니다.**
실제로 그랬고, 멀쩡한 도시를 통째로 다시 뽑느라 부족한 칸이 줄지 않았습니다.

**`rebuilder` 를 왜 따로 두나** — `build_page` 는 결정론 렌더러라 사람의 지시문을
받을 데가 없습니다. 게이트 B 에서 적은 `note` 를 실제로 소비하는 노드가 필요합니다.

**`collect_city` 는 노드 하나지만 `claude -p` 를 두 번 부릅니다** (명소 / 일정).
노드를 쪼갠 것이 아니라 **한 응답이 감당할 분량**을 나눈 것입니다. Studio 그림에는
상자 하나로 보입니다 — 노드 분리 기준(책임·재시도 전략·분기 지점) 어디에도
걸리지 않기 때문입니다.

<!-- MACHINE:BEGIN -->
```json
{
  "step": 2,
  "produces": "spec_only",
  "decisions": {
    "G-노드개수": "B",
    "G-검사기노드화": "A",
    "G-실행주체": "B"
  },
  "fixed": {
    "task_to_node": {
      "TASK-입력읽기": "read_request",
      "TASK-국가정보": "collect_country",
      "TASK-도시선정": "select_cities",
      "TASK-명소수집": "collect_city (claude -p 1회차)",
      "TASK-일정수집": "collect_city (claude -p 2회차)",
      "TASK-재수집": "repair_city (Send fan-out · 지적된 도시만)",
      "TASK-지시반영": "rebuilder (게이트 B 의 note 를 소비)",
      "TASK-페이지생성": "build_page",
      "TASK-기능점검": "(간선) check_page -> diagnose_page -retry-> build_page",
      "TASK-정성점검": "quality_pass"
    },
    "new_nodes": ["check_information", "check_page", "check_quality",
                  "human_gate_a", "human_gate_b", "repair_city", "repair_country",
                  "rebuilder"],
    "executor": {
      "read_request": "code", "collect_country": "llm", "select_cities": "llm",
      "collect_city": "llm", "check_information": "code", "repair_city": "llm",
      "repair_country": "llm",
      "human_gate_a": "human", "build_page": "code", "check_page": "code",
      "human_gate_b": "human", "rebuilder": "llm+code",
      "quality_pass": "llm+code", "check_quality": "code",
      "diagnose_info": "code", "diagnose_page": "code",
      "fix_encoding": "code", "test_encoding": "code",
      "fix_image_dead": "code", "test_image_dead": "code",
      "fix_image_spec": "code", "test_image_spec": "code"
    },
    "spine_nodes": ["read_request", "collect_country", "select_cities", "collect_city",
                    "check_information", "repair_city", "repair_country", "human_gate_a",
                    "build_page", "check_page", "human_gate_b", "rebuilder",
                    "quality_pass", "check_quality"],
    "diagnose_nodes": {
      "diagnose_info": "check_information 뒤 (루프 A) · 정적 간선 하나",
      "diagnose_page": "check_page 뒤 (루프 B) · 정적 간선 하나"
    },
    "detours": {
      "registry": "travel_graph/detours/registry.py (한 줄 = 처방 가지 하나 · 순서 = 진단 우선순위)",
      "kit": {"encoding": "A", "image_dead": "A", "image_spec": "B"},
      "nodes_per_detour": ["fix_<kind>", "test_<kind>"],
      "node_functions": ["nodes.fix_detour", "nodes.test_detour"],
      "after_test": {"back": "그 루프의 검사기 (A: check_information · B: check_page)",
                     "retry": "같은 fix_<kind>", "gate": "그 루프의 게이트"},
      "limit": 2,
      "student_adds": "STEP 6 (조건부 — 로그에 후보가 있을 때만) 에서만 · scripts/new_detour.py 로 등록부 한 줄 = 노드 2개",
      "count": "루프 골격 14 + 진단 2 + 처방 가지 3×2 = 22"
    },
    "split_rules": ["책임", "재시도 전략", "권한·도구", "기록 단위",
                     "분기 지점", "재실행 지점", "사람 승인"],
    "rule": "판정을 LLM에 맡기지 않는다"
  },
  "inherited": {
    "verdict_fields": ["info_verdict", "info_short_slots", "page_verdict", "page_short_slots", "quality_verdict", "quality_short_slots"]
  }
}
```
<!-- MACHINE:END -->

<!-- PROJECT:END -->

---

## 읽기 7 — 이 STEP이 끝나면 무엇이 진행되는가

| 항목 | 내용 |
| --- | --- |
| **지금 코드가 만들어지나?** | **아니오.** `travel_graph/nodes.py` 는 킷이 이미 다 써 뒀습니다. |
| **Claude가 하는 일** | ① 답 3개 기록 → ② 결정 장부에 추가 → ③ STEP 3·4 물려받은 값 갱신 |
| **바뀌는 파일** | `specs/02_NODE_BOUNDARY.md` · `specs/00_DECISION_LOG.md` |
| **내가 할 일** | `travel_graph/nodes.py` 를 열어 루프 골격 14 · 진단 2개 · 처방 가지 공용 함수 2개(`fix_detour` · `test_detour`)의 첫 줄 주석만 훑어보기 |

---

## 읽기 8 — 완료 확인과 다음 명령

- [ ] "작업 8개 → 루프 골격 14(노드 14개) + 간선 1개"를 설명할 수 있다
- [ ] `collect_city` 와 `repair_city` 를 왜 나눴는지 말할 수 있다
- [ ] `quality_pass` 와 `check_quality` 를 왜 두 노드로 나눴는지 말할 수 있다
- [ ] 검사기가 왜 노드가 되어야 하는지 한 문장으로 말할 수 있다
- [ ] 판정 노드가 결정론 코드인 이유를 안다
- [ ] 진단이 왜 검사기와 다른 노드인지(판정 vs 원인), 처방 가지가 왜 수집 노드가 아니라 검사기로 돌아오는지 말할 수 있다
- [ ] 상태가 `APPROVED`다

```bash
python scripts/validate_specs.py --step 2
```

<!-- STATUS:BEGIN -->
STATUS: APPROVED
<!-- STATUS:END -->

```text
STEP 3 진행해줘
```
