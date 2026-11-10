# -*- coding: utf-8 -*-
"""기술규칙.dctap.csv 와 어휘설명.csv 를 읽어 기술규칙.ttl(SHACL) 과 어휘설명.ttl(RDFS) 로 인코딩한다.
사용: python csv2ttl.py   (CSV 두 개가 있는 폴더에서 실행)
"""
import csv                                                    # CSV 읽기
from collections import OrderedDict, defaultdict              # 순서를 지키는 dict, 기본값 있는 dict
from rdflib import Graph, Namespace, URIRef, Literal, BNode    # RDF 그래프 만들기
from rdflib.namespace import RDF, RDFS, XSD                   # 표준 네임스페이스
from rdflib.collection import Collection                      # sh:in, sh:or 에 쓰는 RDF 목록

SH = Namespace("http://www.w3.org/ns/shacl#")                 # SHACL(기술규칙의 언어)
DIA = Namespace("https://yunu-jeon.github.io/DH-Korean-Diaspora/ns#")  # 우리 커스텀 어휘
SHAPE = Namespace("https://yunu-jeon.github.io/DH-Korean-Diaspora/ap/shape/")  # 기술규칙 하나하나의 주소
PREFIX = {                                                    # CSV 의 'dcterms:title' 같은 줄임말을 풀 때 쓰는 표
    "dcterms": "http://purl.org/dc/terms/", "dctype": "http://purl.org/dc/dcmitype/",
    "bibo": "http://purl.org/ontology/bibo/", "foaf": "http://xmlns.com/foaf/0.1/",
    "skos": "http://www.w3.org/2004/02/skos/core#", "skosxl": "http://www.w3.org/2008/05/skos-xl#",
    "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#", "dia": str(DIA), "xsd": str(XSD),
    "rdf": str(RDF), "rdfs": str(RDFS),
}


def iri(x):                                                   # 줄임말이든 전체 주소든 URIRef 로
    x = x.strip()                                             # 앞뒤 공백 제거
    if x.startswith("http"):                                  # 이미 전체 주소면
        return URIRef(x)                                      # 그대로
    p, local = x.split(":", 1)                                # 'dcterms' 와 'title' 로 나눔
    return URIRef(PREFIX[p] + local)                          # 전체 주소로 이어 붙임


def new_graph():                                              # 접두어를 묶은 빈 그래프
    g = Graph()                                               # 그래프 생성
    g.bind("sh", SH)                                          # sh: 접두어
    for p, ns in PREFIX.items():                              # 나머지 접두어들
        g.bind(p, Namespace(ns), override=True, replace=True) # (rdflib 기본 geo: 를 덮어씀)
    return g


def read(path):                                               # CSV 를 dict 목록으로
    with open(path, encoding="utf-8-sig") as f:               # 엑셀 BOM 이 있어도 읽히게
        return list(csv.DictReader(f))                        # 첫 줄을 열 이름으로 쓰는 읽기


def encode_rules(rows, g):                                    # 기술규칙.dctap.csv → SHACL
    shapes = OrderedDict()                                    # shapeID → 그 규칙의 행들(나온 순서대로)
    for r in rows:                                            # 모든 행에 대해
        shapes.setdefault(r["shapeID"], []).append(r)         # 같은 shapeID 끼리 묶음
    for sid, props in shapes.items():                         # 클래스 하나 = 기술규칙 하나
        s = SHAPE[sid.replace(":", "-")]                      # 규칙의 주소(예: …/shape/dia-Scene)
        g.add((s, RDF.type, SH.NodeShape))                    # "이것은 SHACL 노드 규칙이다"
        g.add((s, SH.targetClass, iri(sid)))                  # 이 규칙이 검사할 클래스
        g.add((s, RDFS.label, Literal(props[0]["shapeLabel"], lang="ko")))  # 규칙 이름(사람용)
        for r in props:                                       # 속성 한 줄 = 속성 규칙 하나
            p = BNode()                                       # 이름 없는 노드로 속성 규칙을 만듦(견본과 같은 방식)
            g.add((s, SH.property, p))                        # 클래스 규칙에 매달기
            g.add((p, SH.path, iri(r["propertyID"])))         # 어느 속성인가
            g.add((p, SH.name, Literal(r["propertyLabel"], lang="ko")))  # 속성 이름(사람용)
            g.add((p, SH.minCount, Literal(1 if r["mandatory"] == "TRUE" else 0)))  # 필수면 최소 1
            if r["repeatable"] == "FALSE":                    # 반복 불가면
                g.add((p, SH.maxCount, Literal(1)))           # 최대 1
            note = r["note"]                                  # 비고 칸
            if r["valueNodeType"] == "IRI":                   # 값이 다른 자원(주소)이면
                g.add((p, SH.nodeKind, SH.IRI))               # IRI 여야 한다
                if note.startswith("대상 클래스: "):           # 비고에 대상 클래스가 적혀 있으면
                    targets = note.split(";")[0][len("대상 클래스: "):].split(" 또는 ")  # 'A 또는 B' 를 나눔
                    if len(targets) == 1:                     # 하나면
                        g.add((p, SH["class"], iri(targets[0])))  # sh:class 로
                    else:                                     # 여럿이면 '이 중 하나'(sh:or)
                        alts = []                             # 대안 목록
                        for t in targets:                     # 대안마다
                            b = BNode(); g.add((b, SH["class"], iri(t))); alts.append(b)  # [ sh:class t ]
                        head = BNode(); Collection(g, head, alts)  # RDF 목록으로 묶고
                        g.add((p, SH["or"], head))            # sh:or 에 단다
            else:                                             # 값이 글자(리터럴)면
                g.add((p, SH.datatype, XSD.string))           # 평문 문자열이어야 한다(@ko 면 위반)
                if note.startswith("값: "):                   # 정해진 값 목록이 있으면
                    vals = note.split(";")[0][len("값: "):].split(" / ")  # '먹는 것 / 부르는 것 …' 을 나눔
                    head = BNode(); Collection(g, head, [Literal(v.strip()) for v in vals])  # 목록으로
                    g.add((p, SH["in"], head))                # sh:in — 이 값들 중 하나여야 한다
            if note:                                          # 비고는 설명으로 남김
                g.add((p, SH.description, Literal(note, lang="ko")))


def encode_vocab(rows, g):                                    # 어휘설명.csv → RDFS 정의
    seen = defaultdict(set)                                   # 속성마다 이미 단 domain(중복 방지)
    for r in rows:                                            # 한 줄 = 속성 하나(+그 클래스)
        p = iri(r["propertyID"])                              # 속성 주소
        g.add((p, RDF.type, RDF.Property))                    # "이것은 속성이다"(termType)
        if (p, RDFS.comment, None) not in g:                  # 같은 속성이 여러 줄이면 이름·정의는 첫 줄 것 하나만
            g.add((p, RDFS.label, Literal(r["propertyLabel"], lang="ko")))  # 이름
            g.add((p, RDFS.comment, Literal(r["definition"], lang="ko")))  # 뜻풀이
        if r["domain"]:                                       # domain 칸이 차 있을 때만
            g.add((p, RDFS.domain, iri(r["domain"])))         # 이 속성을 쓰는 클래스
        if r["range"]:                                        # range 칸이 차 있으면
            g.add((p, RDFS.range, iri(r["range"])))           # 값의 종류
        if r["inverseOf"]:                                    # 역관계가 있으면
            g.add((p, URIRef("http://www.w3.org/2002/07/owl#inverseOf"), iri(r["inverseOf"])))
        if r["shapeClass"] == "rdfs:Class":                   # 이 줄의 클래스가 우리가 만든 클래스면
            c = iri(r["shapeID"])                             # 클래스 주소
            g.add((c, RDF.type, RDFS.Class))                  # "이것은 클래스다"
            g.add((c, RDFS.comment, Literal(r["shapeDefinition"], lang="ko")))  # 클래스 설명
            if r["subClassOf"]:                               # 상위 클래스가 적혀 있으면
                g.add((c, RDFS.subClassOf, iri(r["subClassOf"])))


if __name__ == "__main__":
    rules, vocab = read("기술규칙.dctap.csv"), read("어휘설명.csv")  # CSV 두 개 읽기
    names = {r["shapeID"]: r["shapeLabel"] for r in rules}   # 클래스의 한국어 이름은 기술규칙 쪽에 있다

    v = new_graph()                                           # 어휘설명 그래프
    encode_vocab(vocab, v)                                    # 인코딩
    for row in vocab:                                         # 우리가 만든 클래스에 한국어 이름 붙이기
        if row["shapeClass"] == "rdfs:Class":
            key = next(k for k in names if iri(k) == iri(row["shapeID"]))  # 같은 클래스를 기술규칙에서 찾아
            v.add((iri(row["shapeID"]), RDFS.label, Literal(names[key], lang="ko")))
    v.serialize("어휘설명.ttl", format="turtle", encoding="utf-8")  # 저장

    r = new_graph()                                           # 기술규칙 그래프
    encode_rules(rules, r)                                    # SHACL 인코딩
    r += v                                                    # 견본처럼 끝에 커스텀 어휘 정의를 동봉
    r.serialize("기술규칙.ttl", format="turtle", encoding="utf-8")  # 저장
    print(f"기술규칙 {len(rules)}행 → 기술규칙.ttl ({len(r)} 트리플) · 어휘설명 {len(vocab)}행 → 어휘설명.ttl ({len(v)} 트리플)")
