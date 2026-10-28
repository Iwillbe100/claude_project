# -*- coding: utf-8 -*-
"""output/ishikawa_data.json 을 읽어 output/ishikawa_trip.html (파일 하나) 을 만든다.
오사카 페이지(src/build_page.py)의 스타일과 스크립트를 그대로 가져와 쓰되 체크 저장 키는 따로 쓴다.
내용은 새로 지어내지 않는다. 모은 데이터만 화면에 옮긴다."""
import json
import re
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "output" / "ishikawa_data.json").read_text(encoding="utf-8"))
meta = data["meta"]
overview = data["overview"]
city = data["city"]

# 오사카 페이지에서 CSS 와 JS 를 가져온다 (같은 검증을 거친 코드를 재사용)
base = (ROOT / "src" / "build_page.py").read_text(encoding="utf-8")
CSS = re.search(r"<style>(.*?)</style>", base, re.S).group(1)
JS = re.search(r"<script>(.*?)</script>", base, re.S).group(1)
JS = JS.replace("travel-checks-v1", "ishikawa-checks-v1")

KIND_LABEL = {"명소": "명소", "식사": "식사", "이동": "이동", "휴식": "휴식"}


def sources(items):
    out = []
    for item in items:
        out.append(
            '<li class="evi"><p>%s</p><a data-source href="%s" target="_blank" rel="noopener">출처: %s</a></li>'
            % (e(item["text"]), e(item["source_url"], quote=True), e(item.get("source_name") or item["source_url"]))
        )
    return '<ul class="evidence">' + "".join(out) + "</ul>"


# ---- 개요 (아코디언)
f1 = []
for block in overview:
    f1.append(
        '<div class="acc-item">'
        '<button type="button" class="acc-header" data-acc="feature1" data-key="%s" aria-expanded="false">%s</button>'
        '<div class="acc-panel" data-acc="feature1" data-key="%s">%s</div></div>'
        % (e(block["key"], quote=True), e(block["key"]), e(block["key"], quote=True), sources(block["items"]))
    )

# ---- 명소 (우측 서랍)
spots_html = []
for s in city["spots"]:
    im = s["image"]
    spots_html.append(
        '<article class="spot">'
        '<button type="button" class="spot-btn" data-spot="%s" aria-expanded="false">%s</button>'
        '<img data-spot-image="%s" src="%s" alt="%s" loading="lazy" '
        'onerror="this.style.display=\'none\';this.nextElementSibling.hidden=false">'
        '<div class="img-fallback" hidden>사진을 불러오지 못했습니다 (%s)</div>'
        '<div class="spot-detail" data-spot-detail="%s" hidden><p>%s</p>%s</div>'
        '</article>' % (
            e(s["name"], quote=True), e(s["name"]), e(s["name"], quote=True), e(im["url"], quote=True),
            e(im["alt"], quote=True), e(s["name"]), e(s["name"], quote=True), e(s["detail"]), sources(s["items"]))
    )
notes = "".join("<p>%s</p>" % e(ln.strip()) for ln in city["preference_note"].splitlines() if ln.strip())
drawer = (
    '<div class="city-panel" data-city-panel="%s" hidden>'
    '<h3>%s</h3><p class="why"><strong>왜 이 도시인가</strong> %s</p>'
    '<div class="spots">%s</div>'
    '<div class="pref" data-preference-note="%s"><h4>이 일정을 이렇게 짠 이유</h4>%s</div>'
    '</div>' % (e(city["name"], quote=True), e(city["name"]), e(city["why_selected"]),
                "".join(spots_html), e(city["name"], quote=True), notes)
)
city_button = '<button type="button" class="city-btn" data-city="%s">%s 명소 8곳 보기</button>' % (
    e(city["name"], quote=True), e(city["name"]))

# ---- 일정 (체크리스트)
day_html = []
for d in city["itinerary"]["days"]:
    blocks = []
    for b in d["blocks"]:
        where = b.get("spot") or b.get("place") or ""
        check_key = "%s-%d-%s-%s" % (city["name"], d["day"], b["start"], b["end"])
        blocks.append(
            '<li data-block="%s-%s"><label class="chk-wrap"><input type="checkbox" class="chk" '
            'data-check="%s" data-day-key="%s-%d" aria-label="%s %s~%s 완료 표시"></label> '
            '<span class="time">%s~%s</span> <span class="kind k-%s">%s</span> '
            '<strong>%s</strong><br><span class="why">%s</span></li>'
            % (b["start"], b["end"], e(check_key, quote=True), e(city["name"], quote=True), d["day"],
               e(where, quote=True), b["start"], b["end"], b["start"], b["end"], e(b["kind"]),
               e(KIND_LABEL[b["kind"]]), e(where), e(b["why"]))
        )
    day_html.append(
        '<div class="day" data-day="%d"><h4>%d일차 · %s <span class="day-progress" data-progress="%s-%d">0 / %d 완료</span></h4>'
        '<ol class="blocks">%s</ol></div>'
        % (d["day"], d["day"], e(d["label"]), e(city["name"], quote=True), d["day"], len(d["blocks"]), "".join(blocks))
    )
f3 = (
    '<div class="acc-item">'
    '<button type="button" class="acc-header" data-acc="feature3" data-key="%s" aria-expanded="false">%s 일정 (3박 4일)</button>'
    '<div class="acc-panel" data-acc="feature3" data-key="%s">%s<h4>일정 근거</h4>%s</div></div>'
    % (e(city["name"], quote=True), e(city["name"]), e(city["name"], quote=True), "".join(day_html),
       sources(city["itinerary"]["items"]))
)
TOTAL = sum(len(d["blocks"]) for d in city["itinerary"]["days"])
hero = city["spots"][1]["image"]  # 겐로쿠엔(겨울)
assume = "".join("<li>%s</li>" % e(a) for a in meta["assumptions"])

HTML = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>일본 이시카와(가나자와) 3박 4일 — 일정 체크리스트</title>
<style>__CSS__
.hero-one{margin:0 0 14px}
.hero-one img{width:100%;max-height:300px;object-fit:cover;border-radius:10px;border:1px solid var(--line)}
</style>
</head>
<body>
<div class="wrap">
<header class="top">
<h1>일본 이시카와(가나자와) 3박 4일 · 일정 체크리스트</h1>
<p>__SEASON__ · 가나자와 중심 · 오사카 일정과는 별도의 파일입니다</p>
<p class="jump"><a class="jump-link" href="#feature3">▶ 일정 체크리스트로 바로 가기</a></p>
<div class="tags"><span>좋아하는 것 : 맛집 · 휴식 · 쇼핑</span><span>걷기 : 상관없음</span></div>
</header>

<section id="feature1">
<h2>1. 가나자와 한눈에 보기</h2>
<div class="hero-one"><img data-role="hero" src="__HERO_SRC__" alt="__HERO_ALT__" onerror="this.alt='대표 사진을 불러오지 못했습니다'"></div>
__F1__
</section>

<section id="feature2">
<h2>2. 명소 둘러보기</h2>
<div class="cities">__CITY_BUTTON__</div>
<p class="hint">버튼을 누르면 오른쪽에서 명소 목록이 열립니다. 명소를 누르면 사진과 상세 소개가 펼쳐집니다.</p>
<aside id="city-drawer" aria-label="가나자와 명소" hidden>
<button type="button" class="back" data-back>← 뒤로 가기 (닫기)</button>
__DRAWER__
</aside>
</section>

<section id="feature3">
<h2>3. 가나자와 3박 4일 일정 (체크리스트)</h2>
<p class="hint">일정을 마칠 때마다 블록 앞 체크박스로 완료를 표시하세요. 날짜가 정해지지 않아 시각은 계획입니다.</p>
<div class="progress-all"><span id="progress-all-text">전체 0 / __TOTAL__ 완료</span> <button type="button" id="reset-checks">체크 초기화</button></div>
<div class="compare">
<h4>이 일정의 전제 (확인되지 않은 가정)</h4>
<ul>__ASSUME__
<li>오미초 시장은 대부분의 상점이 수요일과 일요일에 쉬고, 21세기 미술관 전람회 존은 월요일에 쉽니다. 날짜가 정해져 2일차가 수요일·일요일에 걸리면 2일차 전체와 3일차 전체를 통째로 바꾸세요(2일차에 오미초·겐로쿠엔·가나자와성이 함께 묶여 있습니다).</li>
<li>체크 표시는 이 브라우저에만 저장되며, 저장이 막힌 환경에서는 새로고침하면 사라집니다.</li>
</ul>
</div>
__F3__
</section>

<footer>
정보는 공개 자료를 모은 것이며 가격·영업시간·휴무는 출발 전에 다시 확인해야 합니다. 사진이 해당 장소가 맞는지와 사실 정보는 직접 확인해 주세요.
</footer>
</div>

<script>__JS__</script>
</body>
</html>
"""

out = (HTML.replace("__CSS__", CSS).replace("__JS__", JS)
       .replace("__SEASON__", e(meta["season"]))
       .replace("__HERO_SRC__", e(hero["url"], quote=True)).replace("__HERO_ALT__", e(hero["alt"], quote=True))
       .replace("__F1__", "".join(f1)).replace("__CITY_BUTTON__", city_button)
       .replace("__DRAWER__", drawer).replace("__F3__", f3)
       .replace("__TOTAL__", str(TOTAL)).replace("__ASSUME__", assume))

(ROOT / "output" / "ishikawa_trip.html").write_text(out, encoding="utf-8")
print("written output/ishikawa_trip.html", len(out), "chars · 블록", TOTAL)
