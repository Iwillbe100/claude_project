# LangGraph + LangSmith 실습 환경 세팅 지시문 — 그래프 스타터 킷

이 문서 하나로 **Python 확보 → `.venv` 생성 → 버전 정합 설치 → LangSmith `.env` 연결 → 노드별 실시간 트레이싱 검증**까지 끝난다.
교육생마다 OS·Python·네트워크가 다르므로, **STEP 0에서 환경을 먼저 진단한 뒤** 그 결과에 맞는 명령만 실행한다.

---

## 교육생이 클로드 코드에 던질 한 마디

프로젝트 폴더에서 클로드 코드를 열고, 아래 문장을 그대로 붙여 넣는다.

```
settings 폴더를 파악해서 해당 프로젝트 경로에 세팅 완료해줘.
```

에이전트는 이 한 줄을 받으면 **이 문서를 열어 STEP 0부터 순서대로 실행**한다.
`PROJECT_ROOT` 는 이 `settings` 폴더의 부모 — 즉 **`graph_starter_kit`** 이다.

---

## 빠른 시작 — 사람이 직접 할 때 (약 5분)

> **에이전트는 이 절을 건너뛰고 0절(규약)부터 따른다.** 아래는 교육생이 손으로 할 때의 최단 경로다.
> 막히면 이 순서로 찾는다 — 설치 실패: STEP 4 표 · `ENV_LINK: FAIL`: STEP 5 표 ·
> `ENV_VERIFY: FAIL`: STEP 6 표(C01~C12) · Studio: STEP 8·9 표 · 그 밖: 부록 B.

**먼저 필요한 것**

| 항목 | 필요한가 | 왜 |
|---|---|---|
| Python **3.12** | **필수** | 강사 환경과 같은 조합. 없으면 STEP 1 |
| LangSmith 계정 + API 키 | **필수** | 세팅 게이트(C06·C09)가 확인한다. Studio 화면도 smith.langchain.com 에 있다 |
| Claude Code (`claude`) **구독 로그인** | **필수** | `live` 조사뿐 아니라 **`replay` 에서도 루프 C(정성 3회)가 `claude -p` 를 부른다** (C11) |
| Docker · C 컴파일러 · `requirements-optional.txt` | 필요 없음 | `langgraph dev` 는 인메모리로 뜬다. 선택 패키지는 설치하지 않는다(STEP 4). **Intel Mac 만 예외가 있다** (STEP 1 상자) |

**Windows (PowerShell)** — 킷 폴더(`graph_starter_kit`)에서

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install --require-virtualenv -r settings\requirements.lock.txt
notepad .env                                               # LANGSMITH_API_KEY 한 줄을 본인 키로 바꾸고 저장
.\.venv\Scripts\python.exe settings\scripts\link_env.py    # 마지막 줄 ENV_LINK: PASS
.\.venv\Scripts\python.exe settings\scripts\verify_env.py  # 마지막 줄 ENV_VERIFY: PASS
```

**macOS / Linux** — 킷 폴더에서

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install --require-virtualenv -r settings/requirements.lock.txt
nano .env                                                  # LANGSMITH_API_KEY 한 줄을 본인 키로
.venv/bin/python settings/scripts/link_env.py              # ENV_LINK: PASS
.venv/bin/python settings/scripts/verify_env.py            # ENV_VERIFY: PASS
```

**그다음부터는 창을 열 때마다 가상환경을 먼저 켠다.** 킷 문서(`README.md` 등)의 `python …` ·
`langgraph dev` 명령은 **가상환경이 켜진 창**을 전제로 한다. 켜지 않고 `python` 을 부르면
시스템 Python 이 잡혀 `verify_env.py` 가 C01~C05 를 전부 FAIL 로 낸다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force   # 이 창에서만 적용
.\.venv\Scripts\Activate.ps1                                         # Windows
```
```bash
source .venv/bin/activate                                            # macOS / Linux
```

켠 창의 **킷 폴더**에서 `langgraph dev --no-reload --port 2024` 로 Studio 를 띄운다 (STEP 9-2 참고).
끝나면 `Ctrl+C` 로 끈다. LangSmith 에 노드별 트레이스가 실제로 쌓이는지까지 보려면 STEP 7(스모크)을 한 번 돌린다.

---

## 0. 이 문서를 실행하는 AI 에이전트를 위한 규약

아래 R1~R11은 **모든 STEP에 우선한다.**

| # | 규약 |
|---|---|
| **R1** | `PROJECT_ROOT` = **이 파일이 들어 있는 `settings` 폴더의 부모 디렉터리** (= 교육생이 내려받은 `graph_starter_kit`). 맨 처음에 절대 경로로 확정하고, 이후 모든 명령에 그 절대 경로를 쓴다. 상대 경로로 추측하지 않는다. |
| **R2** | STEP은 **번호 순서대로**. 각 STEP 끝의 **게이트(G*)가 PASS가 아니면 다음 STEP으로 넘어가지 않는다.** 실패하면 그 STEP의 "실패 시 조치"만 수행하고 최대 2회 재시도한다. 그래도 실패하면 **중단하고 교육생에게 보고**한다. |
| **R3** | **`activate`에 의존하지 않는다.** 클로드 코드는 명령마다 셸이 초기화되므로 활성화 상태가 유지되지 않는다. 항상 **절대 경로 인터프리터**로 호출한다.<br>Windows: `<PROJECT_ROOT>\.venv\Scripts\python.exe`  ·  macOS/Linux: `<PROJECT_ROOT>/.venv/bin/python` |
| **R4** | **버전을 임의로 바꾸지 않는다.** `requirements.lock.txt`를 수정하거나 `--upgrade`로 개별 패키지를 올리지 않는다. lock에서 줄을 빼도 설치량은 줄지 않고 재현성만 잃는다(부록 A 참고). |
| **R5** | **API 키를 원문으로 출력하지 않는다.** `.env`를 `type`/`cat`/`Get-Content`로 통째로 출력하지 않는다. 키 확인은 **마스킹 출력을 내주는 제공 스크립트로만** 한다. |
| **R6** | STEP 0에서 확정한 **교육생 OS에 해당하는 명령만** 실행한다. 다른 OS 명령을 시험 삼아 돌리지 않는다. |
| **R7** | **파괴적 작업 전에는 교육생에게 확인**을 받는다 — 기존 `.venv` 삭제, 기존 `.env` 덮어쓰기, 패키지 대량 제거. (스크립트가 자동 백업을 남기는 경우는 그대로 진행해도 된다.) |
| **R8** | `langgraph dev`는 **블로킹 프로세스**다. 반드시 **백그라운드로 띄우고**, 확인이 끝나면 **반드시 종료**한다. 켜 둔 채 방치하지 않는다. |
| **R9** | STEP마다 **한 줄 요약**을 남기고, 마지막에 **STEP별 PASS/FAIL 표**로 보고한다. |
| **R10** | 네트워크·프록시로 설치가 막히면 **임의로 `--trusted-host`나 신뢰할 수 없는 인덱스를 쓰지 않는다.** 사내 프록시/인덱스 설정을 교육생에게 물어본다. |
| **R11** | **세팅 중에는 `.claude/settings.json` 을 만들지 않는다.** 그 권한 파일은 *실습용*이고, 켜는 시점은 **STEP 10 이후**다(STEP 10의 "실습용 권한 파일" 절). 세팅 순서를 흐트러뜨리지 않기 위한 규칙이다. 이미 만들어져 있어서 명령이 막히면, 지우지 말고 **교육생에게 알리고 세팅이 끝날 때까지 잠시 치워 둘지 물어본다.** |

---

## 1. 완료 정의 (Definition of Done)

아래 10개가 전부 충족되어야 "세팅 완료"다.

| # | 조건 | 확인 방법 |
|---|---|---|
| D1 | Python **3.12.x** 인터프리터 확보 (3.13 불가) | STEP 1 게이트 |
| D2 | `<PROJECT_ROOT>/.venv` 생성, 3.12 기반 | STEP 2 게이트 |
| D3 | `requirements.lock.txt`대로 설치, 의존성 충돌 0건 | `pip check` |
| D4 | 핵심 14종 패키지 버전이 lock과 **정확히 일치** | `verify_env.py` C03 |
| D5 | `langgraph` CLI + inmem 런타임 동작 | `verify_env.py` C04 |
| D6 | `<PROJECT_ROOT>/.env`에 LangSmith 키 연결, 인증 통과 | `verify_env.py` C06·C09 |
| D7 | 그래프 1회 실행 시 **노드별 span**이 LangSmith에 기록됨 | `smoke_graph.py` → 트레이스 URL |
| D8 | `langgraph dev` 기동 후 Studio에서 노드 실시간 관찰 가능 | STEP 8 게이트 |
| D9 | `claude` CLI가 **구독 인증**으로 로그인되어 있음 | `verify_env.py` C11 |
| D10 | **이 킷의 그래프**가 컴파일되고 Studio에 `travel` 로 등록됨 | STEP 9 게이트 |

---

## 2. 이 패키지에 들어 있는 파일

```
graph_starter_kit/                ← PROJECT_ROOT
├── .env                          ← 교육생이 본인 LangSmith 키를 넣는 곳 (유일한 개인 설정)
├── langgraph.json                ← 이 킷의 Studio 진입점 (graph: travel)
├── travel_graph/                 ← 실습 코드 (루프 골격 14 · 진단 2 노드)
│   └── detours/                  ← 규칙 처방 가지 — registry.py(한 줄 = 가지 하나) · 가지 모듈 · 실패 기록(log.py)
├── scripts/                      ← 검사기 · 실행 도구 (킷 소유)
│   └── detour_tests/             ← 처방 가지 시험지 (진단과 합격을 같은 시험지로 본다)
├── graph/                        ← 루프 킷 인계본
├── evidence/
│   ├── runs/                     ← 실행 증거 · 정성 회차 기록
│   ├── failures/                 ← 실패 기록 <thread_id>.jsonl (그래프를 돌리면 생긴다)
│   └── langgraph_dev.*.log       ← `langgraph dev` 서버 로그 (STEP 8 · 9 의 기동 명령이 남긴다)
├── .claude/
│   ├── settings.example.json     ← 실습용 권한 파일. **세팅이 끝난 뒤에** 켠다 (R11 · STEP 10)
│   └── skills/                   ← 실습 스킬 — graph-spec-builder · spec-sync · graph-run ·
│                                   evidence-review · graph-detour-builder (실습 STEP 6 · 조건부)
└── settings/
    ├── SETUP.md                  ← 지금 읽고 있는 단일 지시문
    ├── requirements.lock.txt     ← 유일한 설치 파일. 79개 전량 고정, 4계층으로 분류됨
    ├── requirements-optional.txt ← [설치 안 함] LLM 프로바이더 · SQLite 체크포인터 등
    ├── DEPENDENCY_REPORT.md      ← 버전 정합 실측 · 충돌 원인 분석 (읽기용)
    ├── .env.example              ← LangSmith 키 템플릿
    ├── scripts/
    │   ├── link_env.py           ← .env 탐색 · 검증 · 루트 연결 (표준 라이브러리만, 멱등)
    │   └── verify_env.py         ← C01~C12 검증기 (PASS/FAIL 게이트)
    └── smoke/
        ├── smoke_graph.py        ← 3노드 그래프 (ingest → analyze → report)
        └── langgraph.json        ← 스모크용 Agent Server 진입점
```

의존성 파일은 **`requirements.lock.txt` 하나뿐이다.** extras 표기(`[inmem]` 등)를 쓰지 않으므로
pip의 `-c` 제약 파일로도 그대로 재사용된다. 별도 `constraints.txt`가 필요 없는 이유다.

---

# STEP 0 — 운영 환경 진단

**목적:** 교육생 OS·아키텍처·설치된 Python·네트워크 상태를 먼저 확정한다. 이후 모든 STEP은 여기서 정한 분기를 따른다.

### Windows (PowerShell)

```powershell
"PROJECT_ROOT : " + (Resolve-Path ".").Path
"OS           : " + [System.Environment]::OSVersion.VersionString
"ARCH         : $env:PROCESSOR_ARCHITECTURE"
"PowerShell   : $($PSVersionTable.PSVersion)"
"--- 설치된 Python ---"
py -0p
"--- 네트워크 ---"
"pypi.org     : " + (curl.exe -s -o NUL -w "%{http_code}" --max-time 15 https://pypi.org/simple/)
"langsmith    : " + (curl.exe -s -o NUL -w "%{http_code}" --max-time 15 https://api.smith.langchain.com/info)
```

### macOS / Linux (bash · zsh)

```bash
echo "PROJECT_ROOT : $(pwd)"
echo "OS           : $(uname -srm)"
echo "SHELL        : $SHELL"
echo "--- 설치된 Python ---"
command -v python3.12 || echo "python3.12 없음"
python3 --version 2>/dev/null || echo "python3 없음"
echo "--- 네트워크 ---"
curl -s -o /dev/null -w "pypi.org     : %{http_code}\n" --max-time 15 https://pypi.org/simple/
curl -s -o /dev/null -w "langsmith    : %{http_code}\n" --max-time 15 https://api.smith.langchain.com/info
```

### 게이트 G0

- `PROJECT_ROOT`를 **절대 경로로 확정**했다.
- `pypi.org`, `langsmith` 모두 **HTTP 200**이다.
- 설치된 Python 목록을 파악했다 (3.12 유무를 기록).

**실패 시 조치**

| 증상 | 조치 |
|---|---|
| `pypi.org`가 200이 아님 | 사내 프록시/방화벽. 교육생에게 프록시 주소 또는 사내 PyPI 미러 주소를 물어본다. **임의로 인증서 검증을 끄지 않는다.** |
| `langsmith`가 200이 아님 | 방화벽이 `*.smith.langchain.com`을 막는 경우다. 네트워크 담당자에게 허용 요청. 설치 자체는 계속 진행하되 STEP 6~8은 보류. |
| `py` 명령이 없음 (Windows) | Python 런처 미설치. STEP 1로 진행. |

---

# STEP 1 — Python 3.12 확보

**목적:** 3.12.x 인터프리터를 확보한다.

> **왜 3.12인가.** 강사 환경(CPython 3.12.3)에서 설치·기동·트레이싱까지 검증한 조합이 이것뿐이다.
> `langgraph.json` 도 `"python_version": "3.12"` 로 선언되어 있다.
> **주의: 3.13 이나 3.11 로 venv 를 만들어도 lock 설치는 오류 없이 끝난다** (2026-09-27 실측 — 79개 모두 해석됨).
> `pyproject.toml` 의 `requires-python = ">=3.12,<3.13"` 은 킷을 `pip install -e .` 할 때만 걸리는데,
> 이 킷은 그 설치를 하지 않는다(STEP 9). 그래서 버전 차이는 **설치가 아니라 `verify_env.py` C01 에서 잡힌다.**
> C01 이 FAIL 이면 설치가 성공했더라도 `.venv` 를 3.12 로 다시 만든다.

### 이미 3.12가 있으면 (STEP 2로 바로 이동)

```powershell
py -3.12 --version                 # Windows
```
```bash
python3.12 --version               # macOS / Linux
```

`Python 3.12.x`가 나오면 설치 불필요.

> ### C 컴파일러는 필요 없다 — 단, Intel Mac 은 STEP 0 의 아키텍처를 확인한다
>
> lock 79개 중 **`forbiddenfruit==0.1.4` 만 wheel 이 없어** 설치 때 소스에서 빌드되지만,
> **순수 파이썬이라 C 컴파일러가 필요 없다** (C 확장은 `FFRUIT_EXTENSION=true` 일 때만 만든다 —
> 2026-09-27 소스 확인). 빌드 단계에서 pip 이 `setuptools` 를 인덱스에서 받아 오므로,
> 사내 미러를 쓴다면 거기에 `setuptools` 가 있어야 한다.
>
> 나머지 78개는 Windows x64 · Linux x86_64/aarch64 · **Apple Silicon Mac** 용 wheel 이 모두 있다.
> **예외는 Intel Mac(`uname -m` 이 `x86_64`)이다.** `cryptography==50.0.1` 이 Apple Silicon
> 용 wheel 만 내놓아 Intel Mac 에서는 소스 빌드(Rust 컴파일러 필요)로 떨어지고 대개 실패한다.
> STEP 0 의 `OS` 줄이 `Darwin … x86_64` 이면 **설치 전에 강사에게 알린다** (부록 B).

### 설치가 필요한 경우

**Windows**

```powershell
winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements
```

- 설치 후 **새 PowerShell 창**을 열어야 `py -3.12`가 잡힌다.
- `winget`이 없으면 <https://www.python.org/downloads/release/python-3129/> 에서 *Windows installer (64-bit)*를 받아 설치한다. 설치 화면에서 **"Add python.exe to PATH"를 반드시 체크**한다.

**macOS**

```bash
brew install python@3.12
# 경로가 안 잡히면:
export PATH="$(brew --prefix)/opt/python@3.12/bin:$PATH"
```

- Homebrew가 없으면 <https://brew.sh> 설치 후 진행하거나, python.org 3.12 pkg 설치본을 쓴다.

**Linux (Ubuntu · Debian)**

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv
```

- 저장소에 3.12가 없으면:
  ```bash
  sudo add-apt-repository -y ppa:deadsnakes/ppa && sudo apt update
  sudo apt install -y python3.12 python3.12-venv
  ```

### 게이트 G1

`py -3.12 --version` (Windows) 또는 `python3.12 --version` (macOS/Linux)이 **`Python 3.12.x`**를 출력한다.

**실패 시 조치**

| 증상 | 조치 |
|---|---|
| 설치했는데 `py -3.12`가 없음 | 새 터미널을 연다. 그래도 없으면 `py -0p`로 실제 설치 경로를 확인해 그 절대 경로를 STEP 2에서 직접 쓴다. |
| `python --version`이 3.13을 가리킴 | **정상이다.** 기본 python이 3.13이어도 상관없다. STEP 2에서 `py -3.12` / `python3.12`로 venv를 만들면 된다. |
| `ensurepip` 오류 (Linux) | `python3.12-venv` 패키지가 빠졌다. 위 apt 명령을 다시 확인한다. |

---

# STEP 2 — 가상환경 `.venv` 생성

**목적:** `<PROJECT_ROOT>/.venv`를 3.12 기반으로 만든다. 시스템 Python을 절대 오염시키지 않는다.

### 기존 `.venv` 확인 (있는 경우에만)

```powershell
& "<PROJECT_ROOT>\.venv\Scripts\python.exe" --version      # Windows
```
```bash
"<PROJECT_ROOT>/.venv/bin/python" --version                # macOS / Linux
```

- **3.12.x가 나오면 재사용**한다 (STEP 3으로).
- 다른 버전이거나 깨져 있으면 **교육생에게 확인받고(R7)** 삭제 후 재생성한다.

### 생성

**Windows**
```powershell
py -3.12 -m venv "<PROJECT_ROOT>\.venv"
& "<PROJECT_ROOT>\.venv\Scripts\python.exe" --version
```

**macOS / Linux**
```bash
python3.12 -m venv "<PROJECT_ROOT>/.venv"
"<PROJECT_ROOT>/.venv/bin/python" --version
```

### 교육생이 직접 터미널을 쓸 때만 필요한 활성화

에이전트는 R3에 따라 활성화 없이 절대 경로로 호출한다. 아래는 **교육생이 손으로 실습할 때**를 위한 것이다.

| 셸 | 명령 |
|---|---|
| PowerShell | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force` → `.\.venv\Scripts\Activate.ps1` |
| cmd.exe | `.venv\Scripts\activate.bat` |
| bash · zsh | `source .venv/bin/activate` |
| fish | `source .venv/bin/activate.fish` |

### 게이트 G2

```powershell
& "<PROJECT_ROOT>\.venv\Scripts\python.exe" -c "import sys;print(sys.version.split()[0]);print(sys.prefix)"
```

- 첫 줄이 **`3.12.x`**
- 둘째 줄이 **`<PROJECT_ROOT>\.venv`** (다른 경로면 잘못된 venv를 보고 있는 것)

**실패 시 조치**

| 증상 | 조치 |
|---|---|
| `Activate.ps1 ... 실행할 수 없습니다` | PowerShell 실행 정책 문제. 위 `Set-ExecutionPolicy -Scope Process` 명령을 먼저 실행. 이 설정은 **해당 창에서만** 유효하므로 시스템 정책을 바꾸지 않는다. |
| `venv` 생성 중 권한 오류 | OneDrive·네트워크 드라이브·회사 보안 폴더일 가능성. 로컬 디스크의 짧은 경로(예: `C:\lg`)로 프로젝트를 옮긴다. |
| 경로가 너무 길다는 오류 (Windows) | 260자 제한. 프로젝트를 `C:\` 가까운 짧은 경로로 옮긴다. |

---

# STEP 3 — pip 툴체인 정비

**목적:** 낡은 pip이 wheel을 못 찾아 소스 빌드로 빠지는 사고를 막는다.

**Windows**
```powershell
& "<PROJECT_ROOT>\.venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
```
**macOS / Linux**
```bash
"<PROJECT_ROOT>/.venv/bin/python" -m pip install --upgrade pip setuptools wheel
```

### 게이트 G3

`python.exe -m pip --version`이 정상 출력되고, 경로가 `<PROJECT_ROOT>/.venv` 안을 가리킨다.

> `setuptools`는 STEP 4에서 lock에 적힌 `84.0.0`으로 다시 맞춰진다. 여기서 최신으로 올라가도 문제없다.

---

# STEP 4 — 의존성 설치 (버전 정합)

**목적:** 강사 환경과 **동일한 버전 조합**을 만든다. 명령은 하나뿐이다.

```text
실측   79개 · 약 120MB · 1~3분 (회선·백신 검사에 따라. 2026-09-27 Windows 11, pip 캐시 있음: 2분 8초)
       디스크는 .venv 기준 약 140MB 를 본다
```

**Windows**
```powershell
& "<PROJECT_ROOT>\.venv\Scripts\python.exe" -m pip install --require-virtualenv -r "<PROJECT_ROOT>\settings\requirements.lock.txt"
& "<PROJECT_ROOT>\.venv\Scripts\python.exe" -m pip check
```
**macOS / Linux**
```bash
"<PROJECT_ROOT>/.venv/bin/python" -m pip install --require-virtualenv -r "<PROJECT_ROOT>/settings/requirements.lock.txt"
"<PROJECT_ROOT>/.venv/bin/python" -m pip check
```

> **79개가 설치되는 것이 정상이다.** 그중 32개는 `langgraph dev`(Studio 실시간 노드 추적)를
> 켜기 위한 전이 의존성이다. lock에서 그 줄들을 지워도 pip이 의존성으로 다시 끌어오므로
> 설치량은 그대로이고, **버전 고정만 사라진다.** 근거와 계층별 내역은 부록 A에 있다.
>
> **macOS · Linux 는 81개다.** `langgraph-api` 가 Windows 가 아닐 때만 `uvloop` · `httptools`
> 두 개를 더 요구하기 때문이다. lock 은 Windows 에서 계산해 이 둘이 고정돼 있지 않다 — 정상이며,
> `pip check` 가 통과하면 된다.

### 게이트 G4

`pip check`가 **`No broken requirements found.`**를 출력하고 종료 코드가 `0`이다.

**실패 시 조치**

| 증상 | 조치 |
|---|---|
| `forbiddenfruit` 빌드 실패 | 컴파일러 문제가 아니다(순수 파이썬). 빌드용 `setuptools` 를 인덱스에서 못 받은 경우다 — STEP 3 을 다시 하고, 사내 미러면 `setuptools` 가 있는지 확인한다. |
| `cryptography` 빌드 실패 · `can't find Rust compiler` (Intel Mac) | `cryptography==50.0.1` 에 Intel Mac 용 wheel 이 없다. **임의로 버전을 바꾸지 말고** 강사에게 보고한다 (부록 B). |
| `SSL: CERTIFICATE_VERIFY_FAILED` | 사내 SSL 검사 장비. **R10** — 임의로 검증을 끄지 말고 교육생에게 사내 CA 인증서 또는 프록시 설정을 확인한다. |
| `ResolutionImpossible` | 기존 `.venv`에 다른 버전이 남아 있을 수 있다. 교육생 확인 후 `.venv`를 지우고 STEP 2부터 다시. |
| 다운로드가 매우 느림 | 사내 PyPI 미러가 있으면 `--index-url`로 지정한다. 없으면 그대로 기다린다. |

### 선택 항목은 기본적으로 설치하지 않는다

`requirements-optional.txt`(LLM 프로바이더, SQLite 체크포인터 등)는 **강사 환경에 없는 패키지**다. 설치하는 순간 환경이 달라지므로 **커리큘럼이 명시적으로 지시할 때만** 설치한다. 이때 **lock을 제약 파일로 함께 걸어** 이미 맞춰 둔 79개가 몰래 올라가지 않게 막는다.

```powershell
& "<PROJECT_ROOT>\.venv\Scripts\python.exe" -m pip install --require-virtualenv `
    -r "<PROJECT_ROOT>\settings\requirements-optional.txt" `
    -c "<PROJECT_ROOT>\settings\requirements.lock.txt"
```

설치 후 STEP 6을 다시 돌린다. `ResolutionImpossible`이 나면 오류가 아니라 **정상 신호**다 — 해당 패키지가 `langchain-core==1.6.1`과 호환되지 않는다는 뜻이므로, **`-c`를 빼고 재시도하지 말고** 버전을 낮춰 잡거나 강사에게 확인한 조합을 쓴다.

---

# STEP 5 — LangSmith `.env` 연결

**목적:** LangSmith API 키를 프로젝트 루트에 연결한다. 키 값은 **절대 화면에 원문으로 찍지 않는다(R5).**

`.env` 는 기본적으로 **`<PROJECT_ROOT>/.env`**(= `graph_starter_kit/.env`)에 있다고 가정한다.
킷 배포본에 이 파일이 이미 들어 있고, 교육생은 **`LANGSMITH_API_KEY` 한 줄만** 본인 키로 바꾸면 된다.

```
LANGSMITH_API_KEY=lsv2_pt_...                    ← 각자 발급받아 채운다. 이 한 줄만 바꾸면 된다
LANGSMITH_TRACING=true                           ← 그대로
LANGSMITH_PROJECT=langgraph-travel-course        ← 뒤에 본인 식별자를 붙이면 좋다

GRAPH_CLAUDE_MODEL=sonnet                        ← 그대로. `claude -p` 호출 모델
GRAPH_CLAUDE_EFFORT=medium                       ← 그대로. 사고 강도
LANGGRAPH_NO_VERSION_CHECK=true                  ← 그대로. `langgraph dev` 의 업그레이드 권유를 끈다
```

`GRAPH_CLAUDE_*` 두 줄은 **조사(`collect_*`)와 정성 판정이 `claude -p` 를 부를 때 쓰는 값**이다
(코드 기본값과 같다 — `sonnet` · `medium` · 시간 제한 600초). 마지막 줄은 STEP 8 의 ⚠ 참고.
`link_env.py` 는 이런 항목을 **그대로 보존**하므로 손대지 않아도 된다.
의미와 다른 선택지는 `settings/.env.example` 에 적혀 있다 (배포본 `.env` 와 내용이 같다).

> **`.env` 를 읽는 것은 `langgraph dev` · `verify_env.py` · 스모크 그래프뿐이다.**
> `scripts/run_once.py` 는 `.env` 를 읽지 않으므로 터미널 실행은 **LangSmith 트레이스도 남지 않는다.**
> 트레이스는 Studio(`langgraph dev`) 실행에서 본다.

> **`claude` 실행 파일 경로는 적지 않는다.** `travel_graph/claude_cli.py` 가 후보를
> **실제로 실행해 보고** 쓸 수 있는 것을 고른다. 자동 탐색이 전부 실패하는 교육장에서만
> `GRAPH_CLAUDE_BIN` 한 줄을 더한다 (`settings/.env.example` 의 마지막 항목).
> 무엇이 잡히고 무엇이 왜 탈락했는지는 **킷 폴더에서** `python -m travel_graph.claude_cli` 로 본다
> (다른 폴더에서 돌리면 `No module named 'travel_graph'`). 이 명령은 `.env` 를 읽지 않으므로,
> `.env` 에 적은 `GRAPH_CLAUDE_BIN` 이 먹는지는 `verify_env.py` 의 C11 `실행 파일` 줄로 확인한다.

스크립트가 아래 순서로 탐색해 **처음 발견한 파일 하나만** 쓴다 (키가 채워졌는지는 그다음에 본다).
배포본에는 3번(`<PROJECT_ROOT>/.env`)이 들어 있으므로 **보통 3번에서 멈춘다** — 거기 키가
자리표시자면 4~6번에 진짜 키가 있어도 FAIL 이다. 다른 곳의 `.env` 를 쓰려면 `--source` 로 지정한다.

1. `--source`로 직접 지정한 경로
2. 환경 변수 `LANGSMITH_ENV_FILE`
3. `<PROJECT_ROOT>/.env` ← **기본 가정**
4. `<PROJECT_ROOT>/settings/.env`
5. `<PROJECT_ROOT>/../.env`
6. `<PROJECT_ROOT>/../test_graph/.env` (강사 작업 폴더용. 교육생은 해당 없음)

**Windows**
```powershell
& "<PROJECT_ROOT>\.venv\Scripts\python.exe" "<PROJECT_ROOT>\settings\scripts\link_env.py"
```
**macOS / Linux**
```bash
"<PROJECT_ROOT>/.venv/bin/python" "<PROJECT_ROOT>/settings/scripts/link_env.py"
```

스크립트가 하는 일:
- 원본 `.env`를 찾아 `LANGSMITH_API_KEY`가 실제 키인지(자리표시자가 아닌지) 확인
- `LANGSMITH_TRACING` / `LANGSMITH_PROJECT`가 없으면 기본값으로 보강
- `<PROJECT_ROOT>/.env`로 복사 (내용이 달라질 때만. 기존 파일은 `.env.bak`로 백업 — 백업은 한 벌만 남는다)
- `<PROJECT_ROOT>/.gitignore`에 `.env` · `.env.bak` · `.venv/` · `__pycache__/` · `.langgraph_api/` 등록
- 키 값은 `lsv2_pt_****  (총 51자)` 처럼 **앞머리와 길이만** 찍는다 (2026-09-27 실측: 원문 노출 0건)

기본 경로(3번)에서 바로 키를 채웠다면 원본과 대상이 같은 파일이라 `처리 : 이미 최신 상태 (변경 없음)` 이 정상이다.

### 게이트 G5

마지막 줄이 **`ENV_LINK: PASS`**다.

**실패 시 조치**

| 증상 | 조치 |
|---|---|
| `.env 원본을 찾지 못했습니다` | `settings/.env.example`을 `<PROJECT_ROOT>/.env`로 복사하고, <https://smith.langchain.com> → Settings → API Keys에서 발급한 키를 채운 뒤 재실행. |
| `자리표시자입니다` | 키가 아직 예시 문자열이다. 실제 키로 교체한다. |
| 원본 위치가 다름 | `--source "<실제 경로>"`로 직접 지정한다. |

> **교육생끼리 트레이스가 섞이지 않게** `LANGSMITH_PROJECT`에 본인 식별자를 붙이는 것을 권장한다. 예: `langgraph-travel-course-hong`

---

# STEP 6 — 설치 검증 (핵심 게이트)

**목적:** 여기서 PASS가 나야 비로소 "강사와 동일한 환경"이다.

**Windows**
```powershell
& "<PROJECT_ROOT>\.venv\Scripts\python.exe" "<PROJECT_ROOT>\settings\scripts\verify_env.py"
```
**macOS / Linux**
```bash
"<PROJECT_ROOT>/.venv/bin/python" "<PROJECT_ROOT>/settings/scripts/verify_env.py"
```

검사 항목:

| ID | 검사 | 실패하면 |
|---|---|---|
| C01 | Python 3.12.x 인터프리터 | STEP 1·2로 되돌아간다 |
| C02 | `<PROJECT_ROOT>/.venv`에서 실행 중 | 다른 인터프리터로 돌리고 있다. R3 위반 |
| C03 | 핵심 14종 버전이 lock과 일치 | STEP 4 재실행 |
| C04 | `langgraph` CLI + `langgraph-api` + `langgraph-runtime-inmem` | dev 3종 세트 중 하나가 빠졌다. STEP 4 재실행 |
| C05 | `StateGraph` / `get_stream_writer` / `langsmith.trace` / `dotenv` 임포트 | 설치 손상. `.venv` 재생성 |
| C06 | `<PROJECT_ROOT>/.env` 존재 + 필수 키 (마스킹 출력) | STEP 5 재실행 |
| C07 | `LANGSMITH_TRACING`이 참 값 | `.env`에서 `true`로 수정 |
| C08 | LangSmith 엔드포인트 도달 | 방화벽·프록시 확인 |
| C09 | API 키 인증 성공 | 키 재발급 후 STEP 5 재실행 |
| C10 | 스모크 그래프 컴파일 (노드 3개) | `settings/smoke/smoke_graph.py` 손상 여부 확인 |
| C11 | **`claude` CLI 존재 + 구독 인증** | Claude Code 설치 / `claude` 실행 후 `/login`. **어느 실행 파일이 채택됐는지**가 표의 `실행 파일` 줄에, 탈락한 후보와 그 이유가 그 아래에 찍힌다. **`replay` 로만 돌려도 필요하다** — 루프 C(정성 3회)는 모드와 무관하게 `claude -p` 를 부른다 |
| C12 | **`claude` 가 실제로 웹을 조회하는가** (live 실측) | 부록 B의 "live 인데 매번 replay" · "`[WinError 193]`" 항목을 본다. 급하면 `GRAPH_MODE=replay`로 실습은 계속 가능 |

부가 옵션:
- `--json` : 기계 판독용 JSON 출력
- `--offline` : 네트워크 검사(C08·C09·C12) 생략. 오프라인 교육장에서만 사용
- `--skip-claude` : C11·C12 생략. `claude` 설치·로그인 전에 나머지를 먼저 확인할 때만 쓴다.
  **실습 시작 전에는 C11 이 반드시 통과해야 한다** — 루프 C 는 `replay` 여도 `claude -p` 를 부른다

실측(2026-09-27, Windows 11): 전체 약 30초(그중 C12 약 25초) · `--offline --skip-claude` 약 2초.

### 게이트 G6

**판정 기준은 마지막 줄 하나다 — `ENV_VERIFY: PASS`.** 하나라도 FAIL이면 **다음 STEP으로 넘어가지 않는다.**

> **`경고 N` 은 실패가 아니다.** 검증기는 `통과 / 실패 / 경고`를 따로 센다.
> 옵션에 따라 이렇게 나오며, 모두 `ENV_VERIFY: PASS` 이므로 **게이트는 통과다.**
> 통과 개수를 세어 판정하지 않는다.
>
> | 실행 | 요약 줄 |
> |---|---|
> | 옵션 없음 | `통과 12 / 실패 0 / 경고 0` (환경에 `ANTHROPIC_API_KEY` 가 있으면 C11 이 경고 → `통과 11 / 경고 1`) |
> | `--skip-claude` | `통과 10 / 실패 0 / 경고 2` |
> | `--offline` | `통과 9 / 실패 0 / 경고 3` |
> | `--offline --skip-claude` | `통과 8 / 실패 0 / 경고 4` |

> **C11과 C12는 다른 것을 본다.** C11은 "`claude`가 있고 로그인돼 있는가",
> C12는 "그 `claude`가 **실제로 웹을 조회하는가**". C11이 OK인데 C12가 FAIL인 경우가
> 실제로 있었다 — 그때 그래프는 죽지 않고 조용히 `replay`로 내려가므로, 화면은
> 정상인데 **매번 같은 인계본 자료가 나온다.** 가장 찾기 어려운 종류의 실패다.

> **다만 둘은 이제 같은 실행 파일을 본다.** 예전에는 C11이 후보를 실행해 보고 채택하는데
> `research.py`는 `shutil.which("claude")` 결과를 그대로 믿어서, Windows에서 실행되지 않는
> shim이 잡히면 **C11만 통과하고 C12가 `[WinError 193]`으로 실패**했다. 경로 탐색이 두 벌로
> 갈라져 있었기 때문이다. 2026-09-09부터 둘 다 `travel_graph/claude_cli.py` 하나만 쓴다.
>
> 이 실패는 PATH·PATHEXT·설치 방식에 따라 갈려 **강사 PC에서는 재현되지 않는다.**
> 그래서 C11이 **탈락한 후보와 그 이유를 표에 함께 싣는다.** 교육생 화면의 그 줄들이
> 원격으로 판단할 유일한 단서다.

> **C11은 pip 패키지 검사가 아니다.** `claude`는 npm 으로 설치되는 CLI이므로
> `requirements.lock.txt`와 무관하고, 그래서 C03이 아니라 별도 게이트다.
>
> C11이 확인하는 것은 4개 키뿐이다 — `loggedIn` · `authMethod` · `apiProvider` ·
> `subscriptionType`. `claude auth status` 원문에는 email·orgId 도 들어 있지만
> **읽지도 출력하지도 않는다(R5).**
>
> `authMethod`가 **`claude.ai`**이면 구독 인증이다. 원하는 상태다.
> 환경에 `ANTHROPIC_API_KEY`가 있으면 C11이 **WARN**을 낸다 — API 키가 구독 인증을
> 이기기 때문이다. 그래프의 서브프로세스 호출은 이 값을 제거하고 실행하지만,
> 다른 도구가 조용히 API 과금으로 넘어갈 수 있으므로 알려 준다.

---

# STEP 7 — 노드별 트레이싱 실증

**목적:** "그래프를 돌리면 노드마다 span이 LangSmith에 실시간으로 쌓인다"를 눈으로 확인한다. **LLM을 호출하지 않으므로 토큰 비용은 0이다.**

**Windows**
```powershell
& "<PROJECT_ROOT>\.venv\Scripts\python.exe" "<PROJECT_ROOT>\settings\smoke\smoke_graph.py"
```
**macOS / Linux**
```bash
"<PROJECT_ROOT>/.venv/bin/python" "<PROJECT_ROOT>/settings/smoke/smoke_graph.py"
```

기대 출력(요약):

```
 [  0.01s] custom   {'event': 'ingest:start'}
 [  0.41s] NODE OK  ingest   -> raw='...', lines=[...]
 [  0.82s] NODE OK  analyze  -> counts={'DEBUG': 1, 'INFO': 2, ...}, invalid=1
 [  1.22s] NODE OK  report   -> report='총 7줄 / ...'
 트레이스 : https://smith.langchain.com/o/.../r/...
SMOKE_TRACE: PASS
```

- `NODE OK` 줄 = **노드 단위 상태 업데이트** (`stream_mode="updates"`)
- `custom` 줄 = **노드 안에서 흘려보낸 진행 이벤트** (`get_stream_writer()`)
- 두 줄기가 함께 보인다는 것은, 긴 작업을 하는 노드가 "멈춘 것인지 진행 중인지" 구분 가능하다는 뜻이다.

### 게이트 G7

- 마지막 줄이 **`SMOKE_TRACE: PASS`**
- **`트레이스 : https://smith.langchain.com/o/.../r/...` 형태의 실제 URL이 찍혔다**
- 출력된 **트레이스 URL을 교육생이 브라우저로 열어**, `smoke_run` 아래에 **`ingest` / `analyze` / `report` 세 개의 span**이 보이는 것을 확인한다.

> **`SMOKE_TRACE: PASS` 만으로 판정하지 않는다.** 이 문구는 *그래프가 돌았다*는
> 뜻이지 *트레이스가 전송됐다*는 뜻이 아니다. 키가 잘못돼 전송이 401/403으로
> 막혀도 그래프 자체는 정상으로 돌기 때문에 **PASS 가 찍힌다.**
> 그때는 URL 자리에 `https://smith.langchain.com/ -> 프로젝트 '...' 에서 확인`
> 이라는 **안내 문구만** 나온다. 그러면 G6의 C09로 돌아간다.

**실패 시 조치**

| 증상 | 조치 |
|---|---|
| `트레이싱이 꺼져 있습니다` 경고 | `.env`의 `LANGSMITH_TRACING=true` 확인 후 재실행 |
| 트레이스 URL은 나오는데 화면이 비어 있음 | 전송이 배치로 이뤄져 **몇 초 지연**된다. 새로고침한다. 그래도 없으면 LangSmith 좌상단 **워크스페이스**와 `LANGSMITH_PROJECT` 이름이 맞는지 확인한다. |
| 401 / 403 | 키 만료 또는 워크스페이스 불일치. 재발급 후 STEP 5부터 다시. |

---

# STEP 8 — Studio 실시간 추적 (`langgraph dev`)

**목적:** 로컬 Agent Server를 띄워 **그래프 구조와 노드별 입출력을 화면에서 실시간으로** 본다. dev 3종 세트(`langgraph-cli` + `langgraph-api` + `langgraph-runtime-inmem`)가 인메모리 런타임을 제공하므로 **Docker가 필요 없다.**

> ### ⚠ 가장 흔한 실패 원인
> `langgraph.json` 안의 상대 경로(`./smoke_graph.py`, `../../.env`)는 **config 파일 위치가 아니라 "현재 작업 디렉터리" 기준으로 해석된다.**
> 따라서 **반드시 `langgraph.json`이 있는 폴더로 이동한 뒤** 실행해야 한다. `--config`로 다른 폴더의 설정을 가리키면
> `GraphLoadError: Failed to load graph 'smoke' from ./smoke_graph.py: [Errno 2] No such file or directory` 로 기동이 멈춘다 (2026-09-27 재현).
>
> ### ⚠ 업그레이드 권유는 따르지 않는다 (R4)
> `.env` 에 `LANGGRAPH_NO_VERSION_CHECK=true` 가 없으면 기동 로그에
> `A newer version of langgraph-api is available … (pip install -U langgraph-api)` ·
> `langgraph-api 0.13.3 is End of Life … You should upgrade immediately` 가 찍힌다.
> **따르지 않는다.** dev 3종 세트는 lock 으로 함께 고정돼 있어 하나만 올리면 Studio 가 깨질 수 있다.
> 로컬(127.0.0.1) 실습 서버라 그대로 써도 된다. 배포본 `.env` 에는 이 안내를 끄는 줄이 들어 있다.

### 기동 (반드시 백그라운드 — R8)

`langgraph dev`는 **Ctrl+C 를 누를 때까지 끝나지 않는다.** 앞에서 그냥 실행하면
셸이 붙잡혀 다음 명령을 낼 수 없고, 도구 타임아웃까지 기다리게 된다.

> **에이전트라면:** 이 명령을 **백그라운드 실행 기능으로** 띄운다 (Claude Code 라면
> Bash 도구의 백그라운드 옵션). 그리고 **그 작업 ID를 기억해 두었다가 게이트 확인이
> 끝나면 반드시 정지시킨다.** 아래 OS별 명령은 **교육생이 손으로 할 때**의 것이다.

**Windows** — 프로세스를 띄우고 **PID를 받아 둔다** (서버 로그는 `evidence\` 의 두 파일에 남는다)
```powershell
New-Item -ItemType Directory -Force "<PROJECT_ROOT>\evidence" | Out-Null
$srv = Start-Process -PassThru -WindowStyle Hidden `
    -FilePath "<PROJECT_ROOT>\.venv\Scripts\langgraph.exe" `
    -WorkingDirectory "<PROJECT_ROOT>\settings\smoke" `
    -ArgumentList "dev","--no-browser","--no-reload","--port","2024","--host","127.0.0.1" `
    -RedirectStandardOutput "<PROJECT_ROOT>\evidence\langgraph_dev.out.log" `
    -RedirectStandardError "<PROJECT_ROOT>\evidence\langgraph_dev.err.log"
"PID = $($srv.Id)"     # <- 종료할 때 쓴다
```
**macOS / Linux** — 뒤로 보내고 **PID를 받아 둔다** (서버 로그는 `evidence/langgraph_dev.log`)
```bash
mkdir -p "<PROJECT_ROOT>/evidence"
cd "<PROJECT_ROOT>/settings/smoke"
"<PROJECT_ROOT>/.venv/bin/langgraph" dev --no-browser --no-reload --port 2024 --host 127.0.0.1 \
    > "<PROJECT_ROOT>/evidence/langgraph_dev.log" 2>&1 &
echo "PID = $!"        # <- 종료할 때 쓴다
```

> **서버 로그는 기동이 안 될 때 가장 먼저 여는 곳이다.** `GraphLoadError` · 포트 점유 · Traceback 이
> 여기 남는다 (Windows 는 두 파일을 다 본다 — 서버 로그 본문은 `langgraph_dev.out.log`, 표준 오류로
> 나간 것은 `langgraph_dev.err.log`). 로그 경로는 절대 경로로 적는다 —
> `-RedirectStandard*` 의 상대 경로는 `-WorkingDirectory` 가 아니라 **지금 PowerShell 창의 위치** 기준이다.
> 에이전트가 백그라운드 실행 기능으로 띄웠다면 그 작업의 출력이 곧 서버 로그다.

### 기동 확인

기동에 **수 초~30초** 걸린다 (2026-09-27 실측 약 3초). 바로 확인하면 연결 실패가 뜨는 것이 정상이므로, 200이
나올 때까지 몇 초 간격으로 다시 확인한다.

```powershell
curl.exe -s -o NUL -w "%{http_code}`n" --max-time 5 http://127.0.0.1:2024/ok
```

`200`이 나오면 준비 완료. 등록된 그래프 확인 (OS 공통 · 따옴표 문제 없음):

```powershell
& "<PROJECT_ROOT>\.venv\Scripts\python.exe" -c "import json,urllib.request as u; r=u.urlopen(u.Request('http://127.0.0.1:2024/assistants/search', data=json.dumps({'limit':10}).encode(), headers={'Content-Type':'application/json'})); print([a['graph_id'] for a in json.load(r)])"
```

→ `['smoke']`가 나와야 한다.

### 교육생이 볼 화면

브라우저에서 아래 주소를 연다.

```
https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
```

- 왼쪽에 **`ingest → analyze → report` 그래프**가 그려진다.
- 입력 `{}` 또는 `{"raw": "..."}`로 실행하면 **노드가 하나씩 점등되며** 각 노드의 입출력 상태가 오른쪽에 실시간으로 쌓인다.
- 같은 실행이 LangSmith 프로젝트에도 트레이스로 남는다 (서버가 `langgraph.json` 의 `env` 로 `.env` 를 싣기 때문이다).
  스모크 그래프는 멈추는 곳이 없어 실행 하나가 트레이스 하나다. 킷 그래프는 게이트(`interrupt`)에서
  트레이스가 나뉘므로 LangSmith 의 **Threads** 탭에서 `thread_id` 로 이어 본다 (`GRAPH_CONTRACT.md` 8절).

### 종료 (반드시 수행 — R8)

남겨 두면 포트 2024가 계속 점유되어 **STEP 9가 `[WinError 10048]`로 실패한다.**

**PID를 알고 있을 때** (위에서 받아 둔 값)
```powershell
Stop-Process -Id <PID> -Force                      # Windows
```
```bash
kill <PID>                                         # macOS / Linux
```

**PID를 잃어버렸을 때 — 포트로 찾아 죽인다**
```powershell
Get-NetTCPConnection -LocalPort 2024 -State Listen |
    Select-Object -ExpandProperty OwningProcess |
    ForEach-Object { Stop-Process -Id $_ -Force }   # Windows
```
```bash
lsof -ti tcp:2024 | xargs kill                     # macOS / Linux
```

종료됐는지는 `/ok` 확인이 **200이 아닌 값**(연결 실패)을 내는 것으로 판정한다.

### 게이트 G8

- `http://127.0.0.1:2024/ok` → **200**
- 등록된 그래프 목록에 **`smoke`** 포함
- 확인 후 **서버 종료 완료**

**실패 시 조치**

| 증상 | 조치 |
|---|---|
| `/ok` 가 계속 200 이 아님 (기동 실패) | 서버 로그(`evidence\langgraph_dev.out.log` · `.err.log` · macOS/Linux `evidence/langgraph_dev.log`)의 마지막 줄을 본다. 아래 표의 어느 증상인지 거기서 갈린다. |
| `GraphLoadError … smoke_graph.py … No such file or directory` | 작업 디렉터리가 틀렸다. 위 ⚠ 항목대로 `settings/smoke`로 이동한 뒤 실행. |
| 로그에 `pip install -U langgraph-api` · `End of Life` | 업그레이드하지 않는다(R4). 위 ⚠ 항목 참고. |
| `[WinError 10048]` / `Address already in use` | 포트 2024 점유. `--port 2025`로 바꾸고 Studio URL의 `baseUrl`도 함께 바꾼다. |
| Studio 화면이 로컬 서버에 연결되지 않음 | 브라우저가 `https` 페이지에서 `http://127.0.0.1`을 막는 경우다. `--tunnel` 옵션으로 공개 터널을 쓰거나, 크롬에서 해당 사이트의 "안전하지 않은 콘텐츠"를 허용한다. |
| 방화벽 팝업 | `127.0.0.1` 바인딩이므로 외부 노출은 없다. 로컬 허용으로 충분하다. |

---

# STEP 9 — 이 킷의 그래프 등록 확인

**목적:** 스모크가 아니라 **실습 킷 자신의 그래프**가 Studio에 뜨는지 확인한다.

> **editable 설치는 필요 없다.** `langgraph.json` 의 `"dependencies": ["."]` 가
> 프로젝트 루트를 경로에 넣어 주므로 `travel_graph` 가 그대로 임포트된다.
> `pip install -e .` 를 돌리면 lock 으로 맞춰 둔 버전이 움직일 수 있다(R4).

### 9-1. 그래프가 컴파일되는지 (서버 없이)

**Windows**
```powershell
Set-Location "<PROJECT_ROOT>"
$env:GRAPH_MODE="replay"
& "<PROJECT_ROOT>\.venv\Scripts\python.exe" -c "from travel_graph.build import graph; print('NODES', len(graph.get_graph().nodes))"
```
**macOS / Linux**
```bash
cd "<PROJECT_ROOT>"
GRAPH_MODE=replay "<PROJECT_ROOT>/.venv/bin/python" -c "from travel_graph.build import graph; print('NODES', len(graph.get_graph().nodes))"
```

→ 배포본 그대로면 `NODES 24` 가 나온다 — 노드 22개(루프 골격 14 + 진단 2 + 규칙 처방 가지 3개 × 2) +
`__start__` + `__end__`.

> **개수는 바뀔 수 있다.** 처방 가지는 등록부(`travel_graph/detours/registry.py`) 한 줄마다
> 노드 두 개(`fix_<이름>` · `test_<이름>`)가 붙는다. 교육생이 실습 STEP 6(처방 가지 추가 · 조건부)에서
> 가지를 하나 더하면 `NODES 26` 이 된다 (**22 + 2 × 더한 가지 수** + `__start__` · `__end__`).
> 그래서 이 게이트는 **개수가 아니라 구성**으로 판정한다. 아래 구성 확인을 함께 돌린다.

**구성 확인** (9-1 과 같은 작업 디렉터리 · `GRAPH_MODE=replay`. 출력은 영문이라 콘솔 코드페이지와 무관하다)

**Windows**
```powershell
Set-Location "<PROJECT_ROOT>"
$env:GRAPH_MODE="replay"
& "<PROJECT_ROOT>\.venv\Scripts\python.exe" -c "from travel_graph.build import graph, SPINE, DIAGNOSE; from travel_graph import detours; n=set(graph.get_graph().nodes)-{'__start__','__end__'}; d={x for k in detours.ALL for x in (k.fix_node,k.test_node)}; print('NODES', len(n)+2, '| spine', len(set(SPINE)&n), '/ 14 | diagnose', len(set(DIAGNOSE)&n), '/ 2 | detours', len(detours.ALL), '=', len(d&n), 'nodes | extra', sorted(n-set(SPINE)-set(DIAGNOSE)-d) or 'none')"
```
**macOS / Linux**
```bash
cd "<PROJECT_ROOT>"
GRAPH_MODE=replay "<PROJECT_ROOT>/.venv/bin/python" -c "from travel_graph.build import graph, SPINE, DIAGNOSE; from travel_graph import detours; n=set(graph.get_graph().nodes)-{'__start__','__end__'}; d={x for k in detours.ALL for x in (k.fix_node,k.test_node)}; print('NODES', len(n)+2, '| spine', len(set(SPINE)&n), '/ 14 | diagnose', len(set(DIAGNOSE)&n), '/ 2 | detours', len(detours.ALL), '=', len(d&n), 'nodes | extra', sorted(n-set(SPINE)-set(DIAGNOSE)-d) or 'none')"
```

→ 배포본: `NODES 24 | spine 14 / 14 | diagnose 2 / 2 | detours 3 = 6 nodes | extra none` (2026-09-27 실측 동일)

> **Windows 에서 손으로 했다면 확인 뒤 `Remove-Item Env:GRAPH_MODE` 로 지운다.** `$env:GRAPH_MODE`
> 는 그 창이 닫힐 때까지 남아서, 같은 창에서 나중에 켠 `langgraph dev` 가 **조용히 `replay` 로 돈다.**
> (bash 의 `GRAPH_MODE=replay 명령` 은 그 한 줄에만 적용되므로 지울 필요가 없다.)

**루프 골격 14개와 진단 2개가 다 있고, 나머지가 등록된 처방 가지의 `fix_` · `test_` 노드뿐이면 정상이다**
(`spine 14 / 14` · `diagnose 2 / 2` · `detours N = 2N nodes` · `extra none`).
`extra` 에 이름이 찍히면 등록부 밖의 노드가 끼어든 것이다.

  | 나온 값 | 뜻 |
  |---|---|
  | `NODES 24` | 지금 킷. 루프 골격 14 + 진단 2 + 처방 가지 3개(`encoding` · `image_dead` · `image_spec`) × 2 |
  | `NODES 26` · `28` … | 실습 STEP 6 에서 처방 가지를 더한 킷 (하나에 +2). 구성 확인이 `extra none` 이면 정상 |
  | `NODES 16` | 처방 가지 이전 킷 (루프 골격 14개뿐). 재수집이 `repair_city` + `repair_country` fan-out 이다 |
  | `NODES 15` | 국가 소개 재수집이 없던 킷 (`repair_country` 를 넣기 전) |
  | `NODES 14` | 그 이전 킷 (재수집이 `research` 노드 하나였다) |
  | `NODES 12` | 루프 C 이전 킷. `graph/03_CONTRACT.json` 에 `quality_contract` 가 있는지 확인한다 |

  노드 목록까지 보려면 `print(sorted(graph.get_graph().nodes))` 를 쓴다.
  `__start__` · `__end__` 를 뺀 22개(배포본)가 아래와 같아야 한다.

```text
  루프 골격 14   read_request · collect_country · select_cities · collect_city
                 check_information · repair_city · repair_country · human_gate_a
                 build_page · check_page · human_gate_b · rebuilder
                 quality_pass · check_quality
  진단 2         diagnose_info · diagnose_page
  처방 가지 6    fix_encoding · test_encoding · fix_image_dead · test_image_dead
                 fix_image_spec · test_image_spec          ← 등록부 한 줄마다 fix_ · test_ 두 개
```

### 9-2. Studio에 등록되는지

`langgraph.json` 이 **프로젝트 루트**에 있으므로 루트에서 실행한다 (STEP 8의 ⚠ 참고).

**기동 방식은 STEP 8과 똑같다 — 반드시 백그라운드로 띄우고 PID를 받아 둔다(R8).**
바뀌는 것은 **작업 디렉터리뿐**이다: `settings\smoke` 가 아니라 `<PROJECT_ROOT>`.

**Windows** (서버 로그는 STEP 8 과 같은 `evidence\` 의 두 파일에 남는다)
```powershell
New-Item -ItemType Directory -Force "<PROJECT_ROOT>\evidence" | Out-Null
$srv = Start-Process -PassThru -WindowStyle Hidden `
    -FilePath "<PROJECT_ROOT>\.venv\Scripts\langgraph.exe" `
    -WorkingDirectory "<PROJECT_ROOT>" `
    -ArgumentList "dev","--no-browser","--no-reload","--port","2024","--host","127.0.0.1" `
    -RedirectStandardOutput "<PROJECT_ROOT>\evidence\langgraph_dev.out.log" `
    -RedirectStandardError "<PROJECT_ROOT>\evidence\langgraph_dev.err.log"
"PID = $($srv.Id)"
```
**macOS / Linux**
```bash
mkdir -p "<PROJECT_ROOT>/evidence"
cd "<PROJECT_ROOT>"
"<PROJECT_ROOT>/.venv/bin/langgraph" dev --no-browser --no-reload --port 2024 --host 127.0.0.1 \
    > "<PROJECT_ROOT>/evidence/langgraph_dev.log" 2>&1 &
echo "PID = $!"
```

> **`--no-reload` 를 반드시 붙인다.** 감시 기능(uvicorn · watchfiles)은 `*.py` 만 본다 — 그래프가
> 실행 중에 `output/` 에 쓰는 json · html 로는 재시작하지 않는다. 문제는 실행 중에 `.py` 가 바뀔 때다
> (코드 수정 · 실습 STEP 6 의 `new_detour.py` 가 파일을 만들 때). 감시가 켜져 있으면 서버가 다시 떠
> **돌던 run 이 끊긴다.** 그 대신 새 코드는 서버를 직접 다시 켜야 반영된다.

등록 확인:

```powershell
& "<PROJECT_ROOT>\.venv\Scripts\python.exe" -c "import json,urllib.request as u; r=u.urlopen(u.Request('http://127.0.0.1:2024/assistants/search', data=json.dumps({'limit':10}).encode(), headers={'Content-Type':'application/json'})); print([a['graph_id'] for a in json.load(r)])"
```

→ `['travel']` 이 나와야 한다. **확인 후 서버를 반드시 종료한다(R8)** — 종료 명령은
STEP 8의 "종료" 절과 같다 (PID 또는 포트 2024로 찾아 죽인다).

### 게이트 G9

- 9-1이 **`NODES 24`** 를 출력 (노드 22개 = 루프 골격 14 + 진단 2 + 처방 가지 3×2, + `__start__` + `__end__`).
  실습 STEP 6 에서 처방 가지를 더한 킷이면 22 + 2 × 더한 수 + 2
- 구성 확인이 **`spine 14 / 14 | diagnose 2 / 2`** 이고 **`extra none`** — 루프 골격 14개와 진단 2개가 있고,
  나머지가 등록된 처방 가지의 `fix_` · `test_` 뿐이다
- `/assistants/search` 결과에 **`travel`** 포함
- 서버 종료 완료

**실패 시 조치**

| 증상 | 조치 |
|---|---|
| `ModuleNotFoundError: travel_graph` | 작업 디렉터리가 `PROJECT_ROOT` 가 아니다. `langgraph.json` 이 있는 폴더에서 실행한다. |
| `HandoffMissing: graph/03_CONTRACT.json 이 없습니다` | 인계본이 비었다. 루프 킷 `output/graph/` 7개 파일을 `graph/` 에 복사한다. 배포본에는 예시가 들어 있다. |
| `NODES 16` 이 나옴 (구성 확인은 `ImportError` 로 멈춤 — `SPINE` · `detours` 가 없다) | 처방 가지 이전 킷이다. 배포본을 다시 받는다 — 문서(`CLAUDE.md` · `specs/`)는 22노드 기준이다. |
| 구성 확인의 `extra` 에 이름이 찍힘 | 루프 골격 · 진단 · 등록된 처방 가지 어디에도 없는 노드가 `build.py` 에 끼어들었다. 배포본이면 강사에게 보고한다. `python scripts/check_graph_shape.py` 11번(처방 가지 계약)이 같은 것을 잡는다. |
| `DetourRegistryError` | 처방 가지 등록부(`travel_graph/detours/registry.py`)가 잘못됐다 — 이름 형식 · 이름 겹침 · `loop` 값 · 빈 `title`. 에러 문장이 몇 번째 줄인지 알려 준다. 세팅 단계에서는 배포본 그대로여야 하므로 강사에게 보고한다. |
| 실행 중 서버가 계속 재시작 | `--no-reload` 를 빠뜨렸다 (감시는 `*.py` 만 보므로, 실행 중 `.py` 가 바뀌면 다시 뜬다). |
| `/ok` 가 200 이 아니거나 `['travel']` 이 안 나옴 | 서버 로그(`evidence\langgraph_dev.out.log` · `.err.log` · macOS/Linux `evidence/langgraph_dev.log`)의 Traceback 을 본다. |
| `[WinError 10048]` | 포트 점유. `--port 2025` 로 바꾸고 Studio URL 의 `baseUrl` 도 함께 바꾼다. |

---

# STEP 10 — 최종 보고

아래 표를 채워 교육생에게 보고한다.

| STEP | 내용 | 게이트 | 결과 |
|---|---|---|---|
| 0 | 운영 환경 진단 | G0 | |
| 1 | Python 3.12 확보 | G1 | |
| 2 | `.venv` 생성 | G2 | |
| 3 | pip 툴체인 | G3 | |
| 4 | 의존성 설치 (79개) | G4 | |
| 5 | `.env` 연결 | G5 | |
| 6 | 설치 검증 (C01~C12) | G6 | |
| 7 | 노드별 트레이싱 실증 | G7 | |
| 8 | Studio 실시간 추적 (스모크) | G8 | |
| 9 | **이 킷의 그래프 등록** | G9 | |

함께 안내할 것:

```text
가상환경 켜기   .\.venv\Scripts\Activate.ps1  (Windows)  ·  source .venv/bin/activate  (macOS/Linux)
                ← 아래 python · langgraph 명령은 전부 가상환경이 켜진 창을 전제로 한다
검증 재실행     python settings/scripts/verify_env.py
실습 준비도     python scripts/check_graph_readiness.py     ← NOT_READY 가 정상
실습 시작       claude  →  "STEP 1 진행해줘"
LangSmith       .env 의 LANGSMITH_PROJECT 이름으로 https://smith.langchain.com 에서 확인
```

> **`check_graph_readiness.py` 가 `NOT_READY`(exit 2) 를 내는 것은 정상이다.**
> 아직 STEP 을 하나도 안 했다는 뜻이지 환경 문제가 아니다.

### 실습용 권한 파일 켜기 (세팅이 전부 끝난 뒤에)

킷에는 `.claude/settings.example.json` 이 들어 있다. **실습 중에 권한 확인이
계속 뜨는 것을 막는 파일**이다 — `Read`·`Edit`·`Write`·`Bash`·`WebFetch` 를
`allow` 에 올려 두어서 실습 명령이 확인 없이 바로 돈다. 응답 언어(한국어)와
모델도 여기서 고정한다.

**이 파일은 세팅이 끝난 지금 켠다(R11).** 세팅 순서를 흐트러뜨리지 않기 위해서다.

**Windows**
```powershell
Copy-Item "<PROJECT_ROOT>\.claude\settings.example.json" "<PROJECT_ROOT>\.claude\settings.json"
```
**macOS / Linux**
```bash
cp "<PROJECT_ROOT>/.claude/settings.example.json" "<PROJECT_ROOT>/.claude/settings.json"
```

켠 뒤에는 실습 명령이 확인 없이 돈다. 되돌리려면 `settings.json` 을
`settings.json.off` 로 옮겼다가 필요할 때 되돌린다.

> **이 파일은 잠금장치가 아니다.** `allow` 만 있고 `deny` 는 없다. 정말로 보호
> 파일을 잠그고 싶다면 `deny` 를 직접 넣는다. 개념은 이렇다.
>
> ```json
> "permissions": {
>   "allow": ["Read", "Edit", "Write", "Bash", "WebFetch"],
>   "deny": ["Edit(scripts/**)", "Edit(graph/**)", "Read(.env)"]
> }
> ```
>
> 각각 *검사기를 못 고치게* · *인계본을 못 고치게* · *키를 못 읽게* 라는 뜻이다.
>
> **다만 `Edit(scripts/**)` 는 실습 STEP 6(처방 가지 추가 · 조건부)을 막는다.** 그 STEP 에서 교육생이
> 처방 가지 시험지 `scripts/detour_tests/test_<이름>.py` 를 직접 채우기 때문이다. `deny` 를
> 넣어 배포한다면 계약 검사기만 잠그도록 좁힌다 — 예: `"Edit(scripts/check_*.py)"`.
>
> **기본값에 넣지 않은 이유.** `deny` 는 걸릴 때마다 확인을 띄우고, 강의는 시간이
> 정해져 있다. 확인 창이 반복되면 수강생이 실습 흐름을 놓친다. 그래서 이 킷은
> 검사기를 **규칙으로** 지킨다 — `CLAUDE.md` 7절이 보호 파일 목록을 명시하고,
> 그 목록을 어기면 회귀 검사(`scripts/selftest/run_graph_regression.py`)에서
> 드러난다. 강의 성격상 더 강하게 잠가야 한다면 위 `deny` 를 넣어 배포한다.
>
> 참고로 **루프 킷에는 해시 잠금이 따로 있다** — `python scripts/check_loop_readiness.py --lock`
> 이 보호 파일의 해시를 `state/spec_lock.json` 에 적어 두고, 이후 파일이 바뀌면
> 준비도 검사가 잡아낸다. 그래프 킷에는 그 잠금이 없다.

---

# 부록 A. 버전 정합 매트릭스

**기준 환경: CPython 3.12.3 / Windows 11 x64.** 아래 조합은 실제로 설치·기동·트레이싱까지 검증된 조합이다.

| 패키지 | 고정 버전 | 역할 | 어긋나면 생기는 일 |
|---|---|---|---|
| **Python** | `3.12.x` | 인터프리터 | 3.13·3.11 에서도 lock 설치는 되지만 검증되지 않은 조합이다. `verify_env.py` C01 이 FAIL 로 잡는다 |
| `langgraph` | `1.2.11` | `StateGraph`·노드·엣지·스트리밍 런타임 | 그래프 API 시그니처가 달라져 예제가 안 돌아간다 |
| `langgraph-checkpoint` | `4.2.0` | 상태 직렬화·체크포인터 인터페이스 | 스레드 재개·`InMemorySaver` 동작 불일치 |
| `langgraph-prebuilt` | `1.1.0` | 사전 제작 노드(ToolNode 등) | `langgraph` 1.2.x와 쌍으로 움직인다 |
| `langgraph-sdk` | `0.4.4` | Agent Server 클라이언트 | Studio ↔ 로컬 서버 프로토콜 불일치 |
| `langgraph-cli` | `0.4.31` | `langgraph dev` 명령 | 아래 두 개가 함께 없으면 Docker를 요구하며 기동 실패 |
| `langgraph-api` | `0.13.3` | 로컬 Agent Server 본체 | Studio가 그래프 스키마를 못 읽는다 |
| `langgraph-runtime-inmem` | `0.33.3` | 인메모리 런/스레드 저장소 | Docker 없이 띄우는 경로가 사라진다 |
| `langchain-core` | `1.6.1` | Runnable 기반 클래스. **노드 span이 여기서 생성된다** | 부모/자식 span이 끊겨 LangSmith에 평평한 run만 남는다 |
| `langchain-protocol` | `0.0.19` | core ↔ api 공용 메시지 스키마 | 직렬화 오류 |
| `langsmith` | `0.12.1` | 트레이스 전송 클라이언트 | `langchain-core` 1.x와 한 쌍. 한쪽만 올리면 추적이 조용히 끊긴다 |
| `pydantic` | `2.13.5` | State 스키마 검증 | v1 계열로 내려가면 `StateGraph` 스키마 추론이 깨진다 |
| `python-dotenv` | `1.2.3` | `.env` 로딩 | 키가 안 올라와 트레이싱이 꺼진 채 동작 |
| `PyYAML` | `6.0.3` | 워크플로 설정 파싱 | 실습 킷 설정 로더 실패 |
| `pytest` | `9.1.1` | 검증 테스트 | 실습 킷의 기대 실패 개수가 달라진다 |

**설계 원칙 2가지**

1. **트레이싱 체인은 한 덩어리다.** `langchain-core` · `langsmith` · `langchain-protocol` 중 하나만 올리면 트레이스가 **에러 없이 조용히** 망가진다. 그래서 셋을 같은 lock에 묶어 고정했다.
2. **`langgraph dev`는 3종 세트다.** `langgraph-cli` + `langgraph-api` + `langgraph-runtime-inmem`. 마이너 버전이 어긋나면 Studio가 그래프 스키마를 못 읽는다.

---

## 왜 79개인가 — lock을 줄일 수 없는 이유

교육생이 lock을 열어 보면 `grpcio`, `opentelemetry-*`, `cryptography`, `protobuf`, `prometheus_client` 같은
**그래프와 무관해 보이는 이름**이 잔뜩 보인다. 실제로 직접 의존성 9종에서 출발한 의존성 폐포를 계산해 본 결과는 다음과 같다.

| 계층 | 개수 | 정체 |
|---|---:|---|
| **T1** | 9 | 실습 코드가 직접 `import` / 실행하는 것 |
| **T2** | 3 | `langgraph dev` 3종 세트 (Studio 실시간 노드 추적) |
| **T3** | 35 | T1이 요구하는 전이 의존성 |
| **T4** | **32** | **T2가 요구하는 전이 의존성** ← "무관해 보이는" 것들이 전부 여기 |
| 합계 | **79** | **군더더기 0건.** lock에 있으나 폐포에 없는 항목 = 0, 폐포에 있으나 lock에 없는 항목 = 0 |

**핵심:** lock에서 T4의 줄을 지워도 **설치되는 패키지 수는 그대로다.** pip이 `langgraph-api`의
의존성으로 다시 끌어오기 때문이다. 달라지는 것은 단 하나 — **버전이 고정되지 않은 채로 들어온다.**
즉 지우면 환경이 가벼워지는 게 아니라 **재현성만 잃는다.**

T4를 실제로 없애는 유일한 방법은 **T2(`langgraph dev`)를 포기**하는 것이다. 그러면 79 → **44개**로 줄지만,
Studio에서 노드가 하나씩 점등되는 실시간 화면을 볼 수 없게 된다. 이 교육과정의 핵심 요구사항이므로 유지한다.
(LangSmith 웹 트레이스 자체는 T1만으로도 남는다. 사라지는 것은 Studio 실시간 화면뿐이다.)

T4의 정체를 굳이 풀어 보면 이렇다.

| 묶음 | 역할 |
|---|---|
| `uvicorn` `starlette` `sse-starlette` `watchfiles` | Agent Server 웹 서버와 SSE 스트리밍. **노드 상태가 브라우저로 흐르는 통로** |
| `opentelemetry-*` (7) `prometheus_client` | 서버 자체 계측 · 메트릭 |
| `grpcio-*` (3) `protobuf` `googleapis-common-protos` | 런타임 내부 RPC |
| `cryptography` `cffi` `pycparser` `PyJWT` | 서버 인증 계층 |
| `blockbuster` `forbiddenfruit` | 이벤트 루프 블로킹 탐지 |
| `croniter` `python-dateutil` `six` | 예약 실행(cron) 지원 |
| `structlog` `click` `pathspec` `cloudpickle` `jsonschema_rs` `setuptools` | 로깅 · CLI · 스키마 · 빌드 |

---

# 부록 B. 트러블슈팅

| 증상 | 원인 | 조치 |
|---|---|---|
| `Activate.ps1`을 실행할 수 없음 | PowerShell 실행 정책 | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force` (해당 창에서만 적용) |
| 설치는 됐는데 `import langgraph` 실패 | 시스템 Python으로 실행 중 | **R3** — 절대 경로 `.venv` 인터프리터로 호출. `verify_env.py` C02가 이를 잡아낸다 |
| `pip` SSL 인증서 오류 | 사내 SSL 검사 장비 | 사내 CA를 신뢰 저장소에 등록하거나 `PIP_INDEX_URL`로 사내 미러 지정. **검증을 끄지 않는다** |
| `forbiddenfruit` 빌드 실패 | 컴파일러 문제가 아니다 — 순수 파이썬 sdist 다. 빌드용 `setuptools` 를 인덱스에서 못 받았다 | STEP 3 재실행. 사내 미러면 `setuptools` 가 있는지 확인 |
| **Intel Mac 에서 `cryptography` 빌드 실패** (`can't find Rust compiler` 등) | `cryptography==50.0.1` 은 macOS 용 wheel 이 **Apple Silicon(arm64) 것뿐**이다 (2026-09-27 PyPI 확인). Intel Mac 은 소스 빌드로 떨어진다 | **임의로 버전을 바꾸지 말고** 강사에게 보고한다. 강사가 검증한 대체 핀을 내려 준다 |
| lock의 특정 전이 의존성에 해당 플랫폼 휠이 없음 | 드묾. Windows x64 · Linux x86_64/aarch64 · Apple Silicon 은 전부 wheel 이 있다 (2026-09-27 확인). 그 밖의 조합 | **임의로 버전을 바꾸지 말고** 실패한 패키지명과 pip 로그를 강사에게 보고한다. 강사가 해당 플랫폼에서 검증한 핀을 내려 준다 (교육생이 각자 다른 버전을 고르면 환경 통일이 무너진다) |
| **`[WinError 193]` / C11은 OK인데 C12만 FAIL** | Windows에서 `claude`를 찾기는 했는데 **실행할 수 없는 shim**을 골랐다. npm은 `claude`(`#!/bin/sh`로 시작하는 POSIX 스크립트) · `claude.cmd` · `claude.ps1`을 함께 만들고, 어느 것이 잡히는지는 PATH 순서·PATHEXT·Python 패치 버전·설치 방식에 따라 갈린다. **강사 PC에서는 재현되지 않는다** | `python -m travel_graph.claude_cli` 로 후보와 탈락 사유를 본다. 2026-09-09부터 `travel_graph/claude_cli.py`가 후보를 **실제로 실행해 보고** 채택하므로 죽은 shim은 자동으로 건너뛴다. 그래도 전부 실패하면 `.env`에 `GRAPH_CLAUDE_BIN=<claude 실행 파일 절대 경로>`. **전역 npm 폴더는 건드리지 않는다** — 다른 실습이 깨진다 |
| **정보량은 PASS인데 화면에 사진이 안 나옴** | 관광지 이미지를 `{"asset": {…}}`로 한 겹 감쌌다. 화면은 `image.url`을 직접 읽는다. 예전에는 루프 A가 두 형태를 다 통과시켜 **루프 A는 PASS, 루프 B만 SHORT**인 교착이 났다 (재수집이 안 걸리니 화면도 안 고쳐진다) | 2026-09-09부터 루프 A가 규격을 강제한다. `다낭/… 이미지: asset 으로 한 겹 싸여 있습니다`가 못 채운 칸에 뜨고 **그 도시만 재수집**으로 돌아간다. 규격은 국가 소개가 `{"asset": {…}}`, 관광지가 `{"url": …}` 직접 |
| **루프 킷에서 고른 배치가 그래프판에 안 나옴** (탭 · 툴바 없음) | `page.py`가 `accordion/drawer/accordion` 한 조합만 만들었다. 계약 검증과 인계본 수용 검사는 다른 조합도 허용하므로 **수집을 다 끝낸 뒤 `build_page`에서 죽었다** | 2026-09-09부터 렌더러가 계약의 `layout`을 그대로 만든다 — `D-페이지구성`의 세 선택지가 모두 그려지고 루프 B도 검사한다. 검사기는 원래 셋 다 검사할 줄 알았으므로 이제 계약·렌더러·검사기가 한 줄로 맞는다 |
| **`rebuild` 뒤 깨진 이미지가 남음** | `rebuilder`가 주소를 바꿔도 옛 `verified` 기록이 남아, 죽은 새 주소가 옛 `status: 200`으로 루프 A를 통과했다. 그 칸은 부족으로 잡히지 않으니 루프가 다시 보지 않는다 | 2026-09-09부터 `apply_fixes`가 **주소가 바뀐 자산만 다시 열어 본다.** 죽었으면 그 자리에서 부족이 되어 재수집으로 돌아가고, 멀쩡하면 새 기록으로 통과한다. 증거의 `applied[].rechecked`에 남는다 |
| **`live`인데 매번 `replay`로 내려감** | `claude -p` 호출에 `--tools`만 있고 `--allowedTools`가 없음. `dontAsk`는 "허용"이 아니라 "묻지 않음"이라 **거부**된다 | `verify_env.py` **C12**로 확인. `research.py`가 두 옵션을 함께 주도록 고쳐져 있다(2026-09-06). 그래도 FAIL이면 프로젝트 `.claude/settings.json`의 `deny`에 `WebSearch`가 없는지 본다 |
| **관광지 이미지가 전부 `status 0`** | `verify_asset()`의 User-Agent에 한글이 있으면 HTTP 헤더가 latin-1로 인코딩되지 못해 **요청을 보내기도 전에** 실패한다 | 헤더는 ASCII만 쓴다. 2026-09-06에 수정됨. 증상이 방화벽 차단과 똑같아 오진하기 쉽다 |
| `web_search_requests`가 0이라 검색이 안 된 줄 앎 | Claude Code의 WebSearch는 서버 도구가 아니라 **클라이언트 도구**다. 횟수는 `modelUsage.<모델>.webSearchRequests`에 적힌다 | 오독이다. `history` 꼬리표의 `실검색 N회`를 본다 (`research._search_count()`가 맞는 칸을 읽는다) |
| 도시 한 곳 수집이 5분을 넘겨 폴백 | 실제 검색이 돌면 한 도시가 2~6분 걸린다. 예전 기본 타임아웃(300초)이 짧았다 | 기본값을 600초로 올렸다. 더 필요하면 `GRAPH_CLAUDE_TIMEOUT=900` |
| **루프 A를 돌수록 못 채운 칸이 늘어남** | 재수집이 지적된 칸을 고치지 않고 처음부터 다시 만들었다 (`short_slots` 미사용) | 2026-09-08에 재수집을 `repair_city` 노드로 분리하고 **patch 방식**으로 바꿨다. `history`에 `repair_city[다낭]: 지적 N곳 · patch M건 적용`이 찍히면 정상, `collect_city[…]`가 찍히면 첫 수집이다 |
| 루프 A 한 바퀴가 10분 넘게 걸림 | `research_node`가 국가·도시 3개를 **순차로** 불렀다 | 2026-09-08에 그 노드를 없애고 `repair_city` **`Send` fan-out**으로 바꿨다. LangGraph가 병렬을 맡으므로 스레드를 쓰지 않는다. 지적된 도시만 도니 한 바퀴가 더 짧다 |
| **출처 링크가 늘 "화면에 없습니다"** | `page.esc()`가 `&`·`'`를 HTML 엔티티로 바꿔, 원문 대조하는 검사기가 못 찾았다 | HTML5 최소 escape로 고쳤다(2026-09-06). 출처 40/43 → 43/43 |
| **`국가상태` 패널이 60자 미달** | 확인은 했는데 해당 사항이 없는 칸(`checked: true, items: []`)을 "아직 채워지지 않았습니다"로 그렸다 | 확인한 사실을 화면에 적도록 고쳤다(2026-09-06) |
| 교육생마다 수집 결과가 다름 | `claude -p`가 킷의 `CLAUDE.md`와 개인 `~/.claude` 설정·훅·플러그인을 끌어온다 | `--safe-mode`로 커스터마이징만 끈다(기본 켜짐). 끄려면 `GRAPH_CLAUDE_SAFE_MODE=0` |
| **정성 회차가 `error_max_turns`로 ERROR** | 판정 1회가 쓰는 턴은 14~16인데 상한이 14였다(여유 0). 같은 입력에서도 흔들려 **어느 회차든** 걸릴 수 있었다 | 상한을 24로 올렸다(2026-09-06). 루프 C는 폴백이 없어 여기서 죽으면 회차가 통째로 ERROR가 된다 |
| `langgraph dev`가 `GraphLoadError … No such file or directory` | 작업 디렉터리가 `langgraph.json` 위치와 다름 | `langgraph.json`이 있는 폴더로 이동한 뒤 실행 (STEP 8 ⚠ 참고) |
| `langgraph dev`가 "업그레이드하라" · `End of Life` 를 띄움 | PyPI 최신판과 비교한 안내일 뿐이다 | **업그레이드하지 않는다(R4).** `.env` 에 `LANGGRAPH_NO_VERSION_CHECK=true` 를 두면 안 뜬다 |
| 켜지 않은 창에서 `python …` 이 C01~C05 FAIL | 가상환경을 켜지 않아 시스템 Python 이 잡혔다 | 빠른 시작의 "가상환경을 먼저 켠다" 참고. 또는 `.venv\Scripts\python.exe` 로 부른다 |
| 트레이스가 엉뚱한 프로젝트·워크스페이스로 감 | 시스템 환경변수에 예전 `LANGSMITH_*` · `LANGCHAIN_*` 가 남아 `.env` 보다 먼저 잡혔다 | 이름만 확인한다 (값은 찍지 않는다, R5): `Get-ChildItem Env: \| Where-Object Name -like 'LANG*' \| Select-Object Name` · `env \| cut -d= -f1 \| grep ^LANG`. 있으면 지우고 창을 새로 연다 |
| 포트 2024 점유 | 이전 `langgraph dev`가 안 죽음 | 프로세스 종료 또는 `--port 2025` 사용 |
| 트레이스가 LangSmith에 안 보임 | ① `LANGSMITH_TRACING`이 `false` ② 프로젝트/워크스페이스 불일치 ③ 배치 전송 지연 ④ 터미널 실행(`scripts/run_once.py`) — `.env` 를 읽지 않아 트레이스를 보내지 않는다 | ④ 면 정상이다 — 트레이스는 `langgraph dev`(Studio) 실행에서 본다. `verify_env.py` C07·C09로 ①②를 먼저 배제하고, ③은 몇 초 뒤 새로고침 |
| 킷 그래프 한 실행의 트레이스가 여러 개로 나뉨 | 게이트(`interrupt`)에서 멈추면 트레이스가 끝나고, 재개는 새 루트 트레이스다 | 정상. LangSmith **Threads** 탭에서 `thread_id` 로 이어 본다 (`GRAPH_CONTRACT.md` 8절) |
| 401 / 403 | 키 만료·오타·다른 워크스페이스 키 | 키 재발급 → STEP 5 재실행 |
| 한글이 `???`로 깨짐 (Windows) | 콘솔 코드페이지 | `chcp 65001` 실행, 또는 `$env:PYTHONUTF8=1` 설정 |
| 경로가 너무 길다는 오류 | Windows 260자 제한 | 프로젝트를 `C:\lg` 같은 짧은 경로로 이동 |
| 교육생끼리 트레이스가 섞임 | 같은 `LANGSMITH_PROJECT` 사용 | `.env`의 `LANGSMITH_PROJECT`에 본인 식별자를 붙인다 |
| 설치 후 갑자기 버전이 달라짐 | 다른 문서를 보고 `pip install -U`를 함 | **R4** — STEP 4를 lock으로 재실행해 되돌린다 |

---

# 부록 C. 초기화 · 재설치

환경이 꼬였을 때는 **처음부터 다시 만드는 것이 가장 빠르다.** `.venv`만 지우면 되고, 소스와 `.env`는 그대로 둔다.

**Windows**
```powershell
Remove-Item -Recurse -Force "<PROJECT_ROOT>\.venv"
```
**macOS / Linux**
```bash
rm -rf "<PROJECT_ROOT>/.venv"
```

이후 **STEP 2부터** 다시 진행한다. `.env`는 이미 연결되어 있으므로 STEP 5는 그대로 통과한다.

손상된 휠이 의심되면 **`.venv`를 지우기 전에** pip 캐시를 먼저 비운다 (지운 뒤에는 그 인터프리터가 없다).

```powershell
& "<PROJECT_ROOT>\.venv\Scripts\python.exe" -m pip cache purge   # 먼저
Remove-Item -Recurse -Force "<PROJECT_ROOT>\.venv"                 # 그다음
```
```bash
"<PROJECT_ROOT>/.venv/bin/python" -m pip cache purge   # 먼저
rm -rf "<PROJECT_ROOT>/.venv"                          # 그다음
```


---

# 부록 D. 체크포인트와 사람 개입(HITL) — 추가로 설치할 것이 있나

**없다.** 이것이 이 부록의 결론이다. 자주 나오는 오해라 근거를 적어 둔다.

## D-1. `interrupt` 는 체크포인터를 요구한다

사람이 답할 때까지 상태를 어딘가 들고 있어야 하기 때문이다. 그런데 **경로마다
그 '어딘가'를 대는 주체가 다르다.**

| 실행 경로 | 상태를 누가 들고 있나 | 필요한 패키지 | lock에 있나 |
|---|---|---|---|
| **`langgraph dev` (Studio)** | **Agent Server** 가 스레드/런을 직접 영속화 | `langgraph-api` + `langgraph-runtime-inmem` | **예 (T2)** |
| 순수 파이썬 · pytest | `InMemorySaver()` 를 **직접 넘긴다** | `langgraph-checkpoint` | **예 (T1)** |
| (참고) 서버 없이 파일로 재개 | `SqliteSaver` | `langgraph-checkpoint-sqlite` | **아니오 — 설치하지 않는다** |

```python
# Studio 경로 — 체크포인터를 넘기지 않는다
graph = builder.compile(name="travel")

# 순수 파이썬 경로 — 반드시 넘긴다
from langgraph.checkpoint.memory import InMemorySaver
graph = builder.compile(checkpointer=InMemorySaver())
```

**Studio 에서 `compile(checkpointer=...)` 를 쓰면 Agent Server 가 붙이는 것과 싸운다.**
그래서 이 킷의 `compile_graph()` 는 체크포인터를 **명시적 옵트인 인자**로 두었다.

## D-2. `langgraph-checkpoint-sqlite` 를 설치하지 않는 이유

```text
1  이 실습의 모든 경로(Studio · run_once.py · pytest)가 그것 없이 동작한다
2  requirements-optional.txt 에 있다 = 강사 환경에 없다
   설치하는 순간 교육생 환경 != 강사 환경이 된다 (R4)
3  '서버 없이 하루 뒤 파일에서 재개' 를 해 보고 싶을 때만 푼다
```

풀어야 한다면 **반드시 lock 을 제약 파일로 함께 건다.**

```powershell
& "<PROJECT_ROOT>\.venv\Scripts\python.exe" -m pip install --require-virtualenv `
    langgraph-checkpoint-sqlite `
    -c "<PROJECT_ROOT>\settings\requirements.lock.txt"
```

## D-3. `thread_id` 가 곧 재개 지점이다

```text
같은 thread_id 로 다시 부른다   →  멈춘 자리에서 이어진다
새 thread_id 로 부른다          →  처음부터 돈다
```

Studio 왼쪽의 스레드 목록이 이것이다. 게이트에서 멈춘 스레드는 같은 `thread_id` 로 부르면 그 자리에서 이어진다.

**서버를 껐다 켜도 스레드는 대개 남는다.** 이름은 인메모리 런타임이지만, `langgraph dev` 는
**실행한 폴더의 `.langgraph_api/`** 에 스레드와 체크포인트를 **10초마다** 저장했다가 다시 켤 때
불러온다 (2026-09-27 실측: `Stop-Process -Force` 로 끈 뒤 재기동해도 스레드 상태가 그대로였다).
끄기 직전 10초 안의 변화만 잃을 수 있다. **처음부터 깨끗하게** 시작하려면 서버를 끈 뒤
`.langgraph_api/` 폴더를 지운다 (`.gitignore` 에 이미 있다).

## D-4. `interrupt` 앞은 멱등해야 한다

재개하면 그 노드 함수는 **첫 줄부터 다시 실행된다.** 노드 중간에서 이어지지 않는다.

```python
def human_gate_a(state):
    payload = gate_a_payload(state)   # ① 재개 때마다 다시 실행 → 부작용 금지
    answer = interrupt(payload)       # ② 여기서 멈춘다
    return {...}                      # ③ 여기부터는 정확히 한 번만
```

파일 쓰기·카운터 증가는 **반드시 `interrupt` 뒤**에 둔다.

## D-5. 요약 — 세팅 관점에서 할 일

```text
STEP 4 에서 requirements.lock.txt 를 그대로 설치하면 끝이다.
체크포인트·HITL 을 위해 추가로 설치할 것은 없다.
```
