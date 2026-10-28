---
name: graph-run
description: 완성된 그래프를 실행한다. "그래프 돌려줘", "Studio 켜줘", "langgraph dev 실행", "이어서 돌려줘" 같은 요청에서 사용한다. 게이트에서 멈추면 사람의 답을 받아 재개하고, 끝나면 최종 검증까지 한다.
user-invocable: true
argument-hint: "[replay | live]"
---

# graph-run — 그래프 실행 진행자

## 활성화 조건

STEP 5가 `APPROVED` 이고 `check_graph_readiness.py` 가 `READY` 일 때.
아직 아니면 **켜지 않고** 무엇이 남았는지 알려 준다.

---

## 절대 규칙 8가지

1. **`langgraph dev` 는 블로킹 프로세스다.** 반드시 백그라운드로 띄우고,
   확인이 끝나면 **반드시 종료**한다. 켜 둔 채 방치하지 않는다.
2. **`--no-reload` 를 반드시 붙인다.** 감시 기능은 `*.py` 만 본다(`output/` 의 json · html 쓰기로는
   재시작하지 않는다). 실행 중 `.py` 가 바뀌면(코드 수정 · STEP 6 의 `new_detour.py`) 서버가 다시 떠
   **돌던 run 이 끊긴다.** 그 대신 새 코드는 서버를 직접 다시 켜야 반영된다.
3. **게이트에서 사람 대신 답하지 않는다.** 답을 받을 때까지 기다린다.
4. 게이트 현황을 보여 줄 때 **못 채운 칸을 숨기지 않는다.**
5. **선택지 없이 "어떻게 할까요?" 라고 묻지 않는다.** 선택지와 각각의 결과를 함께 준다.
6. `live` 가 `replay` 로 폴백했으면 **반드시 보고한다.** live 결과인 척하지 않는다.
7. 종료 코드만이 근거다. "잘 된 것 같습니다" 는 근거가 아니다.
8. **API 키를 화면에 원문으로 출력하지 않는다.**

---

## 실행 순서

### 1) 사전 점검

```bash
python scripts/check_graph_readiness.py     # READY (exit 0)
python scripts/check_graph_shape.py         # PASS  (exit 0) — 검사행 12개 (11 = 처방 가지 계약)
```

둘 다 통과가 아니면 **여기서 멈추고** 무엇이 남았는지 표로 알려 준다.

`live` 로 돌릴 거라면 **한 줄 더** 잰다. 30~60초 걸리지만, 이것을 건너뛰면
`live` 가 조용히 `replay` 로 내려가는 것을 실행이 끝난 뒤에야 알게 된다.

```bash
python settings/scripts/verify_env.py       # C12 = live 웹검색 실측
```

`C12` 가 `FAIL` 이면 `live` 를 권하지 않는다. 원인을 그대로 전하고
`replay` 로 돌릴지 묻는다. **"아마 될 겁니다"라고 말하지 않는다.**

### 2) 모드 정하기

| 상황 | 모드 | 이유 |
| --- | --- | --- |
| 기본 | `live` | 실제 조사. 병렬 이득이 진짜로 측정된다 |
| 남은 시간이 15분 미만 | `replay` | 10초. 게이트 실습에 시간을 쓸 수 있다 |
| 네트워크·`claude` 인증이 막힘 | `replay` | live 는 어차피 폴백된다 |
| 처방 가지 관찰 (실패 재현 `inject`) | `replay` | 결과가 항상 같아 재현한 실패 말고 다른 증상이 섞이지 않는다. 처방 가지가 켜지는 것만 보면 된다 |

교육생에게 **남은 시간을 묻고** 권한다.

### 3) 빠른 확인이면 터미널로

```bash
python scripts/run_once.py --mode replay --auto stop      # 루프 A 만 — 게이트 A 에서 끝
python scripts/run_once.py --mode replay --auto proceed   # 루프 B 까지 — 게이트 A 통과 → 게이트 B 에서 스스로 멈춘다
python scripts/run_once.py --mode replay --inject image_dead --auto stop   # 처방 가지 관찰 — 그 실패를 재현해 가지를 켠다
```

**에이전트가 돌릴 때는 `--auto` 를 반드시 준다** (구조 · 처방 가지 확인용 실행이다. 실습 실행의
게이트 답은 사람에게 받는다 — 규칙 3). `run_once.py` 는 답이 없으면 권장값으로
넘어가지 않고 **그 게이트에서 끝낸다** — `--auto` 답을 다 썼으면 `(--auto) 답을 다 썼습니다 —
이 게이트에서 끝냅니다.`, 표준입력이 터미널이 아니면 `표준입력이 터미널이 아닙니다 — 권장값으로
넘어가지 않고 이 게이트에서 끝냅니다.`, 입력이 EOF 면 `입력이 없습니다 — 이 게이트에서 끝냅니다.`
를 찍고, 요약 줄에 `사람 호출 : 2회 — human_gate_a → human_gate_b   (human_gate_b 에서 답 없이
끝냄)` 처럼 남긴다. 그래서 `--auto proceed` 는 정성 3회(`claude -p`, 6~12분)에 들어가지 않는다.
게이트 B 에 `done` 을 주는 것(`--auto proceed,done`)은 **정성 3회를 실제로 돌리겠다**는 뜻이다.
끝에는 `history — 검사기 · 진단 · 처방 가지 · 게이트 줄만` 이 그대로 찍힌다 — 보고서 · 06_DETOUR 의
기록은 여기서 옮겨 적는다.

**`--inject` 는 평소에 쓰지 않는다.** 실패 재현(inject)은 이미 있는 처방 가지가 켜지는 것을 보거나,
STEP 6 에서 새 가지의 시험지 빨간불을 먼저 볼 때 그 실패를 다시 일으키는 장치다. `replay` 에서
재현이 없으면 처방 가지는 **한 번도 켜지지 않는다** (루프 골격 그대로 · 진단 노드만 매번 돈다).
(`live` 는 실제로 모은 사진 주소가 죽어 있으면 재현 없이도 `image_dead` 가 켜질 수 있다 — 그것이
가지의 본래 일이다.) 이름은 `travel_graph/detours/registry.py` 에 있다 (`encoding` · `image_dead` ·
`image_spec`, 쉼표로 여럿). **replay 로 돌리는 것을 권한다** — live 는 수집 결과가 매번 달라, 재현한
실패 말고 다른 증상이 섞여 무엇이 가지를 켰는지 흐려진다.

> 실패 재현과 `--auto` 를 같이 쓸 때 — 처방 가지가 한도를 다 쓰면 그 루프의 게이트에 서므로
> (루프 A 는 재수집 전에 **일찍**) 미리 준 답이 하나씩 밀릴 수 있다. 답이 모자라면 그 게이트에서
> 끝나므로 위험하지 않다. 답을 더 줄 때는 게이트 B 에 `done` 이 가지 않게 순서를 맞춘다.
>
> 처방 가지 관찰(`--inject image_dead --auto stop`)의 history 는 이렇게 나온다 (replay 실측).
>
> ```text
> check_information: SHORT · 부족 12곳 · 1바퀴
> diagnose_info: ▷ 이미지 주소가 죽어 있음 — 증상 1곳 → 처방 가지 fix_image_dead (1/2회째)
> fix_image_dead: 1/2회째 · 고침 1곳 · 못 고침 0곳
>   ↳ 하노이/탕롱 황성 이미지: 해시가 든 주소를 권장 형태로 바로잡았습니다 (Special:FilePath/Central_Sector_of_the_Imperial_Citadel_o)
> test_image_dead: PASS · 1/2회 → check_information (검사기로 복귀)
> check_information: SHORT · 부족 9곳 · 1바퀴 (처방 가지에서 복귀 — 바퀴를 쓰지 않음)
> diagnose_info: 처방 가지 대상 없음 → 루프 골격 그대로
> check_information: PASS · 부족 0곳 · 2바퀴
> diagnose_info: 처방 가지 대상 없음 → 루프 골격 그대로
> human_gate_a: stop
> ```
>
> 부족 12곳 → 9곳이 재현한 한 장(해시 두 글자 `8/8c` 를 지어낸 upload 주소 · 404)의 세 줄이
> 사라진 것이고, 복귀한 검사기 줄이 `1바퀴` 그대로인 것이 "바퀴를 쓰지 않음"이다.

### 4) 관찰이 목적이면 Studio

**블로킹 프로세스다(규칙 1). 백그라운드로 띄우고 PID 를 받아 둔다.**
작업 디렉터리는 `langgraph.json` 이 있는 **프로젝트 루트**여야 한다.

> 에이전트라면 Bash 도구의 **백그라운드 실행**을 쓰고 **작업 ID 를 기억**한다.
> 아래는 교육생이 손으로 띄울 때의 명령이다.

```powershell
# Windows — 서버 로그를 evidence\ 에 남긴다 (Traceback 을 찾을 곳)
New-Item -ItemType Directory -Force evidence | Out-Null
$srv = Start-Process -PassThru -WindowStyle Hidden `
    -FilePath ".venv\Scripts\langgraph.exe" `
    -ArgumentList "dev","--no-browser","--no-reload","--port","2024","--host","127.0.0.1" `
    -RedirectStandardOutput "evidence\langgraph_dev.out.log" `
    -RedirectStandardError "evidence\langgraph_dev.err.log"
"PID = $($srv.Id)"
```
```bash
# macOS / Linux — 서버 로그를 evidence/ 에 남긴다
mkdir -p evidence
.venv/bin/langgraph dev --no-browser --no-reload --port 2024 --host 127.0.0.1 \
    > evidence/langgraph_dev.log 2>&1 &
echo "PID = $!"
```

기동에 **10~30초** 걸린다. `http://127.0.0.1:2024/ok` 가 **200** 이 될 때까지
몇 초 간격으로 확인하고, 그 뒤에 아래를 안내한다.

서버 로그는 **실행이 이상할 때 마지막에 보는 곳**이다 — 노드가 예외로 죽으면 Traceback 이 여기 남는다
(Windows 는 두 파일을 다 본다 — 서버 로그 본문은 `evidence\langgraph_dev.out.log`, 표준 오류로 나간 것은
`evidence\langgraph_dev.err.log`. macOS / Linux 는 `evidence/langgraph_dev.log` 하나).
에이전트가 백그라운드 실행으로 띄웠다면 그 작업의 출력이 곧 서버 로그다.

```text
Studio    https://smith.langchain.com/studio?baseUrl=http://127.0.0.1:2024

입력칸에 {} 만 넣고 Submit 하시면 됩니다.
(read_request 가 graph/03_CONTRACT.json 값으로 채웁니다)
처방 가지가 켜지는 것을 보려면 {"inject": ["image_dead"]} 를 넣습니다 (실패 재현).
평소에는 inject 칸을 비웁니다.

볼 것 6가지
  ① collect_country 와 select_cities 가 **동시에** 켜진다
  ② collect_city 3개가 **동시에** 켜진다      ← 병렬. 루프에는 없던 그림
     (collect_city 는 같은 걸음의 collect_country 가 끝나야 시작한다 — live 면 몇 분)
  ③ check_information → diagnose_info 뒤에서 길 하나가 골라진다   ← 라우터가 상태를 읽은 결과
     재수집은 repair_city ×N 과 repair_country ×0|1 이 **함께** 간다
     → 다음 check_information 은 그 갈래가 **모두** 끝난 뒤 한 번 켜진다 (한 걸음 = superstep)
       live 면 가장 느린 갈래(보통 2~6분)를 기다리는 동안 패널에 안 보인다 — 정상
  ④ quality_pass 3개가 **겹치지 않고 차례로** 켜진다  ← 고정 예산 순환. 순차가 정상
  ⑤ 검사기 바로 뒤에 진단 노드(diagnose_info · diagnose_page)가 **매번** 켜진다
     ← 판정(기준을 채웠나) 다음에 원인(무엇이 터졌나). 그 실패가 없으면 "루프 골격 그대로"
  ⑥ (그 실패가 났거나 재현했을 때만) 처방 가지 fix_<이름> → test_<이름> 이 켜지고 **검사기로 돌아온다**
     ← history 에 "(처방 가지에서 복귀 — 바퀴를 쓰지 않음)" 이 찍힌다
```

⑤ 는 재현이 없어도 보인다. ⑥ 은 **그 실패가 났을 때만** 보인다 — `replay` 기본 실행에서
처방 가지가 안 켜지는 것이 정상이다. 교육생이 "fix 노드가 한 번도 안 켜져요"라고 하면 그렇게 답한다.

**③ 에서 "재수집 뒤 check_information 이 안 보인다"고 하면** 먼저 기다리게 하고, 오래 걸리면 이 순서로 본다.

```text
1  LangSmith     열려 있는(끝나지 않은) claude -p · repair_* run 이 있나 — 있으면 그 갈래를 기다리는 중
2  상태          curl.exe -s http://127.0.0.1:2024/threads/<tid>/state — next · tasks 에 무엇이 남았나
3  run 상태      curl.exe -s http://127.0.0.1:2024/threads/<tid>/runs — status 가 running · error · success 중 무엇인가
4  서버 로그     evidence\langgraph_dev.out.log · .err.log (macOS / Linux 는 evidence/langgraph_dev.log) 의 Traceback
```

history 에 `check_information: … 2바퀴` 줄이 있으면 검사기는 돌았다 — 패널에서 놓친 것이다.
`diagnose_info` 입구는 `check_information` 하나뿐이라, 두 번째 `diagnose_info` 나 게이트 A 를 봤다면
검사기는 반드시 돌았다.

### 5) ★ 게이트에서 — 여기가 본편

그래프가 멈추면 **payload 를 표로 정리해서** 보여 준다.

**세 정지 지점이 같은 5키 화면을 쓴다.** 키 순서가 곧 읽는 순서다.

> **`⑤ 답` 의 `note` 는 비어 있지 않다.** 화면이 `② 왜` 의 원인에 맞는 지시문을
> 미리 채워 준다. 그대로 써도 되고 고쳐 써도 된다. **비워 두면 재수집 프롬프트가
> 지난 바퀴와 똑같아져 같은 결과가 나온다** — 실측에서 그랬다.


```text
① 지금    루프 A(정보량) · SHORT · 2/3바퀴 · 못 채운 칸 40곳 · 같은 오류 반복 0/2

② 왜      (목록이 아니라 요약이다. 40곳이 실제로는 서너 종류에서 나온다)
          원인      이미지 주소가 죽어 있음        몇 곳  27 / 40
          고치려면  정보가 없어서가 아니라 주소가 틀려서입니다. `지시문` 에 고칠 방향을 적으십시오
          예        다낭/한강다리 이미지: 목표 살아 있는 이미지 1 / 실제 부족

③ 권장    more — 부족의 대부분이 이미지 주소 한 종류입니다. 정보가 없어서가 아니라 주소가
          틀려서입니다. `⑤ 답` 의 `note` 에 고칠 방향을 적어 `more` 를 고르면 한 바퀴에 붙는
          경우가 많습니다

④ 고르기  more     지적된 것만 다시 모읍니다 · 도시: 다낭 — 지적이 없는 곳은 호출조차 하지 않습니다
          proceed  부족해도 페이지를 만듭니다 (못 채운 칸은 보고서에 남습니다)
          stop     여기서 멈춥니다 (END)

⑤ 답      {"action": "more", "note": "이미지는 영문 파일명을 우선 쓰고
                                       Commons 에서 실제로 확인한 것만 써라"}
```

**`② 왜` 를 먼저 읽는다.** 못 채운 칸 목록 열 줄이 아니라 이 요약이 판단 재료다.
원본이 필요하면 `research_path` 가 가리키는 파일을 연다.

> **사진 한 장이 비면 검사기는 세 줄을 낸다** (`…: 목표 살아 있는 이미지 1 / 실제 부족` ·
> `url 이 없습니다` · `alt 가 없습니다`). 원인 묶기는 같은 칸에 `url 이 없습니다` 가 있으면 세 줄을
> 모두 `이미지를 아직 안 모음` 으로 센다 — 재현 없는 replay 첫 바퀴는 `이미지를 아직 안 모음 9 / 9`.
> `이미지 주소가 죽어 있음` 은 **주소가 있는데 열리지 않는** 사진만이고, `image_dead` 처방 가지도
> 그 사진만 맡는다.

**수집이 실패한 도시는 `② 왜` 에 따로 뜬다.** `관광지 수 3/0`(부족)과
`후에 — 수집 실패`(그 도시를 아예 못 모음)는 판단이 완전히 다르다.

**`② 왜` 맨 앞에 `처방 가지…` 줄이 뜨면** 정해진 고칠 법(규칙 처방 가지)으로 끝나지 않은 문제가
있다는 뜻이다. 줄은 세 종류다 (`nodes._detour_lines`).

```text
처방 가지가 못 고침 — <title>                 fix 를 처방 한도(detour_limit 2회)까지 써 보고도 시험지 불합격
                                              (또는 한도를 이미 다 써서 진단이 건너뜀). 몇 곳 = 증상 수
처방 가지 시험지가 깨짐 — <title>             교육생 시험지가 실행 중에 멈춤 — 증상이 아니다. 몇 곳 = 시험지 오류
처방 가지를 미룸 — <title> (정성 회차 중)     정성이 시작된 뒤라 루프 B 가지를 미룸 (해시 사슬 보호)
```

처방 가지가 한도를 다 쓰면 **그 루프의 게이트**(A 가지 → 게이트 A · B 가지 → 게이트 B)에
선다 (루프 A 는 재수집 전에 일찍). 아래는 `image_dead` 의 고치는 법을 일부러 망가뜨린 복사본에서
`--inject image_dead` 로 그 실패를 재현해 띄운 화면이다 (replay).

```text
② 왜      원인      처방 가지가 못 고침 — 이미지 주소가 죽어 있음      몇 곳  1곳
          고치려면  정해진 절차(주소 형태 바로잡기 · 인계본 사진 · 검색)로도 살아 있는 사진을
                    못 찾았습니다. `more` 를 고르면 재수집이 note 대로 다시 찾습니다 —
                    'Commons 에서 실제로 확인한 파일 이름만 써라'고 적으십시오
          예        [image_dead] 죽은 이미지 주소: 목표 0 / 실제 1
```

교육생에게는 이렇게 전한다.

- **"더 모으면 되는 부족"과 다른 줄이다.** 정해진 절차로도 안 된 문제라 사람이 알아야 한다.
- `③ 권장` 을 그대로 읽어 준다. **줄 종류에 맞춰 계산된 값이다** (`_recommend_a` · `_recommend_b`).

  ```text
                             게이트 A                                    게이트 B
  처방 가지가 못 고침        부족이 남았으면 more (한도도 새로 채워짐),  done — '고치려면' 칸을 따른다 (데이터로
                             검사기가 세는 부족이 없으면 proceed         고칠 수 있으면 rebuild · research,
                                                                         화면 코드 문제면 보고서에 남기고 done)
  처방 가지 시험지가 깨짐    proceed — STEP 6 에서 시험지를 고친다       done — 같음
  처방 가지를 미룸           (루프 B 만)                                 done — 정성을 이어 간다. research ·
                                                                         rebuild 면 정성이 0 이 되고 가지가 다시 선다
  ```

  어느 가지의 이유를 다른 가지에 붙이지 않는다 — 구체적인 고칠 법은 `고치려면` 칸(그 가지
  모듈의 `HOWTO`)에 있다.
- `more`(A) · `research` · `rebuild`(B) 를 고르면 **처방 한도가 새로 채워진다**
  (`detour_attempts` → `{}`). history 에 `human_gate_a: 처방 한도를 새로 채웁니다` /
  `human_gate_b: 처방 한도를 새로 채웁니다` 가 남는다. 바깥 루프는 사람 소유라서다. 재수집 ·
  재생성이 데이터를 바꾼 뒤 처방 가지가 다시 설 수 있다. `proceed` · `stop` · `done` 은 그대로 둔다.
- 증상 원문은 실패 기록 `evidence/failures/<thread_id>.jsonl` 에 있다. 같은 실패가 로그에 반복되면
  (`failure_report.py` ③ · ③-2 의 후보) 그때 STEP 6 에서 가지로 뺀다.
- **정성(루프 C)이 한 회차라도 돈 뒤에는 루프 B 가지를 타지 않는다** (파일 해시 사슬 보호).
  history 에는 `diagnose_page: 증상은 있지만 처방 가지를 타지 않음 (image_spec: 정성 회차 중 — 파일
  해시 사슬을 지키려고 미룸) → 루프 골격 그대로`, 게이트 `② 왜` 에는 `처방 가지를 미룸 — <title> (정성
  회차 중)` 으로 뜬다. 실패 기록에는 `"failure_kind": ""` · `"decision": "루프 골격 그대로"` 와 증상
  (`symptoms` 의 `why` 에 미룬 이유)이 남는다 — 실패가 아니다. 게이트 B 에서 `research` ·
  `rebuild` 를 고르면 정성 회차가 0 이 되므로 그때부터 다시 탈 수 있다.

게이트 B는 선택지가 다르고 **두 번 선다.** 화면 `① 지금` 줄의 `정성 n/3회` 로 구분해 안내한다.

```text
[게이트 B] ① 지금 줄의 "정성 0/3" 일 때

   research  정보가 모자랍니다 → check_information 으로. 다시 세고 다친 도시만 모읍니다
   rebuild   화면이 모자랍니다 → rebuilder 가 **note 에 적은 지시대로** 고칩니다
   done      정성 점검 3회를 시작합니다   → 대개 이쪽

[게이트 B] "정성 3/3" 일 때

   research / rebuild  → **정성 회차가 0으로 되돌아갑니다** (결과물을 다시 만들기 때문)
   done                확정하고 끝                → 대개 이쪽
```

> **`rebuild` 를 고를 때는 `note` 를 반드시 받아 적는다.** 그 문장이 곧 수정 지시다.
> 비워 두면 `rebuilder` 가 고칠 방향이 없어 아무것도 하지 않는다.
> `rebuilder` 는 `output/research_data.json` 을 고쳐 화면을 다시 만든다 —
> HTML 만 손대면 다음 `build_page` 에서 날아가기 때문이다.
> **계약을 낮추라는 지시(글자 수 기준을 낮춰라 등)는 거부한다.**

**`research` · `rebuild` 를 고르기 전에 회차가 0으로 되돌아간다는 사실을 반드시 알린다.**

답을 받으면 `specs/00_DECISION_LOG.md` 4번 게이트 답 기록에 남긴다.

### 5-b) 루프 C — 정성 3회 (사람이 답할 것이 없다)

게이트 B에서 `done` 을 고르면 `quality_pass ↔ check_quality` 순환이 세 번 돈다.
**사람은 기다리기만 한다.** 다만 아래를 안내한다.

```text
회차 1  내용이 실한가          Q-반복금지 · Q-취향연결 · Q-뺀이유 · Q-상세삼요소
회차 2  실행 가능하고 사실인가   Q-일정현실성 · Q-근거일치 · Q-도시차별화 · Q-실용누락
회차 3  독자 관점에서 완결인가   Q-동행반영 · Q-계약무결

한 회차 2~4분 (claude -p 판정 + 수정 + 되돌아감 확인). 세 회차면 6~12분입니다.
기록은 evidence/runs/<run_id>/quality/pass1~3.json 에 남습니다.
```

회차가 끝날 때마다 `history` 의 줄을 그대로 보고한다. **고치지 못한 위반이 있으면
숨기지 않는다** — `passN.json` 의 `skipped_fix` 에 이유가 있다.

`check_quality` 가 `ERROR` 를 내면 `blocked.json` 을 열어 이유를 그대로 전한다.
`claude` 를 부르지 못한 경우가 대부분이며, **모의 판정으로 통과시키지 않는다.**

### 6) 끝나면 최종 검증

```bash
python scripts/verify_all.py
```

`[정성]` 이 SHORT 면 두 경우를 구분해 보고한다.

```text
"N회차 기록이 아직 없습니다"      아직 덜 돌았다 → 그래프를 더 돌린다
"위반이라 적고 고치지 않았습니다"   판정은 했는데 수정이 적용되지 않았다
                                → passN.json 의 skipped_fix 를 그대로 인용한다
```

### 7) 서버 종료

**반드시 끈다.** 남기면 포트 2024가 점유되어 다음 실행이 `[WinError 10048]` /
`Address already in use` 로 실패한다. 에이전트라면 4)에서 기억해 둔 백그라운드
작업을 정지시킨다.

```powershell
# Windows — PID 를 알 때 / 잃어버렸을 때
Stop-Process -Id <PID> -Force
Get-NetTCPConnection -LocalPort 2024 -State Listen |
    Select-Object -ExpandProperty OwningProcess |
    ForEach-Object { Stop-Process -Id $_ -Force }
```
```bash
# macOS / Linux — PID 를 알 때 / 잃어버렸을 때
kill <PID>
lsof -ti tcp:2024 | xargs kill
```

`/ok` 가 **200이 아닌 값**을 내면 종료된 것이다.

> **서버를 껐다 켜도 스레드는 대개 남는다.** `langgraph dev` 는 실행한 폴더의 `.langgraph_api/` 에
> 스레드와 체크포인트를 10초마다 저장했다가 다시 켤 때 불러온다 (끄기 직전 10초 안의 변화만 잃을 수
> 있다). 처음부터 깨끗하게 시작하려면 `settings/SETUP.md` D-3 을 따른다.

---

## 완료 보고 형식 (CLAUDE.md 12절)

```text
상태        : SUCCESS
실행 모드   : replay          ← 폴백했으면 "live→replay 폴백" 이라고 적는다
thread_id   : vietnam-5d-run1
루프 A      : 2바퀴  판정 PASS
루프 B      : 1바퀴  판정 PASS
루프 C      : 3/3회  판정 PASS   ← 고치지 못한 위반이 있으면 그대로 적는다
게이트      : A=proceed  B=done  C=done   ← 처방 가지가 한도를 다 써 게이트에 더 섰으면 그 정지도 적는다
처방 가지   : 타지 않음         ← 탔으면 결과까지: "image_dead 1회 → PASS → check_information 복귀",
                                   "image_spec 2/2회 FAIL → 게이트 B". 재현한 실행이면 "(재현: image_dead)" 를 붙인다
실패 기록   : evidence/failures/vietnam-5d-run1.jsonl
구조 검사   : exit 0
최종 명령   : python scripts/verify_all.py  exit 0
채운 칸     : 전부
못 채운 칸  : 없음
결과물      : output/travel_site.html

루프판 대비
  반복        8        →  (측정값)  ← 처방 가지는 바퀴로 세지 않는다. 같은 뜻으로 비교된다
  시간        40분     →  (측정값)
  재실행 범위  바퀴 전체 →  노드 단위
  사람 호출   2        →  3        ← 3 이 정상 — 게이트 A 1 · B 2 (루프판 2 에 정성 뒤 확정이
                                     하나 더). 처방 가지가 한도를 다 쓰면 그 루프의 게이트에 서고, 거기서
                                     more · research · rebuild 를 고르면 같은 게이트에 한 번 더 선다 (그런
                                     정지 하나마다 +1). 늘어난 수와 이유를 적는다
  정성 회차   3/3      →  3/3      ← 고정 예산. 빨라지지 않는다
  못 채운 칸  0건      →  0건      ← 같아야 정상. 다만 주소가 틀려 못 채운 칸(image_dead)은
                                     처방 가지가 줄일 수 있다 — 없던 사진이 생기는 것은 아니다
```

`처방 가지` 줄은 `run_once.py` 끝의 `처방 가지   :` 줄(탄 가지의 `fix_<이름>` 이 차례로 찍힌다)과
`history — …` 의 `fix_<이름>` · `test_<이름>` 줄에서 결과까지 옮긴다 (Studio 면 결과 패널의 `history`). 사람 호출 수는 `run_once.py` 의
`사람 호출 : N회 — human_gate_a → …` 줄 그대로다 — `(… 에서 답 없이 끝냄)` 이 붙었으면 그 게이트에서
멈춘 것이지 답한 것이 아니다. `실패 기록` 은 `python scripts/failure_report.py` 로 읽는다.

---

## 문제가 생기면

| 증상 | 조치 |
| --- | --- |
| `InvalidUpdateError` | STEP 4 미완료. `graph-spec-builder` 로 |
| 게이트에서 안 멈춤 | STEP 5 미완료 |
| 실행 중 서버 재시작 | `--no-reload` 누락. 감시는 `*.py` 만 보므로 실행 중 코드 수정 · `new_detour.py` 가 서버를 다시 띄워 돌던 run 이 끊긴다 |
| 재수집 뒤 `check_information` 이 안 보임 | **가장 느린 갈래 대기 — 정상 (superstep 장벽).** `repair_city ×k` · `repair_country` 가 한 걸음에서 나란히 돌고, `check_information` 은 그 갈래가 **모두** 끝난 뒤 한 번 켜진다 (live 한 갈래 = `claude -p` 1회 + 바뀐 사진 재확인 → 보통 2~6분, 최악 10분+). 확인 순서: LangSmith 의 열린 `claude -p · repair_*` → `curl.exe -s http://127.0.0.1:2024/threads/<tid>/state` 의 `next` · `tasks` → `/threads/<tid>/runs` 의 `status` → 서버 로그 Traceback. history 에 `check_information: … 2바퀴` 줄이 있으면 검사기는 돌았다 (패널에서 놓친 것) — 실행 순서 4) |
| `check_information` run 이 빨간색 · 스택이 검사기 `.strip()` | 재수집 patch 가 칸의 형을 바꿨다 (K1 — 글자 칸에 목록 등). 지금 킷은 그런 patch 를 `형이 다릅니다 (지금은 글자, 받은 것은 목록) — 같은 형으로 보내십시오` 로 거부하고 history 의 `↳ 적용 못 함:` 에 남긴다. **그래도 나오면 킷 결함이다** — 검사기를 고치지 말고 thread_id · 스택 · 서버 로그와 함께 보고한다 |
| 노드가 두 번 돎 | fan-in 을 리스트로 안 썼다 |
| 10분 넘게 안 끝남 | `live` 모드거나, 게이트 B 에 `done` 을 줘서 정성 3회(`claude -p`, 6~12분)에 들어갔다. 끊고(에이전트면 백그라운드 작업 정지) `replay` · `--auto proceed` 로 |
| `claude 를 찾지 못했습니다` | 수집은 `replay` 로 폴백된다. **정성은 폴백하지 않고 멈춘다** |
| 정성이 `ERROR` | `evidence/runs/*/quality/blocked.json` 을 읽어 그대로 전한다 |
| 정성이 계속 `SHORT` | `passN.json` 의 `skipped_fix` 를 본다. 조용히 넘어간 것이 아니다 |
| `quality_pass` 가 세 번 안 돎 | 게이트 B에서 `done` 을 골랐는지 확인. `research`/`rebuild` 면 0으로 초기화됨 |
| `fix_*` · `test_*` 가 한 번도 안 켜짐 | **정상.** 처방 가지는 그 실패가 났을 때만 켜진다 — 재현(inject)이 없으면(`replay`) 켜지지 않는다. 보려면 `{"inject": ["image_dead"]}` 또는 `--inject image_dead --auto stop` |
| `fix ↔ test` 가 두 번 돌고 게이트에서 멈춤 | 처방 한도(2회)를 다 썼다 (`test_<이름>: FAIL · 2/2회 → human_gate_*`). `② 왜` 맨 앞 `처방 가지가 못 고침` 줄과 `③ 권장` 을 전한다 — 실행 순서 5) 참고 |
| `run_once.py` 가 게이트에서 바로 끝남 (`… 에서 답 없이 끝냄`) | **정상.** 답이 없으면(표준입력이 터미널이 아님 · `--auto` 답을 다 씀 · EOF) 권장값으로 넘어가지 않고 멈춘다. 더 보려면 `--auto` 에 답을 더 준다 (루프 B 까지는 `--auto proceed`) |
| `모르는 처방 가지 이름` (`run_once.py`, exit 1) · `모르는 inject 이름을 버렸습니다` (Studio history) | `--inject` · `inject` 이름 오타. 고를 수 있는 이름은 `travel_graph/detours/registry.py` |
| 정성 중에 화면 규격 증상이 있는데 처방 가지를 안 탐 | **정상.** 정성이 한 회차라도 돈 뒤에는 루프 B 가지를 타지 않는다 (해시 사슬 보호). 게이트 `② 왜` 에 `처방 가지를 미룸 — <title> (정성 회차 중)` 으로 뜬다 |
| `GraphRecursionError` | Studio 에서는 사실상 나지 않는다 — Studio 서버(langgraph-api 0.13.3)의 기본 `recursion_limit` 이 10011, langgraph 1.2.11 자체의 기본이 10007 이다 (`LANGGRAPH_DEFAULT_RECURSION_LIMIT`). `run_once.py` 는 150 으로 둔다 (처방 가지 한 번이 걸음 넷(fix · test · 검사기 · 진단)을 더 쓰고, 재시도마다 둘(fix · test)이 는다). 나면 같은 노드가 끝없이 도는지 history 로 보고, 구조 검사 7 · 9번(상한 없는 순환)을 돌린다 |
| 구조 검사 11번(처방 가지 계약) FAIL | STEP 6 에서 만든 가지 조각이 어긋났다. 실행하지 말고 `graph-detour-builder` 로 |

---

## 끝나면 넘기는 곳

| 상황 | 다음 |
| --- | --- |
| 실행이 끝남 (게이트 확정 · 최종 검증까지) | `evidence-review` — 증거 정리 · 실패 기록 · 루프판 비교표 |
| 실행을 본 뒤 `failure_report.py` ③ · ③-2 에 후보가 있음 | STEP 6 (처방 가지 추가 · 조건부) — `graph-detour-builder` 가 후보 하나를 처방 가지로 만든다 |
| 후보가 없음 (`… STEP 6 은 하지 않아도 됩니다`) | STEP 6 없이 `evidence-review` 로 마친다 |

**실행과 STEP 6 을 섞지 않는다.** STEP 6 으로 넘기기 전에 서버를 끈다(실행 순서 7).
가지 조각을 만드는 동안 `--no-reload` 서버가 옛 코드를 붙들고 있으면 새 가지가
그림에 안 나온다 (`--no-reload` 라 새 `.py` 로 다시 뜨지도 않는다 — 직접 다시 켠다).
STEP 6 이 끝나면 다시 이 스킬로 돌아와 새 가지의 실패를 재현(`inject`)해 본다.
