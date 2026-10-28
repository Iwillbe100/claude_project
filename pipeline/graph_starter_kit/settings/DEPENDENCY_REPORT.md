# 의존성 정합 보고 — 그래프 킷 기준

**측정 시각:** 2026-09-06 (루프 C 개정 반영) · **기준 환경:** CPython 3.12.3 / Windows 11 x64
**측정 방법:** `pip check` + `verify_env.py` C03 + 실제 그래프 컴파일·기동·`interrupt` 왕복
+ **정성 3회(`quality_pass ↔ check_quality`) 실제 실행**
**2026-09-27 재측정 (처방 가지 개정 — 루프 골격 + 진단 + 규칙 처방 가지):** Python 3.12 · `langgraph` 1.2.11 에서
그래프 컴파일(`NODES 24`) · 구조 검사 12행 PASS · 회귀 221개 PASS 만 다시 쟀다.
**2026-09-27 배포 전 점검 (킷 복사본, Windows 11 · CPython 3.12.3):** 새 `.venv` 에 lock 설치
2분 8초(pip 캐시 있음) · 79개 · `.venv` 139MB · `pip check` 충돌 0건 · `verify_env.py` C01~C07 · C10~C12
OK(C12 실검색 1회, 약 25초) · `langgraph dev` 로 `['smoke']` · `['travel']` 등록 확인.
C08·C09 는 실제 키 없이 점검해 다시 재지 않았다 (1장의 값은 2026-09-06 측정).
**2026-09-28:** 회귀에 T16(재수집 patch 형 검사 · 바뀐 사진만 재확인 · 보고서 ③-2)이 더해져 킷 기본
**240개** — 같은 조건(Python 3.12 · `langgraph` 1.2.11, 킷 복사본)에서 240개 PASS. 설치 조합은 그대로다.

이 문서는 **킷을 만들 때 실측한 결과**입니다. 교육생 환경에서 다시 재려면 (킷 폴더 · 가상환경을 켠 창에서):

```bash
python settings/scripts/verify_env.py
```

---

## 1. 결론

```text
의존성 충돌        0건        pip check → "No broken requirements found."
핵심 14종 버전     전량 일치   requirements.lock.txt 와 정확히 동일
그래프 컴파일      정상       노드 22개 + START/END   ← NODES 24  (2026-09-27 재측정)
                              루프 골격 14 + 진단 2 + 처방 가지 3개 × 2 (fix_ · test_)
처방 가지 3개      정상       회귀 240개 PASS (T14 처방 가지 동작 · T15 구조 검사 11번 변이 9종 ·
                              T16 재수집 patch 형 검사 · 보고서 ③-2)   ← 2026-09-28 (09-27 은 221개)
langgraph dev      정상       assistants/search → ['travel']
interrupt 왕복     정상       게이트 A 정지 → 재개 → 게이트 B 정지 → 재개 → 종료
정성 3회 순환      정상       quality_pass ×3 순차 · 되돌아감 확인 exit 0
LangSmith 인증     정상       C08 HTTP 200 · C09 인증 성공
```

**체크포인트·HITL 을 위해 추가로 설치할 패키지는 없습니다.** (근거는 3장)
**루프 C(정성 완성도)를 위해 추가로 설치할 패키지도 없습니다.** (근거는 5장)
**진단 · 규칙 처방 가지(루프 골격 + 진단 + 처방 가지 개정)를 위해 추가로 설치할 패키지도 없습니다.** (근거는 5장)

---

## 2. 실측된 버전

| 패키지 | lock | 실측 | 이 킷에서 쓰는 곳 |
| --- | --- | --- | --- |
| Python | 3.12.x | **3.12.3** | `langgraph.json` 이 3.12 로 선언 |
| `langgraph` | 1.2.11 | **1.2.11** | `StateGraph` · `Send` · `interrupt` · `Command` |
| `langgraph-checkpoint` | 4.2.0 | **4.2.0** | `InMemorySaver` (순수 파이썬 경로) |
| `langgraph-cli` | 0.4.31 | **0.4.31** | `langgraph dev` |
| `langgraph-api` | 0.13.3 | **0.13.3** | 로컬 Agent Server — **스레드 영속화 담당** |
| `langgraph-runtime-inmem` | 0.33.3 | **0.33.3** | 인메모리 런/스레드 저장소 |
| `langgraph-prebuilt` | 1.1.0 | **1.1.0** | (이 킷은 직접 쓰지 않음) |
| `langgraph-sdk` | 0.4.4 | **0.4.4** | Agent Server 클라이언트 (검증용) |
| `langchain-core` | 1.6.1 | **1.6.1** | 노드 span 이 여기서 생성된다 |
| `langsmith` | 0.12.1 | **0.12.1** | 트레이스 전송 |

---

## 3. ★ "체크포인트 때문에 뭘 더 깔아야 하나" — 아니오

`interrupt` 는 체크포인터를 요구합니다. **그런데 경로마다 그것을 대는 주체가 다릅니다.**

| 실행 경로 | 상태를 누가 들고 있나 | 필요한 패키지 | lock에 있나 |
| --- | --- | --- | --- |
| `langgraph dev` (Studio) | **Agent Server** | `langgraph-api` + `langgraph-runtime-inmem` | **예 (T2)** |
| `run_once.py` · pytest | `InMemorySaver()` 를 직접 넘김 | `langgraph-checkpoint` | **예 (T1)** |
| 서버 없이 파일로 재개 | `SqliteSaver` | `langgraph-checkpoint-sqlite` | **아니오 — 설치 안 함** |

```python
# Studio 경로 — 체크포인터를 넘기지 않는다
graph = builder.compile(name="travel")

# 순수 파이썬 경로 — 반드시 넘긴다
graph = builder.compile(checkpointer=InMemorySaver())
```

### 왜 SQLite 체크포인터를 안 까나

```text
1  이 실습의 모든 경로가 그것 없이 동작한다 (실측 완료)
2  requirements-optional.txt 에 있다 = 강사 환경에 없다
   설치하는 순간 교육생 환경 != 강사 환경 (SETUP.md R4)
3  Studio 에서 compile(checkpointer=...) 를 쓰면 Agent Server 것과 싸운다
```

굳이 풀어야 한다면 **반드시 lock 을 제약 파일로 함께 겁니다.**

```bash
python -m pip install --require-virtualenv langgraph-checkpoint-sqlite \
    -c settings/requirements.lock.txt
```

---

## 4. 잠재 충돌 항목과 원인 분석

| # | 항목 | 증상 | 원인 | 해결 |
| --- | --- | --- | --- | --- |
| 1 | **Python 3.13 (또는 3.11)** | 설치는 **오류 없이 끝난다** — `verify_env.py` C01 만 FAIL | lock 79개가 3.13 · 3.11 에서도 해석된다 (2026-09-27 `pip install --dry-run` 실측). `pyproject.toml` 의 `requires-python = ">=3.12,<3.13"` 은 `pip install -e .` 때만 걸리는데 킷은 그 설치를 하지 않는다 | `py -3.12` 로 venv 재생성 (SETUP STEP 1~2). 설치 성공을 3.12 의 증거로 읽지 않는다 |
| 2 | **`httpx` 와 `httpx2`** | 이름이 비슷해 하나를 지우고 싶어짐 | `langsmith` 가 별도 HTTP 스택(`httpx2`)을 쓴다. **다른 패키지다** | 둘 다 둔다. 지우면 트레이싱이 조용히 끊긴다 |
| 3 | **`langchain-anthropic` 설치** | (예전) `ResolutionImpossible` | 당시 `langchain-core==1.6.1` 과 호환 범위가 어긋났다. **2026-09-27 에는 `-c lock` 을 걸어도 `langchain-anthropic` 1.7.1 이 해석된다** (dry-run 실측) — 즉 설치가 된다고 해서 필요한 것은 아니다 | **설치하지 않는다.** 이 킷은 `claude -p` 서브프로세스를 쓰므로 애초에 필요 없고, 설치하는 순간 강사 환경과 달라진다. `ResolutionImpossible` 이 나면 `-c lock` 을 빼고 재시도하지 않는다 |
| 4 | **`ANTHROPIC_API_KEY` 환경변수** | 구독 인증 대신 API 과금 | API 키가 구독 인증을 **이긴다** | `research.py` 가 서브프로세스 환경에서 제거한다(`SCRUB_ENV`). `verify_env.py` C11 이 WARN 으로 알려 준다 |
| 5 | **`forbiddenfruit` 은 wheel 이 없다** | 설치 때 소스 빌드 | `blockbuster`(이벤트 루프 블로킹 탐지)의 의존성. **순수 파이썬**이라 C 컴파일러는 필요 없다 (C 확장은 `FFRUIT_EXTENSION=true` 일 때만 — 2026-09-27 sdist 확인) | 빌드 실패는 대개 빌드용 `setuptools` 를 인덱스에서 못 받은 것이다. 사내 미러 확인 |
| 5b | **Intel Mac 에서 `cryptography` 빌드 실패** | `can't find Rust compiler` 등 | `cryptography==50.0.1` 의 macOS wheel 은 **arm64 뿐**이다 (48.0.1 까지는 universal2). Windows x64 · Linux x86_64/aarch64 · Apple Silicon 은 lock 전체에 wheel 이 있다 (2026-09-27 `--only-binary` 실측) | 교육생은 버전을 바꾸지 않고 강사에게 보고. `langgraph-api` 의 요구는 `cryptography>=42.0.0` 이라 강사가 Intel Mac 용 대체 핀을 검증해 내려 줄 수 있다 |
| 5c | **macOS · Linux 는 81개가 설치됨** | "79개가 아니다" | `langgraph-api` 가 Windows 가 아닐 때만 `uvloop` · `httptools` 를 요구한다. lock 은 Windows 에서 계산해 이 둘이 없다 | 정상. `pip check` 만 보면 된다. 두 패키지는 버전이 고정되지 않은 채 들어온다 |
| 5d | **`langgraph dev` 가 업그레이드를 권함** | `A newer version of langgraph-api is available` · `End of Life … upgrade immediately` | 기동 때 PyPI 최신판과 비교한다 (`langgraph_api/cli.py`) | **따르지 않는다(R4).** `.env` 의 `LANGGRAPH_NO_VERSION_CHECK=true` 가 이 안내를 끈다 (배포본 `.env` 에 들어 있음) |
| 6 | **T4 32개를 지우고 싶어짐** | "그래프와 무관해 보임" | `langgraph-api` · `langgraph-runtime-inmem` 의 하드 의존성 | 지워도 pip 이 다시 끌어온다. **버전 고정만 사라진다** |
| 7 | **정성 3회에서 `recursion_limit` 초과** | `GraphRecursionError` | 순환이 넷에서 여섯으로 늘었다. 처방 가지 개정 뒤에는 진단 노드가 검사기 뒤에 **매번** 한 걸음을 더하고, **처방 가지 한 번이 걸음 넷(fix · test · 검사기 · 진단)을 더 쓰고, 재시도마다 둘(fix · test)이 는다** (실측 순서: 검사기 → 진단 → fix → test → 검사기 → 진단 → …) | `run_once.py` 가 **150** 으로 둔다 (회귀 테스트 T14 도 150). `langgraph` 1.2.11 코어의 기본값은 **10007** 이다 (`langgraph/_internal/_config.py` · 환경 변수 `LANGGRAPH_DEFAULT_RECURSION_LIMIT`). Studio 서버(`langgraph-api` 0.13.3)도 같은 환경 변수를 읽고 기본값이 10011 이다 (`langgraph_api/utils/config.py`, 2026-09-28 원본 확인) — 그래서 **Studio 에서는 사실상 나지 않는다.** 예전 안내의 25 는 옛 기본값(`langchain-core`)을 전제한 것이다. 그래도 나면 같은 노드가 끝없이 도는지 history 로 본다 |
| 8 | **정성 회차가 네트워크를 탄다** | 오프라인에서 `check_quality` 가 ERROR | 정성 판정은 `claude -p` 를 부른다. 수집과 달리 **replay 폴백이 없다** | 의도된 설계다. 모의로 통과시키면 "고친 척"을 자동화하는 셈이다. `blocked.json` 에 이유가 남는다 |
| 9 | **이미지 확인이 네트워크를 탄다** | `live` 수집이 느려짐 | `research.verify_asset()` 이 주소를 직접 연다 (`urllib`, 20초 타임아웃) | 표준 라이브러리라 설치 추가 없음. 실패해도 `verified.status = 0` 으로 **기록**하고 진행한다 |
| 10 | **`langgraph dev` 가 실행 중 재시작** | 돌던 run 이 끊김 | 감시 기능(`--no-reload` 없이 켤 때)이 파일 변경에 서버를 다시 띄운다. `langgraph-api` 0.13.3 은 uvicorn 의 기본 감시 패턴을 쓰고, uvicorn(`watchfiles`)은 **`*.py` 만** 감시한다 — `quality_pass` · `build_page` 가 `output/**` · `evidence/**` 에 쓰는 json · html 로는 재시작하지 않는다 (2026-09-28 원본 확인. 예전 이 칸의 "파일 쓸 때마다 재시작"은 틀린 설명이었다). 재시작을 일으키는 것은 실행 중 `.py` 변경이다 — 코드 수정, STEP 6 의 `new_detour.py` 가 가지 파일을 만들 때 | **`--no-reload` 필수.** 대신 새 코드는 서버를 직접 다시 켜야 반영된다 |
| 11 | **`claude` CLI 권한 규약** | `live` 인데 매번 `replay` 로 내려감 | `--tools` 는 **가용성**, `--allowedTools` 는 **권한**. `--permission-mode dontAsk` 는 "허용"이 아니라 "묻지 않음"이므로 승인 없는 도구는 **거부**된다 | 두 옵션을 함께 준다. `verify_env.py` **C12** 가 실측으로 잡는다 (2026-09-06 수정) |
| 12 | **HTTP 헤더 인코딩** | 관광지 이미지가 전부 `verified.status = 0` | `urllib` 는 헤더를 latin-1 로 인코딩한다. User-Agent 에 한글이 있으면 `UnicodeEncodeError` | User-Agent 를 ASCII 로. 증상이 방화벽 차단과 구분되지 않아 오진이 잦다 (2026-09-06 수정) |
| 13 | **`live` 조사 시간** | 도시 한 곳에서 타임아웃 → 폴백 | 검색이 실제로 돌면 도시 한 곳이 2~6분. 예전 기본값 300초로는 모자랐다 | 기본 `GRAPH_CLAUDE_TIMEOUT` 을 600초로. 병렬이라 전체 시간은 그대로다 |
| 14 | **루프 A 가 수렴하지 않음** | 못 채운 칸이 30 → 33 으로 **늘어남** | `research_node` 명세는 "부족한 칸만 다시 모은다" 인데 live 분기가 `short_slots` 를 받고도 쓰지 않아 매 바퀴 **처음부터 다시** 만들었다 | 재수집 분기를 만들어 지난 결과 + 지적 목록을 함께 준다. 실측 25곳 → 6곳 (2026-09-06 수정) |
| 14b | **멀쩡한 도시까지 다시 뽑음** | 다낭만 터져도 세 도시가 전부 재수집 | `research_node` 하나가 안에서 **모든 도시**를 불렀고, 지적이 없는 도시는 `todo` 가 비어 재수집 분기를 못 타고 **첫 수집 프롬프트로 떨어졌다** | 노드를 `repair_city` 로 바꾸고 라우터(`fan_out_repairs`)가 **다친 도시만 `Send`** 한다. 손대지 않은 도시는 호출조차 되지 않는다 |
| 14c | **한 응답이 잘림** | 취향 설명·일정이 얇아짐 | 도시 하나가 계약을 채우려면 7,400자인데 이 CLI 의 실측 잘림 임계가 12,341자였다. 여유가 없어 모델이 JSON 뒤쪽을 줄여 맞췄다 | 도시 수집을 `claude -p` **두 번**(명소/일정)으로 나눈다. 3,700자씩이 되고, 일정이 실패해도 명소는 남는다 |
| 14d | **재수집이 멀쩡한 칸을 지움** | 고치라고 시킨 바퀴에서 부족이 늘어남 | "고치지 않은 값은 그대로 옮겨 적으라"고 전체 JSON 재타이핑을 시켰다 | **patch 형식**으로 고친 곳만 받는다. 안 건드린 값은 물리적으로 안 바뀌므로 `_keep_bigger` 방어 코드도 없앴다 |
| 14e | **실패가 빈 껍데기로 감춰짐** | 게이트가 "관광지 수 3/0" 한 줄만 보여 줌 | `select_cities` 가 인계본에 없는 도시를 고른 채 live 가 실패하면 `_replay_city` 가 빈 도시를 **정상인 척** 돌려줬다 | `city_failures` 상태 칸에 사유를 남기고 게이트 `② 왜` 가 "수집 실패"로 따로 보여 준다 |
| 14f | **국가 소개는 고칠 방법이 없었음** | 부족 6곳이 그대로 최종 보고서까지 감 | 국가 소개에는 **재수집 경로가 아예 없었다.** 근거는 "자산 제외 2,677자라 잘릴 위험이 없으니 1회차에 실패할 리 없다"였는데, 그것은 **잘림**만 배제하고 **수집 부족**은 배제하지 못한다. 근거 15건을 24턴 한 번에 요구했고 모델은 얇게 내고 `end_turn` 으로 스스로 끝냈다 (턴이 터졌으면 replay 폴백으로 내려가 부족이 0 이 됐을 것이다) | `repair_country` 노드를 만들어 도시와 **같은 fan-out** 에 태운다. patch 로 지적된 칸만 고친다 |
| 14g | **한글 경로 patch 가 전부 거부됨** | 국가 재수집이 조용히 아무것도 안 고침 | `_PATH_TOKEN` 이 `[A-Za-z_]` 라 `매력.items[2]` 를 못 읽었다. `_path_parts` 가 빈 리스트를 돌려주고 모든 patch 가 "경로 형식을 못 읽었습니다"로 거부됐다 | `[^\W\d]\w*` 로 넓힌다. 잘못된 경로(`9bad`)는 여전히 거부한다 |
| 14h | **재수집을 수집 노드 재사용으로 만들면 멈춤** | 예외 없이 조용히 정지 | 합류(`add_edge([a,b],c)`)에 되돌이 간선을 걸면 합류가 다른 갈래를 영영 기다린다. 최소 재현 `['A','B','J1','A']` 에서 끝 | 재수집은 합류를 우회하는 **별도 노드**여야 한다. `repair_city` · `repair_country` 가 따로 있는 이유다 |
| 14i | **`서로 다른 출처` 부족을 개수 문제로 오분류** | 지시가 "더 찾아라"로 나가 같은 출처에서 한 건을 더 얹고 또 실패 | 그 줄에도 `목표 2 / 실제 1` 이 붙어 있어 `_CAUSE_A` 의 `목표` 규칙에 먼저 걸렸다. 도시·국가 양쪽에서 났다 | `· 서로 다른 출처` 규칙을 `목표` **앞에** 둔다. 고칠 법 안내를 "다른 도메인에서 찾아 갈아 끼워라"로 바꾼다 |
| 14j | **게이트가 `more` 대상을 잘못 안내** | 국가만 부족한데 "지적된 **도시**만 다시 모읍니다"라고 표시 | 화면 문구가 고정 문자열이라 라우터가 실제로 무엇을 Send 할지와 무관했다 | `gate_a_payload` 가 `fan_out_repairs` 와 **같은 규칙으로** 대상을 계산해 그대로 적는다 |
| 15 | **재수집 한 바퀴가 11분** | 루프 A 3바퀴에 30분 | `research_node` 가 국가·도시 3개를 **순차로** 불렀다 | (2026-09-06) 스레드로 동시에 불렀다. 11분 → 약 4분. **→ 14b 로 대체됨.** `repair_city` `Send` fan-out 이 되면서 병렬을 LangGraph 가 맡고 스레드는 없앴다. `tracing._parent()` 의 `contextvars` 주석이 그 흔적이다 |
| 16 | **출처 링크가 늘 "화면에 없습니다"** | 루프 B 가 3바퀴를 다 쓰고도 SHORT | `page.esc()` 가 `html.escape(quote=True)` 라 `&` → `&amp;`, `'` → `&#x27;`. 검사기는 URL 을 **원문 그대로** 찾는다(`url not in text`) | HTML5 최소 escape 로 바꾼다 — 모호한 `&` 와 `< > "` 만 바꾸고 나머지는 원문 유지. 출처 40/43 → **43/43** (2026-09-06 수정) |
| 17 | **확인한 칸이 "미작성"으로 보임** | `국가상태` 패널이 60자 하한 미달 | 조건부 칸(`checked: true, items: []`)을 빈 칸과 똑같이 그렸다. 개수 검사기는 둘을 구분하는데 화면은 안 했다 | 확인한 사실을 화면에 적는다. 거짓말이 아니라 **상태를 그대로 적는 것**이다 (2026-09-06 수정) |
| 18 | **교육생마다 수집 결과가 다름** | 재현이 안 됨 | `claude -p` 가 cwd(킷 루트)와 홈의 `CLAUDE.md`·훅·플러그인·스킬을 자동으로 끌어온다 | `--safe-mode` 로 커스터마이징만 끈다(인증·모델·권한은 유지). 끌어오는 컨텍스트 12,834 → 1,584 토큰. 끄려면 `GRAPH_CLAUDE_SAFE_MODE=0` |
| 19 | **실패 사유가 빈칸으로 기록됨** | `코드 1 로 종료했습니다: ` 만 남음 | `claude -p` 는 실패해도 stderr 가 비어 있는 경우가 있다(사용량 한도, 부모와 함께 종료 등). 사유는 stdout 의 JSON 봉투에 있다 | stderr 가 비면 stdout JSON 에서 사유를 꺼내 붙인다 |
| 20 | **정성 회차가 `error_max_turns`** | 루프 C 가 ERROR (폴백 없음) | 판정 1회가 실제로 쓰는 턴은 **14~16**인데 상한이 **14**였다 — 여유가 0. 같은 입력에서도 흔들리므로 **어느 회차든** 걸릴 수 있었다 | 상한을 실측 최대의 1.5배인 **24**로. 무한정 올리지 않는다 — 이 상한은 폭주를 잡는 장치다. 턴 초과는 **exit 1** 로 오므로 사유를 stdout 에서 꺼내 숫자와 함께 다시 쓴다 |
| 21 | **응답이 중간에 잘림** | `JSON 블록을 찾지 못했습니다` → replay 폴백 | 이 계약이 요구하는 도시 JSON 이 **한 번에 담기는 한계에 가깝다.** 실측 성공 11,805자 / 잘림 12,341자. 앞에 서술을 길게 쓰면 블록이 닫히기 전에 끝난다 | 프롬프트에서 서술을 금지해 출력 예산을 JSON 에 쓴다. 그래도 잘리면 **잘렸다고 이름을 붙여** 보고한다(`중단 이유` · `응답 길이`). 형식 문제와 길이 문제를 구분해야 조치가 갈린다 |
| 22 | **트레이스에 `claude -p` 가 안 보임** | 노드 소요만 보이고 안쪽이 빔 | 서브프로세스라 LangSmith 가 볼 수 없다 | `travel_graph/tracing.py` 가 `RunTree` 로 자식 run 을 만든다. **패키지 추가 없음** (`langsmith` 는 이미 lock 에 있다) |
| 23 | **스레드 안 호출이 트레이스에서 떨어져 나감** | root run 이 여러 개로 흩어짐 | 부모를 찾는 통로가 contextvar 인데 `ThreadPoolExecutor.submit` 은 그것을 옮기지 않는다 | `contextvars.copy_context().run` 으로 감싼다. 실측: 그냥 submit → `None` / copy_context → 노드 run 을 정확히 잡는다 |
| 24 | **LangSmith 에 도는 중(pending) tool run 이 남음** | 끝난 호출인데 "아직 도는 중" 처럼 보임 | 결과 줄이 오기 전에 호출이 끝난 도구 턴을 `tracing.py` 의 `finish()` 가 닫지 않았다 (닫는 것은 `fail()` 뿐이었다) | `finish()` 가 남은 tool 자식을 닫는다 (2026-09-28). **패키지 추가 없음.** 트레이스가 게이트(`interrupt`)마다 새 루트로 나뉘는 것은 이것과 다른 일이다 — 정상이며 Threads 탭에서 `thread_id` 로 이어 본다 |

> **20번의 실측 근거.** `--safe-mode` 는 턴을 늘리지 않는다. 오히려 줄인다.
>
> ```text
> safe-mode ON   turns 14   113s
> safe-mode OFF  turns 16   128s
> 예전 상한      14              <- 붙어 있었다
> ```
>
> **"회차가 쌓여서"가 아니다.** 정성 수정은 그렇게 크지 않다 — 한 실행에서
> 1회차 316자, 2회차 478자로 합쳐 794자였고, 이는 87KB 파일의 **0.9%** 다.
> 수정을 **0건** 적용한(=파일이 전혀 안 바뀐) 실행도 있었는데 그 실행은 3회 다
> 통과했다. 원인은 파일 크기가 아니라 **상한에 붙어 있던 값**이다.
> 판정자가 큰 파일을 몇 조각으로 읽고 `Grep` 을 몇 번 쓰느냐에 따라 턴이
> 흔들리므로, 특정 회차가 위험한 것이 아니라 **매 회차가 동전 던지기**였다.

---

## 4-b. 2026-09-06 실측 — `live` 조사가 조용히 `replay` 로 내려가던 문제

증상은 하나인데 원인이 셋이었다. 셋 다 **에러를 내지 않아서** 화면만 봐서는
정상과 구분되지 않았다. 아래는 같은 프롬프트로 옵션만 바꿔 가며 잰 결과다.

| 옵션 조합 | `permission_denials` | 실제 검색 | 결과 |
| --- | --- | --- | --- |
| `--tools WebSearch` (기존) | `[{tool_name: "WebSearch"}]` | 0회 | 모델이 "권한이 막혀…" 문장만 출력 → JSON 없음 → **replay 폴백** |
| `--tools` + `--allowedTools` | `[]` | 2~9회 | 정상. 근거 URL 이 실제 조회 결과 |
| `--permission-mode bypassPermissions` | `[]` | 2~9회 | 되기는 하나 **권한을 통째로 여는 것**이라 킷은 쓰지 않는다 |

**원인 1 — 옵션 두 개의 역할이 다르다.**
`--tools` 는 도구를 *띄우고*, `--allowedTools` 는 그것을 *승인 없이 쓰게 한다.*
`dontAsk` 는 "사람에게 묻지 않는다"는 뜻이라, 승인이 없으면 물어보는 대신 **거부**한다.
그래서 도구는 목록에 보이는데 호출은 전부 막혔다.

**원인 2 — 실패가 다른 얼굴로 나타났다.**
거부당한 모델은 예외를 던지지 않고 *설명 문장*을 냈다. 킷은 ```json 블록만 찾으므로
"JSON 블록을 찾지 못했습니다"라는, 원인과 무관한 메시지로 폴백했다.
지금은 `permission_denials` 를 먼저 읽어 **막힌 도구 이름을 그대로** 말한다.

**원인 3 — 검사 지표를 잘못 읽었다.**
`usage.server_tool_use.web_search_requests` 는 이 CLI 에서 **언제나 0** 이다.
Claude Code 의 WebSearch 는 서버 도구가 아니라 CLI 가 보조 모델로 돌리는
클라이언트 도구여서, 횟수는 `modelUsage.<모델>.webSearchRequests` 에 적힌다.
0 을 보고 "검색이 안 됐다"고 읽으면 고쳐 놓고도 안 고쳐진 줄 안다.

**딸려 나온 결함 하나 더.** 폴백 상태에서는 인계본의 `verified` 기록을 물려 써서
가려져 있었는데, `live` 가 살아나자 이미지 실측이 **4곳 중 4곳 실패**로 나왔다.
네트워크가 아니라 `verify_asset()` 의 User-Agent 에 한글이 있어서였다 (표의 12번).
고친 뒤 같은 도시를 다시 재니 `status 200 image/jpeg` 4/4.

```text
고치기 전   collect_city[밴쿠버]: … 이미지 status=0 ×4   ← 전부 죽은 것처럼 보임
고친 뒤     collect_city[밴쿠버]: … 이미지 status=200 ×4  · 실검색 9회
```

**그리고 그 뒤에 하나 더 나왔다.** `live` 가 살아나자 루프 A 가 돌기 시작했는데,
**돌수록 못 채운 칸이 늘었다** (30 → 33). 당시 `nodes.research_node`(2026-09-08 에
`repair_city` 로 대체됨) 의 명세는

> 전부 다시 하지 않는다. `info_short_slots` 에 적힌 칸만 다시 모은다.

인데, `collect_one_city()` 의 live 분기가 `short_slots` 를 **받고도 쓰지 않았다.**
`_replay_city()` 만 썼다. 그래서 재수집이 "지적된 곳 고치기"가 아니라 "처음부터 다시
만들기"가 되어, 같은 종류의 실수를 **다른 자리에서** 반복했다.

이것 역시 폴백에 가려져 있었다 — replay 로 내려가면 `_replay_city()` 가 돌았고,
거기서는 `short_slots` 가 제대로 쓰였기 때문이다.

```text
고치기 전   research → 전체 재생성 → 밴쿠버 지적 25곳 그대로 (자리만 바뀜)
고친 뒤     research → 지난 결과 + 지적 목록 전달 → 밴쿠버 25곳 → 6곳 · 전체 33 → 14
```

세 결함의 관계는 이렇다. **하나가 다음 하나를 가리고 있었다.**

```text
권한 차단  →  항상 replay 폴백  →  ① 이미지 UA 결함이 안 보임 (인계본 기록을 물려 씀)
                              →  ② 재수집 결함이 안 보임 (_replay_city 가 대신 동작)
```

그래서 "검색만 고치면 끝"이 아니었다. 폴백을 걷어 내야 나머지가 보였다.

---

## 5. 이 킷이 lock 에 **추가한 것 없음**

```text
graph_starter_kit 가 쓰는 외부 패키지
  langgraph          StateGraph · Send · interrupt · Command
  langgraph-checkpoint  InMemorySaver
  langgraph-cli/api/runtime-inmem   langgraph dev
  python-dotenv      .env 로딩 (settings/smoke)
  (표준 라이브러리)   json · subprocess · ast · html · importlib · hashlib · urllib.request

새로 추가한 pip 패키지: 없음
```

`travel_graph/page.py` 는 표준 라이브러리만 씁니다 (템플릿 엔진 없음).
`travel_graph/research.py` 는 `subprocess` 로 `claude` CLI 를 부릅니다 (npm 설치물, pip 무관).

### 루프 C 개정으로 늘어난 것 (2026-09-06)

| 늘어난 것 | 무엇을 쓰나 | 설치 필요 |
| --- | --- | --- |
| `travel_graph/quality.py` | `hashlib` · `json` · `subprocess` · `datetime` · `re` | **없음** (전부 표준 라이브러리) |
| `travel_graph/tracing.py` | `langsmith.run_trees.RunTree` · `json` · `datetime` | **없음** (`langsmith` 는 이미 T1 에 있다) |
| `research.verify_asset()` | `urllib.request` | **없음** (표준 라이브러리) |
| `scripts/check_quality_passes.py` | `json` · `pathlib` | **없음** (루프 킷에서 그대로 복사) |
| 노드 2개 (`quality_pass` · `check_quality`) | 기존 `langgraph` API 그대로 | **없음** |

> 해시 라이브러리(`hashlib`)와 HTTP(`urllib`)를 표준 라이브러리로 고른 이유는
> 하나입니다 — **lock 79개에 한 줄도 더하지 않기 위해서**입니다.
> `requests` 는 이미 lock 에 있지만(T3) `langsmith` 의 전이 의존성이므로,
> 킷 코드가 직접 의존하면 T1 이 늘어나 계층 구분이 흐려집니다.

### 처방 가지 개정으로 늘어난 것 (2026-09-27)

| 늘어난 것 | 무엇을 쓰나 | 설치 필요 |
| --- | --- | --- |
| `travel_graph/detours/` (등록부 · 처방 가지 모듈 3개 · 실패 기록 `log.py` · 새 가지 틀) | `re` · `json` · `copy` · `importlib` · `dataclasses` · `datetime` · `pathlib` · `urllib.parse` · `urllib.request` | **없음** (전부 표준 라이브러리) |
| `scripts/detour_tests/` (처방 가지 시험지 3개 + 공용 `_common.py`) | `html.parser` · `urllib.parse` · `argparse` · `json` · `re` + 킷의 `scripts/_contract.py` | **없음** (표준 라이브러리. 시험지는 `travel_graph` 를 import 하지 않는다) |
| `scripts/new_detour.py` · `scripts/failure_report.py` | `argparse` · `json` · `collections` · `re` | **없음** |
| 노드 8개 (진단 2 · 처방 가지 `fix_` · `test_` 6) | 기존 `langgraph` API 그대로 (`add_node` · `add_edge` · `add_conditional_edges`) | **없음** |

> `image_dead` 처방 가지는 live 에서 바꾼 사진 주소를 **실제로 열어 보고**(`research.verify_asset()`
> 과 같은 경로), 2회째에는 Commons 를 검색한다(`urllib.request`, 20초 타임아웃). 둘 다 표준
> 라이브러리라 설치 추가가 없다. replay 에서는 네트워크를 타지 않는다 (표의 9번과 같은 성격).

---

## 6. 다시 잴 때

킷 폴더에서, **가상환경을 켠 창**으로 (Windows PowerShell · macOS/Linux 공통 명령):

```bash
python settings/scripts/verify_env.py            # C01~C12 (C12 = live 웹검색 실측)
python -m pip check                              # 충돌 0건
python scripts/check_graph_shape.py              # 그래프 구조 검사행 12개 (11 = 처방 가지 계약)
python scripts/selftest/run_graph_regression.py  # 회귀 240개 (replay · 약 10~15초 · 처방 가지 하나에 +11)
python scripts/run_once.py --mode replay --auto proceed,done,done       # 끝까지 — 정성 3회는 claude -p (6~12분)
python scripts/verify_all.py --skip-quality      # 정성 빼고 exit 0
python scripts/verify_all.py                     # 정성 포함 exit 0 (6~12분 더)
```

**버전을 바꾸고 싶어지면 `requirements.lock.txt` 를 고치지 말고 강사에게 확인하십시오.**
lock 에서 줄을 빼도 설치량은 줄지 않고 재현성만 잃습니다.
