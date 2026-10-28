# 그래프 엔지니어링 스타터 킷

**질문 13개에 답하면 루프가 그래프가 되고, Studio에서 돌아간다.**

주제는 루프 킷과 **똑같습니다** — 베트남 여행 정보 웹페이지.
바뀌는 것은 **실행 구조**뿐입니다. 그래야 두 방식을 같은 표에 올려 비교할 수 있습니다.

---

## 30초 요약

```text
1  루프 킷 인계본을 graph/ 에 넣는다   →  계약·데이터·실측이 들어온다
2  질문 13개에 답한다 (STEP 1~5)      →  상태·간선·reducer·게이트를 왜 그렇게 짰는지 정한다 (코드는 완성본)
3  langgraph dev 로 켠다              →  Studio에서 그래프가 도는 걸 본다
4  게이트에서 멈춘다                   →  ★ 내가 방향을 정한다 (3번 — 게이트 A 1 · B 2)
5  정성 3회를 돈다 (킷 고정)           →  셀 수 없는 것은 회차로 닫는다
6  같은 검사기로 잰다                   →  python scripts/verify_all.py
7  실패 기록을 본다 (STEP 6 · 조건부)  →  반복되는 실패가 있을 때만 규칙 처방 가지 하나를 더한다 (약 20분)
                                          후보(보고서 ③ · ③-2)가 없으면 하지 않는다. 루프 B 가지까지면 30~40분 — 과제
```

1~6번(STEP 1~5 + 실행)이 약 60분입니다. 7번은 **로그에 처방 가지 후보가 있을 때만** 합니다.

**그래프로 옮겨서 얻는 것은 "실패가 가지가 된다"는 것입니다.** 루프는 모든 실패를
"한 바퀴 더"로 뭉쳐 처리했지만, 그래프는 원인마다 다른 길을 그림으로 보여 주고(추적),
같은 모양으로 늘리며(확장), 그 실패를 다시 일으켜 같은 길을 다시 태워 볼 수 있습니다(재현 · `inject`).
킷에는 **규칙 처방 가지** 3개(encoding · image_dead · image_spec)가 이미 들어 있습니다 — 알려졌거나
로그로 잡힌 실패를 규칙(결정론) 노드로 빼 둔 것이라, 실행에서 그 실패가 나면 켜지고 안 나면 진단만 지나갑니다.
**그래프는 반복되는 실패를 로그를 따라 규칙 처방 가지로 키웁니다.** 새 실패가 로그에 반복해서 남을 때만
7번(STEP 6)에서 같은 방식으로 가지를 더합니다. 결정은 늘지 않습니다 — **13개 그대로**.

---

## 시작하는 법

### 0) 환경 세팅 (한 번만)

**이 킷 폴더(`graph_starter_kit`) 안에서** Claude Code 를 열고, 아래 한 줄을 그대로
붙여 넣습니다. 상위 폴더에서 열면 `settings/` 를 못 찾습니다.

```bash
cd graph_starter_kit
claude
```

```text
settings 폴더를 파악해서 해당 프로젝트 경로에 세팅 완료해줘.
```

Python 3.12 확보 → `.venv` → 패키지 79개 → `.env` 연결 → 검증 → Studio 기동까지
**5~10분**이면 끝납니다. 미리 준비할 것은 **LangSmith API 키**
(<https://smith.langchain.com> → Settings → API Keys)와 **구독으로 로그인된 Claude Code** 둘입니다 —
`claude` 는 `live` 조사뿐 아니라 `replay` 에서도 정성 3회(루프 C)가 부릅니다.
킷에 든 `.env` 의 `LANGSMITH_API_KEY` 한 줄만 본인 키로 바꾸면 됩니다.
에이전트 없이 손으로 하려면 `settings/SETUP.md` 맨 위의 **"빠른 시작"** 을 따릅니다.

끝나면 아래가 `PASS` 여야 합니다.

```bash
python settings/scripts/verify_env.py
```

> `경고 N` 이 있어도 마지막 줄이 **`ENV_VERIFY: PASS`** 면 통과입니다.

> 이 문서의 `python` · `langgraph` 는 **`.venv` 안의 것**입니다. 새 터미널에서 직접 칠 때는 먼저
> 켭니다 — Windows PowerShell `.\.venv\Scripts\Activate.ps1` · macOS/Linux `source .venv/bin/activate`
> (실행 정책 오류가 나면 `settings/SETUP.md` STEP 2). Claude Code 안에서는 명령마다 활성화가 풀리므로
> `.venv` 의 파이썬 경로(`.venv\Scripts\python.exe` · `.venv/bin/python`)로 부릅니다 (`settings/SETUP.md` R3).

### 1) 준비도 확인

> **내 루프 결과를 쓰려면** 이 명령 전에 `graph/00_START_HERE.md` 의 안내대로 루프 킷의
> `output/graph/` 를 `graph/` 에 덮어씁니다. 안 하면 킷에 든 베트남 예시본으로 그대로 진행합니다.

```bash
python scripts/check_graph_readiness.py     # NOT_READY 가 정상입니다
```

> 처음 실행하면 **`NOT_READY`(exit 2)** 가 나옵니다. **오류가 아닙니다.**
> 아직 STEP 을 하나도 안 했기 때문입니다.

### 2) 시작

```bash
claude
```

Claude Code 안에서 (0 단계에서 연 창이 아직 열려 있으면 그 창에 바로):

```text
STEP 1 진행해줘
```

---

## 폴더 안내

```text
graph/               ★ 루프 킷 인계본 (지금은 예시가 들어 있습니다)
  01_HANDOFF.md        그래프 설계용 — 이것만 읽으면 됩니다
  03_CONTRACT.json     검사 계약. **잠김** — 고치면 비교가 깨집니다
  04_RUN_EVIDENCE.md   실측. 어디에 구멍이 났는지
  05_STATE_SEED.json   Studio 입력에 붙여 넣을 초기 상태
  research_data.json   루프가 모은 정보 원본 (replay 모드 자료)

specs/               STEP 1~5 명세 (여기서 13개에 답한다)
  06_DETOUR.md         STEP 6 처방 가지 추가 명세 (조건부 · 실행 뒤 · 결정 0개)
travel_graph/        그래프 코드
  state.py             ← STEP 1 · STEP 4 에서 바뀝니다
  nodes.py             ← STEP 5 에서 바뀝니다 (나머지는 킷 제공)
  edges.py             ← STEP 3 에서 바뀝니다
  build.py             배선. **킷 제공 — 고치지 않습니다**
  research.py page.py  수집·페이지 생성. **킷 제공**
  quality.py           정성 회차 절차 (해시 사슬·되돌아감 확인). **킷 제공**
  contract.py          계약·인계본 읽기 창구. **킷 제공**
  claude_cli.py        claude 실행 파일 찾기 (Windows shim 대응). **킷 제공**
  tracing.py           LangSmith 흔적. **킷 제공**
  detours/             ★ 규칙 처방 가지. **등록부 한 줄 = 가지 하나 = 노드 두 개**
    registry.py          등록부. 적힌 순서가 곧 진단 우선순위  ← STEP 6 에서 한 줄 추가
    encoding.py  image_dead.py  image_spec.py
                         킷 기본 처방 가지 3개 — 고치는 법(fix) · 실패 재현(inject). **킷 제공**
    __init__.py  log.py  _template.py
                         처방 가지 틀 · 실패 기록 · 새 모듈 틀. **킷 제공**
scripts/             킷 제공. 고치지 않는다 (CLAUDE.md 7절 보호 파일)
  detour_tests/        처방 가지 **시험지** — 진단도 합격도 이것으로 본다. 킷 것 3개는 보호.
                       STEP 6 에서 test_<내 가지>.py 하나만 만든다 (계약 검사기와 다르다)
  new_detour.py        새 처방 가지 세 조각(등록부 한 줄 · 모듈 · 시험지)을 만든다. STEP 6
  failure_report.py    실패 기록 보고서 — ③ · ③-2 에 후보가 있을 때만 STEP 6 을 한다
templates/           되물음·보고서 양식
settings/            환경 세팅 (SETUP.md 한 줄로 끝)
output/              결과물 (그래프가 만든다)
state/ evidence/     실행 기록
  evidence/failures/   실패 기록 <thread_id>.jsonl — 진단 · 시험 노드가 남긴다
langgraph.json       Studio 진입점
```

---

## 명령 정리

| 명령 | 언제 | 결과 |
| --- | --- | --- |
| `python scripts/check_graph_readiness.py` | 시작 전 · STEP 사이 | `READY`(0) / `ERROR`(1) / `NOT_READY`(2) |
| `python scripts/validate_specs.py --step N` | STEP 을 끝낼 때 | `PASS`(0) / `ERROR`(1) / `SHORT`(2) |
| `python scripts/check_graph_shape.py` | **STEP 3·4 뒤** · STEP 6 뒤 | 그래프 구조 **검사행 12개** (1~11 + 6b · 11 = 처방 가지 계약) |
| `python scripts/run_once.py --mode replay` | 빠르게 한 번 돌릴 때 | 터미널에서 게이트까지 (게이트에서 답을 입력. 답이 없으면 그 게이트에서 끝) · 끝에 history 줄 |
| `python scripts/run_once.py --mode replay --inject image_dead --auto stop` | 처방 가지 관찰 · 루프 A 확인 | 그 실패를 재현해 처방 가지 fix → test → 검사기 복귀를 본다 (쉼표로 여럿) · 게이트 A 에서 끝 |
| `python scripts/run_once.py --mode replay --inject image_spec --auto proceed` | 루프 B 확인 | 게이트 A 통과 → 게이트 B 에서 스스로 끝 (정성 3회로 들어가지 않는다). 루프 B 처방 가지의 재현 없는 오탐 확인은 `--inject` 를 빼고 이것으로 |
| `python scripts/failure_report.py` | 실행 뒤 — STEP 6 을 할지 정한다 | 실패 기록 보고서 (최근 실행). ③ · ③-2 에 후보가 있으면 끝 줄이 `다음: … STEP 6 진행해줘`, 없으면 `… STEP 6 은 하지 않아도 됩니다`. `--all` 은 이 킷의 실행 전부, `<폴더>…` 는 강사가 여러 교육생 것을 모을 때 |
| `python scripts/new_detour.py <이름> --loop A --title "…"` | STEP 6 | 처방 가지 세 조각 생성. 만든 직후에도 그래프는 그대로 돈다 |
| `python scripts/selftest/run_graph_regression.py` | **킷을 고쳤을 때** · STEP 6 회귀 (실습 본편 아님) | **240개** (T1~T16) 통과/실패 · replay · 약 10~15초 (처방 가지 하나에 +11) |
| `langgraph dev --no-reload --port 2024` | STEP 5 뒤 | Studio 에서 관찰 |
| `python scripts/check_information_count.py` | 루프 A 판정 | **루프 킷과 같은 파일** |
| `python scripts/check_page_contract.py` | 루프 B 판정 | **루프 킷과 같은 파일** |
| `python scripts/check_quality_passes.py` | 루프 C 판정 | **루프 킷과 같은 파일** |
| `python scripts/verify_all.py` | 최종 검증 | `SUCCESS`(0) / `ERROR`(1) / `SHORT`(2) |
| `python scripts/verify_all.py --skip-quality` | 정성 회차 안에서 | 되돌아감 확인 전용 |
| `python -m travel_graph.claude_cli` | **`live` 가 안 될 때** | claude 후보를 실제로 실행해 보고 채택 · 탈락 사유를 보여 준다 |

---

## 노드 22개 = 루프 골격 14 + 진단 2 + 처방 가지 6 · 라우터 6개 + fan-out 2개

그래프는 세 겹입니다. **루프 골격**(루프 킷의 작업이 옮겨 온 노드 14개)은 그대로 두고,
검사기 바로 뒤에 **진단** 노드를 세워, "정해진 고칠 법이 있는 문제"만 **규칙 처방 가지**로
보냅니다. 처방 가지는 고치고(fix · 처방) → 같은 시험지로 다시 재고(test · 재검) → 루프 골격의
검사기로 돌아옵니다. 나머지 부족은 재수집(LLM)이 맡습니다.

```text
          ┌── 루프 A 모은다 ──┐         ┌── 루프 B 만든다 ──┐         ┌─ 루프 C 다듬는다 ─┐
 START → 수집 → 검사 → ◇진단 A → ★게이트 A → 페이지 → 검사 → ◇진단 B → ★게이트 B → 정성 3회 → END
                  ▲       │                         ▲       │
                  └─▷가지──┘                         └─▷가지──┘
               (encoding · image_dead)              (image_spec)
                고치고 → 시험 → 복귀                  고치고 → 시험 → 복귀
```

처방 가지 하나는 **모두 같은 모양**입니다.

```text
 check_* ─▶ ◇diagnose_* ─┬─ (처방 가지 대상 없음) ────────────▶ 루프 골격 그대로
                         └─ <이름> ─▶ fix_<이름> ─▶ test_<이름> ─┬ 합격           → check_*   (검사기로 복귀 · 바퀴 안 씀)
                                                                ├ 불합격 · 한도 안 → fix_<이름> (한 번 더)
                                                                └ 불합격 · 한도 끝 → ★human_gate_* (사람)
```

<details>
<summary>전체 배선 (노드 22개) — <code>travel_graph/build.py</code> 배선도 그대로</summary>

```text
★ = 사람 · ◇ = 진단 · ▷ = 처방 가지

START → read_request → { collect_country , select_cities }        ← 정적 간선 2개 = 병렬
                        select_cities -Send-> collect_city × N     ← fan-out ① 고른 도시 전부
{ collect_country , collect_city × N } → check_information        ← fan-in
check_information → ◇diagnose_info
◇diagnose_info -route_after_info-> { ▷fix_<A 처방 가지> ,             ← 원인이 먼저
                                     repair_city × 다친 도시 ,      ← fan-out ② 지적된 것만
                                     repair_country × 0 또는 1 ,
                                     ★human_gate_a }
{ repair_city , repair_country } → check_information               ← 안쪽 루프 A
★human_gate_a -route_after_gate_a-> { repair_* , build_page , END } ← 바깥 루프 A
build_page → check_page → ◇diagnose_page
◇diagnose_page -route_after_page-> { ▷fix_<B 처방 가지> , build_page , ★human_gate_b }
★human_gate_b -route_after_gate_b-> { check_information , rebuilder ,
                                      quality_pass , END }         ← 바깥 루프 B
rebuilder → check_page
quality_pass → check_quality -route_after_quality-> { quality_pass , build_page ,
                                                     ★human_gate_b , END }  ← 고정 예산 순환

▷ 처방 가지 하나 (모두 같은 모양)
  fix_<이름> → test_<이름> -route_after_detour-> { back  → 그 루프의 검사기 (같은 자로 다시 잰다)
                                                  retry → fix_<이름>      (한 번 더)
                                                  gate  → 그 루프의 게이트 (사람에게) }
```

</details>

| 종류 | 노드 | 실행 주체 |
| --- | --- | --- |
| 루프 골격 | `read_request` · `check_information` · `check_page` · `check_quality` · `build_page` | 결정론 |
| 루프 골격 | `collect_country` · `select_cities` · `collect_city` · `repair_city` · `repair_country` | LLM |
| 루프 골격 | `quality_pass` · `rebuilder` | LLM+결정론 (고칠 곳은 LLM 이 지목, 고치기·해시·기록은 코드) |
| 루프 골격 | `human_gate_a` · `human_gate_b` | 사람 (게이트 B 는 두 번 선다) |
| 진단 | `diagnose_info` (루프 A) · `diagnose_page` (루프 B) | **결정론** — 판정 다음에 원인. 판정이 PASS 여도 돈다 |
| 처방 가지 | `fix_encoding` → `test_encoding` · `fix_image_dead` → `test_image_dead` · `fix_image_spec` → `test_image_spec` | **결정론 · LLM 호출 0** — 정해진 절차로 고치고, 같은 시험지로 다시 잰다 (image_dead 는 live 에서 주소를 실제로 열어 보고, 2회째에 Commons 를 검색한다 — LLM 이 아니다) |

**재수집(LLM)과 처방 가지는 실패를 맡는 두 길입니다.**

```text
                재수집(LLM) repair_*                 규칙 처방 가지 fix_* → test_*
원인            몰라도 받는다                        알아본 원인만
같은 입력이면   매번 다른 결과                       같은 결과 (결정론)
비용            토큰 · 바퀴를 쓴다                   LLM 호출 0 · 바퀴 안 씀
끝              바퀴 상한 3 → ★게이트                처방 한도 2 → ★게이트
```

킷 기본 가지 3개는 이렇게 자랐습니다 — encoding 은 원인과 고칠 법이 이미 알려진 실패 축(Windows cp949 ·
현지 글자 파일명)이라 로그 실측 전에 미리 만들었고, image_dead 는 루프 킷 실행 로그(모델이 해시 두 글자
`8/8c` 를 지어내 11장 전부 죽음 — 재수집(LLM)으로는 또 지어냄, 킷에 든 예시 인계본 `graph/04_RUN_EVIDENCE.md` 1-b)에서,
image_spec 은 실습생의 게이트 입력(원본 크기 사진이 서랍을 뚫음 — 검사기는 못 봄)에서 나왔습니다.
그 밖의 부족은 아직 재수집(LLM)에 둡니다 — 같은 실패가 로그에서 반복되고 고칠 법이 정해지면 가지로 뺍니다.

**라우터는 6개입니다.** STEP 3 에서 읽고 고치는 것은 넷 — `route_after_info` ·
`route_after_gate_a` · `route_after_page` · `route_after_gate_b`. 그 안의 처방 가지 분기와
게이트 B 의 정성 분기는 `킷 고정 ▼` 구간이고, 나머지 둘(`route_after_quality` ·
`route_after_detour`)은 킷 고정입니다. 라우터 규칙은 하나 — **원인을 먼저, 판정을 다음에,
상한은 탈출구로.** 판정(기준을 채웠나 — 검사기)과 원인(무엇이 터졌나 — 진단)은 다른 일이라
라우터가 둘을 나란히 읽습니다.

**루프 골격은 잠급니다.** 노드는 진단 노드에서만 갈라지는 처방 가지로만 늘리고
(`python scripts/new_detour.py`), 처방 가지는 수집 노드가 아니라 **그 루프의 검사기**로
돌아옵니다. 수집 노드로 돌아가면 합류가 `collect_city` 를 영영 기다립니다.
`check_graph_shape.py` 11번(처방 가지 계약)이 이 모양을 확인합니다.

**fan-out 이 두 번 나옵니다.** 첫 수집은 고른 도시를 전부, 재수집은 **지적된 도시만**.
손대지 않은 도시는 호출조차 되지 않습니다. 그래서 `cities` reducer 는 `operator.add` 가
아니라 이름으로 덮어쓰는 `merge_cities` 여야 합니다 — 되돌아오는 간선이 있는
그래프에서 reducer 는 멱등해야 합니다.

**루프 A·B 는 검사기가 통과할 때까지 도는 통과선 루프**이고,
**루프 C 는 정해진 3회를 채울 때까지 도는 고정 예산 루프**입니다.
닫는 것이 `verdict` 가 아니라 **카운터**라서 라우터 모양이 다릅니다.

**처방 가지는 넷째 순환입니다.** 진단 → fix → test → 검사기로 복귀하고, 불합격이면
fix ↔ test 를 처방 한도(`detour_limit` = 2)까지 되풀이한 뒤 그 루프의 게이트로 갑니다.
합격하고 돌아온 방문은 **바퀴(`loop_a_iter` · `loop_b_iter`)로 세지 않습니다** — 그래서
루프판과 "반복 횟수"를 같은 뜻으로 비교할 수 있습니다 (바퀴 상한 3 · 처방 한도 2). `replay` 에서
실패를 재현하지 않으면(`inject` 비움) 처방 가지는 한 번도 켜지지 않고, 진단 노드만 매번 켜집니다.
`live` 에서는 모델이 사진 주소를 지어내는 식의 **진짜 실패**가 나면 재현 없이도 켜질 수 있습니다 —
그것이 처방 가지를 둔 이유입니다.

---

## 실행 모드 두 가지

| 모드 | 어떻게 모으나 | 걸리는 시간 | 언제 |
| --- | --- | --- | --- |
| **`live`** (기본) | `claude -p` 로 실제 웹 조사 | 수집만 10~15분 | 실습 본편 |
| `replay` | `graph/research_data.json` 에서 잘라 씀 | 10초 | 구조 확인 · 네트워크가 막힌 곳 |

```bash
python scripts/run_once.py                  # live
python scripts/run_once.py --mode replay    # replay
python scripts/run_once.py --mode replay --inject image_dead --auto stop   # 그 실패를 재현해 처방 가지를 켠다
```

`run_once.py` 는 답이 없으면(`--auto` 답을 다 씀 · 표준입력이 터미널이 아님) **그 게이트에서 끝내고**,
끝에 `history — 검사기 · 진단 · 처방 가지 · 게이트 줄만` 을 그대로 보여 줍니다.
재현 없는 replay(`--auto proceed`)의 끝부분은 이렇습니다 — 진단은 매번 돌지만 가지는 켜지지 않습니다.

```text
 처방 가지   : 타지 않음   (실패 기록: evidence/failures/run-YYYYmmdd-HHMMSS.jsonl)
 history — 검사기 · 진단 · 처방 가지 · 게이트 줄만
   check_information: SHORT · 부족 9곳 · 1바퀴
   diagnose_info: 처방 가지 대상 없음 → 루프 골격 그대로
   check_information: PASS · 부족 0곳 · 2바퀴
   diagnose_info: 처방 가지 대상 없음 → 루프 골격 그대로
   human_gate_a: proceed
   check_page: PASS · 부족 0곳 · 1바퀴
   diagnose_page: 처방 가지 대상 없음 → 루프 골격 그대로
```

**실패 재현(`inject`)** 은 이미 있는 가지가 켜지는 것을 보거나, STEP 6 에서 새 가지의 시험지
빨간불을 먼저 볼 때 그 실패를 다시 일으키는 장치입니다. Studio 에서는 입력 칸에
`{"inject": ["image_dead"]}` 를 넣는 것과 같습니다. 평소에는 비워 둡니다.

`live` 로 시작했는데 `claude` 가 없거나 시간을 초과하면 **조용히 죽지 않고**
`replay` 로 내려간 뒤 그 사실을 `history` 에 남깁니다.

### 지금 도는 것이 정말 `live` 인가

수집 노드는 **실제 웹조회 횟수**를 `history` 꼬리표에 적습니다. 이것 말고는
`live` 와 폴백을 화면에서 구분할 방법이 없습니다 (둘 다 정상으로 보입니다).

```text
collect_city[하노이]: 명소 3곳 · 실검색 9회 · 일정 5일 · 실검색 4회      진짜 live
collect_country: live 로 10칸 수집 · (!) 실검색 0회 — 기억으로…         조사를 안 함
collect_city[하노이]: 명소 실패(권한이 막혀 WebSearch …) → replay 폴백   막힘. live 아님
collect_city[후에]: 명소 수집 실패 → 대체할 자료도 없음                  인계본에 없는 도시
```

실행 전에 한 번 재어 두면 당일에 헤매지 않습니다.

```bash
python settings/scripts/verify_env.py        # C12 = live 웹검색 실측
```

### 트레이스에서 `claude -p` 안쪽 보기

LangSmith 트레이스는 노드만 보여 주는 것이 아니라 **그 안에서 무엇을 물었고 무엇을
검색했는지**까지 보여 줍니다. `travel_graph/tracing.py` 가 만듭니다 (패키지 추가 없음).

```text
collect_city                        (chain)
├ claude -p · collect_city[하노이] 명소   (llm)     프롬프트 전문 · 최종 JSON · 토큰 · 비용
│ ├ 1 WebSearch                     (tool)    질의어 → 검색 결과
│ └ JSON 블록 추출                   (parser)  마지막 텍스트 → dict
└ claude -p · collect_city[하노이] 일정   (llm)     (같은 모양 — 도시 수집은 claude -p 를 두 번 부른다)
```

턴이 도착하는 대로 자식이 열리므로 **진행되는 것이 실시간으로 보입니다.**
run 수를 아끼고 싶으면 `GRAPH_TRACE_TOOLS=0`, 통째로 끄려면 `GRAPH_TRACE_CLAUDE=0`.

> 트레이스는 `langgraph dev`(Studio) 실행에서 남습니다 — `run_once.py` 는 `.env` 를 읽지 않아
> 터미널 실행은 트레이스가 없습니다. 게이트(`interrupt`)에서 멈추면 트레이스가 나뉘므로
> 한 실행은 LangSmith **Threads** 탭에서 `thread_id` 로 이어 봅니다.

> **시간이 촉박하면 `GRAPH_MODE=replay` 로 켜십시오.** 결과가 항상 같아서
> 게이트 실습과 Studio 관찰에 시간을 온전히 쓸 수 있습니다.

---

## 루프 킷에서 그대로 가져온 것

```text
scripts/check_information_count.py    바이트 단위로 같음
scripts/check_page_contract.py        바이트 단위로 같음
scripts/check_quality_passes.py       바이트 단위로 같음
specs/QUALITY_RUBRIC.md               정성 규율 10가지 그대로 (§6 되돌리기 단위만 그래프판은 fix 한 건 — GRAPH_CONTRACT.md 4-b)
                                      바이트 단위로 같은 복사본이라 머리말의 `MASTER_SPEC.md` · `02_PAGE_DESIGN` 링크는
                                      루프 킷 기준이다 — 그래프 킷에서는 `graph/03_CONTRACT.json` 의 `quality_contract` 를 본다
templates/QUALITY_PASS.md             회차 기록 양식 그대로 (그래프판 기록에는 skipped_fix 칸 하나가 더 붙는다 — GRAPH_CONTRACT 4-b)
graph/03_CONTRACT.json                루프에서 정한 숫자 그대로
```

**계약을 그래프용으로 '개선'하지 마세요.** 두 판을 같은 표에 못 올리게 됩니다.
`scripts/_contract.py` 만 다릅니다 — 계약을 읽는 위치(`MASTER_SPEC.md` → `graph/03_CONTRACT.json`), 그리고 `asset_problems` 가 죽은 이미지의 사유(status/에러)를 한 줄로 먼저 돌려주는 점입니다. 그래서 부족 줄 수는 다를 수 있습니다 — 열어 봤는데 실패한 이미지 한 장이 루프 킷에서는 대개 2줄, 그래프 킷에서는 원인 1줄이고, `error` 가 있는데 status 가 허용값인 기록은 그래프 킷에서만 부족입니다 (`scripts/_contract.py` 머리말).

---

## 자주 하는 실수

| 실수 | 왜 나쁜가 |
| --- | --- |
| `03_CONTRACT.json` 을 고쳐 통과시키기 | 채점표를 고치면 시험이 무의미하다 |
| `compile(checkpointer=...)` 를 Studio 에서 쓰기 | Agent Server 것과 싸운다 |
| 정적 간선 2개를 if/else 로 착각 | 둘 다 실행된다 |
| reducer 를 미리 붙여 두기 | 왜 필요한지 몸으로 못 겪는다 |
| 라우터에서 자유 문장 보기 | 제어 흐름이 문장 해석에 좌우된다 |
| **회차 카운터에 reducer 붙이기** | 2회차에 1+2=3 이 되어 한 회차를 건너뛰고 나간다 (정성 2회만 돈다). 카운터는 덮어쓰기다 |
| **정성 3회를 정적 간선 3개로** | 병렬이 되어 해시 사슬이 끊긴다. 순환 하나로 돈다 |
| 못 채운 칸을 조용히 넘기기 | 가장 나쁜 실패다. 보고서에 반드시 적는다 |
| **처방 가지를 수집 노드로 되돌리기** | 합류가 `collect_city` 를 영영 기다린다. 예외 없이 조용히 멈춘다. 처방 가지는 **그 루프의 검사기**로 돌아온다 |
| **시험지를 약하게 만들어 통과** | 채점표를 고치는 것과 같다. 진단도 합격도 같은 시험지라, 문제가 사라지는 게 아니라 **안 보이게** 될 뿐이다 |
| **루프 골격(또는 진단)에 노드 추가** | 루프 골격 14 · 진단 2 는 잠겨 있다. 노드는 처방 가지로만 늘린다 (`new_detour.py`). `check_graph_shape.py` 11번이 ERROR 를 낸다 |
| 처방 가지가 판정 · 바퀴 · 게이트 칸을 쓰기 | 판정은 검사기가, 바퀴는 루프 골격이, 게이트는 사람이 쓴다. 처방 가지가 덮으면 판정 독립과 루프판 비교가 깨진다. 11번이 잡는다 |
| 후보가 없는데 STEP 6 하기 | 가지를 만들려고 없는 실패를 찾게 된다. 보고서 ③ · ③-2 가 비면 STEP 6 은 하지 않는다 |

---

## 루프판과 무엇이 달라지나

| | 루프판 | 그래프판 |
| --- | --- | --- |
| 도시 3개 수집 | 순서대로 | **나란히** |
| 실패 후 재실행 범위 | 바퀴 전체 | **노드 단위** |
| 되물음 | 터미널에서 답한다 | **그래프가 멈춘다** (`interrupt`) |
| 페이지에서 수집으로 되돌리기 | 불가능 | **간선 하나** (`human_gate_b → check_information`) |
| 부분 재수집 | 전부 다시 | **지적된 도시만** (`fan_out_repairs` Send) |
| 사람의 지시로 결과물 수정 | 없음 | `rebuilder` 노드 (게이트 B 의 `note` 를 소비) |
| 구조가 눈에 보이나 | 아니오 | **Studio 화면** |
| 정성 3회 | 사람이 손으로 기록 | **노드가 돌고 해시로 증명** |
| 검사기 | 같음 (3개) | **같음 (3개)** |
| 못 채운 칸 | 0건 | **0건** |
| 계약 밖 아쉬움 | 1건 | 검사기가 세지 않는다 — 보고서에 적는다 |
| 실패를 다루는 법 | 모두 "한 바퀴 더" | **원인마다 다른 가지** (진단 → 처방 가지) — 그림으로 보인다 |
| 실패 라우팅 7종 | 문서(고정표)로만 있다 | **일부가 실제 배선** (`failure_kind` = 처방 가지 이름) · 등록부 한 줄로 같은 모양을 늘린다 (`new_detour.py`) |
| 반복되는 실패 | 매번 "한 바퀴 더"(LLM) | **로그를 따라 규칙 처방 가지로** — 새 실패가 로그에 반복되면 STEP 6 에서 가지를 더한다 |
| 같은 실패 다시 보기 | 같은 실패가 다시 나야 본다 | **실패 재현** (`inject`) — 그 실패를 다시 일으켜 같은 길을 다시 탄다 |

**"못 채운 칸이 같다"가 중요합니다.** 그래프로 옮긴다고 인터넷에 없는 사진이 생기지 않습니다.
그래프가 개선하는 것은 **실행 효율과 복구 능력**입니다.

**복구 능력의 실체가 처방 가지입니다.** 다만 처방 가지가 들어와도 비교는 같은 뜻으로 남도록 만들었습니다.

```text
반복 횟수     처방 가지는 바퀴로 세지 않는다 → 루프판과 같은 뜻으로 비교된다
사람 호출     재현 없는 기본 실행에서는 3번 (게이트 A 1 · B 2) — 루프판 2 에 정성 뒤 확정이 하나 더.
              처방 가지가 처방 한도를 다 쓰면 그 루프의 게이트에 한 번 더 설 수 있다 — 그때는 적는다
못 채운 칸    "인터넷에 없는 정보"는 그대로다. 다만 **주소가 틀려서** 못 채운 칸(image_dead)은
              처방 가지가 정해진 절차로 줄일 수 있다 — 이것이 복구 능력이다. 없던 사진이 생기는 게 아니다
정성 3회      빨라지지 않는다
```
