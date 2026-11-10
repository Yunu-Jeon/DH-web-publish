# -*- coding: utf-8 -*-
"""Omeka S 의 값 주석(근거(provenance) 템플릿)을 SPARQL 로 찾을 수 있는 Turtle 로 내보낸다.
Sparql 모듈은 값 주석을 인덱싱하지 않고 ARC2 는 RDF-star 를 모르므로, 값 하나를 rdf:Statement 노드 하나로 적는다.

  <…/graph/evidence/item-62-v3> a rdf:Statement ;
      rdf:subject   <http://localhost:8000/api/items/62> ;      # Omeka 인덱스와 같은 아이템 IRI
      rdf:predicate skosxl:literalForm ;
      rdf:object    "Kim Chee"@en ;
      dia:basis "보고" ; prov:atLocation "lee2014:78" ; prov:wasDerivedFrom <http://localhost:8000/api/items/9> .

사용: py export_evidence.py <키 JSON> <출력.ttl>
그 뒤: docker cp 출력.ttl 컨테이너:/tmp/evidence.ttl
      docker exec 컨테이너 php /tmp/load_ttl.php /tmp/evidence.ttl https://yunu-jeon.github.io/DH-Korean-Diaspora/graph/evidence
"""
import sys, json, urllib.request, urllib.parse
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, SKOS

BASE = "http://localhost:8000/api"
KEY = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
OUT = Path(sys.argv[2])
EV = Namespace("https://yunu-jeon.github.io/DH-Korean-Diaspora/graph/evidence/")
DIA = Namespace("https://yunu-jeon.github.io/DH-Korean-Diaspora/ns#")
PROV = Namespace("http://www.w3.org/ns/prov#")


def get(path, **params):
    url = f"{BASE}/{path}?{urllib.parse.urlencode({**params, **KEY})}"
    with urllib.request.urlopen(url) as r:
        return json.load(r)


_iri = {}
def prop_iri(pid):  # 속성 ID → 전체 IRI(어휘 네임스페이스 + 로컬 이름)
    if pid not in _iri:
        p = get(f"properties/{pid}")
        ns = get(f"vocabularies/{p['o:vocabulary']['o:id']}")["o:namespace_uri"]
        _iri[pid] = URIRef(ns + p["o:local_name"])
    return _iri[pid]


def term(v):  # Omeka 값 → RDF 항
    if v.get("value_resource_id"):
        return URIRef(f"{BASE}/{v.get('value_resource_name', 'items')}/{v['value_resource_id']}")
    if v.get("type") == "uri" or (v.get("@id") and "@value" not in v):
        return URIRef(v["@id"])
    return Literal(v["@value"], lang=v.get("@language") or None)


def main():
    g = Graph()
    for p, ns in [("ev", EV), ("dia", DIA), ("prov", PROV), ("skos", SKOS)]:
        g.bind(p, ns)
    page, items = 1, []
    while True:
        got = get("items", per_page=100, page=page)
        items += got
        if len(got) < 100:
            break
        page += 1

    n = 0
    for it in items:
        subject = URIRef(f"{BASE}/items/{it['o:id']}")
        k = 0
        for key, vals in it.items():
            if ":" not in key or not isinstance(vals, list):
                continue
            for v in vals:
                if not isinstance(v, dict) or "property_id" not in v:
                    continue
                k += 1  # 아이템 안에서 값의 순번(노드 이름이 다시 내보내도 같게)
                ann = v.get("@annotation")
                if not ann:
                    continue
                st = EV[f"item-{it['o:id']}-v{k}"]
                g.add((st, RDF.type, RDF.Statement))
                g.add((st, RDF.subject, subject))
                g.add((st, RDF.predicate, prop_iri(v["property_id"])))
                g.add((st, RDF.object, term(v)))
                for akey, avals in ann.items():
                    if ":" not in akey:
                        continue
                    for av in avals:
                        if isinstance(av, dict) and "property_id" in av:
                            g.add((st, prop_iri(av["property_id"]), term(av)))
                n += 1
    OUT.write_text(g.serialize(format="turtle"), encoding="utf-8")
    print(f"아이템 {len(items)}개 · 근거 붙은 값 {n}개 · 트리플 {len(g)}개 → {OUT}")


main()
