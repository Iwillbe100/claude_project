# 실패 보고서 양식

그래프가 `ERROR` 로 멈췄거나 구조 검사가 실패했을 때, 또는 규칙 처방 가지가 처방 한도를 다 써서
게이트로 넘어왔을 때 씁니다.

---

```text
언제        : 노드 <이름> 에서 / 검사기 <이름> 에서
실패 유형   : CODE_ERROR | INFORMATION_INSUFFICIENT | SPEC_CONFLICT
              TEST_ERROR | ENVIRONMENT_ERROR | PERMISSION_ERROR | UNKNOWN_ERROR
다음 행동   : RETRY | RESEARCH | REVISE_SPEC | HITL | STOP
오류 지문   : <last_error_hash>   같은 지문 반복 N회
원인(진단)  : failure_kind = <처방 가지 이름>   ← 진단 노드가 처방 가지를 골랐을 때만. 없으면 ""
실패 기록   : evidence/failures/<thread_id>.jsonl
서버 로그   : Traceback 첫 줄 · 끝 줄   ← Studio 실행에서 노드가 ERROR 일 때
              (Windows evidence/langgraph_dev.out.log · .err.log · macOS / Linux evidence/langgraph_dev.log.
               터미널 실행이면 그 터미널 출력)

오류 첫 줄  :
  ...

바꾼 것     : (없으면 "없음")
```

**`실패 유형` 과 `failure_kind` 는 다른 축이다.** `실패 유형` 7종은 루프에서 이식한 **넓은
분류**이고 그대로 쓴다. `failure_kind` 는 진단 노드(`diagnose_info` · `diagnose_page`)가 쓰는
**더 좁은 분류**이고, 값은 등록된 처방 가지 이름이다. 둘을 섞어 적지 않는다.

| failure_kind | 넓게 보면 (실패 유형) | 왜 처방 가지인가 (어디서 나왔나) |
| --- | --- | --- |
| `image_dead` | INFORMATION_INSUFFICIENT 중 "정보는 있는데 주소가 틀림" | 재수집(LLM)은 같은 식으로 주소를 지어낸다 — 정해진 절차로 고친다 (루프 킷 실행 로그: 해시 두 글자를 지어내 11장 전부 죽음) |
| `encoding` | CODE_ERROR / ENVIRONMENT_ERROR 쪽 (파이프가 글자를 망침) | 검사기가 세지 않는 실패 — 판정 PASS 여도 있다 (원인과 고칠 법이 이미 알려진 실패 축: Windows cp949 · 현지 글자 파일명) |
| `image_spec` | CODE_ERROR (화면 규격) | 검사기는 사진이 "있는가"만 본다 (실습생 게이트 입력: 원본 크기 사진이 서랍을 뚫음) |

---

## 그래프 구조 검사 12개

| 검사 | 증상 | 어디서 고치나 |
| --- | --- | --- |
| 1 도달 불가 노드 | `START` 에서 갈 수 없다 | `build.py` 배선 (킷 제공이라 보통 안 남) |
| 2 END 에 못 가는 노드 | 무한 루프 | 같음 |
| 3 reducer 없는 병렬 쓰기 | `InvalidUpdateError` | **STEP 4** `state.py` |
| 4 라우터 반환값 불일치 | 런타임 `KeyError` | **STEP 3** `edges.py` |
| 5 자유 문장 라우팅 | 제어가 문장 해석에 좌우 | **STEP 3** `edges.py` |
| 6 아무도 안 읽는 상태 필드 | 상태만 무거워짐 (경고) | `state.py` |
| **6b 검사기가 못 보는 노드** | `return {...}` 리터럴이 아니라 3·6번이 그 노드를 건너뜀 | `nodes.py` — 딕셔너리 리터럴로 돌려준다 |
| 7 상한 검사 없는 순환 | 종료 조건 없음. `edges.py` 에 없는 라우터가 붙은 순환도 "상한 없음"으로 본다 | **STEP 3** `edges.py` |
| **8 회차 카운터에 reducer** | 2회차에 1+2=3 이 되어 한 회차를 건너뛰고 나간다 (정성 2회만 돈다) | `state.py` — `Annotated` 를 벗긴다 |
| **9 고정 예산 순환이 카운터를 안 봄** | 3회를 채워도 못 나간다 | `edges.py` — 킷 고정이라 보통 안 남 |
| **10 선언 ALLOWED 와 배선 불일치** | 런타임 `KeyError`. `ALLOWED` 에 아예 없는 라우터(`fan_*` 빼고)도 불일치로 잡는다 | `edges.py` 의 `ALLOWED` 와 `build.py` 매핑을 맞춘다 |
| **11 처방 가지 계약** | 처방 가지가 약속한 모양이 아니다 — 루프 골격 14 · 진단 2 · 등록된 처방 가지 밖의 노드가 있다 (정본 이름은 검사기가 쥔다 — `build.py` 의 `SPINE` 에 이름을 끼워도 잡힌다) / 검사기 → 진단이 정적 간선 하나가 아니다 / 모듈 · 시험지가 제자리에 없거나 모양이 틀렸다(`fix(data, *, attempt, mode)` · `inject(obj)` · `INJECT_AT` · 시험지 문법 오류 · `run(root=None)` 없음) / 진단 밖에서 갈라진다 / `test_<이름>` 뒤가 `{back: 그 루프의 검사기, retry: 같은 fix, gate: 그 루프의 게이트}` 가 아니다 / 처방 가지 노드가 판정 · 바퀴 · 게이트 칸에 쓴다 / 시험 뒤 라우터가 `detour_limit` 을 안 읽는다 · 시험지가 `travel_graph` 를 import 한다 / 진단 뒤 라우터가 `failure_kind` · `detour_limit` 을 안 읽는다 (`킷 고정 ▼` 처방 가지 분기가 지워졌다). 이 둘은 **코드**에서 읽는지 본다 — 주석 속 글자로는 통과하지 못한다 | **STEP 6** 의 세 조각 — `travel_graph/detours/<이름>.py` · `scripts/detour_tests/test_<이름>.py` · `registry.py` 한 줄. 또는 STEP 3 에서 `edges.py` 의 `킷 고정 ▼` 구간을 건드렸을 때 |

> **검사기가 못 잡는 것도 있습니다.** `route_after_gate_b` 에서 정성 회차 분기를
> 지우면 `quality_pass` 가 한 번도 실행되지 않지만, 배선은 그대로라 12개 검사행이
> **전부 통과합니다.** 루프 C 가 돌았는지는 `history` 로 확인하십시오.
> `route_after_info` · `route_after_page` 의 `킷 고정 ▼` 처방 가지 분기는 다릅니다 — 지우면
> **11번(처방 가지 계약)** 이 빨간불을 냅니다 (진단 뒤 라우터가 `failure_kind` · `detour_limit` 을 읽는지 본다).
> 회귀 테스트 T15 가 킷 복사본에 이 변이를 실제로 만들어 확인합니다.

```bash
python scripts/check_graph_shape.py
```

> 3번 안내문을 잘 읽으십시오. 겹친 키가 **회차 카운터**이면
> "reducer 를 붙이라"가 아니라 **"순환으로 바꾸라"** 고 말합니다.
> 카운터에 reducer 를 붙이면 8번에 걸립니다.

---

## 루프 C(정성)에서 멈췄을 때

| 증상 | 뜻 | 어디를 보나 |
| --- | --- | --- |
| `check_quality` 가 `ERROR` | 판정 자체가 서지 않았다 (보통 `claude` 를 못 부름) | `evidence/runs/*/quality/blocked.json` |
| "N회차 기록이 아직 없습니다" | 아직 덜 돌았다. 정상 상태 | 그래프를 더 돌린다 |
| "위반이라 적고 고치지 않았습니다" | 판정은 했는데 수정이 적용되지 않았다 | `passN.json` 의 **`skipped_fix`** |
| "앞 회차와 이어짐: 끊김" | 회차 사이에 밖에서 파일이 바뀌었다 | 병렬 배치는 아닌지 · 수동 편집은 없었는지 |
| "무수정 회차: 바뀜" | 고친 것이 없다는데 파일이 바뀌었다 | 같은 위 |

**정성 판정은 `replay` 로 폴백하지 않습니다.** 모의로 통과시키면 "고친 척"을
자동화하는 셈이라서, 판정을 못 하면 그래프가 멈춥니다. 이것은 설계된 동작입니다.

---

## 처방 가지가 한도를 다 썼을 때

처방 가지는 `fix_<이름> → test_<이름>` 을 처방 한도(`detour_limit`, 2회)까지 돈다. 그래도 시험지가
불합격이면 **그 루프의 게이트**(A 가지 → `human_gate_a` · B 가지 → `human_gate_b`)에서
멈춘다. `ERROR` 가 아니다 — 정해진 고칠 법으로 안 된 문제를 사람에게 넘긴 것이다.

```text
처방 가지   : <이름> (<title>) · 루프 A | B · 2/2회 · 시험지 FAIL
              history: test_<이름>: FAIL · 2/2회 → human_gate_a | human_gate_b
증상        : failure_evidence 원문 그대로   ← 게이트 ② 왜 맨 앞 "처방 가지가 못 고침 — <title>" 줄
  [image_dead] 죽은 이미지 주소: 목표 0 / 실제 1
  [image_dead] 하노이/탕롱 황성 이미지: 손으로 만들 수 없는 주소 형태입니다 (upload.wikimedia.org). 권장 형태: …
고친 것     : history 의 fix_<이름> 줄 그대로 (고침 N곳 · 못 고침 N곳 · ↳ 못 고침: …)
실패 기록   : evidence/failures/<thread_id>.jsonl   (python scripts/failure_report.py <그 파일> 로 읽는다)
              ② image_dead       들어감 1번 · 시도 2번 · 합격 0번
              ③ [일화] 실행 1곳 · 1번 — 처방 가지 image_dead 가 못 고침 · 손으로 만들 수 없는 주소 형태입니다 …
                (재현(inject) 실행이면 ③ 에 뜨지 않는다 — 보고서가 빼고 센다)
실패 재현   : 없음 | <이름>   ← inject 로 그 실패를 재현한 실행이면 적는다 (저절로 난 실패인 척하지 않는다)
게이트 답   : more | proceed | stop  (A)   ·   research | rebuild | done  (B)
사람 호출   : run_once.py 의 "사람 호출 : N회 — human_gate_a → …" 그대로 (한도 끝 정지 포함)
다음 행동   : 아래 표에서 하나
```

게이트 `② 왜` 의 처방 가지 줄은 세 종류다. 이 양식을 쓰는 것은 첫째다.

```text
처방 가지가 못 고침 — <title>                 한도까지 fix → test 를 돌고도 불합격 (또는 한도를 이미 다 씀)
처방 가지 시험지가 깨짐 — <title>             시험지가 실행 중에 멈춤 — 증상이 아니다. 시험지를 혼자 돌려 고친다
처방 가지를 미룸 — <title> (정성 회차 중)     정성이 시작된 뒤라 미룸 (해시 사슬 보호) — 실패가 아니다
```

| 상황 | 다음 행동 |
| --- | --- |
| 부족이 남았다 (게이트 A 의 `③ 권장` 이 `more`) | `more` + `note`. 재수집(LLM)이 데이터를 바꾸고 **처방 한도가 새로 채워진다** (`human_gate_a: 처방 한도를 새로 채웁니다`). 게이트 A 에 한 번 더 서므로 사람 호출이 는다 |
| 검사기가 세지 않는 종류만 남았다 (깨진 글자 등 · 게이트 A 의 `③ 권장` 이 `proceed`) | `proceed`. 못 고친 증상을 최종 보고서에 **그대로** 남긴다 |
| 게이트 B (`③ 권장` 은 `done — … '고치려면' 칸을 따르십시오`) | `고치려면` 칸(그 가지의 `HOWTO`)을 따른다. 데이터로 고칠 수 있으면 `rebuild` · `research` (한도도 새로 채워진다), 화면 코드(CSS) 쪽이면 `done` — `image_spec` 의 S2 · S3 은 처방 가지도 `rebuild` 도 못 고친다. 킷 문제면 사람에게 넘긴다 |
| `처방 가지 시험지가 깨짐` (`③ 권장` 이 `proceed` · `done`) | 그래프는 그대로 진행한다. `python scripts/detour_tests/test_<이름>.py` 를 혼자 돌려 오류 줄을 고친다 (STEP 6) |
| 같은 증상이 실행마다 나온다 | `failure_report.py` ③ 에서 실행 몇 곳에 나왔는지 본다 (한 번 `[일화]` · 같은 줄 2번 이상 또는 2실행 이상 `[후보]` · 3실행 이상 `[패턴 — 킷 처방 가지 후보]`). 한도를 다 쓴 가지는 ③ 에 `처방 가지 <이름> 가 못 고침` 으로 올라온다 — 새 가지가 아니라 **그 가지의 fix 를 고칠 재료**다. 여러 실행을 보려면 `--all` (강사는 `<폴더>…`) |

- **시험지를 약하게 고쳐 통과시키지 않는다.** 시험지는 진단과 합격을 **같이** 보는 자라서,
  약하게 만들면 진단도 같이 눈을 감는다. 검사기를 고쳐 통과시키지 않는 것과 같은 규칙이다.
- **증상 줄은 라우팅에 쓰이지 않는다.** 라우터가 읽는 처방 가지 칸은 `failure_kind` ·
  `detour_attempts` · `detour_limit` · `detour_verdict` 뿐이다. `failure_evidence` 는 사람이
  읽는 자유 문장이다 (그래프 규칙 3 — 자유 문장을 라우팅에 쓰지 않는다).
- 정성(루프 C)이 한 회차라도 돈 뒤에는 루프 B 가지를 타지 않는다 (해시 사슬 보호).
  그때 게이트 `② 왜` 에는 `처방 가지를 미룸 — <title> (정성 회차 중)`, history 에는
  `diagnose_page: 증상은 있지만 처방 가지를 타지 않음 (image_spec: 정성 회차 중 — 파일 해시 사슬을
  지키려고 미룸) → 루프 골격 그대로` 가 남는다. 실패 기록(jsonl)에는 `"failure_kind": ""` ·
  `"decision": "루프 골격 그대로"` 와 증상(`symptoms` 의 `why` 에 미룬 이유)이 남고, 보고서 ③ 에는
  `처방 가지 image_spec 가 못 맡음` 으로 뜬다 — 실패가 아니다.

---

## 반드시 지키는 것

1. **실패 증거 없이 고치지 않는다.** 종료 코드와 오류 첫 줄을 먼저 남긴다.
2. **원인을 여러 개 추측해 동시에 고치지 않는다.** 한 번에 한 곳.
3. **검사기를 고쳐서 통과시키지 않는다.** 처방 가지 시험지도 약하게 고쳐 통과시키지 않는다.
4. `ERROR`(1) 와 `SHORT`(2) 를 구분해서 보고한다. `2` 는 정상적인 진행 중 상태다.
