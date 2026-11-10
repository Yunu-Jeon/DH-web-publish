# -*- coding: utf-8 -*-
"""한 뿌리, 다른 땅 AP + 스타터킷 화면 계약을 한 표로 적고, 그 표에서 SHACL(TTL)과 DCTAP(CSV)을 함께 만든다.
표 하나에서 두 파일을 만들어 둘이 어긋나지 않게 한다. 사용: python build_rules.py <출력폴더>
"""
import csv, sys, os                                   # CSV 쓰기, 인자, 경로

PREFIXES = """@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rico: <https://www.ica.org/standards/RiC/ontology#> .
@prefix ric: <http://archives.nanet.go.kr/id/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix skosxl: <http://www.w3.org/2008/05/skos-xl#> .
@prefix geo: <http://www.w3.org/2003/01/geo/wgs84_pos#> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix dctype: <http://purl.org/dc/dcmitype/> .
@prefix bibo: <http://purl.org/ontology/bibo/> .
@prefix dia: <https://yunu-jeon.github.io/DH-Korean-Diaspora/ns#> .
"""

# 모양(shape): (ID, 대상 클래스들, 한국어 이름, 설명)
SHAPES = [
    ("scene", ["dia:Scene"], "생활 장면", "AP 생활 장면. 화면용 표준 타입은 rico:Activity 를 병기한다."),
    ("object", ["skos:Concept"], "생활 대상", "AP 생활 대상(과 네 측면 개념). 표준 타입과 AP 클래스가 같다."),
    ("word", ["skosxl:Label"], "어휘", "AP 어휘. skosxl:Label 은 skos:Concept 와 서로소라 표준 타입은 rico:Concept 를 병기한다."),
    ("place", ["dcterms:Location"], "장소", "AP 장소. 표준 타입 rico:Place 를 병기한다."),
    ("group", ["foaf:Group"], "문화권", "AP 문화권. 표준 타입 rico:Concept 와 rico:DemographicGroup 을 병기한다."),
    ("source", ["bibo:AcademicArticle", "bibo:Thesis", "bibo:Document"], "출처", "AP 출처. 표준 타입 rico:Record 를 병기한다."),
    ("material", ["dctype:Text", "dctype:StillImage", "dctype:MovingImage"], "자료", "AP 자료(1차 사료). 표준 타입 rico:Record 를 병기한다."),
    ("scheme", ["skos:ConceptScheme"], "개념체계", "화면 계약용. AP에는 없지만 주제 화면이 개념체계를 요구한다."),
    ("collection", ["rico:RecordSet"], "컬렉션", "화면 계약용. col- 접두 RecordSet 하나."),
]

# 속성 행: (모양, 경로, 이름, 최소, 최대(None=제한 없음), 종류, 값 제약, 층, 비고)
# 종류 L=평문 리터럴(xsd:string, 언어태그 금지), I=IRI. 층 AP=AP 속성, 화면=스타터킷 계약용으로 더한 것, 근거=관계망 밖 근거 층
ASPECT_IN = '("먹는 것" "부르는 것" "일하는 것" "배우는 것")'
ROWS = [
    ("scene", "rdf:type", "표준 타입 병기", 1, None, "I", "hasValue rico:Activity", "화면", "12종 중 정확히 1개"),
    ("scene", "rico:identifier", "식별자", 1, 1, "L", "", "화면", "원 사이트 ID(scene:…)"),
    ("scene", "dcterms:title", "장면 제목", 1, 1, "L", "", "AP", ""),
    ("scene", "rico:name", "화면 이름", 1, 1, "L", "", "화면", "dcterms:title 과 같은 값(가이드 §2.3)"),
    ("scene", "dcterms:description", "설명", 1, 1, "L", "", "AP", "문장 배열을 순서대로 이은 하나"),
    ("scene", "rico:generalDescription", "화면 설명", 0, 1, "L", "", "화면", "문학 속 재현이면 앞에 표시"),
    ("scene", "dcterms:subject", "다루는 생활 대상", 0, None, "I", "class skos:Concept", "AP", ""),
    ("scene", "rico:isRelatedTo", "관계망 간선", 0, None, "I", "", "화면", "생활 대상·문화권으로(hasOrHadSubject 는 domain 위반이라 쓰지 않음)"),
    ("scene", "dcterms:spatial", "장소·문화권", 1, None, "I", "", "AP", ""),
    ("scene", "rico:isAssociatedWithPlace", "관련 장소", 0, None, "I", "class rico:Place", "화면", "장면 → 장소 한 방향(§2.9)"),
    ("scene", "dcterms:temporal", "시기", 0, 1, "L", "", "AP", "서술형이라 rico 날짜 술어에 넣지 않음(§2.5)"),
    ("scene", "dia:aspect", "생활문화의 측면", 1, 1, "L", "in " + ASPECT_IN, "AP", ""),
    ("scene", "rico:hasActivityType", "측면 개념", 1, 1, "I", "class rico:ActivityType", "화면", "dia:aspect 값과 같은 측면"),
    ("scene", "dcterms:source", "근거 출처", 1, None, "I", "class rico:Record", "근거", ""),
    ("scene", "dia:citation", "근거 쪽수", 1, None, "L", "pattern ^[^:]+:.+$", "근거", "출처ID:쪽"),
    ("scene", "rico:isOrWasSubjectOf", "컬렉션 소속", 1, 1, "I", "class rico:RecordSet", "화면", ""),

    ("object", "rico:identifier", "식별자", 1, 1, "L", "", "화면", ""),
    ("object", "skos:prefLabel", "대표 이름", 1, 1, "L", "", "AP", "AP는 @ko 이지만 가이드 §2.4에 따라 평문"),
    ("object", "skos:altLabel", "비우선어", 0, None, "L", "", "화면", "측면 개념의 한자 표기"),
    ("object", "skos:definition", "설명", 0, 1, "L", "", "AP", ""),
    ("object", "dia:aspect", "생활문화의 측면", 0, 1, "L", "in " + ASPECT_IN, "AP", "측면 개념 자신에는 없음"),
    ("object", "skos:broader", "상위 측면", 0, 1, "I", "class skos:Concept", "화면", "dia:aspect 를 계층으로(하위→상위)"),
    ("object", "skos:exactMatch", "외부 전거", 0, 1, "I", "", "AP", ""),
    ("object", "skos:inScheme", "소속 개념체계", 1, 1, "I", "class skos:ConceptScheme", "화면", ""),
    ("object", "dcterms:source", "근거 출처", 0, None, "I", "class rico:Record", "근거", "AP 1..n — 측면 개념에는 없어 0으로 둠(아래 sparql 제약이 생활 대상만 검사)"),
    ("object", "dia:citation", "근거 쪽수", 0, None, "L", "pattern ^[^:]+:.+$", "근거", ""),

    ("word", "rdf:type", "표준 타입 병기", 1, None, "I", "hasValue rico:Concept", "화면", ""),
    ("word", "rico:identifier", "식별자", 1, 1, "L", "", "화면", ""),
    ("word", "skosxl:literalForm", "표기", 1, 1, "L", "", "AP", "언어태그는 dcterms:language 로 옮김"),
    ("word", "skos:prefLabel", "화면 이름", 1, 1, "L", "", "화면", "literalForm 과 같은 값"),
    ("word", "dcterms:language", "표기의 언어", 0, 1, "L", "pattern ^[a-z]{2,3}$", "화면", "떼어 낸 언어태그(내보내기 전용 보조)"),
    ("word", "dia:variantForm", "이표기", 0, None, "L", "", "AP", ""),
    ("word", "skos:altLabel", "검색용 이표기", 0, None, "L", "", "화면", "dia:variantForm 과 같은 값"),
    ("word", "dia:gloss", "뜻", 1, 1, "L", "", "AP", ""),
    ("word", "rico:generalDescription", "화면 설명", 0, 1, "L", "", "화면", "dia:gloss 와 같은 값"),
    ("word", "dia:denotes", "가리키는 생활 대상", 0, 1, "I", "class skos:Concept", "AP", ""),
    ("word", "rico:isRelatedTo", "관계망 간선", 0, None, "I", "", "화면", "생활 대상·문화권으로"),
    ("word", "dcterms:spatial", "쓰인 문화권", 1, None, "I", "class foaf:Group", "AP", ""),
    ("word", "dia:sourceLanguage", "기원 언어", 0, 1, "L", "pattern ^[a-z]{3}$", "AP", "ISO 639-3"),
    ("word", "dia:etymologyNote", "어원 설명", 0, 1, "L", "", "AP", "연구자 해석"),
    ("word", "skos:inScheme", "소속 개념체계", 1, 1, "I", "class skos:ConceptScheme", "화면", ""),
    ("word", "dcterms:source", "근거 출처", 1, None, "I", "class rico:Record", "근거", ""),
    ("word", "dia:citation", "근거 쪽수", 1, None, "L", "pattern ^[^:]+:.+$", "근거", ""),
    ("word", "rico:isOrWasSubjectOf", "컬렉션 소속", 1, 1, "I", "class rico:RecordSet", "화면", ""),

    ("place", "rdf:type", "표준 타입 병기", 1, None, "I", "hasValue rico:Place", "화면", ""),
    ("place", "rico:identifier", "식별자", 1, 1, "L", "", "화면", ""),
    ("place", "dcterms:title", "이름", 1, 1, "L", "", "AP", ""),
    ("place", "rico:name", "화면 이름", 1, 1, "L", "", "화면", ""),
    ("place", "geo:lat", "위도", 1, 1, "L", "pattern ^-?[0-9]{1,2}\\\\.[0-9]+$", "AP", "십진 문자열(§2.6)"),
    ("place", "geo:long", "경도", 1, 1, "L", "pattern ^-?[0-9]{1,3}\\\\.[0-9]+$", "AP", "geo:lon 이 아님"),
    ("place", "dcterms:isPartOf", "상위 장소", 0, 1, "I", "class dcterms:Location", "AP", ""),
    ("place", "rico:isOrWasContainedBy", "상위 장소(간선)", 0, 1, "I", "class rico:Place", "화면", "RiC-O: 장소 → 장소"),
    ("place", "skos:exactMatch", "외부 전거", 0, 1, "I", "", "AP", ""),
    ("place", "dia:citation", "근거 쪽수", 0, None, "L", "pattern ^[^:]+:.+$", "근거", ""),

    ("group", "rdf:type", "표준 타입 병기", 1, None, "I", "hasValue rico:Concept", "화면", ""),
    ("group", "rico:identifier", "식별자", 1, 1, "L", "", "화면", ""),
    ("group", "dcterms:title", "이름", 1, 1, "L", "", "AP", ""),
    ("group", "skos:prefLabel", "화면 이름", 1, 1, "L", "", "화면", ""),
    ("group", "dcterms:description", "이동 개요", 1, 1, "L", "", "AP", "문장 배열을 이은 하나"),
    ("group", "rico:generalDescription", "화면 설명", 0, 1, "L", "", "화면", ""),
    ("group", "dcterms:spatial", "주요 장소", 1, None, "I", "class dcterms:Location", "AP", ""),
    ("group", "rico:isAssociatedWithPlace", "주요 장소(간선)", 0, None, "I", "class rico:Place", "화면", ""),
    ("group", "skos:inScheme", "소속 개념체계", 1, 1, "I", "class skos:ConceptScheme", "화면", ""),
    ("group", "dcterms:source", "근거 출처", 1, None, "I", "class rico:Record", "근거", ""),

    ("source", "rdf:type", "표준 타입 병기", 1, None, "I", "hasValue rico:Record", "화면", ""),
    ("source", "rico:identifier", "식별자", 1, 1, "L", "", "화면", ""),
    ("source", "dcterms:creator", "저자", 1, None, "L", "", "AP", "문자열(AP에 인물 클래스 없음)"),
    ("source", "dcterms:title", "제목", 1, 1, "L", "", "AP", ""),
    ("source", "rico:title", "화면 이름", 1, 1, "L", "", "화면", "기록류 이름은 rico:title"),
    ("source", "dcterms:date", "발행 연도", 0, 1, "L", "", "AP", ""),
    ("source", "dcterms:isPartOf", "수록 학술지·단행본", 0, 1, "L", "", "AP", ""),
    ("source", "bibo:uri", "링크", 0, 1, "L", "", "AP", ""),
    ("source", "dcterms:accessRights", "접근 조건", 1, 1, "L", "", "AP", ""),
    ("source", "rico:isOrWasIncludedIn", "컬렉션 소속", 1, 1, "I", "class rico:RecordSet", "화면", "기록류의 소속 술어(§2.8)"),

    ("material", "rdf:type", "표준 타입 병기", 1, None, "I", "hasValue rico:Record", "화면", ""),
    ("material", "dcterms:title", "제목", 1, 1, "L", "", "AP", ""),
    ("material", "rico:title", "화면 이름", 1, 1, "L", "", "화면", ""),
    ("material", "dcterms:type", "유형", 1, 1, "L", "", "AP", ""),
    ("material", "dcterms:date", "생산 연도", 0, 1, "L", "", "AP", ""),
    ("material", "dcterms:rights", "이용 조건", 1, 1, "L", "", "AP", ""),
    ("material", "dcterms:source", "원 소장처 링크", 1, 1, "I", "", "AP", ""),
    ("material", "dcterms:spatial", "문화권", 1, None, "I", "class foaf:Group", "AP", ""),
    ("material", "dcterms:relation", "관련 생활 장면", 0, None, "I", "class dia:Scene", "AP", ""),
    ("material", "dia:citation", "근거 쪽수", 0, None, "L", "pattern ^[^:]+:.+$", "근거", ""),
    ("material", "rico:isOrWasIncludedIn", "컬렉션 소속", 1, 1, "I", "class rico:RecordSet", "화면", ""),

    ("scheme", "skos:prefLabel", "체계 이름", 1, 1, "L", "", "화면", ""),
    ("scheme", "rico:identifier", "식별자", 1, 1, "L", "", "화면", ""),
    ("scheme", "skos:scopeNote", "범위", 0, 1, "L", "", "화면", ""),
    ("collection", "rico:title", "컬렉션 이름", 1, 1, "L", "", "화면", "지역명은 col- 로 시작"),
]

VOCAB = """
# --- 위 규칙이 쓰는 커스텀 어휘(dia:) 정의 — LLM·검증기가 용어 뜻을 이 파일 안에서 찾는다 ---
dia:Scene a rdfs:Class ;
    rdfs:label "생활 장면"@ko ;
    rdfs:comment "먹고, 부르고, 일하고, 배우는 생활문화의 한 장면. 사건이나 개념 어느 쪽에도 맞지 않는 서사 단위. 스타터킷 화면용으로는 rico:Activity 를 함께 단다."@ko .
dia:aspect a rdf:Property ;
    rdfs:label "생활문화의 측면"@ko ;
    rdfs:comment "먹는 것 / 부르는 것 / 일하는 것 / 배우는 것 중 하나. 대표 측면 하나를 고르는 것은 큐레이터의 해석이다."@ko .
dia:citation a rdf:Property ;
    rdfs:label "근거 쪽수"@ko ;
    rdfs:comment "\\"출처ID:쪽\\" 문자열. 쪽은 PDF 쪽이 아니라 인쇄된 쪽수. 웹 문헌은 절 이름."@ko .
dia:variantForm a rdf:Property ;
    rdfs:label "이표기"@ko ;
    rdfs:domain skosxl:Label ;
    rdfs:comment "Kim Chee / 김치처럼 검색에 필요한 다른 표기. 시기·매체 맥락은 담지 못한다."@ko .
dia:gloss a rdf:Property ;
    rdfs:label "뜻"@ko ;
    rdfs:domain skosxl:Label ;
    rdfs:comment "SKOS-XL 이름표는 원래 뜻을 갖지 않지만 문화권마다 다른 뜻을 담으려고 어휘에 둔다."@ko .
dia:denotes a rdf:Property ;
    rdfs:label "가리키는 생활 대상"@ko ;
    rdfs:domain skosxl:Label ;
    rdfs:range skos:Concept ;
    rdfs:comment "말과 대상을 분리하는 핵심 연결. 활동·호칭처럼 가리키는 사물이 없는 말은 비워 둔다."@ko .
dia:sourceLanguage a rdf:Property ;
    rdfs:label "기원 언어"@ko ;
    rdfs:domain skosxl:Label ;
    rdfs:comment "ISO 639-3 코드(rus, jpn, eng, kor). dcterms:language(자원이 쓰인 언어)와 뜻이 다르다."@ko .
dia:etymologyNote a rdf:Property ;
    rdfs:label "어원 설명(연구자 해석)"@ko ;
    rdfs:domain skosxl:Label ;
    rdfs:comment "보고된 사실과 해석을 분리하려는 속성."@ko .
"""


def constraint(c):                                     # '값 제약' 칸을 SHACL 구문으로
    if not c: return ""
    kind, val = c.split(" ", 1)
    return {"class": f"sh:class {val}", "hasValue": f"sh:hasValue {val}", "in": f"sh:in {val}",
            "pattern": f'sh:pattern "{val}"'}[kind]


def shacl(rows):                                       # 표 → SHACL Turtle 본문
    out = [PREFIXES, ""]
    for sid, targets, label, comment in SHAPES:
        out.append(f"ric:ap-shape-{sid} a sh:NodeShape ;")
        out.append("    " + " ;\n    ".join(f"sh:targetClass {t}" for t in targets) + " ;")
        out.append(f'    rdfs:label "{label}"@ko ;')
        out.append(f'    rdfs:comment "{comment}"@ko ;')
        props = [r for r in rows if r[0] == sid]
        blocks = []
        for _, path, name, mn, mx, kind, cons, layer, note in props:
            b = [f"sh:path {path}", f'sh:name "{name}"@ko', f"sh:minCount {mn}"]
            if mx is not None and path != "rdf:type": b.append(f"sh:maxCount {mx}")
            b.append("sh:datatype xsd:string" if kind == "L" else "sh:nodeKind sh:IRI")  # 평문 강제: @ko 면 위반
            if cons: b.append(constraint(cons))
            desc = f"[{layer}] {note}".strip()
            b.append(f'sh:description "{desc}"@ko')
            blocks.append("[ " + " ;\n        ".join(b) + " ]")
        out.append("    sh:property " + " ,\n      ".join(blocks) + " .\n")
    # 생활 대상(측면 개념이 아닌 것)에만 근거 출처 필수 — SPARQL 제약 대신 대상 선택으로 처리
    out.append("""ric:ap-shape-object-sourced a sh:NodeShape ;
    rdfs:label "생활 대상 — 근거 필수"@ko ;
    sh:targetSubjectsOf dia:aspect ;
    sh:property [ sh:path dcterms:source ; sh:minCount 1 ; sh:nodeKind sh:IRI ;
        sh:description "[근거] dia:aspect 를 가진 개체(장면·생활 대상)는 근거 출처가 1개 이상"@ko ] .
""")
    out.append("""ric:ap-shape-collection-name a sh:NodeShape ;
    rdfs:label "컬렉션 지역명"@ko ;
    sh:targetClass rico:RecordSet ;
    sh:pattern "^http://archives\\\\.nanet\\\\.go\\\\.kr/id/col-" ;
    rdfs:comment "가이드 §2.8 — col- 접두가 없으면 거대 허브가 된다"@ko .
""")
    out.append(VOCAB)
    return "\n".join(out)


def dctap(rows, path):                                 # 표 → 사람용 대조표(Excel에서 열림)
    names = {s[0]: (s[1][0], s[2]) for s in SHAPES}
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["shapeID", "shapeLabel", "propertyID", "propertyLabel", "mandatory", "repeatable",
                    "valueNodeType", "valueDataType", "valueConstraint", "layer", "note"])
        for sid, path_, name, mn, mx, kind, cons, layer, note in rows:
            w.writerow([names[sid][0], names[sid][1], path_, name, "TRUE" if mn >= 1 else "FALSE",
                        "TRUE" if mx is None else "FALSE", "literal" if kind == "L" else "IRI",
                        "string" if kind == "L" else "", cons, layer, note])


if __name__ == "__main__":
    out = sys.argv[1]
    open(os.path.join(out, "기술규칙.ttl"), "w", encoding="utf-8").write(shacl(ROWS))
    dctap(ROWS, os.path.join(out, "기술규칙.dctap.csv"))
    print("규칙", len(ROWS), "행 →", out)
