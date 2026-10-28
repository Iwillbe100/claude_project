# 정성 회차 기록 형식 (Quality Pass)

루프 C는 **3회 돕니다.** 회차마다 이 형식으로 한 파일을 남깁니다.

```text
evidence/runs/<run_id>/quality/pass1.json
evidence/runs/<run_id>/quality/pass2.json
evidence/runs/<run_id>/quality/pass3.json
```

`scripts/check_quality_passes.py`가 이 파일만 보고 판정합니다.
**글이 좋아졌는지는 보지 않습니다.** 절차를 지켰는지만 봅니다.

**적을 때 걸리는 세 가지**

```text
verdict 가 VIOLATION 인데 where 가 "-"       자리를 못 대면 고칠 수도, 확인할 수도 없다
verify_after.exit_code 를 그냥 0 이라고 적음   마지막 회차는 판정기가 직접 다시 돌려 맞춰 본다
3회 내내 applied_fix 가 비어 있음             SHORT. 되물음으로 사람에게 넘어간다
```

---

## 1. 한 회차의 모양 (고정)

```json
{
  "pass": 1,
  "focus": ["Q-반복금지", "Q-취향연결", "Q-뺀이유", "Q-상세삼요소"],
  "checked_at": "2026-09-05T15:02:11",
  "snapshot_before": {
    "output/research_data.json": "sha256:1a2b…",
    "output/travel_site.html": "sha256:3c4d…"
  },
  "rules": [
    {"id": "Q-반복금지", "verdict": "VIOLATION",
     "where": "cities[0].preference_note",
     "note": "30줄 중 21줄이 번호만 다른 같은 문장"},
    {"id": "Q-취향연결", "verdict": "OK", "where": "-", "note": "원문 표현과 이어짐"}
  ],
  "applied_fix": [
    {"rule": "Q-반복금지", "file": "output/research_data.json",
     "what": "복제 21줄을 관광지별 실제 취향 연결 문장으로 교체"}
  ],
  "snapshot_after": {
    "output/research_data.json": "sha256:9f8e…",
    "output/travel_site.html": "sha256:7d6c…"
  },
  "verify_after": {
    "command": "python scripts/verify_all.py --skip-quality",
    "exit_code": 0
  }
}
```

---

## 2. 칸마다의 뜻

| 칸 | 뜻 | 안 지키면 |
| --- | --- | --- |
| `pass` | 회차 번호 (1·2·3) | 파일이 없으면 `SHORT` |
| `focus` | 그 회차의 렌즈. `quality_contract.pass_focus`와 **정확히 같아야** 함 | 렌즈를 안 바꾼 것으로 봄 |
| `rules` | 규율 **10개 전부** 판정. `OK` 또는 `VIOLATION` | 빠뜨리면 `SHORT` |
| `applied_fix` | 이번 회차에 **실제로 바꾼 것** | `VIOLATION`인데 없으면 `SHORT` |
| `snapshot_before` / `snapshot_after` | 회차 전후 파일 해시 | 고쳤다는데 안 바뀌었으면 `SHORT` |
| `verify_after` | 회차 끝의 정량 재검증 | `exit 0`이 아니면 `SHORT` |

---

## 3. 반드시 지키는 것

1. **10개를 전부 판정한다.** 그 회차의 초점(렌즈)만 보는 것이 아니라, 초점을 **먼저 고칠 뿐**이다 (렌즈 수는 1·2회차 4개, 3회차 2개).
2. **`VIOLATION`이라 적었으면 반드시 고친다.** 적어 놓고 넘어갈 수 없다.
3. **고칠 게 없으면 `applied_fix`를 비운다.** 그때는 파일 해시가 그대로여야 한다.
   억지로 고친 척하면 해시가 바뀌어서 걸린다.
4. **회차 끝마다 정량 재검증을 돌린다.**

```bash
python scripts/verify_all.py --skip-quality
```

`exit 0`이 아니면 **그 회차의 수정을 되돌린다.** 정성 개선이 정량 계약을 깨뜨리면 안 된다.

5. **앞 회차의 `snapshot_after` = 다음 회차의 `snapshot_before`.**
   그 사이에 몰래 고치면 어긋나서 걸린다.

---

## 4. 해시 만드는 법

```bash
python -c "import hashlib;print('sha256:'+hashlib.sha256(open('output/travel_site.html','rb').read()).hexdigest())"
```

---

## 5. 누가 판정하는가

| 판정 | 담당 |
| --- | --- |
| 이 글이 반복인가 · 취향과 이어지는가 · 일정이 현실적인가 | LLM |
| 3회를 돌았는가 · 10개를 다 봤는가 · 고쳤다는데 바뀌었는가 | 코드 |
| 최종 결과물이 쓸 만한가 | 사람 |
