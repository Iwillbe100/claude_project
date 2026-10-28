# MASTER_SPEC.md — 승인된 결정 통합본

이 파일은 **직접 쓰는 문서가 아닙니다.** STEP 7에서 STEP 1~6의 승인된 결정을 모아 채웁니다.

**검사 스크립트는 숫자를 스스로 갖지 않습니다. 전부 이 파일에서 읽습니다.**

```text
MASTER_SPEC.md  count_contract / page_contract / quality_contract
        │  읽음
        ├──▶  scripts/check_information_count.py   루프 A 판정
        ├──▶  scripts/check_page_contract.py       루프 B 판정
        ├──▶  scripts/check_quality_passes.py      루프 C 판정
        └──▶  scripts/verify_all.py                최종 스위치 (A → B → C)
```

---

## 0. 현재 상태

<!-- PROJECT:BEGIN -->

```text
상태: 완성 (STEP 1~7 승인 · 결정 21 / 21 · 2026-10-23)
```

STEP 1~7의 승인된 결정을 아래 2·4번에 모았습니다.

<!-- PROJECT:END -->

---

## 1. 이 파일은 어떻게 만들어지는가

1. STEP 1~6의 상태가 모두 `APPROVED`인지 확인한다.
2. 각 STEP 문서의 `MACHINE` JSON 블록을 읽는다.
3. 아래 2·3·4번을 채우고 0번의 "미완성" 표시를 지운다.
4. **값을 만들어 내지 않는다.** 승인된 결정에 없는 내용은 빈칸으로 남긴다.
5. 채운 뒤 `python scripts/check_loop_readiness.py`를 실행한다.

> 4번의 `null`은 **교육생이 고르는 값**입니다. 숫자가 이미 적혀 있는 칸은 **킷이 정한 고정값**이므로
> 건드리지 않습니다. 어느 쪽인지는 아래 3번 표에서 구분합니다.

---

## 2. 결정 21개 통합표

<!-- PROJECT:BEGIN -->

| STEP | 결정 ID | 확정 값 | 이 값을 쓰는 곳 |
| --- | --- | --- | --- |
| 1 | `D-여행입력` | 일본(오사카) · 4일 (11/13~16) | 검색어 · 도시마다의 일정 칸 수 |
| 1 | `D-취향분류` | 3갈래 (preferred / not_preferred / detailed) | 도시·관광지 고르는 잣대 |
| 1 | `D-도시선정기준` | 1등 내 취향 · 2등 유명도 · 3등 교통 | 어느 도시가 뽑히는가 |
| 2 | `D-페이지구성` | 기능1 accordion · 기능2 drawer · 기능3 accordion | 화면 계약 |
| 2 | `D-디자인요구` | dark · 청록 #14B8A6 | 색·글꼴 |
| 2 | `D-취향설명분량` | 도시마다 15줄 이상 | 취향 설명 줄 수 검사 |
| 3 | `D-도시수` | 1 (오사카) | 카운트 계약 |
| 3 | `D-명소수` | 3 | 카운트 계약 |
| 3 | `D-소개근거수` | 3 | 카운트 계약 |
| 3 | `D-일정근거수` | 2 | 카운트 계약 |
| 4 | `D-작업목록` | 권장 7개 (A 5 · B 2) | 반복 단위 |
| 4 | `D-수정금지파일` | specs/** scripts/** templates/** CLAUDE.md MASTER_SPEC.md LOOP_CONTRACT.md | 보호 범위 선언 (잠금은 킷 고정 28개) |
| 4 | `D-사람확인지점` | 루프 A 끝 · B 끝 · C 끝 | 되물음 지점 |
| 5 | `D-정보량테스트` | 개수와출처와분량 | 루프 A 깐깐함 |
| 5 | `D-페이지테스트` | 내용대조 | 루프 B 깐깐함 |
| 5 | `D-최종검증명령` | python scripts/verify_all.py | 종료 스위치 |
| 6 | `D-정보루프반복` | 3바퀴 | 루프 A 상한 |
| 6 | `D-페이지루프반복` | 3바퀴 | 루프 B 상한 |
| 6 | `D-무진전기준` | 같은 오류 2회 | 제자리걸음 감지 |
| 7 | `D-성공조건` | verify_all.py exit 0 + 사람이 브라우저로 열어 확인 | 성공 판정 |
| 7 | `D-최대반복` | 10번 | 전체 상한 |

<!-- PROJECT:END -->

---

## 3. 고정 설계 요약 (교육생이 정하지 않는 것)

| 항목 | 값 | 출처 |
| --- | --- | --- |
| 필수 입력 | 국가 · 여행 일수 · 여행 스타일 | STEP 1 |
| 출처 등급 | 따지지 않는다. 블로그·카페도 쓴다 | STEP 1 |
| 최종 산출물 | `output/travel_site.html` 파일 하나 | STEP 2 |
| 화면 이름표 | `data-*` 계약 (검사기가 이걸로 찾는다) | STEP 2 |
| 데이터 특성 | `다건` `단건` `조건부` `자산` | STEP 3 |
| 저장 위치 | `output/research_data.json` | STEP 3 |
| **분량 하한** | 근거 60자 · 관광지 상세 300자 · 도시 선정 이유 120자 · 취향 설명 줄당 30자 · 일정 블록 이유 40자 | STEP 3 |
| **중복 상한** | 취향 설명 고유 줄 90% · 두 글 사이 유사도 60% | STEP 3 |
| **자산 유효성** | `verified` 기록 필수 · `upload.wikimedia.org` 주소 금지 (thumb·원본 모두 — `Special:FilePath` 형태만) | STEP 3 |
| **일정 단위** | 도시마다 `days` 일 · 하루 4블록 이상 · `HH:MM` | STEP 3 |
| 루프 개수와 순서 | A(정보량) → B(페이지) → C(정성 완성도) | STEP 4 |
| 검사기 소유 | 킷이 제공. `scripts/**` 수정 금지 | STEP 5 |
| 종료 코드 | 0 PASS · 1 ERROR · 2 SHORT | STEP 5 |
| **루프 C 반복** | **3회 고정. 최소이자 최대** | STEP 6 |
| **정성 규율** | 10가지. `specs/QUALITY_RUBRIC.md` | STEP 6 |
| 실패 라우팅 | 7종 고정표 | STEP 6 |
| 종료 상태 | 7가지 | STEP 7 |

---

## 4. 검사 계약 (스크립트가 읽는 곳)

<!-- MACHINE:BEGIN -->
```json
{
  "source": "specs/*.md 의 MACHINE 블록",
  "request": {
    "country": "일본",
    "days": 4,
    "style": {
      "preferred": ["맛집", "휴식", "쇼핑"],
      "not_preferred": ["여행일정에서 많이 걸어야하는건 싫어"],
      "detailed": ["오사카-고베를 갈꺼야. 고베마라톤에 참가하면서 겸사겸사 가는거야", "11/15일 대회야. 대회를 뛰어야해서 여행일정에서 많이 걸어야하는건 싫어", "여행 일정은 11/13~16(3박4일)", "오사카 여행 나는 숙소를 시티프라자오사카로 잡았어 11/13~16까지 쭉 맞춰서 일정 다시 짜줘", "11/13 8:05분 출발 09:50도착해서 11/16 23:25~01:40으로 복귀하는 일정이야", "오사카 일정으로 하면 될거같아 고베일정은 지워줘"]
    },
    "city_priority": ["내 취향", "유명도", "교통"]
  },
  "count_contract": {
    "strictness": "개수와출처와분량",
    "distinct_source_mode": "url",
    "min_chars": {
      "evidence_item": 60,
      "spot_detail": 300,
      "why_selected": 120,
      "preference_note_line": 30,
      "itinerary_block_why": 40
    },
    "dedup": {
      "min_unique_line_ratio": 0.9,
      "max_pair_similarity": 0.6,
      "shingle_size": 8
    },
    "asset_rule": {
      "require_verified": true,
      "verified_fields": ["status", "content_type", "checked_at"],
      "allowed_status": [200],
      "content_type_prefix": "image/",
      "banned_url_substrings": ["upload.wikimedia.org"],
      "recommended_form": "https://commons.wikimedia.org/wiki/Special:FilePath/<파일명>?width=1024"
    },
    "country_intro": {
      "매력":       {"kind": "다건", "target": 3, "distinct_sources": 2},
      "역사":       {"kind": "다건", "target": 3, "distinct_sources": 2},
      "문화":       {"kind": "다건", "target": 3, "distinct_sources": 2},
      "주의사항":   {"kind": "다건", "target": 3, "distinct_sources": 2},
      "국가상태":   {"kind": "조건부", "target": 1},
      "항공권가격": {"kind": "단건", "target": 1},
      "환율":       {"kind": "단건", "target": 1},
      "교통개요":   {"kind": "단건", "target": 1},
      "국기이미지": {"kind": "자산", "target": 1},
      "대표이미지": {"kind": "자산", "target": 1}
    },
    "cities": {
      "city_count": 1,
      "spots_per_city": 3,
      "evidence_per_spot": {"kind": "다건", "target": 3, "distinct_sources": 2},
      "image_per_spot": {"kind": "자산", "target": 1},
      "preference_note_min_lines": 15
    },
    "itinerary": {
      "evidence_per_city": {"kind": "다건", "target": 2, "distinct_sources": 2},
      "days_per_city": 4,
      "blocks_per_day_min": 4,
      "spot_blocks_per_day_min": 1,
      "time_format": "HH:MM",
      "block_kinds": ["명소", "식사", "이동", "휴식"]
    }
  },
  "page_contract": {
    "output_file": "output/travel_site.html",
    "single_file": true,
    "strictness": "내용대조",
    "min_chars": {
      "panel_floor": 60,
      "conditional_slot_chars": 20
    },
    "feature1": {
      "layout": "accordion",
      "flag_image": true,
      "hero_image": true,
      "headers": ["매력", "역사", "문화", "국가상태", "여행정보"],
      "header_slots": {
        "매력": ["매력"],
        "역사": ["역사"],
        "문화": ["문화", "주의사항"],
        "국가상태": ["국가상태"],
        "여행정보": ["항공권가격", "환율", "교통개요"]
      }
    },
    "feature2": {
      "layout": "drawer",
      "spot_images": true,
      "spot_detail": true,
      "back_button": true,
      "preference_note_min_lines": 15
    },
    "feature3": {
      "layout": "accordion",
      "per_city_days": true,
      "time_blocks": true
    },
    "theme": {"mode": "dark", "primary": "#14B8A6"}
  },
  "quality_contract": {
    "passes": 3,
    "rubric_file": "specs/QUALITY_RUBRIC.md",
    "record_dir": "evidence/runs/<run_id>/quality",
    "record_template": "templates/QUALITY_PASS.md",
    "regression_command": "python scripts/verify_all.py --skip-quality",
    "watch_files": ["output/research_data.json", "output/travel_site.html"],
    "rules": [
      "Q-반복금지", "Q-취향연결", "Q-뺀이유", "Q-상세삼요소", "Q-일정현실성",
      "Q-근거일치", "Q-도시차별화", "Q-동행반영", "Q-실용누락", "Q-계약무결"
    ],
    "pass_focus": {
      "1": ["Q-반복금지", "Q-취향연결", "Q-뺀이유", "Q-상세삼요소"],
      "2": ["Q-일정현실성", "Q-근거일치", "Q-도시차별화", "Q-실용누락"],
      "3": ["Q-동행반영", "Q-계약무결"]
    }
  },
  "loops": {
    "A": {"name": "정보량 충족", "limit": 3,
          "verifier": "python scripts/check_information_count.py"},
    "B": {"name": "페이지 완성", "limit": 3,
          "verifier": "python scripts/check_page_contract.py"},
    "C": {"name": "정성 완성도", "limit": 3,
          "verifier": "python scripts/check_quality_passes.py"}
  },
  "options": {
    "same_error_limit": 2,
    "max_iterations": 10,
    "final_verifier_command": "python scripts/verify_all.py",
    "success_condition": "python scripts/verify_all.py exit 0 + 사람이 브라우저로 열어 확인"
  }
}
```
<!-- MACHINE:END -->

> **허용값이 정해진 칸이 있습니다.** `strictness` 두 개, `count_contract.distinct_source_mode`, 세 개의 `layout` 이 그렇습니다.
> 여기에 선택지 문구(예: `"우측 툴바"`)를 적으면 검사기는 `ERROR`를 냅니다 —
> 예전에는 그 자리의 검사가 조용히 사라졌습니다.
>
> ```text
> count_contract.strictness   개수만 · 개수와출처 · 개수와출처와분량
> count_contract.distinct_source_mode   url · host
> page_contract.strictness    요소존재 · 동작연결 · 내용대조
> feature1.layout             accordion · tabs
> feature2.layout             drawer · accordion
> feature3.layout             accordion · tabs
> ```
>
> **칸을 통째로 지우는 것도 막습니다.** 지우면 검사기가 자기 안의 기본값으로
> 되돌아가서, "검사기는 숫자를 스스로 갖지 않는다"는 이 파일의 약속이 깨집니다.
>
> `null`이 하나라도 남아 있으면 검사기는 `ERROR`를 냅니다.
> 이것은 "덜 만들었다"가 아니라 **"명세가 아직 안 끝났다"**는 뜻입니다.
> 숫자가 이미 적힌 칸(`min_chars`, `dedup`, `asset_rule`, `blocks_per_day_min`,
> `quality_contract`, `loops.C.limit`)은 **킷 고정값**이므로 고치지 않습니다.
> 예외 둘 — `page_contract.theme` 과 `feature2.back_button` 은 권장값 **A** 로 미리 채워 둔
> 칸입니다. STEP 2 에서 `D-디자인요구` · `D-페이지구성` 으로 다른 값을 고르면 이 두 칸을 덮어씁니다
> (`theme` 은 화면 분위기라 검사기가 대조하지 않습니다 — 고른 값을 옮겨 적는 것을 잊지 않습니다).

---

## 5. 이 파일이 완성되었는지 확인

```bash
python scripts/check_loop_readiness.py
```

`MASTER_SPEC / LOOP_CONTRACT / loop_state 준비` 항목이 `[OK]`가 되면 완성입니다.
