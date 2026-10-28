#!/usr/bin/env python3
"""LangGraph + LangSmith 실습 환경 검증기.

C01~C12 검사를 전부 수행하고 PASS/FAIL 표를 출력한다. 하나가 실패해도 나머지
검사를 계속 수행하므로, 한 번 실행으로 남은 문제를 모두 볼 수 있다.

  python settings/scripts/verify_env.py                # 표 출력
  python settings/scripts/verify_env.py --json         # 기계 판독용 JSON
  python settings/scripts/verify_env.py --offline      # 네트워크 검사(C08/C09/C12) 생략
  python settings/scripts/verify_env.py --skip-claude  # claude CLI 검사(C11/C12) 생략 (설치·로그인 전 임시로만)

C11 과 C12 는 **다른 것을 본다.** C11 은 "claude 가 있고 로그인돼 있는가",
C12 는 "그 claude 가 **실제로 웹을 조회하는가**". C11 이 통과해도 C12 가 막힐 수
있고, 그때 그래프는 죽지 않고 조용히 replay 로 내려간다 — 가장 찾기 어려운 실패다.

종료 코드 : 0 = 전체 통과, 1 = 실패 항목 있음
마지막 줄 : "ENV_VERIFY: PASS" 또는 "ENV_VERIFY: FAIL"
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

SCRIPT_DIR = Path(__file__).resolve().parent
SETTINGS_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SETTINGS_DIR.parent
LOCK_FILE = SETTINGS_DIR / "requirements.lock.txt"
SMOKE_FILE = SETTINGS_DIR / "smoke" / "smoke_graph.py"

sys.path.insert(0, str(SCRIPT_DIR))

REQUIRED_PY = (3, 12)

# lock 파일에서 실제로 대조할 핵심 패키지. 나머지 전이 의존성은 pip 가 보증한다.
CORE_PACKAGES = [
    "langgraph",
    "langgraph-cli",
    "langgraph-api",
    "langgraph-runtime-inmem",
    "langgraph-checkpoint",
    "langgraph-prebuilt",
    "langgraph-sdk",
    "langchain-core",
    "langchain-protocol",
    "langsmith",
    "pydantic",
    "python-dotenv",
    "pyyaml",
    "pytest",
]

CORE_IMPORTS = [
    ("langgraph.graph", "StateGraph"),
    ("langgraph.graph", "START"),
    ("langgraph.config", "get_stream_writer"),
    ("langgraph.checkpoint.memory", "InMemorySaver"),
    ("langchain_core.runnables", "RunnableConfig"),
    ("langsmith", "Client"),
    ("langsmith", "trace"),
    ("dotenv", "load_dotenv"),
]

TRUTHY = {"1", "true", "yes", "on"}
DEFAULT_ENDPOINT = "https://api.smith.langchain.com"
#: link_env.py 와 같은 목록. 자리표시자 키는 C06 에서 막고, C09 는 네트워크로 보내지 않는다.
PLACEHOLDER_MARKERS = ("여기에", "your", "xxx", "<", "changeme", "paste")


def looks_placeholder(value: str) -> bool:
    low = (value or "").strip().lower()
    return not low or any(m in low for m in PLACEHOLDER_MARKERS)

OK, FAIL, WARN = "OK", "FAIL", "WARN"
_MARK = {OK: "[ OK ]", FAIL: "[FAIL]", WARN: "[WARN]"}


# --------------------------------------------------------------------------- #
# 유틸
# --------------------------------------------------------------------------- #
def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).strip().lower()


def read_lock() -> "dict[str, str]":
    """requirements.lock.txt -> {정규화된 이름: 버전}."""
    pins: dict[str, str] = {}
    if not LOCK_FILE.is_file():
        return pins
    for line in LOCK_FILE.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or "==" not in line:
            continue
        name, _, ver = line.partition("==")
        name = name.split("[", 1)[0]            # langgraph-cli[inmem] -> langgraph-cli
        pins[norm(name)] = ver.strip()
    return pins


def installed_version(name: str) -> "str | None":
    from importlib.metadata import PackageNotFoundError, version
    try:
        return version(name)
    except PackageNotFoundError:
        return None
    except Exception:  # noqa: BLE001
        return None


def load_env_file(path: Path) -> "dict[str, str]":
    """.env 를 dict 로. python-dotenv 없이도 동작하도록 표준 라이브러리만 사용."""
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        key, _, val = line.partition("=")
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        out[key.strip()] = val
    return out


def mask(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return "(비어 있음)"
    for p in ("lsv2_pt_", "lsv2_sk_", "ls__"):
        if v.startswith(p):
            return f"{p}**** ({len(v)}자)"
    return f"{v[:2]}**** ({len(v)}자)"


def venv_bin() -> Path:
    return Path(sys.executable).parent


# --------------------------------------------------------------------------- #
# 개별 검사
# --------------------------------------------------------------------------- #
def c01_python() -> "tuple[str, str]":
    v = sys.version_info
    got = f"{v.major}.{v.minor}.{v.micro}"
    if (v.major, v.minor) == REQUIRED_PY:
        return OK, got
    return FAIL, f"{got} -> 3.12.x 필요 (langgraph.json python_version=3.12)"


def c02_venv() -> "tuple[str, str]":
    expected = (PROJECT_ROOT / ".venv").resolve()
    prefix = Path(sys.prefix).resolve()
    if sys.prefix == sys.base_prefix:
        return FAIL, (f"가상환경 밖의 인터프리터입니다: {sys.executable} "
                      "-> 가상환경을 켜거나 .venv 의 python 으로 다시 실행")
    if prefix != expected:
        return FAIL, f"다른 venv 입니다: {prefix}  (기대: {expected})"
    return OK, str(prefix)


def c03_versions(pins: "dict[str, str]") -> "tuple[str, str, list[str]]":
    if not pins:
        return FAIL, f"lock 파일을 읽지 못했습니다: {LOCK_FILE}", []
    mismatched: list[str] = []
    missing: list[str] = []
    for pkg in CORE_PACKAGES:
        want = pins.get(norm(pkg))
        got = installed_version(pkg)
        if want is None:
            continue
        if got is None:
            missing.append(f"{pkg} (미설치, 기대 {want})")
        elif got != want:
            mismatched.append(f"{pkg} {got} != {want}")
    lines = missing + mismatched
    if lines:
        return FAIL, f"{len(lines)}개 불일치", lines
    return OK, f"핵심 {len(CORE_PACKAGES)}종 lock 과 일치", []


def c04_cli() -> "tuple[str, str]":
    exe = venv_bin() / ("langgraph.exe" if os.name == "nt" else "langgraph")
    if not exe.is_file():
        import shutil as _sh
        found = _sh.which("langgraph")
        if not found:
            return FAIL, "langgraph 실행 파일 없음 -> STEP 4 (requirements.lock.txt 설치) 재실행"
        exe = Path(found)
    try:
        p = subprocess.run([str(exe), "--version"], capture_output=True, text=True, timeout=90)
    except Exception as exc:  # noqa: BLE001
        return FAIL, f"langgraph --version 실행 실패: {exc.__class__.__name__}"
    if p.returncode != 0:
        return FAIL, f"langgraph --version 종료코드 {p.returncode}: {(p.stderr or '').strip()[:160]}"
    ver = (p.stdout or p.stderr).strip().splitlines()[0] if (p.stdout or p.stderr).strip() else "?"
    for mod in ("langgraph_api", "langgraph_runtime_inmem"):
        if importlib.util.find_spec(mod) is None:
            return FAIL, f"{ver} / {mod} 없음 -> `langgraph dev` 불가 (STEP 4 lock 설치 재실행)"
    return OK, f"{ver} / inmem 런타임 탑재"


def c05_imports() -> "tuple[str, str, list[str]]":
    bad: list[str] = []
    for mod, attr in CORE_IMPORTS:
        try:
            m = __import__(mod, fromlist=[attr])
            if not hasattr(m, attr):
                bad.append(f"{mod}.{attr} 없음")
        except Exception as exc:  # noqa: BLE001
            bad.append(f"{mod} 임포트 실패: {exc.__class__.__name__}: {exc}")
    if bad:
        return FAIL, f"{len(bad)}건 실패", bad
    return OK, f"{len(CORE_IMPORTS)}개 심볼 정상", []


def c06_env(env: "dict[str, str]") -> "tuple[str, str, list[str]]":
    path = PROJECT_ROOT / ".env"
    if not path.is_file():
        return FAIL, f"{path} 없음 -> `python settings/scripts/link_env.py` 실행", []
    detail: list[str] = []
    key = env.get("LANGSMITH_API_KEY", "")
    if not key.strip():
        return FAIL, "LANGSMITH_API_KEY 가 비어 있음", []
    if looks_placeholder(key):
        return FAIL, "LANGSMITH_API_KEY 가 자리표시자 상태 -> .env 에 본인 키를 넣고 link_env.py 실행", []
    detail.append(f"LANGSMITH_API_KEY  = {mask(key)}")
    detail.append(f"LANGSMITH_PROJECT  = {env.get('LANGSMITH_PROJECT', '(없음)')}")
    detail.append(f"LANGSMITH_ENDPOINT = {env.get('LANGSMITH_ENDPOINT', DEFAULT_ENDPOINT + ' (기본값)')}")
    return OK, str(path), detail


def c07_tracing(env: "dict[str, str]") -> "tuple[str, str]":
    val = env.get("LANGSMITH_TRACING", os.environ.get("LANGSMITH_TRACING", ""))
    if val.strip().lower() in TRUTHY:
        return OK, f"LANGSMITH_TRACING={val}"
    return FAIL, f"LANGSMITH_TRACING={val or '(없음)'} -> true 여야 노드별 추적이 전송됩니다"


def c08_reach(env: "dict[str, str]") -> "tuple[str, str]":
    base = (env.get("LANGSMITH_ENDPOINT") or DEFAULT_ENDPOINT).rstrip("/")
    try:
        with urllib.request.urlopen(f"{base}/info", timeout=20) as resp:
            return OK, f"{base} -> HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        return (OK, f"{base} -> HTTP {exc.code} (도달함)") if exc.code < 500 else (FAIL, f"{base} -> HTTP {exc.code}")
    except Exception as exc:  # noqa: BLE001
        return FAIL, f"{base} 도달 실패: {exc.__class__.__name__} (프록시/방화벽 확인)"


def c09_auth(env: "dict[str, str]") -> "tuple[str, str]":
    key = env.get("LANGSMITH_API_KEY", "")
    if not key.strip():
        return FAIL, "API 키가 없어 인증을 확인할 수 없습니다"
    if looks_placeholder(key):
        #  자리표시자를 서버에 보내 봐야 401 이 오고 "재발급하라"는 엉뚱한 안내가 된다
        #  (한글 자리표시자는 헤더 인코딩 오류가 난다). 원인은 C06 하나다.
        return FAIL, "키가 아직 자리표시자라 인증을 확인하지 않았습니다 (C06 먼저)"
    try:
        from langsmith import Client
    except Exception as exc:  # noqa: BLE001
        return FAIL, f"langsmith 임포트 실패: {exc.__class__.__name__}"
    try:
        client = Client(api_url=(env.get("LANGSMITH_ENDPOINT") or DEFAULT_ENDPOINT).rstrip("/"), api_key=key)
        projects = list(client.list_projects(limit=1))
        return OK, f"인증 성공 (조회된 프로젝트 {len(projects)}건)"
    except Exception as exc:  # noqa: BLE001
        msg = f"{exc.__class__.__name__}: {exc}"
        if any(t in msg.lower() for t in ("401", "403", "unauthor", "forbidden", "invalid")):
            return FAIL, "API 키 인증 실패(401/403) -> 키를 다시 발급해 .env 에 넣으십시오"
        return FAIL, f"인증 확인 실패: {msg[:180]}"


def c11_claude_cli() -> "tuple[str, str, list[str]]":
    """`claude` CLI 존재 + 구독 인증 확인.

    pip 패키지가 아니므로 lock 과 무관하다. 그래서 C03 이 아니라 별도 게이트다.

    ★ 경로는 **그래프가 쓰는 것과 같은 자리**에서 얻는다 (`travel_graph/claude_cli.py`).
      예전에는 이 함수가 자기만의 후보 목록을 갖고 있었고 `research` 는
      `shutil.which("claude")` 를 그대로 믿었다. 그래서 **C11 은 통과하는데 C12 만
      실패하는** 갈라짐이 실제로 일어났다 — C12 는 그래프가 쓰는 함수를 그대로 부르는
      검사인데, 정작 경로 탐색만은 두 벌로 베껴져 있었던 것이다.

          검증기가 그래프와 다른 것을 보면, 그 검증기는 아무것도 보증하지 못한다.

    ★ **탈락한 후보와 그 이유를 표에 함께 싣는다.** 이 실패는 PATH · PATHEXT · 설치
      방식에 따라 갈려 강사 PC 에서는 재현되지 않는다. 교육생 화면에 남은 이 줄들이
      원격으로 진단할 유일한 단서다.

    `claude auth status` 에서 확인하는 것은 4개 키뿐이다. 원문에는 email·orgId 도
    들어 있으므로 **그 둘은 읽지도 출력하지도 않는다(R5)**.
    """
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from travel_graph import claude_cli
    except Exception as exc:  # noqa: BLE001
        return FAIL, f"travel_graph/claude_cli.py 를 불러오지 못했습니다: {exc.__class__.__name__}: {exc}", []

    try:
        executable = claude_cli.resolve()
    except claude_cli.ClaudeCliNotFound as exc:
        return (FAIL,
                "claude 실행 파일을 찾지 못했습니다 -> Claude Code 설치, 또는 "
                ".env 에 GRAPH_CLAUDE_BIN=<claude 실행 파일 절대 경로>",
                claude_cli.describe(exc.attempts))

    attempts = claude_cli.report()
    version = next((a["version"] for a in attempts if a["ok"]), "?")
    detail: list[str] = [f"실행 파일 : {executable}", f"버전      : {version}"]
    #  탈락한 후보만 덧붙인다. 첫 후보가 바로 채택되면 아무것도 붙지 않는 것이 정상이다.
    detail += claude_cli.describe(attempts, failed_only=True)
    try:
        p = subprocess.run(
            [executable, "auth", "status"], capture_output=True, text=True,
            timeout=60, encoding="utf-8", errors="replace",
        )
        data = json.loads(p.stdout)
    except Exception as exc:  # noqa: BLE001
        return FAIL, f"`claude auth status` 확인 실패: {exc.__class__.__name__}", detail

    for key in ("loggedIn", "authMethod", "apiProvider", "subscriptionType"):
        if key in data:
            detail.append(f"{key:<10}: {data[key]}")
    if not data.get("loggedIn"):
        return FAIL, "로그인되어 있지 않습니다 -> `claude` 를 실행해 /login 하십시오", detail

    if os.environ.get("ANTHROPIC_API_KEY"):
        # 죽이지는 않는다. 그래프의 서브프로세스 호출은 이 값을 제거하고 실행한다.
        # 다만 조용히 API 과금으로 넘어가는 것이 가장 흔한 사고이므로 경고한다.
        detail.append("경고      : ANTHROPIC_API_KEY 가 환경에 있습니다 (구독 인증을 이깁니다)")
        return WARN, f"인증 OK ({data.get('authMethod')}) — 단, API 키 환경변수 존재", detail
    return OK, f"인증 OK (authMethod={data.get('authMethod')})", detail


def c12_live_search() -> "tuple[str, str, list[str]]":
    """`claude -p` 가 **실제로 웹을 조회하는지** 한 번 호출해서 확인한다.

    C11(존재 · 로그인)을 통과해도 여기서 막힐 수 있다. 보는 것이 다르기 때문이다.

        C11   claude 가 설치돼 있고 구독으로 로그인돼 있는가
        C12   그 claude 가 **WebSearch 를 실제로 돌리는가**            <- 여기

    실패한 실제 사례: 호출 옵션에 `--tools` 만 있고 `--allowedTools` 가 없으면,
    도구는 보이는데 승인이 없어 **호출이 거부된다.** 모델은 "권한이 막혀 검색할 수
    없습니다"라는 문장만 내고 JSON 을 만들지 않는다 -> 수집 노드가 `live` 를 포기하고
    `replay` 로 내려간다 -> 화면은 정상으로 보이는데 **매번 같은 인계본 자료가 나온다.**
    그래서 이 검사는 그래프가 쓰는 함수(`research._claude_run`)를 **그대로** 부른다.
    옵션을 여기에 다시 적지 않는 이유다 — 베끼면 둘이 갈라진다.

    ★ 실제로 한 번 갈라졌던 곳이 **경로 탐색**이다. C11 은 후보를 실행해 보고 채택했는데
      `research` 는 `shutil.which()` 를 그대로 믿어서, Windows 에서 실행 안 되는 shim 이
      잡히면 **C11 만 통과하고 C12 가 실패**했다. 지금은 둘 다 `travel_graph/claude_cli.py`
      하나만 쓴다.
    """
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from travel_graph import research
    except Exception as exc:                                      # noqa: BLE001
        return FAIL, f"travel_graph.research 임포트 실패: {exc.__class__.__name__}", []

    prompt = (
        "지금 웹에서 'LangGraph 공식 문서' 를 검색해 주소 한 개를 확인하십시오.\n"
        "반드시 WebSearch 를 실제로 호출하십시오. 기억으로 답하지 마십시오.\n"
        "마지막에 아래 형식의 ```json 블록 하나만 출력하십시오.\n"
        '```json\n{"url": "https://..."}\n```'
    )
    try:
        payload, stats = research._claude_run(prompt, tools=["WebSearch"], max_turns=6)
    except research.ClaudeUnavailable as exc:
        return FAIL, f"live 조회 실패: {exc}", [
            "확인 1: `python -m travel_graph.claude_cli` 로 어떤 실행 파일이 잡히는지 봅니다 "
            "(WinError 193 이 보이면 shim 문제입니다)",
            "확인 2: `claude -p --permission-mode dontAsk --tools WebSearch "
            "--allowedTools WebSearch` 로 직접 불러 봅니다",
            "확인 3: 프로젝트 .claude/settings.json 의 deny 에 WebSearch 가 없는지",
            "우회   : GRAPH_MODE=replay 로 두면 실습은 계속할 수 있습니다 (조사는 인계본 자료)",
        ]

    detail = [f"권한거부 : {', '.join(stats.get('denied') or []) or '없음'}",
              f"실검색   : {stats.get('searches')}회",
              f"응답 키  : {', '.join(list(payload)[:4]) or '(없음)'}"]
    if stats.get("denied"):
        return FAIL, "권한이 막혀 " + "/".join(stats["denied"]) + " 를 쓰지 못했습니다", detail
    if not stats.get("searches"):
        return WARN, "도구는 열렸는데 실제 조회가 0회입니다 (모델이 기억으로 답함)", detail
    return OK, f"실제 웹조회 {stats['searches']}회 확인", detail


def c10_smoke() -> "tuple[str, str]":
    if not SMOKE_FILE.is_file():
        return FAIL, f"{SMOKE_FILE} 없음"
    try:
        spec = importlib.util.spec_from_file_location("smoke_graph_probe", SMOKE_FILE)
        module = importlib.util.module_from_spec(spec)          # type: ignore[arg-type]
        spec.loader.exec_module(module)                          # type: ignore[union-attr]
        graph = getattr(module, "graph", None)
        if graph is None:
            return FAIL, "smoke_graph.py 에 모듈 수준 `graph` 가 없습니다"
        nodes = [n for n in graph.get_graph().nodes if n not in ("__start__", "__end__")]
        return OK, f"컴파일 성공 / 노드 {len(nodes)}개: {', '.join(nodes)}"
    except Exception as exc:  # noqa: BLE001
        return FAIL, f"{exc.__class__.__name__}: {exc}"


# --------------------------------------------------------------------------- #
# 실행
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="LangGraph 실습 환경 검증")
    ap.add_argument("--json", action="store_true", help="JSON 으로 출력")
    ap.add_argument("--offline", action="store_true", help="네트워크 검사(C08/C09/C12) 생략")
    ap.add_argument(
        "--skip-claude", action="store_true",
        help="claude CLI 검사(C11/C12) 생략. claude 설치·로그인 전에 나머지만 볼 때 "
             "(루프 C 정성 판정은 replay 에서도 claude 를 부르므로 실습 전에는 C11 이 통과해야 한다)",
    )
    args = ap.parse_args()

    env = load_env_file(PROJECT_ROOT / ".env")
    for k, v in env.items():                    # C09/스모크가 참조할 수 있게 주입
        os.environ.setdefault(k, v)

    pins = read_lock()
    results: list[dict] = []

    def add(cid: str, title: str, outcome) -> None:
        if len(outcome) == 3:
            status, detail, extra = outcome
        else:
            status, detail = outcome
            extra = []
        results.append({"id": cid, "title": title, "status": status, "detail": detail, "extra": extra})

    add("C01", "Python 3.12.x 인터프리터", c01_python())
    add("C02", "프로젝트 .venv 에서 실행 중", c02_venv())
    add("C03", "핵심 패키지 버전 정합(lock 대조)", c03_versions(pins))
    add("C04", "langgraph CLI + inmem 런타임", c04_cli())
    add("C05", "핵심 심볼 임포트", c05_imports())
    add("C06", ".env 존재 및 필수 키", c06_env(env))
    add("C07", "LangSmith 트레이싱 활성화", c07_tracing(env))
    if args.offline:
        add("C08", "LangSmith 엔드포인트 도달", (WARN, "--offline 로 생략"))
        add("C09", "LangSmith API 키 인증", (WARN, "--offline 로 생략"))
    else:
        add("C08", "LangSmith 엔드포인트 도달", c08_reach(env))
        add("C09", "LangSmith API 키 인증", c09_auth(env))
    add("C10", "스모크 그래프 컴파일", c10_smoke())
    if args.skip_claude:
        add("C11", "claude CLI 존재 및 구독 인증", (WARN, "--skip-claude 로 생략"))
        add("C12", "claude live 웹검색 실측", (WARN, "--skip-claude 로 생략"))
    elif args.offline:
        add("C11", "claude CLI 존재 및 구독 인증", c11_claude_cli())
        add("C12", "claude live 웹검색 실측", (WARN, "--offline 로 생략"))
    else:
        add("C11", "claude CLI 존재 및 구독 인증", c11_claude_cli())
        #  C12 는 30~60초 걸린다. 그래도 뺄 수 없다 — 이것을 건너뛰면 `live` 가 조용히
        #  `replay` 로 내려가는 것을 **실행 당일에야** 알게 된다.
        add("C12", "claude live 웹검색 실측", c12_live_search())

    failed = [r for r in results if r["status"] == FAIL]
    warned = [r for r in results if r["status"] == WARN]
    verdict = "PASS" if not failed else "FAIL"

    if args.json:
        print(json.dumps(
            {
                "verdict": verdict,
                "project_root": str(PROJECT_ROOT),
                "python": sys.version.split()[0],
                "executable": sys.executable,
                "checks": results,
            },
            ensure_ascii=False, indent=2,
        ))
        return 0 if verdict == "PASS" else 1

    print("=" * 78)
    print(" LangGraph + LangSmith 실습 환경 검증")
    print("=" * 78)
    print(f" PROJECT_ROOT : {PROJECT_ROOT}")
    print(f" 인터프리터   : {sys.executable}")
    print("-" * 78)
    for r in results:
        print(f" {r['id']}  {_MARK[r['status']]}  {r['title']}")
        print(f"           {r['detail']}")
        for line in r["extra"]:
            print(f"             - {line}")
    print("-" * 78)
    print(f" 통과 {len(results) - len(failed) - len(warned)} / 실패 {len(failed)} / 경고 {len(warned)}")
    if failed:
        print("\n 실패 항목:")
        for r in failed:
            print(f"   - {r['id']} {r['title']}: {r['detail']}")
        print("\n 조치는 settings/SETUP.md 의 '트러블슈팅' 절을 참고하십시오.")
    print(f"\nENV_VERIFY: {verdict}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
