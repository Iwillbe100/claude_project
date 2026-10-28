# STEP 2 — 페이지 구성안

> **한 줄 목적:** 화면을 어떻게 생기게 할지 **미리 그림으로 정한다.** 이 그림이 곧 시험 문제가 된다.
> **내가 결정할 것: 3개** · **코드 생성: 없음 (명세 문서만 바뀜)**

| 이전 | 다음 | 문서 규칙 | 결정 장부 |
| --- | --- | --- | --- |
| [STEP 1 — 입력과 취향](01_INPUT_AND_STYLE.md) | [STEP 3 — 정보량 카운트](03_INFORMATION_COUNT.md) | [00_INDEX](00_INDEX.md) | [00_DECISION_LOG](00_DECISION_LOG.md) |

---

## 읽기 1 — 이 STEP에서 정하는 것

여기서 그린 화면 그림이 **그대로 검사 항목이 됩니다.**

```text
STEP 2 에서 "도시를 누르면 우측 툴바가 열린다" 라고 적으면
   ↓
검사기가 "우측 툴바가 있는가 / 누르는 연결이 있는가" 를 실제로 봅니다
   ↓
없으면 FAIL → 루프가 다시 돕니다
```

**그러니 여기서 대충 적으면, 대충 만들어도 통과합니다.** 이 STEP이 결과물 품질을 결정합니다.

---

## 읽기 2 — 앞에서 물려받은 결정

<!-- PROJECT:BEGIN -->

| 물려받은 것 | 값 | 어디서 |
| --- | --- | --- |
| 국가 · 여행 일수 | 일본(오사카) · 4일 | `D-여행입력` |
| 스타일 갈래 | 3갈래 (preferred / not_preferred / detailed) | `D-취향분류` |

<!-- PROJECT:END -->

---

## 읽기 3 — 이미 정해 둔 것 (읽고 넘어가기)

| 항목 | 고정값 |
| --- | --- |
| 최종 산출물 | **`output/travel_site.html` 파일 하나** |
| CSS · JavaScript | 그 파일 **안에** 적는다. 바깥 파일을 만들지 않는다 |
| 화면 순서 | 기능1 → 기능2 → 기능3, 한 페이지에 위에서 아래로 |
| 이미지 | 인터넷 주소를 그대로 건다. 안 열리면 **대체 박스**를 보여 준다 |
| 평가하지 않는 것 | 얼마나 예쁜가 (사람 몫) |
| 평가하는 것 | 정해 둔 칸이 **있는가 · 눌리는가 · 내용이 들어갔는가** |

**화면에 붙이는 이름표 (고정)** — 검사기는 이 이름표를 보고 칸을 찾습니다.

```text
기능1  <section id="feature1">
       <img data-role="flag">              국기 (좌측 상단)
       <img data-role="hero">              대표 사진 (우측 상단)
       <button class="acc-header" data-acc="feature1" data-key="매력">
       <div    class="acc-panel"  data-acc="feature1" data-key="매력">

기능2  <section id="feature2">
       <button data-city="다낭">           도시 단추
       <aside  id="city-drawer">           우측 툴바
       <div    data-city-panel="다낭">     툴바 안 도시 칸
       <button data-spot="미케 비치">      관광지 단추
       <img    data-spot-image="미케 비치"> 관광지 사진
       <div    data-spot-detail="미케 비치"> 관광지 상세
       <div    data-preference-note="다낭"> 취향 설명 (<p> 줄로 씀)
       <button data-back>                  뒤로 가기

기능3  <section id="feature3">
       <button class="acc-header" data-acc="feature3" data-key="다낭">
       <div    class="acc-panel"  data-acc="feature3" data-key="다낭">
       <div    data-day="1">               1일차 칸 (도시 칸 **안에** 둔다)
       <li     data-block="09:00-11:30">   시간 블록
       <a      data-source href="...">     출처 링크 (권장 표기 · 검사기는 출처 주소 문자열만 대조)

탭을 고른 경우 (기능1 · 기능3)
       <button data-tab="매력">            탭 단추
       <div    data-tab-panel="매력">      탭 내용
```

> 이름표를 바꾸면 검사기가 못 찾습니다. **이름표는 고정, 배치만 내가 고릅니다.**
> (출처 링크의 `data-source` 만 예외 — 검사기는 모은 출처 주소가 화면 어딘가에 있는지를 봅니다.)

**어디에 두는가도 계약입니다 (고정)**

```text
도시 단추       기능2 구역 안, 툴바 **밖**   (여는 쪽이므로)
도시 칸         툴바 **안**
관광지 단추 · 상세 · 사진 · 취향 설명 · 뒤로 가기   전부 툴바 **안**
```

> 이름표만 있으면 어디에 있든 통과하던 때가 있었습니다. 그래서 **전부 펼쳐진
> 평면 문서에 빈 껍데기 툴바 하나**가 만점을 받았습니다. 지금은 검사기가
> 툴바 안으로 범위를 좁혀서 찾습니다 — 기능3이 이미 하던 방식과 같습니다.

**처음에는 닫혀 있어야 합니다 (고정)**

```text
우측 툴바 · 관광지 상세 · 아코디언 패널   처음에 닫힘
탭 내용                                  한 칸만 보임

닫는 방법 세 가지 중 아무거나
   hidden 속성          <aside id="city-drawer" hidden>
   인라인 스타일         style="display:none"
   CSS 클래스           .acc-panel{display:none}   (파일 안 <style> 에서 찾습니다)
```

> 열고 닫는 배치인데 처음부터 다 펼쳐져 있으면, 그건 아코디언이 아니라 목차이고
> 단추는 장식입니다. 이름표만으로는 그 둘을 구분할 수 없어서 이 검사를 둡니다.

**연결은 코드로 있어야 합니다 (고정)**

```text
안 됩니다   /* data-city data-spot data-back */          주석은 코드가 아닙니다
안 됩니다   var x = "data-city";                          쓰이지 않는 문자열
됩니다      e.target.closest('button[data-city]')
됩니다      document.getElementById('city-drawer')
```

> 검사기는 `<script>` 에서 주석을 지운 뒤, 그 이름표가 `querySelector` ·
> `closest` · `getElementById` 같은 **DOM 질의 안에서** 쓰였는지 봅니다.

**기능3은 도시마다 따로 완결됩니다 (고정)**

```text
이 페이지는 "며칠을 어떻게 돌까"가 아니라 "어느 도시로 갈까"를 돕습니다.

  다낭 칸     여행 일수만큼의 일정 전체
  호이안 칸   여행 일수만큼의 일정 전체
  후에 칸     여행 일수만큼의 일정 전체
        └── 셋을 나란히 놓고 내가 한 도시를 고릅니다
```

> 그래서 `data-day` 칸은 **도시 칸 안에** 있어야 합니다.
> 화면 전체에서 한 번에 세면 "한 도시에 몰아 넣은 일정"도 통과해 버립니다.
> 검사기는 도시 칸 안으로 범위를 좁혀 **도시마다** 셉니다.

**하루는 시간 블록으로 씁니다 (고정)**

```text
<div data-day="1">
  <li data-block="09:00-11:30"> 오전 · 명소 · 왜 넣었는지
  <li data-block="12:00-13:00"> 점심 · 식사
  <li data-block="13:30-17:00"> 오후 · 명소
  <li data-block="18:30-20:30"> 저녁 · 식사
```

> `data-block` 값은 **`HH:MM-HH:MM`** 입니다. 오전·오후 두 덩어리로 나눈 일정은
> "몇 시에 무엇을"이 없어 실제로 쓸 수 없습니다. 하루 최소 블록 수는 계약에 있습니다.

**기능1 헤더에 무엇이 들어가나 (고정)** — STEP 3에서 모을 정보가 여기로 들어갑니다.

| 아코디언 헤더 | 채우는 정보 슬롯 |
| --- | --- |
| 매력 | `매력` |
| 역사 | `역사` |
| 문화 | `문화` + `주의사항` (문화적으로 조심할 점) |
| 국가상태 | `국가상태` — 지금 알려진 것이 없으면 **"확인했으나 특별한 내용 없음"**이라고 적는다 |
| 여행정보 | `항공권가격` + `환율` + `교통개요` |

> 헤더는 5개, 정보 슬롯은 8개입니다. **한 헤더에 여러 슬롯이 들어갈 수 있습니다.**
> 어느 슬롯이 어디로 가는지 정해 두지 않으면 루프가 추측하게 되고, 빠뜨리는 칸이 생깁니다.

---

## 읽기 4 — 내가 결정할 질문

<!-- FIXED:BEGIN -->

| 결정 ID | 질문 | 이 값이 바꾸는 것 |
| --- | --- | --- |
| `D-페이지구성` | 기능 1·2·3을 각각 **어떤 배치**로 보여 주나? | 검사기가 찾을 칸의 모양 |
| `D-디자인요구` | 색과 글꼴을 어떻게 하나? | 화면 분위기 (검사는 안 함) |
| `D-취향설명분량` | 도시마다 취향 설명을 **몇 줄 이상** 쓰나? | 검사기가 세는 줄 수 |

**쉬운 선택지**

| 결정 ID | A | B | C | 권장 |
| --- | --- | --- | --- | --- |
| `D-페이지구성` | 아코디언 · 우측 툴바 · 아코디언<br>`accordion` `drawer` `accordion` | 탭 · 우측 툴바 · 아코디언<br>`tabs` `drawer` `accordion` | 셋 다 아코디언 (툴바 없음)<br>`accordion` `accordion` `accordion`<br>**+ `back_button` 을 `false` 로** | **A** |
| `D-디자인요구` | 밝은 배경 · 파랑 강조 | 어두운 배경 · 청록 강조 | 직접 지정 | **A** |
| `D-취향설명분량` | 10줄 | 15줄 | 20줄 | **B** |

**아코디언 · 툴바 · 탭이 뭔가요?**

```text
아코디언   제목을 누르면 아래로 스르륵 펼쳐지고, 다시 누르면 접힌다     accordion
우측 툴바  도시를 누르면 오른쪽에서 서랍처럼 밀려 나온다 (관광지 목록)   drawer
탭         위에 단추가 나란히 있고, 누르면 아래 내용만 바뀐다           tabs
```

> **계약에는 오른쪽의 영어 값을 적습니다.** 표의 한글 문구를 그대로 옮겨 적으면
> 검사기가 그 배치를 알아보지 못합니다. 실제로 `"우측 툴바"` 라고 적었더니
> **툴바 검사 6개가 통째로 사라졌는데 판정은 PASS** 였던 일이 있습니다.

> **툴바와 뒤로 가기는 한 쌍입니다.** 뒤로 가기는 *툴바에서 도시 목록으로* 돌아가는
> 단추입니다. 그래서 `drawer` 를 고르지 않으면 돌아갈 곳이 없습니다.
>
> `MASTER_SPEC.md` 의 골격은 권장값 **A** 를 전제로 `back_button` 이 `true` 로
> 적혀 있습니다. **선택지 C 를 고르면 그 줄도 `false` 로 바꿉니다.** 그대로 두면
> 계약 검증이 이렇게 막습니다 (틀린 채로 진행되지는 않습니다).
>
> ```text
> page_contract.feature2: 툴바가 없는 배치(accordion)인데 back_button 이 true 입니다
>   — 돌아갈 곳이 없는 뒤로 가기 단추를 요구하게 됩니다
> ```
>
> 같은 이유로, 아래 `dom_contract.feature2` 의 `aside#city-drawer` 와
> `button[data-back]` 은 **`drawer` 를 골랐을 때만** 만드는 것입니다. 나머지
> 이름표(`button[data-city]` · `div[data-spot-detail]` 등)는 배치와 무관하게
> 전부 필요하고, 검사기도 배치와 무관하게 찾습니다.
> 지금은 허용값이 아니면 `ERROR`(exit 1)로 멈추므로 조용히 넘어가지 않습니다.

> `D-취향설명분량`은 **"박물관은 취향이 아니어서 뺐습니다"** 같은 설명을 몇 줄 쓸지입니다.
> 10줄이면 얕고, 20줄이면 길어서 루프가 오래 돕니다. **15줄이 적당합니다.**

<div></div>

> **줄 수만 정하면 같은 문장을 복사해서 채웁니다.** 실제로 그런 일이 있었습니다 —
> 30줄을 요구했더니 9줄만 내용이 있고 21줄은 번호만 바꾼 같은 문장이었습니다.
> 그래서 킷이 두 가지를 **고정으로** 함께 검사합니다. 이건 고르지 않습니다.
>
> ```text
> 줄마다 최소 글자 수      계약의 min_chars.preference_note_line
> 서로 다른 줄의 비율      계약의 dedup.min_unique_line_ratio
> ```
>
> 숫자를 키우면 **내용이 늘어나는 것이 아니라 복제가 늘어납니다.** 그래서 줄 수는 그대로 두고
> 줄의 질을 검사합니다.

<!-- FIXED:END -->

---

## 읽기 5 — 내 답 적기

<!-- ANSWERS:BEGIN -->

### `D-페이지구성`
- 고른 것: A (아코디언 · 우측 툴바 · 아코디언)
- 직접 쓰고 싶다면:

### `D-디자인요구`
- 고른 것: B (어두운 배경 · 청록 강조)
- 직접 쓰고 싶다면:

### `D-취향설명분량`
- 고른 것: B (15줄)
- 직접 쓰고 싶다면:

<!-- ANSWERS:END -->

---

## 읽기 6 — Claude가 정리한 결과

<!-- PROJECT:BEGIN -->

| 결정 ID | 확정 값 | 고른 이유 | 승인 시각 |
| --- | --- | --- | --- |
| `D-페이지구성` | 기능1 `accordion` · 기능2 `drawer` · 기능3 `accordion` | 권장값. 도시 목록에서 서랍으로 관광지를 보는 흐름이 명확함 | 2026-10-23 |
| `D-디자인요구` | 어두운 배경(dark) · 청록 강조(#14B8A6) | 교육생 선택 B. 청록 색상값은 가정(결정 장부 3번) | 2026-10-23 |
| `D-취향설명분량` | 도시마다 15줄 이상 | 권장값. 적당한 깊이 | 2026-10-23 |

**확정된 화면 그림**

| 기능 | 무엇이 보이나 | 배치 | 눌렀을 때 |
| --- | --- | --- | --- |
| 기능1 국가 소개 | 국기(좌상단) · 대표 사진(우상단) · 헤더 5개(매력·역사·문화·국가상태·여행정보) | 아코디언 | 헤더를 누르면 해당 내용이 펼쳐지고 다시 누르면 접힘 (처음엔 닫힘) |
| 기능2 도시·관광지 | 도시 단추(오사카) → 우측 툴바에 관광지 단추·사진·상세·취향 설명(15줄 이상) | 우측 툴바 | 도시를 누르면 툴바가 열리고, 관광지를 누르면 상세가 열리며, 뒤로 가기로 도시 목록에 돌아옴 |
| 기능3 도시별 일정 | 도시마다 4일치 일정, 하루는 `HH:MM-HH:MM` 시간 블록과 출처 링크 | 아코디언 | 도시 헤더를 누르면 그 도시의 4일 일정이 펼쳐짐 (처음엔 닫힘) |

<!-- MACHINE:BEGIN -->
```json
{
  "step": 2,
  "produces": "spec_only",
  "decisions": {
    "D-페이지구성": {
      "feature1": {"layout": "accordion", "flag_image": true, "hero_image": true},
      "feature2": {"layout": "drawer", "spot_detail": true, "back_button": true},
      "feature3": {"layout": "accordion"}
    },
    "D-디자인요구": {"mode": "dark", "primary": "#14B8A6"},
    "D-취향설명분량": 15
  },
  "fixed": {
    "output_file": "output/travel_site.html",
    "single_file": true,
    "feature_order": ["feature1", "feature2", "feature3"],
    "feature1_headers": ["매력", "역사", "문화", "국가상태", "여행정보"],
    "feature1_header_slots": {
      "매력": ["매력"],
      "역사": ["역사"],
      "문화": ["문화", "주의사항"],
      "국가상태": ["국가상태"],
      "여행정보": ["항공권가격", "환율", "교통개요"]
    },
    "image_policy": "주소를 손으로 만들지 않는다. 조회로 얻고 열어 본 뒤 건다. 실패하면 대체 박스",
    "feature3_rule": "일정은 도시마다 따로 완결된다. data-day 는 도시 칸 안에 둔다",
    "time_block_format": "HH:MM-HH:MM",
    "layout_values": {
      "feature1": ["accordion", "tabs"],
      "feature2": ["drawer", "accordion"],
      "feature3": ["accordion", "tabs"]
    },
    "scope_rule": "도시 단추는 툴바 밖, 도시 칸부터 뒤로 가기까지는 툴바 안",
    "closed_rule": "툴바·관광지 상세·아코디언 패널은 처음에 닫혀 있어야 한다",
    "dom_contract": {
      "feature1": ["section#feature1", "img[data-role=flag]", "img[data-role=hero]"],
      "feature2": ["section#feature2", "button[data-city]", "aside#city-drawer",
                   "button[data-spot]", "img[data-spot-image]",
                   "div[data-spot-detail]", "div[data-preference-note]",
                   "button[data-back]"],
      "feature3": ["section#feature3", "div[data-day]", "li[data-block]"]
    },
    "not_evaluated": "얼마나 예쁜가"
  },
  "inherited": {
    "country": "일본",
    "days": 4,
    "style_slots": ["preferred", "not_preferred", "detailed"]
  }
}
```
<!-- MACHINE:END -->

<!-- EXAMPLE:BEGIN -->
> **[작성 예시 — 실제 결정이 아닙니다]**
>
> ```json
> "D-페이지구성": {
>   "feature1": {"layout": "accordion", "flag_image": true, "hero_image": true},
>   "feature2": {"layout": "drawer", "spot_detail": true, "back_button": true},
>   "feature3": {"layout": "accordion"}
> },
> "D-디자인요구": {"mode": "light", "primary": "#1F6FEB"},
> "D-취향설명분량": 15
> ```
<!-- EXAMPLE:END -->

<!-- PROJECT:END -->

---

## 읽기 7 — 이 STEP이 끝나면 무엇이 진행되는가

| 항목 | 내용 |
| --- | --- |
| **지금 코드가 만들어지나?** | **아니오.** 화면 그림만 문서로 확정합니다. |
| **Claude가 실제로 하는 일** | ① 배치를 기능별로 정리 → ② 읽기 6의 화면 그림 표 채우기 → ③ 결정 장부에 추가 → ④ STEP 3·4·5·7의 물려받은 값 갱신 |
| **바뀌는 파일** | `specs/02_PAGE_DESIGN.md` · `specs/00_DECISION_LOG.md` · `PROJECT_MEMORY.md` · `specs/03_INFORMATION_COUNT.md` · `specs/04_BOUNDARY_TASKS_SAFETY.md` · `specs/05_TEST_AND_VERIFIER.md` · `specs/07_EXECUTION_CONTRACT.md` |
| **내가 지금 실행할 명령** | Claude Code에 `STEP 2 진행해줘` → 질문에 답 → `python scripts/validate_specs.py --step 2` |

---

## 읽기 8 — 완료 확인과 다음 명령

- [ ] 기능 1·2·3의 배치가 각각 정해졌다
- [ ] 취향 설명 줄 수가 **숫자**다
- [ ] 화면 그림 표에 "눌렀을 때 무엇이 일어나는가"가 적혀 있다
- [ ] 기능3이 **도시마다 따로** 일정을 갖는다는 것을 확인했다
- [ ] 배치를 **계약값**(`accordion` / `drawer` / `tabs`)으로 적었다
- [ ] 상태가 `APPROVED`다

```bash
python scripts/validate_specs.py --step 2
```

<!-- STATUS:BEGIN -->
STATUS: APPROVED
<!-- STATUS:END -->

```text
STEP 3 진행해줘
```
