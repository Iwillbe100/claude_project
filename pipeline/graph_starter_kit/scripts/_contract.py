#!/usr/bin/env python3
"""명세에서 '검사 기준'을 읽어 오는 공용 모듈. (그래프 킷판)

루프 킷과 **딱 한 곳만 다르다.** 기준을 어디서 읽는가.

  루프 킷    MASTER_SPEC.md 의 MACHINE 블록      (교육생이 STEP 1~7로 채운 곳)
  그래프 킷  graph/03_CONTRACT.json              (루프 킷이 내보낸 인계본)

  graph/03_CONTRACT.json  ──읽음──▶  check_information_count.py   루프 A
                          ──읽음──▶  check_page_contract.py       루프 B
                          ──읽음──▶  check_quality_passes.py      루프 C
                                     (스크립트는 숫자를 직접 갖지 않는다)

**왜 계약을 다시 정하지 않는가.** 루프판과 그래프판을 같은 자로 재기 위해서다.
계약을 그래프용으로 '개선'하는 순간 두 방식을 같은 표에 올릴 수 없게 된다.
그래서 계약은 인계본에서 그대로 읽고, 이 킷에서는 **실행 구조만** 바꾼다.

check_information_count.py · check_page_contract.py · check_quality_passes.py 는
루프 킷 파일과 **바이트 단위로 같다.** 바뀐 것은 이 로더 하나뿐이다.
아래 도우미들(rule · norm_text · unique_ratio · duplicate_lines · similarity ·
is_time · to_minutes · sha256_file)도 루프 킷과 같은 것을 그대로 둔다.

**예외는 `asset_problems` 하나다.** 그래프 킷은 죽은 이미지의 **사유**(status/에러)를
한 줄로 돌려준다 — 재수집 프롬프트가 그 사유를 읽어 고칠 방향을 정하기 때문이다
(`nodes._CAUSE_A` 가 `이미지 주소가 열리지 않았습니다` 로 분류한다).
루프 킷은 빠진 필드를 하나씩 나열한다. **이미지 행의 판정(부족)은 둘 다 같지만 부족 줄 수는
다를 수 있다** — `check_slot` 이 `problems[:2]` 까지 기록하므로, 열어 봤는데 실패한 이미지
한 장마다 루프 킷은 2줄(예: `verified.content_type 이 비어 있습니다` ·
`verified.checked_at 이 비어 있습니다`), 그래프 킷은 원인 1줄을 남긴다. 그래서 '못 채운 칸 N곳'은
그런 이미지 한 장마다 그래프 킷이 1곳 적다. 금지 주소가 함께 걸리면 둘 다 2줄로 같다.
`error` 가 있는데 status 가 허용값인 기록은 루프 킷에서는 통과, 그래프 킷에서는 부족이다.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def use_utf8_output():
    """Windows 콘솔에서 한글이 깨지지 않게 한다."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # pragma: no cover
            pass


class ContractError(Exception):
    """명세를 읽지 못했다. 이것은 '미완성'이 아니라 '깨짐'이다."""


def _strip_examples(text):
    return re.sub(
        r"<!--\s*EXAMPLE:BEGIN\s*-->.*?<!--\s*EXAMPLE:END\s*-->",
        "",
        text,
        flags=re.DOTALL,
    )


def load_machine_json(path):
    """파일의 MACHINE 블록 안에 있는 첫 json 코드 블록을 읽는다.

    이 킷의 검사 계약은 `graph/03_CONTRACT.json` 에서 오지만, STEP 명세 문서
    (`specs/0N_*.md`)는 루프 킷과 같은 MACHINE 블록 형식을 쓴다.
    `validate_specs.py` 가 그것을 읽을 때 이 함수를 쓴다.
    """
    if not path.exists():
        raise ContractError(path.name + " 파일이 없습니다")
    text = _strip_examples(path.read_text(encoding="utf-8"))
    region = re.search(
        r"<!--\s*MACHINE:BEGIN\s*-->(.*?)<!--\s*MACHINE:END\s*-->", text, re.DOTALL
    )
    if not region:
        raise ContractError(path.name + " 에 MACHINE 블록이 없습니다")
    block = re.search(r"```json\s*(.*?)```", region.group(1), re.DOTALL)
    if not block:
        raise ContractError(path.name + " 의 MACHINE 블록에 json 코드가 없습니다")
    try:
        return json.loads(block.group(1))
    except json.JSONDecodeError as exc:
        raise ContractError(path.name + " 의 MACHINE JSON 형식 오류: " + str(exc))


CONTRACT_PATH = "graph/03_CONTRACT.json"


def load_contract_json(root=None):
    """인계본의 검사 계약을 읽는다. 이것이 이 킷의 유일한 기준 출처다."""
    root = Path(root) if root else ROOT
    path = root / CONTRACT_PATH
    if not path.exists():
        raise ContractError(
            CONTRACT_PATH + " 이 없습니다. 루프 킷에서 "
            "`python scripts/export_graph_handoff.py` 로 만든 output/graph/ 폴더를 "
            "이 킷의 graph/ 에 통째로 복사하십시오"
        )
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ContractError(CONTRACT_PATH + " 형식 오류: " + str(exc))


def load_spec(root=None):
    """graph/03_CONTRACT.json 에서 검사에 필요한 네 가지를 꺼낸다.

    **quality_contract 가 네 번째다.** 루프 킷이 세 번째 루프(정성 완성도)를
    추가하면서 늘었다. 이것이 없는 인계본은 개정 전 버전이므로 다시 뽑아야 한다.
    """
    root = Path(root) if root else ROOT
    data = load_contract_json(root)

    request = data.get("request")
    counts = data.get("count_contract")
    page = data.get("page_contract")
    quality = data.get("quality_contract")

    for name, value in (
        ("request", request),
        ("count_contract", counts),
        ("page_contract", page),
        ("quality_contract", quality),
    ):
        if not isinstance(value, dict) or not value:
            raise ContractError(
                CONTRACT_PATH + " 에 " + name + " 이 없습니다"
                " (개정 전 인계본입니다. 루프 킷에서 다시 뽑으십시오)"
            )

    holes = []
    for name, value in (("request", request), ("count_contract", counts),
                        ("page_contract", page), ("quality_contract", quality)):
        holes.extend(find_nulls(value, name))
    if holes:
        raise ContractError(
            CONTRACT_PATH + " 의 검사 계약에 아직 채우지 않은 값이 "
            + str(len(holes)) + "개 있습니다: " + ", ".join(holes[:5])
            + " (루프 킷에서 STEP 7까지 끝낸 뒤 인계본을 다시 뽑으십시오)"
        )
    spec = {
        "request": request,
        "count_contract": counts,
        "page_contract": page,
        "quality_contract": quality,
        "loops": data.get("loops") or {},
        "options": data.get("options") or {},
    }
    # 여기서 한 번 더 본다. null 이 없어도 **값이 틀리면** 검사가 사라지기 때문이다.
    check_contract_shape(spec, CONTRACT_PATH)
    return spec


def find_nulls(node, path=""):
    """계약 안에 아직 채우지 않은 null 이 어디에 있는지 알려 준다."""
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            found.extend(find_nulls(value, path + "." + str(key) if path else str(key)))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(find_nulls(value, path + "[" + str(index) + "]"))
    elif node is None:
        found.append(path)
    return found



# --------------------------------------------------------------------------
# 계약값 검증 — 모르는 값을 조용히 넘기지 않는다
#
# 이 킷이 실제로 겪은 사고가 여기서 나왔다.
#   page_contract.feature2.layout 에 선택지 문구 그대로 "우측 툴바" 를 적었더니
#   검사기 안의 `== "drawer"` 가 어긋나 **검사행 6개가 통째로 사라졌고**,
#   그런데도 판정은 PASS 였다. 결과물이 아니라 **검사기가 스스로 약해진** 것이다.
#
# 그래서 허용값 밖의 값은 '아직 덜 됐다(SHORT)'가 아니라 '깨졌다(ERROR)'로 다룬다.
# null 은 find_nulls 가 먼저 잡으므로 여기서는 건너뛴다.
# --------------------------------------------------------------------------

#: 계약이 가질 수 있는 값. 여기 없는 값이 오면 그 자리의 검사가 사라지므로 막는다.
ALLOWED_ENUMS = {
    "count_contract.strictness": ("개수만", "개수와출처", "개수와출처와분량"),
    "count_contract.distinct_source_mode": ("url", "host"),
    "page_contract.strictness": ("요소존재", "동작연결", "내용대조"),
    "page_contract.feature1.layout": ("accordion", "tabs"),
    "page_contract.feature2.layout": ("drawer", "accordion"),
    "page_contract.feature3.layout": ("accordion", "tabs"),
}

#: 없으면 검사기가 자기 안의 기본값으로 조용히 되돌아가는 칸.
#: "검사기는 숫자를 스스로 갖지 않는다"는 약속을 코드가 지키게 하는 목록이다.
#: (null 로 두는 것은 '아직 안 정함'이지만, 키를 지우는 것은 '검사를 끈 것'이다)
REQUIRED_KEYS = (
    "count_contract.strictness",
    "count_contract.distinct_source_mode",
    "count_contract.min_chars.evidence_item",
    "count_contract.min_chars.spot_detail",
    "count_contract.min_chars.why_selected",
    "count_contract.min_chars.preference_note_line",
    "count_contract.min_chars.itinerary_block_why",
    "count_contract.dedup.min_unique_line_ratio",
    "count_contract.dedup.max_pair_similarity",
    "count_contract.dedup.shingle_size",
    "count_contract.asset_rule.require_verified",
    #  ★ 이 두 섹션이 없으면 검사기가 "검사할 칸 0개 / 도시 0개면 충분" 으로 되돌아가
    #    **완전히 빈 데이터에 PASS** 를 낸다. 나머지 섹션은 지우면 요란하게 실패한다.
    "count_contract.country_intro",
    "count_contract.cities",
    "count_contract.cities.city_count",
    "count_contract.cities.spots_per_city",
    "count_contract.itinerary.blocks_per_day_min",
    "page_contract.output_file",
    "page_contract.strictness",
    "page_contract.min_chars.panel_floor",
    "page_contract.min_chars.conditional_slot_chars",
    "page_contract.feature1.layout",
    "page_contract.feature1.headers",
    "page_contract.feature1.header_slots",
    "page_contract.feature2.layout",
    "page_contract.feature3.layout",
    "quality_contract.passes",
    "quality_contract.rules",
    "quality_contract.pass_focus",
    "quality_contract.watch_files",
    "quality_contract.regression_command",
)

#: 0 이나 음수로 두면 그 검사는 무엇이든 통과시킨다. 사실상 검사를 끈 것과 같다.
POSITIVE_KEYS = (
    "count_contract.min_chars.evidence_item",
    "count_contract.min_chars.spot_detail",
    "count_contract.min_chars.why_selected",
    "count_contract.min_chars.preference_note_line",
    "count_contract.min_chars.itinerary_block_why",
    "count_contract.cities.city_count",
    "count_contract.cities.spots_per_city",
    "count_contract.dedup.shingle_size",
    "count_contract.itinerary.blocks_per_day_min",
    "page_contract.min_chars.panel_floor",
    "page_contract.min_chars.conditional_slot_chars",
    "quality_contract.passes",
)

#: 비율은 0 초과 1 이하여야 뜻이 있다. 0 이면 항상 통과, 1 초과면 영원히 실패다.
RATIO_KEYS = (
    "count_contract.dedup.min_unique_line_ratio",
    "count_contract.dedup.max_pair_similarity",
)

_MISSING = object()


def dig(node, dotted):
    """'a.b.c' 경로로 계약 안쪽 값을 꺼낸다. 칸 자체가 없으면 _MISSING."""
    cur = node
    for key in dotted.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return _MISSING
        cur = cur[key]
    return cur


def check_contract_shape(spec, source="검사 계약"):
    """계약이 '검사가 성립하는 모양'인지 본다. 아니면 ContractError.

    여기서 걸리는 것은 결과물의 문제가 아니라 **계약의 문제**다.
    루프를 더 돌려도 해결되지 않으므로 exit 1(ERROR) 로 사람에게 넘긴다.
    """
    problems = []

    for path in REQUIRED_KEYS:
        if dig(spec, path) is _MISSING:
            problems.append(
                path + " 칸이 없습니다 — 지우면 검사기가 자기 안의 기본값으로 되돌아갑니다")

    for path, allowed in ALLOWED_ENUMS.items():
        value = dig(spec, path)
        if value is _MISSING or value is None:
            continue
        if value not in allowed:
            problems.append(
                path + " = " + repr(value) + " 는 허용값이 아닙니다 (허용: "
                + " / ".join(allowed) + "). 선택지 문구가 아니라 계약값을 적습니다")

    for path in POSITIVE_KEYS:
        value = dig(spec, path)
        if value is _MISSING or value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            problems.append(
                path + " = " + repr(value) + " 입니다. 1 이상이어야 검사가 성립합니다")

    for path in RATIO_KEYS:
        value = dig(spec, path)
        if value is _MISSING or value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) \
                or not (0 < value <= 1):
            problems.append(
                path + " = " + repr(value) + " 입니다. 0 초과 1 이하여야 합니다")

    # 배치와 부속 기능이 어긋나면 '만들 수 없는 화면'을 요구하게 된다.
    feature2 = dig(spec, "page_contract.feature2")
    if isinstance(feature2, dict) and feature2.get("layout") == "accordion" \
            and feature2.get("back_button"):
        problems.append(
            "page_contract.feature2: 툴바가 없는 배치(accordion)인데 back_button 이 true 입니다"
            " — 돌아갈 곳이 없는 뒤로 가기 단추를 요구하게 됩니다")

    quality = dig(spec, "quality_contract")
    if isinstance(quality, dict):
        focus = quality.get("pass_focus")
        passes = quality.get("passes")
        if isinstance(focus, dict) and isinstance(passes, int):
            missing = [str(n) for n in range(1, passes + 1) if str(n) not in focus]
            if missing:
                problems.append(
                    "quality_contract.pass_focus 에 " + ", ".join(missing)
                    + "회차의 렌즈가 없습니다 (passes=" + str(passes) + ")")

    if problems:
        raise ContractError(
            source + " 의 검사 계약이 성립하지 않습니다:\n  - " + "\n  - ".join(problems))


def load_research(root=None):
    """루프가 모은 정보를 읽는다. 없으면 '아직 안 모았다'는 뜻이다."""
    root = Path(root) if root else ROOT
    path = root / "output" / "research_data.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ContractError("output/research_data.json 형식 오류: " + str(exc))


# --------------------------------------------------------------------------
# 결과를 모으는 그릇
# --------------------------------------------------------------------------


class Result:
    """한 검사기의 결과. 세 가지를 분명히 구분한다.

      ok        통과
      short     기준에 못 미침  (아직 덜 됨. 루프가 더 돌면 된다)
      broken    구조가 깨짐      (사람이 고쳐야 한다)
    """

    def __init__(self, title):
        self.title = title
        self.rows = []      # (이름, 목표, 실제, 통과여부)
        self.short = []     # 부족한 것
        self.broken = []    # 깨진 것

    def row(self, name, target, actual, passed):
        self.rows.append((name, target, actual, bool(passed)))
        if not passed:
            self.short.append(name + ": 목표 " + str(target) + " / 실제 " + str(actual))

    def note_short(self, message):
        self.short.append(message)

    def note_broken(self, message):
        self.broken.append(message)

    @property
    def verdict(self):
        if self.broken:
            return "ERROR"
        if self.short:
            return "SHORT"
        return "PASS"

    @property
    def exit_code(self):
        return {"PASS": 0, "ERROR": 1, "SHORT": 2}[self.verdict]

    def to_dict(self):
        return {
            "title": self.title,
            "verdict": self.verdict,
            "rows": [
                {"name": n, "target": t, "actual": a, "passed": p}
                for n, t, a, p in self.rows
            ],
            "short": self.short,
            "broken": self.broken,
        }


def print_result(result, show_rows=True):
    line = "=" * 66
    print(line)
    print(" " + result.title)
    print(line)
    if show_rows and result.rows:
        print("  {:<34}{:>8}{:>8}   {}".format("검사 항목", "목표", "실제", "판정"))
        print("  " + "-" * 62)
        for name, target, actual, passed in result.rows:
            mark = "OK" if passed else "부족"
            print("  {:<34}{:>8}{:>8}   {}".format(
                name[:34], str(target), str(actual), mark))
        print("")

    if result.broken:
        print(" [ERROR] 구조가 깨졌습니다. 루프를 더 돌려도 해결되지 않습니다.")
        for message in result.broken:
            print("   - " + message)
    elif result.short:
        print(" [부족] " + str(len(result.short)) + "곳이 기준에 못 미칩니다.")
        for message in result.short[:12]:
            print("   - " + message)
        if len(result.short) > 12:
            print("   ... 그 밖 " + str(len(result.short) - 12) + "곳")
    else:
        print(" [PASS] 모든 기준을 채웠습니다.")
    print(line)


# --------------------------------------------------------------------------
# 계약에서 숫자 꺼내기
# --------------------------------------------------------------------------


def rule(node, *path, **kw):
    """계약 안쪽 값을 안전하게 꺼낸다. 없으면 default.

    검사기가 숫자를 직접 갖지 않기 위한 통로다.
    default 는 '계약이 아직 이 칸을 갖지 않은 옛 명세'를 위한 것일 뿐,
    정상적인 명세에서는 언제나 계약의 값이 쓰인다.
    """
    default = kw.get("default")
    cur = node
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return default if cur is None else cur


# --------------------------------------------------------------------------
# 글 검사 도우미 — 짧은 글·복제된 글을 기계가 알아채는 법
# --------------------------------------------------------------------------

_DROP_RE = re.compile(r"[0-9\W_]+", re.UNICODE)


def norm_text(text):
    """번호와 기호를 지우고 공백을 눌러 붙인다.

    '밴쿠버 참고 메모 1: …' 과 '밴쿠버 참고 메모 2: …' 를 같은 문장으로 보기 위해서다.
    숫자만 바꿔 복사한 줄은 이 정규화를 거치면 완전히 같아진다.
    """
    return _DROP_RE.sub("", (text or "")).strip()


def unique_ratio(lines):
    """정규화한 뒤 서로 다른 줄의 비율. 1.0 이면 전부 다른 줄이다."""
    normed = [norm_text(line) for line in lines if (line or "").strip()]
    normed = [n for n in normed if n]
    if not normed:
        return 0.0
    return len(set(normed)) / len(normed)


def duplicate_lines(lines):
    """두 번 이상 나온 줄을 (대표 원문, 횟수)로 돌려준다."""
    seen = {}
    for line in lines:
        key = norm_text(line)
        if not key:
            continue
        seen.setdefault(key, [0, line.strip()])
        seen[key][0] += 1
    return [(v[1], v[0]) for v in seen.values() if v[0] > 1]


def similarity(left, right, size=8):
    """두 글이 얼마나 겹치는가 (0.0 ~ 1.0). 글자 묶음의 자카드 유사도.

    '도시 이름만 바꾼 같은 글' 을 잡기 위한 검사다.
    """
    a = norm_text(left)
    b = norm_text(right)
    if not a or not b:
        return 0.0
    if len(a) < size or len(b) < size:
        return 1.0 if a == b else 0.0
    sa = {a[i:i + size] for i in range(len(a) - size + 1)}
    sb = {b[i:i + size] for i in range(len(b) - size + 1)}
    union = sa | sb
    if not union:
        return 0.0
    return len(sa & sb) / len(union)


# --------------------------------------------------------------------------
# 시간 검사 — 일정 블록이 HH:MM 으로 이어지는가
# --------------------------------------------------------------------------

TIME_RE = re.compile(r"^([01][0-9]|2[0-3]):([0-5][0-9])$")
TIME_RANGE_RE = re.compile(r"([01][0-9]|2[0-3]):([0-5][0-9])\s*[-~–]\s*([01][0-9]|2[0-3]):([0-5][0-9])")


def is_time(value):
    return bool(TIME_RE.match((value or "").strip()))


def to_minutes(value):
    match = TIME_RE.match((value or "").strip())
    if not match:
        return None
    return int(match.group(1)) * 60 + int(match.group(2))


# --------------------------------------------------------------------------
# 자산 검사 — 주소가 '있는가' 가 아니라 '살아 있는가'
# --------------------------------------------------------------------------


def asset_problems(asset, asset_rule):
    """이미지 한 장이 계약을 만족하는지 본다. 문제 목록을 돌려준다.

    검사기는 네트워크를 타지 않는다. 대신 '네트워크를 탔다는 기록'을 본다.
    그래야 판정이 빠르고, 인터넷이 없는 곳에서도 같은 결과가 나온다.
    """
    problems = []
    if not isinstance(asset, dict):
        return ["이미지 칸이 없습니다"]

    url = (asset.get("url") or "").strip()
    alt = (asset.get("alt") or "").strip()
    if not url:
        problems.append("url 이 없습니다")
    if not alt:
        problems.append("alt 가 없습니다")
    if url and not url.startswith(("http://", "https://")):
        problems.append("url 이 http(s) 로 시작하지 않습니다")

    for banned in (asset_rule.get("banned_url_substrings") or []):
        if banned and banned in url:
            problems.append(
                "손으로 만들 수 없는 주소 형태입니다 (" + banned + "). 권장 형태: "
                + str(asset_rule.get("recommended_form", ""))
            )
            break

    if asset_rule.get("require_verified"):
        verified = asset.get("verified")
        if not isinstance(verified, dict):
            problems.append("verified 기록이 없습니다 (수집할 때 실제로 열어 보고 적습니다)")
        else:
            problems.extend(_verified_problems(verified, asset_rule))
    return problems


def _verified_problems(verified, asset_rule):
    """`verified` 기록 하나를 읽어 문제 목록을 만든다. **첫 줄에 원인을 놓는다.**

    ★ 왜 순서가 중요한가. 이 목록을 쓰는 쪽(`check_information_count.py`)이
      `problems[:2]` 로 **앞의 두 줄만** 못 채운 칸에 적는다. 그 두 줄이 그대로
      사람의 게이트 화면에 뜨고, 재수집 프롬프트로도 들어간다. 그러니 앞자리에
      무엇을 놓느냐가 **루프가 수렴하는지 아닌지**를 정한다.

      실측으로 겪은 실패가 이것이다. 이미지 주소가 안 열려 `status: 0` 이 됐는데,
      `0 or ""` 가 빈 문자열이 되는 바람에 앞의 두 줄이

          verified.status 이 비어 있습니다
          verified.content_type 이 비어 있습니다

      로 채워졌다. 정작 원인을 말하는 `verified.status 가 0 입니다` 는 세 번째라
      잘려 나갔다. 사람은 "수집을 안 했나 보다"로 읽고, 모델은 아무 행동도 지시받지
      못한 채 **같은 주소를 다시 만들었다.** 못 채운 칸이 줄지 않았다.

      그래서 **열어 봤는데 실패한 것**과 **아예 안 모은 것**을 갈라, 전자는 원인
      한 줄로 먼저 보고한다. (status 가 허용값 밖일 때) 판정 자체는 달라지지 않는다 — 어느 쪽이든 부족이다.
    """
    problems = []
    allowed = asset_rule.get("allowed_status") or [200]
    status = verified.get("status")
    error = str(verified.get("error") or "").strip()

    #  (1) 열어 봤고 실패했다 -> 원인 한 줄. 이것이 problems[0] 이어야 한다.
    if error or (status is not None and status not in allowed):
        problems.append("이미지 주소가 열리지 않았습니다 — "
                        + (error or "status " + str(status))
                        + " (허용: " + str(allowed) + ")")
        return problems

    #  (2) 그 밖에는 '안 모은 칸'을 본다.
    #      ★ `or ""` 를 쓰지 않는다. 정수 0 이나 False 가 빈 값으로 둔갑한다.
    for field in (asset_rule.get("verified_fields") or []):
        value = verified.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            problems.append("verified." + field + " 이 비어 있습니다")
    if status not in allowed:
        problems.append("verified.status 가 " + str(status)
                        + " 입니다 (허용: " + str(allowed) + ")")
    prefix = asset_rule.get("content_type_prefix")
    ctype = str(verified.get("content_type") or "")
    if prefix and not ctype.startswith(prefix):
        problems.append("verified.content_type 이 " + (ctype or "없음")
                        + " 입니다 (" + prefix + "… 이어야 합니다)")
    return problems


def sha256_file(path):
    import hashlib
    path = Path(path)
    if not path.exists():
        return None
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
