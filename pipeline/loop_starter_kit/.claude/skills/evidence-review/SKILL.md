---
name: evidence-review
description: 루프가 끝난 뒤 증거를 정리하고 보고서를 만든다. "왜 멈췄어?", "무슨 일이 있었는지 정리해줘", "보고서 만들어줘", "결과 요약해줘" 같은 요청에서 사용한다. 채운 칸과 못 채운 칸을 숨기지 않고 그대로 적는다.
user-invocable: true
argument-hint: "[run_id]"
---

# evidence-review — 증거 정리와 보고서 작성

## 활성화 조건

- `loop-run`이 `SUCCESS` 또는 `HALT_*`로 끝난 직후
- 사용자가 "왜 멈췄는지", "무엇을 했는지" 물을 때
- 사람에게 넘길 되물음이 필요할 때

---

## 절대 규칙

1. 증거에 있는 사실만 쓴다. **로그에 없는 내용을 추측해 쓰지 않는다.**
2. 실패를 성공처럼 표현하지 않는다.
3. **못 채운 칸을 반드시 목록으로 적는다.** `SUCCESS`여도 적는다. 조용히 넘어가는 것이 가장 나쁜 실패다.
4. API 키, 토큰, 개인정보는 `<REDACTED>`로 대체한다.
5. 모델의 비공개 사고 과정을 옮겨 적지 않는다. 판단의 **결과**만 적는다.

---

## 실행 순서

### 1) 실행 폴더 찾기

`evidence/runs/` 아래에서 대상 `run_id`를 고른다. 지정이 없으면 가장 최근 것.

### 2) 사실 수집

| 읽을 파일 | 뽑는 것 |
| --- | --- |
| `run_manifest.json` | 시작 시각, 국가·일수, 검사 계약 요약 |
| `events.jsonl` | 반복별 루프·명령·종료 코드·실패 유형·변경 파일 |
| `test_results/` | 검사기 출력 원문 경로 |
| `changes/` | 변경된 파일과 해시 |
| `quality/pass*.json` | 정성 회차별 판정 · 고친 것 · 파일 해시 · 재검증 종료 코드 |
| `state/loop_state.json` | 마지막 상태, 루프별 반복 횟수, 종료 이유 |

### 3) 못 채운 칸 확인 — 가장 중요한 단계

```bash
python scripts/check_information_count.py --json
python scripts/check_page_contract.py --json
python scripts/check_quality_passes.py --json
```

`rows` 중 `passed: false`인 것을 **전부** 뽑아 목록으로 만든다.
`SUCCESS`로 끝났다면 이 목록은 비어 있어야 한다. 비어 있지 않은데 `SUCCESS`라면 **명세와 어긋난 것**이므로 알린다.

### 4) 같은 오류 반복 확인

`events.jsonl`의 `error_hash`를 세어 본다.

```text
같은 지문이 D-무진전기준 이상 → 진전 없음의 근거
같은 루프가 연속 실패 → 진단이 부족했다는 신호
```

숫자로 보여 준다. "비슷해 보인다"고 쓰지 않는다.

### 5) 요약 작성

```text
루프 A 반복    : 3바퀴  마지막 exit 0
루프 B 반복    : 2바퀴  마지막 exit 0
루프 C 정성    : 3/3회  마지막 exit 0
실행한 명령    : 9개
실패 유형 분포 : INFORMATION_INSUFFICIENT 3, CODE_ERROR 1
바꾼 파일      : output/research_data.json (4회), output/travel_site.html (2회)
같은 오류 지문 : sha256:ab12… 2회
못 채운 칸     : 없음
```

### 5b) 정성 회차에서 무엇이 바뀌었나

`quality/pass*.json` 을 읽어 **회차별로** 정리한다. 이것이 정성 루프의 유일한 증거다.

```text
1회차 (내용)        위반 3 · 고침 3   취향 설명 복제 21줄 교체 외
2회차 (실행 가능성)  위반 2 · 고침 2   일정 시간 재배치 · 근거 없는 문장 삭제
3회차 (독자 관점)    위반 0 · 고침 0   파일 그대로
되돌아감            없음 (회차마다 verify_all --skip-quality exit 0)
```

**"고칠 것 없음"을 성과 없음으로 쓰지 않는다.** 3회차가 깨끗한 것은 앞 두 회차가
제대로 일했다는 뜻이다. 다만 **3회 내내 위반 0** 이면 렌즈가 무디었을 가능성을 적는다.

### 6) 보고서 생성

| 종료 상태 | 만들 파일 | 양식 |
| --- | --- | --- |
| `SUCCESS` | `evidence/runs/<run_id>/final_report.md` | `templates/FINAL_REPORT.md` |
| `HALT_*` | `evidence/runs/<run_id>/failure_report.md` | `templates/FAILURE_REPORT.md` |
| 사람 결정 필요 | 위에 더해 `reverse_question.md` | `templates/REVERSE_QUESTION.md` |

되물음에는 **선택지 2~3개와 각 선택의 결과**를 반드시 넣는다. 선택지 없이 "도와주세요"라고 쓰지 않는다.

### 7) 그래프 인계본 만들기

```bash
python scripts/export_graph_handoff.py
```

| 종료 코드 | 뜻 | 할 일 |
| --- | --- | --- |
| `0` | 인계본 완성 | 사람에게 `output/graph/` 경로를 알린다 |
| `2` | 만들었지만 루프가 덜 끝남 (파일·기록이 빠졌거나 `verify_all` 판정이 `SUCCESS` 가 아님 — 상태 '미완성') | 무엇이 비었는지 그대로 전한다 |
| `1` | 명세가 깨져 못 만듦 | `spec-sync` 로 넘긴다 |

**손으로 쓰지 않는다.** 이 폴더는 `MASTER_SPEC` · `research_data` · `events.jsonl` 에서
기계가 뽑는다. 사람이 고치면 명세와 어긋난다.

인계본에 들어가는 것 중 **`04_RUN_EVIDENCE.md` 가 가장 중요하다.** 결정은 다시 볼 수 있지만
"어디서 몇 번 실패했는가"는 이 실행에서만 알 수 있다. 다음 강의에서 어디에 규칙 처방 가지를 둘지가
여기서 정해진다 (그래프의 루프 골격은 그대로 두고, 진단 노드 뒤 처방 가지로만 늘린다).
그 파일의 **8. 루프판 기준선**(반복 · 시간 · 사람 호출 · 정성 회차)이 그래프판 비교표의 왼쪽 칸이 된다.
숫자가 비어 있으면 `run_manifest.json`의 `started_at` · `loop_state.json`의 `updated_at` ·
`events.jsonl`의 `next_action` 기록이 빠졌다는 뜻이므로 그대로 알린다.

### 8) 기억 갱신

`PROJECT_MEMORY.md`의 **6. 루프 실행 기록** 표에 한 줄 추가한다.

```text
| run_id | 시작 | 종료 상태 | 루프 A | 루프 B | 루프 C | 못 채운 칸 | 증거 경로 |
```

되물음에서 고른 답은 **7. 되물음에서 내가 고른 답** 표에 남긴다.

---

## 보고 형식

```text
run_id     : 2026-09-05T14-20-05
상태       : HALT_RESEARCH_GAP
루프 A     : 3바퀴 (상한 도달)
루프 B     : 시작 안 함
근거       : events.jsonl 7줄, error_hash 2회 반복
못 채운 칸 : 후에/황제릉 이미지 · 다낭 일정 근거 1건
생성 문서  : failure_report.md, reverse_question.md
사람이 할 일:
  [1] 한 바퀴만 더 돌린다              (약 3분, 성공 가능성 낮음)
  [2] 부족한 채로 루프 B로 넘어간다     ← 권장. 못 채운 칸은 보고서에 남습니다
  [3] D-명소수를 3 → 2로 낮춘다        (spec-sync 필요, 다시 잠가야 함)
```

### 사람의 답을 받은 뒤 어디로 넘기나

| 사람이 고른 것 | 넘기는 곳 | 먼저 할 일 |
| --- | --- | --- |
| 더 돌린다 · 이어서 한다 | `loop-run` | `state/loop_state.json`의 상한을 사람이 올려 준 값으로 갱신 |
| 기준을 바꾼다 | `spec-sync` | 사람이 `state/spec_lock.json` 삭제 → 명세 수정 → `check_loop_readiness` → `--lock` 재실행 |
| 여기서 마친다 | (끝) | `PROJECT_MEMORY.md` 실행 기록에 못 채운 칸을 남긴다 |

**넘기기 전에 반드시 확인한다.** 사람이 고르지 않았는데 혼자 다음 단계로 넘어가지 않는다.

---

**사람이 눈으로 봐야 할 것**을 마지막에 항상 적는다.

```text
- 사진이 그 관광지가 맞는가 (기계는 열리는지만 기록으로 확인했습니다)
- 환율·항공권 가격이 지금도 맞는가
- 취향 설명이 내가 쓴 말과 정말 맞는가
```

그리고 마지막에 인계본 위치를 알린다.

```text
다음 강의로 넘길 것: output/graph/   (먼저 읽을 것: 00_START_HERE.md)
```
