# -*- coding: utf-8 -*-
"""output/research_data.json 을 읽어 output/travel_site.html (파일 하나) 을 만든다.
내용은 새로 지어내지 않는다. 모은 데이터만 화면에 옮긴다."""
import json
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "output" / "research_data.json").read_text(encoding="utf-8"))
intro = data["country_intro"]
cities = data["cities"]
req = data["request"]

DAY_LABEL = {1: "11/13(금)", 2: "11/14(토)", 3: "11/15(일) 고베마라톤", 4: "11/16(월)"}
KIND_LABEL = {"명소": "명소", "식사": "식사", "이동": "이동", "휴식": "휴식"}


def sources(items):
    out = []
    for item in items:
        out.append(
            '<li class="evi"><p>%s</p><a data-source href="%s" target="_blank" rel="noopener">출처: %s</a></li>'
            % (e(item["text"]), e(item["source_url"], quote=True), e(item.get("source_name") or item["source_url"]))
        )
    return "<ul class=\"evidence\">" + "".join(out) + "</ul>"


def slot(label, key):
    node = intro[key]
    if key == "국가상태":
        return ('<h4>%s</h4><p class="slot-note">%s</p>' % (e(label), e(node.get("note") or "확인했으나 특별한 내용 없음")))
    return "<h4>%s</h4>%s" % (e(label), sources(node["items"]))


HEADERS = [
    ("매력", [("국가의 매력", "매력")]),
    ("역사", [("역사", "역사")]),
    ("문화", [("문화", "문화"), ("문화적으로 조심할 점", "주의사항")]),
    ("국가상태", [("국가 상태·질병", "국가상태")]),
    ("여행정보", [("항공권 가격", "항공권가격"), ("환율", "환율"), ("교통 개요", "교통개요")]),
]

f1 = []
for key, slots in HEADERS:
    body = "".join(slot(lbl, k) for lbl, k in slots)
    f1.append(
        '<div class="acc-item">'
        '<button type="button" class="acc-header" data-acc="feature1" data-key="%s" aria-expanded="false">%s</button>'
        '<div class="acc-panel" data-acc="feature1" data-key="%s">%s</div></div>' % (key, e(key), key, body)
    )

flag = intro["국기이미지"]["asset"]
hero = intro["대표이미지"]["asset"]

# ---- 기능2
city_buttons = "".join(
    '<button type="button" class="city-btn" data-city="%s">%s</button>' % (e(c["name"]), e(c["name"])) for c in cities
)

drawer_panels = []
for c in cities:
    spots_html = []
    for s in c["spots"]:
        im = s["image"]
        spots_html.append(
            '<article class="spot">'
            '<button type="button" class="spot-btn" data-spot="%s" aria-expanded="false">%s</button>'
            '<img data-spot-image="%s" src="%s" alt="%s" loading="lazy" '
            'onerror="this.style.display=\'none\';this.nextElementSibling.hidden=false">'
            '<div class="img-fallback" hidden>사진을 불러오지 못했습니다 (%s)</div>'
            '<div class="spot-detail" data-spot-detail="%s" hidden><p>%s</p>%s</div>'
            '</article>' % (
                e(s["name"]), e(s["name"]), e(s["name"]), e(im["url"], quote=True), e(im["alt"], quote=True),
                e(s["name"]), e(s["name"]), e(s["detail"]), sources(s["items"]))
        )
    notes = "".join("<p>%s</p>" % e(ln.strip()) for ln in c["preference_note"].splitlines() if ln.strip())
    drawer_panels.append(
        '<div class="city-panel" data-city-panel="%s" hidden>'
        '<h3>%s</h3><p class="why"><strong>왜 이 도시인가</strong> %s</p>'
        '<div class="spots">%s</div>'
        '<div class="pref" data-preference-note="%s"><h4>내 취향과 연결한 설명</h4>%s</div>'
        '</div>' % (e(c["name"]), e(c["name"]), e(c["why_selected"]), "".join(spots_html), e(c["name"]), notes)
    )

# ---- 기능3
f3 = []
for c in cities:
    it = c["itinerary"]
    day_html = []
    for d in it["days"]:
        blocks = []
        for b in d["blocks"]:
            where = b.get("spot") or b.get("place") or ""
            check_key = "%s-%d-%s-%s" % (c["name"], d["day"], b["start"], b["end"])
            blocks.append(
                '<li data-block="%s-%s"><label class="chk-wrap"><input type="checkbox" class="chk" '
                'data-check="%s" data-day-key="%s-%d" aria-label="%s %s~%s 완료 표시"></label> '
                '<span class="time">%s~%s</span> <span class="kind k-%s">%s</span> '
                '<strong>%s</strong><br><span class="why">%s</span></li>'
                % (b["start"], b["end"], e(check_key, quote=True), e(c["name"], quote=True), d["day"],
                   e(where, quote=True), b["start"], b["end"],
                   b["start"], b["end"], e(b["kind"]), e(KIND_LABEL[b["kind"]]),
                   e(where), e(b["why"]))
            )
        day_html.append(
            '<div class="day" data-day="%d"><h4>%d일차 · %s <span class="day-progress" data-progress="%s-%d">0 / %d 완료</span></h4>'
            '<ol class="blocks">%s</ol></div>'
            % (d["day"], d["day"], e(DAY_LABEL[d["day"]]), e(c["name"], quote=True), d["day"], len(d["blocks"]),
               "".join(blocks))
        )
    f3.append(
        '<div class="acc-item">'
        '<button type="button" class="acc-header" data-acc="feature3" data-key="%s" aria-expanded="false">%s 일정 (4일)</button>'
        '<div class="acc-panel" data-acc="feature3" data-key="%s">%s<h4>일정 근거</h4>%s</div></div>'
        % (e(c["name"]), e(c["name"]), e(c["name"]), "".join(day_html), sources(it["items"]))
    )

TOTAL_BLOCKS = sum(len(d["blocks"]) for c in cities for d in c["itinerary"]["days"])
style_pref = " · ".join(req["style"]["preferred"])

HTML = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>일본 오사카 4일 — 여행 일정 체크리스트</title>
<style>
:root{--bg:#0b1316;--card:#121c20;--line:#223238;--text:#e6f1f2;--mute:#9fb3b6;--accent:#14B8A6;--accent2:#0e8a7c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:"Noto Sans KR","Malgun Gothic",system-ui,sans-serif;line-height:1.7}
.wrap{max-width:1040px;margin:0 auto;padding:16px}
header.top{padding:28px 16px 8px}
header.top h1{margin:0 0 6px;font-size:1.7rem}
header.top p{margin:0;color:var(--mute)}
.tags span{display:inline-block;margin:8px 6px 0 0;padding:2px 12px;border:1px solid var(--accent);border-radius:99px;color:var(--accent);font-size:.85rem}
section{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin:18px 0}
section>h2{margin:0 0 12px;font-size:1.25rem;color:var(--accent)}
.hero{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:14px}
.hero img{border-radius:10px;border:1px solid var(--line);background:#fff}
.hero img[data-role=flag]{width:96px;height:64px;object-fit:contain;padding:4px}
.hero img[data-role=hero]{width:min(60%,420px);height:auto;max-height:260px;object-fit:cover}
.acc-item{border:1px solid var(--line);border-radius:10px;margin:8px 0;overflow:hidden}
.acc-header{width:100%;text-align:left;background:#0f1a1e;color:var(--text);border:0;padding:12px 14px;font-size:1rem;cursor:pointer}
.acc-header:hover,.acc-header[aria-expanded=true]{background:var(--accent2);color:#fff}
.acc-panel{display:none;padding:6px 16px 14px}
.acc-panel.open{display:block}
h4{margin:14px 0 4px;color:var(--accent)}
ul.evidence{list-style:none;margin:0;padding:0}
li.evi{padding:8px 0;border-bottom:1px dashed var(--line)}
li.evi p{margin:0 0 2px}
a[data-source]{color:var(--accent);font-size:.82rem}
.slot-note{margin:0;color:var(--mute)}
.cities{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px}
.city-btn{background:var(--accent);color:#04201c;border:0;border-radius:10px;padding:12px 26px;font-size:1.05rem;font-weight:700;cursor:pointer}
.city-btn:hover{background:#2dd4bf}
.hint{color:var(--mute);margin:4px 0 0;font-size:.9rem}
aside#city-drawer{position:fixed;top:0;right:0;width:min(560px,100%);height:100%;overflow:auto;background:#0f1a1e;border-left:2px solid var(--accent);padding:18px;z-index:20;box-shadow:-8px 0 24px rgba(0,0,0,.5)}
aside[hidden],.city-panel[hidden],.spot-detail[hidden],.img-fallback[hidden]{display:none}
.back{background:transparent;color:var(--accent);border:1px solid var(--accent);border-radius:8px;padding:6px 14px;cursor:pointer;margin-bottom:10px}
.spot{border:1px solid var(--line);border-radius:10px;padding:10px;margin:10px 0}
.spot-btn{background:#16262b;color:var(--text);border:1px solid var(--line);border-radius:8px;padding:8px 12px;cursor:pointer;font-size:1rem;width:100%;text-align:left}
.spot-btn[aria-expanded=true]{border-color:var(--accent);color:var(--accent)}
.spot img{width:100%;max-height:220px;object-fit:cover;border-radius:8px;margin-top:8px}
.img-fallback{margin-top:8px;padding:30px 10px;border:1px dashed var(--mute);border-radius:8px;text-align:center;color:var(--mute)}
.pref p{margin:6px 0;padding-left:10px;border-left:3px solid var(--accent2)}
.why{background:#0b1316;padding:10px;border-radius:8px}
.compare{background:#0b1316;border:1px solid var(--accent2);border-radius:10px;padding:6px 14px;margin:10px 0}
.compare ul{margin:6px 0;padding-left:18px}
.day{margin:14px 0}
ol.blocks{list-style:none;margin:0;padding:0}
ol.blocks li{padding:8px 10px;margin:6px 0;background:#0b1316;border-left:3px solid var(--accent2);border-radius:6px}
.jump{margin:10px 0 0}
.jump-link{display:inline-block;background:var(--accent);color:#04201c;font-weight:700;padding:8px 16px;border-radius:99px;text-decoration:none}
.time{color:var(--accent);font-variant-numeric:tabular-nums}
.chk-wrap{display:inline-block;margin-right:6px;vertical-align:middle}
.chk{width:20px;height:20px;accent-color:var(--accent);cursor:pointer}
ol.blocks li.done{opacity:.55;border-left-color:var(--accent)}
ol.blocks li.done strong{text-decoration:line-through}
.day-progress{margin-left:8px;font-size:.8rem;color:var(--mute);font-weight:400}
.progress-all{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:8px 0;padding:8px 12px;background:#0b1316;border:1px solid var(--line);border-radius:8px}
#reset-checks{background:transparent;color:var(--accent);border:1px solid var(--accent);border-radius:8px;padding:4px 12px;cursor:pointer}
.kind{font-size:.75rem;padding:1px 8px;border-radius:99px;border:1px solid var(--mute);color:var(--mute)}
.k-명소{border-color:var(--accent);color:var(--accent)}
.why{color:#c8d6d8}
footer{color:var(--mute);font-size:.8rem;padding:10px 16px 40px}
@media (max-width:600px){.hero{flex-direction:column}.hero img[data-role=hero]{width:100%}}
</style>
</head>
<body>
<div class="wrap">
<header class="top">
<h1>일본 오사카 4일 · 일정 체크리스트</h1>
<p>2026년 11월 13일(금) ~ 16일(월) · 3박 4일 · 11월 15일 고베마라톤 참가</p>
<p>오사카 숙소: 시티 플라자 오사카 (체크인 15:00 · 체크아웃 11:00) · 항공: 11/13 08:05 출발 09:50 도착 · 11/16 23:25 출발</p>
<p class="jump"><a class="jump-link" href="#feature3">▶ 일정 체크리스트로 바로 가기</a></p>
<div class="tags"><span>좋아하는 것 : __PREF__</span><span>피하고 싶은 것 : 많이 걷는 일정</span></div>
</header>

<section id="feature1">
<h2>1. 일본 한눈에 보기</h2>
<div class="hero">
<img data-role="flag" src="__FLAG_SRC__" alt="__FLAG_ALT__" onerror="this.alt='국기 이미지를 불러오지 못했습니다'">
<img data-role="hero" src="__HERO_SRC__" alt="__HERO_ALT__" onerror="this.alt='대표 사진을 불러오지 못했습니다'">
</div>
__F1__
</section>

<section id="feature2">
<h2>2. 도시와 관광지 고르기</h2>
<div class="cities">__CITY_BUTTONS__</div>
<p class="hint">도시를 누르면 오른쪽에서 관광지 목록이 열립니다. 관광지를 누르면 사진과 상세 소개가 펼쳐집니다.</p>
<aside id="city-drawer" aria-label="도시와 관광지" hidden>
<button type="button" class="back" data-back>← 뒤로 가기 (도시 목록으로)</button>
__DRAWER__
</aside>
</section>

<section id="feature3">
<h2>3. 오사카 4일 일정 (체크리스트)</h2>
<p class="hint">일정을 마칠 때마다 블록 앞 체크박스로 완료를 표시하세요. 시각은 계획이며 대회 출발 시각은 공식 발표에 맞춰 조정해야 합니다.</p>
<div class="progress-all"><span id="progress-all-text">전체 0 / __TOTAL__ 완료</span> <button type="button" id="reset-checks">체크 초기화</button></div>
<div class="compare">
<h4>이 일정의 전제</h4>
<ul>
<li><strong>숙소</strong> — 시티 플라자 오사카(11/13~16). 체크인 15:00 · 체크아웃 11:00이고 천연 온천수 노천탕이 있습니다. 가까운 사카이스지혼마치역에서 사카이스지선으로 나가호리바시(도톤보리·신사이바시·구로몬이 걸어서 닿음)와 닛폼바시까지 짧게 갑니다.</li>
<li><strong>항공</strong> — 11/13 08:05 출발 09:50 도착, 11/16 23:25 출발. 마지막 날은 아침에 체크아웃하고 짐을 맡긴 뒤 밤까지 시간을 씁니다.</li>
<li><strong>11/15 고베마라톤</strong> — 우메다에서 한큐 특급으로 산노미야까지 약 30분이고, 고베시청 앞에서 출발해 고베 하버랜드에서 결승합니다. 대회 출발 시각과 지하철 환승 시간은 확인하지 못한 가정이라 출발 전에 확인해야 합니다.</li>
<li>체크 표시는 이 브라우저에만 저장되며, 저장이 막힌 환경에서는 새로고침하면 사라집니다.</li>
</ul>
</div>
__F3__
</section>

<footer>
정보는 공개 자료를 모은 것이며 가격·환율·운영시간은 출발 전에 다시 확인해야 합니다. 사진이 해당 장소가 맞는지와 사실 정보는 직접 확인해 주세요.
</footer>
</div>

<script>
(function () {
  var drawer = document.getElementById('city-drawer');

  function setOpen(header, open) {
    var panel = header.parentElement.querySelector('.acc-panel');
    header.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (panel) { panel.classList.toggle('open', open); }
  }

  function showCity(name) {
    var panels = drawer.querySelectorAll('[data-city-panel]');
    for (var i = 0; i < panels.length; i++) {
      panels[i].hidden = panels[i].getAttribute('data-city-panel') !== name;
    }
    drawer.hidden = false;
    drawer.scrollTop = 0;
  }

  function toggleSpot(button) {
    var name = button.getAttribute('data-spot');
    var detail = drawer.querySelector('[data-spot-detail="' + name + '"]');
    if (!detail) { return; }
    var willOpen = detail.hidden;
    detail.hidden = !willOpen;
    button.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
  }

  document.addEventListener('click', function (ev) {
    var t = ev.target;
    var header = t.closest('.acc-header');
    if (header) {
      setOpen(header, header.getAttribute('aria-expanded') !== 'true');
      return;
    }
    if (t.closest('a.jump-link')) {
      var first = document.querySelector('.acc-header[data-acc="feature3"]');
      if (first) { setOpen(first, true); }
      return;
    }
    var city = t.closest('button[data-city]');
    if (city) {
      showCity(city.getAttribute('data-city'));
      return;
    }
    var spot = t.closest('button[data-spot]');
    if (spot) {
      toggleSpot(spot);
      return;
    }
    if (t.closest('[data-back]')) {
      drawer.hidden = true;
    }
  });

  var STORE_KEY = 'travel-checks-v1';
  function readStore() {
    try {
      var raw = window.localStorage.getItem(STORE_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (err) { return {}; }
  }
  function writeStore(obj) {
    try { window.localStorage.setItem(STORE_KEY, JSON.stringify(obj)); } catch (err) { /* 저장이 막혀도 화면은 동작한다 */ }
  }
  var checked = readStore();

  function refreshChecks() {
    var boxes = document.querySelectorAll('input.chk');
    var perDay = {};
    var done = 0;
    for (var i = 0; i < boxes.length; i++) {
      var box = boxes[i];
      var on = !!checked[box.getAttribute('data-check')];
      box.checked = on;
      box.closest('li').classList.toggle('done', on);
      var dk = box.getAttribute('data-day-key');
      perDay[dk] = perDay[dk] || {total: 0, done: 0};
      perDay[dk].total += 1;
      if (on) { perDay[dk].done += 1; done += 1; }
    }
    var labels = document.querySelectorAll('[data-progress]');
    for (var j = 0; j < labels.length; j++) {
      var st = perDay[labels[j].getAttribute('data-progress')] || {total: 0, done: 0};
      labels[j].textContent = st.done + ' / ' + st.total + ' 완료';
    }
    var all = document.getElementById('progress-all-text');
    if (all) { all.textContent = '전체 ' + done + ' / ' + boxes.length + ' 완료'; }
  }

  document.addEventListener('change', function (ev) {
    var box = ev.target.closest('input.chk');
    if (!box) { return; }
    var key = box.getAttribute('data-check');
    if (box.checked) { checked[key] = 1; } else { delete checked[key]; }
    writeStore(checked);
    refreshChecks();
  });
  document.getElementById('reset-checks').addEventListener('click', function () {
    checked = {};
    writeStore(checked);
    refreshChecks();
  });
  refreshChecks();

  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape') { drawer.hidden = true; }
  });
})();
</script>
</body>
</html>
"""

out = (HTML.replace("__PREF__", e(style_pref))
       .replace("__FLAG_SRC__", e(flag["url"], quote=True)).replace("__FLAG_ALT__", e(flag["alt"], quote=True))
       .replace("__HERO_SRC__", e(hero["url"], quote=True)).replace("__HERO_ALT__", e(hero["alt"], quote=True))
       .replace("__F1__", "".join(f1))
       .replace("__CITY_BUTTONS__", city_buttons)
       .replace("__DRAWER__", "".join(drawer_panels))
       .replace("__F3__", "".join(f3))
       .replace("__TOTAL__", str(TOTAL_BLOCKS)))

(ROOT / "output" / "travel_site.html").write_text(out, encoding="utf-8")
print("written output/travel_site.html", len(out), "chars")
