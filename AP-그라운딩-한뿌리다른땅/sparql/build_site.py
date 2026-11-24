# -*- coding: utf-8 -*-
"""queries.json 으로 Omeka S 공개 사이트 「한 뿌리, 다른 땅」의 'SPARQL 검색' 페이지를 만든다(있으면 고친다).
페이지 = 머리말(HTML 블록) + Sparql 모듈의 검색 블록 + 예제 질의 카드(HTML 블록). 카드를 누르면 ?query= 로 질의가 채워져 바로 실행된다.
사용: py build_site.py <키 JSON: {"key_identity": …, "key_credential": …}>
"""
import sys, json, html, urllib.request, urllib.parse
from pathlib import Path

BASE = "http://localhost:8000/api"
KEY = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
Q = json.loads((Path(__file__).parent / "queries.json").read_text(encoding="utf-8"))
SITE = {"o:title": "한 뿌리, 다른 땅", "o:slug": "hanppuri", "o:theme": "hanppuri"}  # 테마: omeka-themes/hanppuri
PAGE_SLUG = "sparql"


def api(method, path, data=None, params=None):
    url = f"{BASE}/{path}?{urllib.parse.urlencode({**(params or {}), **KEY}, doseq=True)}"
    req = urllib.request.Request(url, method=method, headers={"Content-Type": "application/json"},
                                 data=json.dumps(data).encode("utf-8") if data is not None else None)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} → {e.code}: {e.read().decode('utf-8')[:600]}")


def full_query(q):
    return Q["prefixes"] + q["query"].replace("GRAPH", Q["graph"])


# 예제 질의 묶음(queries.json 의 id → 묶음). 묶음에 없는 질의는 '그 밖의 질의'로 간다.
GROUPS = [
    ("말과 대상", ["word-search", "one-root", "borrowed-words", "interpretation"]),
    ("장면과 문화권", ["aspect-scenes", "group-aspect-count", "places"]),
    ("근거", ["scene-evidence", "pages-of-source", "basis-interpretation", "sentence-evidence"]),
    ("검수", ["to-check"]),
]


def intro_html():
    """머리말(정적 사이트 홈 소개와 같은 위계) + 데이터 규모 알약. 검색 칸은 바로 아래 Sparql 블록."""
    return "\n".join([
        '<p class="eyebrow">SPARQL 검색</p>',
        "<h1>그라운딩 결과를 질의로 찾기</h1>",
        '<p class="lead">10주차 기술규칙(AP)으로 만든 그라운딩 결과와, 값마다 달아 둔 근거를 SPARQL 로 검색합니다. '
        "아래 예제를 누르면 질의가 검색 칸에 채워지고 결과가 바로 나옵니다. 질의를 고쳐 다시 검색할 수 있습니다.</p>",
        '<ul class="stat-row">'
        '<li class="stat"><b>40</b>생활 장면</li><li class="stat"><b>34</b>어휘</li><li class="stat"><b>26</b>생활 대상</li>'
        '<li class="stat"><b>18</b>장소</li><li class="stat"><b>3</b>문화권</li><li class="stat"><b>13</b>출처</li>'
        '<li class="stat"><b>922</b>값 단위 근거</li></ul>',
    ])


def examples_html():
    """예제 질의를 묶음별 작은 카드로. 카드 전체가 링크이고 결과(#results)로 바로 내려간다."""
    by_id = {q["id"]: (n, q) for n, q in enumerate(Q["queries"], 1)}
    grouped = [(name, [by_id[i] for i in ids if i in by_id]) for name, ids in GROUPS]
    rest = [by_id[i] for i in by_id if not any(i in ids for _, ids in GROUPS)]
    if rest:
        grouped.append(("그 밖의 질의", rest))
    out = ['<div class="section-title"><h2>예제 질의</h2>'
           f'<p>그라운딩 그래프 <code>…/graph/grounding</code> · 값 단위 근거 그래프 <code>…/graph/evidence</code></p></div>']
    for name, items in grouped:
        out.append(f'<div class="example-group"><h3>{html.escape(name)}</h3><ul class="example-grid">')
        for n, q in items:
            href = "?" + urllib.parse.urlencode({"query": full_query(q)}) + "#results"
            out.append(f'<li><a class="example-card" href="{html.escape(href)}"><span class="num">{n:02d}</span>'
                       f'<strong>{html.escape(q["title"])}</strong><span class="desc">{html.escape(q["scenario"])}</span>'
                       '<span class="go">실행 →</span></a></li>')
        out.append("</ul></div>")
    out.append('<p class="notice"><strong>직접 쓸 때</strong> — 이 저장소(ARC2)는 필수 패턴이 5개 이상이면 오류가 나므로 4개까지만 쓰고 '
               '나머지는 <code>OPTIONAL</code> 로 감쌉니다. <code>REGEX</code> 에는 늘 <code>"i"</code> 옵션을 붙입니다. '
               '그라운딩 결과만 보려면 <code>FROM &lt;…/graph/grounding&gt;</code> 을 붙입니다.</p>')
    return "\n".join(out)


def main():
    sites = [s for s in api("GET", "sites") if s["o:slug"] == SITE["o:slug"]]
    site = sites[0] if sites else api("POST", "sites", {**SITE, "o:is_public": True,
                                                          "o:summary": "한인 디아스포라 생활문화·어휘 아카이브"})
    page_data = {
        "o:site": {"o:id": site["o:id"]}, "o:title": "SPARQL 검색", "o:slug": PAGE_SLUG, "o:is_public": True,
        "o:block": [
            {"o:layout": "html", "o:data": {"html": intro_html()}},
            {"o:layout": "sparql", "o:data": {"interface": "default"}},
            {"o:layout": "html", "o:data": {"html": examples_html()}},
        ],
    }
    pages = [p for p in api("GET", "site_pages", params={"site_id": site["o:id"]}) if p["o:slug"] == PAGE_SLUG]
    page = api("PUT", f"site_pages/{pages[0]['o:id']}", page_data) if pages else api("POST", "site_pages", page_data)

    # 사이트 메뉴: 이미 있는 항목(예: 자료에게 묻기)은 두고, 검색 페이지를 맨 앞, '자료 둘러보기'를 맨 뒤에 둔다
    nav = [n for n in site.get("o:navigation", [])
           if not (n["type"] == "page" and n["data"].get("id") == page["o:id"]) and n["type"] != "browse"]
    nav = ([{"type": "page", "data": {"label": "", "id": page["o:id"]}, "links": []}] + nav
           + [{"type": "browse", "data": {"label": "자료 둘러보기", "query": ""}, "links": []}])
    api("PATCH", f"sites/{site['o:id']}", {"o:navigation": nav, "o:homepage": {"o:id": page["o:id"]},
                                           "o:theme": SITE["o:theme"]})
    print(f"site {site['o:id']} /s/{SITE['o:slug']} · page {page['o:id']} /s/{SITE['o:slug']}/page/{PAGE_SLUG}")


main()
