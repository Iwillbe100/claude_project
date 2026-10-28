#!/usr/bin/env python3
"""셀프테스트가 쓰는 **아주 작은 합격 세계**를 만든다. 킷 소유 — 수정 금지.

검사기를 검사하려면 먼저 "이건 통과해야 한다"는 기준점이 있어야 한다.
그 기준점을 실제 여행 데이터로 만들면 너무 크고, 무엇이 왜 통과했는지 안 보인다.
그래서 여기서는 **도시 1개 · 관광지 1곳 · 1일 · 하한 10자짜리 최소 세계**를 만든다.

  contract()   계약 (양쪽 킷 형식으로 다 써 둔다)
  research()   그 계약을 딱 맞게 채운 수집 결과
  page()       그 수집 결과를 딱 맞게 담은 화면
  quality()    정성 1회차 기록

이 셋은 서로 맞물려 있다. 하나만 어긋나도 그 자리의 검사행이 빨간불이 되어야 하고,
그것을 확인하는 것이 `run_selftest.py` 가 하는 일이다.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

LONG = "이 문장은 최소 글자 수를 넘기기 위한 설명이며 실제 조사 내용을 대신한다"


def contract(feature2_layout: str = "drawer") -> dict:
    """검사가 성립하는 최소 계약. 하한을 낮췄을 뿐 모양은 진짜와 같다.

    `feature2_layout` 으로 **선택지 C 세계**(툴바 없이 셋 다 아코디언)를 만든다.
    예전에는 이 값이 `drawer` 로 못 박혀 있어서 자체 검사 전체가 툴바 세계만
    밟았고, 그래서 "아코디언일 때만 사라지는 검사" 두 개가 살아남았다.
    툴바가 없으면 돌아갈 곳도 없으므로 `back_button` 도 함께 내린다.
    """
    return {
        "request": {
            "country": "테스트국", "days": 1,
            "style": {"preferred": ["역사"], "not_preferred": [], "detailed": ["걷기"]},
            "city_priority": ["역사"],
        },
        "count_contract": {
            "strictness": "개수와출처와분량",
            "distinct_source_mode": "url",
            "min_chars": {
                "evidence_item": 10, "spot_detail": 10, "why_selected": 10,
                "preference_note_line": 5, "itinerary_block_why": 5,
            },
            "dedup": {"min_unique_line_ratio": 0.9, "max_pair_similarity": 0.6,
                      "shingle_size": 8},
            "asset_rule": {
                "require_verified": True,
                "verified_fields": ["status", "content_type", "checked_at"],
                "allowed_status": [200], "content_type_prefix": "image/",
                "banned_url_substrings": ["/thumb/"],
                "recommended_form": "https://example.test/img/<파일명>",
            },
            "country_intro": {
                "매력": {"kind": "다건", "target": 1, "distinct_sources": 1},
                "역사": {"kind": "다건", "target": 1, "distinct_sources": 1},
                "문화": {"kind": "다건", "target": 1, "distinct_sources": 1},
                "주의사항": {"kind": "다건", "target": 1, "distinct_sources": 1},
                "국가상태": {"kind": "조건부", "target": 1},
                "항공권가격": {"kind": "단건", "target": 1},
                "환율": {"kind": "단건", "target": 1},
                "교통개요": {"kind": "단건", "target": 1},
                "국기이미지": {"kind": "자산", "target": 1},
                "대표이미지": {"kind": "자산", "target": 1},
            },
            "cities": {
                "city_count": 1, "spots_per_city": 1,
                "evidence_per_spot": {"kind": "다건", "target": 1, "distinct_sources": 1},
                "image_per_spot": {"kind": "자산", "target": 1},
                "preference_note_min_lines": 2,
            },
            "itinerary": {
                "evidence_per_city": {"kind": "다건", "target": 1, "distinct_sources": 1},
                "days_per_city": 1, "blocks_per_day_min": 2,
                "spot_blocks_per_day_min": 1, "time_format": "HH:MM",
                "block_kinds": ["명소", "식사", "이동", "휴식"],
            },
        },
        "page_contract": {
            "output_file": "output/travel_site.html", "single_file": True,
            "strictness": "내용대조",
            "min_chars": {"panel_floor": 10, "conditional_slot_chars": 5},
            "feature1": {
                "layout": "accordion", "flag_image": True, "hero_image": True,
                "headers": ["매력", "역사", "문화", "국가상태", "여행정보"],
                "header_slots": {
                    "매력": ["매력"], "역사": ["역사"],
                    "문화": ["문화", "주의사항"], "국가상태": ["국가상태"],
                    "여행정보": ["항공권가격", "환율", "교통개요"],
                },
            },
            "feature2": {"layout": feature2_layout, "spot_images": True,
                         "spot_detail": True,
                         "back_button": feature2_layout == "drawer",
                         "preference_note_min_lines": 2},
            "feature3": {"layout": "accordion", "per_city_days": True, "time_blocks": True},
            "theme": {"mode": "light", "primary": "#1F6FEB"},
        },
        "quality_contract": {
            "passes": 1,
            "rubric_file": "specs/QUALITY_RUBRIC.md",
            "record_dir": "evidence/runs/<run_id>/quality",
            "record_template": "templates/QUALITY_PASS.md",
            "regression_command": "python scripts/verify_all.py --skip-quality",
            "watch_files": ["output/research_data.json", "output/travel_site.html"],
            "rules": ["Q-반복금지", "Q-취향연결"],
            "pass_focus": {"1": ["Q-반복금지", "Q-취향연결"]},
        },
        "loops": {
            "A": {"name": "정보량 충족", "limit": 3,
                  "verifier": "python scripts/check_information_count.py"},
            "B": {"name": "페이지 완성", "limit": 3,
                  "verifier": "python scripts/check_page_contract.py"},
            "C": {"name": "정성 완성도", "limit": 1,
                  "verifier": "python scripts/check_quality_passes.py"},
        },
        "options": {"same_error_limit": 2, "max_iterations": 20,
                    "final_verifier_command": "python scripts/verify_all.py",
                    "success_condition": "verify_all exit 0"},
    }


def _asset(name):
    return {"url": "https://example.test/img/" + name + ".png", "alt": name + " 사진",
            "verified": {"status": 200, "content_type": "image/png",
                         "checked_at": "2026-01-01T00:00:00"}}


def _evidence(tag, number):
    return {"text": tag + " " + str(number) + " " + LONG,
            "source_url": "https://" + tag + ".example.test/" + str(number)}


def research() -> dict:
    """위 계약을 **딱 맞게** 채운 수집 결과."""
    intro = {}
    for name in ("매력", "역사", "문화", "주의사항"):
        intro[name] = {"items": [_evidence(name, 1)]}
    intro["국가상태"] = {"checked": True, "items": [_evidence("국가상태", 1)]}
    for name in ("항공권가격", "환율", "교통개요"):
        intro[name] = {"items": [_evidence(name, 1)]}
    intro["국기이미지"] = {"asset": _asset("flag")}
    intro["대표이미지"] = {"asset": _asset("hero")}

    spot = {
        "name": "테스트명소",
        "detail": "관광지 상세 설명 " + LONG,
        "items": [_evidence("명소", 1)],
        "image": _asset("spot"),
    }
    city = {
        "name": "테스트시",
        "why_selected": "이 도시를 고른 이유 " + LONG,
        "spots": [spot],
        "preference_note": ("걷기 좋은 동선이라 넣었다\n"
                            "체험형 프로그램은 취향이 아니라 뺐다"),
        "itinerary": {
            "items": [_evidence("일정", 1)],
            "days": [{
                "day": 1,
                "blocks": [
                    {"start": "09:00", "end": "11:00", "kind": "명소",
                     "spot": "테스트명소", "why": "오전에 한적해서 넣었다"},
                    {"start": "12:00", "end": "13:00", "kind": "식사",
                     "place": "테스트식당", "why": "명소 바로 옆이라 넣었다"},
                ],
            }],
        },
    }
    return {"country": "테스트국", "days": 1, "country_intro": intro, "cities": [city]}


CSS = (".acc-panel{display:none}.acc-panel.open{display:block}"
       ".drawer{position:fixed;right:0}")

JS = """
document.addEventListener('click', function (e) {
  var acc = e.target.closest('.acc-header[data-acc]');
  if (acc) {
    var p = document.querySelector('.acc-panel[data-acc="' + acc.getAttribute('data-acc')
      + '"][data-key="' + acc.getAttribute('data-key') + '"]');
    if (p) { p.classList.toggle('open'); }
    return;
  }
  var city = e.target.closest('button[data-city]');
  if (city) {
    document.querySelectorAll('[data-city-panel]').forEach(function (x) { x.hidden = false; });
    var drawer = document.getElementById('city-drawer');
    if (drawer) { drawer.hidden = false; }
    return;
  }
  var spot = e.target.closest('button[data-spot]');
  if (spot) {
    var box = document.querySelector('[data-spot-detail="' + spot.getAttribute('data-spot') + '"]');
    if (box) { box.hidden = !box.hidden; }
    return;
  }
  if (e.target.closest('[data-back]')) {
    var back = document.getElementById('city-drawer');
    if (back) { back.hidden = true; }
  }
});
"""


def _ev_html(items):
    return "".join(
        '<li>' + i["text"] + ' <a data-source href="' + i["source_url"] + '">'
        + i["source_url"] + '</a></li>' for i in items)


def page(data: dict, rules: dict) -> str:
    """위 수집 결과를 **딱 맞게** 담은 화면. 계약이 요구하는 관계를 전부 지킨다."""
    intro = data["country_intro"]
    city = data["cities"][0]
    spot = city["spots"][0]
    slots = rules["feature1"]["header_slots"]

    f1 = ['<section id="feature1">',
          '<img data-role="flag" src="' + intro["국기이미지"]["asset"]["url"]
          + '" alt="국기">',
          '<img data-role="hero" src="' + intro["대표이미지"]["asset"]["url"]
          + '" alt="대표">']
    for header in rules["feature1"]["headers"]:
        body = "".join("<ul>" + _ev_html(intro[s].get("items") or []) + "</ul>"
                       for s in slots[header])
        f1.append('<button class="acc-header" data-acc="feature1" data-key="'
                  + header + '">' + header + '</button>')
        f1.append('<div class="acc-panel" data-acc="feature1" data-key="'
                  + header + '">' + body + '</div>')
    f1.append("</section>")

    #  도시 칸 **안**의 내용은 배치와 무관하게 같다. 달라지는 것은 그것을 무엇으로
    #  감싸느냐뿐이다 — 툴바(`aside#city-drawer`)냐 아코디언 패널이냐.
    body = ['<button data-spot="' + spot["name"] + '">' + spot["name"] + '</button>',
            '<div data-spot-detail="' + spot["name"] + '" hidden>',
            '<img data-spot-image="' + spot["name"] + '" src="'
            + spot["image"]["url"] + '" alt="' + spot["image"]["alt"] + '">',
            "<p>" + spot["detail"] + "</p>",
            "<ul>" + _ev_html(spot["items"]) + "</ul>",
            "</div>",
            '<div data-preference-note="' + city["name"] + '">'
            + "".join("<p>" + line + "</p>"
                      for line in city["preference_note"].splitlines())
            + "</div>"]

    if rules["feature2"].get("layout") == "drawer":
        f2 = ['<section id="feature2">',
              '<button data-city="' + city["name"] + '">' + city["name"] + '</button>',
              '<aside id="city-drawer" hidden>',
              '<button data-back="1">뒤로</button>',
              '<div data-city-panel="' + city["name"] + '" hidden>']
        f2 += body
        f2.append("</div></aside></section>")
    else:
        #  선택지 C — 툴바도 뒤로 가기도 없다. 도시 칸 자체가 열고 닫히는 칸이라
        #  `.acc-panel{display:none}` 로 닫혀 있다. 이름표(`data-city` ·
        #  `data-city-panel`)는 **배치와 무관하게 그대로** 붙는다.
        f2 = ['<section id="feature2">',
              '<button class="acc-header" data-acc="feature2" data-key="' + city["name"]
              + '" data-city="' + city["name"] + '">' + city["name"] + '</button>',
              '<div class="acc-panel" data-acc="feature2" data-key="' + city["name"]
              + '" data-city-panel="' + city["name"] + '">']
        f2 += body
        f2.append("</div></section>")

    plan = city["itinerary"]
    blocks = "".join(
        '<li data-block="' + b["start"] + "-" + b["end"] + '">'
        + b["kind"] + " " + b.get("spot", b.get("place", "")) + " " + b["why"] + "</li>"
        for b in plan["days"][0]["blocks"])
    f3 = ['<section id="feature3">',
          '<button class="acc-header" data-acc="feature3" data-key="' + city["name"]
          + '">' + city["name"] + '</button>',
          '<div class="acc-panel" data-acc="feature3" data-key="' + city["name"] + '">',
          "<ul>" + _ev_html(plan["items"]) + "</ul>",
          '<div data-day="1"><ul>' + blocks + "</ul></div>",
          "</div></section>"]

    return ('<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">'
            "<title>셀프테스트</title><style>" + CSS + "</style></head><body>"
            + "".join(f1) + "".join(f2) + "".join(f3)
            + "<script>" + JS + "</script></body></html>\n")


def sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def quality(root: Path, rules: dict) -> dict:
    """정성 1회차 기록. **실제로 한 군데를 고친** 회차로 만든다."""
    watch = rules["quality_contract"]["watch_files"]
    before = {name: sha(root / name) for name in watch}
    # 화면에 한 글자를 더해 해시를 실제로 바꾼다 (고친 척이 아니라 진짜 수정)
    target = root / "output" / "travel_site.html"
    target.write_text(target.read_text(encoding="utf-8").replace(
        "</body>", "<!-- 정성 1회차 수정 --></body>"), encoding="utf-8")
    after = {name: sha(root / name) for name in watch}
    return {
        "pass": 1,
        "focus": rules["quality_contract"]["pass_focus"]["1"],
        "checked_at": "2026-01-01T00:00:00",
        "snapshot_before": before,
        "rules": [
            {"id": "Q-반복금지", "verdict": "VIOLATION",
             "where": "output/travel_site.html", "note": "꼬리말이 비어 있었다"},
            {"id": "Q-취향연결", "verdict": "OK", "where": "-", "note": "이어짐"},
        ],
        "applied_fix": [{"rule": "Q-반복금지", "file": "output/travel_site.html",
                         "what": "꼬리말 주석을 채웠다"}],
        "snapshot_after": after,
        "verify_after": {
            "command": rules["quality_contract"]["regression_command"], "exit_code": 0},
    }


MASTER_SPEC_TEMPLATE = """# MASTER_SPEC.md (셀프테스트용)

<!-- MACHINE:BEGIN -->
```json
{payload}
```
<!-- MACHINE:END -->
"""


def build(root: Path, feature2_layout: str = "drawer") -> dict:
    """임시 폴더에 합격 세계를 통째로 만든다. 만든 계약을 돌려준다.

    `feature2_layout="accordion"` 이면 선택지 C 세계를 만든다.
    """
    rules = contract(feature2_layout)
    data = research()

    (root / "output").mkdir(parents=True, exist_ok=True)
    (root / "graph").mkdir(parents=True, exist_ok=True)

    payload = json.dumps(rules, ensure_ascii=False, indent=2)
    (root / "MASTER_SPEC.md").write_text(
        MASTER_SPEC_TEMPLATE.format(payload=payload), encoding="utf-8")
    (root / "graph" / "03_CONTRACT.json").write_text(payload + "\n", encoding="utf-8")

    (root / "output" / "research_data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "output" / "travel_site.html").write_text(
        page(data, rules["page_contract"]), encoding="utf-8")

    quality_dir = root / "evidence" / "runs" / "2026-01-01T00-00-00" / "quality"
    quality_dir.mkdir(parents=True, exist_ok=True)
    (quality_dir / "pass1.json").write_text(
        json.dumps(quality(root, rules), ensure_ascii=False, indent=2), encoding="utf-8")
    return rules


__all__ = ["build", "contract", "research", "page", "quality"]
