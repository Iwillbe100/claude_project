r"""Claude Code CLI 를 **찾아내는 단 하나의 자리.** 킷 소유 — 수정 금지.

한 줄 요약: **경로를 추측하지 않고, 실행해서 증명한다.**

---

## 왜 이 파일이 따로 있는가

`shutil.which("claude")` 한 줄이면 될 것 같지만, Windows 에서는 그 한 줄이
**실행할 수 없는 파일**을 돌려주는 일이 실제로 있다. npm 으로 Claude Code 를 깔면
같은 이름의 shim 이 여러 개 생기기 때문이다.

    %APPDATA%\npm\claude       308B   #!/bin/sh 로 시작하는 POSIX 스크립트  <- 실행 불가
    %APPDATA%\npm\claude.cmd   160B   Windows 배치 shim
    %APPDATA%\npm\claude.ps1   520B   PowerShell shim
    %APPDATA%\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe    진짜 바이너리

맨 위의 **확장자 없는 POSIX shim** 이 걸리면 `subprocess` 는 그것을 실행하지 못하고
이렇게 죽는다.

    [WinError 193] %1은(는) 올바른 Win32 응용 프로그램이 아닙니다

그리고 **그래프는 죽지 않는다.** `research` 가 이 오류를 `ClaudeUnavailable` 로 바꿔
조용히 `replay` 로 내려가기 때문이다. 화면은 정상으로 보이는데 매번 같은 자료가
나온다 — 이 킷이 가장 경계하는 종류의 실패다.

★ 이 실패의 진짜 위험은 **환경마다 다르게 나타난다**는 것이다. 어느 shim 이 걸리는지는
  PATH 순서 · PATHEXT · Python 패치 버전 · 설치 방식(npm / native installer / WSL)에
  따라 갈린다. 강사 PC 에서는 `.cmd` 가 멀쩡히 잡히므로 **강사는 이 실패를 재현하지
  못한다.** 그래서 "`claude` 대신 `claude.cmd` 를 찾게 한다"는 식의 수정은 이번
  교육생만 살리고 다음 교육생에서 다른 모양으로 다시 터진다. 이름을 잘못 고른 것이
  문제가 아니라 **고른 것을 검증하지 않은 것**이 문제이기 때문이다.

## 그래서 무엇을 하는가

후보를 순서대로 놓고 **하나씩 실제로 `--version` 을 실행해서, 종료 코드 0 인 첫 번째
것만** 채택한다. 추측하지 않는다. `WinError 193` 이 나면 그 후보를 버리고 다음으로
간다. 그리고 무엇이 왜 탈락했는지를 `report()` 에 남긴다 — 재현할 수 없는 실패는
**화면에 이유가 남아야만** 원격으로 진단할 수 있다 (`verify_env.py` C11 이 그 표를
그대로 싣는다).

## 킷 전체가 이 함수 하나만 쓴다

예전에는 검증기(C11)와 그래프(`research`)가 **각자 다른 방법으로** claude 를 찾았다.
C11 은 후보를 실행해 보고 채택했고, `research` 는 `shutil.which()` 결과를 그대로
믿었다. 그래서 **C11 은 통과하는데 C12 만 실패하는** 갈라짐이 실제로 일어났다.
C12 는 그래프가 쓰는 함수를 그대로 부르도록 만든 검사인데, 정작 경로 탐색만은
두 벌로 베껴져 있었던 것이다.

    검증기가 그래프와 다른 것을 보면, 그 검증기는 아무것도 보증하지 못한다.

## 왜 `.exe` 를 `.cmd` 보다 먼저 보는가

`.cmd` 는 `cmd.exe` 를 한 겹 더 띄우고 그 아래에서 진짜 프로세스(node)가 돈다.
`research._stream` 은 시간이 초과하면 감시 타이머가 프로세스를 죽이는데, `proc.kill()` 만
하면 `cmd.exe` 만 죽고 그 자식은 stdout 파이프를 쥔 채 고아로 남는다. 그래서 지금은
Windows 에서 `taskkill /T /F` 로 트리째 끊은 뒤 `proc.kill()` 을 한다. 그래도 `.exe` 를
직접 부르면 kill 이 한 겹 없이 바로 목표에 닿으므로 한 겹 더 안전하다. 취향이 아니라
타임아웃 설계와 맞물린 이유다.

같은 이유로 **`cmd.exe /c` 로 감싸지 않는다.** Windows 는 `shell=False` 로도 `.cmd` 를
실행할 수 있어 감쌀 필요가 없고, 감싸면 프로세스가 한 겹 더 생겨 위의 트리 종료에 기대야 한다. 게다가
이 킷은 `--allowedTools WebSearch,Read,Grep` 처럼 쉼표가 든 인자를 넘기므로 셸 파싱을
한 겹 더 태울 이유가 없다.

## 교육장 탈출구

`.env` 에 `GRAPH_CLAUDE_BIN=C:\경로\claude.exe` 를 적으면 그것을 **맨 먼저** 본다.
단, 그것도 실행해서 증명한다. 지정한 것이 죽어 있으면 경고를 한 번 남기고 나머지
후보로 계속 간다 — 조용히 무시하지도, 그것 하나 때문에 실습을 멈추지도 않는다.

## 직접 돌려 볼 수 있다

    python -m travel_graph.claude_cli

이 PC 에서 후보가 어떤 순서로 잡히고 무엇이 왜 탈락했는지 그대로 찍는다.
교육생 환경을 원격으로 진단할 때 이 출력 하나면 된다.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

WINDOWS = os.name == "nt"

#: 후보 하나가 살아 있는지 보는 데 주는 시간.
#: 실측: `claude.exe --version` 48ms, `claude.cmd --version` 79ms. 20초는 백신이
#: 수백 MB 짜리 바이너리를 처음 훑는 경우까지 감안한 값이다. 여기서 오래 기다리면
#: 그래프의 첫 노드가 통째로 느려지므로, 넉넉하되 무한정은 아니게 둔다.
PROBE_TIMEOUT = 20.0

#: npm 전역 설치본 안에서 진짜 바이너리가 있는 자리 (shim 폴더 기준 상대 경로).
_NPM_NATIVE = ("node_modules", "@anthropic-ai", "claude-code", "bin")

_LOCK = threading.Lock()
_RESOLVED: "str | None" = None
_ATTEMPTS: "list[dict]" = []
_WARNED = False


class ClaudeCliNotFound(RuntimeError):
    """후보를 **전부 실행해 봤지만** 하나도 살아 있지 않았다.

    `attempts` 에 후보별로 무엇을 왜 버렸는지가 들어 있다. 부르는 쪽은 이것을 사람이
    읽는 화면에 그대로 실어야 한다 — 강사 PC 에서 재현되지 않는 실패이기 때문이다.
    """

    def __init__(self, message: str, attempts: "list[dict]") -> None:
        super().__init__(message)
        self.attempts = attempts


# --------------------------------------------------------------------------- #
# 후보 모으기 — 어디를 볼 것인가
# --------------------------------------------------------------------------- #


def _which(name: str) -> "str | None":
    try:
        return shutil.which(name)
    except Exception:                                       # noqa: BLE001
        return None


def _npm_native_near(shim: "str | None") -> "list[str]":
    """npm shim 옆에서 그 설치본의 **진짜 실행 파일**로 건너간다.

    npm prefix 는 교육생마다 다를 수 있다. 그것을 물어보려면 `npm config get prefix` 로
    node 를 띄워야 하는데 느리고 실패할 수도 있다. shim 의 부모 폴더에서 상대 경로로
    찾으면 prefix 가 어디에 있든 그대로 맞는다.
    """
    if not shim:
        return []
    try:
        parent = Path(shim).parent
    except Exception:                                       # noqa: BLE001
        return []
    return [str(parent.joinpath(*_NPM_NATIVE, "claude.exe" if WINDOWS else "claude"))]


def candidates() -> "list[tuple[str, str]]":
    """볼 곳을 **(경로, 출처) 로 순서대로.** 앞에 있을수록 먼저 증명한다.

    존재하지 않는 경로는 여기서 걸러 낸다 — 없는 파일을 실행해 보는 것은 낭비이고,
    진단 표가 빈 경로로 길어지면 진짜 이유가 묻힌다. 다만 `GRAPH_CLAUDE_BIN` 만은
    예외로 남긴다. 교육생이 오타를 냈을 때 "그 경로에 파일이 없습니다"가 표에 찍혀야
    하기 때문이다.
    """
    forced = (os.environ.get("GRAPH_CLAUDE_BIN") or "").strip().strip('"').strip("'")
    raw: "list[tuple[str, str]]" = []
    if forced:
        raw.append((forced, "GRAPH_CLAUDE_BIN"))

    if WINDOWS:
        cmd_shim = _which("claude.cmd")
        posix_shim = _which("claude")
        raw.append((_which("claude.exe") or "", "PATH(claude.exe)"))
        raw += [(p, "npm 네이티브") for p in _npm_native_near(cmd_shim)]
        raw += [(p, "npm 네이티브") for p in _npm_native_near(posix_shim)]
        appdata = os.environ.get("APPDATA") or ""
        if appdata:
            raw.append((str(Path(appdata).joinpath("npm", *_NPM_NATIVE, "claude.exe")),
                        "npm 기본 prefix"))
        raw.append((str(Path.home() / ".local" / "bin" / "claude.exe"), "native installer"))
        raw.append((cmd_shim or "", "PATH(claude.cmd)"))
        #  ★ 확장자 없는 shim 은 **맨 마지막**이다. 그것이 POSIX 스크립트면 여기서
        #    WinError 193 으로 탈락하지만, 버리지 않고 순서만 내린다 — 다른 설치
        #    방식에서는 그것이 진짜 실행 파일일 수도 있기 때문이다.
        raw.append((posix_shim or "", "PATH(claude)"))
    else:
        raw.append((_which("claude") or "", "PATH(claude)"))
        raw.append((str(Path.home() / ".local" / "bin" / "claude"), "native installer"))

    seen: "set[str]" = set()
    out: "list[tuple[str, str]]" = []
    for path, source in raw:
        if not path:
            continue
        try:
            exists = Path(path).is_file()
            key = os.path.normcase(os.path.abspath(path))
        except OSError:
            continue
        if not exists and source != "GRAPH_CLAUDE_BIN":
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append((path, source))
    return out


# --------------------------------------------------------------------------- #
# 증명하기 — 실제로 실행해 본다
# --------------------------------------------------------------------------- #


def _attempt(path: str, source: str, ok: bool, version: str, why: str) -> dict:
    return {"path": path, "source": source, "ok": ok, "version": version, "why": why}


def _os_error_text(exc: OSError) -> str:
    """실행 실패를 **교육생이 조치할 수 있는 문장**으로 바꾼다."""
    if getattr(exc, "winerror", None) == 193:
        return ("[WinError 193] 실행 가능한 Windows 프로그램이 아닙니다 "
                "— npm 이 만든 확장자 없는 POSIX shim 입니다")
    if isinstance(exc, FileNotFoundError):
        return "그 경로에 파일이 없습니다"
    if isinstance(exc, PermissionError):
        return "실행 권한이 없습니다"
    return f"{exc.__class__.__name__}: {exc}"


def probe(path: str, source: str = "", *, timeout: float = PROBE_TIMEOUT) -> dict:
    """후보 하나를 **실제로 실행해서** 쓸 수 있는지 본다.

    돌려주는 것: `{"path", "source", "ok", "version", "why"}`

    ★ `WinError 193` 이 잡히는 자리가 정확히 여기다. "찾았다"와 "실행할 수 있다"는
      다른 말이고, 그 차이는 실행해 봐야만 안다. 이 한 번의 호출이 이 파일의 전부다.

    ★ `stdin` 을 막아 둔다. 부모의 stdin 을 물려받으면 `langgraph dev` 같은 서버 아래에서
      CLI 가 입력을 기다리며 멈출 수 있다.
    """
    try:
        proc = subprocess.run(
            [path, "--version"], shell=False,
            stdin=subprocess.DEVNULL, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return _attempt(path, source, False, "",
                        f"`--version` 이 {timeout:.0f}초 안에 끝나지 않았습니다")
    except OSError as exc:
        return _attempt(path, source, False, "", _os_error_text(exc))
    except Exception as exc:                                # noqa: BLE001
        return _attempt(path, source, False, "", f"{exc.__class__.__name__}: {exc}")

    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()
        why = f"`--version` 종료코드 {proc.returncode}"
        if tail:
            why += f": {tail[0].strip()[:120]}"
        return _attempt(path, source, False, "", why)

    head = (proc.stdout or proc.stderr or "").strip().splitlines()
    return _attempt(path, source, True, head[0].strip() if head else "?", "")


def _warn_if_forced_lost(attempts: "list[dict]") -> None:
    """`GRAPH_CLAUDE_BIN` 을 지정했는데 그것이 채택되지 않았으면 **말해 준다.**

    조용히 다른 것을 쓰면 "설정했는데 왜 반영이 안 되지"가 된다. 그렇다고 실습을 멈출
    이유도 없으므로(살아 있는 다른 후보를 찾았다) 경고만 남기고 진행한다.
    `research._effort()` 가 모르는 에포트 값을 다루는 방식과 같다.
    """
    global _WARNED
    if _WARNED or not attempts:
        return
    first = attempts[0]
    if first.get("source") != "GRAPH_CLAUDE_BIN" or first.get("ok"):
        return
    _WARNED = True
    print(f"[claude_cli] GRAPH_CLAUDE_BIN={first['path']!r} 을 쓰지 못했습니다 "
          f"({first['why']}) -> 다른 후보로 진행합니다")


def _not_found_text(attempts: "list[dict]") -> str:
    """`history` 와 LangSmith 트레이스에 남을 **한 줄.**

    ★ 짧아야 한다. 이 문장은 `research` 를 거쳐 게이트 화면의 `history` 꼬리표에
      **자르지 않고 그대로** 실리고, 도시가 3개면 세 줄이 다 이것으로 채워진다.
      그래서 대표 사유 하나와 **전모를 어디서 보는지**만 적는다. 후보별 전체 표는
      `report()` · `describe()` 와 `verify_env.py` C11 이 보여 준다.
    """
    if not attempts:
        return ("claude CLI 를 찾지 못했습니다 (후보 경로가 하나도 없습니다) — "
                "Claude Code 를 설치하고 `claude --version` 이 되는지 확인하십시오")
    first = attempts[0]
    return (f"claude CLI 후보 {len(attempts)}개가 전부 실행되지 않았습니다 "
            f"({first['source']}: {first['why']}) — 후보별 사유는 "
            f"`python -m travel_graph.claude_cli`")


def resolve(*, refresh: bool = False) -> str:
    """쓸 수 있다고 **증명된** claude 실행 파일의 절대 경로. 없으면 `ClaudeCliNotFound`.

    ★ 성공만 캐시한다. 실패까지 캐시하면 `langgraph dev` 를 띄워 둔 채 교육생이 설치를
      고쳐도 서버를 껐다 켜기 전에는 반영되지 않는다. 실패 경로는 대개 후보가 아예
      없거나(파일 존재만 보므로 즉시) 즉시 거부되므로(WinError 193) 다시 보는 값이 싸다.

    ★ 잠금이 필요한 이유: 도시 3곳이 `Send` fan-out 으로 **동시에** 이 함수를 부른다.
      잠금이 없으면 같은 탐색을 세 번 하고 `report()` 가 뒤섞인다.
    """
    global _RESOLVED, _ATTEMPTS
    with _LOCK:
        cached = _RESOLVED
        if cached and not refresh:
            return cached
        attempts: "list[dict]" = []
        for path, source in candidates():
            result = probe(path, source)
            attempts.append(result)
            if result["ok"]:
                _RESOLVED, _ATTEMPTS = path, attempts
                _warn_if_forced_lost(attempts)
                return path
        _ATTEMPTS = attempts
        raise ClaudeCliNotFound(_not_found_text(attempts), attempts)


def available() -> bool:
    """부를 수 있는가. 예외 대신 참/거짓만 필요한 자리를 위한 얇은 껍데기."""
    try:
        resolve()
    except ClaudeCliNotFound:
        return False
    return True


# --------------------------------------------------------------------------- #
# 진단 — 재현되지 않는 실패는 화면에 이유가 남아야 한다
# --------------------------------------------------------------------------- #


def report() -> "list[dict]":
    """마지막 탐색에서 후보별로 무슨 일이 있었는가.

    **진단 화면에 그대로 싣는 값이다.** 이 실패는 강사 PC 에서 재현되지 않으므로,
    교육생 화면에 남은 이 표가 유일한 단서가 된다.
    """
    with _LOCK:
        return [dict(a) for a in _ATTEMPTS]


def describe(attempts: "list[dict] | None" = None, *, failed_only: bool = False) -> "list[str]":
    """후보 탐색 결과를 **사람이 읽는 한 줄씩**으로. `verify_env.py` C11 이 그대로 쓴다.

    여기서 한 번만 모양을 정한다. 부르는 쪽마다 따로 그리면 또 갈라지기 때문이다.
    """
    rows = report() if attempts is None else attempts
    lines: "list[str]" = []
    for item in rows:
        if failed_only and item.get("ok"):
            continue
        mark = "채택" if item.get("ok") else "탈락"
        source = str(item.get("source") or "?")
        line = f"{mark} · {source:<16} {item.get('path')}"
        why = item.get("why") or item.get("version") or ""
        if why:
            line += f"  -> {why}"
        lines.append(line)
    return lines


def main() -> int:
    """`python -m travel_graph.claude_cli` — 이 PC 에서 무엇이 잡히는지 눈으로 본다."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[union-attr]
    except Exception:                                       # noqa: BLE001
        pass
    print("=" * 70)
    print(" claude CLI 탐색 — 후보를 실제로 실행해서 증명한다")
    print("=" * 70)
    try:
        executable = resolve()
    except ClaudeCliNotFound as exc:
        for line in describe(exc.attempts):
            print("  " + line)
        print("-" * 70)
        print(" 결과: 쓸 수 있는 claude 를 찾지 못했습니다")
        print("\n 조치")
        print("   1) `claude --version` 이 터미널에서 되는지 확인합니다")
        print("   2) 그래도 안 되면 .env 에 절대 경로를 지정합니다")
        print("      GRAPH_CLAUDE_BIN=C:\\Users\\<이름>\\AppData\\Roaming\\npm\\"
              "node_modules\\@anthropic-ai\\claude-code\\bin\\claude.exe")
        print("   3) live 조사 없이 실습만 이어가려면 GRAPH_MODE=replay")
        return 1
    for line in describe():
        print("  " + line)
    print("-" * 70)
    print(f" 결과: {executable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
