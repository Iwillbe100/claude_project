---
name: spec-sync
description: 승인된 결정이 바뀌었을 때 영향 범위를 계산하고 이후 STEP 문서를 동기화한다. "D-도시수를 바꾸고 싶어", "명소를 5개로 늘리자", "이 결정 바꾸면 뭐가 영향받아?", "문서 동기화해줘", "STEP 문서 일관성 확인" 같은 요청에서 사용한다.
user-invocable: true
argument-hint: "[결정 ID 또는 바꿀 내용]"
---

# spec-sync — 결정 변경 전파기

## 활성화 조건

이미 승인된 결정을 바꾸려 할 때. 또는 문서끼리 어긋났는지 확인하려 할 때.

---

## 절대 규칙

1. **조용히 덮어쓰지 않는다.** 바꾸기 전에 영향 범위를 표로 보여 주고 확인을 받는다.
2. **`읽기 4`의 질문 문장은 어떤 경우에도 바꾸지 않는다.** 바뀌는 것은 값뿐이다.
3. 갱신은 `PROJECT` 영역과 `MACHINE` JSON 안에서만 한다.
4. 영향받는 STEP은 상태를 `NEEDS_REVIEW`로 바꾼다. 임의로 `APPROVED`로 되돌리지 않는다.

---

## 결정이 어디로 흐르는가

| 바뀐 결정 | 다시 봐야 하는 곳 |
| --- | --- |
| `D-여행입력` | STEP 3 `days_per_city` → **도시마다** 일정 칸 수 · 검색어 전체 |
| `D-취향분류` | `USER_REQUEST.md` 칸 수 → STEP 2 취향 설명 내용 |
| `D-도시선정기준` | STEP 3 도시 선정 → `why_selected` 문장 |
| `D-페이지구성` | `page_contract.layout` → 루프 B 검사 항목 전체 |
| `D-디자인요구` | `page_contract.theme` (검사 대상 아님) |
| `D-취향설명분량` | STEP 3 `preference_note_min_lines` → 루프 A·B 양쪽 검사 |
| `D-도시수` | 관광지 총 개수 → 이미지 장수 → **일정 칸 = 도시수 × 여행 일수** · STEP 4 `inherited.city_count` |
| `D-명소수` | 관광지 총 개수 → 이미지 장수 → 루프 A 시간 · STEP 4 `inherited.spots_per_city` |
| `D-소개근거수` | 기능1·기능2 근거 목표치 전부 |
| `D-일정근거수` | 기능3 근거 목표치 |
| `D-작업목록` | STEP 5 루프별 테스트 · STEP 7 첫 작업 · `LOOP_CONTRACT` 순서 |
| `D-수정금지파일` | `LOOP_CONTRACT` 보호 파일 칸 · 준비도 검사(`specs`·`scripts` 포함 여부). `--lock` 잠금 대상(킷 고정 28개)은 바뀌지 않는다 |
| `D-사람확인지점` | STEP 6 되물음 시점 |
| `D-정보량테스트` | `count_contract.strictness` → 루프 A 판정 기준 |
| `D-페이지테스트` | `page_contract.strictness` → 루프 B 판정 기준 |
| `D-최종검증명령` | STEP 7 `inherited.final_verifier_command` |
| `D-정보루프반복` `D-페이지루프반복` `D-무진전기준` | STEP 7 종료 조건 · 되물음 시점 |
| `D-성공조건` `D-최대반복` | `LOOP_CONTRACT` 실행 값 |

**숫자 결정은 `MASTER_SPEC.md`의 검사 계약까지 반드시 함께 고친다.**
스크립트는 그 계약에서만 숫자를 읽기 때문에, 명세만 고치고 계약을 안 고치면 **검사 기준이 그대로다.**

**킷 고정값은 교육생 결정이 아니다 — 바꾸자는 요청이 오면 먼저 알린다**

```text
min_chars     분량 하한        근거 · 상세 · 선정 이유 · 취향 설명 줄
dedup         중복 상한        고유 줄 비율 · 글 사이 유사도
asset_rule    이미지 유효성     verified 기록 · 만들 수 없는 주소 형태 금지
itinerary     일정 형식        도시마다 여행 일수 · 하루 블록 수 · HH:MM
quality       정성 루프        규율 10가지 · 3회 · 되돌아감 확인
```

이 값들은 **결정 21개에 들어 있지 않다.** 낮추면 지난번에 겪은 실패가 그대로 돌아온다.

```text
분량 하한을 낮추면    기준선에서 문장을 끊는다
중복 상한을 풀면      번호만 바꾼 같은 문장으로 줄 수를 채운다
자산 검사를 끄면      전부 죽은 이미지 11장이 통과한다
정성 회차를 줄이면    점검했다고 말만 하고 넘어간다
```

> 그래도 바꿔야 한다면 **킷 개정**이지 결정 변경이 아니다.
> 사람에게 그 차이를 분명히 말하고, 승인 없이는 손대지 않는다.

---

## 실행 순서

1. 바꾸려는 결정 ID와 현재 값을 확인한다.
2. 위 표로 영향받는 STEP을 계산한다.
3. 영향 범위를 표로 보여 준다.

```text
바꿀 것 : D-명소수  3 → 5
영향    : 관광지 총 개수 9 → 15
          필요한 이미지 11 → 17장
          루프 A 예상 시간 15분 → 30분
재검토  : specs/03, specs/04, specs/05, specs/07, MASTER_SPEC.md(count_contract)
```

4. 확인을 받으면 `specs/00_DECISION_LOG.md`의 변경 이력에 **시각 · 결정 ID · 이전 값 · 새 값 · 이유 · 영향받은 STEP**을 적는다.
   같은 내용을 `PROJECT_MEMORY.md` 5번(바꾼 결정)과 3번 값에도 반영한다.
5. 해당 STEP의 `읽기 5`·`읽기 6`을 새 값으로 고친다.
6. 뒤 STEP 문서의 물려받은 결정 표와 `inherited` 블록을 고친다.
7. 영향받는 STEP의 상태를 `NEEDS_REVIEW`로 바꾼다.
8. `MASTER_SPEC.md` · `LOOP_CONTRACT.md`가 이미 채워져 있었다면 다시 채워야 한다고 알린다.
9. `specs/00_DECISION_LOG.md`의 **5번 루프 구조도**에 그 값이 들어 있었다면 다시 그린다.
   숫자만 바뀌면 그 숫자 자리만, 작업 목록이 바뀌면 5-1의 작업표도 바꾼다.
10. 검사한다.

```bash
python scripts/validate_specs.py
python scripts/check_loop_readiness.py
```

---

## 루프가 도는 중에 결정을 바꾸려 할 때

명세를 바꾸면 잠금(`state/spec_lock.json`)과 어긋납니다. 어긋난 채로는 준비도 검사가
`ERROR`("잠금 이후 보호 파일이 바뀌었습니다")를 내고 `--lock`도 거부합니다. 반드시 이 순서로 안내한다.

```text
1  루프를 멈춘다
2  사람이 state/spec_lock.json 을 지운다   ← 잠금 해제. 사람이 승인한 변경일 때만
3  spec-sync로 문서를 고친다
4  python scripts/check_loop_readiness.py  → READY 확인
5  python scripts/check_loop_readiness.py --lock  → 다시 잠근다
6  루프를 다시 시작한다
```

---

## 보고 형식

```text
변경     : D-명소수  3 → 5
이유     : 도시마다 볼 곳이 너무 적어서
기록     : specs/00_DECISION_LOG.md 변경 이력 1줄 · PROJECT_MEMORY.md 5번 1줄
갱신     : specs/03, specs/04(inherited.spots_per_city), specs/05, MASTER_SPEC.md(count_contract.cities.spots_per_city)
           00_DECISION_LOG 5번 구조도 (도시당 3곳 → 5곳)
상태     : STEP 4 · 5 · 7 → NEEDS_REVIEW
검사     : validate_specs.py exit 0 / check_loop_readiness.py NOT_READY(2)
다음     : "STEP 5 다시 검토해줘"
```
