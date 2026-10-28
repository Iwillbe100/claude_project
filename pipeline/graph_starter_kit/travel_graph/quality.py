"""루프 C(정성 완성도) 한 회차의 실제 작업. **킷 소유 — 수정 금지.**

`nodes.py` 를 얇게 두기 위해 "어떻게 정성을 점검하는가"를 전부 여기에 가둔다.
`research.py`(어떻게 모으는가) · `page.py`(어떻게 그리는가) 와 같은 자리다.

    루프 A·B    검사기가 통과할 때까지 돈다        →  **통과선 루프**
    루프 C      정해진 3회를 채울 때까지 돈다      →  **고정 예산 루프**

품질에 점수를 매기면 글을 쓴 쪽이 자기 글에 점수를 준다(판정 독립 붕괴). 그래서
`check_quality_passes.py` 는 **품질이 아니라 절차**를 본다. 이 모듈은 그 절차가
정직하게 남도록 한 회차를 원자적으로 처리한다.

    1  회차 시작 전 파일 해시를 찍는다            snapshot_before
    2  규율 10개를 전부 판정한다 (claude -p)      이번 회차의 렌즈부터 고친다
    3  위반이라 적은 것을 **하나씩** 고친다        output/** 만 손댄다
       한 건 넣을 때마다 `verify_all.py --skip-quality`
       exit 0 이 아니면 **그 한 건만** 되돌린다   나머지 멀쩡한 수정은 남는다
    4  회차 끝 파일 해시를 찍는다                  snapshot_after
    5  회차 끝에 한 번 더 재검증한다                기록의 verify_after 에 남는다
    6  passN.json 을 쓴다                          진실은 디스크에 있다

한 회차의 수정을 통째로 묶어 검증하면 하나가 계약을 깨뜨렸을 때 나머지까지 날아간다.
실제로 그렇게 됐다 — 세 건 중 하나 때문에 셋 다 되돌아갔고, 판정기는
"위반이라 적고 고치지 않았습니다"라고만 말했다. 그래서 한 건씩 검증한다.

**병렬로 돌리지 마십시오.** 회차 N 의 `snapshot_before` 는 회차 N-1 의
`snapshot_after` 와 같아야 하고 판정기가 그 사슬을 확인한다. 세 회차는 서로의
결과 위에 쌓이므로 `build_page` 와는 **다른 이유로** 순차여야 한다 —
`build_page` 는 입력이 다 모여야 해서, `quality_pass` 는 **자기 앞 회차의 출력이
자기 입력이라서**다.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from travel_graph import contract, page, research

# --------------------------------------------------------------------------- #
# 계약에서 읽는다. 이 모듈은 숫자를 스스로 갖지 않는다.
# --------------------------------------------------------------------------- #


class QualityBlocked(RuntimeError):
    """정성 판정을 할 수 없다. **조용히 통과시키지 않고** 그래프를 멈춘다."""


def rules() -> dict:
    return contract.contract().get("quality_contract") or {}


def passes_required() -> int:
    return int(rules().get("passes") or 3)


def watch_files() -> list[str]:
    return list(rules().get("watch_files") or [])


def focus_for(number: int) -> list[str]:
    return list((rules().get("pass_focus") or {}).get(str(number)) or [])


def rubric_text() -> str:
    path = contract.ROOT / (rules().get("rubric_file") or "specs/QUALITY_RUBRIC.md")
    return path.read_text(encoding="utf-8") if path.exists() else ""


# --------------------------------------------------------------------------- #
# 해시 · 기록 위치
# --------------------------------------------------------------------------- #


def sha256_file(rel: str):
    path = contract.ROOT / rel
    if not path.exists():
        return None
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot() -> dict:
    return {name: sha256_file(name) for name in watch_files()}


RUNS = contract.ROOT / "evidence" / "runs"


def run_dir(new: bool = False) -> Path:
    """회차 기록을 남길 폴더.

    `check_quality_passes.py` 는 `evidence/runs/` 의 **가장 마지막 폴더**를 본다.
    그래서 1회차에서만 새로 만들고, 2·3회차는 그것을 그대로 쓴다.
    """
    RUNS.mkdir(parents=True, exist_ok=True)
    existing = sorted(p for p in RUNS.iterdir() if p.is_dir())
    if new or not existing:
        stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        target = RUNS / stamp
        target.mkdir(parents=True, exist_ok=True)
        return target
    return existing[-1]


def quality_dir(new: bool = False) -> Path:
    folder = run_dir(new) / "quality"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


# --------------------------------------------------------------------------- #
# 판정 — claude -p 가 규율 10개를 본다
# --------------------------------------------------------------------------- #

_PATH_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)|\[(\d+)\]")


def _resolve(root, dotted):
    """`cities[0].spots[1].detail` 같은 경로에서 (부모, 키)를 찾는다.

    LLM 이 준 경로를 **그대로 믿지 않는다.** 실제로 있는 자리인지 걸어 보고,
    없으면 고치지 않은 것으로 남긴다.

    딱 한 가지 예외가 **리스트 끝에 붙이기**다. `items[2]` 처럼 지금 길이와 같은
    번호를 주면 새 항목을 하나 추가한다. 근거를 더하거나 일정 블록을 늘리는
    수정이 이 형태라서, 막아 두면 정성 루프가 할 수 있는 일이 글 다듬기뿐이 된다.
    **딕셔너리에 새 키를 만드는 것은 허용하지 않는다** — 화면에 그려지지 않는
    칸을 늘려 봐야 "고친 척"만 된다.
    """
    steps = []
    for name, index in _PATH_RE.findall(dotted or ""):
        steps.append(name if name else int(index))
    if not steps:
        return None, None
    node = root
    for step in steps[:-1]:
        try:
            node = node[step]
        except (KeyError, IndexError, TypeError):
            return None, None
    last = steps[-1]
    try:
        node[last]
        return node, last
    except IndexError:
        if isinstance(node, list) and isinstance(last, int) and last == len(node):
            node.append(None)                      # 끝에 한 칸만 만든다
            return node, last
        return None, None
    except (KeyError, TypeError):
        return None, None


#: 판정값은 두 가지뿐이다. 판정기가 그 둘만 인정한다.
_VERDICTS = ("OK", "VIOLATION")
_VIOLATION_WORDS = ("VIOLAT", "위반", "미흡", "부족", "결함", "문제")
_OK_WORDS = ("OK", "PASS", "이상 없음", "이상없음", "없음", "준수", "적합", "양호")


def normalize_verdict(raw) -> tuple[str, str]:
    """판정값을 `OK` / `VIOLATION` 둘 중 하나로 접고, 원래 값을 함께 돌려준다.

    실제로 겪은 일이다 — 판정자가 `"위반"` · `"위반→수정함"` · `"위반(미해결, 이월)"`
    처럼 제 나름의 말을 쓴다. 그대로 두면 판정기가 "판정값이 어긋남" 으로 SHORT 를 낸다.

    **모르는 값은 `VIOLATION` 쪽으로 접는다.** 반대로 접으면 지적을 조용히 지우게 된다.
    원래 값은 버리지 않고 `note` 앞에 남긴다.
    """
    text = str(raw or "").strip()
    if not text:
        return "VIOLATION", "(판정값이 비어 있음)"
    upper = text.upper()
    if upper in _VERDICTS:
        return upper, ""
    if any(word in upper or word in text for word in _VIOLATION_WORDS):
        return "VIOLATION", text
    if any(word in upper or word in text for word in _OK_WORDS):
        return "OK", text
    return "VIOLATION", text


def judge(number: int, focus: list[str]) -> dict:
    """규율 10개를 전부 판정하고, 고칠 것을 경로와 새 값으로 받아 온다.

    **판정만 시킨다.** 파일을 직접 고치게 하지 않는다(`--disallowed-tools` 에 Edit).
    고치는 일은 아래 `apply_fixes` 가 결정론 코드로 한다. 그래야 무엇이 어떻게
    바뀌었는지 기록이 정확해진다.
    """
    counts = contract.counts()
    chars = counts.get("min_chars") or {}
    dedup = counts.get("dedup") or {}
    itinerary = counts.get("itinerary") or {}
    all_rules = ", ".join(rules().get("rules") or [])
    prompt = (
        f"당신은 여행 정보 결과물의 **정성 점검자**입니다. {number}회차입니다.\n\n"
        f"[읽을 파일]\n"
        f"- output/research_data.json  (수집 결과. 화면은 여기서 생성됩니다)\n"
        f"- output/travel_site.html    (생성된 화면)\n"
        f"- graph/02_USER_REQUEST.md  (취향 원문 — Q-취향연결 · Q-동행반영 판정 기준)\n"
        f"- {rules().get('rubric_file')}  (규율 10가지 전문)\n\n"
        f"[규율 10가지]\n{all_rules}\n\n"
        f"[이번 회차의 렌즈] {', '.join(focus)}\n"
        f"  10가지를 **전부** 판정하되, 고치는 것은 이 렌즈에 해당하는 항목부터 합니다.\n\n"
        f"[규율 전문]\n{rubric_text()[:4000]}\n\n"
        f"[★ 이 결과물의 성격 — 잘못 읽기 쉬운 부분]\n"
        f"- 도시 {len(contract.baseline().get('cities') or [])}개의 일정은 **서로 독립적인 "
        f"{itinerary.get('days_per_city')}일 계획**입니다. 도시를 이어 붙인 하나의 여정이 아닙니다.\n"
        f"  이 페이지는 '며칠을 어떻게 돌까'가 아니라 **'어느 도시로 가면 좋을까'** 를 돕습니다.\n"
        f"  그러므로 A도시 5일차와 B도시 1일차의 시각을 비교해 모순이라고 적지 마십시오.\n\n"
        f"[★ 판정값은 정확히 두 가지뿐입니다]\n"
        f'  "OK"  또는  "VIOLATION"  — 다른 말을 쓰지 마십시오.\n'
        f'  ("위반", "위반→수정함", "부분 충족" 같은 값은 판정기가 받지 않습니다)\n\n'
        f"[고칠 때 지켜야 할 계약 — 어기면 그 수정은 자동으로 되돌려집니다]\n"
        f"- 근거 1건 {chars.get('evidence_item')}자 이상 · 관광지 상세 {chars.get('spot_detail')}자 이상\n"
        f"- 도시 선정 이유 {chars.get('why_selected')}자 이상 · 취향 설명 줄마다 "
        f"{chars.get('preference_note_line')}자 이상\n"
        f"- 일정 블록의 why 는 {chars.get('itinerary_block_why')}자 이상\n"
        f"- **같은 문장을 여러 칸에 복사하지 마십시오.** 고유 줄 "
        f"{int(float(dedup.get('min_unique_line_ratio') or 0.9) * 100)}% · 두 글 사이 유사도 "
        f"{int(float(dedup.get('max_pair_similarity') or 0.6) * 100)}% 를 넘으면 걸립니다.\n"
        f"  실용 정보를 여러 관광지에 넣을 때는 **관광지마다 다른 문장**으로 쓰십시오.\n"
        f"- 하루는 {itinerary.get('blocks_per_day_min')}블록 이상, 시각은 HH:MM, 서로 겹치지 않게,\n"
        f"  '명소' 블록이 {itinerary.get('spot_blocks_per_day_min')}개 이상이고 그 관광지는 "
        f"그 도시에서 조사한 것이어야 합니다.\n"
        f"- 도시마다 {itinerary.get('days_per_city')}일이 다 있어야 합니다. 날을 지우지 마십시오.\n\n"
        f"[고칠 수 있는 자리]\n"
        f"- `output/research_data.json` **안쪽뿐**입니다. HTML 은 여기서 자동 생성됩니다.\n"
        f"- 기존 값 바꾸기:  `cities[0].spots[1].detail`\n"
        f"- **리스트 끝에 추가하기**: 지금 길이와 같은 번호를 쓰면 새 항목이 붙습니다.\n"
        f"  예) `items` 가 2개이면 `cities[0].spots[1].items[2]` 로 근거 1건을 더합니다.\n"
        f"- 딕셔너리에 없던 키를 만드는 것은 되지 않습니다 (화면에 안 그려집니다).\n\n"
        f"[그 밖에]\n"
        f"- 계약을 낮추지 마십시오. 정성 점검은 결과물을 고치는 일이지 기준을 고치는 일이 아닙니다.\n"
        f"- 위반이라 적었으면 같은 회차에서 적용 가능한 fix 를 반드시 함께 내십시오.\n"
        f"- 고칠 것이 없으면 verdict 를 OK 로 적고 fixes 를 비우십시오. 지어내지 마십시오.\n"
        f"- 각 fix 는 **하나씩 따로 검증**됩니다. 계약을 깨뜨린 것만 되돌아가고 나머지는 남습니다.\n\n"
        "마지막에 아래 형식의 ```json 블록 하나만 출력하십시오.\n"
        '```json\n'
        '{"rules": [{"id": "Q-반복금지", "verdict": "OK", "where": "-", "note": "..."}],\n'
        ' "fixes": [{"rule": "Q-반복금지", "path": "cities[0].spots[1].detail",\n'
        '            "value": "고쳐 넣을 전체 값(문자열/객체/리스트)", "what": "무엇을 왜 바꿨는지"}]}\n'
        '```'
    )
    try:
        #  ★ 상한은 **실측으로 정한 값**이다. 예전 값 14 는 여유가 0이었다.
        #
        #      판정 1회가 실제로 쓰는 턴   14 ~ 16   (같은 입력에서도 흔들린다)
        #      예전 상한                  14        <- 붙어 있었다
        #      지금 상한                  24        <- 실측 최대의 1.5배
        #
        #    87KB JSON 과 92KB HTML 을 나눠 읽으니 두 자릿수 턴은 정상 소모다.
        #    판정자가 파일을 몇 조각으로 읽고 Grep 을 몇 번 쓰느냐에 따라 회차마다
        #    달라지므로, **특정 회차가 위험한 것이 아니라 어느 회차든 걸릴 수 있다.**
        #    실제로 한 실행은 3회 내내 수정을 0건 적용했는데도(=파일이 전혀 안 바뀜)
        #    세 번 다 통과했고, 다른 실행은 3회차에서 `error_max_turns` 로 죽었다.
        #    "회차가 쌓여서"가 아니라 **상한에 붙어 있었기 때문**이다.
        #
        #    루프 C 는 폴백이 없어서 여기서 죽으면 그 회차가 통째로 ERROR 가 된다.
        #    그렇다고 무한정 올리지는 않는다. 이 상한은 **폭주를 잡는 장치**다.
        data = research._claude_json(prompt, tools=["Read", "Grep", "Glob"], max_turns=24,
                                     label=f"정성 판정 {number}/{len(rules().get('pass_focus') or {}) or 3}회차")
    except research.ClaudeUnavailable as exc:
        raise QualityBlocked(
            f"정성 판정을 수행할 수 없습니다: {exc}. "
            "루프 C 는 규율 판정을 요구하므로 이 회차를 통과시키지 않습니다"
        )
    if not isinstance(data.get("rules"), list):
        raise QualityBlocked("정성 판정 응답에 rules 배열이 없습니다")
    return data


# --------------------------------------------------------------------------- #
# 적용 — 결정론 코드가 한다
# --------------------------------------------------------------------------- #


#: 고칠 수 있는 값의 종류. 글만이 아니라 **구조**도 고칠 수 있어야 한다 —
#: `Q-일정현실성` 은 하루의 블록 목록을 통째로 다시 짜야 하는 경우가 많다.
#: 잘못 고치면 `verify_all --skip-quality` 가 걸러 내고 그 한 건만 되돌린다 (회차 끝 재검증이 실패하면 회차 전체).
FIXABLE = (str, int, float, list, dict)


# --------------------------------------------------------------------------- #
# 자산 재검증 — 고친 주소를 **다시 열어 본다**
# --------------------------------------------------------------------------- #


def _asset_slots(data):
    """자산이 있어야 할 자리를 `(식별자, 부모, 키)` 로 훑는다.

    규격은 `scripts/check_information_count.py` 의 `asset_at` 과 같다 —
    국가 소개는 `{"asset": …}` 로 한 겹 싸고, 관광지는 `image` 칸 자체가 자산이다.
    두 곳이 어긋나면 여기서 고친 것을 검사기가 못 보므로 규격을 같이 둔다.
    """
    intro = data.get("country_intro")
    if isinstance(intro, dict):
        for name, slot in intro.items():
            if isinstance(slot, dict) and isinstance(slot.get("asset"), dict):
                yield ("intro", name), slot, "asset"
    for city_index, city in enumerate(data.get("cities") or []):
        if not isinstance(city, dict):
            continue
        for spot_index, spot in enumerate(city.get("spots") or []):
            if isinstance(spot, dict) and isinstance(spot.get("image"), dict):
                yield ("city", city_index, spot_index), spot, "image"


def _asset_urls(data) -> dict:
    """지금 데이터의 자산 주소를 자리별로 찍어 둔다 (수정 전후 비교용)."""
    return {slot_id: (parent[key].get("url") or "").strip()
            for slot_id, parent, key in _asset_slots(data)}


def reverify_changed_assets(data, before_urls) -> list:
    """주소가 바뀐 자산만 **다시 열어 보고** 기록을 새로 쓴다. 바뀐 주소를 돌려준다.

    ★ 왜 필요한가. `verified` 는 **수집하는 쪽이 실제로 열어 보고 적는 기록**이고
      (`research.verify_asset`), 검사기는 네트워크를 타지 않고 그 기록만 본다.
      그런데 `rebuilder` 는 사람의 지시로 주소를 바꿀 수 있고 웹을 검색하지는 못한다.
      바꾼 주소에 옛 기록이 그대로 남으면 **죽은 주소가 옛 `status: 200` 으로 루프 A 를
      통과한다.** 그 칸은 부족으로 잡히지 않으므로 루프가 다시 보지 않는다 —
      화면에는 깨진 이미지가 남는데 판정은 PASS 인, 가장 찾기 어려운 실패다.

    ★ 다시 열어 보면 죽은 주소는 그 자리에서 `status` 가 200 이 아니게 되고, 루프 A 가
      부족으로 잡아 그 도시를 재수집으로 돌려보낸다. **루프가 스스로 닫히는 자리다.**
      멀쩡한 주소면 새 기록으로 그대로 통과하므로 한 바퀴를 아낀다.

    ★ 주소가 그대로인 자산은 건드리지 않는다. 회차마다 전부 다시 여는 것은 느리고,
      바뀌지 않은 기록을 다시 쓸 이유도 없다.
    """
    changed = []
    todo = [(slot_id, parent, key) for slot_id, parent, key in _asset_slots(data)
            if (parent[key].get("url") or "").strip()
            and before_urls.get(slot_id) != (parent[key].get("url") or "").strip()]
    for number, (slot_id, parent, key) in enumerate(todo, 1):
        url = (parent[key].get("url") or "").strip()
        #  ★ 한 건에 최대 20초가 걸린다 (`research.verify_asset` 의 timeout).
        #    한 번의 수정이 자산 여러 개의 주소를 바꾸면 몇 분이 조용히 흐르고,
        #    `langgraph dev` 화면에서는 그것이 **멈춤처럼 보인다.** 그래서 센다.
        print(f"[quality] 바뀐 주소 재검증 {number}/{len(todo)} — {url[:78]}")
        parent[key] = research.verify_asset(parent[key])
        changed.append(url)
    return changed


def apply_fixes(fix_list) -> tuple[list[dict], list[dict]]:
    """판정자가 지목한 자리에 새 값을 넣고 HTML 을 다시 만든다.

    **fix 를 하나씩 넣고 그때마다 되돌아감을 확인한다.** 한 회차의 수정을 통째로
    묶어서 검증하면, 하나가 계약을 깨뜨렸을 때 나머지 멀쩡한 수정까지 같이 날아간다.
    실제로 그렇게 됐다 — 세 건 중 하나 때문에 셋 다 되돌아갔다.

        넣는다  →  verify_all --skip-quality  →  exit 0 이면 남기고, 아니면 되돌린다

    `output/**` 밖으로는 한 글자도 나가지 않는다. 정성 루프가 계약이나 검사기를
    낮출 권한을 갖지 않게 하기 위해서다.

    **적용하지 못한 것을 조용히 버리지 않는다.** 버리면 판정기가
    "위반이라 적고 고치지 않았다"고만 말하고 그 이유는 아무 데도 남지 않는다.
    돌려주는 두 번째 목록이 그 이유다.
    """
    applied, skipped = [], []
    if not fix_list:
        return applied, skipped

    for fix in fix_list:
        if not isinstance(fix, dict):
            skipped.append({"rule": "", "path": "", "why": "fix 항목이 객체가 아닙니다"})
            continue
        rule = str(fix.get("rule") or "")
        dotted = str(fix.get("path") or "")
        value = fix.get("value")
        what = str(fix.get("what") or dotted)

        if not isinstance(value, FIXABLE):
            skipped.append({"rule": rule, "path": dotted, "what": what,
                            "why": f"고칠 수 없는 값 종류입니다 ({type(value).__name__})"})
            continue

        data = json.loads(contract.RESEARCH_OUT.read_text(encoding="utf-8-sig"))
        parent, key = _resolve(data, dotted)
        if parent is None or key is None:
            skipped.append({"rule": rule, "path": dotted, "what": what,
                            "why": "그 경로가 output/research_data.json 안에 없습니다 "
                                   "(리스트 끝에 붙이려면 지금 길이와 같은 번호를 쓰십시오)"})
            continue

        backup = backup_files()
        before_urls = _asset_urls(data)
        parent[key] = value
        #  ★ 주소를 바꿨으면 **다시 열어 본다.** 옛 검증 기록이 새 주소를 보증하게
        #    두면 죽은 이미지가 루프를 빠져나간다 (`reverify_changed_assets` 참고).
        rechecked = reverify_changed_assets(data, before_urls)
        contract.write_research(data)
        page.write(data)                   # 화면은 데이터에서 다시 만든다

        _command, code = regression()
        if code == 0:
            entry = {"rule": rule,
                     "file": "output/research_data.json",
                     "what": what}
            if rechecked:
                #  기록에 남긴다. 주소를 바꿨다는 사실과 그것을 다시 열어 봤다는
                #  사실이 증거에 함께 있어야 사람이 판단할 수 있다.
                entry["rechecked"] = rechecked
            applied.append(entry)
        else:
            restore(backup)
            skipped.append({"rule": rule, "path": dotted, "what": what,
                            "why": f"이 수정이 정량 계약을 깨뜨려 되돌렸습니다 "
                                   f"(재검증 exit {code})"})
    return applied, skipped


def rebuild_from_note(note: str) -> dict:
    """사람이 게이트에 적은 지시문대로 결과물을 고친다 (rebuilder 노드).

    ★ `quality_pass` 와 **같은 규격**이다. 판정만 LLM 이 하고 적용은 `apply_fixes` 가
      결정론으로 한다. fix 하나를 넣을 때마다 `verify_all --skip-quality` 로 되돌아감을
      확인하고, 계약을 깨뜨린 것만 되돌린다.

    ★ **HTML 을 직접 고치지 않는다.** `output/research_data.json` 을 고치면
      `apply_fixes` 가 `page.write()` 로 화면을 다시 만든다. HTML 만 손대면
      `build_page` 가 다시 도는 순간 사라지기 때문이다.

    ★ 그래도 상태에는 남겨야 한다. `build_page` 는 **파일이 아니라 상태**에서
      페이지를 만들기 때문이다. 그 일은 노드(`nodes.rebuilder`)가 한다 —
      이 함수가 고친 데이터를 읽어 상태로 돌려준다.
    """
    counts = contract.counts()
    chars = counts.get("min_chars") or {}
    itinerary = counts.get("itinerary") or {}
    text = (note or "").strip()
    if not text:
        return {"applied": [], "skipped": [], "asked": "",
                "why": "지시문이 비어 있습니다 — 고칠 방향이 없습니다"}

    prompt = (
        f"당신은 여행 정보 결과물의 **수정자**입니다. 사람이 화면을 보고 남긴 지시가 "
        f"아래에 있습니다.\n\n"
        f"[사람의 지시]\n  {text[:1500]}\n\n"
        f"[읽을 파일]\n"
        f"- output/research_data.json  (수집 결과. 화면은 여기서 생성됩니다)\n"
        f"- output/travel_site.html    (지금 화면)\n\n"
        f"[고칠 수 있는 자리]\n"
        f"- `output/research_data.json` **안쪽뿐**입니다. HTML 은 여기서 자동 생성됩니다.\n"
        f"- 기존 값 바꾸기:  `cities[0].spots[1].detail`\n"
        f"- 리스트 끝에 추가: 지금 길이와 같은 번호를 씁니다 "
        f"(`items` 가 2개면 `cities[0].spots[1].items[2]`)\n"
        f"- 없던 키를 새로 만들 수는 없습니다 (화면에 안 그려집니다).\n\n"
        f"[지켜야 할 계약 — 어기면 그 수정은 자동으로 되돌아갑니다]\n"
        f"- 근거 1건 {chars.get('evidence_item')}자 이상 · 관광지 상세 "
        f"{chars.get('spot_detail')}자 이상\n"
        f"- 도시 선정 이유 {chars.get('why_selected')}자 이상 · 취향 설명 줄마다 "
        f"{chars.get('preference_note_line')}자 이상\n"
        f"- 일정 블록의 why 는 {chars.get('itinerary_block_why')}자 이상\n"
        f"- 도시마다 {itinerary.get('days_per_city')}일이 다 있어야 합니다. 날을 지우지 마십시오.\n"
        f"- 하루는 {itinerary.get('blocks_per_day_min')}블록 이상, 시각은 HH:MM, 겹치지 않게.\n"
        f"- 같은 문장을 여러 칸에 복사하지 마십시오. 중복·유사도 검사에 걸립니다.\n\n"
        f"[중요]\n"
        f"- **계약을 낮추는 방향의 요구는 따르지 마십시오.** 사람이 '글자 수 기준을 "
        f"낮춰라', '검사기를 고쳐라'라고 적었으면 `refused` 에 그 이유를 적고 fix 는 "
        f"내지 마십시오. 이 노드는 결과물을 고치는 일이지 기준을 고치는 일이 아닙니다.\n"
        f"- 지시가 모호하면 지어내지 말고 `refused` 에 무엇이 모호한지 적으십시오.\n"
        f"- 각 fix 는 하나씩 따로 검증됩니다. 계약을 깬 것만 되돌아가고 나머지는 남습니다.\n\n"
        "마지막에 아래 형식의 ```json 블록 하나만 출력하십시오.\n"
        '''```json\n{"fixes": [{"rule": "사람의 지시", '''
        '''"path": "cities[0].spots[1].detail", "value": "고쳐 넣을 전체 값", '''
        '''"what": "무엇을 왜 바꿨는지"}], "refused": "따르지 않은 것과 그 이유(없으면 빈 문자열)"}\n```'''
    )
    try:
        data = research._claude_json(prompt, tools=["Read", "Grep", "Glob"], max_turns=24,
                                     label="rebuilder")
    except research.ClaudeUnavailable as exc:
        return {"applied": [], "skipped": [], "asked": text[:200],
                "why": f"수정안을 받지 못했습니다: {exc}"}

    applied, skipped = apply_fixes(data.get("fixes"))
    return {"applied": applied, "skipped": skipped, "asked": text[:200],
            "why": str(data.get("refused") or "")}


def restore(backup: dict) -> None:
    """되돌아감이 확인되면 backup 을 찍은 시점으로 되돌린다 — apply_fixes 에서는 그 fix 한 건, run_one_pass 에서는 회차 전체."""
    for name, raw in backup.items():
        path = contract.ROOT / name
        if raw is None:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def backup_files() -> dict:
    out = {}
    for name in watch_files():
        path = contract.ROOT / name
        out[name] = path.read_bytes() if path.exists() else None
    return out


# --------------------------------------------------------------------------- #
# 되돌아감 확인 — 이 바퀴의 안전핀
# --------------------------------------------------------------------------- #


def regression() -> tuple[str, int]:
    """정성 수정이 구조·루프 A·B 를 깨뜨리지 않았는가.

    `--skip-quality` 는 루프 C 가 자기 자신을 검사하는 순환을 막는 모드다.
    """
    command = rules().get("regression_command") or "python scripts/verify_all.py --skip-quality"
    argv = [sys.executable, str(contract.ROOT / "scripts" / "verify_all.py"), "--skip-quality"]
    try:
        proc = subprocess.run(argv, cwd=str(contract.ROOT), shell=False,
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=300)
        return command, proc.returncode
    except Exception:                                   # noqa: BLE001
        return command, 1


# --------------------------------------------------------------------------- #
# 기록 — 진실은 디스크에 있다
# --------------------------------------------------------------------------- #


def write_record(number, focus, before, judged, applied, after, command, code,
                 skipped=None) -> Path:
    folder = quality_dir(new=(number == 1))
    record = {
        "pass": number,
        "focus": focus,
        "checked_at": datetime.now().replace(microsecond=0).isoformat(),
        "snapshot_before": before,
        "rules": judged,
        "applied_fix": applied,
        #: 판정기는 이 칸을 보지 않는다. **사람이 본다** — "위반이라 적고 고치지
        #: 않았습니다" 가 왜 나왔는지 여기 말고는 알 길이 없다.
        "skipped_fix": skipped or [],
        "snapshot_after": after,
        "verify_after": {"command": command, "exit_code": code},
    }
    path = folder / f"pass{number}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_readable(folder / f"pass{number}.md", record)
    return path


def _write_readable(path: Path, record: dict) -> None:
    """사람이 읽는 형태. 판정기는 이 파일을 보지 않는다."""
    lines = [
        f"# 정성 점검 {record['pass']}회차",
        "",
        f"- 렌즈: {', '.join(record['focus'])}",
        f"- 시각: {record['checked_at']}",
        f"- 되돌아감 확인: `{record['verify_after']['command']}` "
        f"→ exit {record['verify_after']['exit_code']}",
        "",
        "| 규율 | 판정 | 어디 | 메모 |",
        "| --- | --- | --- | --- |",
    ]
    for row in record["rules"]:
        lines.append("| {} | {} | {} | {} |".format(
            row.get("id", ""), row.get("verdict", ""),
            str(row.get("where", "-"))[:40], str(row.get("note", ""))[:60]))
    lines += ["", "## 실제로 고친 것", ""]
    if record["applied_fix"]:
        for fix in record["applied_fix"]:
            lines.append(f"- `{fix['rule']}` · {fix['file']} — {fix['what']}")
    else:
        lines.append("- 없음")
    if record.get("skipped_fix"):
        lines += ["", "## 고치려 했으나 적용하지 못한 것 (조용히 넘기지 않는다)", ""]
        for fix in record["skipped_fix"]:
            lines.append(f"- `{fix.get('rule')}` · `{fix.get('path')}` — {fix.get('why')}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_blocked(reason: str) -> Path:
    """판정을 못 했다는 사실을 남긴다. **통과시키지 않는다.**"""
    folder = quality_dir()
    path = folder / "blocked.json"
    path.write_text(json.dumps({
        "reason": reason,
        "checked_at": datetime.now().replace(microsecond=0).isoformat(),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def blocked_reason():
    """`check_quality` 가 본다. 있으면 판정 자체가 서지 않았다는 뜻이다."""
    RUNS.mkdir(parents=True, exist_ok=True)
    existing = sorted(p for p in RUNS.iterdir() if p.is_dir())
    if not existing:
        return None
    path = existing[-1] / "quality" / "blocked.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("reason")
    except json.JSONDecodeError:
        return "정성 점검 기록(blocked.json)이 깨졌습니다"


def clear_blocked() -> None:
    RUNS.mkdir(parents=True, exist_ok=True)
    existing = sorted(p for p in RUNS.iterdir() if p.is_dir())
    if not existing:
        return
    path = existing[-1] / "quality" / "blocked.json"
    if path.exists():
        path.unlink()


# --------------------------------------------------------------------------- #
# 한 회차 전체 — `nodes.quality_pass` 가 부르는 유일한 함수
# --------------------------------------------------------------------------- #


def _unfixed(judged: list, applied: list) -> list:
    """VIOLATION 으로 적혔는데 그 규율 이름으로 적용된 fix 가 없는 규율 id (판정기와 같은 규칙)."""
    fixed = {str(f.get("rule") or "").strip() for f in applied if isinstance(f, dict)}
    return [r["id"] for r in judged if r.get("verdict") == "VIOLATION" and r["id"] not in fixed]


def judge_followup(number: int, judged: list, unfixed: list, skipped: list) -> dict:
    """위반이라 적고 fix 가 없는 규율만 다시 묻는다. 돌려주는 모양은 `judge` 와 같다."""
    rows = [r for r in judged if r["id"] in unfixed]
    reasons = [s for s in skipped if str(s.get("rule") or "") in unfixed]
    prompt = (
        f"당신은 정성 점검자입니다. {number}회차 판정에서 아래 규율을 **VIOLATION** 으로 적었지만 "
        f"그 규율 이름으로 적용된 fix 가 없습니다. 판정기는 이것을 '위반이라 적고 고치지 않았다'로 봅니다.\n\n"
        f"[위반으로 적은 규율]\n{json.dumps(rows, ensure_ascii=False, indent=1)}\n\n"
        f"[적용하지 못한 fix 와 이유 (있다면)]\n{json.dumps(reasons, ensure_ascii=False, indent=1)}\n\n"
        f"[읽을 파일] output/research_data.json · output/travel_site.html · graph/02_USER_REQUEST.md · "
        f"{rules().get('rubric_file')}\n\n"
        "규율마다 둘 중 하나를 하십시오. 다른 규율은 다시 판정하지 마십시오.\n"
        "  1) 적용 가능한 fix 를 **그 규율 id 로** 냅니다 (계약 하한 · 중복 금지는 첫 판정 때와 같습니다).\n"
        "  2) 파일을 다시 보니 위반이 아니면 verdict 를 OK 로 바꾸고 note 에 이유를 적습니다.\n"
        "마지막에 아래 형식의 ```json 블록 하나만 출력하십시오.\n"
        '```json\n{"rules": [{"id": "Q-…", "verdict": "OK 또는 VIOLATION", "where": "…", "note": "…"}],\n'
        ' "fixes": [{"rule": "Q-…", "path": "cities[0].spots[1].detail", "value": "…", "what": "…"}]}\n```'
    )
    return research._claude_json(prompt, tools=["Read", "Grep", "Glob"], max_turns=16,
                                 label=f"정성 보완 {number}회차")


def merge_followup(judged: list, unfixed: list, extra: dict) -> tuple:
    """보완 답을 합친다. 돌려주는 것: (고친 판정 목록, 적용할 fix 목록).

    ★ 다시 보니 위반이 아니라고 한 규율만 OK 로 바꾸고, 처음 판정을 note 에 남긴다 — 판정을
      조용히 지우지 않는다. fix 는 **보완을 요청한 규율 이름으로 온 것만** 받는다.
    """
    judged = [dict(r) for r in judged]
    for row in (extra or {}).get("rules") or []:
        if not isinstance(row, dict) or str(row.get("id") or "") not in unfixed:
            continue
        folded, raw = normalize_verdict(row.get("verdict"))
        if folded != "OK":
            continue
        for r in judged:
            if r["id"] == row.get("id"):
                r["note"] = (f"[같은 회차 보완 — 다시 보니 위반 아님: {str(row.get('note') or '')}] "
                             f"처음 판정(VIOLATION · {r.get('where')}): {r.get('note')}")
                r["verdict"] = "OK"
    fixes = [f for f in (extra or {}).get("fixes") or []
             if isinstance(f, dict) and str(f.get("rule") or "") in unfixed]
    return judged, fixes


def run_one_pass(number: int) -> dict:
    """정성 점검 한 회차. **원자적으로** 끝난다.

    파일 쓰기를 끝낸 뒤에 돌려준다. `check_quality` 는 상태가 아니라 디스크를
    읽으므로, 여기서 반쯤 끝내고 나가면 "마지막 회차 = 지금 파일" 검사가 어긋난다.
    """
    focus = focus_for(number)
    before = snapshot()
    backup = backup_files()

    verdict = judge(number, focus)                     # 못 하면 QualityBlocked

    #  판정값을 두 가지로 접는다. 원래 표현은 버리지 않고 note 앞에 남긴다.
    judged = []
    for row in verdict.get("rules") or []:
        if not isinstance(row, dict):
            continue
        folded, raw = normalize_verdict(row.get("verdict"))
        note = str(row.get("note") or "")
        judged.append({
            "id": str(row.get("id") or ""),
            "verdict": folded,
            "where": str(row.get("where") or "-"),
            "note": (f"[판정자가 쓴 값: {raw}] " + note) if raw else note,
        })

    applied, skipped = apply_fixes(verdict.get("fixes"))

    #  ★ **위반이라 적고 fix 가 없으면 같은 회차 안에서 한 번 더 묻는다.** 판정자가 규율을
    #    VIOLATION 으로 적고 그 규율 이름의 fix 를 내지 않는 일이 실제로 있다 (live 리허설:
    #    1회차 Q-근거일치 · 2회차 Q-실용누락 — 고친 내용이 다른 규율 이름으로만 적혔다).
    #    판정기는 그것을 "위반이라 적고 고치지 않았습니다" 로 SHORT 를 내고, 정성 3회가
    #    끝나도 verify_all 이 SHORT 로 남는다. 루프 킷에서는 Claude 가 규율대로 스스로
    #    보완하지만(QUALITY_RUBRIC — 같은 회차에서 다시 고친다), 이 노드는 판정과 적용이
    #    나뉘어 있으므로 보완 질문을 코드가 한 번 던진다. 한 번뿐이다 — 폭주를 막는다.
    unfixed = _unfixed(judged, applied)
    if unfixed:
        try:
            extra = judge_followup(number, judged, unfixed, skipped)
        except research.ClaudeUnavailable:
            extra = {}
        judged, fixes = merge_followup(judged, unfixed, extra)
        more_applied, more_skipped = apply_fixes(fixes)
        applied += more_applied
        skipped += more_skipped

    command, code = regression()
    if code != 0:
        #  fix 를 하나씩 검증했으므로 여기까지 오면 보통 0 이다. 그래도 0 이 아니면
        #  이 회차 밖에서 무언가 바뀐 것이므로 회차 시작 상태로 되돌린다.
        restore(backup)
        skipped += [dict(f, why="회차 끝 재검증이 실패해 이 회차를 통째로 되돌렸습니다")
                    for f in applied]
        applied = []
        command, code = regression()

    after = snapshot()
    path = write_record(number, focus, before, judged, applied, after, command, code, skipped)
    clear_blocked()

    violations = [r.get("id") for r in judged if r.get("verdict") == "VIOLATION"]
    unfixed = [v for v in violations if v not in {f["rule"] for f in applied}]
    return {
        "pass": number,
        "record": str(path.relative_to(contract.ROOT)).replace("\\", "/"),
        "violations": violations,
        "applied": applied,
        "skipped": skipped,
        "unfixed": unfixed,
        "exit_code": code,
    }


__all__ = [
    "QualityBlocked", "run_one_pass", "passes_required", "focus_for",
    "blocked_reason", "write_blocked", "run_dir", "normalize_verdict",
]
