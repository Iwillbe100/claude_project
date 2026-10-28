#!/usr/bin/env python3
"""LangSmith .env 탐색 -> 검증 -> 프로젝트 루트 연결.

표준 라이브러리만 사용한다. 가상환경 구축 전(시스템 파이썬)에도, 구축 후(.venv)에도
똑같이 동작해야 하므로 python-dotenv 조차 import 하지 않는다.

하는 일
  1. 원본 .env 를 정해진 우선순위로 찾는다 (기본 가정: <PROJECT_ROOT>/.env)
  2. LANGSMITH_API_KEY 가 실제로 들어 있는지, 자리표시자가 아닌지 검사한다
  3. LANGSMITH_TRACING / LANGSMITH_PROJECT 가 없으면 기본값을 채워 정규화한다
  4. <PROJECT_ROOT>/.env 로 복사한다 (기존 파일은 .env.bak 로 백업)
  5. <PROJECT_ROOT>/.gitignore 에 .env 가 있는지 확인하고 없으면 추가한다

키 값은 어떤 경우에도 원문 그대로 출력하지 않는다. 항상 마스킹한다.

사용법
  python settings/scripts/link_env.py               # 기본 탐색
  python settings/scripts/link_env.py --source PATH # 원본 .env 를 직접 지정
  python settings/scripts/link_env.py --check-only  # 복사하지 않고 진단만
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

try:  # Windows 콘솔(cp949)에서도 한글/기호가 깨지지 않게
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

# settings/scripts/link_env.py -> parents[0]=scripts, [1]=settings, [2]=PROJECT_ROOT
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_DIR = Path(__file__).resolve().parents[1]

REQUIRED_KEYS = ("LANGSMITH_API_KEY",)
DEFAULTED_KEYS = {
    "LANGSMITH_TRACING": "true",
    "LANGSMITH_PROJECT": "langgraph-travel-course",
}
# 자리표시자로 남아 있으면 "채워지지 않은 키"로 간주한다.
PLACEHOLDER_MARKERS = ("여기에", "your", "xxx", "<", "changeme", "paste")

SAFE_PREFIXES = ("lsv2_pt_", "lsv2_sk_", "ls__")


def mask(value: str) -> str:
    """키를 복원 불가능한 형태로만 보여 준다."""
    v = value.strip()
    if not v:
        return "(비어 있음)"
    for p in SAFE_PREFIXES:
        if v.startswith(p):
            return f"{p}****  (총 {len(v)}자)"
    return f"{v[:2]}****  (총 {len(v)}자)"


def parse_env(path: Path) -> "list[tuple[str, str, str]]":
    """.env 를 (key, value, 원본줄) 목록으로 읽는다. 주석/빈 줄은 ('', '', 줄)."""
    rows: list[tuple[str, str, str]] = []
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            rows.append(("", "", raw))
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            rows.append(("", "", raw))
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        rows.append((key, val, raw))
    return rows


def looks_unfilled(value: str) -> bool:
    if not value.strip():
        return True
    low = value.lower()
    return any(m in low for m in PLACEHOLDER_MARKERS)


def candidates(explicit: str | None) -> "list[Path]":
    out: list[Path] = []
    if explicit:
        out.append(Path(explicit).expanduser().resolve())
    env_override = os.environ.get("LANGSMITH_ENV_FILE")
    if env_override:
        out.append(Path(env_override).expanduser().resolve())
    out.extend(
        [
            PROJECT_ROOT / ".env",                        # 기본 가정: graph_starter_kit/.env
            SETTINGS_DIR / ".env",
            PROJECT_ROOT.parent / ".env",                 # 배포본을 하위 폴더에 푼 경우
            PROJECT_ROOT.parent / "test_graph" / ".env",
        ]
    )
    seen: set[str] = set()
    uniq: list[Path] = []
    for p in out:
        k = str(p).lower()
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return uniq


#: .env 유출 방지 + 실행 산출물(.langgraph_api, __pycache__) 커밋 방지.
GITIGNORE_ENTRIES = (".env", ".env.bak", ".venv/", "__pycache__/", ".langgraph_api/")


def ensure_gitignore(root: Path) -> str:
    gi = root / ".gitignore"
    try:
        body = gi.read_text(encoding="utf-8", errors="replace") if gi.exists() else ""
        have = {ln.strip().lstrip("/") for ln in body.splitlines()}
        missing = [e for e in GITIGNORE_ENTRIES if e not in have and e.rstrip("/") not in have]
        if not missing:
            return "이미 등록됨"
        sep = "" if not body or body.endswith("\n") else "\n"
        gi.write_text(body + sep + "\n".join(missing) + "\n", encoding="utf-8")
        return ("새로 만듦: " if not body else "추가함: ") + ", ".join(missing)
    except Exception as exc:  # noqa: BLE001
        return f"건너뜀 ({exc.__class__.__name__})"


def main() -> int:
    ap = argparse.ArgumentParser(description="LangSmith .env 연결 및 검증")
    ap.add_argument("--source", help="원본 .env 경로를 직접 지정")
    ap.add_argument("--check-only", action="store_true", help="복사하지 않고 진단만 수행")
    args = ap.parse_args()

    print("=" * 74)
    print(" LangSmith .env 연결")
    print("=" * 74)
    print(f" PROJECT_ROOT : {PROJECT_ROOT}")

    tried = candidates(args.source)
    source: Path | None = None
    for p in tried:
        if p.is_file():
            source = p
            break

    if source is None:
        print("\n[FAIL] .env 원본을 찾지 못했습니다. 탐색한 경로:")
        for p in tried:
            print(f"        - {p}")
        print("\n 조치:")
        print(f"   1) settings/.env.example 을 복사한다 -> {PROJECT_ROOT / '.env'}")
        print("   2) https://smith.langchain.com > Settings > API Keys 에서 키를 발급해 채운다")
        print("   3) 이 스크립트를 다시 실행한다")
        print("\nENV_LINK: FAIL")
        return 1

    print(f" 원본 .env    : {source}")

    rows = parse_env(source)
    values = {k: v for k, v, _ in rows if k}

    problems: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in values:
            problems.append(f"{key} 항목이 .env 에 없습니다")
        elif looks_unfilled(values[key]):
            problems.append(f"{key} 가 아직 자리표시자입니다(실제 키로 교체 필요)")

    print("\n--- .env 내용 (키 값은 마스킹) ---")
    for key in ("LANGSMITH_API_KEY", "LANGSMITH_TRACING", "LANGSMITH_PROJECT", "LANGSMITH_ENDPOINT"):
        if key not in values:
            note = "(없음 -> 기본값으로 채움)" if key in DEFAULTED_KEYS else "(없음 -> 기본 엔드포인트 사용)"
            print(f"  {key:<20} {note}")
            continue
        shown = mask(values[key]) if "KEY" in key else values[key]
        print(f"  {key:<20} {shown}")

    extra = [k for k in values if k.startswith("LANGSMITH_") is False]
    if extra:
        print(f"  (그 밖의 항목 {len(extra)}개는 그대로 보존합니다)")

    if problems:
        print("\n[FAIL] .env 검증 실패:")
        for p in problems:
            print(f"        - {p}")
        print("\nENV_LINK: FAIL")
        return 1

    tracing = values.get("LANGSMITH_TRACING", DEFAULTED_KEYS["LANGSMITH_TRACING"])
    if tracing.strip().lower() not in ("1", "true", "yes", "on"):
        print(f"\n[WARN] LANGSMITH_TRACING={tracing} -> 트레이싱이 꺼져 있습니다.")
        print("       노드별 추적을 보려면 true 로 바꾸십시오.")

    dest = PROJECT_ROOT / ".env"

    if args.check_only:
        print("\n[ OK ] 진단만 수행했습니다 (--check-only). 복사하지 않았습니다.")
        print("\nENV_LINK: PASS")
        return 0

    # 누락된 기본 키를 보강한 내용을 만든다 (원본 줄 순서/주석은 그대로 보존).
    out_lines = [raw for _, _, raw in rows]
    appended: list[str] = []
    for key, default in DEFAULTED_KEYS.items():
        if key not in values:
            appended.append(f"{key}={default}")
    if appended:
        if out_lines and out_lines[-1].strip():
            out_lines.append("")
        out_lines.append("# --- link_env.py 가 자동으로 보강한 항목 ---")
        out_lines.extend(appended)

    new_text = "\n".join(out_lines).rstrip("\n") + "\n"

    # "쓰면 실제로 달라지는가"를 기준으로 판단한다. 원본 파일끼리 비교하면 줄바꿈
    # 정규화 차이만으로도 매번 백업이 쌓여, 재실행이 잦은 실습에서 지저분해진다.
    if not dest.exists():
        action = "프로젝트 루트에 새로 생성"
        dest.write_text(new_text, encoding="utf-8")
    elif dest.read_text(encoding="utf-8-sig", errors="replace") == new_text:
        action = "이미 최신 상태 (변경 없음)"
    else:
        shutil.copy2(dest, PROJECT_ROOT / ".env.bak")
        action = "기존 .env 를 .env.bak 로 백업 후 갱신"
        dest.write_text(new_text, encoding="utf-8")

    print(f"\n 대상 .env    : {dest}")
    print(f" 처리         : {action}")
    if appended:
        print(f" 보강         : {', '.join(a.split('=')[0] for a in appended)}")
    print(f" .gitignore   : {ensure_gitignore(PROJECT_ROOT)}")
    print("\n[ OK ] LangSmith .env 연결 완료.")
    print("\nENV_LINK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
