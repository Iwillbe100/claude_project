"""단일 HTML 페이지를 만든다. **킷 소유 — 수정 금지.**

노드가 부르는 것은 `write()` 하나다(안에서 `render()` 로 HTML 을 만든다). 부르는
노드는 `build_page` · `fix_image_spec`(처방 가지) 둘이고, `rebuilder` · `quality_pass` 는
`quality.apply_fixes` 를 거쳐 부른다. 결정론 코드로 짠 이유는 두 가지다.

  1. 화면 이름표(`data-*`)는 **루프 킷에서 이미 확정된 계약**이다. 매번 LLM 이
     다시 짜면 이름표가 흔들려 검사기가 못 찾는다. 계약은 고정, 실행 구조만 바꾼다.
  2. 30분 실습에서 페이지 생성에 3분을 쓰면 게이트 실습 시간이 사라진다.

**그렇다고 루프 B가 의미 없어지는 것은 아니다.** 페이지는 수집 데이터에서 나오므로,
수집이 덜 됐으면 `check_page` 가 SHORT 를 낸다. 즉 루프 B는 "코드가 틀렸나"가 아니라
"데이터가 화면 계약을 채우는가"를 본다 — 루프 킷의 `check_page_contract.py` 와 같은 자다.

**사진은 틀에 담는다** (`.spot-img` 는 4:3 비율 · 잘라 맞춤, `.flag` · `.hero` 는 높이
상한). 예전에는 폭만 정해 세로 사진 한 장이 서랍을 뚫고 길어졌다 — 교육생이 게이트에
*"이미지 규격이 안 맞음"* 이라고 적어 낸 것이 이것이었다. 검사기는 사진이 **있는가**만
보므로 이 결함을 못 잡는다. 처방 가지 시험지 `scripts/detour_tests/test_image_spec.py` 의
S2 가 이 틀이 살아 있는지 본다. 이 CSS 에서 틀을 지우면 그 시험지가 불합격을 낸다.
"""
from __future__ import annotations

import html
import re

from travel_graph import contract

#: `&` 뒤에 `이름;` 이 오면 **모호한 참조**라 escape 해야 한다.
#: 그 밖의 `&` 는 HTML5 에서 그대로 두어도 적법하다 (`?a=1&b=2` 처럼).
_AMBIGUOUS_AMP = re.compile(r"&(?=[A-Za-z0-9]+;)")

#: `html` 은 아래 `esc()` 가 쓰지 않지만, 이 파일을 읽는 사람이 표준 함수와
#: 무엇이 다른지 바로 비교할 수 있게 남겨 둔다.
_ = html


def _as_list(value):
    return value if isinstance(value, list) else []


def _as_dict(value):
    return value if isinstance(value, dict) else {}


def esc(value) -> str:
    """HTML 로 안전하게 만들되 **원문을 최대한 남긴다.**

    ★ `html.escape(quote=True)` 를 쓰지 않는 이유가 있다. 그것은 `&` 를 `&amp;` 로,
      `'` 를 `&#x27;` 로 바꾼다. 그런데 `check_page_contract` 는 출처 URL 과
      도시·관광지 이름을 **원문 문자열 그대로** 화면에서 찾는다 (`url not in text`).
      그래서 화면에 분명히 있는데도 "화면에 없습니다"로 잡혔다.

          데이터  https://oktour.ca/wp/index.php?l=kr&p=Canada&pluId=55
          화면    https://oktour.ca/wp/index.php?l=kr&amp;p=Canada&amp;pluId=55   <- 못 찾는다
          데이터  .../File:Ripley's_Aquarium_of_Canada.jpg
          화면    .../File:Ripley&#x27;s_Aquarium_of_Canada.jpg                   <- 못 찾는다

      바로 아래 `_evidence_list` 의 주석이 "출처 URL 을 **본문에 그대로** 남긴다"
      라고 적어 둔 그 약속을 `esc()` 가 깨고 있었다. 루프 킷 실측에서 "출처 링크
      3건 누락 (URL 특수문자 escape 문제)" 으로 나왔던 것이 같은 자리다.

      HTML5 에서 `&` 는 `&이름;` 꼴의 **모호한 참조**일 때만 escape 가 필요하고,
      `'` 는 텍스트 노드와 **큰따옴표 속성** 안에서 escape 가 필요 없다.
      이 파일의 속성은 전부 큰따옴표를 쓴다. 그래서 **꼭 필요한 것만** 바꾼다 —
      화면에는 원문이 남고 HTML 도 유효하다.
    """
    text = str(value or "")
    text = _AMBIGUOUS_AMP.sub("&amp;", text)
    return text.replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _items(node) -> list:
    return [i for i in _as_list(_as_dict(node).get("items")) if isinstance(i, dict)]


def _evidence_list(nodes: list, slot=None) -> str:
    """근거 목록. 출처 URL 을 **본문에 그대로** 남긴다 — 검사기가 그것을 대조한다.

    비어 있을 때 두 가지를 구분한다. 계약이 '조건부'로 둔 칸(여행경보 같은 것)은
    **확인했는데 해당 사항이 없을 수 있다.** 개수 검사기는 이 둘을 구분해서
    `checked` 표시만 있으면 통과시키는데, 화면이 둘 다 "아직 채워지지 않았습니다"
    로 그리면 **확인한 사실이 화면에서 사라진다.** 읽는 사람에게도 거짓말이 되고,
    화면 계약의 분량 하한도 영영 못 채운다.
    """
    if not nodes:
        if isinstance(slot, dict) and slot.get("checked"):
            return ('<p class="checked">이 항목은 확인했으며, 현재 해당하는 사항이 '
                    '확인되지 않았습니다. 출발 전에 외교부 해외안전여행 공지에서 '
                    '다시 한 번 확인하십시오.</p>')
        return '<p class="empty">이 칸은 아직 채워지지 않았습니다.</p>'
    out = ["<ul class=\"ev\">"]
    for item in nodes:
        text = esc(item.get("text"))
        url = esc(item.get("source_url"))
        link = f' <a class="src" href="{url}" target="_blank" rel="noopener">{url}</a>' if url else ""
        out.append(f"<li>{text}{link}</li>")
    out.append("</ul>")
    return "".join(out)


# --------------------------------------------------------------------------- #
# 기능 1 — 국가 소개 (아코디언)
# --------------------------------------------------------------------------- #


def _layout_block(area: str, layout: str, sections: list, marks=None) -> str:
    """(키, 라벨, 본문) 목록을 **계약이 정한 배치로** 그린다.

    내용을 만드는 일과 배치하는 일을 나눈 자리다. 배치가 바뀌어도 이름표(`data-*`)와
    본문은 그대로여야 검사기가 같은 것을 센다 — 그것이 "같은 계약, 다른 배치"다.

    `marks` 는 `{키: (단추에 더할 속성, 칸에 더할 속성)}`. 기능2를 아코디언으로 그릴 때
    `data-city` · `data-city-panel` 을 같이 달기 위한 자리다. 검사기는 배치와 무관하게
    같은 이름표를 찾으므로, 배치를 바꿔도 이름표는 따라가야 한다.

    ★ 탭은 **한 칸만 보인다.** 첫 칸을 빼고 `hidden` 을 단다. 검사기는 패널이 둘 이상일
      때 `len(panels) - 1` 개가 닫혀 있는지 세고, `hidden` 속성을 닫힘으로 읽는다.

    ★ 아코디언은 CSS 로 닫는다 (`.acc-panel{display:none}`). 검사기가 `<style>` 을 읽어
      '기본이 닫힘'인 클래스를 모으기 때문에 속성 없이도 닫힘으로 인정된다.
    """
    marks = marks or {}
    if layout == "tabs":
        out = [f'<div class="tab-row" data-tab-area="{esc(area)}">']
        for index, (key, label, _body) in enumerate(sections):
            on = " on" if index == 0 else ""
            more = marks.get(key, ("", ""))[0]
            out.append(
                f'<button class="tab-btn{on}" data-tab-area="{esc(area)}" '
                f'data-tab="{esc(key)}"{more}>{esc(label)}</button>')
        out.append("</div>")
        for index, (key, _label, body) in enumerate(sections):
            hide = "" if index == 0 else " hidden"
            more = marks.get(key, ("", ""))[1]
            out.append(
                f'<div class="tab-panel" data-tab-area="{esc(area)}" '
                f'data-tab-panel="{esc(key)}"{more}{hide}>' + body + "</div>")
        return "".join(out)

    out = []
    for key, label, body in sections:
        button_more, panel_more = marks.get(key, ("", ""))
        out.append(
            f'<button class="acc-header" data-acc="{esc(area)}" data-key="{esc(key)}"'
            f'{button_more}>{esc(label)}<span class="chev">▾</span></button>')
        out.append(
            f'<div class="acc-panel" data-acc="{esc(area)}" data-key="{esc(key)}"'
            f'{panel_more}>' + body + "</div>")
    return "".join(out)


def _feature1(intro: dict, rules: dict, country: str) -> str:
    flag = _as_dict(_as_dict(intro.get("국기이미지")).get("asset"))
    hero = _as_dict(_as_dict(intro.get("대표이미지")).get("asset"))
    headers = _as_list(rules.get("headers"))
    slots = _as_dict(rules.get("header_slots"))
    layout = str(rules.get("layout") or "accordion")

    parts = ['<section id="feature1"><h2>1. ' + esc(country) + ' 소개</h2>']
    parts.append('<div class="hero-row">')
    parts.append(
        f'<img data-role="flag" class="flag" src="{esc(flag.get("url"))}" '
        f'alt="{esc(flag.get("alt") or country + " 국기")}">')
    parts.append(
        f'<img data-role="hero" class="hero" src="{esc(hero.get("url"))}" '
        f'alt="{esc(hero.get("alt") or country + " 대표 사진")}">')
    parts.append("</div>")

    sections = []
    for key in headers:
        keys = _as_list(slots.get(key)) or [key]
        body = [f'<h4>{esc(key)}</h4>']
        for slot_name in keys:
            node = intro.get(slot_name)
            body.append(f'<h5>{esc(slot_name)}</h5>')
            body.append(_evidence_list(_items(node), node))
        sections.append((key, key, "".join(body)))
    parts.append(_layout_block("feature1", layout, sections))
    parts.append("</section>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# 기능 2 — 도시와 관광지 (우측 툴바 또는 아코디언)
# --------------------------------------------------------------------------- #


def _city_body(city: dict, rules: dict) -> str:
    """도시 한 곳의 내용. **배치와 무관하게 같다** — 이름표도 같다.

    툴바든 아코디언이든 검사기는 같은 이름표를 찾는다. 다른 것은 이 내용을 어디에
    담느냐뿐이다 (`<aside>` 안이냐, 펼쳐지는 패널이냐).
    """
    name = esc(city.get("name"))
    panel = [f'<h3>{name}</h3>',
             f'<p class="why">{esc(city.get("why_selected"))}</p>']
    for spot in _as_list(city.get("spots")):
        if not isinstance(spot, dict) or not spot.get("name"):
            continue
        spot_name = esc(spot.get("name"))
        image = _as_dict(spot.get("image"))
        panel.append(
            f'<button class="spot-card" data-spot="{spot_name}">{spot_name}</button>')
        panel.append(f'<div class="spot-detail" data-spot-detail="{spot_name}" hidden>')
        if rules.get("spot_images"):
            url = esc(image.get("url"))
            alt = esc(image.get("alt") or spot.get("name"))
            if url:
                panel.append(
                    f'<img data-spot-image="{spot_name}" class="spot-img" '
                    f'src="{url}" alt="{alt}">')
            else:
                panel.append(
                    f'<div class="no-img" data-spot-image="{spot_name}">'
                    f'사진을 구하지 못했습니다</div>')
        panel.append(f'<p class="detail">{esc(spot.get("detail"))}</p>')
        panel.append(_evidence_list(_items(spot)))
        panel.append("</div>")

    note = str(city.get("preference_note") or "")
    lines = [ln.strip() for ln in note.splitlines() if ln.strip()]
    panel.append(f'<div class="pref" data-preference-note="{name}">')
    panel.append("<h4>왜 이 관광지를 골랐는가</h4>")
    for line in lines:
        panel.append(f"<p>{esc(line)}</p>")
    panel.append("</div>")
    return "".join(panel)


def _feature2(cities: list, rules: dict) -> str:
    """도시와 관광지. 계약의 `layout` 이 `drawer` 면 우측 툴바, `accordion` 이면 펼침이다.

    ★ 아코디언일 때는 툴바가 없으므로 **뒤로 가기 단추도 없다.** 계약이 그 둘을 함께
      정하도록 되어 있고(`back_button`), 검사기도 계약을 보고 그 행을 만든다.
      돌아갈 곳 없는 단추를 그리면 화면과 계약이 어긋난다.
    """
    layout = str(rules.get("layout") or "drawer")
    if layout != "drawer":
        parts = ['<section id="feature2"><h2>2. 도시와 관광지</h2>',
                 '<p class="hint">도시를 누르면 관광지 목록이 아래로 펼쳐집니다.</p>']
        sections = []
        for city in cities:
            name = str(city.get("name"))
            count = len(_as_list(city.get("spots")))
            sections.append((name, f"{name} · 관광지 {count}곳", _city_body(city, rules)))
        #  ★ 도시 단추와 도시 칸에 `data-city` · `data-city-panel` 을 함께 단다.
        #    배치는 아코디언이지만 검사기가 찾는 이름표는 배치와 무관하게 같다.
        marks = {key: (f' data-city="{esc(key)}"', f' data-city-panel="{esc(key)}"')
                 for key, _label, _body in sections}
        parts.append(_layout_block("feature2", "accordion", sections, marks))
        parts.append("</section>")
        return "".join(parts)

    parts = ['<section id="feature2"><h2>2. 도시와 관광지</h2>',
             '<p class="hint">도시를 누르면 오른쪽에 관광지 목록이 열립니다.</p>',
             '<div class="city-row">']
    for city in cities:
        name = esc(city.get("name"))
        parts.append(
            f'<button class="city-card" data-city="{name}">{name}'
            f'<span class="cnt">관광지 {len(_as_list(city.get("spots")))}곳</span></button>')
    parts.append('</div>')

    parts.append('<aside id="city-drawer" class="drawer" hidden>')
    if rules.get("back_button"):
        parts.append('<button class="back" data-back="1">← 뒤로 가기</button>')
    for city in cities:
        name = esc(city.get("name"))
        parts.append(f'<div class="city-panel" data-city-panel="{name}" hidden>'
                     + _city_body(city, rules) + "</div>")
    parts.append("</aside></section>")
    return "".join(parts)

# --------------------------------------------------------------------------- #
# 기능 3 — 도시별 일정 (아코디언)
# --------------------------------------------------------------------------- #


def _feature3(cities: list, rules: dict) -> str:
    """일정은 **도시 칸 안에서** 도시마다 완결된다.

    `data-day` 를 도시 칸(`acc-panel`) 안에 두는 것이 계약이다. 전역으로 흩어 놓으면
    한 도시에 일정을 몰아 넣어도 "일자 칸 5개"로 세어져 통과해 버린다.
    하루 안의 `data-block="HH:MM-HH:MM"` 은 "오전/오후" 두 덩어리로 뭉개는 것을 막는다.
    """
    layout = str(rules.get("layout") or "accordion")
    parts = ['<section id="feature3"><h2>3. 도시별 일정</h2>',
             '<p class="hint">도시마다 여행 일수만큼의 일정이 따로 있습니다. '
             '하루는 시간 블록으로 나뉩니다.</p>']
    sections = []
    for city in cities:
        name = str(city.get("name"))
        plan = _as_dict(city.get("itinerary"))
        body = ["<h4>일정을 이렇게 짠 근거</h4>", _evidence_list(_items(plan))]
        for day in _as_list(plan.get("days")):
            if not isinstance(day, dict):
                continue
            body.append(f'<div class="day" data-day="{esc(day.get("day"))}">')
            body.append(f'<h5>{esc(day.get("day"))}일차</h5><ul>')
            for block in _as_list(day.get("blocks")):
                if not isinstance(block, dict):
                    continue
                span = f'{esc(block.get("start"))}-{esc(block.get("end"))}'
                where = esc(block.get("spot") or block.get("place"))
                body.append(
                    f'<li data-block="{span}"><b>{span}</b>'
                    f'<span class="kind">{esc(block.get("kind"))}</span>'
                    f'{where} — {esc(block.get("why"))}</li>')
            body.append("</ul></div>")
        sections.append((name, name + " 일정", "".join(body)))
    parts.append(_layout_block("feature3", layout, sections))
    parts.append("</section>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# 스타일 · 동작
# --------------------------------------------------------------------------- #

CSS = """
:root{--pri:#1F6FEB;--bg:#F7F9FC;--card:#FFF;--line:#D8E0EC;--ink:#111827;--dim:#5B6676}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font-family:'Pretendard','Malgun Gothic',system-ui,sans-serif;line-height:1.6}
header{background:var(--pri);color:#fff;padding:26px 32px}
header h1{margin:0 0 4px;font-size:26px}
header p{margin:0;opacity:.85;font-size:14px}
main{max-width:1080px;margin:0 auto;padding:24px 20px 80px}
section{background:var(--card);border:1px solid var(--line);border-radius:14px;
 padding:20px 22px;margin-bottom:22px}
h2{margin:0 0 14px;font-size:20px;color:var(--pri)}
h3{font-size:17px;margin:14px 0 6px}
h4{font-size:15px;margin:12px 0 4px}
h5{font-size:13px;margin:10px 0 3px;color:var(--dim)}
.hero-row{display:flex;gap:14px;align-items:flex-start;margin-bottom:14px}
.flag{width:120px;height:auto;max-height:90px;object-fit:contain;
 border:1px solid var(--line);border-radius:8px}
.hero{flex:1;min-width:0;max-height:200px;object-fit:cover;border-radius:8px}
.acc-header{display:flex;justify-content:space-between;width:100%;text-align:left;
 background:#EEF3FA;border:1px solid var(--line);border-radius:9px;padding:10px 14px;
 margin-top:8px;font-size:15px;font-weight:700;cursor:pointer}
.acc-header.open{background:var(--pri);color:#fff}
.acc-panel{border:1px solid var(--line);border-top:0;border-radius:0 0 9px 9px;
 padding:12px 16px;display:none}
.acc-panel.open{display:block}
.tab-row{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 0}
.tab-btn{background:#EEF3FA;border:1px solid var(--line);border-bottom:0;
 border-radius:9px 9px 0 0;padding:9px 16px;font-size:14px;font-weight:700;cursor:pointer}
.tab-btn.on{background:var(--pri);color:#fff}
.tab-panel{border:1px solid var(--line);border-radius:0 9px 9px 9px;padding:12px 16px}
.ev{margin:4px 0 10px;padding-left:18px;font-size:14px}
.ev li{margin-bottom:5px}
.src{font-size:11px;color:var(--dim);word-break:break-all}
.empty{font-size:13px;color:#B45309}
.city-row{display:flex;gap:12px;flex-wrap:wrap}
.city-card{background:#EEF3FA;border:1px solid var(--line);border-radius:11px;
 padding:14px 20px;font-size:16px;font-weight:700;cursor:pointer;text-align:left}
.city-card .cnt{display:block;font-size:12px;font-weight:400;color:var(--dim)}
.drawer{position:fixed;top:0;right:0;width:min(460px,92vw);height:100vh;overflow-y:auto;
 background:#fff;border-left:2px solid var(--pri);padding:18px 20px;
 box-shadow:-8px 0 24px rgba(0,0,0,.12);z-index:9}
.back{background:var(--pri);color:#fff;border:0;border-radius:8px;
 padding:7px 14px;font-size:13px;cursor:pointer;margin-bottom:10px}
.spot-card{display:block;width:100%;text-align:left;background:#F4F7FC;
 border:1px solid var(--line);border-radius:9px;padding:9px 13px;margin-top:7px;
 font-size:14px;font-weight:600;cursor:pointer}
.spot-detail{border:1px solid var(--line);border-top:0;padding:10px 13px;font-size:13px}
.spot-img{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;
 border-radius:8px;margin-bottom:8px;background:#EEF3FA}
.no-img{background:#FEF3C7;border:1px dashed #D97706;border-radius:8px;
 padding:16px;text-align:center;font-size:13px;color:#92400E;margin-bottom:8px}
.detail{font-size:13px}
.pref{background:#F6F8FB;border-left:4px solid var(--pri);border-radius:8px;
 padding:10px 14px;margin-top:14px}
.pref p{font-size:13px;margin:4px 0}
.why{font-size:13px;color:var(--dim)}
.hint{font-size:13px;color:var(--dim)}
.day{border-left:3px solid var(--pri);padding-left:11px;margin:10px 0}
.day ul{margin:4px 0;padding-left:18px;font-size:13px}
.day li{margin-bottom:4px}
.day li b{color:var(--pri);margin-right:6px}
.kind{display:inline-block;background:#E3ECF9;border-radius:5px;
 padding:0 6px;margin-right:6px;font-size:11px;color:#24457A}
footer{max-width:1080px;margin:0 auto;padding:0 20px 40px;font-size:12px;color:var(--dim)}
"""

JS = """
document.addEventListener('click', function (e) {
  var tab = e.target.closest('button[data-tab]');
  if (tab) {
    var tarea = tab.getAttribute('data-tab-area'), tkey = tab.getAttribute('data-tab');
    document.querySelectorAll('[data-tab-panel]').forEach(function (p) {
      if (p.getAttribute('data-tab-area') !== tarea) { return; }
      p.hidden = p.getAttribute('data-tab-panel') !== tkey;
    });
    document.querySelectorAll('button[data-tab]').forEach(function (b) {
      if (b.getAttribute('data-tab-area') === tarea) {
        b.classList.toggle('on', b === tab);
      }
    });
    return;
  }
  var acc = e.target.closest('.acc-header[data-acc]');
  if (acc) {
    var area = acc.getAttribute('data-acc'), key = acc.getAttribute('data-key');
    /* 이름을 셀렉터에 이어 붙이지 않는다. 도시·관광지 이름에 따옴표가 들어가면
       querySelector 가 SyntaxError 를 내고 그 아코디언이 통째로 죽는다. */
    document.querySelectorAll('.acc-panel[data-acc][data-key]').forEach(function (p) {
      if (p.getAttribute('data-acc') !== area) { return; }
      if (p.getAttribute('data-key') !== key) { return; }
      p.classList.toggle('open');
      acc.classList.toggle('open');
    });
    return;
  }
  var city = e.target.closest('button[data-city]');
  if (city) {
    var name = city.getAttribute('data-city');
    document.querySelectorAll('[data-city-panel]').forEach(function (p) {
      var mine = p.getAttribute('data-city-panel') === name;
      p.hidden = !mine;
      p.classList.toggle('open', mine);
    });
    var drawer = document.getElementById('city-drawer');
    if (drawer) { drawer.hidden = false; }
    return;
  }
  var spot = e.target.closest('button[data-spot]');
  if (spot) {
    var sn = spot.getAttribute('data-spot');
    /* 위와 같은 이유로 값을 셀렉터에 넣지 않고 속성을 비교한다. */
    document.querySelectorAll('[data-spot-detail]').forEach(function (box) {
      if (box.getAttribute('data-spot-detail') !== sn) { return; }
      box.hidden = !box.hidden;
    });
    return;
  }
  var back = e.target.closest('[data-back]');
  if (back) {
    var d = document.getElementById('city-drawer');
    if (d) { d.hidden = true; }
  }
});
"""


# --------------------------------------------------------------------------- #
# 조립
# --------------------------------------------------------------------------- #

#: 예전에는 `rules` 에서 `headers` · `header_slots` · `spot_images` 만 꺼내 쓰고
#: `layout` 은 아예 읽지 않았다. 그래서 계약에 무엇을 적든 한 배치만 나왔다 —
#: 루프 킷에서 교육생이 고른 `D-페이지구성` 이 그래프판 화면에 닿지 않았고,
#: "두 판을 같은 계약으로 잰다"는 전제가 화면 배치에서만 조용히 깨져 있었다.
#: 그다음에는 어긋나면 멈추게 했는데, 멈추는 것은 사고를 막을 뿐 교육생이 고른 배치를
#: 만들어 주지는 않았다 — 수집을 다 끝낸 뒤 `build_page` 에서 죽었다.
#:
#: **지금은 계약이 정한 배치를 그대로 만든다.** 검사기는 이미 아코디언 · 탭 · 툴바를
#: 다 검사할 줄 알았으므로, 렌더러가 따라오면서 계약 · 렌더러 · 검사기가 한 줄로 맞는다.


def render(data: dict) -> str:
    """수집 데이터 하나로 단일 HTML 문자열을 만든다. 외부 파일을 참조하지 않는다."""
    rules = contract.page_rules()
    country = data.get("country") or (contract.request_defaults().get("country") or "여행")
    days = data.get("days") or contract.request_defaults().get("days") or ""
    intro = _as_dict(data.get("country_intro"))
    cities = [c for c in _as_list(data.get("cities")) if isinstance(c, dict) and c.get("name")]

    return (
        "<!DOCTYPE html>\n<html lang=\"ko\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{esc(country)} {esc(days)}일 여행 정보</title>"
        f"<style>{CSS}</style></head><body>"
        f"<header><h1>{esc(country)} {esc(days)}일 여행 정보</h1>"
        "<p>LangGraph 그래프 실습 · 검사 계약은 루프 킷과 동일합니다</p></header><main>"
        + _feature1(intro, _as_dict(rules.get("feature1")), str(country))
        + _feature2(cities, _as_dict(rules.get("feature2")))
        + _feature3(cities, _as_dict(rules.get("feature3")))
        + "</main><footer>"
        f"생성: build_page 노드 · 도시 {len(cities)}개 · "
        f"검사: python scripts/verify_all.py</footer>"
        f"<script>{JS}</script></body></html>\n"
    )


def write(data: dict) -> str:
    """파일로 떨어뜨리고 경로를 돌려준다. 검사기가 읽는 자리와 같다."""
    contract.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    contract.HTML_OUT.write_text(render(data), encoding="utf-8")
    return str(contract.HTML_OUT.relative_to(contract.ROOT)).replace("\\", "/")


__all__ = ["render", "write"]
