# 여기서 시작합니다 — 내 루프 인계본

> 루프 킷의 `export_graph_handoff.py` 가 **내 루프 결과**로 만든 인계본입니다.
>
> 그래프 킷의 `graph/` 폴더에 **7개 파일을 통째로 덮어쓴** 뒤
> `python scripts/check_graph_readiness.py` 를 한 번 돌리세요.
>
> **그래프 구조는 루프 골격 + 진단 + 규칙 처방 가지입니다** (루프 골격 14 + 진단 2 + 처방 가지 3×2 = Studio 그림
> 22개). 구조는 그래프 킷 문서(`CLAUDE.md` · `specs/`)가 정본이고, 이 인계본이 정본인 것은
> 루프에서 넘어온 것 — 계약 · 취향 원문 · 실측 — 입니다.

---

## 이 폴더의 파일 7개

| 파일 | 언제 쓰나 | 누가 읽나 |
| --- | --- | --- |
| `00_START_HERE.md` | 지금 | 사람 |
| `01_HANDOFF.md` | **그래프를 설계할 때** | 사람 · STEP 1~5 의 `읽기 3` |
| `02_USER_REQUEST.md` | 취향 원문이 필요할 때 | `collect_city` 노드 |
| `03_CONTRACT.json` | 결과를 **채점할 때** | `scripts/check_*.py` ★ |
| `04_RUN_EVIDENCE.md` | **어디서 구멍이 났는지** 볼 때 · 루프판 기준선(8번) | 사람 · STEP 2 · STEP 6 |
| ↑ 안의 `quality_contract` | **정성 3회**의 규율과 렌즈 | `check_quality_passes.py` · `quality_pass` 노드 |
| `05_STATE_SEED.json` | 그래프를 **실행할 때** | Studio 입력 칸 |
| `research_data.json` | 비교 기준선 · replay 모드 자료 | `travel_graph/research.py` |

---

## 순서

```text
1  01_HANDOFF.md 를 읽는다        무엇이 그대로고 무엇이 새로 필요한지
2  STEP 1~5 를 진행한다           결정 13개에 답한다 (코드는 완성본 — 권장값이 아닐 때만 바뀐다)
3  05_STATE_SEED.json 으로 돌린다  langgraph dev → Studio
4  같은 검사기로 잰다              python scripts/verify_all.py
5  STEP 6 — 처방 가지 추가 (조건부 · 실행 뒤)
                                  failure_report.py ③ · ③-2 에 후보가 있을 때만
```

**3번과 4번의 숫자를 `04_RUN_EVIDENCE.md` 8번(루프판 기준선)과 비교하는 것이 이 실습의
결론입니다.** 5번은 실패 기록에 처방 가지 후보가 있을 때만 붙는 확장입니다 — 후보가 없으면
하지 않습니다. 결정이 없고(결정은 13개 그대로), 루프 골격은 건드리지 않습니다.
평소 실행에서는 `05_STATE_SEED.json` 의 `inject`(실패 재현)를 비워 둡니다.

---

## 절대 하지 말 것

```text
03_CONTRACT.json 을 그래프용으로 '개선'하기
```

계약을 고치는 순간 루프판과 그래프판을 **같은 자로 잴 수 없게 됩니다.**
이 실습의 요점은 "같은 계약, 다른 실행 구조"입니다. 계약은 잠겨 있습니다.

---

## 이번 인계본

```text
run_id   : 2026-10-23T14-38-25
도시 수   : 2
상태     : 완성
```

