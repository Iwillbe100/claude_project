# MEMORY.md — 다음 실행이 읽는 상태

> 에이전트만 수정한다. 사람이 직접 확인한 결과는 프롬프트로 전달되며, 에이전트가 `출처: 사람`으로 기록한다.
> 짧게 유지한다. 코드와 긴 로그는 넣지 않는다.
> 상태 값: 미시작 / 진행중 / 사람 확인 대기 / 완료 / 중단

## 현재 상태
| SPEC | 상태 | 회차 | 비고 |
|---|---|---|---|
| SPEC_00_PROJECT | 완료 | 1/3 | 자동·사람 확인 모두 통과. "블록이 생성·이동하지 않는다" 조건은 SPEC_01 결정 16으로 대체 |
| SPEC_01_SPAWN_MOVE_ROTATE | 완료 | 1/3 | 자동 29/29, 정적 점검, 헤드리스 Chrome 시나리오 A~G 통과. 2026-10-26 사람 확인 A~G 모두 정상 |
| SPEC_02_COLLISION_LOCK_CLEAR | 완료 | 1/3 | 질문 9개 "제안대로"(출처: 사람). 자동 46/46, 정적 점검, 헤드리스 Chrome 시나리오 A~F 통과. 2026-10-26 사람 확인 A~F 모두 정상 |
| SPEC_02B_DESIGN | 완료 | 1/3 | 동화 밤하늘 디자인 + 고정·줄 제거 연출. 자동 46/46, 보호 파일 diff 동일, 헤드리스 Chrome 통과. 2026-10-26 사람 확인 A~E 모두 정상 |
| SPEC_03_SCORE_HARDDROP_LEADERBOARD | 완료 | 1/3 | 점수·하드 드롭·로컬 리더보드. 질문 13개 "제안대로"(출처: 사람, 승인 파일 본문엔 질문 표시가 남아 있어 결정은 MEMORY 기록을 따름). 자동 59/59, 정적·브라우저 자동화 통과. 2026-10-26 사람 확인 "잘되었어"(A~F 확인 요청에 대한 답) |
| SPEC_04_LEVEL | 완료 | 1/3 | 레벨·속도·다음 블록·일시정지. 질문 10개 "제안대로"(출처: 사람). `/spec-run`으로 실행(Ralph 미사용). 자동 65/65, 정적·브라우저 자동화 통과. 2026-10-26 사람 확인 "잘된거같아"(A~E 확인 요청에 대한 답) |
| SPEC_05_GHOST_HOLD | 완료 | 1/3 | 워크숍 A(SPEC 05+). 고스트+홀드(7-bag 제외). 질문 9개 "제안대로"(출처: 사람). 자동 74/74, 정적·브라우저 자동화 통과. 2026-10-26 사람 확인 A~D 모두 정상 |
| ~~SPEC_01_START_SPAWN~~ | 대체됨 | 1/3 | 사람이 프로젝트에서 제거. SPEC_01_SPAWN_MOVE_ROTATE로 대체(결정 16·17) |
| ~~SPEC_02_FALL_MOVE_ROTATE~~ | 대체됨 | - | 사람이 프로젝트에서 제거. 내용은 SPEC_01_SPAWN_MOVE_ROTATE에 포함 |

워크숍 순서(출처: 사람): 01 생성·낙하·이동·회전 → 02 충돌·고정·줄 제거·게임오버 → 03 점수·하드 드롭·로컬 리더보드 → 04 레벨·속도·다음 블록·일시정지.

## 마지막 실행
- 2026-10-26: `/spec-run SPEC_00_PROJECT.md` 재실행 → 읽기 전용 회귀 검증만(회차 소모 없음). 전부 통과.
- 2026-10-26: `/spec-run SPEC_01_START_SPAWN.md` 1회차(구 SPEC). 생성까지 구현.
- 2026-10-26: `/spec-run SPEC_01_SPAWN_MOVE_ROTATE.md` 첫 요청 → 파일이 `.draft`라 시작 안 함(회차 소모 없음).
- 2026-10-26: `/spec-run SPEC_01_SPAWN_MOVE_ROTATE.md` 1회차. game.js·main.js·test.js 수정(style.css·HTML 변경 없음, 새 파일 없음). 생성 기준점을 너비 기준으로 계산(I는 SRS 4×4 상자라 기준점 row -1, 셀은 0행). 실패 없이 1회에 통과.
- 2026-10-26: `/spec-new`로 SPEC_02 초안 작성 → 사람이 승인(이름 변경). `/spec-run SPEC_02_COLLISION_LOCK_CLEAR.md` 시작 시 질문 9개가 미답이라 확인 요청 → "제안대로".
- 2026-10-26: `/spec-run SPEC_02_COLLISION_LOCK_CLEAR.md` 1회차. game.js(canPlace·clearLines·lockPiece, 이동 판정을 canPlace로, restartGame에 GAME_OVER 추가)·main.js(LANDED 다음 타이머에 고정, GAME_OVER 타이머 정지, 고정 셀 색, 버튼 상태)·test.js(신규 17개) 수정. 기존 29개 테스트 본문은 사전 백업과 diff로 동일 확인. 실패 없이 1회에 통과.

- 2026-10-26: 사람이 frontend-design 플러그인 설치 후 디자인 변경 요청 → CLAUDE.md 규칙대로 코드 대신 `SPEC_02B_DESIGN.draft.md` 작성(game.js·index.html·테스트 불변, style.css·main.js만). 워크숍 슬라이드(텍스트 추출 시 한글 깨짐)에서 영문으로 확인된 플러그인은 SPEC 04용 `ralph-wiggum`뿐.

- 2026-10-26: `/spec-run SPEC_02B_DESIGN.md` 1회차. style.css 전면 교체(토큰·시스템 글꼴·별 배경·금테 액자·보석 블록·연출 키프레임·reduced-motion·focus-visible), main.js에 효과 레이어(.fx-layer)와 drop()의 고정 직전 줄 계산 추가. game.js·index.html·test.html·test.js 불변(백업 diff). 자체 점검 중 ↑↓ 화살표가 이모지 글꼴로 바뀌는 문제 발견 → 글꼴 목록에 'Segoe UI Symbol' 추가로 수정(실패 아님, 같은 회차).
- 2026-10-26: `/spec-new` 절차로 `SPEC_03_SCORE_HARDDROP_LEADERBOARD.draft.md` 작성. SPEC_02 테스트("lockPiece는 score 불변") 때문에 점수는 새 함수(lockAndScore·softDrop·hardDrop)로 붙이도록 설계.
- 2026-10-26: `/spec-run SPEC_03_SCORE_HARDDROP_LEADERBOARD.md` 1회차. game.js(점수 상수·lockAndScore·softDrop·hardDrop·리더보드 순수 함수), main.js(↓ softDrop, Space hardDrop+연출, localStorage try/catch, 저장 폼, 목록), index.html(패널에 records 섹션 추가, 기존 줄 삭제 없음), style.css(목록·폼, 패널 폭 260px), test.js(신규 13개). lockPiece·moveDown 불변. 자체 점검: 390px에서 10자 한글 이름이 말줄임으로 잘림 → 줄바꿈(overflow-wrap)으로 수정(같은 회차). 조작 안내의 분홍빛 ↑는 이모지가 아니라 화면 캡처의 서브픽셀 렌더링(CSS.getPlatformFontsForNode: Palatino·Batang·Book Antiqua만 사용).
- 2026-10-26: `/spec-new` 절차로 `SPEC_04_LEVEL.draft.md` 작성. 미리보기를 상태에 넣으면 SPEC_02·03 테스트("주입한 random이 새 블록을 정함")와 충돌 → main.js가 nextType을 들고 randomForType으로 주입하는 설계 제안.
- 2026-10-26: `/spec-run SPEC_04_LEVEL.md` 1회차. game.js(레벨 상수·getLevel·getDropInterval·togglePause·randomForType), main.js(nextType+takeNext로 주입, 레벨 간격 타이머·간격 바뀌면 재시작, 4×4 미리보기, KeyP 일시정지·안내, 레벨 표시), index.html(미리보기·레벨·일시정지 안내 추가), style.css, test.js(신규 6개). 자체 점검: 처음엔 보드 div 줄을 고쳐 "index.html 삭제 줄 없음" 조건 위반 → 원래 줄 복원, 안내를 형제로 두고 main.js가 보드 안으로 옮기도록 수정(같은 회차).
- 2026-10-26: `/spec-run SPEC_05_GHOST_HOLD` 1회차. game.js(createInitialState에 holdType·holdUsed, lockPiece가 holdUsed=false, calculateGhostY, holdPiece), main.js(ghost- 클래스로 고스트 먼저 그림, KeyC 홀드·빈 홀드일 때만 takeNext, drawMini로 홀드·다음 칸, 사용 시 흐림), index.html(hold 섹션 추가만), style.css(패널 2열 그리드·고스트 윤곽선·흐림), test.js(신규 9개). 실패 없음.
- 2026-10-26: 사람이 "마무리" 결정(출처: 사람). SPEC 00~05(02B 포함) 모두 완료, 테스트 74개. 다음에 이어간다면 후보: SPEC_06 7-bag, 하네스 규칙 정리(아래 열린 항목), 워크숍 B.

## 반복된 실패
같은 유형이 2회 이상이면 `유형 | 횟수 | 대응책` 형식으로 기록한다.
- 승인(이름 변경)된 SPEC에 미답 `[사람 확인 필요]` 질문이 남아 있음 | 4회(SPEC_02·03·04·05) | `/spec-run` 시작 전 미답 질문 수를 grep으로 세고, 있으면 실행 전에 "제안대로 진행/중단"을 묻고 답을 MEMORY에 `출처: 사람`으로 기록한다. 하네스 규칙화(승인=제안 수용 여부)는 사람 결정 필요. (에이전트 구현 실패는 아님)

## 열린 [사람 확인 필요]
- 하네스: 완료된 SPEC을 다시 `/spec-run` 하면 어떻게 할지 규칙이 없음(이번엔 읽기 전용 회귀 검증으로 처리). 규칙화 여부 결정 필요.
- 하네스: 뒤 SPEC이 앞 SPEC 조건을 바꾸는 경우의 일반 규칙 없음(SPEC_01 결정 16, SPEC_02 질문 9에서 개별 처리). SPEC_02로 SPEC_01의 "LANDED에서 타이머 정지·`재시작` 버튼"과 시나리오 A-5·A-6·E는 회귀 검증에서 제외.
- 하네스: 승인(이름 변경)된 SPEC에 미답 `[사람 확인 필요]` 질문이 남아 있을 때의 규칙 없음(SPEC_02는 실행 전 질문해 "제안대로" 받음). 승인 = 제안 수용으로 볼지 결정 필요.

## 사람 확인 결과 (출처: 사람)
- 2026-10-26 | SPEC_00 | index.html 콘솔 오류 | 없음
- 2026-10-26 | SPEC_00 | 390px 폭 레이아웃 | 정상(가로 스크롤 없음)
- 2026-10-26 | SPEC_00 | 5초 대기·방향키 후 보드 | 변화 없음
- 2026-10-26 | SPEC_01 개정 초안 | 질문 11개 | "제안대로" (결정 7~17)
- 2026-10-26 | SPEC_01 | 초안 승인 | 사람이 `.draft` 제거, 구 SPEC_01·SPEC_02 파일 프로젝트에서 제거
- 2026-10-26 | SPEC_01 | 수동 시나리오 A~G(시작·낙하·LANDED, 좌우·벽, ↓·타이머, 회전, 재시작, 무작위·색, 390px·스크롤·콘솔) | 모두 정상
- 2026-10-26 | SPEC_02 | 질문 9개(고정 시점, ↓ 타이머, 고정 셀 값·색, 줄 제거 방식, 다음 블록, 게임오버 조건·화면, 버튼, SPEC_01 조건 대체) | "제안대로"
- 2026-10-26 | SPEC_02B 초안 | 질문 10개 | "제안대로" (동화 밤하늘·불꽃놀이, 시스템 글꼴, 연출은 겹쳐 보이기·게임 불멈춤, 줄 수별 강도, 고정 금빛 반짝임, 색 이름 유지, 제목 광택 1회, 움직임 줄이기 존중, 번호 02B, 테스트 추가 없음)
- 2026-10-26 | SPEC_03 | 질문 13개 | "제안대로" — 1 점수 100/300/500/800·↓ 칸당 1·Space 칸당 2·자동 0·배수 없음, 2 lockPiece·moveDown 불변+lockAndScore·softDrop·hardDrop 추가, 3 하드 드롭 즉시 고정·다음 낙하 700ms·READY/LANDED/GAME_OVER 무시, 4 Space 항상 막음(이름 입력칸 제외), 5 이름 trim 후 2~10자(코드 포인트)·종류 제한 없음, 6 GAME_OVER 때 폼·자동 포커스·게임당 1회·저장 없이 재시작 가능, 7 TOP10 밖 안내 후 폼 숨김, 8 점수 내림차순·동점 playedAt 이른 것 먼저·11번째부터 버림, 9 키 tetris-loop.leaderboard.v1·{id,name,score,clearedLines,playedAt}·ISO·id=playedAt+무작위, 10 손상 → 빈 목록·틀린 항목 버림, 11 저장소 불가 안내, 12 `최고 기록` 목록·`이름 (2~10자)`·`기록 저장`·금색 강조, 13 0점 저장 가능
- 2026-10-26 | SPEC_05 | 수동 시나리오 A~D(고스트, 홀드, 기존 기능, 390px·콘솔) | 모두 정상
- 2026-10-26 | SPEC_05 | 질문 9개(승인 파일에 미답 상태로 남아 실행 전 질문) | "제안대로" — 1 고스트+홀드, 2 고스트 2px 윤곽선·현재 블록 우선·READY/GAME_OVER 없음, 3 KeyC·PLAYING만·이름 입력칸 제외, 4 빈 홀드=보관+미리보기 소비, 찬 홀드=교환(생성 위치·회전 0, 미리보기 그대로), 블록당 1회, 5 홀드 후 타이머 재시작, 6 막힌 자리 GAME_OVER, 7 holdType·holdUsed 추가·lockPiece가 holdUsed 초기화, 8 패널 맨 위 홀드·다음 나란히·사용 중 흐림·조작 안내 문구 유지, 9 점수 영향 없음
- 2026-10-26 | SPEC_05 범위 | 워크숍 A 선택, 기능 고르기 | "고스트 블록, 홀드 (C 키)" (7-bag 제외)
- 2026-10-26 | SPEC_04 | 수동 시나리오 A~E(다음 블록, 레벨·속도, 일시정지, 기존 기능, 390px·콘솔) 확인 요청에 대한 답 | "잘된거같아" → 모두 정상으로 기록
- 2026-10-26 | SPEC_04 | 질문 10개(승인 파일에 미답 상태로 남아 실행 전 질문) | "제안대로" — 1 레벨 floor(줄/10)+1·상한 없음, 2 간격 max(100, 700-(레벨-1)×60)·다음 낙하부터, 3 점수 배수 없음, 4 상태·기존 함수 불변·main.js가 nextType을 randomForType으로 주입, 5 패널 맨 위 4×4 미리보기·READY/GAME_OVER 비움, 6 KeyP 기준·이름 입력칸 제외, 7 PLAYING↔PAUSED만, 8 어둡게+`일시정지 · P를 누르면 계속`·키 무시·버튼 비활성·재개 후 현재 간격, 9 `레벨`은 `제거한 줄` 아래·리더보드엔 없음, 10 SPEC_04_COMPLETE = 자동·에이전트 통과(사람 확인 대기)
- 2026-10-26 | SPEC_03 | 수동 시나리오 A~F(점수, 하드 드롭, 저장, 이름 규칙, 손상 기록, 390px·콘솔) 확인 요청에 대한 답 | "잘되었어" → 모두 정상으로 기록
- 2026-10-26 | SPEC_02B | 수동 시나리오 A~E(분위기·색·글꼴, 고정 연출, 줄 제거 연출, 게임 진행 불변, 390px·움직임 줄이기·포커스·콘솔) | 모두 정상
- 2026-10-26 | SPEC_02 | 수동 시나리오 A~F(고정·다음 블록, 쌓기·충돌, 줄 제거, 게임 오버, 재시작, 390px·스크롤·콘솔) | 모두 정상

## 에이전트 확인 결과 (출처: 에이전트)
- 2026-10-26 | SPEC_00 | Node 8/8, Chrome test.html 8/8, 정적 점검 통과.
- 2026-10-26 | SPEC_00 회귀 | 구 SPEC_01 이후 코드 기준 전부 통과(390px, 콘솔 0 포함).
- 2026-10-26 | SPEC_01 | Node(vm) 29/29(기존 17 + 신규 12), Chrome test.html "통과 29 · 실패 0".
- 2026-10-26 | SPEC_01 | 정적: 6개 파일만, 스크립트 순서·defer 유지, game.js에 document/window/setTimeout/setInterval/addEventListener 없음, 외부 URL·import 없음, main.js에 숫자 700 없음·DROP_INTERVAL_MS 사용, 방향키 4개 preventDefault.
- 2026-10-26 | SPEC_01 | CDP A: 시작→PLAYING·J (0,3)(1,3)(1,4)(1,5)·0·0·버튼 비활성, 재클릭 변화 없음, 10초 bottom 15, 13.2초 LANDED, 낙하 간격 687~710ms, LANDED 후 키 무반응·`재시작` 활성.
- 2026-10-26 | SPEC_01 | CDP E: 재시작 2회 모두 빈 보드·새 블록·PLAYING·0·0·`시작` 비활성, 10초 bottom 15, 간격 690~711ms(타이머 중복 없음).
- 2026-10-26 | SPEC_01 | CDP B: ← 열 3→0 후 정지, → 오른쪽 끝 9 후 정지. C: ↓ 5번(300ms 간격) 정확히 5칸, 마지막 ↓ 후 첫 자동 낙하 709ms. D: T 회전 모양·4회 복귀·왼쪽 벽 회전 무시, I 생성 직후 회전 무시·한 칸 뒤 (0,5)~(3,5).
- 2026-10-26 | SPEC_01 | CDP F: 새로고침 20회 7종 모두 등장, 7색 서로 다름. G: 390px scrollWidth=clientWidth=390, 세로 배치, READY·PLAYING 방향키 defaultPrevented=true, Space는 false, 콘솔 오류 0.

- 2026-10-26 | SPEC_02 | Node(vm) 46/46(기존 29 + 신규 17), Chrome test.html "통과 46 · 실패 0". test.js 1~344행(기존 테스트) 사전 백업과 diff 동일.
- 2026-10-26 | SPEC_02 | 정적: 6개 파일만, 스크립트 순서·defer 유지, game.js 금지 패턴 없음, 외부 URL·import 없음, main.js drop()에서 LANDED→lockPiece, update()에서 GAME_OVER→타이머 정지, 숫자 700 없음.
- 2026-10-26 | SPEC_02 | CDP A: LANDED 690ms 뒤 고정, 고정 블록 같은 색 유지, 새 블록 생성·낙하, LANDED 동안 버튼 비활성. B(O,O,O,T 고정 순서): O 쌓기 겹침 없음, 고정 블록 쪽 → 막힘, O2 위 T 회전 막힘. C(I,I,O): 19행 제거, 18행 O가 19행으로, 제거한 줄 1, 점수 0.
- 2026-10-26 | SPEC_02 | CDP D: ↓ 연타로 11개 고정 후 GAME_OVER, 새 블록 안 그림(44칸), 3초+키 변화 없음, `재시작` 활성. E: 재시작 빈 보드·0·0·PLAYING·`시작` 비활성, 10초 시점 bottom 15. F: 390px 가로 스크롤 없음, GAME_OVER에서도 방향키 defaultPrevented, 콘솔 오류 0.

- 2026-10-26 | SPEC_02B | Node 46/46, Chrome test.html 46/0. 문구 불변(title·h1·dt·상태·버튼·조작 안내). 1줄 제거: fx-lock 4·fx-band 1·fx-spark 14, 고정 후 첫 낙하 ≈692ms, 2초 뒤 효과 0개. 4줄(390px): band 4·spark 56·burst 3·ray 48·흔들림, scrollWidth 390=clientWidth 내내 유지, 2초 뒤 0개. reduced-motion: h1 애니메이션 none, fx-lock·fx-band만 fx-fade 0.18s, 0.4초 뒤 0개. Tab 포커스 금색 외곽선. 콘솔 오류 0.

- 2026-10-26 | SPEC_03 | Node 59/59(기존 46 + 신규 13), Chrome test.html 59/0, test.js 1~544행 백업과 동일. 정적: 6개 파일, 스크립트 순서·defer 유지, index.html 삭제 줄 없음, game.js에 DOM·localStorage·타이머 없음, main.js localStorage 2곳 모두 try 안, innerHTML 없음, 숫자 700 없음.
- 2026-10-26 | SPEC_03 | CDP: 자동 낙하 0점, ↓×5=5점, I·I·O 하드 드롭 38+38+36+100=212·lines 1, 하드 드롭 시 fx-lock 4, 다음 첫 낙하 ≈664ms. READY·PLAYING Space defaultPrevented, scrollY 0. 게임 오버 → 폼 표시·입력칸 포커스·`재시작`, '별님' 저장 → 목록 강조·localStorage 5필드 JSON 배열·새로고침 후 유지. '가'·공백·11자 거부 안내. 입력칸 ←·Space 안 막힘('a b'). 두 번째 저장 점수순 정렬. 재시작 시 폼·문구 숨김. TOP10 밖 안내·저장값 불변. '{broken' → 빈 목록·오류 0·게임 정상·다음 저장 정상. localStorage 차단 → 안내·게임 정상·오류 0. 390px 폼 열린 상태 scrollWidth=clientWidth=390, 10자 이름 줄바꿈(잘림 없음). 콘솔 오류 0.

- 2026-10-26 | SPEC_04 | Node 65/65(기존 59 + 신규 6), Chrome test.html 65/0, test.js 1~718행 백업과 동일. 정적: 6개 파일, 스크립트 순서·defer, index.html 삭제 줄 없음, game.js 금지 패턴 없음, main.js 낙하 간격 숫자 직접 사용 없음(60은 효과 난수 범위뿐).
- 2026-10-26 | SPEC_04 | CDP: READY 미리보기 비움·P 무시. 레벨 1 낙하 간격 699~708ms. 하드 드롭 10회 연속 새 블록 = 직전 미리보기. P → PAUSED·안내 표시·버튼 비활성·3초+방향키·Space 변화 없음(기본 동작 막힘), P → PLAYING·첫 낙하 703ms. 한글 ㅔ(KeyP) 일시정지·재개. GAME_OVER P 무시·미리보기 비움. 이름 입력칸 p 입력('별님p' 저장). 재시작 레벨 1. O 25개로 10줄 → 레벨 2, 간격 638~642ms. 390px 가로 스크롤 없음. 콘솔 오류 0.

- 2026-10-26 | SPEC_05 | Node 74/74(기존 65 + 신규 9), Chrome test.html 74/0, test.js 1~776행 백업과 동일. 정적: 6개 파일, 스크립트 순서·defer, index.html 삭제 줄 없음(조작 안내 문구 그대로), game.js 금지 패턴 없음.
- 2026-10-26 | SPEC_05 | CDP: READY 고스트·홀드 없음. 시작 시 고스트 4칸·바닥 19행·현재 블록과 같은 모양. 이동·회전 5가지 뒤 하드 드롭 고정 칸 = 직전 고스트 5/5. C: 홀드=현재, 새 블록=직전 미리보기, 미리보기 바뀜, 홀드 칸 흐림. 같은 블록 C 재입력 변화 없음. 고정 후 ㅊ(KeyC) 교환·미리보기 그대로. PAUSED·GAME_OVER C 무시(GAME_OVER 고스트 0). 이름 입력칸 c 입력('cat별님' 저장). 재시작 홀드 비움. 390px 가로 스크롤 없음. 콘솔 오류 0.

## 검증 도구 메모
- 블록 순서 고정이 필요하지만 Math.random 전체를 바꾸면 안 될 때(효과 난수 등): addScriptToEvaluateOnNewDocument로 `globalThis.TetrisGame` 대입을 가로채 startGame·lockPiece·restartGame에 순서용 random을 넘긴다(테스트 브라우저 안에서만).
- 헤드리스 Chrome + DevTools 프로토콜(Node 24 내장 WebSocket)로 클릭·키 입력·콘솔·390px·스크린샷 검증이 가능하다. 스크립트는 세션 scratchpad에만 두고 프로젝트 폴더에 넣지 않는다.
- 블록 종류 고정이 필요하면 `Page.addScriptToEvaluateOnNewDocument`로 테스트 브라우저 안에서만 `Math.random`을 바꾼다(프로젝트 코드 변경 없음).
- 헤드리스에서 합성 키 이벤트는 페이지를 스크롤하지 않는 것으로 보임 → 스크롤 방지는 `defaultPrevented`로만 확인 가능, 실제 스크롤은 사람 확인.
