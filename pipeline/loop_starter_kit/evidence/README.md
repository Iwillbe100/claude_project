# evidence/ — 무엇을 했고 결과가 무엇이었나

이 폴더는 **실행 증거**를 담습니다.
증거가 없으면 "고쳤다"는 말도, "같은 실패다"라는 말도, "성공했다"는 말도 확인할 수 없습니다.

---

## 1. 폴더 구조

실행할 때마다 새 폴더를 만듭니다.

```text
evidence/
└─ runs/
   └─ <run_id>/
      ├─ run_manifest.json    이 실행이 무엇이었는지
      ├─ events.jsonl         반복마다 한 줄씩
      ├─ test_results/        검사기 출력 파일
      ├─ changes/             변경 파일 목록과 해시
      ├─ quality/             정성 회차마다 한 파일 (pass1~3.json)
      ├─ failure_report.md    중단했을 때
      ├─ reverse_question.md  사람 결정이 필요할 때 (templates/REVERSE_QUESTION.md)
      └─ final_report.md      성공했을 때
```

`run_id`는 시각으로 만듭니다. 예: `2026-09-04T11-20-05`

---

## 2. `run_manifest.json`

```json
{
  "run_id": "2026-09-05T14-20-05",
  "started_at": "2026-09-05T14:20:05",
  "country": "베트남",
  "days": 5,
  "first_task": "TASK-입력읽기",
  "final_verifier": "python scripts/verify_all.py",
  "loop_limits": {"A": 3, "B": 3},
  "spec_lock": "state/spec_lock.json",
  "max_iterations": 10
}
```

---

## 3. `events.jsonl`

한 반복이 끝날 때마다 **한 줄**을 추가합니다. (`.jsonl` = 한 줄에 JSON 하나)

```json
{"iteration":1,"loop":"A","task_id":"TASK-명소수집","command":"python scripts/check_information_count.py","exit_code":2,"failure_type":"INFORMATION_INSUFFICIENT","error_hash":"sha256:ab12...","short_slots":["다낭/한강 용다리 이미지","후에 취향 설명 줄 수"],"changed_files":[],"next_action":"RESEARCH","log_path":"test_results/iter01.txt"}
{"iteration":2,"loop":"A","task_id":"TASK-명소수집","command":"python scripts/check_information_count.py","exit_code":0,"failure_type":null,"error_hash":null,"short_slots":[],"changed_files":["output/research_data.json"],"next_action":"REVERSE_QUESTION","log_path":"test_results/iter02.txt"}
```

`next_action` 에는 실패 라우팅 값(`RETRY` · `RESEARCH` · `REVISE_SPEC` · `HITL` · `STOP`) 말고 진행 값 셋을 적습니다.

```text
REVERSE_QUESTION   되물음을 띄운 줄 (통과든 상한이든)
QUALITY            루프 C 가 남은 회차를 도는 줄 (판정기 exit 2 는 진행 중이다)
DONE               최종 검증(verify_all.py exit 0)으로 정상 종료한 줄
```

출발점 빨간불(RED — 수집 전 `verify_all.py` 가 SHORT 인지 확인)을 남길 때는 `iteration` 을 **0** 으로 적습니다.
반복이 아니라 출발점이라 바퀴로 세지 않습니다.

인계본(`export_graph_handoff.py`)은 `REVERSE_QUESTION` · `HITL` 줄 수를 **사람 호출 횟수**로 세고,
`failure_type` 이 적혔거나 다음 행동이 실패 라우팅이면서 검사기가 통과하지 않은 줄만 **실패**로 셉니다
(진행 값 셋과 `iteration` 0 줄은 실패가 아닙니다).

---

## 4. 반드시 남기는 것

```text
실행한 명령
종료 코드
어느 루프였나 (A 정보량 / B 페이지 / C 정성)
실패 유형 (7가지 중 하나)
오류 지문 (같은 실패인지 비교용)
부족했던 칸 목록
변경한 파일
선택한 다음 행동
로그 파일 경로
중단했다면 그 이유
```

---

## 5. 절대 남기지 않는 것

```text
API 키, 토큰, 비밀번호
개인정보 (이름, 이메일, 전화번호, 주소)
모델의 비공개 사고 과정 전체
```

필요하면 값 대신 `<REDACTED>`로 씁니다.

> 증거는 "무엇을 했고 결과가 무엇이었나"의 기록입니다. "무슨 생각을 했나"의 기록이 아닙니다.

---

## 6. 증거를 읽는 법

```text
같은 error_hash가 D-무진전기준 이상 → 진전이 없다. 되물음을 띄울 때다
같은 short_slots가 계속 남음        → 인터넷에 그 정보가 없을 가능성이 크다
changed_files가 매번 다름           → 원인을 못 찾고 여기저기 고치고 있다
exit_code 2가 계속                  → 아직 덜 됐다 (정상)
exit_code 1                         → 깨졌다. 더 돌려도 소용없다
```

정리는 `/evidence-review` Skill이 대신 해 줍니다.

---

## 7. 정리

오래된 실행 폴더는 지워도 됩니다. 다만 `PROJECT_MEMORY.md`의 실행 기록 요약 표는 남겨 두세요.
