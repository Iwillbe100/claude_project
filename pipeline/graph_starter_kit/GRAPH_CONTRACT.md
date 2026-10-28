# GRAPH_CONTRACT.md — 그래프 실행 절차

**STEP 5까지 끝난 뒤에 여는 문서입니다.** 루프 킷의 `LOOP_CONTRACT.md` 에 대응합니다.
실행을 본 뒤 로그에 후보가 있을 때만 하는 **STEP 6(처방 가지 추가 · 조건부)** 은 11절에 있습니다.

---

## 0. 실행 전 확인

```bash
python scripts/check_graph_readiness.py      # READY (exit 0) 여야 합니다
python scripts/check_graph_shape.py          # PASS  (exit 0) 여야 합니다 · 검사행 12개
```

`NOT_READY` 면 아직 STEP 이 남았습니다. `ERROR` 면 구조가 깨졌습니다.

구조 검사는 **12행**(1~11 + 6b)입니다. 11번 **처방 가지 계약**은 규칙 처방 가지(fix → test)가 진단에서만
갈라지고 그 루프의 검사기로 돌아오는지 봅니다 — STEP 6 에서 가지를 더한 뒤에도 PASS 여야 합니다.
준비도(`check_graph_readiness.py`)는 STEP 1~5 만 봅니다. STEP 6 은 실행 **뒤**의 일이라
READY 조건이 아닙니다.

---

## 1. Studio 켜기

```bash
langgraph dev --no-reload --port 2024
```

| 옵션 | 왜 |
| --- | --- |
| `--no-reload` | **필수.** 감시 기능이 켜져 있으면 실행 중 `.py` 가 바뀔 때(코드 수정 · STEP 6 의 `new_detour.py` 가 파일을 만들 때) 서버가 다시 떠 **돌던 run 이 끊깁니다.** 감시는 `*.py` 만 보므로 `output/` 의 json · html 쓰기로는 재시작하지 않습니다. 그 대신 새 코드는 서버를 직접 다시 켜야 반영됩니다 |
| `--port 2024` | 기본값. 이미 쓰고 있으면 다른 번호로 |
| `--no-browser` | 브라우저를 자동으로 안 여는 옵션 |

브라우저가 열리지 않으면 터미널에 찍힌 주소를 직접 엽니다. 서버 로그(오류가 나면 Traceback)는 이
터미널에 찍힙니다 — 파일로 남기려면 `graph-run` 스킬의 백그라운드 기동 명령(`evidence\langgraph_dev.*.log`)을 씁니다.

```text
Studio      https://smith.langchain.com/studio?baseUrl=http://127.0.0.1:2024
API         http://127.0.0.1:2024
```

> **왜 로컬 서버인데 smith.langchain.com 주소인가** — 화면(Studio)만 웹에서 오고,
> 그래프는 내 컴퓨터에서 돕니다. `.env` 의 `LANGSMITH_API_KEY` 는 화면 인증과
> 트레이스 전송에 쓰입니다.

---

## 2. 입력 넣고 제출

왼쪽 그래프 그림에서 노드 22개가 보입니다 — **루프 골격 14 + 진단 2 + 처방 가지 6**.
루프 골격이 가운데 줄이고, 검사기 바로 뒤의 `diagnose_info` · `diagnose_page` 에서
`fix_*` → `test_*` 처방 가지 셋이 갈라져 나갑니다.

오른쪽 입력 폼에 **5칸**만 나옵니다 (`country` `days` `style` `city_priority` `inject`).
상태 전체가 아니라 `TravelInput` 만 그려지기 때문입니다. **`inject` 는 평소 비웁니다** —
처방 가지가 켜지는 것을 보거나 STEP 6 에서 새 가지의 빨간불을 먼저 볼 때, 그 실패를
재현하려고만 씁니다 (아래).

### 가장 쉬운 방법 — 빈 입력

```json
{}
```

`read_request` 가 `graph/03_CONTRACT.json` 의 값으로 채웁니다.

### 내 값으로 하고 싶으면

`graph/05_STATE_SEED.json` 에서 아래 네 칸만 복사해 붙여 넣습니다 (인계본의 `inject` 는 평소
`[]` 입니다 — 복사하지도 바꾸지도 않아도 됩니다).

```json
{
  "country": "베트남",
  "days": 5,
  "style": {"preferred": ["역사", "건축"], "not_preferred": ["시끄러운 곳"], "detailed": []},
  "city_priority": ["역사 유적 밀도", "도보 접근성"]
}
```

### 실패 재현(inject) — 처방 가지가 켜지는 것을 볼 때

```json
{"inject": ["image_dead"]}
```

다른 칸은 비워도 됩니다. 수집 직후 첫 도시(또는 국가 소개)에서 그 실패를 다시 일으키고,
진단 노드가 찾아 처방 가지로 보냅니다. 실패 재현(inject)은 이미 있는 가지가 켜지는 것을 보거나,
STEP 6 에서 새 가지의 시험지 빨간불을 먼저 볼 때 그 실패를 다시 일으키는 장치입니다.
고를 수 있는 이름은 `travel_graph/detours/registry.py` 에 있습니다
(`encoding` · `image_dead` · `image_spec`, 여럿이면 목록에 나란히). `replay` 에서 쓰는 것을 권합니다.
터미널에서는 같은 일을 이렇게 합니다.

```bash
python scripts/run_once.py --mode replay --inject image_dead --auto stop      # 루프 A 처방 가지 — 게이트 A 에서 끝
python scripts/run_once.py --mode replay --inject image_spec --auto proceed   # 루프 B 처방 가지 — 게이트 B 에서 스스로 끝
```

`run_once.py` 는 **답이 없으면 그 게이트에서 끝냅니다** (`--auto` 답을 다 씀 · 표준입력이 터미널이
아님 · 입력 EOF) — 권장값으로 넘어가 정성 3회(`claude -p`)로 들어가지 않습니다. 끝에
`history — 검사기 · 진단 · 처방 가지 · 게이트 줄만` 을 그대로 출력합니다.

> `replay` 에서 재현(inject)이 없으면 처방 가지는 **한 번도 켜지지 않습니다** (루프 골격 그대로).
> `live` 에서는 진짜 실패(예: 모델이 지어낸 사진 주소)로 켜질 수 있습니다 — 그것이 가지의 본래 일입니다.
> 모르는 이름은 버리고 `read_request` 의 history 에 *"모르는 inject 이름을 버렸습니다"* 가 남습니다.

**Submit** 을 누릅니다.

---

## 3. 실시간으로 볼 것

```text
① 노드가 순서대로 점등된다
     read_request → collect_country · select_cities 가 **동시에** 켜진다
     → collect_city 3개가 **동시에** 켜진다     ← 병렬. 루프에는 없던 그림
       (collect_city 는 select_cities 만이 아니라 같은 걸음의 collect_country 가 끝나야 시작한다)

② 각 노드의 입력/출력이 오른쪽에 쌓인다
     collect_city 를 눌러 보면 "cities: [1개]" 만 돌려준 것이 보인다
     → 상태 전체가 아니라 **변경분**만 돌려준다는 게 눈에 보인다

③ check_information → diagnose_info 뒤에서 길 하나가 골라진다
     failure_kind(원인)와 info_verdict(판정)에 따라 처방 가지 · 재수집(LLM) · human_gate_a 중 하나로 간다
     SHORT 이면 **지적된 도시 수만큼** repair_city 가 갈라지고,
     국가 소개가 다쳤으면 repair_country 1개가 **함께** 간다 (두 번째 fan-out)
     → 라우터가 상태 값을 읽고 고른 결과
     → 다음 check_information 은 재수집 갈래가 **모두** 끝난 뒤 한 번 켜진다 (한 걸음 = superstep)
       live 에서 가장 느린 갈래(보통 2~6분)를 기다리는 동안 패널에 안 보이는 것이 정상 (10절)

④ quality_pass 가 **겹치지 않고 차례로** 세 번 켜진다   (4-b 절)
     그 사이마다 check_quality 가 켜진다     ← 고정 예산 순환. 순차가 정상

⑤ ★ 게이트에서 멈춘다   (4 절)
     human_gate_a 한 번 · human_gate_b 두 번 — 같은 5키 화면

⑥ 검사기 뒤에 **진단 노드가 매번** 켜진다
     check_information → diagnose_info · check_page → diagnose_page
     → 판정(기준을 채웠나) 다음에 원인(무엇이 터졌나). 판정이 PASS 여도 돈다
     → replay 에서 재현이 없으면 history 에 "diagnose_info: 처방 가지 대상 없음 → 루프 골격 그대로" 가 찍힌다

⑦ 그 실패가 나면(또는 재현하면) 처방 가지 fix → test 가 켜지고 **검사기로 돌아온다**
     예) {"inject": ["image_dead"]} → diagnose_info → fix_image_dead → test_image_dead
         → check_information   ← 수집 노드가 아니라 **그 루프의 검사기**로 복귀
     history 에 "(처방 가지에서 복귀 — 바퀴를 쓰지 않음)" 이 찍힌다
     시험에 떨어지면 같은 fix 로 한 번 더, 처방 한도(2)를 다 쓰면 그 루프의 게이트로 간다
```

---

## 4. ★ 게이트에서 멈춤 — 여기가 이 실습의 본편

`human_gate_a` 에서 그래프가 **멈춥니다.** Studio 에 이렇게 뜹니다.

**세 정지 지점이 같은 5키 화면을 씁니다.** 키 순서가 곧 읽는 순서입니다.

```text
① 지금    루프 A(정보량) · SHORT · 2/3바퀴 · 못 채운 칸 40곳 · 같은 오류 반복 0/2
② 왜      [{원인: 이미지 주소가 죽어 있음, 몇 곳: 27 / 40,
            고치려면: 정보가 없어서가 아니라 주소가 틀려서입니다 …}]
③ 권장    more — 부족의 대부분이 이미지 주소 한 종류입니다 …
④ 고르기  more     지적된 것만 다시 모읍니다 · 도시: 다낭 — 지적이 없는 곳은 호출조차 하지 않습니다
          proceed  부족해도 페이지를 만듭니다 (못 채운 칸은 보고서에 남습니다)
          stop     여기서 멈춥니다 (END)
⑤ 답      {"action": "more | proceed | stop", "note": "이미지는 영문 파일명을 우선 쓰고 Commons 에서 실제로 확인한 것만 써라. 확인 못 한 칸은 아예 건드리지 마라"}
```

**`② 왜` 가 목록이 아니라 요약인 것이 핵심입니다.** 부족 40곳이 실제로는 서너
종류에서 나옵니다. 원본 목록을 함께 주면 요약을 읽지 않으므로 주지 않습니다 —
원본이 필요하면 `research_path` 가 가리키는 파일을 엽니다.

**수집이 실패한 도시는 `② 왜` 에 따로 뜹니다.** 부족(`관광지 수 3/0`)과
실패(그 도시를 아예 못 모음)는 판단이 완전히 다르기 때문입니다.

**처방 가지가 못 고친 것은 `② 왜` 맨 앞에 뜹니다** — `처방 가지가 못 고침 — <title>` 줄 (`title` = 등록부의 가지 제목).
처방 가지는 정해진 절차로 고칠 수 있는 문제만 맡아, 처방 한도(`detour_limit` = 2)까지 fix → test 를
되풀이합니다. 그래도 불합격이면 **그 루프의 게이트**로 옵니다. 그래서 실패를 재현했거나
처방 가지가 한도를 다 쓴 실행에서는 기본 3번(A · B · C) 말고 게이트에 한 번 더 설 수 있습니다.
그 줄의 `고치려면` 에는 그 가지의 안내가, `예` 에는 시험지가 남긴 증상 한 줄이 붙습니다.
처방 가지 줄은 세 종류입니다.

```text
처방 가지가 못 고침 — <title>                 한도를 다 썼거나 시험에 떨어짐 (몇 곳 = 증상 수)
처방 가지 시험지가 깨짐 — <title>             교육생 시험지가 실행 중에 멈춤 — 증상이 아닙니다.
                                              시험지를 혼자 돌려 오류 줄을 고칩니다 (STEP 6)
처방 가지를 미룸 — <title> (정성 회차 중)     파일 해시 사슬을 지키려고 미룸. research · rebuild 면 다시 섭니다
```

`③ 권장` 은 이때도 계산이고, **처방 가지 줄의 종류에 맞춰** 냅니다 — 한 가지의 이유를 다른
가지에 붙이지 않습니다. 부족이 남았으면 `more`, 검사기가 세지 않는 종류만 남았으면
`proceed`(게이트 A) · `done`(게이트 B, "'고치려면' 칸을 따르십시오"). 교육생의 `fix()` ·
`inject()` 가 예외를 내도 그래프는 죽지 않습니다 — 못 고침 · *"(재현하지 못함)"* 으로 history 에 남습니다.

> **사람이 `more`(게이트 A) · `research` · `rebuild`(게이트 B) 를 고르면 처방 한도가
> 새로 채워집니다.** 바깥 루프는 사람이 소유하므로, 사람이 "한 번 더"를 고른 뒤에는
> 처방 가지도 다시 설 수 있습니다 (history 에 *"human_gate_a: 처방 한도를 새로 채웁니다"* ·
> *"human_gate_b: 처방 한도를 새로 채웁니다"* 가 남습니다).
> `proceed` · `done` 은 한도를 그대로 둡니다.

### 답하는 법

Studio 의 resume 입력칸에 **JSON** 으로 넣습니다.

```json
{"action": "proceed", "note": "사진은 없어도 진행합니다"}
```

| 칸 | 쓰임 |
| --- | --- |
| `action` | **라우팅에 쓰인다.** 비우고 `note` 에만 지시문을 적으면(허용값이 아닌 말도 지시문으로 읽는다) **첫 허용값**(게이트 A `more` · 게이트 B `research`) — 방향을 적었다는 것은 더 돌리겠다는 뜻이다. **다른 게이트의 낱말**(예: 게이트 B 에 `stop`)은 기본값(`proceed` · `done`)으로 가고 history 에 *"이 게이트의 답이 아닙니다"* 가 남는다. 둘 다 비우면 기본값 (`nodes._decide_gate`) |
| `note` | 자유 문장. **라우팅에 쓰이지 않는다.** 기록과 다음 프롬프트에만 |

> 문자열 `proceed` 만 넣어도 됩니다. `normalize_gate` 가 흡수합니다.

### 게이트 B는 선택지가 다르고, **두 번 섭니다**

```json
{"action": "done", "note": "브라우저로 확인했습니다"}
```

| 고르면 | 어디로 |
| --- | --- |
| `research` | **정보 수집까지 되돌아간다** (`check_information` → 다시 세고 다친 도시만) ← 루프에서는 불가능했던 경로 |
| `rebuild` | `rebuilder` 가 **`note` 에 적은 지시대로** 결과물을 고친다 |
| `done` | 정성 회차가 **3회 미만이면 루프 C 시작**, **3회면 확정하고 끝** |

> `rebuild` 를 고를 때는 `note` 를 **반드시 적습니다.** 그 문장이 곧 수정 지시입니다.
> `rebuilder` 는 HTML 을 직접 고치지 않고 `output/research_data.json` 을 고쳐
> 화면을 다시 만듭니다 — HTML 만 손대면 `build_page` 가 다시 도는 순간 날아갑니다.
> 계약을 낮추라는 지시(글자 수 기준을 낮춰라 등)는 거부합니다.

무엇을 묻고 있는지는 화면 `① 지금` 줄의 `정성 N/3회` 로 구분합니다.

```text
① 지금  루프 B(페이지) · PASS · 1/3바퀴 · 정성 0/3회 · 못 채운 칸 0곳     ← 지금 done 을 고르면 정성 점검이 시작된다
① 지금  정성 3회 완료 · … · 정성 3/3회 · …                               ← 지금 done 을 고르면 끝난다
```

> `research` 나 `rebuild` 를 고르면 결과물이 다시 만들어져 정성 회차가 디스크에
> 남긴 수정이 사라집니다. 그래서 그때 **회차가 0으로 되돌아갑니다.**
> 정성은 처음부터 다시 3회입니다.

---

## 4-b. 루프 C — 정성 점검 3회 (사람이 답할 것이 없습니다)

게이트 B에서 `done` 을 고르면 `quality_pass` → `check_quality` 순환이 **세 번** 돕니다.

```text
회차 1  내용이 실한가          Q-반복금지 · Q-취향연결 · Q-뺀이유 · Q-상세삼요소
회차 2  실행 가능하고 사실인가   Q-일정현실성 · Q-근거일치 · Q-도시차별화 · Q-실용누락
회차 3  독자 관점에서 완결인가   Q-동행반영 · Q-계약무결
```

**회차마다 규율 10개를 전부 판정하되, 고치는 우선순위(렌즈)만 다릅니다.**
같은 렌즈로 세 번 보면 2회차부터 "이상 없음"만 나오기 때문입니다.

**위반이라 적고 그 규율의 fix 가 없으면 같은 회차 안에서 한 번 더 묻습니다** (`quality.judge_followup`).
판정자는 그 규율의 fix 를 내거나, 다시 보니 위반이 아니면 OK 와 이유를 적습니다(처음 판정은 note 에 남습니다).
보완은 한 번뿐이라, 그래도 남으면 판정기가 SHORT 를 내고 게이트 C 의 `③ 권장` 이 `rebuild` 를 권합니다 —
`done` 을 고르면 `verify_all` 이 SHORT(exit 2)인 채로 끝납니다. live 리허설에서 판정자가 위반을 적고
fix 를 다른 규율 이름으로만 낸 일이 실제로 있었습니다.

Studio 에서 볼 것:

```text
quality_pass 가 세 번 켜진다          ← 병렬이 아니라 **순차**다
그 사이마다 check_quality 가 켜진다    ← 회차 카운터를 읽고 다시 보낸다
history 에 회차별 위반/수정 건수가 쌓인다
```

한 회차는 `claude -p` 판정 + 수정 + 되돌아감 확인까지 **2~4분** 걸립니다.
세 회차면 **6~12분**입니다. `replay` 모드에서도 정성 판정만은 실제로 수행합니다 —
모의로 통과시키면 "고친 척"을 자동화하는 셈이 되기 때문입니다.

기록은 `evidence/runs/<run_id>/quality/pass1~3.json` 에 남습니다.

```text
snapshot_before / snapshot_after   파일 해시. 고쳤다면 반드시 바뀌어야 한다
rules                              규율 10개 전부의 판정
applied_fix                        실제로 고친 것
skipped_fix                        고치려 했으나 적용 못 한 것 ★ 조용히 넘기지 않는다 (그래프판에만 있는 추가 칸 — templates/QUALITY_PASS.md 양식에는 없고 판정기도 보지 않는다)
verify_after                       verify_all --skip-quality 의 종료 코드
```

> **그래프판의 되돌리기 단위는 fix 한 건입니다.** `quality.py` 가 fix 를 하나 넣을 때마다 `verify_all.py --skip-quality` 를 돌리고, exit 0 이 아니면 **그 한 건만** 되돌립니다. 나머지 수정은 남습니다. 같은 회차 안에서 다시 고치지 않고, 이유를 `skipped_fix` 에 "이 수정이 정량 계약을 깨뜨려 되돌렸습니다 (재검증 exit N)"로 남긴 뒤 다음 회차로 넘어갑니다. 회차 끝 재검증까지 실패할 때만 회차 전체를 되돌립니다. `specs/QUALITY_RUBRIC.md` §6의 '그 회차의 수정을 되돌립니다'는 루프판(사람/Claude가 손으로 도는 판) 기준입니다.

---

## 5. 멈춘 그래프를 나중에 이어서 돌리기

Studio 왼쪽의 **스레드 목록**에서 그 스레드를 다시 엽니다.
`thread_id` 하나가 "한 번의 실행"입니다. 어제 게이트에서 멈춘 것을 오늘 이어서 돌 수 있습니다.

```text
같은 thread_id 로 다시 부른다   →  멈춘 자리에서 이어진다
새 thread_id 로 부른다          →  처음부터 돈다
```

**노드 단위로 되감기(fork)도 됩니다.** 어떤 노드의 상태를 눌러 "Fork" 하면
그 지점부터 다른 값으로 다시 돌릴 수 있습니다. 루프에서는 바퀴 전체를 다시 돌아야 했습니다.

**처방 가지도 fork 로 다시 태웁니다.** 진단 노드(`diagnose_info` · `diagnose_page`)의 상태에서
Fork 하면 수집부터 다시 돌지 않고 **그 자리부터** 처방 가지(fix → test → 검사기 복귀)를
다시 볼 수 있습니다. 라우터가 읽는 원인 칸은 `failure_kind` 하나라서, 이 값을 비워 Fork 하면
같은 자리에서 가지 없이 루프 골격으로 가는 길과 나란히 비교할 수도 있습니다.
실패 재현(2절)이 "같은 실패를 처음부터 다시 일으키기"라면, fork 는 "같은 갈림길에 다시 서기"입니다.

---

## 6. 끝나면 — 같은 자로 잰다

```bash
python scripts/verify_all.py
```

```text
[구조]   check_graph_shape.py        그래프 킷 신규 · 검사행 12개 (11 = 처방 가지 계약)
[정보량] check_information_count.py  루프 킷과 동일
[페이지] check_page_contract.py      루프 킷과 동일
[정성]   check_quality_passes.py     루프 킷과 동일 · 3회 절차
최종: SUCCESS  (exit 0)
```

> **처방 가지 시험지(`scripts/detour_tests/`)는 `verify_all` 에 없습니다.** 같은 자로 재는
> 비교를 지키려고 일부러 뺐습니다. 최종 판정은 루프 킷과 같은 계약 검사기가 하고,
> 처방 가지 시험지는 "그 문제가 사라졌나"만 봅니다 — 진단 노드와 시험 노드가 그래프 **안에서**
> 쓰는 도구입니다. 처방 가지가 합격해도 검사기로 돌아가 **같은 검사기가 다시 잽니다** (판정 독립).

`[정성]` 이 `SHORT` 로 나오는 흔한 경우가 세 가지 있습니다. 구분해서 보고합니다.

```text
"N회차 기록이 아직 없습니다"          아직 덜 돌았다. 그래프를 더 돌리면 된다
                                     (단 evidence/runs/*/quality/blocked.json 이 있으면 판정 자체를 못 한 것 — 그 reason 부터 본다. 대개 claude 를 부를 수 없음)
"위반이라 적고 고치지 않았습니다"       판정은 했는데 수정이 적용되지 않았다
                                     → passN.json 의 skipped_fix 에 이유가 있다
"정성 3회 동안 고친 것이 0건입니다"     3회 모두 OK 라 고친 것이 없다. 흠이 없는 것과 보지 않은 것을
                                     판정기가 구분하지 못한다 → 사람이 게이트 C 에서 확인한다
                                     (rebuild — 정성은 처음부터 다시 3회 / done — 이대로 확정)
```

결과물은 `output/travel_site.html` 파일 하나입니다. 브라우저로 열어 확인합니다.

---

## 7. 루프판과 비교 — 이 실습의 결론

루프판 기준선은 아래 표 왼쪽 칸입니다 — `graph/04_RUN_EVIDENCE.md` 의 **「루프판 기준선」 절**에서
옵니다. 아래 숫자는 킷에 든 **예시 인계본**(6번)의 것입니다. 루프 킷의 `export_graph_handoff.py` 로
**내 인계본을 뽑아 덮어썼다면** 같은 이름의 절이 8번에 있으니 그 숫자로 바꿔 적습니다. 칸에
`(기록 없음 …)` 이 적혀 있으면 루프를 돌린 내 기록에서 옮깁니다. 옆에 놓고 채웁니다.

| | 루프판 | 그래프판 (내 실행) |
| --- | --- | --- |
| 반복 횟수 | 8 (A 3 · B 2 · C 3) | |
| 전체 시간 | 약 40분 | |
| 실패 후 재실행 범위 | 바퀴 전체 | |
| 사람 호출 횟수 | 2 | |
| 정성 회차 | 3 / 3 | |
| `verify_all` | exit 0 | |
| 못 채운 칸 | 0건 | |
| 계약 밖 아쉬움 | 1건 | |

**"못 채운 칸이 같다"가 나오면 제대로 된 것입니다.**
그래프가 개선하는 것은 실행 효율과 복구 능력이지, 인터넷에 없는 정보의 존재 여부가 아닙니다.

**처방 가지가 들어와도 이 표는 같은 뜻으로 비교됩니다.** 그렇게 되도록 만들었습니다.

```text
반복 횟수     처방 가지는 바퀴로 세지 않는다. 합격하고 돌아온 방문은 history 에
              "(처방 가지에서 복귀 — 바퀴를 쓰지 않음)" 이 찍힌다 → 루프판과 같은 뜻.
              처방 가지를 탄 횟수는 history 의 fix_* 줄 · 실패 기록으로 따로 본다
              (run_once.py 는 끝에 "처방 가지 : …" 한 줄로 요약하고, history 줄도 그대로 보여 준다)
사람 호출     재현 없는 기본 실행에서는 3번 (게이트 A 1 · B 2) — 루프판 2 에 정성 뒤 확정이 하나 더.
              처방 가지가 한도를 다 쓰면 그 루프의 게이트에 한 번 더 설 수 있다 — 그때는 늘어난 대로 적는다
못 채운 칸    "인터넷에 없는 정보"는 그대로다. 다만 **주소가 틀려서** 못 채운 칸(image_dead)은
              처방 가지가 정해진 절차로 줄일 수 있다 — 이것이 그래프의 "복구 능력"이다.
              없던 사진이 생기는 게 아니다
정성 3회      빨라지지 않는다
```

> 이 표는 **실패를 재현하지 않은 실행**으로 채웁니다. 재현(inject) 실행은 일부러 다시 일으킨
> 실패라 루프판과 같은 조건이 아닙니다.

---

## 8. LangSmith 에서 노드별로 뜯어보기

<https://smith.langchain.com> → 프로젝트 `langgraph-travel-course` (또는 `.env` 에 적은 이름)

**트레이스는 Studio(`langgraph dev`) 실행에서 남습니다.** `langgraph.json` 의 `"env": ".env"` 가 서버에
`.env`(키 · `LANGSMITH_TRACING` · 프로젝트 이름)를 싣기 때문입니다. 터미널 실행(`run_once.py`)은 `.env` 를
읽지 않으므로 **트레이스가 없습니다.**

**한 실행 = 트레이스 하나가 아닙니다 — 게이트에서 나뉩니다.** `interrupt` 로 멈추면 그 트레이스가 끝나고,
재개는 **새 루트 트레이스**로 시작합니다(재개하면 게이트 노드가 첫 줄부터 다시 돌므로 그 게이트 노드가 맨 앞).
기본 실행(게이트 A 1 · B 2)은 트레이스 **3~4개**로 나뉩니다. 한 실행을 이어 보려면 LangSmith 의
**Threads** 탭에서 `thread_id` 로 찾습니다.

```text
트레이스 1  시작 → 게이트 A                 collect_city 3개가 **같은 시간대에 겹쳐** 있다 → 병렬의 증거
트레이스 2  게이트 A 재개 → 게이트 B
트레이스 3  게이트 B 재개 → 게이트 C        quality_pass 3개가 **겹치지 않고 이어져** 있다 → 순차의 증거
트레이스 4  게이트 C 재개 → END             (done 으로 확정하면)
각 노드 run 의 입력/출력이 곧 그 노드의 ΔS 다
```

병렬과 순차는 **서로 다른 트레이스**에서 봅니다. 게이트에서 `more` · `research` · `rebuild` 를 고르면
재개가 늘어난 만큼 트레이스도 늘어납니다.

**노드별로 찍히는 모양**

| 대상 | 트레이스에 찍히는 모양 | 읽는 법 |
| --- | --- | --- |
| 루프 골격 14 · 진단 2 · 처방 가지 6 | 루트 `travel` 아래 노드 이름의 chain run — 방문마다 1개 | 이름이 곧 노드 |
| `collect_*` · `repair_*` · `rebuilder` · `quality_pass` (live 면 `select_cities` 도) | 그 아래 `claude -p · <라벨>`(llm) → 도구 턴(tool) · `JSON 블록 추출`(parser). 라벨 예: `collect_city[하노이] 명소` · `repair_city[다낭]` · `repair_country` · `정성 판정 1/3회차` | 프롬프트 · 최종 JSON · 실검색 · 권한거부 · 중단 이유 · 토큰 |
| 라우터 (`route_after_info` 등) | 출발 노드의 자식 run (`route_after_info` 는 `diagnose_info` 밑) | 갈림길은 이 run 의 출력으로 읽는다 |
| `check_information` · `check_page` 반복 방문 | 방문마다 run 1개. 이름으로는 "재수집 뒤" 인지 "처방 가지 복귀" 인지 구분이 안 된다 | `langgraph_step` 메타데이터 · 바로 앞 형제 run · history 꼬리 `(처방 가지에서 복귀 — 바퀴를 쓰지 않음)` |
| `route_after_detour` ×3 | 셋 다 이름이 같다 | 목적지는 부모 `test_<이름>` 으로 읽는다 |
| `human_gate_a` · `human_gate_b` | 멈추면 그 트레이스가 끝나고, 재개는 새 루트 트레이스 | Threads 탭에서 `thread_id` 로 이어 본다 |

> 재수집(`repair_*`) 뒤 `check_information` run 이 한동안 없으면 — 끝나지 않은(열린) `claude -p · repair_*`
> run 이 있는지 봅니다. 그 걸음의 갈래가 모두 끝나야 검사기가 시작합니다 (10절).

---

## 9. 끝내는 법

```bash
# 터미널에서 Ctrl+C
```

`langgraph dev` 는 블로킹 프로세스입니다. **켜 둔 채 방치하지 마십시오.**

---

## 10. 문제가 생기면

| 증상 | 원인 · 조치 |
| --- | --- |
| `InvalidUpdateError: Can receive only one value per step` | STEP 4 의 reducer 가 아직 안 붙었습니다 |
| 게이트에서 안 멈추고 그냥 끝남 | STEP 5 의 `interrupt` 가 아직 안 붙었습니다 |
| `interrupt` 인데 오류가 남 (순수 파이썬) | `compile_graph(InMemorySaver())` 로 체크포인터를 넘기십시오 |
| Studio 에서 실행 중 서버가 재시작됨 | `--no-reload` 를 빠뜨렸습니다. 감시 기능은 `*.py` 만 보므로, 실행 중 코드를 고치거나 `new_detour.py` 가 파일을 만들면 서버가 다시 떠 돌던 run 이 끊깁니다 |
| 재수집(`repair_*`) 뒤 `check_information` 이 한동안 안 보임 | **대개 정상 — 가장 느린 갈래를 기다립니다.** `repair_city ×k` · `repair_country` 는 한 걸음(superstep)에서 나란히 돌고, 패널에는 먼저 끝난 갈래가 먼저 쌓이지만 `check_information` 은 그 걸음의 **모든 갈래가 끝난 뒤** 한 번 켜집니다. live 에서 한 갈래 = `claude -p` 1회(타임아웃 600초 · 24턴) + 바뀐 사진 재확인 → 보통 2~6분, 최악 10분+ (근거를 많이 요구하는 `repair_country` 가 가장 느리기 쉽습니다). 확인 순서: LangSmith 에 열려 있는 `claude -p · repair_*` run → `curl.exe -s http://127.0.0.1:2024/threads/<tid>/state` 의 `next` · `tasks` → `/threads/<tid>/runs` 의 `status` → 서버 로그의 Traceback. history 에 `check_information: … 2바퀴` 줄이 있거나 두 번째 `diagnose_info` · 게이트 A 를 봤다면 검사기는 돌았습니다 (패널에서 놓친 것 — `diagnose_info` 입구는 `check_information` 하나뿐) |
| `check_information` run 이 빨간색(error) · 스택 끝이 검사기의 `.strip()` | 재수집이 칸의 형을 바꾸는 patch(예: 글자 칸에 목록)를 넣은 경우입니다. 지금 킷은 그런 patch 를 `형이 다릅니다 (지금은 글자, 받은 것은 목록) — 같은 형으로 보내십시오` 로 거부하고 history 의 `↳ 적용 못 함:` 에 남깁니다. 그래도 나오면 킷 결함이니 thread_id · 스택을 보고합니다 (검사기는 고치지 않습니다) |
| 노드가 통째로 두 번 돎 | fan-in 을 두 줄로 나눠 썼습니다. `add_edge([...], "...")` 리스트로 |
| `KeyError` 가 라우터 뒤에서 남 | 라우터 반환값이 매핑에 없습니다. `check_graph_shape.py` 4번 |
| `claude 를 찾지 못했습니다` | `live` 모드인데 CLI 가 없습니다. `GRAPH_MODE=replay` 로 돌리십시오 |
| 실행이 10분 넘게 안 끝남 | `live` 모드입니다. Ctrl+C 후 `GRAPH_MODE=replay`. replay 라도 게이트 B 에서 `done` 이면 정성 3회(`claude -p`)에 6~12분이 듭니다 — 구조만 볼 때는 `run_once.py --mode replay --auto proceed` (게이트 B 에서 스스로 끝) |
| 트레이스가 LangSmith 에 안 뜸 | 터미널 실행(`run_once.py`)이면 정상입니다 — `.env` 를 읽지 않아 트레이스를 보내지 않습니다. 트레이스는 Studio(`langgraph dev`) 실행에서 남습니다 (`langgraph.json` 의 `"env": ".env"`). Studio 인데도 없으면 `.env` 의 `LANGSMITH_TRACING=true` · `LANGSMITH_PROJECT` 를 확인하고 서버를 다시 켭니다 |
| 한 실행의 트레이스가 여러 개로 흩어짐 | **정상.** 게이트(`interrupt`)에서 멈추면 트레이스가 끝나고, 재개는 새 루트 트레이스입니다. LangSmith **Threads** 탭에서 `thread_id` 로 이어 봅니다 (8절) |
| 처방 가지가 계속 떨어진다 (test 불합격 → 한 번 더 → 게이트) | 정해진 절차로 못 고친 것입니다. 게이트 `② 왜` 맨 앞의 *"처방 가지가 못 고침"* 줄, 상태의 `failure_evidence`, 실패 기록(`evidence/failures/<thread_id>.jsonl` · `python scripts/failure_report.py`)에서 무엇이 남았는지 봅니다. 시험지를 약하게 만들어 통과시키지 않습니다. 줄이 *"처방 가지 시험지가 깨짐"* 이면 증상이 아니라 시험지가 터진 것입니다 — `python scripts/detour_tests/test_<이름>.py` 를 혼자 돌려 오류 줄을 고칩니다 |
| 처방 가지가 안 켜진다 | **대개 정상** — 가지는 그 실패가 났을 때만 켜지고, 진단만 매번 돕니다. `replay` 에서 재현(inject)이 없으면 가지가 안 켜지는 것이 정상입니다. 켜지는 것을 보려면 재현 이름을 확인합니다 — `registry.py` 의 이름 그대로, 입력은 `{"inject": ["image_dead"]}`. 틀린 이름은 `read_request` 의 history 에 *"모르는 inject 이름을 버렸습니다"* 로 남습니다. **정성 회차 중**(루프 C 가 한 번이라도 돈 뒤)에는 루프 B 가지를 타지 않습니다 — 파일 해시 사슬을 지키려고. 증상은 게이트에 남고, 게이트 B 에서 `research` · `rebuild` 를 고르면 다시 탈 수 있습니다 |
| `check_graph_shape.py` 11번 ERROR | **처방 가지 계약**이 깨졌습니다 — 루프 골격 · 진단 · 등록된 처방 가지 밖의 노드, 진단 밖에서 갈라짐, 수집 노드로 복귀, 가지가 루프 골격 칸(판정 · 바퀴 · 게이트)을 씀, 등록부 · 모듈 · 시험지 세 조각 불일치, 시험지 문법 오류 · `run(root=None)` 없음, 시험지가 `travel_graph` 를 import 함, `build.py` 의 `SPINE` 에 이름을 더 적음(루프 골격 · 진단의 정본 이름은 검사기가 쥡니다), 라우터가 `detour_limit` · `failure_kind` 를 코드가 아니라 주석에만 적음 등. 메시지가 가리키는 조각을 `specs/06_DETOUR.md` 대로 고칩니다 (세 조각은 `new_detour.py` 로 만들면 자리가 맞습니다) |

---

## 11. 처방 가지 추가 (STEP 6 · 조건부)

**실행을 본 뒤, 로그에 처방 가지 후보가 있을 때만 하는 일입니다.** 결정은 없습니다 — 결정 13개는
그대로입니다. 준비도 검사도 STEP 1~5 만 봅니다.

킷 기본 가지 3개는 알려진 실패 · 로그로 잡힌 실패를 규칙(결정적) 노드로 확장해 둔 결과물이고,
그래프 안에서 늘 돕니다 — 진단은 매번, 가지는 그 실패가 났을 때만 켜집니다.
`encoding` 은 알려진 실패 축(Windows cp949 · 현지 글자 파일명)이라 로그 실측 전에 미리 구축했고,
`image_dead` 는 루프 킷 실행 로그(해시 두 글자 `8/8c` 를 지어내 11장 전부 죽음 — 킷에 든 예시 인계본 `graph/04_RUN_EVIDENCE.md` 1-b),
`image_spec` 은 실습생 게이트 입력(원본 크기 사진이 서랍을 뚫음 — 검사기는 못 봄)에서 나왔습니다.
STEP 6 은 **새 실패가 로그에 반복해서 남을 때만** 같은 방식으로 가지를 하나 더합니다.

- **진입 조건** — `python scripts/failure_report.py` (또는 `--all` · 모은 폴더)의 ③ · ③-2 에 후보가
  있을 때만. 보고서 끝 줄이 `이번 실행의 실패는 이미 처방 가지와 재수집이 맡았습니다 — STEP 6 은 하지 않아도 됩니다`
  이면 "STEP 6 불필요"로 끝냅니다. replay 기본 실행은 ③ · ③-2 가 모두 비는 것이 정상입니다.
- **시간** — STEP 1~5 + 실행 약 60분. STEP 6 은 후보가 있을 때만 약 20분(관찰 5 + 가지 15).
  자기 실패로 루프 B 가지까지 만들면 30~40분이 듭니다 — 과제로 권합니다.

명세는 `specs/06_DETOUR.md`, 절차는 `graph-detour-builder` 스킬(`.claude/skills/graph-detour-builder/SKILL.md`)이
안내합니다. Claude Code 에서 STEP 6 을 요청하면 이 스킬이 아래 순서를 이끕니다.

```text
0  관찰         python scripts/failure_report.py 로 실패 기록을 읽는다
                (② 처방 가지가 맡은 실패 · ③ 아직 처방 가지가 없는 실패 · ③-2 재수집(LLM)이 반복해서 맡은 원인)
                ③ · ③-2 가 비면 여기서 끝 — STEP 6 불필요
                가지가 켜지는 모양은 replay + 실패 재현 하나(--inject image_dead)로 Studio 에서 본다
1  후보 고르기  ③ 또는 ③-2 에서 하나 — 같은 입력에 같은 고칠 법이 있을 때만 가지로 뺀다
                (없으면 아직 재수집(LLM)에 둔다 — 같은 실패가 반복되고 고칠 법이 정해지면 그때 뺀다)
2  세 조각      python scripts/new_detour.py <이름> --loop A|B --title "…"
                → 만든 직후에도 그래프는 그대로 돈다 · check_graph_shape 12행 PASS
                (--loop B 면 INJECT_AT = "country" — 루프 B 가지는 replay 에서 국가 소개의 증상으로만 재현된다)
3  시험지 먼저  test_<이름>.py + inject() 채우기 → --inject <이름> 으로 그 실패를 재현해 불합격(빨간불) 확인
                (루프 A: --auto stop · 루프 B: --auto proceed — 끝에 찍히는 history 줄을 06_DETOUR 에 옮긴다)
4  고치는 법    fix() 채우기 → 같은 명령 → 합격(초록불) · 검사기로 복귀
5  회귀         check_graph_shape (12행) · run_graph_regression · replay 로 재현 없이 한 번 돌려 처방 가지 0회
                (루프 B 가지면 반드시 --auto proceed — 루프 B 까지 가야 진단 B 가 돈다)
6  기록         06_DETOUR.md 의 MACHINE detour 블록 · STATUS APPROVED · PROJECT_MEMORY
```

- **한 번은 일화, 세 번은 패턴.** 내 가지는 내 킷에만 둡니다. 킷에 넣는 가지는 로그에서 반복 확인된
  실패(여러 교육생 기록에서 서로 다른 실행 3곳 이상 — `failure_report.py <폴더>…` 의 "패턴") **또는**
  원인과 고칠 법이 이미 알려진 실패 축(예: 인코딩)뿐입니다. (킷 기본 셋 가운데 `image_dead` 는 두 실행,
  `image_spec` 은 게이트 입력 한 번에서 나왔습니다 — 킷 저자가 보기로 넣은 예외입니다)
- 하지 않는 것: 계약 검사기 · `03_CONTRACT.json` 수정, 시험지를 약하게 만들어 통과,
  수집 노드로 복귀, 루프 골격 칸(판정 · 바퀴 · 게이트) 쓰기, 루프 골격 · 진단에 노드 추가.
- STEP 6(처방 가지 추가)은 STEP 진행 · 그래프 실행과 **다른 모드**입니다. 섞지 않습니다.
- `langgraph dev` 는 `--no-reload` 로 켜 두므로, 새 가지는 **서버를 다시 켜야** Studio 그림에 나타납니다
  (`new_detour.py` 가 `.py` 를 만들 때 돌던 run 이 끊기지 않게 하는 것도 `--no-reload` 입니다).
