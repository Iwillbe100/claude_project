"""처방 가지(detour) — **문제가 난 지점에서만** 연다.

그래프의 루프 골격(노드 14개)은 그대로 둔다. 검사기 뒤에 **진단 노드** 하나를 세우고,
진단이 "이건 고칠 방법이 정해진 문제다"라고 가려낸 것만 처방 가지로 보낸다.
나머지는 지금처럼 재수집(LLM)이 맡는다 — 가지는 **알아본 실패**를 LLM 보다 먼저 받는 길이다.

    재수집(LLM)   원인을 몰라도 받는다 · 매번 다른 결과 · 토큰 · 바퀴를 쓴다
    처방 가지     알아본 원인만 받는다 · 같은 입력 → 같은 결과 · LLM 0 · 바퀴를 안 쓴다

★ 가지는 어떻게 생기나. 실패 기록(`evidence/failures/`)에서 같은 실패가 되풀이되고 고칠 법이
  정해지면 가지로 뺀다 (STEP 6 · `scripts/failure_report.py` 의 ③ · ③-2). 원인과 고칠 법이 이미
  알려진 실패 축(예: 인코딩)은 로그 실측 전에 미리 구축해 둔다. 킷 기본 셋 셋의 출생은
  `registry.py` 에 적혀 있다.

    check_* ─▶ diagnose_* ─┬─ (처방 가지 대상 없음) ─────────────▶ 루프 골격 그대로
                           └─ <kind> ─▶ fix_<kind> ─▶ test_<kind> ─┬ 합격         → check_* (검사기로 복귀)
                                                                  ├ 불합격·한도 안 → fix_<kind> 한 번 더
                                                                  └ 불합격·한도 끝 → 사람 (게이트)

**처방 가지 하나 = 세 조각.** 이름(kind)만 정하면 자리가 정해진다.

    travel_graph/detours/registry.py        한 줄   무엇을 · 어느 루프에서
    travel_graph/detours/<kind>.py          fix()   고치는 법 · inject() 실패 재현
    scripts/detour_tests/test_<kind>.py     run()   시험지 — **진단도 이것으로 하고 합격도 이것으로 판정한다**

★ 왜 시험지 하나로 진단과 합격을 같이 보나. 진단 기준과 합격 기준이 다르면
  "진단은 문제라는데 시험은 합격"인 틈이 생기고, 그 틈에서 그래프가 같은 처방 가지를
  끝없이 돈다. 한 파일이 두 역할을 하면 그 틈이 **구조적으로** 생기지 않는다.

★ 왜 처방 가지는 루프 골격의 **검사기 노드**로 돌아오나. 처방 가지의 시험지는 "그 문제가
  사라졌는가"만 본다. 계약을 채웠는가는 루프 골격의 검사기(루프 킷과 바이트 단위로 같은
  파일)가 본다. 판정 독립을 지키려면 반드시 같은 검사기로 다시 재야 한다.
  수집 노드(`collect_*`)로 돌아가면 합류(fan-in)가 영영 기다려 **조용히 멈춘다.**

★ 처방 가지는 **바퀴를 쓰지 않는다.** 바퀴(`loop_a_iter` · `loop_b_iter`)는 검사
  횟수다(첫 수집 1, 재수집·재생성마다 +1). 처방 가지는 자기 한도(`detour_limit`)를 따로 갖는다. 그래서 처방 가지가 돌아도
  재수집 기회가 줄지 않는다.
"""
from __future__ import annotations

import importlib
import importlib.util
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from travel_graph.detours.registry import DETOURS

ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = ROOT / "scripts" / "detour_tests"

#: 처방 가지 하나가 **사람의 판단 없이** 돌 수 있는 횟수. 게이트에서 사람이
#: `more` · `research` · `rebuild` 를 고르면 0 으로 되돌아간다 (바깥 루프는 사람 소유).
LIMIT = 2

#: 라우터 매핑에서 이미 쓰는 이름. 처방 가지 이름과 겹치면 간선이 엉뚱한 곳으로 간다.
#: `log` · `registry` 는 이 폴더의 파일 이름이라 모듈 자리가 겹친다.
RESERVED = frozenset({"repair", "repair_country", "gate", "retry", "back",
                      "build", "stop", "research", "rebuild", "done", "quality",
                      "again", "halt", "more", "proceed", "log", "registry"})

_KIND_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class DetourRegistryError(RuntimeError):
    """등록부가 잘못됐다. 그래프를 만들기 전에 멈춘다 — 틀린 배선으로 돌지 않게."""


@dataclass(frozen=True)
class Detour:
    kind: str
    loop: str
    title: str

    # ---- 이름에서 자리가 나온다 -------------------------------------------
    @property
    def fix_node(self) -> str:
        return "fix_" + self.kind

    @property
    def test_node(self) -> str:
        return "test_" + self.kind

    @property
    def diagnose(self) -> str:
        """이 처방 가지가 **갈라져 나오는** 진단 노드."""
        return "diagnose_info" if self.loop == "A" else "diagnose_page"

    @property
    def home(self) -> str:
        """합격하면 **돌아가는** 루프 골격의 검사기 노드."""
        return "check_information" if self.loop == "A" else "check_page"

    @property
    def gate(self) -> str:
        """한도를 다 쓰면 **넘기는** 사람의 자리."""
        return "human_gate_a" if self.loop == "A" else "human_gate_b"

    @property
    def module_name(self) -> str:
        return "travel_graph.detours." + self.kind

    @property
    def module_path(self) -> Path:
        return Path(__file__).resolve().parent / (self.kind + ".py")

    @property
    def test_path(self) -> Path:
        return TESTS_DIR / ("test_" + self.kind + ".py")

    @property
    def module(self):
        return importlib.import_module(self.module_name)


def _validate(rows) -> tuple:
    """등록부를 읽어 `Detour` 로 바꾼다. **틀린 줄이 있으면 여기서 멈춘다.**"""
    out, seen = [], set()
    for number, row in enumerate(rows, 1):
        where = f"registry.py 의 {number}번째 줄"
        if not isinstance(row, dict):
            raise DetourRegistryError(f"{where} 이 dict 가 아닙니다")
        kind = str(row.get("kind") or "")
        loop = str(row.get("loop") or "")
        title = str(row.get("title") or "").strip()
        if not _KIND_RE.match(kind):
            raise DetourRegistryError(
                f"{where}: kind '{kind}' 는 영문 소문자·숫자·밑줄만 씁니다 (노드 이름이 됩니다)")
        if kind in RESERVED:
            raise DetourRegistryError(
                f"{where}: kind '{kind}' 는 라우터가 이미 쓰는 이름입니다. 다른 이름을 고르십시오")
        if kind in seen:
            raise DetourRegistryError(f"{where}: kind '{kind}' 가 두 번 등록됐습니다")
        if loop not in ("A", "B"):
            raise DetourRegistryError(
                f"{where}: loop 는 'A'(정보량) 또는 'B'(페이지) 입니다. 지금 값: '{loop}'")
        if not title:
            raise DetourRegistryError(f"{where}: title 이 비어 있습니다")
        seen.add(kind)
        out.append(Detour(kind=kind, loop=loop, title=title))
    return tuple(out)


#: 등록된 처방 가지 전부. **순서 = 진단 우선순위.**
ALL = _validate(DETOURS)


def of_loop(loop: str) -> tuple:
    return tuple(d for d in ALL if d.loop == loop)


def kinds(loop: str) -> tuple:
    return tuple(d.kind for d in of_loop(loop))


def get(kind) -> Detour | None:
    for d in ALL:
        if d.kind == kind:
            return d
    return None


# --------------------------------------------------------------------------- #
# 시험지 — `scripts/detour_tests/test_<kind>.py`
# --------------------------------------------------------------------------- #

_TESTS: dict = {}


def test_module(kind: str):
    """시험지를 불러온다. 검사기(`nodes._checker`)와 같은 방식이다 — 복사하지 않고 불러 쓴다."""
    if kind in _TESTS:
        return _TESTS[kind]
    d = get(kind)
    if d is None:
        raise DetourRegistryError(f"등록되지 않은 처방 가지입니다: {kind}")
    spec = importlib.util.spec_from_file_location("detour_test_" + kind, d.test_path)
    if spec is None or spec.loader is None or not d.test_path.exists():
        raise DetourRegistryError(f"시험지가 없습니다: {d.test_path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _TESTS[kind] = module
    return module


def run_test(kind: str, root=None):
    """시험지를 푼다. 돌려주는 것은 검사기와 같은 `Result` (verdict · short)."""
    return test_module(kind).run(str(root or ROOT))


def probe(loop: str, root=None) -> list:
    """진단 — 그 루프의 시험지를 **등록 순서대로** 전부 풀어 본다.

    돌려주는 것: `[(Detour, Result 또는 None, 오류문장)]` 중 **불합격인 것만**.
    시험지가 스스로 터지면(학생이 막 만든 시험지일 수 있다) 그래프를 죽이지 않고
    오류문장을 남긴다 — 게이트 화면이 그것을 보여 준다.
    """
    found = []
    for d in of_loop(loop):
        try:
            result = run_test(d.kind, root)
        except Exception as exc:                                # noqa: BLE001
            found.append((d, None, f"시험지 test_{d.kind}.py 가 실행 중에 멈췄습니다 — "
                                   f"{type(exc).__name__}: {str(exc)[:120]}"))
            continue
        if result.verdict != "PASS":
            found.append((d, result, ""))
    return found


# --------------------------------------------------------------------------- #
# 고치는 법 · 실패 재현 — `travel_graph/detours/<kind>.py`
# --------------------------------------------------------------------------- #


def fix(kind: str, data: dict, *, attempt: int, mode: str) -> dict:
    """처방 가지 모듈의 `fix()` 를 부른다. `data` 를 **그 자리에서** 고친다.

    돌려주는 것: `{"fixed": [문장], "unfixed": [문장]}`. 모듈이 무엇을 돌려주든
    이 모양으로 맞춘다 — 노드(`nodes.fix_detour`)가 history 를 한 모양으로 쓰도록.
    """
    d = get(kind)
    if d is None:
        raise DetourRegistryError(f"등록되지 않은 처방 가지입니다: {kind}")
    #  ★ 교육생이 막 쓴 fix 가 예외를 내도 **그래프를 죽이지 않는다.** 못 고친 것으로 적고
    #    시험 노드로 넘긴다 — 시험에 떨어지면 한 번 더, 한도면 게이트에서 사람이 본다.
    #    (시험지가 터질 때 `probe` 가 하는 것과 같은 규칙)
    try:
        outcome = d.module.fix(data, attempt=attempt, mode=mode) or {}
    except Exception as exc:                                    # noqa: BLE001
        return {"fixed": [], "unfixed": [
            f"fix() 가 실행 중에 멈췄습니다 — {type(exc).__name__}: {str(exc)[:120]} "
            f"(travel_graph/detours/{kind}.py)"]}
    if not isinstance(outcome, dict):
        outcome = {}
    return {"fixed": [str(x) for x in (outcome.get("fixed") or [])],
            "unfixed": [str(x) for x in (outcome.get("unfixed") or [])]}


def howto(kind) -> str:
    d = get(kind)
    if d is None:
        return ""
    try:
        return str(getattr(d.module, "HOWTO", "") or "")
    except Exception as exc:                                    # noqa: BLE001
        #  모듈 import 가 깨지면 게이트 화면을 그리다 그래프가 죽는다 — 대신 이유를 보여 준다
        return f"처방 가지 모듈을 불러오지 못했습니다 — {type(exc).__name__}: {str(exc)[:100]}"


def parse_inject(value) -> tuple:
    """Studio 입력 `inject` 를 읽는다. `"encoding"` · `"a,b"` · `["a","b"]` 모두 받는다.

    돌려주는 것: (등록된 이름 목록, 모르는 이름 목록).
    """
    if isinstance(value, str):
        items = [x.strip() for x in value.split(",")]
    elif isinstance(value, (list, tuple)):
        items = [str(x).strip() for x in value]
    else:
        items = []
    items = [x for x in items if x]
    known = [x for x in items if get(x) is not None]
    unknown = [x for x in items if get(x) is None]
    return known, unknown


def inject(target: str, obj: dict, wanted) -> list:
    """**실패 재현.** 수집 직후의 도시(`target="city"`) 또는 국가 소개
    (`target="country"`)에 그 가지가 맡는 실패를 다시 일으킨다. 돌려주는 것: history 에 붙일 줄.

    ★ 이미 있는 가지가 켜지는 것을 보거나, STEP 6 에서 새 가지의 시험지가 **먼저
      떨어지는 것**(빨간불)을 볼 때 쓴다. replay 에서 쓰는 것을 권한다.
    """
    wanted = set(wanted or [])
    notes = []
    for d in ALL:
        if d.kind not in wanted or not isinstance(obj, dict):
            continue
        try:
            module = d.module
            if getattr(module, "INJECT_AT", "") != target:
                continue
            note = module.inject(obj)
        except Exception as exc:                                # noqa: BLE001
            notes.append(f"  ↳ ⚠ 실패 재현 [{d.kind}] 이 멈췄습니다 — "
                         f"{type(exc).__name__}: {str(exc)[:100]} (재현하지 못함)")
            continue
        if note:
            notes.append(f"  ↳ ⚠ 실패 재현 [{d.kind}] {note}")
    return notes


__all__ = ["ALL", "LIMIT", "Detour", "DetourRegistryError", "of_loop", "kinds", "get",
           "test_module", "run_test", "probe", "fix", "howto", "parse_inject", "inject"]
