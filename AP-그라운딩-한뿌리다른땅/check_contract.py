# -*- coding: utf-8 -*-
"""AP 그라운딩 가이드 §3 「조용한 실패」 표를 기계로 검사한다(스타터킷이 검사하지 않는 것들).
사용: python check_contract.py <데이터.ttl> [기술규칙.ttl]   — 위반이 있으면 종료 코드 1
"""
import re, sys                                          # 정규식, 인자·종료 코드
from collections import Counter, defaultdict            # 개수 세기
import rdflib                                           # Turtle 파싱
from rdflib import URIRef, Literal                      # 노드 종류 구분
from rdflib.namespace import RDF, RDFS, SKOS

RIC = "http://archives.nanet.go.kr/id/"
RICO = "https://www.ica.org/standards/RiC/ontology#"
STD = {"Person", "CorporateBody", "Position", "Event", "Activity", "Place", "Record", "RecordSet",
       "Instantiation", "Rule", "Concept", "ConceptScheme"}                          # §2.2 화면이 그리는 12종(지역명)
EDGE_NS = (RICO, str(SKOS), "http://xmlns.com/foaf/0.1/", "https://schema.org/", "http://archives.nanet.go.kr/voca#")  # §2.7
NAME = {"Record": RICO + "title", "RecordSet": RICO + "title", "Concept": str(SKOS.prefLabel),
        "ConceptScheme": str(SKOS.prefLabel)}           # §2.3 클래스별 이름 술어(나머지는 rico:name)
INVERSE = [("hasCreator", "isCreatorOf"), ("hasAuthor", "isAuthorOf"), ("hasOrHadSubject", "isOrWasSubjectOf"),
           ("occupiesOrOccupied", "isOrWasOccupiedBy"), ("hasOrHadPosition", "existsOrExistedIn"),
           ("isOrWasMemberOf", "hasOrHadMember"), ("includesOrIncluded", "isOrWasIncludedIn"),
           ("hasOrHadInstantiation", "isOrWasInstantiationOf"), ("isOrWasParticipantIn", "hasOrHadParticipant")]  # §2.9
DATE_P = {RICO + p for p in ("beginningDate", "endDate", "date", "birthDate", "deathDate")}
DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")      # §2.5 세 정밀도


def local(u):                                           # 소비자처럼 '#' 뒤(없으면 마지막 '/' 뒤) 지역명만 본다
    s = str(u)
    return s.rsplit("#", 1)[1] if "#" in s else s.rsplit("/", 1)[1]


def main(path):
    g = rdflib.Graph()
    g.parse(path, format="turtle")                     # 문법 오류면 여기서 예외 = 유일하게 시끄러운 실패
    errs, warns, info = [], [], []
    subjects = {s for s in g.subjects() if isinstance(s, URIRef)}

    std = {}                                            # 개체 → 표준 타입 지역명 목록
    for s in subjects:
        locs = [local(t) for t in g.objects(s, RDF.type)]
        std[s] = [l for l in locs if l in STD]
        if not str(s).startswith(RIC):
            errs.append(f"§2.1 개체가 ric: 밖에 있음: {s}")
        if len(std[s]) == 0:
            errs.append(f"§2.2 표준 타입 없음 → 화면에서 사라짐: {s}")
        elif len(std[s]) > 1:
            errs.append(f"§2.2 표준 타입 2개 이상(비결정): {s} {std[s]}")
        for t in g.objects(s, RDF.type):                # 주의①: 커스텀 클래스 지역명이 12종과 겹치는지
            if local(t) in STD and not (str(t).startswith(RICO) or str(t).startswith(str(SKOS))):
                errs.append(f"§4 커스텀 클래스 지역명이 표준과 겹침: {t}")

    for s, ts in std.items():                           # §2.3 이름 술어
        if len(ts) != 1: continue
        p = URIRef(NAME.get(ts[0], RICO + "name"))
        if not list(g.objects(s, p)):
            errs.append(f"§2.3 이름 술어({local(p)}) 없음 → URI 꼬리 노출: {s}")
        if list(g.objects(s, RDFS.label)):
            errs.append(f"§2.3 rdfs:label 사용(사진 출처 자리로 읽힘): {s}")

    for s, p, o in g:                                   # §2.4 평문 리터럴 / §2.5 날짜 / §2.6 좌표
        if isinstance(o, Literal):
            if o.language or (o.datatype and str(o.datatype) != "http://www.w3.org/2001/XMLSchema#string"):
                errs.append(f"§2.4 언어태그·자료형 붙은 리터럴: {s} {local(p)} {o!r}")
            if str(p) in DATE_P and not DATE_RE.match(str(o)):
                errs.append(f"§2.5 날짜 형식 위반: {s} {local(p)} {o}")
        if str(p) == "http://www.w3.org/2003/01/geo/wgs84_pos#lon":
            errs.append(f"§2.6 geo:lon 사용(geo:long 이어야 함): {s}")
        if str(p).startswith("http://www.w3.org/2003/01/geo/wgs84_pos#") and local(p) in ("lat", "long"):
            if not re.match(r"^-?\d+\.\d+$", str(o)):
                errs.append(f"§2.6 좌표가 십진 문자열이 아님: {s} {o}")
        if "schema.org" in str(p) and str(p).startswith("http://schema.org/"):
            errs.append(f"§3 http://schema.org (https 아님): {p}")

    cols = [s for s in subjects if "RecordSet" in std.get(s, []) and local(s).startswith("col-")]  # §2.8 컬렉션
    if len(cols) != 1:
        errs.append(f"§2.8 col- 컬렉션이 정확히 1개가 아님: {cols}")
    for s in subjects:
        if "RecordSet" in std.get(s, []) and not local(s).startswith("col-"):
            errs.append(f"§2.8 col- 없는 RecordSet(거대 허브 위험): {s}")
    for s, _, c in g.triples((None, URIRef(RICO + "isOrWasIncludedIn"), None)):
        if std.get(s) and std[s][0] not in ("Record", "RecordSet"):
            errs.append(f"§2.8 기록이 아닌 개체를 isOrWasIncludedIn 으로 소속(도메인 위반): {s}")
    for s, ts in std.items():
        if ts and s not in cols and not (set(g.objects(s, URIRef(RICO + "isOrWasIncludedIn"))) |
                                          set(g.objects(s, URIRef(RICO + "isOrWasSubjectOf")))) & set(cols):
            warns.append(f"§2.8 컬렉션 소속 없음(길 B에서 컬렉션 화면에 안 나옴): {s}")

    for a, b in INVERSE:                                # §2.9 역속성 양방향 단언
        A, B = URIRef(RICO + a), URIRef(RICO + b)
        for s, _, o in g.triples((None, A, None)):
            if (o, B, s) in g:
                errs.append(f"§2.9 역속성 양방향: {local(s)} {a} / {b}")

    edges, dropped = Counter(), Counter()               # §2.7 관계망 간선(소비자 필터 흉내)
    deg = Counter()
    for s, p, o in g:
        if not str(p).startswith(EDGE_NS) or p == RDF.type: continue
        if not isinstance(o, URIRef):
            continue                                    # 리터럴은 간선이 아님(속성)
        if std.get(s) and len(std[s]) == 1 and std.get(o) and len(std[o]) == 1:
            if o in cols or s in cols: continue          # 컬렉션과 소속 간선은 화면에서 걷어낸다
            edges[local(p)] += 1; deg[s] += 1; deg[o] += 1
        else:
            dropped[f"{local(p)} → {o}"] += 1
    for k, v in dropped.items():
        warns.append(f"§2.7 소거될 간선(목적어가 그래프 밖·무타입): {k} ×{v}")

    concepts = [s for s, t in std.items() if t == ["Concept"]]  # §3 주제 화면
    schemes = [s for s, t in std.items() if t == ["ConceptScheme"]]
    if concepts and not schemes:
        errs.append("§3 ConceptScheme 이 하나도 없음 → 주제 목록이 빈다")
    for c in concepts:
        if not list(g.objects(c, SKOS.inScheme)):
            errs.append(f"§3 skos:inScheme 없는 개념(주제 목록에 안 뜸): {c}")
    if list(g.triples((None, SKOS.narrower, None))):
        warns.append("§3 skos:narrower 사용 — 계층은 broader 만 읽힌다")
    creators = {o for _, _, o in g.triples((None, URIRef(RICO + "hasCreator"), None))}
    if len(creators) > 1:
        errs.append(f"§2.11 구술자(hasCreator 대상)가 2명 이상: {len(creators)}")

    types = Counter(t[0] for t in std.values() if len(t) == 1)
    info.append(f"트리플 {len(g)} · 개체 {len(subjects)} · 표준 타입별 {dict(types)}")
    info.append(f"관계망 간선 {sum(edges.values())}개(컬렉션 제외): {dict(edges)}")
    top = ", ".join(f"{g.value(n, SKOS.prefLabel) or g.value(n, URIRef(RICO + 'name')) or local(n)}({d})" for n, d in deg.most_common(5))
    info.append(f"연결 수 상위 5: {top}")
    iso = [local(s) for s, t in std.items() if t and s not in cols and deg[s] == 0]
    info.append(f"관계망 외톨이 점 {len(iso)}개: {', '.join(sorted(iso))}")
    return errs, warns, info


if __name__ == "__main__":
    errs, warns, info = main(sys.argv[1])
    for l in info: print("ℹ", l)
    for l in warns: print("⚠", l)
    for l in errs: print("✗", l)
    if len(sys.argv) > 2:                               # 기술규칙(SHACL)도 함께 검사
        import pyshacl
        ok, _, txt = pyshacl.validate(rdflib.Graph().parse(sys.argv[1]), shacl_graph=rdflib.Graph().parse(sys.argv[2]))
        print("SHACL:", "적합" if ok else "위반\n" + txt)
        if not ok: errs.append("SHACL")
    print("계약 위반", len(errs), "건 · 경고", len(warns), "건")
    sys.exit(1 if errs else 0)
