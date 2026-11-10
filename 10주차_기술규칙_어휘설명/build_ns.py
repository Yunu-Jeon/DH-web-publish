# -*- coding: utf-8 -*-
"""어휘설명.ttl 을 읽어 Namespace URI 에 둘 정의서(ns.html)와 RDF 파일(ns.ttl, ns.rdf, ns.jsonld)을 만든다.
사용: py build_ns.py <어휘설명.ttl> <출력 폴더>
"""
import sys, html, datetime
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD, DCTERMS

SRC, OUT = Path(sys.argv[1]), Path(sys.argv[2])
NS = "https://yunu-jeon.github.io/DH-Korean-Diaspora/ns#"
ONT = URIRef(NS.rstrip("#"))
DIA = Namespace(NS)
VANN = Namespace("http://purl.org/vocab/vann/")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
SKOSXL = Namespace("http://www.w3.org/2008/05/skos-xl#")
VERSION, ISSUED = "1.1", datetime.date(2026, 11, 3).isoformat()

# AP(application-profile.md §3)에서 각 용어가 쓰이는 클래스
USED_IN = {
    "Scene": ["생활 장면(클래스 자체)"],
    "aspect": ["생활 장면", "생활 대상"],
    "citation": ["자료", "생활 장면", "어휘"],
    "variantForm": ["어휘"], "gloss": ["어휘"], "denotes": ["어휘"],
    "sourceLanguage": ["어휘"], "etymologyNote": ["어휘"],
    "basis": ["모든 클래스의 값 주석(value annotation)"],
}
SHORT = {str(RDFS): "rdfs:", str(XSD): "xsd:", str(SKOS): "skos:", str(SKOSXL): "skosxl:", NS: "dia:"}

g = Graph().parse(SRC)
# 온톨로지 머리 정보
g.add((ONT, RDF.type, OWL.Ontology))
g.add((ONT, DCTERMS.title, Literal("Diaspora Ontology", lang="en")))
g.add((ONT, RDFS.label, Literal("Diaspora Ontology", lang="en")))
g.add((ONT, DCTERMS.description, Literal(
    "「한 뿌리, 다른 땅: 한인 디아스포라 생활문화·어휘 아카이브」의 커스텀 어휘. "
    "Dublin Core·SKOS·SKOS-XL 등 표준 어휘에 없는 클래스 1개와 속성 8개를 정의한다.", lang="ko")))
g.add((ONT, DCTERMS.creator, Literal("Yunu-Jeon")))
g.add((ONT, DCTERMS.issued, Literal(ISSUED, datatype=XSD.date)))
g.add((ONT, OWL.versionInfo, Literal(VERSION)))
g.add((ONT, VANN.preferredNamespacePrefix, Literal("dia")))
g.add((ONT, VANN.preferredNamespaceUri, Literal(NS, datatype=XSD.anyURI)))
g.add((ONT, RDFS.seeAlso, URIRef("https://yunu-jeon.github.io/DH-Korean-Diaspora/")))
terms = sorted({s for s in g.subjects(RDF.type, None) if str(s).startswith(NS)},
               key=lambda s: (0 if (s, RDF.type, RDFS.Class) in g else 1, str(s)))
for t in terms:
    g.add((t, RDFS.isDefinedBy, ONT))
for p, n in [("dia", DIA), ("vann", VANN), ("owl", OWL), ("dcterms", DCTERMS),
             ("skos", SKOS), ("skosxl", SKOSXL)]:
    g.bind(p, n, override=True)

OUT.mkdir(parents=True, exist_ok=True)
g.serialize(OUT / "ns.ttl", format="turtle", encoding="utf-8")
g.serialize(OUT / "ns.rdf", format="pretty-xml", encoding="utf-8")
g.serialize(OUT / "ns.jsonld", format="json-ld", encoding="utf-8", indent=2)


def short(u):
    s = str(u)
    for full, pre in SHORT.items():
        if s.startswith(full):
            return pre + s[len(full):]
    return s


def link(u):
    s = str(u)
    href = "#" + s[len(NS):] if s.startswith(NS) else s
    return f'<a href="{html.escape(href)}"><code>{html.escape(short(u))}</code></a>'


def one(t, p):
    v = g.value(t, p)
    return str(v) if v is not None else ""


esc = html.escape
toc, sections = [], []
for t in terms:
    local = str(t)[len(NS):]
    is_class = (t, RDF.type, RDFS.Class) in g
    kind = "클래스" if is_class else "속성"
    toc.append(f'<li><a href="#{local}"><code>dia:{local}</code></a> {esc(one(t, RDFS.label))} <span class="ns-kind">{kind}</span></li>')
    rows = [("IRI", f"<code>{esc(str(t))}</code>"),
            ("유형", f"<code>{'rdfs:Class' if is_class else 'rdf:Property'}</code>"),
            ("정의", esc(one(t, RDFS.comment)))]
    if g.value(t, RDFS.domain) is not None:
        rows.append(("정의역(domain)", link(g.value(t, RDFS.domain))))
    if g.value(t, RDFS.range) is not None:
        rows.append(("치역(range)", link(g.value(t, RDFS.range))))
    rows.append(("AP에서 쓰는 곳", esc(", ".join(USED_IN.get(local, [])))))
    body = "\n".join(f"<tr><th scope=\"row\">{k}</th><td>{v}</td></tr>" for k, v in rows)
    sections.append(f"""    <section class="ns-term" id="{local}">
      <h3><code>dia:{local}</code> — {esc(one(t, RDFS.label))}</h3>
      <table class="ns-table">
{body}
      </table>
    </section>""")

n_class = sum(1 for t in terms if (t, RDF.type, RDFS.Class) in g)
page = f"""<!doctype html>
<html lang="ko">
<head>
  <!-- 문서 기본 정보 -->
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Diaspora Ontology (dia) — 한 뿌리, 다른 땅</title>
  <meta name="description" content="한 뿌리, 다른 땅 아카이브의 커스텀 어휘 Diaspora Ontology(dia:) 정의서">
  <!-- 기계가 읽는 같은 어휘 -->
  <link rel="alternate" type="text/turtle" href="ns.ttl">
  <link rel="alternate" type="application/rdf+xml" href="ns.rdf">
  <link rel="alternate" type="application/ld+json" href="ns.jsonld">
  <!-- 파비콘(로고 SVG) -->
  <link rel="icon" href="assets/img/favicon.svg" type="image/svg+xml">
  <!-- 글꼴: 본문 Noto Sans KR, 제목 Noto Serif KR(명조) -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700&family=Noto+Serif+KR:wght@500;600;700&display=swap">
  <!-- 사이트 스타일 -->
  <link rel="stylesheet" href="assets/css/style.css">
  <style>
    .ns-table {{ width: 100%; border-collapse: collapse; margin: 0 0 8px; }}
    .ns-table th, .ns-table td {{ text-align: left; vertical-align: top; padding: 10px 12px; border-top: 1px solid var(--line); }}
    .ns-table th {{ width: 9.5em; color: var(--ink-3); font-weight: 600; }}
    .ns-table td {{ overflow-wrap: anywhere; }}
    .ns-term {{ background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 18px 20px 10px; margin: 0 0 18px; scroll-margin-top: calc(var(--header-h) + 12px); }}
    .ns-term h3 {{ margin: 0 0 10px; }}
    .ns-term:target {{ border-color: var(--accent); }}
    .ns-kind {{ color: var(--ink-3); font-size: 0.88em; }}
    .ns-toc {{ columns: 2 16em; padding-left: 1.2em; }}
    .ns-formats a {{ margin-right: 0.8em; }}
    @media (max-width: 640px) {{
      .ns-table th, .ns-table td {{ display: block; width: auto; }}
      .ns-table th {{ padding-bottom: 2px; }}
      .ns-table td {{ border-top: 0; padding-top: 0; }}
      .ns-term {{ padding: 14px 14px 6px; }}
    }}
  </style>
</head>
<body>
  <!-- 본문 바로가기(키보드 사용자용) -->
  <a class="skip-link" href="#main">본문 바로가기</a>

  <!-- 헤더: 로고와 제목(홈으로), 긴 검색창 -->
  <header class="site-header">
    <div class="header-inner">
      <a class="brand" href="index.html" aria-label="한 뿌리, 다른 땅 — 홈">
        <svg class="logo" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
          <g fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M16 26 V17"/><path d="M16 17 C16 13 11 12 7.5 8.5"/><path d="M16 17 V6.5"/><path d="M16 17 C16 13 21 12 24.5 8.5"/></g>
          <circle cx="16" cy="26" r="2.8" fill="var(--accent)"/><circle cx="7.5" cy="8.5" r="2" fill="currentColor"/><circle cx="16" cy="6.5" r="2" fill="currentColor"/><circle cx="24.5" cy="8.5" r="2" fill="currentColor"/>
        </svg>
        <span>한 뿌리, 다른 땅</span>
      </a>
      <!-- 검색창: 돋보기 아이콘과 굵은 테두리로 눈에 띄게 -->
      <form class="search-form" role="search" action="search.html" method="get">
        <svg class="search-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><g fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/></g></svg>
        <label class="sr-only" for="site-q">아카이브 검색(어휘·음식·장면, 이표기 포함)</label>
        <input id="site-q" name="q" type="search" placeholder="말·음식·장면 검색 (예: Kim Chee, 김치)" autocomplete="off">
        <button type="submit">검색</button>
      </form>
    </div>
  </header>

  <main id="main">
    <!-- 이 파일은 build_ns.py 로 어휘설명.ttl 에서 만든 것입니다 -->
    <h1>Diaspora Ontology</h1>
    <p>{esc(one(ONT, DCTERMS.description))}</p>

    <table class="ns-table">
      <tr><th scope="row">Namespace URI</th><td><code>{NS}</code></td></tr>
      <tr><th scope="row">접두어</th><td><code>dia</code></td></tr>
      <tr><th scope="row">버전</th><td>{VERSION} ({ISSUED})</td></tr>
      <tr><th scope="row">만든 이</th><td>Yunu-Jeon</td></tr>
      <tr><th scope="row">내려받기</th><td class="ns-formats"><a href="ns.ttl">Turtle</a><a href="ns.rdf">RDF/XML</a><a href="ns.jsonld">JSON-LD</a></td></tr>
    </table>
    <p>Omeka S 같은 도구에서 이 어휘를 가져올 때는 위 Namespace URI 와 접두어 <code>dia</code>를 그대로 쓰고, 파일 URL 로 <code>ns.ttl</code> 또는 <code>ns.rdf</code>의 주소를 넣습니다.</p>

    <h2>용어 목록 (클래스 {n_class}개, 속성 {len(terms) - n_class}개)</h2>
    <ul class="ns-toc">
      {chr(10).join('      ' + x for x in toc).strip()}
    </ul>

    <h2>용어 정의</h2>
{chr(10).join(sections)}
  </main>

  <!-- 푸터 -->
  <footer class="site-footer">
    <div class="inner">
      <p>Diaspora Ontology — 「한 뿌리, 다른 땅」의 응용 프로파일(AP)에 쓰이는 커스텀 어휘입니다. <a href="index.html">아카이브 홈</a></p>
    </div>
  </footer>
</body>
</html>
"""
(OUT / "ns.html").write_text(page, encoding="utf-8")
print("terms", len(terms), "triples", len(g))
