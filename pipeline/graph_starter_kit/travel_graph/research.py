"""정보를 실제로 모으는 곳. **킷 소유 — 수정 금지.**

노드가 얇아야 그래프 구조가 눈에 보인다. 그래서 "어떻게 모으는가"는 전부 여기에
가두고, `nodes.py` 는 **상태를 읽고 변경분을 돌려주는 일**만 하게 했다.

실행 모드는 두 가지다 (`GRAPH_MODE` 환경변수 · 기본 `live`).

  live     `claude -p` 를 불러 실제로 웹을 조사한다.  ← 기본값
           도시별 노드가 **병렬로** 돌기 때문에 도시 3개가 한 도시 시간에 끝난다.
           이것이 루프판(순차 13분) 대비 그래프판이 빨라지는 유일한 이유다.

  replay   `graph/research_data.json`(루프가 모은 원본)에서 잘라 쓴다.
           10초 안에 끝나고 결과가 항상 같다. 네트워크·인증이 막힌 교육장,
           그리고 강사 시연용 안전망이다.

  자동 폴백  live 로 시작했는데 `claude` 가 없거나 시간을 초과하면 조용히 죽지 않고
           replay 로 내려간 뒤 **그 이유까지** `history` 에 남긴다. 숨기지 않는다.

  live 확인법  `history` 꼬리표를 본다. `실검색 7회` 처럼 **실제 조회 횟수**가 찍힌다.
           `(!) 실검색 0회` 면 모델이 기억으로 답한 것이고, `권한거부 WebSearch` 면
           도구가 막힌 것이다. 셋을 구분하지 못하면 replay 를 live 로 착각한다.

수집은 두 갈래다.

  첫 수집   `collect_one_city` — **`claude -p` 를 두 번** 부른다 (명소 / 일정).
            한 번에 담으면 계약상 7,400자인데 이 CLI 의 실측 잘림 임계가 12,341자다.
            여유가 4,400자뿐이라 모델이 뒤쪽(취향 설명·일정)을 줄여서 맞춘다.
            나누면 3,700자씩이 되어 임계에서 확실히 벗어나고, **일정이 터져도
            명소는 살아남는다.**

  재수집    `repair_one_city` — 지난 결과를 **읽기용으로만** 주고 고친 곳만
            **patch 목록**으로 받는다. 전체 JSON 재타이핑(12,000자)이 500자가 된다.
            안 건드린 값은 물리적으로 바뀌지 않으므로 `_keep_bigger` 같은
            방어 코드가 필요 없다.

**국가 소개도 도시와 같은 규격으로 다시 모은다** (`repair_country_intro`). 자산 제외 2,677자라
잘릴 위험은 사실상 없지만 `수집 부족`은 분량과 상관없이 난다. 재수집 fan-out 에서 국가 갈래는
0 또는 1 이라 `country_intro` 는 한 걸음에 쓰는 노드가 하나뿐이다 — 그래서 reducer 가 필요 없다.

**실패를 빈 껍데기로 감추지 않는다.** 수집 함수는 `(도시, 기록, 실패사유)` 를
돌려주고, 실패사유가 비어 있지 않으면 노드가 그것을 `city_failures` 에 남긴다.
`select_cities` 가 baseline 에 없는 도시를 고른 채 live 가 실패하면, 예전에는
`{"name": …, "spots": []}` 를 정상인 척 돌려주어 게이트가 아무것도 알리지 못했다.

`interrupt` 앞에서 재실행되어도 안전하도록, 이 모듈의 함수는 **부작용이 없다**
(파일을 쓰지 않고 값만 돌려준다). 파일 쓰기는 `nodes.py` 한 곳에서만 한다.
"""
from __future__ import annotations

import copy
import functools
import json
import os
import re
import subprocess
import threading
import time
import uuid

from travel_graph import claude_cli, contract, tracing

# --------------------------------------------------------------------------- #
# 설정
# --------------------------------------------------------------------------- #

DEFAULT_MODE = "live"

#: 어떤 모델로 부를 것인가. `.env` 의 `GRAPH_CLAUDE_MODEL` 이 그대로 `--model` 로 간다.
#: 별칭(`sonnet` / `opus` / `haiku`) 또는 정식 이름(`claude-sonnet-5`) 둘 다 받는다.
#: 실습 기본값은 `sonnet` — 조사·판정 품질과 비용이 균형을 이루는 지점이다.
#: **코드 기본값과 `.env` 값을 일부러 같게 맞춰 둔다.** `langgraph dev` 는 `.env` 를
#: 읽어 주지만 `scripts/run_once.py` 는 읽지 않는다. 기본값이 다르면 같은 킷이
#: 실행 경로에 따라 다른 모델로 도는 사고가 난다.
CLAUDE_MODEL = os.environ.get("GRAPH_CLAUDE_MODEL", "sonnet") or "sonnet"

#: 얼마나 힘을 줘서 생각하게 할 것인가 (`--effort`). 값은 다섯 개뿐이다.
#: `low / medium / high / xhigh / max`. 실습 기본값은 `medium`.
#:
#: ★ 이 킷은 도시 3곳을 **병렬로** 부르고 정성 판정을 3회 더 돈다. `high` 이상은
#:   한 호출이 길어져 `GRAPH_CLAUDE_TIMEOUT`(600초)을 넘기고 replay 로 내려가기
#:   쉽다. `low` 는 재수집이 부족한 칸을 잘 못 메운다. 그래서 `medium` 이다.
#:
#: ★ 값 검증을 여기서 하는 이유. CLI 는 모르는 값을 주면 **경고만 하고 조용히
#:   기본 에포트로 돌아간다.** 그러면 교육생은 `medum` 오타 하나로 "설정했는데
#:   왜 안 걸리지"를 겪는다. 여기서 잡아 기록에 남기고 `medium` 으로 되돌린다.
#: 빈 값(`GRAPH_CLAUDE_EFFORT=`)이나 `off` 를 주면 옵션 자체를 붙이지 않는다.
CLAUDE_EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")
DEFAULT_EFFORT = "medium"


def _effort() -> str:
    """`--effort` 에 넘길 값. 붙이지 않을 때는 빈 문자열."""
    raw = os.environ.get("GRAPH_CLAUDE_EFFORT")
    if raw is None:
        return DEFAULT_EFFORT
    value = raw.strip().lower()
    if value in ("", "off", "none", "default"):
        return ""                                   # CLI 기본 에포트에 맡긴다
    if value in CLAUDE_EFFORT_LEVELS:
        return value
    print(f"[research] GRAPH_CLAUDE_EFFORT={raw!r} 는 모르는 값입니다 "
          f"({'/'.join(CLAUDE_EFFORT_LEVELS)} 중 하나) -> {DEFAULT_EFFORT} 로 진행합니다")
    return DEFAULT_EFFORT


CLAUDE_EFFORT = _effort()
CLAUDE_TIMEOUT = int(os.environ.get("GRAPH_CLAUDE_TIMEOUT", "600"))

#: 권한 모드. **`dontAsk` 는 "허용한다"가 아니라 "사람에게 묻지 않는다"는 뜻이다.**
#: 승인이 필요한 도구는 물어보는 대신 **거부된다.** 실제 허용은 `--allowedTools` 가
#: 한다. 두 옵션은 하는 일이 다르므로 반드시 함께 준다 (`_claude_run` 의 주석 참고).
CLAUDE_PERMISSION_MODE = os.environ.get("GRAPH_CLAUDE_PERMISSION_MODE", "dontAsk")

#: 서브프로세스에서 절대 쓰지 않는 도구. `--tools` 로 이미 좁히지만, 그것이 넓어졌을
#: 때를 대비한 두 번째 빗장이다. 수집도 정성 판정도 **파일을 직접 고치지 않는다.**
DENY_TOOLS = "Bash,Edit,Write,Task,NotebookEdit"

#: 교육생마다 결과가 달라지는 것을 막는다. `claude -p` 는 작업 디렉터리(=킷 루트)와
#: 홈의 설정을 자동으로 끌어온다 — 킷의 `CLAUDE.md`, 개인 `~/.claude/CLAUDE.md`,
#: 훅, 플러그인, 스킬까지. 그러면 **같은 킷을 받아도 사람마다 수집이 달라진다.**
#: `--safe-mode` 는 그 커스터마이징만 끄고 인증·모델·권한·기본 도구는 그대로 둔다.
#: 실측: 호출당 주입 컨텍스트 12,834 -> 1,584 토큰, 검색 동작 동일.
#: 끄고 싶으면 `GRAPH_CLAUDE_SAFE_MODE=0`.
CLAUDE_SAFE_MODE = os.environ.get("GRAPH_CLAUDE_SAFE_MODE", "1") not in ("0", "false", "False")

#: 구독 인증을 이기는 값들. 서브프로세스 환경에서만 제거한다 (os.environ 은 안 건드림).
SCRUB_ENV = (
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
    "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX",
)

#: replay 모드에서 **1회차에는 계약을 일부러 덜 채운다.**
#: 루프 A가 최소 한 바퀴는 돌아야 라우터가 일하는 것을 눈으로 볼 수 있기 때문이다.
#: 실습용 장치이며 `GRAPH_REPLAY_FULL=1` 로 끌 수 있다.
REPLAY_HOLDS_FIRST_PASS = os.environ.get("GRAPH_REPLAY_FULL", "") not in ("1", "true", "True")

_JSON_FENCE = re.compile(r"```json\s*(.*?)```", re.DOTALL)


def mode() -> str:
    value = (os.environ.get("GRAPH_MODE") or DEFAULT_MODE).strip().lower()
    return value if value in ("live", "replay") else DEFAULT_MODE


# --------------------------------------------------------------------------- #
# claude -p 얇은 러너
# --------------------------------------------------------------------------- #


class ClaudeUnavailable(RuntimeError):
    """claude 를 부르지 못했다. 그래프를 죽이지 않고 replay 로 내려간다."""


@functools.lru_cache(maxsize=8)
def _supports(flag: str) -> bool:
    """이 CLI 가 그 옵션을 아는가. **모르는 옵션을 주면 exit 1 로 죽는다.**

    `claude` 는 npm 설치물이라 교육생마다 버전이 다를 수 있다. 옵션 하나 때문에
    수집이 통째로 replay 로 내려가는 일을 막으려고, 붙이기 전에 한 번만 확인한다.

    ★ 실행 파일은 `claude_cli.resolve()` 로만 얻는다. `shutil.which("claude")` 를
      직접 부르면 Windows 에서 **찾기는 했는데 실행은 안 되는** shim 이 잡히는 일이
      있다 (`claude_cli.py` 머리말 참고). 킷에서 claude 를 찾는 자리는 그 함수
      하나뿐이어야 한다 — 두 벌을 두면 반드시 갈라진다.
    """
    try:
        exe = claude_cli.resolve()
    except claude_cli.ClaudeCliNotFound:
        return False
    try:
        proc = subprocess.run([exe, "--help"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=60)
    except Exception:                                           # noqa: BLE001
        return False
    return flag in (proc.stdout or "")


def _failure_text(envelope: dict, stderr: str) -> str:
    """왜 죽었는지 **말이 되는 한 줄**을 만든다.

    `claude -p` 는 실패해도 stderr 가 비어 있는 경우가 많다 (사용량 한도, 부모와
    함께 종료된 경우 등). 그때 사유는 스트림 마지막의 `result` 이벤트에 들어 있다.
    비워 두면 `코드 1 로 종료했습니다: ` 라는 아무 정보 없는 줄이 기록에 남는다 —
    실측에서 실제로 그렇게 남았고, 원인을 찾는 데 시간을 썼다.
    """
    for key in ("subtype", "error", "message", "result"):
        value = envelope.get(key)
        if isinstance(value, str) and value.strip() and value.strip() != "success":
            return value.strip()[:200]
    if stderr.strip():
        return stderr.strip()[:200]
    return "(stdout·stderr 가 모두 비어 있습니다 — 밖에서 종료되었을 수 있습니다)"


def _stream(cmd: list, prompt: str, env: dict, trace) -> tuple[dict, str, int, str]:
    """`claude -p` 를 **한 줄씩 읽으며** 트레이스를 그린다.

    돌려주는 것: (마지막 `result` 이벤트, 모델이 낸 텍스트, 종료 코드, stderr)

    ★ 왜 `subprocess.run` 이 아니라 직접 스트림을 읽는가.
      `--output-format json` 은 **끝난 뒤에 한 덩어리**로 준다. 그러면 무엇을
      검색했는지, 지금 몇 번째 턴인지가 끝나기 전에는 보이지 않는다. Studio 를
      켜 놓고 진행을 보는 것이 이 킷의 목적이므로, 턴이 도착하는 대로 자식 run 을
      열고 닫는다. `--output-format stream-json` 은 `--verbose` 와 함께 써야 한다.

    ★ 왜 stdin 을 따로 쓰는 스레드가 필요한가.
      프롬프트가 파이프 버퍼보다 크면, 우리가 stdout 을 읽기 시작하기 전에 write
      가 막힌다. 그러면 서로를 기다리는 교착이 된다. 도시 프롬프트는 재수집 때
      지난 회차 JSON 을 통째로 싣기 때문에 실제로 그 크기가 나온다.

    ★ 타임아웃은 감시 타이머가 프로세스를 죽여서 만든다. 그러면 아래 for 문이
      EOF 로 끝나고, 죽인 사실은 `timed_out` 으로 안다.
    """
    try:
        proc = subprocess.Popen(
            cmd, cwd=str(contract.ROOT), shell=False,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", bufsize=1, env=env,
        )
    except (FileNotFoundError, OSError) as exc:
        raise ClaudeUnavailable(f"claude 실행 실패: {exc}")

    def feed():
        try:
            proc.stdin.write(prompt)
        except Exception:                                       # noqa: BLE001
            pass
        finally:
            try:
                proc.stdin.close()
            except Exception:                                   # noqa: BLE001
                pass

    errors: list[str] = []

    def drain():
        try:
            errors.append(proc.stderr.read() or "")
        except Exception:                                       # noqa: BLE001
            pass

    timed_out: list[bool] = []

    def kill():
        timed_out.append(True)
        if os.name == "nt":
            #  ★ Windows 에서 `claude` 가 `.cmd` 셈이면 `proc` 은 cmd.exe 이고 진짜 claude(node)는
            #    그 자식이다. `proc.kill()` 은 cmd.exe 만 죽여 node 가 stdout 파이프를 쥔 채 남고,
            #    아래 for 문이 EOF 를 못 받아 **타임아웃이 시간을 끊지 못한다.** 트리째 끊는다.
            try:
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            except Exception:                                   # noqa: BLE001
                pass
        try:
            proc.kill()
        except Exception:                                       # noqa: BLE001
            pass

    threading.Thread(target=feed, daemon=True).start()
    threading.Thread(target=drain, daemon=True).start()
    timer = threading.Timer(CLAUDE_TIMEOUT, kill)
    timer.start()

    envelope: dict = {}
    texts: list[str] = []
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            kind = event.get("type")
            if kind == "assistant":
                for block in _as_list(_as_dict(event.get("message")).get("content")):
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text" and block.get("text"):
                        texts.append(str(block["text"]))
                    elif block.get("type") == "tool_use":
                        trace.tool_start(str(block.get("id")), str(block.get("name")),
                                         block.get("input"))
            elif kind == "user":
                for block in _as_list(_as_dict(event.get("message")).get("content")):
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        trace.tool_end(str(block.get("tool_use_id")), block.get("content"),
                                       bool(block.get("is_error")))
            elif kind == "result":
                envelope = event
    finally:
        timer.cancel()
        try:
            proc.stdout.close()
        except Exception:                                       # noqa: BLE001
            pass
        proc.wait()

    if timed_out:
        raise ClaudeUnavailable(f"claude -p 가 {CLAUDE_TIMEOUT}초를 초과했습니다")
    return envelope, "\n".join(texts).strip(), proc.returncode, "".join(errors).strip()


def _search_count(envelope: dict) -> int:
    """이번 호출에서 **실제로 나간 웹 조회 횟수.**

    ★ 여기가 두 번째 함정이다. `usage.server_tool_use.web_search_requests` 는 이
      CLI 에서 **언제나 0** 이다. Claude Code 의 WebSearch 는 API 서버 도구가 아니라
      CLI 가 보조 모델로 직접 돌리는 **클라이언트 도구**여서 횟수가 다른 칸에 적힌다.

          usage.server_tool_use.web_search_requests            0   <- 여기만 보면 오독한다
          modelUsage["claude-haiku-4-5-..."].webSearchRequests  1   <- 진짜 횟수

      0 을 보고 "검색이 안 됐다"고 결론 내리지 말 것. 세는 자리가 다를 뿐이다.
    """
    by_model = 0
    for stat in _as_dict(envelope.get("modelUsage")).values():
        if isinstance(stat, dict):
            by_model += int(stat.get("webSearchRequests") or 0)
            by_model += int(stat.get("webFetchRequests") or 0)
    server = _as_dict(_as_dict(envelope.get("usage")).get("server_tool_use"))
    by_server = (int(server.get("web_search_requests") or 0)
                 + int(server.get("web_fetch_requests") or 0))
    return max(by_model, by_server)      # 둘 다 채우는 CLI 에서 이중으로 세지 않는다


def _payload_from(result) -> "dict | None":
    """응답 본문에서 마지막 ```json 블록을 dict 로 꺼낸다. 없으면 None."""
    if isinstance(result, dict):
        return result
    if not isinstance(result, str):
        return None
    try:
        parsed = json.loads(result)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    for block in reversed(_JSON_FENCE.findall(result)):
        try:
            parsed = json.loads(block)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    return None


def _claude_run(prompt: str, *, tools: list[str], max_turns: int,
                label: str = "호출") -> tuple[dict, dict]:
    """`claude -p` 를 부르고 **(JSON 본문, 호출 통계)** 를 돌려준다.

    검증된 불변식만 지킨다 — 프롬프트는 **stdin** 으로(argv 길이 제한 회피),
    `shell=False`, UTF-8 강제, 타임아웃, 그리고 인증 우선순위 상위 키 제거.

    ★ 도구를 쓰게 하려면 **옵션 두 개가 다 필요하다.** 하나만 주면 조용히 막힌다.

          --tools         그 도구를 **띄운다**              (가용성)
          --allowedTools  그 도구를 **승인 없이 쓰게 한다**  (권한)

      `--tools` 만 주고 `--permission-mode dontAsk` 로 돌리면 도구는 보이는데 승인이
      없고 물어볼 사람도 없으므로 **호출이 거부된다.** 그러면 모델은 "권한이 막혀
      검색할 수 없습니다"라는 문장만 내고 ```json 블록을 만들지 않는다 -> 이 함수가
      `ClaudeUnavailable` 을 던지고 -> 그래프는 죽지 않고 replay 로 내려간다.
      **live 인데 매번 replay 로 떨어지던 원인이 정확히 이것이었다.**

      거부된 사실은 `permission_denials` 에 남는다. 아래에서 그것을 읽어
      "JSON 을 못 찾았습니다"가 아니라 **"무엇이 왜 막혔는지"** 를 그대로 알린다.

    ★ `label` 은 LangSmith 트레이스에 뜨는 이름이다 (`claude -p · collect_city[하노이]`).
      노드 이름만으로는 도시 3개가 구분되지 않으므로 부르는 쪽이 지어 준다.
    """
    #  ★ 실행 파일은 여기서 고르지 않는다. `claude_cli.resolve()` 가 후보를 하나씩
    #    **실제로 실행해서** 살아 있는 것만 돌려준다. 예전에는 `shutil.which("claude")`
    #    를 그대로 믿었고, Windows 에서 확장자 없는 POSIX shim 이 잡히면
    #    `[WinError 193]` 으로 죽어 **매번 조용히 replay 로 내려갔다.**
    try:
        exe = claude_cli.resolve()
    except claude_cli.ClaudeCliNotFound as exc:
        #  왜 못 찾았는지까지 그대로 싣는다. 이 문장이 `history` 꼬리표와 트레이스에
        #  남아 교육생 화면의 유일한 단서가 된다 — 강사 PC 에서는 재현되지 않는다.
        raise ClaudeUnavailable(str(exc)) from exc

    granted = ",".join(tools)
    cmd = [
        exe, "-p",
        "--output-format", "stream-json",   # 턴을 하나씩 흘려 준다 (실시간 추적)
        "--verbose",                        # stream-json 에는 이것이 필요하다
        "--model", CLAUDE_MODEL,
        "--permission-mode", CLAUDE_PERMISSION_MODE,
        "--tools", granted,                 # 가용성 — 어떤 도구를 띄울지
        "--allowedTools", granted,          # 권한 — 이 줄이 없으면 전부 거부된다 ★
        "--disallowed-tools", DENY_TOOLS,
        "--session-id", str(uuid.uuid4()),
        "--max-turns", str(max_turns),
    ]
    safe = CLAUDE_SAFE_MODE and _supports("--safe-mode")
    if safe:
        cmd.append("--safe-mode")               # 교육생 환경 차이를 걷어낸다

    #  ★ `--effort` 는 비교적 최근에 생긴 옵션이다. `claude` 는 npm 설치물이라
    #    교육생마다 버전이 다르고, **모르는 옵션을 주면 CLI 가 exit 1 로 죽는다.**
    #    그러면 수집이 통째로 replay 로 내려간다. `--safe-mode` 와 같은 이유로
    #    `--help` 에 있는지 한 번 확인하고(결과는 캐시된다) 붙인다.
    effort = CLAUDE_EFFORT if (CLAUDE_EFFORT and _supports("--effort")) else ""
    if effort:
        cmd += ["--effort", effort]
    env = {k: v for k, v in os.environ.items() if k not in SCRUB_ENV}

    started = time.time()
    trace = tracing.ClaudeTrace(label, prompt, {
        #  앞의 세 개는 LangSmith 가 모델 정보를 그리는 데 쓰는 약속된 이름이다.
        "ls_provider": "anthropic",
        "ls_model_name": CLAUDE_MODEL,
        "ls_model_type": "chat",
        #  아래는 사람이 읽는 칸이다. 실습에서 궁금해지는 것만 골라 담았다.
        "실행 모드": mode(),
        #  ★ 모델·에포트를 트레이스에 박아 둔다. `.env` 를 고쳤는데 반영이 안 될 때
        #    (예: `langgraph dev` 를 껐다 켜지 않았을 때) 여기만 보면 바로 안다.
        #    `(CLI 미지원)` 이면 옵션이 없는 구버전이라 붙이지 못한 것이다.
        "모델": CLAUDE_MODEL,
        "에포트": effort or ("(CLI 미지원)" if CLAUDE_EFFORT else "(지정 안 함)"),
        #  ★ **어느 실행 파일로 불렀는지.** Windows 는 같은 이름의 shim 이 여러 개라
        #    "설치는 했는데 왜 이러지"의 답이 여기 있는 경우가 많다. 진단할 때
        #    교육생에게 물어볼 것이 하나 줄어든다.
        "CLI 경로": exe,
        "허용 도구": granted or "(없음)",
        "금지 도구": DENY_TOOLS,
        "권한 모드": CLAUDE_PERMISSION_MODE,
        "safe_mode": bool(safe),
        "max_turns": max_turns,
        "타임아웃 초": CLAUDE_TIMEOUT,
    })

    try:
        envelope, text, code, stderr = _stream(cmd, prompt, env, trace)
    except ClaudeUnavailable as exc:
        trace.fail(str(exc))
        raise

    usage = _as_dict(envelope.get("usage"))
    denied = sorted({d.get("tool_name") for d in _as_list(envelope.get("permission_denials"))
                     if isinstance(d, dict) and d.get("tool_name")})
    stats = {
        "searches": _search_count(envelope),
        "denied": denied,
        "turns": int(envelope.get("num_turns") or 0),
    }
    meta = {
        "사용 턴": stats["turns"],
        "실검색": stats["searches"],
        "권한거부": "/".join(denied) or "없음",
        "소요 초": round(time.time() - started, 1),
        "비용 usd": envelope.get("total_cost_usd"),
        "입력 토큰": int(usage.get("input_tokens") or 0),
        "출력 토큰": int(usage.get("output_tokens") or 0),
        "캐시 읽기 토큰": int(usage.get("cache_read_input_tokens") or 0),
        "캐시 생성 토큰": int(usage.get("cache_creation_input_tokens") or 0),
        "종료 사유": envelope.get("subtype") or "(없음)",
        #  ★ `stop_reason` 이 `max_tokens` 면 **모델이 말을 다 못 끝낸 것**이고
        #    `end_turn` 이면 스스로 끝낸 것이다. 둘을 구분하지 못하면 "JSON 을 못
        #    찾았습니다"가 형식 문제인지 길이 문제인지 알 길이 없다.
        "중단 이유": envelope.get("stop_reason") or "(없음)",
        "세션": envelope.get("session_id") or "",
    }

    if code != 0:
        reason = _failure_text(envelope, stderr)
        if "error_max_turns" in reason:
            #  이 CLI 는 턴 초과를 **exit 1** 로 알린다 (봉투의 subtype 으로 오지 않는다).
            #  사람이 읽고 바로 조치할 수 있게 숫자를 넣어 다시 쓴다.
            reason = (f"{max_turns}턴 안에 끝내지 못했습니다 (max_turns 초과) — "
                      "읽을 파일이 크거나 프롬프트가 무겁습니다")
        message = f"claude -p 가 코드 {code} 로 종료했습니다: {reason}"
        trace.fail(message, meta)
        raise ClaudeUnavailable(message)

    body = envelope.get("result")
    payload = _payload_from(body if isinstance(body, (str, dict)) else text)
    if payload is None and text:
        payload = _payload_from(text)

    shown = body if isinstance(body, str) and body.strip() else text
    trace.parsed(shown, payload,
                 error="" if payload is not None else "```json 블록을 찾지 못했습니다")

    if payload is not None:
        trace.finish(text=shown, payload=payload, metadata=meta)
        return payload, stats

    # 여기부터는 실패다. **무엇이 막혔는지를 이름으로 말한다.**
    if denied:
        message = ("권한이 막혀 " + "/".join(denied) + " 를 쓰지 못했습니다 — "
                   "`--allowedTools` 와 `.claude/settings.json` 의 deny 를 확인하십시오")
    elif envelope.get("subtype") == "error_max_turns":
        message = f"{max_turns}턴 안에 끝내지 못했습니다 (max_turns 초과)"
    elif shown.count("```json") and shown.count("```") < shown.count("```json") * 2:
        #  여는 fence 는 있는데 닫는 fence 가 모자라다 = **말하다 잘렸다.**
        #  이 계약이 요구하는 JSON 은 한 번에 담기는 한계에 가깝다. 서술을 덧붙이면
        #  블록이 닫히기 전에 끝난다. 실측: 성공 11,805자 / 잘림 12,341자.
        message = (f"응답이 중간에 잘렸습니다 — ```json 블록이 닫히지 않았습니다 "
                   f"(중단 이유 {meta['중단 이유']} · 출력 {len(shown):,}자). "
                   "한 번에 담기 어려운 분량입니다")
    else:
        message = "claude 응답에서 JSON 블록을 찾지 못했습니다"
    meta["응답 길이"] = len(shown)
    trace.fail(message, meta)
    raise ClaudeUnavailable(message)


def _claude_json(prompt: str, *, tools: list[str], max_turns: int,
                 label: str = "호출") -> dict:
    """통계가 필요 없는 호출자용 얇은 껍데기. `quality.py` 가 이것을 쓴다."""
    return _claude_run(prompt, tools=tools, max_turns=max_turns, label=label)[0]


# --------------------------------------------------------------------------- #
# 공통 도우미
# --------------------------------------------------------------------------- #


def _as_list(value):
    return value if isinstance(value, list) else []


def _as_dict(value):
    return value if isinstance(value, dict) else {}


def _stat_text(stats: dict, *, expect_search: bool = True) -> str:
    """`history` 에 붙는 꼬리표. **Studio 화면에서 live 인지 눈으로 확인된다.**

    `(!) 실검색 0회` 가 보이면 모델이 기억으로 답했다는 뜻이다. 그 회차의 근거 URL 은
    믿지 말고 게이트에서 `more` 로 한 바퀴 더 돌린다.

    다만 **조회가 필요 없는 회차도 있다.** 일정 블록의 `why` 를 길게 고쳐 쓰는 재수집이
    그렇다. 그때 0회는 정상이므로 경고를 달지 않는다 (`expect_search=False`).
    늘 경고하면 진짜 경고가 묻힌다.
    """
    count = int(stats.get("searches") or 0)
    if count:
        tail = f" · 실검색 {count}회"
    elif expect_search:
        tail = " · (!) 실검색 0회 — 기억으로 답했을 수 있음"
    else:
        tail = " · 실검색 0회(글만 고치는 회차)"
    if stats.get("denied"):
        tail += " · 권한거부 " + "/".join(stats["denied"])
    return tail


#: 못 채운 칸 이름에 이것이 들어 있으면 **웹을 다시 봐야 채워진다.**
#: 없으면 글만 고치면 되므로 검색이 0회여도 정상이다.
_LOOKUP_WORDS = ("이미지", "근거", "출처")


def _previous_city(state, city_name: str) -> dict:
    """상태에 남아 있는 지난 회차의 그 도시. 없으면 빈 dict."""
    for city in _as_list(state.get("cities")):
        if isinstance(city, dict) and (city.get("name") or "").strip() == city_name:
            return city
    return {}


def _previous_country(state) -> dict:
    """상태에 남아 있는 지난 회차의 국가 소개. 없으면 빈 dict."""
    return _as_dict(state.get("country_intro"))


def _repair_lines(short_slots, keep: str) -> list[str]:
    """검사기가 센 못 채운 칸 중 **이번 대상에 해당하는 것만** 고른다.

    칸 이름은 검사기가 만든 문자열 그대로다 (`밴쿠버/그랜빌 아일랜드 이미지: …`,
    `기능3 밴프 3일차: …`). 도시 이름이나 `기능1` 이 그 안에 들어 있으므로
    부분 문자열로 고를 수 있다. **검사기의 문장을 그대로 모델에게 넘기는 것**이
    핵심이다 — 우리가 요약하면 무엇을 고쳐야 하는지가 흐려진다.
    """
    return [str(s) for s in _as_list(short_slots) if keep in str(s)]


def _human_note(state) -> str:
    """게이트 A 에서 사람이 적은 지시문. `more` 를 골랐을 때만 나온다.

    * 이것이 게이트를 **진짜 선택지**로 만든다. 사람이 `more` 를 고르는데 재수집이
      지난 바퀴와 글자 하나 다르지 않으면, 같은 결과가 나오는 것이 당연하다.
      실측에서 그랬다 - `more` 를 눌러도 부족한 칸이 줄지 않았다. 방향을 바꿀
      수단이 없었기 때문이다.

    * **라우팅에는 절대 쓰지 않는다.** 경로는 `gate_a_answer` 의 세 값
      (`more` / `proceed` / `stop`) 만으로 고른다. 이 문장은 경로가 아니라
      **프롬프트에 실리는 내용**이다. 둘을 섞으면 제어 흐름이 문장 해석에
      좌우되고, 그것이 `CLAUDE.md` 8절 3번이 금지하는 바로 그것이다.

    * `more` 일 때만 읽는 이유. `gate_note` 는 상태에 계속 남는다. 조건 없이
      읽으면 `proceed` 를 고른 뒤에도 옛 지시가 따라다닌다.
    """
    if (state.get("gate_a_answer") or "").strip() != "more":
        return ""
    note = str(state.get("gate_note") or "").strip()
    if not note or note.startswith("("):        # "(자동 통과 - STEP 5 전)" 같은 자리표시자
        return ""
    return ("[사람의 지시]  <- 게이트에서 사람이 직접 적었습니다. "
            "**검사기 지적보다 우선합니다.**\n"
            "  " + note[:800] + "\n\n")


def _repair_howto() -> str:
    """못 채운 칸의 문장을 **행동으로 번역**해 준다. 매번 같은 세 종류가 나온다."""
    form = _as_dict(contract.counts().get("asset_rule")).get("recommended_form")
    return (
        "[고치는 방법]\n"
        "- 지적되지 않은 값은 **건드리지 마십시오.** patch 에 넣지 않으면 그대로 남습니다.\n"
        "  문장을 다듬으면 멀쩡하던 칸이 중복 검사에 걸립니다.\n"
        "- `…왜 넣었는지가 40자 미만` = 그 날의 **모든 블록**의 `why` 를 하한 이상으로 "
        "채우라는 뜻입니다. 어느 블록인지는 알려 주지 않으므로 지적된 날은 "
        "**그 날 블록을 하나도 빼지 말고 전부** patch 하십시오.\n"
        "- `근거: 목표 2 / 실제 1` = 그 관광지에 근거를 **더** 찾아 넣으라는 뜻입니다. "
        "WebSearch 로 실제 조회하고, 이미 있는 것과 **다른 출처**여야 합니다. "
        "추가는 `spots[i].items[<지금 개수>]` 처럼 **바로 뒤 한 칸**에만 넣을 수 있습니다.\n"
        "- `이미지 주소가 열리지 않았습니다 — HTTP 404 …` = 주소 **형식**은 맞는데 그 "
        "**파일명이 Commons 에 없습니다.** 지어낸 이름입니다. WebSearch 로 "
        "`commons.wikimedia.org` 에서 실제 파일명을 확인한 뒤 바꾸십시오. 확인하지 "
        "못했으면 그 칸은 **patch 하지 마십시오** — 지어낸 주소는 또 지적됩니다.\n"
        "- `이미지 주소가 열리지 않았습니다 — 네트워크로 닿지 못했습니다` = **당신 잘못이 "
        "아닙니다.** 그 칸은 patch 하지 마십시오. 사람이 환경을 봐야 하는 문제입니다.\n"
        f"  형식: {form}\n"
        "  `verified` 는 적지 마십시오 — 이 킷의 코드가 직접 열어 보고 채웁니다.\n"
    )


def _style_text(state) -> str:
    style = _as_dict(state.get("style"))
    lines = []
    for key, label in (("preferred", "좋아하는 것"),
                       ("not_preferred", "싫어하는 것"),
                       ("detailed", "자세한 취향")):
        values = [str(v) for v in _as_list(style.get(key))]
        if values:
            lines.append(f"- {label}: " + " / ".join(values))
    return "\n".join(lines) or "- (취향이 비어 있습니다. 무난한 기준으로 고르십시오.)"


def _rules_spots() -> str:
    """**명소 호출**에 실리는 계약. 일정 규칙은 넣지 않는다 — 쓰지도 않을 규칙을 주면
    모델이 그쪽에도 분량을 배분해 정작 필요한 칸이 얇아진다."""
    counts = contract.counts()
    cities = _as_dict(counts.get("cities"))
    chars = _as_dict(counts.get("min_chars"))
    dedup = _as_dict(counts.get("dedup"))
    ratio = int(float(dedup.get("min_unique_line_ratio") or 0.9) * 100)
    return "\n".join([
        f"- 관광지 {cities.get('spots_per_city')}곳",
        f"- 도시 선정 이유 {chars.get('why_selected')}자 이상",
        f"- 관광지마다 근거 {_as_dict(cities.get('evidence_per_spot')).get('target')}건 "
        f"(서로 **다른 출처** 2곳 이상, 각 {chars.get('evidence_item')}자 이상)",
        f"- 관광지마다 상세 소개 {chars.get('spot_detail')}자 이상, 이미지 1장",
        f"- 취향 설명 {cities.get('preference_note_min_lines')}줄 이상, "
        f"**줄마다 {chars.get('preference_note_line')}자 이상이고 줄끼리 서로 달라야 한다** "
        f"(고유 줄 {ratio}% 이상. 번호만 바꿔 복제하면 검사에 걸린다)",
    ])


def _rules_country() -> str:
    """**국가 소개 호출**에 실리는 계약. 칸 이름과 하한을 계약에서 그대로 읽는다."""
    rules = _as_dict(contract.counts().get("country_intro"))
    chars = _as_dict(contract.counts().get("min_chars"))
    item = chars.get("evidence_item")
    lines = []
    for name, spec in rules.items():
        kind = (spec or {}).get("kind")
        if kind == "다건":
            lines.append(f"- {name} {spec.get('target')}건 — 서로 **다른 출처** "
                         f"{spec.get('distinct_sources', 2)}곳 이상, 각 {item}자 이상")
        elif kind == "단건":
            lines.append(f"- {name} 1건 — {item}자 이상")
        elif kind == "조건부":
            lines.append(f"- {name} — 해당 사항이 없으면 `checked: true` 로 "
                         f"**확인했다는 사실만** 적는다 (items 는 비워도 통과)")
        elif kind == "자산":
            lines.append(f"- {name} — 실제로 열리는 주소 1장")
    return "\n".join(lines)


def _rules_itinerary() -> str:
    """**일정 호출**에 실리는 계약."""
    itinerary = _as_dict(contract.counts().get("itinerary"))
    chars = _as_dict(contract.counts().get("min_chars"))
    return "\n".join([
        f"- 일정 근거 {_as_dict(itinerary.get('evidence_per_city')).get('target')}건 "
        f"(서로 다른 출처 2곳 이상, 각 {chars.get('evidence_item')}자 이상)",
        f"- 일정은 **이 도시 하나만으로** {itinerary.get('days_per_city')}일. 도시 합계가 아니다",
        f"- 하루는 {itinerary.get('blocks_per_day_min')}블록 이상, 시각은 "
        f"{itinerary.get('time_format')} 형식, 종류는 "
        f"{'/'.join(_as_list(itinerary.get('block_kinds')))} 중 하나",
        "- 한 날 안에서 시간은 앞뒤가 겹치지 않고 이어져야 한다",
        f"- 하루에 '명소' 블록이 {itinerary.get('spot_blocks_per_day_min')}개 이상이고, "
        f"그 블록의 `spot` 은 **아래 목록에 있는 이름 그대로**여야 한다",
        f"- 블록마다 왜 그 시간에 거기인지 {chars.get('itinerary_block_why')}자 이상",
    ])


def _rules_text() -> str:
    """둘을 합친 것. 재수집 프롬프트가 하한을 통째로 보여 줄 때 쓴다."""
    return _rules_spots() + "\n" + _rules_itinerary()


# --------------------------------------------------------------------------- #
# patch — **고친 곳만 받는다**
# --------------------------------------------------------------------------- #

#: `spots[1].image` · `itinerary.days[0].blocks[2].why` · `매력.items[2]` 를 토막낸다.
#
#  ★ 키가 **한글일 수 있다.** 국가 소개의 칸 이름이 `매력` · `환율` · `국기이미지`
#    이므로 `[A-Za-z_]` 로 잡으면 경로를 통째로 못 읽고 patch 가 전부 거부된다.
#    `[^\W\d]` 는 "글자이되 숫자가 아닌 것" — 한글·영문·밑줄을 함께 받는다.
_PATH_TOKEN = re.compile(r"([^\W\d]\w*)|\[(\d+)\]", re.UNICODE)


def _path_parts(path: str) -> list:
    """경로 문자열을 키·인덱스 리스트로. 모르는 글자가 섞이면 빈 리스트."""
    parts, cursor = [], 0
    text = (path or "").strip()
    while cursor < len(text):
        if text[cursor] == ".":
            cursor += 1
            continue
        match = _PATH_TOKEN.match(text, cursor)
        if not match:
            return []
        parts.append(match.group(1) if match.group(1) is not None else int(match.group(2)))
        cursor = match.end()
    return parts


def _same_shape_smaller(current, value) -> bool:
    """지금 값이 컨테이너일 때, 새 값이 **줄어들지 않는** 같은 모양인가.

    이미지처럼 `{"url": ..., "alt": ...}` 를 통째로 갈아 끼우는 것은 정당한 patch 다.
    반면 관광지 목록을 `[]` 로 비우는 것은 patch 가 아니라 삭제다. 그래서 **모양이
    같고 크기가 줄지 않을 때만** 통째 교체를 허용한다.
    """
    if isinstance(current, list):
        return isinstance(value, list) and len(value) >= len(current)
    if isinstance(current, dict):
        return isinstance(value, dict) and len(value) >= len(current)
    return False


def _kind_of(value) -> str:
    """patch 형 검사에 쓰는 이름. 숫자 둘(int · float)은 같은 형으로 본다."""
    if isinstance(value, bool):
        return "참/거짓"
    if isinstance(value, str):
        return "글자"
    if isinstance(value, (int, float)):
        return "숫자"
    if isinstance(value, list):
        return "목록"
    if isinstance(value, dict):
        return "객체"
    return "빈 값" if value is None else type(value).__name__


def apply_patches(city: dict, patches) -> tuple:
    """patch 를 지난 결과에 적용한다. **적용 못 한 것은 숨기지 않고 함께 돌려준다.**

    ★ 없는 경로를 **만들지 않는다.** 모델이 `spot[0]`(오타)을 주면 조용히 새 키가
      생기고, 검사기는 여전히 부족을 내며, 사람은 왜 안 고쳐지는지 알 길이 없다.
      리스트는 `len(리스트)` 자리(= 바로 뒤 한 칸)까지만 추가를 허용한다 —
      "근거 1건 부족" 같은 정당한 추가는 되고 엉뚱한 자리는 막힌다.

    ★ **칸의 형을 바꾸지 못한다.** 첫 수집은 `_normalize_*` 가 값을 글자로 맞추지만 재수집은
      patch 를 그대로 넣었다. 모델이 `preference_note` 를 목록으로 보내면 그대로 들어가고,
      다음 걸음의 `check_information` 이 그 칸에 `.strip()` 을 불러 **예외로 죽는다** — 그 run 은
      error 로 끝나고 Studio 패널에서는 재수집 뒤의 검사기가 "안 보인다". 검사기는 루프 킷과
      바이트 단위로 같아 고칠 수 없으므로, 들어오는 쪽에서 막는다. 지금 값이 있으면
      (빈 값이 아니면) 같은 형만 받는다.
    """
    out = copy.deepcopy(city)
    skipped = []
    for patch in _as_list(patches):
        if not isinstance(patch, dict):
            continue
        shown = str(patch.get("path") or "")
        parts = _path_parts(shown)
        if not parts:
            skipped.append(f"{shown!r}: 경로 형식을 못 읽었습니다")
            continue
        node, ok = out, True
        for step in parts[:-1]:
            if isinstance(step, int) and isinstance(node, list) and 0 <= step < len(node):
                node = node[step]
            elif isinstance(step, str) and isinstance(node, dict) and step in node:
                node = node[step]
            else:
                skipped.append(f"{shown}: '{step}' 이 지난 결과에 없습니다")
                ok = False
                break
        if not ok:
            continue
        #  ★ `value` 키가 아예 없으면 **거부한다.** 예전에는 `patch.get("value")` 가
        #    `None` 을 돌려주어 멀쩡하던 값을 `null` 로 덮어쓰고도 "적용됨"으로 셌다.
        #    응답이 patch 객체 중간에서 잘리면 정확히 이 모양이 된다.
        if "value" not in patch:
            skipped.append(f"{shown}: value 가 없습니다 (응답이 잘렸을 수 있습니다)")
            continue
        last, value = parts[-1], patch.get("value")

        #  ★ **조상 경로를 통째로 갈아 끼우지 못하게 한다.** `{"path": "spots"}` 한 줄로
        #    관광지 3곳이 전부 사라져도 예전에는 거부 목록이 비어 "성공"으로 보고됐다.
        #    patch 는 "고친 곳만"이라는 약속이므로, 지금 그 자리에 **컨테이너가 있는데**
        #    그것을 통째로 바꾸려는 요청은 patch 가 아니라 재작성이다.
        current = None
        if isinstance(last, str) and isinstance(node, dict):
            current = node.get(last)
        elif isinstance(last, int) and isinstance(node, list) and 0 <= last < len(node):
            current = node[last]
        if isinstance(current, (list, dict)) and current and not _same_shape_smaller(current, value):
            skipped.append(f"{shown}: 이 자리는 통째로 바꿀 수 없습니다 "
                           f"(안에 있는 칸을 하나씩 지정하십시오)")
            continue
        if current is not None and _kind_of(current) != _kind_of(value):
            skipped.append(f"{shown}: 형이 다릅니다 (지금은 {_kind_of(current)}, "
                           f"받은 것은 {_kind_of(value)}) — 같은 형으로 보내십시오")
            continue

        if isinstance(last, int) and isinstance(node, list):
            if 0 <= last < len(node):
                node[last] = value
            elif last == len(node):
                node.append(value)                  # 바로 뒤 한 칸까지만
            else:
                skipped.append(f"{shown}: 인덱스가 목록 범위를 넘습니다")
        elif isinstance(last, str) and isinstance(node, dict):
            node[last] = value
        else:
            skipped.append(f"{shown}: 마지막 칸의 형이 맞지 않습니다")
    return out, skipped


# --------------------------------------------------------------------------- #
# 이미지 확인 — **모델의 자기보고를 믿지 않는다**
# --------------------------------------------------------------------------- #


def _image_unchanged(before, after) -> bool:
    """재수집 뒤 사진이 **그대로인가** — 주소가 같고 확인 기록(`verified`)이 남아 있으면 그대로다.

    patch 가 사진을 통째로 갈아 끼우면 `verified` 가 빠지므로 다시 연다. 주소만 바꾸면 주소가
    달라 다시 연다. 모델이 `verified` 를 지어 붙여도 주소가 바뀌었으면 다시 연다.
    """
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    return (isinstance(after.get("verified"), dict)
            and str(before.get("url") or "") == str(after.get("url") or "")
            and before.get("verified") == after.get("verified"))


def _ascii_url(url: str) -> str:
    """URL 을 **ASCII 로만 된 형태**로 바꾼다. 실패하면 원본을 그대로 돌려준다.

    호스트는 IDNA(퓨니코드), 경로·질의는 퍼센트 인코딩이다. 이미 인코딩된 주소를
    두 번 인코딩하면 `%2F` 가 `%252F` 가 되어 멀쩡한 주소를 깨뜨리므로, `%` 를
    안전 문자로 남겨 **재인코딩하지 않는다.**
    """
    import urllib.parse
    try:
        parts = urllib.parse.urlsplit(url)
        host = parts.netloc
        try:
            host = host.encode("idna").decode("ascii")
        except Exception:                                       # noqa: BLE001
            pass                                                # 이미 ASCII 거나 특이한 형태
        return urllib.parse.urlunsplit((
            parts.scheme, host,
            urllib.parse.quote(parts.path, safe="/%:@$&+,;=~"),
            urllib.parse.quote(parts.query, safe="%=&:/?+,;@"),
            urllib.parse.quote(parts.fragment, safe="%"),
        ))
    except Exception:                                           # noqa: BLE001
        return url


def verify_asset(asset: dict) -> dict:
    """주소를 **직접 열어 보고** 그 결과를 `verified` 에 적는다.

    루프 킷이 실측에서 겪은 결함이 여기서 나왔다. 모델이 URL 형식을 완성하려고
    알 수 없는 조각(`thumb/8/8c/`)을 지어냈고, 주소가 '있기는' 해서 검사기가
    통과시켰다. 이미지 11장이 전부 죽어 있는데 판정은 SUCCESS 였다.

        검사기는 네트워크를 타지 않는다. **네트워크를 탄 기록**을 본다.
        그 기록을 만드는 것은 수집하는 쪽의 일이고, 그 자리가 여기다.

    모델에게 `verified` 를 적어 내라고 시키지 않는다. 그러면 그것마저 지어낸다.
    """
    import urllib.error
    import urllib.request
    from datetime import datetime

    out = dict(asset or {})
    raw = out.get("url")
    if raw is not None and not isinstance(raw, str):
        #  ★ 주소가 목록 · 숫자로 오면 검사기가 그 칸에서 `.strip()` 을 부르다 멈춘다.
        #    빈 주소로 두고 사유를 적는다 — 검사기는 '아직 안 모음'으로 세고 재수집이 채운다.
        out["url"] = ""
        out["verified"] = {"status": None, "content_type": "", "checked_at": "",
                           "error": f"주소가 글자가 아니었습니다 ({type(raw).__name__}) — 비워 두었습니다"}
        return out
    url = (raw or "").strip()
    if not url.startswith(("http://", "https://")):
        return out

    #  ★ **여기서 반드시 퍼센트 인코딩을 한다.** 요청 라인과 헤더는 latin-1 로
    #    인코딩되므로, URL 에 태국어·한글이 한 글자라도 있으면 요청이 나가기도 전에
    #    `UnicodeEncodeError` 가 난다. 실측:
    #
    #      …/Special:FilePath/วัดพระศรีรัตนศาสดาราม.jpg   (실존하는 왓프라깨우 사진)
    #        인코딩 없음  -> status 0 · UnicodeEncodeError   ← 죽은 것으로 기록됨
    #        인코딩 후    -> status 200 · image/jpeg          ← 멀쩡히 살아 있다
    #
    #    이것을 안 하면 **모델이 맞는 파일명을 찾아와도 이 함수가 계속 죽었다고
    #    적는다.** 루프 A 가 그 칸에서 영원히 수렴하지 않는다 — 재수집을 아무리
    #    돌려도 고칠 수 있는 쪽이 없기 때문이다. 방콕·하노이처럼 현지 문자
    #    파일명이 흔한 도시에서 정통으로 걸린다.
    safe_url = _ascii_url(url)

    #  User-Agent 도 같은 이유로 ASCII 여야 한다.
    request = urllib.request.Request(safe_url, headers={
        "User-Agent": "graph-starter-kit/1.0 (LangGraph course; image liveness check)"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            out["verified"] = {
                "status": response.status,
                "content_type": (response.headers.get("Content-Type") or "").split(";")[0].strip(),
                "checked_at": datetime.now().replace(microsecond=0).isoformat(),
            }
    #  실패도 **기록한다.** 지우고 넘어가면 검사기가 '아직 안 모았다'로 읽어
    #  루프 A 가 같은 자리를 계속 다시 돈다. 상태를 남겨야 사람이 판단한다.
    #
    #  ★ 예외를 하나로 뭉뚱그리지 않는다. 조치가 전혀 다르기 때문이다.
    #      404      그 파일명이 Commons 에 없다      -> 모델이 다시 찾으면 된다
    #      URLError 네트워크·방화벽                   -> 사람이 환경을 봐야 한다
    #      그 밖     주소 형식 자체가 잘못됐다         -> 모델이 형식을 고쳐야 한다
    #    이 `error` 문장은 `[지난 회차 결과]` JSON 에 실려 재수집 프롬프트로 그대로
    #    들어간다. 그래서 문장이 **행동을 지시할 수 있어야** 한다.
    except urllib.error.HTTPError as exc:
        out["verified"] = {
            "status": exc.code, "content_type": "", "checked_at": "",
            "error": f"HTTP {exc.code} (주소 형식이 아니라 **파일명**이 틀렸습니다. Commons 에 그 파일이 없습니다)"}
    except urllib.error.URLError as exc:
        out["verified"] = {
            "status": None, "content_type": "", "checked_at": "",
            "error": f"네트워크로 닿지 못했습니다 ({str(getattr(exc, 'reason', exc))[:80]})"}
    except UnicodeEncodeError:
        #  퍼센트 인코딩을 거치므로 여기까지 오면 주소 자체가 깨진 것이다.
        out["verified"] = {
            "status": None, "content_type": "", "checked_at": "",
            "error": "주소에 ASCII 로 바꿀 수 없는 문자가 있습니다 (요청을 보내지 못했습니다)"}
    except Exception as exc:                                    # noqa: BLE001
        out["verified"] = {
            "status": None, "content_type": "", "checked_at": "",
            "error": f"{type(exc).__name__}: {str(exc)[:100]}"}
    return out


# --------------------------------------------------------------------------- #
# 1. 도시 선정
# --------------------------------------------------------------------------- #


def select_city_names(state) -> tuple[list[str], str]:
    """도시 이름만 고른다. 여기서 정해진 개수가 곧 **병렬 폭**이 된다."""
    want = _as_dict(contract.counts().get("cities")).get("city_count") or 3
    country = state.get("country") or "베트남"

    if mode() == "live":
        prompt = (
            f"{country} {state.get('days')}일 여행에서 방문할 도시 {want}개를 고르십시오.\n\n"
            f"[반드시 지킬 것] **WebSearch 로 실제 조회한 뒤** 고르십시오. "
            f"기억으로 답하지 마십시오 — 이 킷은 실제 조회 횟수를 세어 기록에 남깁니다.\n\n"
            f"[여행자 취향]\n{_style_text(state)}\n\n"
            f"[도시를 고르는 기준]\n"
            + "\n".join(f"- {c}" for c in _as_list(state.get('city_priority')))
            + "\n\n마지막에 아래 형식의 ```json 블록 하나만 출력하십시오. 설명은 그 앞에 쓰십시오.\n"
            '```json\n{"cities": ["도시1", "도시2", "도시3"]}\n```'
        )
        try:
            data, stats = _claude_run(prompt, tools=["WebSearch", "WebFetch"], max_turns=10,
                                      label="select_cities")
            names = [str(n).strip() for n in _as_list(data.get("cities")) if str(n).strip()]
            if names:
                return names[:want], (f"select_cities: live 로 도시 {len(names[:want])}개 선정"
                                      + _stat_text(stats))
        except ClaudeUnavailable as exc:
            return _replay_city_names(want), f"select_cities: live 실패({exc}) → replay 폴백"

    return _replay_city_names(want), f"select_cities: replay 로 도시 {want}개 선정"


def _replay_city_names(want: int) -> list[str]:
    names = [str(c["name"]).strip() for c in _as_list(contract.baseline().get("cities"))
             if isinstance(c, dict) and c.get("name")]
    return names[:want] or ["하노이", "다낭", "호이안"][:want]


# --------------------------------------------------------------------------- #
# 2. 국가 소개 — 첫 수집 (고치기는 `repair_country_intro`)
# --------------------------------------------------------------------------- #


def collect_country_intro(state) -> tuple:
    """국가 소개 8칸. 도시와 무관하므로 도시 선정과 나란히 돈다.

    ★ **여기는 첫 수집만 한다.** 고치는 일은 `repair_country_intro` 가 맡는다.
      도시(`collect_one_city` / `repair_one_city`)와 같은 나눔이다.

    ★ 한때 국가 소개에는 재수집 자체가 없었다. 근거는 "자산 제외 2,677자라 한
      응답에 담기고도 남으니(잘림 임계 12,341자) 1회차에 실패할 이유가 없다"였다.
      **그 근거는 `잘림` 만 배제한다.** 실제로 터진 것은 `수집 부족` 이었고 —
      근거 15건을 한 번에 요구하는데 모델이 얇게 내고 스스로 끝냈다 — 그 실패
      방식은 분량과 아무 상관이 없었다. 되먹임이 없으니 부족이 그대로 최종
      보고서까지 갔다. 지금은 도시와 같이 patch 로 고친다.

    돌려주는 것: (국가소개, 기록, 실패사유). 실패사유가 비면 성공이다.
    """
    country = state.get("country") or "베트남"
    rules = _as_dict(contract.counts().get("country_intro"))

    if mode() != "live":
        return _replay_country(), "collect_country: replay 로 국가 소개 수집", ""

    want = ", ".join(f"{k}({v.get('target', 1)}건)" for k, v in rules.items()
                     if v.get("kind") in ("다건", "단건"))
    min_item = _as_dict(contract.counts().get("min_chars")).get("evidence_item", 60)
    prompt = (
        f"{country} 여행 정보 웹페이지의 '국가 소개' 칸을 채울 근거를 모으십시오.\n\n"
        f"[반드시 지킬 것] 근거는 **WebSearch·WebFetch 로 실제 조회해서** 얻으십시오. "
        f"기억으로 쓴 URL 은 열리지 않고, 이 킷은 실제 조회 횟수를 세어 기록에 남깁니다.\n"
        f"[채울 칸] {want}\n"
        f"[규칙] 근거 1건은 **{min_item}자 이상**, '다건' 칸은 **서로 다른 출처 2곳 이상**\n"
        f"[규칙] 같은 내용을 문장만 바꿔 두 번 넣지 마십시오. 중복 검사에 걸립니다.\n"
        f"[규칙] {min_item}자는 하한이지 목표가 아닙니다. 하한에 맞춰 끊지 마십시오.\n"
        f"[출처] 블로그·카페도 씁니다. 등급은 따지지 않습니다.\n\n"
        "**설명 문장을 쓰지 말고 곧바로** 아래 형식의 ```json 블록 하나만 출력하십시오.\n"
        '''```json\n{"매력": {"items": [{"text": "...", "source_url": "https://..."}]}, '''
        '''"역사": {"items": []}, "문화": {"items": []}, "주의사항": {"items": []}, '''
        '''"국가상태": {"checked": true, "items": []}, "항공권가격": {"items": []}, '''
        '''"환율": {"items": []}, "교통개요": {"items": []}}\n```'''
    )
    try:
        data, stats = _claude_run(prompt, tools=["WebSearch", "WebFetch"], max_turns=24,
                                  label="collect_country")
        merged = _merge_country(data)
        return merged, f"collect_country: live 로 {len(merged)}칸 수집" + _stat_text(stats), ""
    except ClaudeUnavailable as exc:
        #  국가 소개는 baseline 이 언제나 있다 (인계본에 들어 있는 칸이므로).
        #  그래도 폴백 사실은 기록에 남긴다 — live 결과인 척하지 않는다.
        return (_replay_country(),
                f"collect_country: live 실패({exc}) → replay 폴백", str(exc))


def _merge_country(data: dict) -> dict:
    """LLM 이 준 것에 이미지 자산 두 칸을 붙인다.

    국기·대표 이미지는 인계본의 것을 쓰되, **live 에서는 다시 열어 본다.**
    남의 `verified` 기록을 그대로 물려 쓰면 그 사이에 죽은 주소를 못 잡는다.
    """
    out = {k: v for k, v in data.items() if isinstance(v, dict)}
    base = _as_dict(contract.baseline().get("country_intro"))
    for key in ("국기이미지", "대표이미지"):
        if key not in base:
            continue
        node = copy.deepcopy(base[key])
        node["asset"] = verify_asset(_as_dict(node.get("asset")))
        out[key] = node
    return out


def _replay_country() -> dict:
    """replay 자료. **1회차에도 덜어내지 않는다.**

    예전에는 여기서도 근거를 한 건씩 빼서 루프 A 를 한 바퀴 돌게 했다. 그런데
    국가 소개의 replay 재수집(`repair_country_intro`)도 이 함수를 그대로 돌려주므로
    여기서 빼면 **영원히 못 채우는 칸**이 된다. 한 바퀴 돌리는 장치는 `_replay_city` 의 이미지 한 장으로 충분하다.
    """
    return copy.deepcopy(_as_dict(contract.baseline().get("country_intro")))


# --------------------------------------------------------------------------- #
# 3. 도시 하나 (★ 병렬로 도는 자리) — **claude -p 를 두 번 부른다**
# --------------------------------------------------------------------------- #


def _empty_city(city_name: str) -> dict:
    """뼈대만. **이것을 정상 결과로 돌려주지 않는다** — 언제나 실패사유와 함께 나간다."""
    return {"name": city_name, "why_selected": "", "spots": [],
            "preference_note": "", "itinerary": {"items": [], "days": []}}


def _baseline_city(city_name: str):
    """인계본에서 그 도시를 찾는다. **없으면 None** — 빈 껍데기를 지어내지 않는다."""
    for city in _as_list(contract.baseline().get("cities")):
        if isinstance(city, dict) and (city.get("name") or "").strip() == city_name:
            return copy.deepcopy(city)
    return None


def _replay_city(city_name: str, hold_first: bool = False):
    """replay 자료. baseline 에 없으면 None."""
    found = _baseline_city(city_name)
    if found is None:
        return None
    if hold_first and REPLAY_HOLDS_FIRST_PASS and found.get("spots"):
        # 1회차: 마지막 관광지의 **이미지만** 뺀다 → check_information 이 SHORT 를 낸다.
        # 일정이 참조하는 관광지 이름은 그대로 남으므로 다른 검사행에 잡음이 없다.
        found["spots"][-1]["image"] = {}
    return found


def _spot_menu(spots: list) -> str:
    """일정 호출에 넘길 관광지 목록. **이름을 그대로 쓰게 하려고** 요약까지 붙인다."""
    lines = []
    for spot in _as_list(spots):
        if not isinstance(spot, dict) or not spot.get("name"):
            continue
        summary = (spot.get("detail") or "").strip().replace("\n", " ")[:60]
        lines.append(f"  - {spot['name']} : {summary}")
    return "\n".join(lines) or "  (없음 — 명소 수집이 실패했습니다)"


def _prompt_spots(city_name: str, state) -> str:
    counts = contract.counts()
    return (
        f"{state.get('country')} {state.get('days')}일 여행 중 **{city_name}** 의 "
        f"관광지를 조사하십시오.\n\n"
        f"[반드시 지킬 것] 관광지·근거·이미지는 **WebSearch·WebFetch 로 실제 조회해서** "
        f"얻으십시오.\n기억으로 쓴 근거와 URL 은 검증에서 걸립니다. 이 킷은 실제 조회 "
        f"횟수를 세어 기록에 남깁니다.\n\n"
        f"[여행자 취향]\n{_style_text(state)}\n\n"
        f"[채워야 할 개수]\n{_rules_spots()}\n\n"
        f"[취향 설명] 왜 이 관광지를 넣었고 **무엇을 왜 뺐는지**를 줄마다 하나씩 씁니다.\n"
        f"뺀 곳은 이름을 밝히십시오. 줄마다 내용이 달라야 하고, 번호만 바꿔 복제하면 "
        f"검사에 걸립니다.\n\n"
        f"[이미지] 주소를 **기억으로 쓰지 마십시오.** 반드시 조회로 얻고, 아래 형태로만 씁니다.\n"
        f"  {_as_dict(counts.get('asset_rule')).get('recommended_form')}\n"
        f"  파일명은 **WebSearch 로 `commons.wikimedia.org` 에서 실제로 확인한 것**만 씁니다.\n"
        f"  확인하지 못했으면 `image` 를 비워 두십시오. 지어낸 주소는 이 킷이 직접 열어 보고\n"
        f"  죽은 것으로 기록하며, 그 칸은 다음 바퀴에서 다시 수집 대상이 됩니다.\n"
        f"  `verified` 는 적지 마십시오 — 이 킷의 코드가 직접 열어 보고 채웁니다.\n\n"
        f"[취향 원문 발췌]\n{contract.user_request()[:1500]}\n\n"
        "**설명 문장을 쓰지 말고 곧바로** 아래 형식의 ```json 블록 하나만 출력하십시오.\n"
        "일정은 이 호출에서 만들지 않습니다. **관광지까지만** 쓰십시오.\n"
        '''```json\n{"name": "''' + city_name + '''", '''
        '''"why_selected": "이 도시를 고른 이유(계약의 하한 이상)", '''
        '''"spots": [{"name": "...", "detail": "계약의 상세 하한 이상", '''
        '''"items": [{"text": "계약의 근거 하한 이상", "source_url": "https://..."}], '''
        '''"image": {"url": "https://...", "alt": "..."}}], '''
        '''"preference_note": "줄바꿈으로 구분. 줄마다 서로 다른 내용"}\n```'''
    )


def _prompt_itinerary(city_name: str, state, spots: list) -> str:
    days = _as_dict(contract.counts().get("itinerary")).get("days_per_city")
    return (
        f"{state.get('country')} 여행 중 **{city_name}** 에 머무는 {days}일치 일정을 "
        f"짜십시오.\n\n"
        f"[이 도시에서 조사한 관광지]  ← `spot` 에는 **이 이름을 그대로** 쓰십시오. "
        f"목록에 없는 이름을 쓰면 검사기가 잡습니다.\n{_spot_menu(spots)}\n\n"
        f"[반드시 지킬 것] 일정 근거(영업시간·이동시간·휴관일 등)는 "
        f"**WebSearch·WebFetch 로 실제 조회해서** 얻으십시오.\n\n"
        f"[여행자 취향]\n{_style_text(state)}\n\n"
        f"[채워야 할 개수]\n{_rules_itinerary()}\n\n"
        "**설명 문장을 쓰지 말고 곧바로** 아래 형식의 ```json 블록 하나만 출력하십시오.\n"
        '''```json\n{"items": [{"text": "일정 근거(하한 이상)", "source_url": "https://..."}], '''
        '''"days": [{"day": 1, "blocks": ['''
        '''{"start": "09:00", "end": "11:30", "kind": "명소", "spot": "위 목록의 이름", '''
        '''"why": "왜 이 시간에 여기인지(하한 이상)"}, '''
        '''{"start": "12:00", "end": "13:10", "kind": "식사", "place": "...", "why": "..."}'''
        ''']}]}\n```'''
    )


def collect_one_city(city_name: str, state) -> tuple:
    """도시 하나의 **첫 수집.** `claude -p` 를 두 번 부른다.

    ★ 노드를 쪼개는 것이 아니다. Studio 그림에서는 `collect_city` 상자 하나 그대로다.
      나누는 것은 **한 응답이 감당할 분량**이다 (7,400자 -> 3,700자씩).

    ★ 순차여야 한다. 일정의 '명소' 블록은 먼저 고른 관광지 이름을 써야 하고
      검사기가 그것을 대조한다. 그래서 ①의 결과를 ②의 프롬프트에 넣는다.

    ★ 쪼갠 이득이 실패에서 드러난다. 예전에는 한 번 잘리면 도시 전체가 날아갔다.
      지금은 **일정이 실패해도 명소는 살아남는다.**

    돌려주는 것: (도시, 기록, 실패사유). 실패사유가 비어 있으면 성공이다.
    """
    if mode() != "live":
        city = _replay_city(city_name, hold_first=True)
        if city is None:
            return (_empty_city(city_name),
                    f"collect_city[{city_name}]: replay 자료에 이 도시가 없습니다",
                    f"replay 자료(graph/research_data.json)에 '{city_name}' 이 없습니다")
        return city, f"collect_city[{city_name}]: replay 로 수집", ""

    notes, failure = [], ""

    # ---- ① 명소 ---------------------------------------------------------
    try:
        data, stats = _claude_run(_prompt_spots(city_name, state),
                                  tools=["WebSearch", "WebFetch"], max_turns=30,
                                  label=f"collect_city[{city_name}] 명소")
        city = _normalize_spots(data, city_name)
        notes.append(f"명소 {len(city['spots'])}곳" + _stat_text(stats))
    except ClaudeUnavailable as exc:
        fallback = _replay_city(city_name)
        if fallback is None:
            #  ★ 여기가 예전에 빈 껍데기를 정상인 척 돌려주던 자리다.
            #    이제는 실패사유와 함께 나가고, 게이트가 그것을 그대로 보여 준다.
            return (_empty_city(city_name),
                    f"collect_city[{city_name}]: 명소 수집 실패 → 대체할 자료도 없음",
                    f"명소 수집 실패({exc}) · 인계본에도 '{city_name}' 이 없어 대체 불가")
        return (fallback,
                f"collect_city[{city_name}]: 명소 실패({exc}) → replay 폴백", str(exc))

    # ---- ② 일정 ---------------------------------------------------------
    try:
        data, stats = _claude_run(_prompt_itinerary(city_name, state, city["spots"]),
                                  tools=["WebSearch", "WebFetch"], max_turns=24,
                                  label=f"collect_city[{city_name}] 일정")
        city["itinerary"] = _normalize_itinerary(data)
        notes.append(f"일정 {len(city['itinerary']['days'])}일" + _stat_text(stats))
    except ClaudeUnavailable as exc:
        fallback = _replay_city(city_name)
        if fallback is None:
            city["itinerary"] = {"items": [], "days": []}
            notes.append(f"일정 실패({exc}) — **명소는 살렸습니다**")
            failure = f"일정 수집 실패({exc}) · 명소 {len(city['spots'])}곳은 남아 있습니다"
        else:
            city["itinerary"] = _as_dict(fallback.get("itinerary"))
            notes.append(f"일정 실패({exc}) → replay 폴백")
            failure = str(exc)

    return city, f"collect_city[{city_name}]: " + " · ".join(notes), failure


def repair_one_city(city_name: str, state, short_slots) -> tuple:
    """지적된 칸만 **patch** 로 받아 지난 결과에 적용한다.

    ★ 전체 JSON 을 다시 받지 않는다. 예전에는 "고치지 않은 값은 그대로 옮겨
      적으십시오"라고 시켰는데, 그러면 한 칸 고치려고 7,400자를 재타이핑하다가
      멀쩡하던 관광지나 하루가 통째로 사라졌다. patch 는 **안 건드린 값이
      물리적으로 바뀌지 않는다.**

    ★ 그래서 `_keep_bigger` 같은 방어 코드가 없어졌다. 방어할 일이 없다.
    """
    previous = _previous_city(state, city_name)
    todo = _repair_lines(short_slots, city_name)
    if not previous:
        # 지난 결과가 없으면 고칠 대상이 없다. 첫 수집으로 돌린다.
        return collect_one_city(city_name, state)
    if not todo:
        # ★ 지적이 없는 도시는 **부르지 않는 것이 맞다** (라우터가 걸러 준다).
        #   그래도 들어왔다면 손대지 않고 그대로 돌려준다 — 예전에는 이 자리에서
        #   첫 수집 프롬프트로 떨어져 멀쩡한 도시를 통째로 다시 뽑았다.
        return previous, f"repair_city[{city_name}]: 지적 없음 — 손대지 않았습니다", ""

    if mode() != "live":
        fixed = _replay_city(city_name)
        if fixed is None:
            return previous, f"repair_city[{city_name}]: replay 자료 없음", ""
        return fixed, f"repair_city[{city_name}]: replay 로 {len(todo)}곳 보정", ""

    prompt = (
        f"{state.get('country')} 여행 중 **{city_name}** 구간에서 "
        f"**지적된 곳만 고치십시오.** 새로 조사하는 일이 아닙니다.\n\n"
        f"[이번에 고칠 곳]  (검사기가 센 결과입니다)\n"
        + "\n".join(f"  - {t}" for t in todo) + "\n\n"
        f"{_human_note(state)}"
        f"{_repair_howto()}\n"
        f"[계약 하한]  고친 값도 이 하한을 지켜야 합니다\n{_rules_text()}\n\n"
        f"[지난 회차 결과]  **읽기용입니다. 다시 적지 마십시오.**\n```json\n"
        f"{json.dumps(previous, ensure_ascii=False)[:20000]}\n```\n\n"
        "**고친 곳만** 아래 형식의 patch 목록으로 출력하십시오.\n"
        "전체 JSON 을 다시 쓰면 분량 때문에 블록이 닫히기 전에 잘립니다.\n\n"
        "경로 쓰는 법\n"
        "  spots[0].detail                  0번째 관광지의 상세 소개\n"
        "  spots[2].image                   2번째 관광지의 이미지 (통째로 교체)\n"
        "  spots[1].items[2]                1번째 관광지의 근거를 **한 칸 추가**\n"
        "                                   (지금 2건이면 [2]. 건너뛴 인덱스는 거부됩니다)\n"
        "  preference_note                  취향 설명 전체\n"
        "  why_selected                     도시 선정 이유\n"
        "  itinerary.items[3]               일정 근거 추가\n"
        "  itinerary.days[3].blocks[1].why  4일차 2번째 블록의 이유\n\n"
        '''```json\n{"patches": ['''
        '''{"path": "spots[2].image", "value": {"url": "https://...", "alt": "..."}}, '''
        '''{"path": "itinerary.days[0].blocks[1].why", "value": "..."}'''
        ''']}\n```'''
    )
    try:
        data, stats = _claude_run(prompt, tools=["WebSearch", "WebFetch"], max_turns=24,
                                  label=f"repair_city[{city_name}]")
    except ClaudeUnavailable as exc:
        return (previous, f"repair_city[{city_name}]: 실패({exc}) — 지난 결과를 그대로 둡니다",
                str(exc))

    patches = _as_list(data.get("patches"))
    fixed, skipped = apply_patches(previous, patches)
    #  이미지는 모델의 자기보고를 받지 않는다. **바뀐 것만** 다시 열어 본다.
    #  ★ 예전에는 주석과 달리 관광지 사진을 **전부** 다시 열었다. 한 장에 20초까지 걸려
    #    재수집 한 갈래가 그만큼 길어졌고 — 다음 걸음의 `check_information` 은 가장 느린
    #    갈래를 기다린다 — Commons 가 429 · 5xx 를 주면 멀쩡한 사진이 "파일명이 틀렸습니다"로
    #    적혔다. 주소가 그대로이고 확인 기록이 남아 있는 사진은 건드리지 않는다.
    before = [s.get("image") if isinstance(s, dict) else None
              for s in _as_list(previous.get("spots"))]
    for index, spot in enumerate(_as_list(fixed.get("spots"))):
        if isinstance(spot, dict) and isinstance(spot.get("image"), dict):
            if _image_unchanged(before[index] if index < len(before) else None, spot["image"]):
                continue
            spot["image"] = verify_asset(spot["image"])

    lookup = any(w in t for t in todo for w in _LOOKUP_WORDS)
    note = (f"repair_city[{city_name}]: 지적 {len(todo)}곳 · "
            f"patch {len(patches) - len(skipped)}건 적용"
            + (f" · 거부 {len(skipped)}건" if skipped else "")
            + _stat_text(stats, expect_search=lookup))
    for line in skipped[:2]:
        note += f"\n  ↳ 적용 못 함: {line}"
    #  ★ patch 를 하나도 못 냈으면 그것도 실패다. 조용히 넘어가면 같은 바퀴를 반복한다.
    applied = len(patches) - len(skipped)
    failure = ("" if applied > 0 else
               ("patch 를 하나도 내놓지 않았습니다 (지적을 못 읽었을 수 있습니다)"
                if not patches else
                f"낸 patch {len(patches)}건이 전부 거부됐습니다 — {skipped[0] if skipped else ''}"))
    return fixed, note, failure


def _repair_howto_country() -> str:
    """국가 소개에서 나오는 지적은 세 종류뿐이다. 문장을 **행동으로 번역**해 준다."""
    form = _as_dict(contract.counts().get("asset_rule")).get("recommended_form")
    return (
        "[고치는 방법]\n"
        "- 지적되지 않은 칸은 **건드리지 마십시오.** patch 에 넣지 않으면 그대로 남습니다.\n"
        "  문장을 다듬으면 멀쩡하던 칸이 중복 검사에 걸립니다.\n"
        "- `목표 2 / 실제 1` = 그 칸에 근거를 **더** 찾아 넣으라는 뜻입니다. "
        "WebSearch 로 실제 조회하고, 이미 있는 것과 **다른 출처**여야 합니다. "
        "추가는 `<칸>.items[<지금 개수>]` 처럼 **바로 뒤 한 칸**에만 넣을 수 있습니다.\n"
        "- `서로 다른 출처 목표 2 / 실제 1` = 건수는 찼는데 **출처가 같습니다.** "
        "기존 항목 하나를 다른 출처의 것으로 **교체**하십시오 (`<칸>.items[1]`).\n"
        "- `이미지 주소가 열리지 않았습니다` = 주소 형식은 맞는데 그 **파일명이 없습니다.** "
        f"WebSearch 로 실제 파일명을 확인한 뒤 바꾸십시오. 권장 형태: {form}. "
        "확인하지 못했으면 그 칸은 **patch 하지 마십시오** — 지어낸 주소는 또 지적됩니다.\n"
        "- 변동값(환율·항공권가격)은 **조회한 날짜와 함께** 적으십시오. 값만 적으면 "
        "출처와 대조가 안 됩니다.\n"
    )


def repair_country_intro(state, short_slots) -> tuple:
    """★ 지적된 **국가 소개 칸만** patch 로 받아 지난 결과에 적용한다.

    `repair_one_city` 와 **같은 규격**이다. 국가 소개만 재수집 경로가 없어서
    첫 수집이 얇게 나오면 그대로 최종 보고서까지 갔다 — 게이트가 "재수집 대상이
    아닙니다"라고 알리기는 했지만, 알리는 것과 고칠 수 있는 것은 다르다.

    ★ **첫 수집으로 돌아가지 않는다.** 지난 결과에 붙이는 patch 만 받는다.
      전체를 다시 뽑게 하면 멀쩡하던 `매력` 3건이 사라지고 부족이 오히려 는다 —
      도시에서 이미 겪은 일이다(DEPENDENCY_REPORT 14d).

    ★ 칸 이름이 **한글**이라 `_PATH_TOKEN` 이 한글 키를 받아야 한다. 받지 못하면
      patch 가 전부 "경로 형식을 못 읽었습니다"로 거부되고, 조용히 아무것도
      고쳐지지 않는다.

    돌려주는 것: (국가소개, 기록, 실패사유). 실패사유가 비면 성공이다.
    """
    previous = _previous_country(state)
    todo = _repair_lines(short_slots, "기능1")
    if not previous:
        #  지난 결과가 없다 = 첫 수집이 아예 안 돌았다. 그때는 첫 수집이 맞다.
        return collect_country_intro(state)
    if not todo:
        #  지적이 없으면 부르지 않는 것이 맞다 (라우터가 걸러 준다).
        return previous, "repair_country: 지적 없음 — 손대지 않았습니다", ""

    if mode() != "live":
        return _replay_country(), f"repair_country: replay 로 {len(todo)}곳 보정", ""

    country = state.get("country") or "베트남"
    prompt = (
        f"{country} 여행 정보 웹페이지의 '국가 소개' 칸에서 "
        f"**지적된 곳만 고치십시오.** 새로 조사하는 일이 아닙니다.\n\n"
        f"[이번에 고칠 곳]  (검사기가 센 결과입니다)\n"
        + "\n".join(f"  - {t}" for t in todo) + "\n\n"
        f"{_human_note(state)}"
        f"{_repair_howto_country()}\n"
        f"[계약 하한]  고친 값도 이 하한을 지켜야 합니다\n{_rules_country()}\n\n"
        f"[근거는 실제 조회로]  WebSearch·WebFetch 로 실제 열어 본 것만 쓰십시오. "
        f"이 킷은 실제 조회 횟수를 세어 기록에 남깁니다.\n\n"
        f"[지난 회차 결과]  **읽기용입니다. 다시 적지 마십시오.**\n```json\n"
        f"{json.dumps(previous, ensure_ascii=False)[:20000]}\n```\n\n"
        "**고친 곳만** 아래 형식의 patch 목록으로 출력하십시오.\n"
        "전체 JSON 을 다시 쓰면 멀쩡한 칸이 사라집니다.\n\n"
        "경로 쓰는 법  (칸 이름은 위 지난 회차 결과의 **키를 그대로** 씁니다)\n"
        "  매력.items[3]              매력에 근거를 **한 칸 추가**\n"
        "                             (지금 3건이면 [3]. 건너뛴 인덱스는 거부됩니다)\n"
        "  역사.items[1]              1번째 근거를 **다른 출처의 것으로 교체**\n"
        "  환율.items[0].text         그 근거의 본문만 교체\n"
        "  환율.items[0].source_url   그 근거의 출처 주소만 교체\n"
        "  국가상태.checked           확인했다는 사실 (해당 없으면 items 는 [] 로 둔다)\n"
        "  국기이미지.asset           이미지를 통째로 교체 {\"url\": ..., \"alt\": ...}\n"
        "  대표이미지.asset.url       이미지 주소만 교체\n\n"
        '''```json\n{"patches": ['''
        '''{"path": "매력.items[3]", "value": {"text": "...", "source_url": "https://..."}}, '''
        '''{"path": "대표이미지.asset.url", "value": "https://..."}'''
        ''']}\n```'''
    )
    try:
        data, stats = _claude_run(prompt, tools=["WebSearch", "WebFetch"], max_turns=24,
                                  label="repair_country")
    except ClaudeUnavailable as exc:
        return (previous, f"repair_country: 실패({exc}) — 지난 결과를 그대로 둡니다",
                str(exc))

    patches = _as_list(data.get("patches"))
    fixed, skipped = apply_patches(previous, patches)
    #  이미지는 모델의 자기보고를 받지 않는다. **바뀐 것만** 다시 열어 본다 (repair_one_city 와 같다).
    for key in ("국기이미지", "대표이미지"):
        node = fixed.get(key)
        if isinstance(node, dict) and isinstance(node.get("asset"), dict):
            old = _as_dict(previous.get(key)).get("asset")
            if _image_unchanged(old, node["asset"]):
                continue
            node["asset"] = verify_asset(node["asset"])

    lookup = any(w in t for t in todo for w in _LOOKUP_WORDS)
    note = (f"repair_country: 지적 {len(todo)}곳 · "
            f"patch {len(patches) - len(skipped)}건 적용"
            + (f" · 거부 {len(skipped)}건" if skipped else "")
            + _stat_text(stats, expect_search=lookup))
    for line in skipped[:2]:
        note += f"\n  ↳ 적용 못 함: {line}"
    #  ★ patch 를 하나도 못 냈으면 그것도 실패다. 조용히 넘어가면 같은 바퀴를 반복한다.
    #  ★ **낸 개수가 아니라 붙은 개수를 본다.** 예전에는 `patches` 가 비었는지만 봐서,
    #    5건을 내고 5건이 전부 거부돼도 실패사유가 비어 있었다. `merge_failures` 는
    #    빈 사유를 "이번엔 성공"으로 읽으므로 실패가 조용히 지워졌다.
    applied = len(patches) - len(skipped)
    failure = ("" if applied > 0 else
               ("patch 를 하나도 내놓지 않았습니다 (지적을 못 읽었을 수 있습니다)"
                if not patches else
                f"낸 patch {len(patches)}건이 전부 거부됐습니다 — {skipped[0] if skipped else ''}"))
    return fixed, note, failure


def _normalize_spots(data: dict, city_name: str) -> dict:
    """명소 응답을 계약 모양으로. **판정은 하지 않는다** — 검사기의 일이다."""
    city = {
        #  ★ **모델이 준 이름을 쓰지 않는다.** `Send` 가 실어 보낸 `city_name` 이
        #    권위다. 예전에는 `data.get("name")` 을 우선했는데, 모델이 `다낭` 을
        #    `Da Nang` 으로 적어 오면 (1) `merge_cities` 가 upsert 가 아니라 **추가**가
        #    되어 도시가 4개로 세지고, (2) `fan_out_repairs` 가 `selected_city_names`
        #    로 대상을 고르므로 그 도시의 부족이 **영원히 재수집되지 않는다.**
        #    reducer 의 키를 모델이 쥐게 두면 안 된다.
        "name": (city_name or data.get("name") or "").strip(),
        "why_selected": str(data.get("why_selected") or "").strip(),
        "spots": [],
        "preference_note": str(data.get("preference_note") or "").strip(),
        "itinerary": {"items": [], "days": []},
    }
    for spot in _as_list(data.get("spots")):
        if not isinstance(spot, dict) or not spot.get("name"):
            continue
        city["spots"].append({
            "name": str(spot["name"]).strip(),
            "detail": str(spot.get("detail") or "").strip(),
            "items": [i for i in _as_list(spot.get("items")) if isinstance(i, dict)],
            # ★ 모델이 준 주소를 **여기서 직접 열어 본다.** 자기보고를 받지 않는다.
            "image": verify_asset(_as_dict(spot.get("image"))),
        })
    return city


def _normalize_itinerary(data: dict) -> dict:
    """일정 응답을 계약 모양으로."""
    return {
        "items": [i for i in _as_list(data.get("items")) if isinstance(i, dict)],
        "days": [d for d in _as_list(data.get("days")) if isinstance(d, dict)],
    }
