# -*- coding: utf-8 -*-
"""Omeka S 사이트 「한 뿌리, 다른 땅」(/s/hanppuri)에 '자료에게 묻기' 페이지를 만든다(있으면 고친다).
페이지 = 안내(HTML 블록) + 빈 자리 <div class="ask-app">. 화면과 동작은 테마의 asset/js/ask.js 가 그린다
(자연어 질문 → SPARQL → Sparql 모듈 엔드포인트 /sparql → 자연어 답).
사이트 메뉴에는 기존 항목을 지우지 않고 맨 뒤에 덧붙인다.
사용: py build_ask.py <키 JSON: {"key_identity": …, "key_credential": …}>
"""
import sys, json, urllib.request, urllib.parse                     # 표준 라이브러리만 쓴다
from pathlib import Path                                            # 파일 경로

BASE = "http://localhost:8000/api"                                  # Omeka S REST API
KEY = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))     # API 키(저장소에 넣지 않는다)
SITE_SLUG, PAGE_SLUG = "hanppuri", "ask"                            # 사이트와 페이지의 주소 이름

INTRO = """<p class="eyebrow">자료에게 묻기</p>
<h1>질문하면, 그래프에서 찾아 답합니다</h1>
<p class="lead">궁금한 것을 우리말로 물으면 질문을 SPARQL 질의로 바꿔 그라운딩 결과 지식그래프(장면 40 · 어휘 34 · 생활 대상 26 · 장소 18 · 문화권 3 · 출처 13)를 검색하고, 찾은 결과를 문장으로 돌려줍니다. 답 아래에서 실제로 보낸 SPARQL 과 결과 표를 그대로 볼 수 있습니다.</p>
<p class="hint">답은 그래프에 있는 값만으로 만듭니다. 근거 쪽수는 카드마다 붙어 있고, 원 아카이브의 개별 자원으로 이어집니다.</p>
<div class="ask-app"></div>"""


def api(method, path, data=None, params=None):                      # API 한 번 부르기
    url = f"{BASE}/{path}?{urllib.parse.urlencode({**(params or {}), **KEY}, doseq=True)}"  # 키를 붙인 주소
    req = urllib.request.Request(url, method=method, headers={"Content-Type": "application/json"},
                                 data=json.dumps(data).encode("utf-8") if data is not None else None)
    try:
        with urllib.request.urlopen(req) as r:                      # 보내고
            return json.loads(r.read() or b"null")                  # JSON 으로 받는다
    except urllib.error.HTTPError as e:                             # 실패하면 이유를 보이고 끝낸다
        raise SystemExit(f"{method} {path} → {e.code}: {e.read().decode('utf-8')[:600]}")


def main():
    site = next((s for s in api("GET", "sites") if s["o:slug"] == SITE_SLUG), None)  # 사이트 찾기
    if not site:
        raise SystemExit("사이트 /s/hanppuri 가 없습니다. 먼저 sparql/build_site.py 를 실행하세요.")
    page_data = {                                                   # 페이지 내용
        "o:site": {"o:id": site["o:id"]}, "o:title": "자료에게 묻기", "o:slug": PAGE_SLUG, "o:is_public": True,
        "o:block": [{"o:layout": "html", "o:data": {"html": INTRO}}],
    }
    pages = [p for p in api("GET", "site_pages", params={"site_id": site["o:id"]}) if p["o:slug"] == PAGE_SLUG]
    page = api("PUT", f"site_pages/{pages[0]['o:id']}", page_data) if pages else api("POST", "site_pages", page_data)

    nav = site.get("o:navigation") or []                            # 지금 메뉴
    if not any(n.get("type") == "page" and n.get("data", {}).get("id") == page["o:id"] for n in nav):  # 아직 없으면
        nav.append({"type": "page", "data": {"label": "", "id": page["o:id"]}, "links": []})  # 맨 뒤에 덧붙인다
        api("PATCH", f"sites/{site['o:id']}", {"o:navigation": nav})
    print(f"page {page['o:id']} → http://localhost:8000/s/{SITE_SLUG}/page/{PAGE_SLUG}")


main()
