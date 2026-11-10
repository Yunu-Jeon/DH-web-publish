# -*- coding: utf-8 -*-
"""queries.json 으로 Omeka S 공개 사이트 「한 뿌리, 다른 땅」의 'SPARQL 검색' 페이지를 만든다(있으면 고친다).
페이지 = 안내와 예제 질의 링크(HTML 블록) + Sparql 모듈의 검색 블록. 링크를 누르면 ?query= 로 질의가 채워져 바로 실행된다.
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


def intro_html():
    """정적 사이트의 홈 소개(작은 머리말·큰 제목·리드)와 장면 카드 모양을 쓴다(클래스는 hanppuri 테마 CSS)."""
    out = [
        '<p class="eyebrow">SPARQL 검색</p>',
        "<h1>그라운딩 결과 검색</h1>",
        '<p class="lead">10주차 기술규칙(AP)으로 만든 그라운딩 결과 <code>한뿌리다른땅.ttl</code>(트리플 2,439개)을 SPARQL 로 검색합니다. '
        "예제 카드의 ‘실행’을 누르면 질의가 아래 검색 칸에 채워지고 결과 표가 나옵니다. 질의를 고쳐 다시 검색할 수 있습니다.</p>",
        f'<p class="hint">그라운딩 결과는 그래프 <code>{html.escape(Q["graph"])}</code> 에 있으니 질의에 <code>FROM &lt;…&gt;</code> 을 붙입니다. '
        f'값마다 붙은 근거(값 종류·근거 쪽수·근거 출처)는 Omeka 값 주석에서 내보낸 그래프 <code>{html.escape(Q["evidence_graph"])}</code> 에 '
        '<code>rdf:Statement</code> 로 들어 있습니다(질의 11·12).</p>',
        '<p class="notice"><strong>쓸 때 주의</strong> — 이 저장소(ARC2)는 필수 패턴이 5개 이상이면 오류가 나므로 4개까지만 쓰고 '
        '나머지는 <code>OPTIONAL</code> 로 감쌉니다. <code>REGEX</code> 에는 늘 <code>"i"</code> 옵션을 붙입니다.</p>',
        "<h2>예제 질의</h2>",
        '<div class="card-grid">',
    ]
    for n, q in enumerate(Q["queries"], 1):
        href = "?" + urllib.parse.urlencode({"query": full_query(q)}) + "#sparql-form"
        out.append(f'<div class="scene-card"><p class="card-meta">질의 {n:02d}</p>'
                   f'<h3 class="card-title">{html.escape(q["title"])}</h3>'
                   f'<p class="card-text">{html.escape(q["scenario"])}</p>'
                   f'<p class="card-actions"><a class="btn btn-primary" href="{html.escape(href)}">실행</a></p></div>')
    out.append("</div>")
    out.append("<h2>검색</h2>")
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
        ],
    }
    pages = [p for p in api("GET", "site_pages", params={"site_id": site["o:id"]}) if p["o:slug"] == PAGE_SLUG]
    page = api("PUT", f"site_pages/{pages[0]['o:id']}", page_data) if pages else api("POST", "site_pages", page_data)

    # 사이트 메뉴에 검색 페이지를 걸고 첫 페이지로 둔다
    nav = [{"type": "page", "data": {"label": "", "id": page["o:id"]}, "links": []}]
    api("PATCH", f"sites/{site['o:id']}", {"o:navigation": nav, "o:homepage": {"o:id": page["o:id"]},
                                           "o:theme": SITE["o:theme"]})
    print(f"site {site['o:id']} /s/{SITE['o:slug']} · page {page['o:id']} /s/{SITE['o:slug']}/page/{PAGE_SLUG}")


main()
