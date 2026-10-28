# 루프 엔지니어링 스타터 킷

**질문 21개에 답하면 명세가 완성되고, 그 명세가 멈출 줄 아는 루프를 만든다.**

주제는 여행 정보 웹페이지지만, 배우는 것은 **루프 설계**입니다.

---

## 30초 요약

```text
1  질문 21개에 답한다          →  STEP 1~7 명세가 채워진다
2  명세가 한곳에 모인다         →  MASTER_SPEC.md 의 검사 계약
3  루프 세 개가 돈다            →  A 정보 모으기 → B 화면 만들기 → C 정성 3회
4  검사기가 판정한다            →  exit 0 이면 끝
5  결과물                      →  output/travel_site.html  (파일 하나)
```

---

## 미리 해 두면 좋은 것 (선택)

`specs/00_DECISION_LOG.md`의 루프 구조도는 mermaid로 그려져 있습니다.
VS Code 기본 미리보기는 이걸 코드 덩어리로만 보여 주므로, 확장을 한 번만 깔아 두세요.

```bash
code --install-extension bierner.markdown-mermaid
```

설치 후 그 파일에서 `Ctrl+Shift+V`를 누르면 그림이 나옵니다.
(<https://mermaid.live> 에 붙여넣거나 GitHub에 올려서 봐도 됩니다.)

---

## 시작하는 법

```bash
cd loop_starter_kit
python scripts/check_loop_readiness.py     # NOT_READY 가 정상입니다
claude
```

Claude Code 안에서:

```text
STEP 1 진행해줘
```

> 처음 실행하면 **`NOT_READY`(exit 2)** 가 나옵니다. **오류가 아닙니다.**
> 아직 아무 질문에도 답하지 않았기 때문입니다.

---

## 폴더 안내

```text
USER_REQUEST.md      내가 쓰는 곳 — 국가·일수·여행 스타일
specs/               STEP 1~7 명세 (여기서 21개에 답한다)
scripts/             킷이 제공하고 잠근다. 고치지 않는다
  check_information_count.py   루프 A 판정
  check_page_contract.py       루프 B 판정
  check_quality_passes.py      루프 C 판정 (정성 3회 이행)
  verify_all.py                최종 스위치
  export_graph_handoff.py      다음 강의(그래프)로 넘길 인계본 생성
templates/           보고서·되물음 양식
MASTER_SPEC.md       결정이 모이는 곳. 검사기가 여기서 숫자를 읽는다
LOOP_CONTRACT.md     루프 실행 절차
CLAUDE.md            운영 규칙
PROJECT_MEMORY.md    결정과 이유
state/               진행 상태
evidence/runs/       실행 증거
output/              결과물 (루프가 만든다)
  travel_site.html           최종 웹페이지 파일 하나
  research_data.json         모은 정보
  graph/                     다음 강의로 넘길 인계본
```

---

## 결정 21개

| STEP | 이름 | 정하는 것 | 개수 |
| --- | --- | --- | --- |
| 1 | 입력과 취향 | 국가 · 일수 · 스타일 · 도시 선정 기준 | 3 |
| 2 | 페이지 구성안 | 화면 배치 · 색 · 취향 설명 분량 | 3 |
| 3 | 정보량 카운트 | 도시 수 · 명소 수 · 근거 수 (**숫자만**) | 4 |
| 4 | 경계·작업·안전 | 작업 목록 · 보호 파일 · 되물음 지점 | 3 |
| 5 | 테스트와 검증 | 깐깐함 등급 · 최종 검증 명령 | 3 |
| 6 | 반복 방법 | 루프별 상한 · 무진전 기준 | 3 |
| 7 | 실행 계약 | 성공 조건 · 최대 반복 | 2 |

---

## 만드는 웹페이지

`output/travel_site.html` **파일 하나**에 기능 세 개가 들어갑니다.

| 기능 | 무엇이 보이나 | 어떻게 움직이나 |
| --- | --- | --- |
| 1 국가 소개 | 국기·대표 사진 + 매력·역사·문화·국가 상태·여행 정보 | 제목을 누르면 아코디언이 펼쳐짐 |
| 2 도시와 관광지 | 도시 카드 → 관광지 목록 → 관광지 상세 | 도시를 누르면 우측 툴바가 열림. 뒤로 가기 있음 |
| 3 도시별 일정 | 근거를 바탕으로 짠 일자별 계획 | 도시 제목을 누르면 아코디언이 펼쳐짐 |

기능 2에는 **"왜 이 관광지를 넣었고 무엇을 뺐는지"** 취향 설명이 `D-취향설명분량` 줄 수만큼(권장 15줄) 들어갑니다.

---

## 루프는 셋

```text
   루프 A 정보량 충족       루프 B 페이지 완성       루프 C 정성 완성도
   ───────────────────    ───────────────────    ───────────────────
   개수 · 분량 · 중복       화면 칸을 빠짐없이       규율 10가지로 3회
   이미지가 살아 있는가      채웠는가                점검하고 고쳤는가
   check_information_count check_page_contract    check_quality_passes
        └── 먼저 끝나야 함 ─┴── 먼저 끝나야 함 ────┘

   각 루프가 끝나면 나에게 되물음이 뜹니다.
   루프 C만 통과선이 아니라 정해진 3회로 끝납니다 (킷 고정).
```

---

## 명령 정리

| 명령 | 언제 | 결과 |
| --- | --- | --- |
| `python scripts/validate_specs.py` | 명세를 채우는 중 | `PASS`(0) / `ERROR`(1) |
| `python scripts/check_loop_readiness.py` | 시작해도 되는지 | `READY`(0) / `ERROR`(1) / `NOT_READY`(2) |
| `python scripts/check_loop_readiness.py --lock` | READY 이후 | 보호 파일 해시 잠금 |
| `python scripts/check_information_count.py` | 루프 A 판정 | `PASS`(0) / `ERROR`(1) / `SHORT`(2) |
| `python scripts/check_page_contract.py` | 루프 B 판정 | `PASS`(0) / `ERROR`(1) / `SHORT`(2) |
| `python scripts/check_quality_passes.py` | 루프 C 판정 | `PASS`(0) / `ERROR`(1) / `SHORT`(2) |
| `python scripts/verify_all.py` | 최종 검증 | `SUCCESS`(0) / `ERROR`(1) / `SHORT`(2) |
| `python scripts/export_graph_handoff.py` | 루프가 끝난 뒤 | 인계본 생성(0) / `ERROR`(1) / 미완성(2) |

---

## 검사기를 킷이 미리 만들어 둔 이유

```text
AI가 채점표를 직접 만들면
    "칸이 3개 이상이면 통과" 라고 써 놓고
    칸 3개짜리 결과물을 만들어서
    스스로 통과시킵니다.
```

실제로 이 일이 있었습니다. 명세는 13칸을 요구했는데 AI가 만든 채점표는 3칸만 셌고, 검사는 통과했습니다.
그래서 `scripts/**` 는 킷이 만들어 넣고 **수정 금지**로 잠급니다.

교육생이 정하는 것은 **얼마나 깐깐하게 볼지**뿐입니다 (STEP 5).

---

## 자주 하는 실수

| 실수 | 왜 나쁜가 |
| --- | --- |
| "잘 된 것 같습니다"를 완료로 믿기 | 종료 코드만이 근거다 |
| 검사기를 고쳐서 통과시키기 | 채점표를 고치면 시험이 무의미하다 |
| 지적되지 않은 칸까지 고치기 | 무엇이 고쳐졌는지 알 수 없고, 채운 칸이 다시 깨질 수 있다 |
| 못 채운 칸을 조용히 넘기기 | 가장 나쁜 실패다. 보고서에 반드시 적는다 |
| 상한 없이 돌리기 | 같은 실수를 오래 반복한다 |

---

## 다음 강의

이 루프를 **그래프**로 옮깁니다. 작업이 노드(루프 골격 14개)가 되고, 실패 라우팅이 간선이 됩니다.
검사기 바로 뒤 **진단 노드 2개**가 원인을 가려, 정해진 고칠 법이 있는 실패만 **규칙 처방 가지**
(고치고 → 시험 → 검사기로 복귀)로 보냅니다.

루프를 끝까지 돌린 뒤 아래를 실행하면 넘길 것이 한 폴더에 모입니다.

```bash
python scripts/export_graph_handoff.py
```

```text
output/graph/
  00_START_HERE.md     무엇을 어떤 순서로 쓰는가
  01_HANDOFF.md        그래프 설계용 — 이것만 붙여넣으면 된다
  02_USER_REQUEST.md   취향 원문 (요약본으로는 부족하다)
  03_CONTRACT.json     검사 계약 — 그래프 결과도 같은 자로 잰다
  04_RUN_EVIDENCE.md   실측 — 어디에 구멍이 났는지 = 어느 처방 가지가 필요한지
                       (8번은 그래프판과 나란히 놓을 루프판 기준선)
  05_STATE_SEED.json   그래프 초기 상태
  research_data.json   루프가 모은 정보 원본
                       (루프 A를 돌리기 전이면 이 파일이 빠져 6개 — 그때는 그래프 킷에 덮어쓰지 않는다)
```

**계약은 그대로 두고 실행 구조만 바꿉니다.** 그래야 두 방식을 같은 표에 올려 비교할 수 있습니다.
