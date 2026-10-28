#!/usr/bin/env python3
"""실패 기록을 읽어 **무엇이 터졌고, 무엇이 새 처방 가지 후보인지** 보여 준다. **킷 소유.**

    python scripts/failure_report.py                    가장 최근 실행 하나
    python scripts/failure_report.py --all              이 킷의 실행 전부
    python scripts/failure_report.py <파일|폴더> …       강사 — 여러 교육생의 기록을 모아서
    python scripts/failure_report.py --json

기록은 진단 · 시험 노드가 `evidence/failures/<thread_id>.jsonl` 에 남긴다. 이 보고서는
네 가지를 보여 준다.

    ①   실행별 요약              진단 몇 번 · 어떤 처방 가지를 탔고 합격했나
    ②   처방 가지가 맡은 실패     등록된 가지가 몇 번 켜졌고 몇 번 고쳤나
    ③   아직 처방 가지가 없는 실패   원인 규칙표에 없는 부족('그 밖') · 수집 실패 · 가지가 못 맡은 증상
    ③-2 재수집(LLM)이 반복해서 맡은 원인   가지 없이 SHORT 로 남아 재수집 · 재생성으로 간 원인.
                                 **같은 원인이 여러 바퀴 · 여러 실행에 되풀이되면** 처방 가지 후보다
                                 ← ③ · ③-2 의 **후보**가 STEP 6 의 재료. 후보가 없으면 STEP 6 은 하지 않는다

    한 번은 일화, 세 번은 패턴.   두 칸 다 같은 등급을 쓴다 —
                                  [일화]  (③-2 는 [한 번 — 재수집이 맡으면 된다])   한 번 나왔다 → STEP 6 아님
                                  [후보]   되풀이됐다 — ③ 은 같은 줄 2번 이상 또는 2실행 이상,
                                           ③-2 는 한 실행에서 2바퀴 이상 또는 2실행 이상  → STEP 6 (내 킷)
                                  [패턴 — 킷 처방 가지 후보]   서로 다른 실행 3곳 이상  → 킷에 넣을 후보
                                  (과적합을 막는다). 교육생의 가지는 본인 킷에만 둔다.

★ 왜 ③-2 가 따로 있나. 원인 규칙표 끝의 포괄 규칙(`목표` → "개수가 모자람")에 걸린 부족은
  '그 밖'이 아니라서 ③ 에 절대 안 뜬다. 그런데 그 부족이 재수집(LLM)을 몇 바퀴 돌아도
  남는다면 — 토큰을 쓰고 매번 다른 결과를 내며 같은 실패를 되풀이한다면 — 그것이 바로
  규칙으로 뺄 후보다. 진단 기록의 `causes` · `loop_iter` 로 센다.
★ 재현(inject) 실행은 ③ · ③-2 에서 세지 않는다. 일부러 다시 일으킨 실패는 로그에 "남은" 실패가
  아니다 — STEP 6 의 빨간불 확인 실행이 제 가지를 후보로 올리는 일도 막는다. ① · ② 에는 그대로 뜬다.
★ replay 실행은 ③-2 에서 세지 않는다. replay 의 재수집은 LLM 이 아니라 인계본을 잘라 쓰므로
  "1바퀴 부족 → 2바퀴 PASS" 가 늘 같다 — 여러 번 돌리면 가짜 패턴이 된다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from _contract import use_utf8_output  # noqa: E402

use_utf8_output()

#: 그래프가 쓰는 자리와 같다 (`travel_graph/detours/log.py` 의 `folder()` 와 같은 규칙).
DEFAULT_DIR = (Path(os.environ["GRAPH_FAILURE_LOG_DIR"])
               if os.environ.get("GRAPH_FAILURE_LOG_DIR", "").strip()
               else ROOT / "evidence" / "failures")
LINE = "=" * 70
PATTERN_RUNS = 3
#: ③ 후보 기준 — 같은 줄이 이만큼 나왔거나(여러 바퀴 · 여러 진단), 이만큼의 실행에 나왔다.
REPEAT_COUNT = 2
#: ③-2 후보 기준 — 한 실행에서 이만큼 **서로 다른 바퀴**에 남았거나, 이만큼의 실행에 나왔다.
REPEAT_ROUNDS = 2
REPEAT_RUNS = 2
#: ③-2 에서 빼는 원인. '그 밖'은 ③ 이 이미 줄마다 보여 준다.
_NOT_REPEAT = ("그 밖",)
#: 루프마다 SHORT 를 맡는 쪽 — 보고서 머리표.
_WHO = {"A": "재수집(LLM)", "B": "재생성 · rebuilder(LLM)"}


def files_from(targets, all_runs: bool) -> list:
    """`[(파일, 실행 이름)]`. 강사가 모은 폴더면 **폴더 안 상대 경로**를 이름으로 쓴다 —
    교육생 폴더 이름(`student01/run-…`)이 남아야 "서로 다른 실행"을 셀 수 있다."""
    if targets:
        out = []
        for raw in targets:
            path = Path(raw)
            if path.is_dir():
                out += [(f, f.relative_to(path).with_suffix("").as_posix())
                        for f in sorted(path.rglob("*.jsonl"))]
            elif path.exists():
                out.append((path, path.stem))
        return out
    found = sorted(DEFAULT_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    return [(f, f.stem) for f in (found if all_runs else found[-1:])]


def read_rows(path: Path) -> list:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def pattern_of(line: str) -> str:
    """위치(도시 · 관광지 이름)를 떼고 숫자를 # 로 — 같은 종류의 실패를 한 줄로 묶는다."""
    text = str(line)
    text = re.sub(r"^\[\w+\]\s*", "", text)                    # [kind] 머리표
    if ": " in text:
        text = text.split(": ", 1)[1]                           # "하노이/문묘 이미지: …" → "…"
    text = re.sub(r"\d+", "#", text)
    return re.sub(r"\s+", " ", text).strip()[:90]


def _places(text) -> int:
    """`"7 / 9"` → 7. 모양이 다르면 0."""
    match = re.match(r"\s*(\d+)", str(text or ""))
    return int(match.group(1)) if match else 0


def _round_of(row: dict, fallback: int) -> int:
    """진단 줄의 바퀴 번호. 옛 기록(`loop_iter` 없음)은 그 실행 안의 진단 순번으로 대신한다."""
    value = row.get("loop_iter")
    try:
        return int(value) if value is not None else fallback
    except (TypeError, ValueError):
        return fallback


def summarize(files: list) -> dict:
    runs = []
    entered, tried, fixed = defaultdict(int), defaultdict(int), defaultdict(int)
    candidates = defaultdict(lambda: {"runs": set(), "count": 0, "example": ""})
    #  ③-2 — (루프, 원인) → 실행마다 **서로 다른 바퀴** 집합 · 부족 칸 수 · 예시
    repeated = defaultdict(lambda: {"rounds": defaultdict(set), "places": 0, "example": ""})
    skipped_replay = 0
    rehearsals = []
    for path, run in files:
        rows = read_rows(path)
        rehearsal = any(r.get("inject") for r in rows)          # 재현(inject) 실행
        diagnoses = [r for r in rows if str(r.get("node", "")).startswith("diagnose_")]
        tests = [r for r in rows if str(r.get("node", "")).startswith("test_")]
        taken = [f"{r.get('failure_kind')}:{r.get('detour_verdict')}" for r in tests]
        for r in diagnoses:
            if r.get("failure_kind"):
                entered[r.get("failure_kind")] += 1            # 진단이 가지로 보낸 횟수
        for r in tests:
            tried[r.get("failure_kind")] += 1                  # fix → test 를 돈 횟수 (재시도 포함)
            if r.get("detour_verdict") == "PASS":
                fixed[r.get("failure_kind")] += 1

        def remember(line, source):
            if rehearsal:
                return                                          # 일부러 일으킨 실패 — 후보가 아니다
            key = f"{source} · {pattern_of(line)}"
            slot = candidates[key]
            slot["runs"].add(run)
            slot["count"] += 1
            slot["example"] = slot["example"] or str(line)[:120]

        for r in diagnoses:
            for line in r.get("unmatched") or []:
                remember(line, "규칙표에 없는 부족")
            for row in r.get("city_failures") or []:
                remember(f"{row.get('city')}: {row.get('why')}", "수집 실패")
            if not r.get("failure_kind"):
                for kind, table in (r.get("symptoms") or {}).items():
                    lines = table.get("lines") if isinstance(table, dict) else table
                    if lines:
                        remember(f"[{kind}] {lines[-1]}", f"처방 가지 {kind} 가 못 맡음")
        #  ★ 한도를 다 쓰고 게이트로 간 가지 — 정해진 절차로 **못 고친** 것이다.
        for r in tests:
            if (r.get("detour_verdict") == "FAIL"
                    and int(r.get("attempt") or 0) >= int(r.get("limit") or 0)):
                evidence = r.get("evidence") or ["(증상 기록 없음)"]
                line = next((x for x in evidence
                             if not re.search(r": 목표 0 / 실제 \d+$", str(x))), evidence[0])
                remember(f"[{r.get('failure_kind')}] {line}",
                         f"처방 가지 {r.get('failure_kind')} 가 못 고침")

        #  ③-2 — 가지 없이 SHORT 로 남은 원인. replay 는 세지 않는다 (위 docstring).
        for order, r in enumerate(diagnoses, start=1):
            if r.get("failure_kind") or r.get("verdict") != "SHORT":
                continue
            if rehearsal:
                continue
            if r.get("mode") == "replay":
                skipped_replay += 1
                continue
            loop = str(r.get("loop") or "?")
            for cause in r.get("causes") or []:
                name = str(cause.get("원인") or "")
                if not name or name in _NOT_REPEAT:
                    continue
                slot = repeated[(loop, name)]
                slot["rounds"][run].add(_round_of(r, order))
                slot["places"] += _places(cause.get("몇 곳"))
                slot["example"] = slot["example"] or str(cause.get("예") or "")[:120]

        if rehearsal:
            rehearsals.append(run)
        runs.append({"run": run, "rows": len(rows), "diagnoses": len(diagnoses),
                     "detours": taken, "mode": (rows[0].get("mode") if rows else "?"),
                     "inject": sorted({k for r in rows for k in (r.get("inject") or [])})})

    def grade(runs: int, count: int) -> str:
        if runs >= PATTERN_RUNS:
            return "패턴 — 킷 처방 가지 후보"
        if count >= REPEAT_COUNT or runs >= REPEAT_RUNS:
            return "후보"
        return "일화"

    table = sorted(({"pattern": k, "runs": len(v["runs"]), "count": v["count"],
                     "example": v["example"], "verdict": grade(len(v["runs"]), v["count"])}
                    for k, v in candidates.items()),
                   key=lambda x: (-x["runs"], -x["count"]))
    again = []
    for (loop, name), v in repeated.items():
        n_runs = len(v["rounds"])
        most = max((len(r) for r in v["rounds"].values()), default=0)
        if n_runs >= PATTERN_RUNS:
            verdict = "패턴 — 킷 처방 가지 후보"
        elif most >= REPEAT_ROUNDS or n_runs >= REPEAT_RUNS:
            verdict = "후보"
        else:
            verdict = "한 번 — 재수집이 맡으면 된다"
        again.append({"loop": loop, "who": _WHO.get(loop, "재수집(LLM)"), "cause": name,
                      "runs": n_runs, "max_rounds": most, "places": v["places"],
                      "example": v["example"], "verdict": verdict,
                      "candidate": verdict != "한 번 — 재수집이 맡으면 된다"})
    again.sort(key=lambda x: (not x["candidate"], -x["runs"], -x["max_rounds"], -x["places"]))
    kinds = sorted(set(entered) | set(tried))
    return {"runs": runs,
            "detours": [{"kind": k, "entered": entered[k], "tried": tried[k], "fixed": fixed[k]}
                        for k in kinds],
            "candidates": table,
            "repeated_causes": again,
            "replay_rows_skipped": skipped_replay,
            "inject_runs_skipped": rehearsals,
            "step6": (any(x["verdict"] != "일화" for x in table)
                      or any(x["candidate"] for x in again))}


def main() -> int:
    parser = argparse.ArgumentParser(description="실패 기록 보고서")
    parser.add_argument("targets", nargs="*", help="jsonl 파일이나 폴더 (강사가 모은 것)")
    parser.add_argument("--all", action="store_true", help="evidence/failures/ 의 실행 전부")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    files = files_from(args.targets, args.all)
    if not files:
        print(" 실패 기록이 없습니다. 그래프를 한 번 돌리면 evidence/failures/ 에 생깁니다.")
        return 2
    report = summarize(files)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(LINE)
    print(f" 실패 기록 보고서 — 실행 {len(report['runs'])}개")
    print(LINE)
    print(" ① 실행별 요약")
    for r in report["runs"]:
        print(f"   {r['run'][:36]:<36} {r['mode']:<7} 진단 {r['diagnoses']}번 · 처방 가지 "
              + (", ".join(r["detours"]) if r["detours"] else "없음")
              + (f" · 재현 {', '.join(r['inject'])}" if r["inject"] else ""))
    print("")
    print(" ② 처방 가지가 맡은 실패")
    if not report["detours"]:
        print("   (처방 가지가 켜지지 않았습니다)")
    for d in report["detours"]:
        print(f"   {d['kind']:<16} 들어감 {d['entered']}번 · 시도 {d['tried']}번 · 합격 {d['fixed']}번")
    print("")
    print(" ③ 아직 처방 가지가 없는 실패 — 규칙표 밖 · 수집 실패 · 가지가 못 맡음 "
          "(같은 줄 2번 이상이면 후보 · 실행 3곳 이상이면 패턴)")
    if not report["candidates"]:
        print("   (없습니다 — 등록된 처방 가지와 원인 규칙표가 다 맡았습니다)")
    for c in report["candidates"][:15]:
        print(f"   [{c['verdict']}] 실행 {c['runs']}곳 · {c['count']}번")
        print(f"      {c['pattern']}")
        print(f"      예) {c['example']}")
    print("")
    print(" ③-2 재수집(LLM)이 반복해서 맡은 원인 — 처방 가지 후보 (같은 입력에 같은 고칠 법이 있으면 가지로)")
    again = report["repeated_causes"]
    if not again:
        print("   (없습니다 — 가지 없이 재수집으로 간 부족이 없거나, 모두 replay 실행입니다)")
    for c in again[:15]:
        print(f"   [{c['verdict']}] 루프 {c['loop']} {c['who']} · {c['cause']}")
        print(f"      실행 {c['runs']}곳 · 한 실행에서 최대 {c['max_rounds']}바퀴 · 부족 합계 {c['places']}곳")
        if c["example"]:
            print(f"      예) {c['example']}")
    if report["inject_runs_skipped"]:
        print(f"   (재현(inject) 실행 {len(report['inject_runs_skipped'])}개는 ③ · ③-2 에서 세지 않았습니다 — "
              "일부러 다시 일으킨 실패입니다)")
    if report["replay_rows_skipped"]:
        print(f"   (replay 진단 {report['replay_rows_skipped']}줄은 세지 않았습니다 — replay 의 재수집은 "
              "LLM 이 아니라 인계본을 잘라 씁니다)")
    print(LINE)
    if report["step6"]:
        print(" 다음: 후보 하나를 골라 specs/06_DETOUR.md 의 `읽기 5` 에 적고 `STEP 6 진행해줘`")
        print("       (같은 입력에 같은 고칠 법이 없으면 재수집에 그대로 둡니다 — 06_DETOUR `읽기 4`)")
    elif report["candidates"]:
        print(" 한 번 나온 실패(일화)뿐입니다 — STEP 6 은 하지 않아도 됩니다")
        print(" (같은 실패가 되풀이되면 — 다음 실행 · --all · 모은 폴더에서 [후보]가 되면 — 그때 합니다)")
    else:
        print(" 이번 실행의 실패는 이미 처방 가지와 재수집이 맡았습니다 — STEP 6 은 하지 않아도 됩니다")
        print(" (live · --all · 여러 교육생의 기록을 모은 폴더에서 후보가 생기면 그때 합니다)")
    print(LINE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
