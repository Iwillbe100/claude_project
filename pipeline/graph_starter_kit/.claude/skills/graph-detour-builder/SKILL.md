---
name: graph-detour-builder
description: STEP 6(처방 가지 추가 · 조건부)을 진행한다. 먼저 실패 기록 보고서(failure_report.py)의 ③ · ③-2 에 후보가 있는지 보고, 없으면 "STEP 6 불필요"로 끝낸다. 후보가 있으면 되풀이된 실패 하나를 골라 진단 노드에서 갈라지는 규칙 처방 가지(등록부 한 줄 · 고치는 법 · 시험지)로 만들고, 시험지를 먼저 채워 빨간불을 본 뒤 고치는 법으로 초록불을 확인한다. "STEP 6 진행해줘", "처방 가지 만들어줘", "이 실패를 노드로 빼줘", "새 가지 추가해줘" 같은 요청에서 사용한다.
user-invocable: true
argument-hint: "[처방 가지 이름]"
---

# graph-detour-builder — 규칙 처방 가지 제작 진행자

## 활성화 조건

STEP 1~5 가 모두 `APPROVED` 이고, 그래프를 **한 번 이상 돌려 본 뒤**이며
(`evidence/failures/` 에 실패 기록이 있거나 `PROJECT_MEMORY.md` 4번에 실행이 적혀 있다),
**실패 기록 보고서 ③ · ③-2 에 처방 가지 후보가 있을 때**(아래 "진입 조건")만 가지를 만든다.
아니면 **시작하지 않고** 넘긴다.

| 상황 | 넘기는 곳 |
| --- | --- |
| STEP 1~5 중 `APPROVED` 가 아닌 것이 있다 | `graph-spec-builder` |
| 그래프를 아직 한 번도 안 돌렸다 | `graph-run` (replay 로 한 번이면 된다) |
| 보고서 ③ · ③-2 에 `[후보]` · `[패턴 …]` 이 없다 (끝 줄 `… STEP 6 은 하지 않아도 됩니다`) | **"STEP 6 불필요"** 라고 말하고 끝낸다 → `evidence-review` |
| "계약 기준을 바꾸고 싶다" · "검사가 너무 깐깐하다" | 계약 변경 — 루프 킷으로 (`spec-sync` 의 답과 같다) |
| "루프 골격에 노드를 더하고 싶다" · "노드를 쪼개고 싶다" | 하지 않는다. 그 실패가 로그에 되풀이됐으면 **처방 가지로 빼는** 이 스킬로 다시 시작한다 |

읽는 순서: `CLAUDE.md` → `python scripts/failure_report.py` 결과(진입 조건) → `specs/06_DETOUR.md`(읽기 0 · 3 · 4 먼저)
→ `travel_graph/detours/registry.py`.

---

## 진입 조건 — 먼저 확인한다 (후보가 없으면 여기서 끝)

킷의 처방 가지 3개(`encoding` · `image_dead` · `image_spec`)는 이미 그래프 안에서 늘 돈다 — 진단은 매번,
가지는 그 실패가 났을 때만. **새 실패가 로그에 되풀이해서 남을 때만** 가지를 하나 더한다.
그러니 첫 일은 보고서를 보는 것이다.

```bash
python scripts/failure_report.py            # 가장 최근 실행 하나
python scripts/failure_report.py --all      # 이 킷의 실행 전부
python scripts/failure_report.py <폴더>…     # 모은 기록 (강사가 여러 교육생 것을 모아서)
```

보고서 끝 줄이 판정이다.

```text
후보가 있을 때
 다음: 후보 하나를 골라 specs/06_DETOUR.md 의 `읽기 5` 에 적고 `STEP 6 진행해줘`
       (같은 입력에 같은 고칠 법이 없으면 재수집에 그대로 둡니다 — 06_DETOUR `읽기 4`)

후보가 없을 때 — ③ · ③-2 가 비었다
 이번 실행의 실패는 이미 처방 가지와 재수집이 맡았습니다 — STEP 6 은 하지 않아도 됩니다
 (live · --all · 여러 교육생의 기록을 모은 폴더에서 후보가 생기면 그때 합니다)

후보가 없을 때 — ③ 에 한 번 나온 [일화] 뿐이다
 한 번 나온 실패(일화)뿐입니다 — STEP 6 은 하지 않아도 됩니다
 (같은 실패가 되풀이되면 — 다음 실행 · --all · 모은 폴더에서 [후보]가 되면 — 그때 합니다)
```

**후보가 없으면 가지를 만들지 않는다.** 최근 실행에서 비었으면 `--all` 도 한 번 본다. 그래도 비면 이렇게
말하고 끝낸다 — 가지를 만들려고 없는 실패를 찾지 않는다.

```text
STEP 6 불필요 — 이번 실행의 실패는 이미 처방 가지와 재수집이 맡았습니다.
  실패 기록 보고서 ③ · ③-2 가 비어 있습니다 (replay 기본 실행은 이것이 정상입니다).
  specs/06_DETOUR.md 는 DRAFT 그대로 둡니다 — validate_specs.py --step 6 의 SHORT(exit 2)는 오류가 아닙니다.
  다음: "결과 정리해줘" (evidence-review). live · --all · 모은 폴더에서 후보가 생기면 그때 STEP 6 을 합니다.
```

가지가 켜지는 모양만 보고 싶다고 하면 **킷의 가지를 재현해** 보여 준다(아래 ①② 의 `--inject image_dead`).
새 가지는 만들지 않는다.

---

## 절대 규칙 10가지

1. **시험지 먼저 — 빨간불을 보고 나서 고친다.** 시험지(`test_<이름>.py`)와 `inject()` 를 채우고
   그 실패를 재현해(`--inject`) **불합격을 눈으로 본 뒤에** `fix()` 를 채운다. 순서를 바꾸지 않는다.
   먼저 고치면 시험지가 "내가 고친 것"에 맞춰지고, 무엇을 잡는지 한 번도 확인하지 못한다.
2. **계약 검사기 · `03_CONTRACT.json` · 킷의 시험지를 고치지 않는다.** `scripts/check_*.py` ·
   `graph/03_CONTRACT.json` · `scripts/detour_tests/_common.py` · `test_encoding.py` · `test_image_dead.py` ·
   `test_image_spec.py` · `_template_test.py.tmpl` · `travel_graph/detours/` 의 `__init__.py` · `log.py` ·
   `encoding.py` · `image_dead.py` · `image_spec.py` · `_template.py` · `scripts/new_detour.py` ·
   `scripts/failure_report.py` 는 킷 소유다. 고쳐야 한다고 판단되면 **고치지 말고 사람에게 넘긴다.**
3. **루프 골격 · 진단에 노드를 더하지 않는다 — 노드는 `new_detour.py` 로만 늘린다.** `build.py` · `edges.py` ·
   `nodes.py` 를 고치지 않는다. 배선 · 라우터 매핑 · `ALLOWED` 는 등록부 한 줄에서 저절로 생긴다.
4. **수집 노드로 돌아가게 하지 않는다.** 합격하면 **그 루프의 검사기**(`check_information` ·
   `check_page`)로 돌아온다 — 킷이 이미 그렇게 배선한다. 수집 노드로 가면 합류가 영영 기다린다.
5. **루프 골격 칸을 쓰지 않는다.** `fix()` 는 받은 `data`(`country` · `days` · `country_intro` · `cities`)만
   그 자리에서 고친다. 판정 · 바퀴 · 게이트 칸은 처방 가지의 것이 아니다. 시험지는 `travel_graph` 를
   import 하지 않는다 (판정 독립).
6. **시험지를 약하게 만들어 통과시키지 않는다.** 초록불이 안 나오면 시험지가 아니라 `fix()` 를
   고친다. 정해진 절차로 못 고치는 것은 `unfixed` 로 남겨 **게이트(사람)** 로 보낸다 — 그것도 정상이다.
7. **정상 인계본에서 합격해야 한다 (오탐 금지).** 재현 없이 돌렸을 때 가지가 켜지면 시험지가
   틀린 것이다. 그 상태로 기록하지 않는다.
8. **한 번은 일화, 세 번은 패턴 — 되풀이된 실패로만 연다.** 후보(보고서 ③ · ③-2)가 없으면 만들지 않고,
   `[일화]` 한 줄 · `[한 번 — 재수집이 맡으면 된다]` 뿐이면 아직 재수집 · 게이트에 둔다. 교육생의 가지는
   **본인 킷에만** 둔다 — 킷 편입을 권하지 않는다. 킷 기본 가지는 여러 교육생의 기록에서 **서로 다른 실행
   3곳 이상**에 나온 것 또는 원인과 고칠 법이 이미 알려진 실패 축(예: 인코딩)뿐이고, 그 판단은
   강사 · 킷 저자의 일이다.
9. **종료 코드가 근거다.** "고친 것 같습니다" 는 근거가 아니다. 시험지 exit · `check_graph_shape`
   exit · 회귀 `실패 0` · `history` 의 `test_<이름>: PASS … (검사기로 복귀)` 줄을 그대로 보여 준다.
10. **결정을 묻지 않는다.** STEP 6 은 결정 0개다 — MACHINE `decisions` 에 키를 넣지 않는다
    (결정 13개 고정). 묻는 것은 `06_DETOUR.md` 읽기 4 의 **여섯 질문**뿐이고, FIXED 블록의 질문
    문장은 고치거나 지우지 않는다.

---

## 실행 순서 — 여덟 걸음 (`06_DETOUR.md` 읽기 1 과 같다)

```text
진입        보고서 ③ · ③-2 에 후보가 있나        없으면 "STEP 6 불필요" 로 끝 (위 진입 조건)
관찰 (5분)
 ① 돌린다   그래프를 돌린 실행이 있다 (Studio · run_once.py) → evidence/failures/<thread_id>.jsonl
 ② 본다     보고서 ③ · ③-2 · history 의 검사기 · 진단 · 처방 가지 줄 · LangSmith
            + 킷의 image_dead 를 재현해 가지가 켜지는 모양
 ③ 묻는다   되풀이됐나?                          아니오 → 끝
 ④ 가른다   같은 입력에 같은 고칠 법이 있나?     아니오 → 재수집(LLM)에 둔다 · 예 → 06_DETOUR.md 읽기 5 에 적는다
가지 (15분)
 ⑤ 만든다   new_detour.py → 구조 검사 12행 PASS (아직 아무것도 안 바뀜)
 ⑥ 빨간불   test_<이름>.py + inject() → --inject 로 그 실패를 재현 → test FAIL → 게이트 정지
 ⑦ 초록불   fix() → 같은 명령 → test PASS → 검사기로 복귀
 ⑧ 잠근다   구조 검사 · 회귀 테스트 · 재현 없이 한 번 (가지 0회) · 06_DETOUR.md MACHINE detour 블록 ·
            STATUS APPROVED · validate_specs --step 6 · 00_DECISION_LOG 6번 한 줄 · PROJECT_MEMORY 5번
```

**시간.** 후보가 있을 때만 약 20분 = 관찰 5분 + 루프 A 처방 가지 15분 (아래 코드 모양 참고용 예 `alt_english`
수준). 자기 실패로 루프 B 가지까지 만들면 **30~40분**이다 — 수업 안에 끝내려 하지 말고 과제로 권한다.
후보가 없으면 하지 않는다 (STEP 1~5 + 실행 약 60분으로 끝).

> **확인 실행은 전부 `replay` 로 한다.** 10초 안에 끝나고 결과가 항상 같다.
> **`--thread` 는 매번 새 이름으로 준다** (`red1` · `green1` …). 같은 이름이면 실패 기록이 한 파일
> (`evidence/failures/<thread>.jsonl`)에 섞이고, 같은 걸음 번호 · 같은 내용의 줄은 **한 번만** 남아 두 번째
> 실행의 (똑같은) 진단 줄이 빠진다. (주지 않으면 실행마다 `run-날짜-시각` 이 붙는다)
> **`--auto` 를 준다.** `run_once.py` 는 답이 없으면 — `--auto` 의 답을 다 썼거나, 표준입력이 터미널이
> 아니거나(에이전트 · 파이프 · Windows 의 NUL), 입력이 EOF 면 — 권장값으로 넘어가지 않고 **그 게이트에서
> 끝낸다.** 그래서 확인 실행이 정성 3회(`claude -p`, 6~12분)까지 들어가지 않는다.
>
> ```text
> 루프 A 처방 가지   --auto stop       게이트 A 에서 끝낸다
> 루프 B 처방 가지   --auto proceed    게이트 A 를 넘겨 루프 B 까지 → 게이트 B 에서 스스로 끝난다
> ```
>
> 끝에 **`history — 검사기 · 진단 · 처방 가지 · 게이트 줄만`** 이 찍힌다. Studio 결과 패널의 `history` 와 같은
> 문장이다. 빨간불 · 초록불 줄(`red_seen` · `green_seen`)은 여기서 그대로 옮겨 적는다.

### ①② 관찰 — 내 실행을 보고, 가지가 켜지는 모양을 본다 (5분)

**먼저 내 실행.** 진입 조건에서 본 보고서의 후보 줄을 짚고, 같은 실행의 `history` 에서 그 실패가 어디서 났는지
보여 준다. 진단 줄이 무엇을 골랐는지가 핵심이다.

```text
diagnose_info: 처방 가지 대상 없음 → 루프 골격 그대로                  평소 — 진단은 매번 켜진다
diagnose_info: ▷ <title> — 증상 N곳 → 처방 가지 fix_<이름> (1/2회째)   진단이 가지를 골랐다
diagnose_page: 증상은 있지만 처방 가지를 타지 않음 (<이름>: <why> · …) → 루프 골격 그대로
```

`처방 가지 대상 없음` 뒤에 SHORT 가 이어져 재수집(`repair_*`)으로 간 바퀴가 여럿이면 그 부족이 ③-2 로 올라온다.
Studio(`langgraph dev`)로 돌린 실행이면 LangSmith 에서 그 바퀴의 `claude -p · repair_city[<도시>]` run 을 열어
모델이 무엇을 되풀이했는지 본다. 터미널 `run_once.py` 는 `.env` 를 읽지 않아 트레이스가 없다.

**다음, 가지 하나가 켜진 모양 — 킷의 `image_dead` 를 재현한다.** 내 가지를 다 만들면 이렇게 돈다.

```bash
python scripts/run_once.py --mode replay --inject image_dead --auto stop --thread obs1
python scripts/failure_report.py
```

터미널(`run_once.py`)에는 노드가 켜진 순서와 `failure_kind` · `detour_verdict` 가 찍힌다.

```text
 [   0.0s]  7  check_information
              info_verdict = SHORT
 [   0.1s]  8  diagnose_info
              failure_kind = image_dead
 [   0.1s]  9  fix_image_dead
              cities += 3
 [   0.1s] 10  test_image_dead
              detour_verdict = PASS
 [   0.1s] 11  check_information
 [   0.1s] 12  diagnose_info
              failure_kind =
 ...
 처방 가지   : fix_image_dead   (실패 기록: evidence/failures/obs1.jsonl)
 ...
 history — 검사기 · 진단 · 처방 가지 · 게이트 줄만
```

Studio 로 보려면 입력 칸에 `{"inject": ["image_dead"]}` 를 넣는다. 결과 패널의 `history` 에는
같은 길이 문장으로 남는다 (터미널 끝의 history 는 이 중 검사기 · 진단 · 처방 가지 · 게이트 줄만). **이 줄들을 짚어 준다.**

```text
read_request: 베트남 · 실행 모드 replay
  ↳ ⚠ 실패 재현(inject) 예약: image_dead — 수집 직후 그 실패를 다시 일으키고, 진단 노드가 찾아 처방 가지로 보냅니다
...
collect_city[하노이]: replay 로 수집
  ↳ ⚠ 실패 재현 [image_dead] 하노이/탕롱 황성 사진 주소를 해시 두 글자(8/8c)를 지어낸 upload 주소로 (404 — 실측 모양)
...
check_information: SHORT · 부족 12곳 · 1바퀴                         ← 판정 (기준을 채웠나)
diagnose_info: ▷ 이미지 주소가 죽어 있음 — 증상 1곳 → 처방 가지 fix_image_dead (1/2회째)   ← 원인
fix_image_dead: 1/2회째 · 고침 1곳 · 못 고침 0곳
  ↳ 하노이/탕롱 황성 이미지: 해시가 든 주소를 권장 형태로 바로잡았습니다 (Special:FilePath/Central_Sector_of_the_Imperial_Citadel_o)
test_image_dead: PASS · 1/2회 → check_information (검사기로 복귀)
check_information: SHORT · 부족 9곳 · 1바퀴 (처방 가지에서 복귀 — 바퀴를 쓰지 않음)
diagnose_info: 처방 가지 대상 없음 → 루프 골격 그대로
repair_city[하노이]: replay 로 3곳 보정                              ← 그다음은 루프 골격이 하던 일
...
check_information: PASS · 부족 0곳 · 2바퀴
diagnose_info: 처방 가지 대상 없음 → 루프 골격 그대로
human_gate_a: stop
```

실패 재현은 실측(킷에 든 예시 인계본 `graph/04_RUN_EVIDENCE.md` 1-b)의 모양 그대로다 — 파일은 실재하고 해시
두 글자(`8/8c`)만 지어낸 upload 주소 + 404. 고치는 법 1회째도 실측에서 통한 고칠 법(해시가 필요 없는
`Special:FilePath` 형태)이다. 이 가지가 생긴 과정은 아래 **"대표 예 — `image_dead` 가 가지가 된 실제 이력"**.

말해 줄 것 세 가지.

```text
① 검사기 뒤에 진단이 매번 켜진다        판정 다음에 원인. replay 에서 재현하지 않으면 "처방 가지 대상 없음"
② 처방 가지는 검사기로 돌아온다         그리고 바퀴를 쓰지 않는다 (부족 12곳 → 9곳 · 1바퀴 → 1바퀴)
③ 재현은 이미 있는 가지를 켜 볼 뿐이다  무엇을 가지로 만들지는 로그가 정한다 — 이 재현 실행은 후보를 만들지 않는다
```

**실패 기록 보고서 읽는 법** — `python scripts/failure_report.py` (가장 최근 실행 하나 — 여기서는 방금의 재현 실행)

```text
 ① 실행별 요약
   obs1                                 replay  진단 3번 · 처방 가지 image_dead:PASS · 재현 image_dead

 ② 처방 가지가 맡은 실패
   image_dead       들어감 1번 · 시도 1번 · 합격 1번

 ③ 아직 처방 가지가 없는 실패 — 규칙표 밖 · 수집 실패 · 가지가 못 맡음 (같은 줄 2번 이상이면 후보 · 실행 3곳 이상이면 패턴)
   (없습니다 — 등록된 처방 가지와 원인 규칙표가 다 맡았습니다)

 ③-2 재수집(LLM)이 반복해서 맡은 원인 — 처방 가지 후보 (같은 입력에 같은 고칠 법이 있으면 가지로)
   (없습니다 — 가지 없이 재수집으로 간 부족이 없거나, 모두 replay 실행입니다)
   (재현(inject) 실행 1개는 ③ · ③-2 에서 세지 않았습니다 — 일부러 다시 일으킨 실패입니다)
======================================================================
 이번 실행의 실패는 이미 처방 가지와 재수집이 맡았습니다 — STEP 6 은 하지 않아도 됩니다
```

| 칸 | 뜻 |
| --- | --- |
| ① | 실행마다 진단이 몇 번 돌았고 어느 처방 가지를 타서 합격(`PASS`)/불합격(`FAIL`)했나 |
| ② | 등록된 처방 가지마다 `들어감`(진단이 보낸 횟수) · `시도`(fix → test 를 돈 횟수, 재시도 포함) · `합격` |
| ③ | **후보 ①.** 네 종류가 올라온다 — `규칙표에 없는 부족`(게이트 원인 규칙표가 못 묶은 검사기 지적) · `수집 실패`(도시를 통째로 못 모음) · `처방 가지 <이름> 가 못 맡음`(진단이 증상을 봤는데 가지를 태우지 않음 — 처방 한도를 이미 다 썼거나 · 정성 회차 중이거나 · 시험지가 멈춤) · `처방 가지 <이름> 가 못 고침`(가지를 탔지만 처방 한도 2회를 다 쓰고 게이트로 감). 줄마다 `[일화]`(한 번) · `[후보]`(같은 줄 2번 이상 · 또는 2실행 이상) · `[패턴 — 킷 처방 가지 후보]`(실행 3곳 이상). **재현(inject) 실행은 세지 않는다** |
| ③-2 | **후보 ②.** 가지 없이 SHORT 로 남아 재수집(루프 A) · 재생성 · rebuilder(루프 B)로 간 원인. (루프, 원인)마다 서로 다른 바퀴 수를 센다 — 한 실행에서 2바퀴 이상 또는 2실행 이상 `[후보]`, 3실행 이상 `[패턴 — 킷 처방 가지 후보]`, 그 밖 `[한 번 — 재수집이 맡으면 된다]`. **replay 실행은 세지 않는다** (replay 재수집은 인계본을 잘라 쓴다 — 가짜 패턴 방지) |

- `--all` 은 이 킷의 실행 전부, `<폴더>…` 는 강사가 여러 교육생의 `evidence/failures/` 를 모아 볼 때 쓴다
  (실행 이름에 교육생 폴더 경로가 남는다).
- **replay 기본 실행은 ③ · ③-2 가 모두 비는 것이 정상이다.** replay 의 인계본이 멀쩡하고, 부족은 원인 규칙표가
  다 맡고, replay 재수집은 세지 않기 때문이다. 후보는 live 실행 · `--all` · 모은 폴더에서 나온다. 비어 있으면
  진입 조건대로 "STEP 6 불필요" 로 끝낸다.
- 재현 실행 뒤의 보고서는 그 재현 실행(가장 최근)을 보여 준다. 내 후보는 `--all` 이나 내 실행 파일
  (`python scripts/failure_report.py evidence/failures/<thread>.jsonl`)로 다시 본다.
- 한도를 다 쓴 가지는 ③ 에 `처방 가지 <이름> 가 못 고침 · <첫 증상>` 으로 뜬다. 단 **재현(inject) 실행은 ③ · ③-2 에서
  세지 않는다** — 아래 `alt_english` 빨간불 실행을 보고서에 넣으면 ③ 은 비고 `(재현(inject) 실행 1개는 ③ · ③-2 에서
  세지 않았습니다 — 일부러 다시 일으킨 실패입니다)` 한 줄만 남는다. 빨간불 확인 실행이 제 가지를 후보로 올리지 않는다.

### ③④ 후보 고르기 — 되풀이됐나 · 같은 고칠 법이 있나

보고서 ③ · ③-2 에서 한 줄을 고르고, **되풀이됐는지**와 **처방 가지가 맡을 실패인지** 먼저 가린다.

```text
③ 묻는다   되풀이됐나?                        ③ · ③-2 의 [후보] · [패턴 …] (③ 은 같은 줄 2번 이상)
                                              아니오 ([일화] 한 줄 · [한 번 …] 뿐) → 끝. 로그가 더 쌓이면 다시 본다
④ 가른다   같은 입력에 같은 고칠 법이 있나?   아래 표
```

```text
처방 가지로 뺀다          정해진 고칠 법이 있다 · 같은 입력이면 같은 결과가 나오게 고칠 수 있다
아직 재수집(LLM)에 둔다   같은 입력에 같은 고칠 법이 아직 없다             → 재수집(repair_*)이 맡는다
                          같은 실패가 로그에서 반복되고 고칠 법이 정해지면 가지로 뺀다 (그래프가 자라는 방향)
사람에게 맡긴다           인터넷에 없는 정보 · 판단이 필요한 것            → 게이트
루프 킷으로 돌아간다      계약 기준 자체가 과하다                          → 03_CONTRACT 는 여기서 안 바꾼다
보고서에 남긴다           화면 코드(page.py) 문제                          → 처방 가지도 rebuild 도 못 고친다
```

둘 다 "예"가 아니면 여기서 끝낸다 — "이 실패는 아직 재수집(LLM) · 게이트가 맡습니다. 같은 실패가 로그에서
되풀이되고 고칠 법이 정해지면 그때 가지로 뺍니다" 라고 말한다.

그다음 `06_DETOUR.md` 읽기 4 의 여섯 질문을 **한 번에 2~3개씩** 묻는다. 매번 오른쪽 칸의
`image_dead` 답을 예로 보여 준다. 답은 읽기 5(`ANSWERS`)에 적는다.

```text
STEP 6 은 결정이 없습니다. 고른 실패에 대해 여섯 가지만 답하시면 처방 가지 세 조각이 정해집니다.

이미 정해 둔 것 (고민 X)
  - 모양은 하나입니다: 진단 → fix → test → 합격하면 그 루프의 검사기로 (바퀴 안 씀)
  - 처방 한도 2회. 넘으면 그 루프의 게이트에서 사람이 봅니다
  - 배선은 등록부 한 줄에서 저절로 생깁니다. build.py 는 건드리지 않습니다

질문 ① 어떤 실패인가요? 실패 기록 보고서(③ · ③-2)의 어느 줄인가요?
   예) image_dead — diagnose_info 줄의 "하노이/탕롱 황성 이미지: 손으로 만들 수 없는 주소 형태입니다 (upload.wikimedia.org)"
질문 ② 어느 루프(A/B)인가요? 왜요?
   예) A — 수집한 데이터(research_data.json)의 주소 문제라 페이지를 만들기 전에 고친다
질문 ③ 시험지가 무엇을 보면 불합격인가요? (정상 인계본에서는 반드시 합격)
   예) 404 기록 · 금지된 주소 형태 · 이미지가 아닌 주소. 안 모은 칸은 보지 않는다
```

- 이름(`kind`)은 영문 소문자 · 숫자 · 밑줄. 라우터가 쓰는 낱말(`repair` · `repair_country` · `gate` · `retry` · `back` ·
  `build` · `stop` · `research` · `rebuild` · `done` · `quality` · `again` · `halt` · `more` · `proceed`)과
  `log` · `registry` 는 쓸 수 없다. `title` 은 게이트 화면에 뜨는 한국어 이름이다.
- **루프 B 가지면 그 실패는 국가 소개에서 재현한다**(`INJECT_AT = "country"` — `new_detour.py --loop B` 가 처음부터
  이렇게 만든다). replay 의 루프 A 는 첫 바퀴 부족을 채울 때 도시를 인계본 통째로 되돌리므로, 도시에서 재현한
  실패는 루프 B 에 닿기 전에 지워진다. 그래서 **루프 B 가지는 replay 에서 국가 소개의 증상으로만 재현된다** —
  관광지 · 도시에만 있는 증상을 루프 B 로 고르면 빨간불을 볼 수 없다. 후보를 고를 때 먼저 가린다.

### ⑤ 세 조각 만들기

```bash
python scripts/new_detour.py <이름> --loop A --title "<화면 이름>" --dry-run    # 무엇이 생기는지만
python scripts/new_detour.py <이름> --loop A --title "<화면 이름>"
python scripts/check_graph_shape.py                                             # 12행 PASS
```

보여 줄 것 — 무엇이 생기고 어디에 붙는지 (아래는 코드 모양 참고용 예 `alt_english`).

```text
  + travel_graph/detours/registry.py   {"kind": "alt_english", "loop": "A", "title": "사진 설명이 영어로 나옴"},
  + travel_graph/detours/alt_english.py
  + scripts/detour_tests/test_alt_english.py
  = 그래프에 노드 두 개가 생깁니다: fix_alt_english · test_alt_english
    diagnose_info ─alt_english→ fix_alt_english → test_alt_english
        합격 → check_information (검사기로 복귀) · 불합격 → 한 번 더 · 한도 → human_gate_a
```

**만든 직후에는 아무것도 바뀌지 않는다**고 분명히 말한다. 빈 시험지는 늘 합격이라 진단이 이
가지를 고르지 않고, 빈 `inject()` 는 아무것도 재현하지 않는다. `--inject <이름>` 으로 돌려도
`diagnose_info: 처방 가지 대상 없음 → 루프 골격 그대로` 가 나온다. 노드는 22 → 24개가 된다.
`new_detour.py` 는 끝에 "다음 순서"와 그 루프에 맞는 확인 명령(A `--auto stop` · B `--auto proceed`)을 출력한다.

### ⑥ 시험지 먼저 — 빨간불

`scripts/detour_tests/test_<이름>.py` 의 `TODO` 와 `travel_graph/detours/<이름>.py` 의 `inject()` 를
채운다. `fix()` 는 **아직 비워 둔다.** 채운 모양은 아래 "코드 모양 참고용 예" 를 따른다.

```bash
python scripts/detour_tests/test_<이름>.py            # 마지막 실행의 output 이 정상이면 exit 0 (오탐 없음)
python scripts/run_once.py --mode replay --inject <이름> --auto stop --thread red1      # 루프 B 는 --auto proceed
```

시험지를 혼자 돌리려면 그 시험지가 읽는 파일이 있어야 한다. 루프 A 는 ①② 관찰로 `output/research_data.json` 이
생긴다. **루프 B 는 화면(`output/travel_site.html`)이 필요한데 관찰 실행(`--auto stop`)은 게이트 A 에서 끝나 화면을
만들지 않는다** — 그대로 돌리면 `[ERROR] … output/travel_site.html 이 없습니다 (build_page 가 먼저 돌아야 합니다)`
(exit 1). `python scripts/run_once.py --mode replay --auto proceed` 로 한 번 돌린 뒤에 혼자 돌린다.

루프 A 라면 그래프를 돌리기 전에 아래 **손으로 확인하기** 로 "정상 인계본 → exit 0 · 재현하면 → exit 2" 를
먼저 볼 수 있다. 둘 중 하나라도 어긋나면 그래프를 돌려도 빨간불이 안 나온다.

보여 줄 것 — 진단이 이 가지를 고르고, 두 번 떨어지고, 게이트에서 멈춘다.

```text
 [   0.1s]  8  diagnose_info
              failure_kind = alt_english
 [   0.1s]  9  fix_alt_english
              cities += 3
 [   0.1s] 10  test_alt_english
              detour_verdict = FAIL
 [   0.1s] 11  fix_alt_english
              cities += 3
 [   0.1s] 12  test_alt_english
              detour_verdict = FAIL
 ⏸  사람 차례 — 그래프가 멈췄습니다
 ① 지금: 루프 A(정보량) · SHORT · 1/3바퀴 · 못 채운 칸 9곳 · 같은 오류 반복 0/2
 ② 왜:
    · 처방 가지가 못 고침 — 사진 설명이 영어로 나옴  (1곳)
        고치려면  사진 설명이 영어로 나옴 — 처방 가지가 못 고쳤습니다. (게이트 화면 '고치려면' 칸에 뜨는 문장)
        예        [alt_english] 사진 설명이 영어로 나옴: 목표 0 / 실제 1
    · 이미지를 아직 안 모음  (9 / 9)
 ...
 (--auto) → stop
 ...
 처방 가지   : fix_alt_english → fix_alt_english   (실패 기록: evidence/failures/red1.jsonl)
 ...
 history — 검사기 · 진단 · 처방 가지 · 게이트 줄만
   check_information: SHORT · 부족 9곳 · 1바퀴
   diagnose_info: ▷ 사진 설명이 영어로 나옴 — 증상 1곳 → 처방 가지 fix_alt_english (1/2회째)
   fix_alt_english: 1/2회째 · 고침 0곳 · 못 고침 0곳
   test_alt_english: FAIL · 1/2회 → fix_alt_english
   fix_alt_english: 2/2회째 · 고침 0곳 · 못 고침 0곳
   test_alt_english: FAIL · 2/2회 → human_gate_a
   human_gate_a: stop
```

이것이 **빨간불**이다 — 시험지가 그 실패를 잡는다는 증거. 끝의 history 에 찍힌
`test_alt_english: FAIL · 2/2회 → human_gate_a` 를 **그대로** 읽기 5 "빨간불" 과 MACHINE `red_seen` 에 옮겨
적는다 (Studio 결과 패널의 `history` 와 같은 줄이다). 실패 기록 `evidence/failures/red1.jsonl` 의 마지막
`test_alt_english` 줄(`"detour_verdict": "FAIL"` · `"attempt": 2` · `"next": "human_gate_a"`)도 같은 내용이다.
이때 게이트 `② 왜` 의 `고치려면` 칸은 아직 틀의 `HOWTO` 문장이다 — ⑦ 에서 모듈과 함께 채운다.
루프 B 라면 같은 줄이 `… → human_gate_b` 이고, 그래프는 게이트 A 를 `proceed` 로 넘긴 뒤 게이트 B 에서 스스로 끝난다.

빨간불이 안 나오면(`처방 가지 대상 없음`) ⑦ 로 가지 않는다 — 아래 "문제가 생기면" 의 **가지가 안 켜진다**.

### ⑦ 고치는 법 — 초록불

`fix()` 를 채운다. 1회째는 **replay 에서 되는 절차**여야 한다 (회귀 T14 가 "한 번에 합격"을 본다).
live 에서만 되는 방법은 2회째로 둔다. 더 할 것이 없으면 2회째는 "없음" — 못 고친 곳은
`unfixed` 로 돌려주면 게이트에서 사람이 본다.

```bash
python scripts/run_once.py --mode replay --inject <이름> --auto stop --thread green1    # 루프 B 는 --auto proceed
```

보여 줄 것 — 터미널 끝의 history (Studio `history` 와 같은 줄).

```text
   check_information: SHORT · 부족 9곳 · 1바퀴
   diagnose_info: ▷ 사진 설명이 영어로 나옴 — 증상 1곳 → 처방 가지 fix_alt_english (1/2회째)
   fix_alt_english: 1/2회째 · 고침 1곳 · 못 고침 0곳
     ↳ 하노이/호안끼엠 호수 이미지: 사진 설명을 관광지 이름으로 바꿨습니다 ('호안끼엠 호수')
   test_alt_english: PASS · 1/2회 → check_information (검사기로 복귀)
   check_information: SHORT · 부족 9곳 · 1바퀴 (처방 가지에서 복귀 — 바퀴를 쓰지 않음)
   diagnose_info: 처방 가지 대상 없음 → 루프 골격 그대로
   check_information: PASS · 부족 0곳 · 2바퀴
   diagnose_info: 처방 가지 대상 없음 → 루프 골격 그대로
   human_gate_a: stop
```

그 위 노드 줄에서는 `test_alt_english` 아래 `detour_verdict = PASS`, 다음 줄이 `check_information`,
`처방 가지   : fix_alt_english` 로 보인다. **복귀 줄의 바퀴 수가 그대로인지**(1바퀴 → 1바퀴) 짚어 준다.
`test_alt_english: PASS · 1/2회 → check_information (검사기로 복귀)` 를 그대로 읽기 5 "초록불" 과 `green_seen` 에 적는다.

### ⑧ 잠근다 — 회귀

```bash
python scripts/check_graph_shape.py                              # 12행 PASS · 11번 처방 가지 계약 OK
python scripts/selftest/run_graph_regression.py                   # 실패 0
python scripts/run_once.py --mode replay --auto stop --thread plain1      # 재현 없이 (루프 A) — "처방 가지   : 타지 않음"
python scripts/run_once.py --mode replay --auto proceed --thread plain2   # 재현 없이 (루프 B 는 반드시 이것)
```

- 회귀 테스트의 **통과 개수는 처방 가지 수에 따라 는다** (킷 기본 240개 → 가지 하나마다 11개씩, 하나를 더하면 251개).
  보는 것은 `실패 0` 이다. T14 가 **내 가지도** 같은 방식으로 돌려 본다 — 재현하면 진단 → fix → test,
  한 번에 합격, 검사기로 복귀, 바퀴를 안 씀, 시험지가 `travel_graph` 를 import 하지 않음. 재현 없는 실행은
  게이트 A 를 `proceed` 로 넘겨 게이트 B 까지 가도 가지를 한 번도 타지 않는지 본다 (루프 B 오탐까지).
  T15 는 킷 복사본을 아홉 가지로 망가뜨려 구조 검사 11번이 빨간불을 내는지 본다.
- 재현 없는 실행에서 가지가 켜지면 규칙 7(오탐) 위반이다. ⑥ 으로 돌아간다. **루프 B 가지의 오탐은
  `--auto stop` 으로는 안 보인다** — 게이트 A 에서 끝나 `diagnose_page` 까지 가지 않는다. `--auto proceed` 로
  돌려 `diagnose_page: 처방 가지 대상 없음 → 루프 골격 그대로` 와 `처방 가지   : 타지 않음` 을 본다.

### ⑧ 잠근다 — 기록

1. `specs/06_DETOUR.md` 읽기 5(`ANSWERS`)를 다 채웠는지 본다 (후보 줄 · 빨간불 · 초록불 줄 포함).
2. 읽기 2 · 읽기 6 의 `PROJECT` 표를 **실제 값**으로 채운다.
3. MACHINE `detour` 블록을 채운다. **빈칸(null)이 없어야** 한다. `decisions` 는 `{}` 그대로.
   `symptom_source` 에는 보고서 ③ · ③-2 의 후보 줄을, `red_seen` · `green_seen` 에는 `run_once.py` 끝의
   history 줄을 **그대로** 옮긴다.
4. `STATUS: APPROVED` 로 바꾸고 검사한다.

   ```bash
   python scripts/validate_specs.py --step 6        # PASS (exit 0)
   ```

   빈칸만 보는 것이 아니다 — `kind` 가 `registry.py` 에 있는지 · `loop` 가 `A`/`B` 인지 · 빈 문자열이 없는지 ·
   `red_seen` 에 `FAIL`, `green_seen` 에 `PASS` 가 있는지도 본다. 어긋나면 SHORT(exit 2)와 그 칸 이름이 나온다.
5. 결정 장부 `specs/00_DECISION_LOG.md` **6번(처방 가지 기록)** 표에 한 줄 남긴다 — 시각 · kind · 루프 · 증상 ·
   시험지 · 고치는 법 · 결과(빨간불 → 초록불 → 회귀). 1번 표(결정)에는 **적을 것이 없다** — 결정 0개다.
6. `PROJECT_MEMORY.md` 5번(겪은 문제와 해결)에 한 줄 남긴다.

아래는 **코드 모양 참고용 (가상 예)** `alt_english` 로 채운 모양이다. 실제 기록의 `symptom_source` 는 내 보고서의 줄이다.

```json
"detour": {
  "kind": "alt_english",
  "loop": "A",
  "title": "사진 설명이 영어로 나옴",
  "symptom_source": "코드 모양 참고용 (가상 예) — live 실행들에서 모델이 사진 설명(alt)을 영어로 적는 일이 되풀이됐다고 가정",
  "test_rule": "사진 자리 전부(국기 · 대표 · 관광지)의 alt 에 한글이 한 글자도 없으면 불합격. 빈 alt 는 루프 골격 검사기의 몫이라 보지 않음",
  "inject": "첫 도시 첫 관광지 사진 alt 를 'Photo of the main sight' 로 (INJECT_AT = city)",
  "fix_1": "alt 를 관광지 이름으로 (국가 소개는 '<국가> <칸 이름>')",
  "fix_2": "없음 — 대신 쓸 한국어 이름이 없으면 unfixed 로 남겨 게이트 A 로",
  "red_seen": "test_alt_english: FAIL · 2/2회 → human_gate_a",
  "green_seen": "test_alt_english: PASS · 1/2회 → check_information (검사기로 복귀)"
}
```

```text
00_DECISION_LOG 6번 한 줄 (예)
| 2026-09-27 18:56 | alt_english | A | 코드 모양 참고용 (가상 예) live 에서 사진 설명(alt)이 영어 | 사진 자리 전부의 alt 에 한글이 없으면 불합격 | alt 를 관광지 이름으로 → 없음(unfixed → 게이트 A) | FAIL 2/2 → 게이트 A · PASS 1/2 → check_information · 12행 PASS · 회귀 251 · 실패 0 · 재현 없이 0회 |

PROJECT_MEMORY 5번 한 줄 (예)
| 사진 설명(alt)이 영어로 나옴 | 모델이 alt 를 파일 이름처럼 영어로 적음 (검사기는 alt 가 "있는가"만 봄) | 처방 가지 alt_english — 시험지: alt 에 한글 · 고치는 법: 관광지 이름 (STEP 6) |
```

---

## 대표 예 — `image_dead` 가 가지가 된 실제 이력

킷의 가지 셋 중 `image_dead` 는 **로그에서 자란** 가지다. 여덟 걸음에 맞춰 보면 이렇다 — 교육생에게 이 순서로
보여 준다 (질문 ①~⑥ 의 예도 이것이다).

```text
① 돌린다   루프 킷 실행 (캐나다 7일) — verify_all 은 SUCCESS · exit 0
② 본다     graph/04_RUN_EVIDENCE.md 1-b "이미지 11장 전부 죽음 — 국기 400 · 대표 404 · 관광지 9장 404"
           모델이 쓴 주소   .../thumb/8/8c/Moraine_Lake_17092005.jpg/1280px-...   ->  404
           올바른 주소      .../thumb/c/c5/Moraine_Lake_17092005.jpg/1280px-...   ->  200   (틀린 것은 해시 두 글자뿐)
③ 묻는다   되풀이됐나 — 예. 해시는 파일 이름에서 파생되는 값이라 모델이 알아낼 방법이 없다.
           다시 모아도 또 지어낸다 (같은 파일 3번 — 이미지만 바퀴를 넘겨 "2바퀴 … 여전히 404")
④ 가른다   같은 입력에 같은 고칠 법이 있나 — 예. 파일 이름만 뽑아 해시가 필요 없는
           Special:FilePath/<파일>?width=1024 로 다시 쓴다 (실측에서 통한 고칠 법)
⑤ 만든다   registry.py 한 줄 · travel_graph/detours/image_dead.py · scripts/detour_tests/test_image_dead.py
⑥ 빨간불   inject() 가 실측 모양 그대로 재현 — upload.wikimedia.org/…/thumb/8/8c/<실제 파일>/1280px-<실제 파일> + 404
           → 시험지 불합격 (exit 2): 하노이/탕롱 황성 이미지: 손으로 만들 수 없는 주소 형태입니다 (upload.wikimedia.org). …
⑦ 초록불   fix_image_dead: 1/2회째 · 고침 1곳 · 못 고침 0곳
           test_image_dead: PASS · 1/2회 → check_information (검사기로 복귀)
⑧ 잠근다   구조 검사 11번 · 회귀 T14 (재현하면 진단 → fix → test · 재현 없으면 0회)
```

재수집(LLM)에 그대로 뒀다면 바퀴마다 토큰을 쓰고 또 지어냈을 실패를, 이제 진단이 알아보고 LLM 보다 먼저
규칙으로 받는다 (LLM 호출 0 · 바퀴 안 씀 · 처방 한도 2 → ★게이트). 나머지 둘의 출생은 다르다 —
`encoding` 은 원인과 고칠 법이 이미 알려진 실패 축(Windows cp949 · 현지 글자 파일명)이라 로그 실측 **전에**
미리 구축했고, `image_spec` 은 실습생이 게이트에 적은 지적(원본 크기 사진이 서랍을 뚫는다 — 검사기는 못 봄)에서
왔다 (`06_DETOUR.md` 읽기 3 (13)).

---

## 코드 모양 참고용 (가상 예) — `alt_english` (사진 설명이 영어로 나옴 · 루프 A)

**실제 로그에서 나온 가지가 아니다.** 세 조각을 채운 코드가 어떤 모양인지 보여 주려고 만든 가상 예다.
검사기는 사진 설명(`alt`)이 **비어 있는가**만 본다. 영어로 적혀 있어도 PASS 다 — **검사기가 세지
않는 실패**라 판정이 PASS 여도 진단이 잡는다. 아래 코드는 이 킷의 복사본에서 `new_detour.py` 로
만든 틀을 채워 실제로 돌려 본 것이다 (구조 검사 12행 PASS · 빨간불 · 초록불 · 회귀 251 · 실패 0).

**시험지** — `scripts/detour_tests/test_alt_english.py` (`from __future__` 줄 아래 전부. 틀과 다른 곳은
`_HANGUL` 한 줄과 `found` 를 채우는 네 줄(TODO 주석 자리)뿐이다 — `re` 와 `_common` 의 도구(`Result` · `assets` ·
`finish` · `main_for` · `read_html` · `read_research` · `walk_strings`)는 틀이 처음부터 import 한다.
`if __name__ == "__main__":` 두 줄도 틀 그대로 둔다)

```python
import re  # noqa: F401  — 글자 모양(예: 한글이 있나)을 볼 때 쓴다
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

#  시험지가 쓰는 도구는 전부 여기서 온다. 쓰지 않는 것이 있어도 지우지 않는다.
#    walk_strings(data)  모든 글 칸을 (이름표, 칸 이름, 값) 으로
#    assets(data)        모든 사진 자리를 (이름표, 사진 dict) 로
from _common import (  # noqa: E402, F401
    Result, assets, finish, main_for, read_html, read_research, walk_strings,
)

_HANGUL = re.compile("[가-힣]")                                # ← 추가


def run(root=None) -> Result:
    """처방 가지 시험지 — 사진 설명이 영어로 나옴"""
    result = Result("처방 가지 시험지 — 사진 설명이 영어로 나옴 (test_alt_english)")
    data, problem = read_research(root)
    if data is None:
        result.note_broken(problem)
        return result

    found = []                                                # ↓ 네 줄 추가 (TODO 주석 자리)
    for label, asset in assets(data):                         # 국기 · 대표 · 관광지 사진 자리 전부
        alt = str(asset.get("alt") or "").strip()
        if alt and not _HANGUL.search(alt):                   # 빈 alt 는 루프 골격 검사기의 몫
            found.append(f"{label}: 사진 설명에 한글이 없습니다 ('{alt[:40]}')")

    finish(result, "사진 설명이 영어로 나옴", found)
    return result
```

**모듈** — `travel_graph/detours/alt_english.py` (docstring 아래 전부. 맨 위 docstring 의 증상 ·
고치는 법 · 실패 재현 칸도 읽기 5 의 답으로 채운다. `fix()` 의 docstring 은 틀 그대로 둬도 된다)

```python
from __future__ import annotations

import re

KIND = "alt_english"
INJECT_AT = "city"                  # "city"(첫 도시) 또는 "country"(국가 소개)
HOWTO = ("사진 설명을 한국어로 바꿀 이름이 없습니다. `more` 를 고르고 note 에 "
         "'사진 설명(alt)은 한국어로 적어라'고 적으십시오")

_HANGUL = re.compile("[가-힣]")


def _images(data: dict):
    """사진 자리마다 (이름표, 자산 dict, 대신 쓸 한국어 이름)."""
    for slot, node in (data.get("country_intro") or {}).items():
        if isinstance(node, dict) and isinstance(node.get("asset"), dict):
            yield f"국가 소개/{slot}", node["asset"], f"{data.get('country')} {slot}"
    for city in data.get("cities") or []:
        for spot in (city.get("spots") or []) if isinstance(city, dict) else []:
            if isinstance(spot, dict) and isinstance(spot.get("image"), dict):
                yield (f"{city.get('name')}/{spot.get('name')} 이미지", spot["image"],
                       str(spot.get("name") or ""))


def fix(data: dict, *, attempt: int, mode: str) -> dict:
    fixed, unfixed = [], []
    for label, image, name in _images(data):
        alt = str(image.get("alt") or "").strip()
        if not alt or _HANGUL.search(alt):
            continue                            # 비었거나(루프 골격의 몫) 이미 한국어
        if _HANGUL.search(name):                # 1회째 — 관광지 이름(한국어)으로 바꾼다
            image["alt"] = name
            fixed.append(f"{label}: 사진 설명을 관광지 이름으로 바꿨습니다 ('{name}')")
        else:                                   # 2회째에 더 할 것이 없다 → 사람에게
            unfixed.append(f"{label}: 대신 쓸 한국어 이름이 없습니다")
    return {"fixed": fixed, "unfixed": unfixed}


def inject(city: dict) -> str:
    """첫 관광지 사진의 설명(alt)을 영어로 바꿔 그 실패를 재현한다."""
    for spot in city.get("spots") or []:
        image = spot.get("image") if isinstance(spot, dict) else None
        if isinstance(image, dict) and image.get("alt"):
            image["alt"] = "Photo of the main sight"
            return f"{city.get('name')}/{spot.get('name')} 사진 설명을 영어로"
    return ""
```

짚어 줄 것.

```text
시험지와 fix 가 같은 자리를 돈다       시험지의 assets() 는 국가 소개(국기 · 대표)와 관광지를 둘 다 돈다
                                     → fix 의 _images() 도 둘 다 돈다 (한쪽만 돌면 "계속 불합격"이 된다)
fix 는 data 를 그 자리에서 고친다      image["alt"] = … — 새 dict 를 만들어 돌려주지 않는다
                                     파일 쓰기 · 상태 되올리기는 nodes.fix_detour 가 한다
칸은 .get() · isinstance 로 읽는다     x["key"] 로 읽으면 없는 칸에서 KeyError — 그래프는 죽지 않지만
                                     fix 는 "못 고침: fix() 가 실행 중에 멈췄습니다", inject 는 "(재현하지 못함)" 이 된다
못 고친 곳은 unfixed 에 적는다          history 에 "↳ 못 고침: …" 으로 남는다. 비워 두면 "고침 0곳 · 못 고침 0곳" 만 남아
                                     사람이 왜 못 고쳤는지 모른다
시험지는 고치는 코드를 부르지 않는다    _HANGUL 을 양쪽에 따로 둔다. 시험지가 alt_english.py 를
                                     import 하면 11번이 잡는다 (판정 독립)
2회째가 없다                          attempt 를 보지 않는다. 한국어 이름이 없으면 사람에게 넘긴다
```

---

## 문제가 생기면

| 증상 | 원인 | 조치 |
| --- | --- | --- |
| 보고서 끝 줄이 `… STEP 6 은 하지 않아도 됩니다` | ③ · ③-2 에 후보가 없다 — 비었거나 `[일화]` 뿐 (replay 기본 실행은 비는 것이 정상) | **문제가 아니다.** "STEP 6 불필요"로 끝낸다 (진입 조건). 가지를 만들려고 실패를 지어내지 않는다 |
| `new_detour.py`: `x '<이름>' 는 라우터가 이미 쓰는 이름입니다` · `이미 등록돼 있습니다` · `이름은 영문 소문자로 시작하고…` | 예약어 · 중복 · 이름 규칙 | 다른 이름. 아무것도 만들어지지 않았으니 그대로 다시 실행 |
| `check_graph_shape` `[ERROR] 그래프를 불러오지 못했습니다: DetourRegistryError: registry.py 의 N번째 줄: …` | 등록부 줄을 손으로 고치다 틀림 (`loop` 가 A/B 가 아님 · title 빈칸 · 중복) | 그 줄을 `new_detour.py` 가 넣은 모양으로 되돌린다. **이 상태에서는 그래프 자체가 안 만들어진다** (Studio 도 못 불러온다) |
| `check_graph_shape` 가 표 대신 `SyntaxError` 추적을 내고 exit 1 | 모듈 `<이름>.py` 의 문법 오류 | `python -c "import travel_graph.detours.<이름>"` 로 줄 번호를 보고 고친다 |
| 11번 `모듈 — fix 의 모양이 fix(data, *, attempt, mode) 가 아닙니다` · `inject(obj) 함수가 없습니다` · `INJECT_AT 이 "city" 또는 "country" 가 아닙니다` | 틀의 함수 머리 · 상수를 지웠거나 바꿈 | 틀 모양 그대로 되살린다 (`*` 뒤 `attempt` · `mode` 는 키워드 전용) |
| 11번 `시험지가 travel_graph 를 import 합니다` | 시험지가 고치는 코드를 빌려 씀 | import 를 지우고 `_common` 도구(`read_research` · `read_html` · `assets` · `walk_strings`)로 다시 쓴다. 같은 규칙이 필요하면 시험지 안에 따로 적는다 |
| 11번 `모듈 … 가 없습니다` · `시험지 … 가 없습니다` | 등록부만 손으로 추가했거나 파일 이름이 `kind` 와 다름 | 이름을 맞춘다. `new_detour.py` 로 만들면 생기지 않는다 |
| 11번 `… 어디에도 없는 노드입니다` · `… 정적 간선 하나만` · `… 들어오는 곳은` · `… 뒤 매핑이 … 여야` · `… 루프 골격의 칸 … 에 씁니다` · `detour_limit 을 읽지 않습니다` | `build.py` · `edges.py` · `nodes.py`(보호 파일)가 바뀜 | **교육생이 고칠 곳이 아니다.** 바꾼 것을 되돌리고 사람에게 넘긴다 |
| **가지가 안 켜진다** — `history` 의 `diagnose_info: 처방 가지 대상 없음 → 루프 골격 그대로` (터미널에서는 `diagnose_info` 아래 `failure_kind =` 가 비어 있음) | ① `inject()` 가 아무것도 재현하지 않음 — `""` 를 돌려줌 · `INJECT_AT` 이 틀림 (Studio `history` 에 `↳ ⚠ 실패 재현 [<이름>]` 줄이 없다) · 예외 (`↳ ⚠ 실패 재현 [<이름>] 이 멈췄습니다 — … (재현하지 못함)`) ② 재현은 됐는데 시험지가 그 실패를 못 봄 ③ 루프 B 인데 `INJECT_AT = "city"` 로 바꿈 → replay 재수집이 도시를 되돌려 실패가 지워짐 (도시에만 있는 증상은 루프 B 로 재현 못 함) ④ 루프 B 인데 `--auto stop` 으로 돌림 → 게이트 A 에서 끝나 `diagnose_page` 까지 안 감 | ①② 아래 **손으로 확인하기** 로 "무엇을 재현했나"와 "시험지가 떨어뜨리나"를 따로 본다. 예외면 `.get()` 으로 읽는다. 실패 기록 `evidence/failures/<thread>.jsonl` 의 **첫 `diagnose_*` 줄** `symptoms` 에 `<이름>` 이 없어도 ② 다 (실행이 끝난 뒤의 output 은 재수집이 되돌려 놓았을 수 있어 혼자 돌린 시험지로는 판단하지 않는다) ③ `"country"` 로 되돌리고 국가 소개의 증상을 고른다 ④ `--auto proceed` |
| `diagnose_*: 증상은 있지만 처방 가지를 타지 않음 (<이름>: …)` | 처방 한도를 다 씀(`처방 한도 2/2 를 다 썼습니다`) · 정성 회차 중(루프 B) | 게이트 `② 왜` 의 `처방 가지가 못 고침 — <title>` · `처방 가지를 미룸 — <title> (정성 회차 중)` 줄을 읽는다. 미룸은 정상이다 (research · rebuild 면 다시 선다) |
| `diagnose_*: 시험지가 멈춘 처방 가지가 있음 — 시험지를 고치십시오 (<이름>: 시험지가 멈춤)` | **내 시험지가 실행 중에 터짐** — 증상이 아니다 | 게이트 `② 왜` 에 `처방 가지 시험지가 깨짐 — <title>` 이 뜬다. `python scripts/detour_tests/test_<이름>.py` 를 혼자 돌려 오류 줄을 고친다 (11번은 문법 · `run()` 만 보고 시험지 안의 실행 오류는 못 본다) |
| 다른 가지가 먼저 켜진다 | 등록 순서 = 진단 우선순위. 한 번에 하나씩 돈다 | `--inject` 에 내 가지 이름만 준다 |
| `모르는 처방 가지 이름: …` | `--inject` 철자 | 등록부의 `kind` 그대로 |
| 시험지를 혼자 돌렸더니 `[ERROR] … output/research_data.json 이 없습니다` · `output/travel_site.html 이 없습니다` (exit 1) | 그래프를 아직 이 폴더에서 돌리지 않아 output 이 없다 · 루프 B 인데 게이트 A 에서 끝난 실행뿐이라 화면이 없다 | 루프 A 는 `run_once.py --mode replay --auto stop`, 루프 B 는 `--auto proceed` 로 한 번 돌린 뒤 다시 |
| Studio 에 새 가지가 안 보인다 | `--no-reload` 로 켠 서버는 코드 변경을 다시 읽지 않는다 | 서버를 껐다 다시 켠다 (`graph-run` 7번 · 4번) |
| **계속 불합격** — `test_<이름>: FAIL · 2/2회 → human_gate_*` | ① `fix()` 가 받은 `data` 를 그 자리에서 안 고침 (`data = {...}` 로 새로 만듦) ② `fix()` 가 `output/` 파일을 직접 고침 → `fix_detour` 가 `data` 로 다시 써서 사라짐 ③ 시험지가 보는 자리와 `fix()` 가 도는 자리가 다름 ④ 정말 정해진 절차로 못 고치는 것 | ①②③ 은 `fix()` 를 고친다. ④ 는 **정상이다** — `unfixed` 로 적고 게이트(사람)로 넘긴다. **시험지를 약하게 만들지 않는다** |
| `fix_<이름>: … 고침 N곳` 인데도 FAIL | 시험지가 보는 자리가 `fix()` 보다 많다(위 ③) · 또는 시험지가 정상 값에서도 불합격을 낸다 (오탐) | 실패 기록의 `test_<이름>` 줄 `evidence` 에 남은 증상이 어느 자리인지 본다. 오탐이면 정상 output 에 시험지를 혼자 돌려 확인하고, 약하게가 아니라 **정확하게** 고친다 |
| 재현 없이도 가지가 켜진다 | 시험지 오탐 (규칙 7) | 위와 같다. 기록(⑧)으로 넘어가지 않는다 |
| `fix_<이름>: … 못 고침 1곳` 아래 `↳ 못 고침: fix() 가 실행 중에 멈췄습니다 — KeyError: …` · 또는 수집 줄 아래 `↳ ⚠ 실패 재현 [<이름>] 이 멈췄습니다 — KeyError: … (재현하지 못함)` | `fix()` · `inject()` 가 없는 칸을 `x["key"]` 로 읽음. **그래프는 죽지 않는다** — fix 는 못 고친 것으로 적혀 test FAIL → 한도면 게이트, inject 는 아무것도 재현하지 않는다 | `.get()` 과 `isinstance` 로 방어한다 (위 "코드 모양 참고용 예" · 킷의 `image_dead.py` 가 쓰는 방식) |
| 같은 자리에 `SyntaxError` · `ImportError` 가 뜨고, 게이트 `고치려면` 칸이 `처방 가지 모듈을 불러오지 못했습니다 — …` | 모듈은 재현하거나 가지가 켜질 때 처음 불린다. 재현 없는 실행에서는 안 보인다 | `python -c "import travel_graph.detours.<이름>"` 로 줄 번호를 보고 고친다 |
| 회귀 T14 `[<이름>] 시험에 한 번에 합격하고 … 로 돌아간다` 실패 | 1회째 절차가 replay 에서 안 됨 (live 전용) | 1회째를 replay 에서 되는 절차로. live 전용은 2회째로 |
| 회귀 T14 `[<이름>] 재현하면 diagnose_* → fix_* → test_*` 실패 | 재현이 안 먹음 | 위 **가지가 안 켜진다** |
| `validate_specs --step 6` ERROR `결정이 0개여야 하는데 N개입니다` · `MACHINE 에 detour 블록이 없습니다` | `decisions` 에 키를 넣음 · `detour` 블록을 지움 | `"decisions": {}` 로 되돌리고 `detour` 블록을 되살린다 |

### 손으로 확인하기 (루프 A) — 인계본에 그 실패를 재현하고 시험지만 풀어 본다

그래프를 돌리지 않고 **"무엇을 재현했나"** 와 **"시험지가 떨어뜨리나"** 를 따로 본다. 인계본
(`graph/research_data.json`)을 임시 폴더에 옮겨 시험지에 `--root` 로 준다. 킷 파일은 건드리지 않는다.
아래는 bash(Git Bash) heredoc 이다 — PowerShell 이면 가운데 파이썬 부분을 임시 파일로 저장해 `python <파일> planted` 로 돌린다.

```bash
python - planted <<'EOF'
import json, shutil, subprocess, sys, tempfile
from pathlib import Path
from travel_graph.detours import alt_english as m                     # ← 내 가지 이름
data = json.loads(Path("graph/research_data.json").read_text(encoding="utf-8"))   # 정상 인계본
if sys.argv[1:] == ["planted"]:
    target = data["cities"][0] if m.INJECT_AT == "city" else data["country_intro"]
    print("재현한 것:", m.inject(target) or "(아무것도 재현하지 않음)", flush=True)
root = Path(tempfile.mkdtemp())
(root / "output").mkdir()
(root / "graph").mkdir()
shutil.copy("graph/03_CONTRACT.json", root / "graph")
(root / "output" / "research_data.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
sys.exit(subprocess.run([sys.executable, f"scripts/detour_tests/test_{m.KIND}.py", "--root", str(root)]).returncode)
EOF
```

```text
python - planted …   재현한 것: … 이 찍히고 시험지 exit 2    ← 그 실패를 재현하고, 시험지가 잡는다
python - clean …     (planted 대신 clean) 시험지 exit 0      ← 정상 인계본에서 합격 — 오탐 없음 (규칙 7)
"재현한 것: (아무것도 재현하지 않음)"                       ← inject() 가 찾는 자리가 틀렸다
재현했는데 exit 0                                           ← 시험지가 그 실패를 못 본다
```

루프 B 가지는 시험지가 화면(HTML)을 읽으므로 이 방법으로는 못 본다. `--inject` 로 그래프를 돌려 확인한다.

---

## 끝나면 넘기는 곳

| 상황 | 다음 |
| --- | --- |
| 후보가 없다 — "STEP 6 불필요" | `evidence-review` — 이 실행의 증거 정리. `06_DETOUR.md` 는 DRAFT 그대로 |
| 가지 완성 (`validate_specs --step 6` PASS) | `evidence-review` — 이 실행의 증거 정리. 가지가 켜진 실행이면 그 줄도 보고서에 |
| 되풀이된 다른 실패로 하나 더 | `graph-detour-builder` 재호출. 등록 순서가 진단 우선순위다 |
| 강사 — 여러 교육생의 기록을 모아 본다 | `python scripts/failure_report.py <폴더>…` → `[패턴 — 킷 처방 가지 후보]`(실행 3곳 이상)만 킷 저자에게 |
| 이미 승인된 결정(STEP 1~5)을 바꾸자고 함 | `spec-sync` |
| 보호 파일을 고쳐야 한다는 결론 | 고치지 않고 사람에게 넘긴다 |
