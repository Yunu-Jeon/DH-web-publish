# -*- coding: utf-8 -*-
"""site-data/archive.js(검수 데이터의 공개용 내보내기)를 AP 그라운딩 가이드 계약에 맞는 Turtle로 바꾼다.

원칙: 새 사실을 만들지 않는다. AP 속성은 그대로 두고(이중 기술),
스타터킷 화면이 읽는 술어(표준 타입·이름·관계)를 옆에 하나씩 더 단다.
사용: python export_ttl.py <archive.js 경로> <출력.ttl> [--include-pending]
"""
import json, re, sys, urllib.parse                      # 표준 라이브러리: JSON 읽기, 정규식, 인자, URL 인코딩
from rdflib import Graph, Namespace, URIRef, Literal     # RDF 그래프를 만들고 Turtle로 직렬화하는 라이브러리
from rdflib.namespace import RDF, RDFS, SKOS, DCTERMS, FOAF, XSD  # 자주 쓰는 표준 네임스페이스

RIC = Namespace("http://archives.nanet.go.kr/id/")                 # 가이드 §2.1: 모든 개체 IRI는 이 안에
RICO = Namespace("https://www.ica.org/standards/RiC/ontology#")    # https·# 로 끝나야 관계가 산다
GEO = Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")        # 좌표(geo:lat / geo:long)
SKOSXL = Namespace("http://www.w3.org/2008/05/skos-xl#")           # 어휘 클래스(skosxl:Label)
DCTYPE = Namespace("http://purl.org/dc/dcmitype/")                 # 자료 유형(dctype:StillImage 등)
BIBO = Namespace("http://purl.org/ontology/bibo/")                 # 출처 유형(bibo:AcademicArticle 등)
DIA = Namespace("https://yunu-jeon.github.io/DH-Korean-Diaspora/ns#")  # AP 1장의 커스텀 어휘
SITE = "https://yunu-jeon.github.io/DH-Korean-Diaspora/item.html?id="  # 원 사이트의 개별 자원 주소

COL = RIC["col-한-뿌리-다른-땅"]                   # 가이드 §2.8: col- 접두 컬렉션(공백·쉼표 없음)
SCHEMES = {                                         # 가이드 §3: ConceptScheme이 없으면 주제 목록이 빈다
    "object": (RIC["scheme-life-objects"], "생활 대상", "음식·생활 사물·일·교육 제도 등 말이 가리키는 대상. 네 측면을 최상위 개념으로 둔다."),
    "word": (RIC["scheme-words"], "디아스포라 어휘", "문화권마다 대상을 부르던 말(이름표). 말과 대상을 분리한다는 AP 설계에 따라 생활 대상과 다른 체계에 둔다."),
    "group": (RIC["scheme-cultures"], "문화권", "고려인·재일조선인·하와이 한인. 사람들의 범주(RiC-O DemographicGroup)로 둔다."),
}
ASPECTS = {                                         # dia:aspect 값 → 측면 개념(사이트 common.js의 한글·한자 표기와 같게)
    "먹는 것": ("aspect-eat", "식(食)"), "부르는 것": ("aspect-call", "호(呼)"),
    "일하는 것": ("aspect-work", "사(事)"), "배우는 것": ("aspect-learn", "학(學)"),
}


def load(path):                                     # archive.js에서 window.ARCHIVE = {...}; 의 JSON만 떼어 읽는다
    text = open(path, encoding="utf-8-sig").read()  # BOM이 있어도 읽히게
    body = text[text.index("{"): text.rindex("}") + 1]  # 첫 { 부터 마지막 } 까지가 JSON
    return json.loads(body)                         # 파이썬 dict로


def as_list(v):                                     # AP 값은 객체 하나이거나 배열이므로 늘 배열로 맞춘다
    return v if isinstance(v, list) else ([] if v is None else [v])


def iri(rid):                                       # 사이트 ID → ric: 안의 사람이 읽는 슬러그
    if ":" in rid:                                  # scene:koryo-daily-table 같은 ID는
        return RIC[rid.replace(":", "-")]           # scene-koryo-daily-table 로(가이드: 문장부호 금지)
    return RIC["ref-" + rid]                        # 출처 ID(kwon2020)는 ref- 접두를 붙인다


def lit(s):                                         # 가이드 §2.4: 언어태그·자료형 없는 평문 리터럴만 쓴다
    return Literal(str(s))


class Builder:
    def __init__(self, data, include_pending):
        self.d = data                               # 원본 데이터
        self.g = Graph()                            # 결과 그래프
        self.pending = include_pending              # 검수 전 자료까지 넣을지
        self.used_refs = set()                      # 실제로 근거로 쓰인 출처만 내보내기 위해 모은다
        self.skipped = []                           # 내보내지 않은 것 목록(보고용)
        for p, ns in [("ric", RIC), ("rico", RICO), ("skos", SKOS), ("skosxl", SKOSXL), ("geo", GEO), ("foaf", FOAF),
                      ("dcterms", DCTERMS), ("dctype", DCTYPE), ("bibo", BIBO), ("dia", DIA), ("rdfs", RDFS)]:
            self.g.bind(p, ns, override=True, replace=True)  # 접두어를 묶는다(rdflib 기본 geo: 를 덮어씀)

    def add(self, s, p, o):                         # 트리플 하나 추가(짧게 쓰려고)
        self.g.add((s, p, o))

    def common(self, s, r, member=True):            # 모든 개체에 공통으로 붙이는 것
        self.add(s, RICO.identifier, lit(r["id"]))  # 원 사이트 ID를 식별자로 보존(스타터킷 AP의 필수 식별자)
        self.add(s, RDFS.seeAlso, URIRef(SITE + urllib.parse.quote(r["id"], safe=":")))  # 원 사이트 페이지(관계망 밖 층)
        if member:
            self.add(s, RICO.isOrWasSubjectOf, COL) # 가이드 §2.8: 기록이 아닌 개체의 소속 술어

    def cites(self, s, r):                          # 값마다 붙은 cite를 모아 dia:citation 으로(가이드 §2.10의 근거 층)
        found = set(r.get("dia:citation", []))      # 원본에 이미 모아 둔 것이 있으면 그대로
        for k, v in r.items():                      # 없는 클래스(장소·생활 대상 등)는 값들의 cite를 모은다
            for x in as_list(v):
                if isinstance(x, dict):
                    found.update(x.get("cite", []))
        for c in sorted(found):
            if c != "sources.json":                 # sources.json 은 문헌 목록 파일이지 근거 쪽수가 아니다
                self.add(s, DIA.citation, lit(c))

    def notes(self, s, r):                          # '확인 필요'·'해석'·'문헌 외'를 사람 검수용 주기로 남긴다
        for k, v in r.items():
            for x in as_list(v):
                if not isinstance(x, dict):
                    continue
                if x.get("status") == "확인 필요":  # 값이 비어 있는 자리 → 숨기지 않고 드러낸다
                    self.add(s, SKOS.editorialNote, lit(f"확인 필요 — {k}: {x.get('note', '')}".strip()))
                elif x.get("basis") in ("해석", "문헌 외") and x.get("note") and "ref" in x:  # 관계에 걸린 편집 판단
                    self.add(s, SKOS.editorialNote, lit(f"{x['basis']} — {k} → {x['ref']}: {x['note']}"))
        if r.get("note"):                           # 자원 전체에 대한 메모
            self.add(s, SKOS.editorialNote, lit(r["note"]))

    def sources(self, s, r):                        # dcterms:source → 출처 개체(IRI, 관계망 밖)
        for x in as_list(r.get("dcterms:source")):
            if isinstance(x, dict) and x.get("ref"):
                self.used_refs.add(x["ref"])
                self.add(s, DCTERMS.source, iri(x["ref"]))

    def values(self, r, key):                       # 값 문자열만(확인 필요로 비어 있는 것은 뺀다)
        return [x["value"] for x in as_list(r.get(key)) if isinstance(x, dict) and x.get("value")]

    def refs(self, r, key):                         # 참조 ID만
        return [x["ref"] for x in as_list(r.get(key)) if isinstance(x, dict) and x.get("ref")]

    def collection_and_schemes(self):
        self.add(COL, RDF.type, RICO.RecordSet)     # 컬렉션: RecordSet 정확히 1개 타입
        self.add(COL, RICO.title, lit("한 뿌리, 다른 땅"))  # 기록류 이름은 rico:title
        self.add(COL, RICO.scopeAndContent, lit("한인 디아스포라 생활문화·어휘 아카이브(One Root, Other Soils). 고려인·재일조선인·하와이 한인의 생활 장면, 생활 대상, 그것을 부르던 말."))
        for s, name, scope in SCHEMES.values():     # 개념체계 3개
            self.add(s, RDF.type, SKOS.ConceptScheme)
            self.add(s, SKOS.prefLabel, lit(name))  # 개념체계 이름은 skos:prefLabel
            self.add(s, SKOS.scopeNote, lit(scope))
            self.add(s, RICO.identifier, lit(str(s).rsplit("/", 1)[1]))
            self.add(s, RICO.isOrWasSubjectOf, COL)
        top = SCHEMES["object"][0]
        for value, (slug, hanja) in ASPECTS.items():  # 네 측면 = 생활 대상 체계의 최상위 개념이자 장면의 활동 유형
            a = RIC[slug]
            self.add(a, RDF.type, SKOS.Concept)       # 표준 타입은 이것 하나
            self.add(a, RDF.type, RICO.ActivityType)  # 병기: RiC-O 활동 유형(지역명이 12종과 겹치지 않음)
            self.add(a, SKOS.prefLabel, lit(value))   # AP 값 그대로
            self.add(a, SKOS.altLabel, lit(hanja))    # 화면 표기(한자 병기)는 비우선어로
            self.add(a, SKOS.inScheme, top)
            self.add(a, SKOS.topConceptOf, top)
            self.add(a, RICO.identifier, lit("dia:aspect=" + value))
            self.add(a, RICO.isOrWasSubjectOf, COL)

    def scene(self, r):
        s = iri(r["id"])
        self.add(s, RDF.type, RICO.Activity)          # 표준 타입: 활동(생활 장면은 '무언가를 하는 일')
        self.add(s, RDF.type, DIA.Scene)              # 병기: AP 클래스
        title = self.values(r, "dcterms:title")[0]
        self.add(s, DCTERMS.title, lit(title))        # AP 속성
        self.add(s, RICO.name, lit(title))            # 화면 이름 자리(가이드 §2.3: 활동은 rico:name)
        desc = " ".join(self.values(r, "dcterms:description"))  # AP 카디널리티 1 → 문장 배열을 순서대로 이어 하나로
        if desc:
            self.add(s, DCTERMS.description, lit(desc))  # AP 속성(문장별 근거는 dia:citation 과 원본 JSON에 남음)
            head = "(문학 속 재현) " if r.get("representation") else ""  # 재현임을 화면 설명에서도 드러낸다
            self.add(s, RICO.generalDescription, lit(head + desc))  # 화면 설명 자리
        if r.get("representation"):
            self.add(s, SKOS.editorialNote, lit(r["representation"]))
        for c in self.refs(r, "dcterms:subject"):
            self.add(s, DCTERMS.subject, iri(c))      # AP 관계(관계망 밖)
            self.add(s, RICO.isRelatedTo, iri(c))     # 관계망 간선(hasOrHadSubject는 domain이 RecordResource라 쓰지 않음)
        self.spatial(s, r)
        for t in self.values(r, "dcterms:temporal"):
            self.add(s, DCTERMS.temporal, lit(t))     # '1937년 이후' 같은 서술형 → rico 날짜 술어에 넣지 않는다(§2.5)
        for a in self.values(r, "dia:aspect"):
            self.add(s, DIA.aspect, lit(a))           # AP 값
            self.add(s, RICO.hasActivityType, RIC[ASPECTS[a][0]])  # 관계망 간선: 활동 → 활동 유형
        self.sources(s, r); self.cites(s, r); self.notes(s, r); self.common(s, r)

    def spatial(self, s, r):                          # dcterms:spatial 은 장소일 수도 문화권일 수도 있다
        for t in self.refs(r, "dcterms:spatial"):
            self.add(s, DCTERMS.spatial, iri(t))
            if t.startswith("place:"):
                self.add(s, RICO.isAssociatedWithPlace, iri(t))  # 가이드 §2.9: 개체에서 장소로 나가는 방향
            else:
                self.add(s, RICO.isRelatedTo, iri(t))  # 문화권은 장소가 아니므로 일반 관계

    def concept(self, r):
        s = iri(r["id"])
        self.add(s, RDF.type, SKOS.Concept)           # AP와 표준이 같은 클래스
        self.add(s, SKOS.prefLabel, lit(self.values(r, "skos:prefLabel")[0]))  # @ko 는 떼어 냄(§2.4)
        for d in self.values(r, "skos:definition"):
            self.add(s, SKOS.definition, lit(d))
        for m in self.values(r, "skos:exactMatch"):
            self.add(s, SKOS.exactMatch, URIRef(m))   # 지금은 전부 '확인 필요'라 실제로는 안 나간다
        self.add(s, SKOS.inScheme, SCHEMES["object"][0])
        for a in self.values(r, "dia:aspect"):
            self.add(s, DIA.aspect, lit(a))
            self.add(s, SKOS.broader, RIC[ASPECTS[a][0]])  # 계층은 하위→상위 broader만(§3)
        self.sources(s, r); self.cites(s, r); self.notes(s, r); self.common(s, r)

    def label(self, r):
        s = iri(r["id"])
        self.add(s, RDF.type, RICO.Concept)           # 표준 타입: 개념(skos:Concept는 skosxl:Label과 서로소라 쓰지 않음)
        self.add(s, RDF.type, SKOSXL.Label)           # 병기: AP 클래스
        form = as_list(r.get("skosxl:literalForm"))[0]
        self.add(s, SKOSXL.literalForm, lit(form["value"]))  # AP 속성(평문)
        self.add(s, SKOS.prefLabel, lit(form["value"]))      # 개념류 이름 자리
        if form.get("lang"):
            self.add(s, DCTERMS.language, lit(form["lang"]))  # 떼어 낸 언어태그를 잃지 않게(내보내기 전용 보조)
        for v in self.values(r, "dia:variantForm"):
            self.add(s, DIA.variantForm, lit(v))      # AP 이표기
            self.add(s, SKOS.altLabel, lit(v))        # 검색에 걸리는 비우선어(가이드 §2.4 권고)
        for g_ in self.values(r, "dia:gloss"):
            self.add(s, DIA.gloss, lit(g_))
            self.add(s, RICO.generalDescription, lit(g_))  # 화면 설명 자리
        for c in self.refs(r, "dia:denotes"):
            self.add(s, DIA.denotes, iri(c))          # AP 핵심 연결(관계망 밖)
            self.add(s, RICO.isRelatedTo, iri(c))     # 관계망 간선(skos:related는 양끝을 skos:Concept로 추론시켜 쓰지 않음)
        self.spatial(s, r)
        for v in self.values(r, "dia:sourceLanguage"):
            self.add(s, DIA.sourceLanguage, lit(v))
        for v in self.values(r, "dia:etymologyNote"):
            self.add(s, DIA.etymologyNote, lit(v))
        self.add(s, SKOS.inScheme, SCHEMES["word"][0])
        self.sources(s, r); self.cites(s, r); self.notes(s, r); self.common(s, r)

    def place(self, r):
        s = iri(r["id"])
        self.add(s, RDF.type, RICO.Place)             # 표준 타입: 장소
        self.add(s, RDF.type, DCTERMS.Location)       # 병기: AP 클래스
        name = self.values(r, "dcterms:title")[0]
        self.add(s, DCTERMS.title, lit(name))
        self.add(s, RICO.name, lit(name))             # 화면 이름 자리
        c = r.get("coords") or {}
        if "lat" in c and "lon" in c:
            self.add(s, GEO.lat, lit(f"{float(c['lat']):.4f}"))   # 십진 문자열(§2.6)
            self.add(s, GEO.long, lit(f"{float(c['lon']):.4f}"))  # geo:lon 이 아니라 geo:long
            self.add(s, SKOS.editorialNote, lit(f"좌표는 {c.get('basis', '')} 값 — {c.get('note', '')}"))
        for p in self.refs(r, "dcterms:isPartOf"):
            self.add(s, DCTERMS.isPartOf, iri(p))     # AP 관계
            self.add(s, RICO.isOrWasContainedBy, iri(p))  # 관계망 간선(RiC-O: 장소 → 장소)
        self.cites(s, r); self.notes(s, r); self.common(s, r)

    def group(self, r):
        s = iri(r["id"])
        self.add(s, RDF.type, RICO.Concept)           # 표준 타입: 개념(사람들의 범주)
        self.add(s, RDF.type, RICO.DemographicGroup)  # 병기: RiC-O 인구 집단(Type → Concept 의 하위)
        self.add(s, RDF.type, FOAF.Group)             # 병기: AP 클래스
        name = self.values(r, "dcterms:title")[0]
        self.add(s, DCTERMS.title, lit(name))
        self.add(s, SKOS.prefLabel, lit(name))        # 개념류 이름 자리
        desc = " ".join(self.values(r, "dcterms:description"))  # AP 카디널리티 1 → 이어서 하나로
        if desc:
            self.add(s, DCTERMS.description, lit(desc))
            self.add(s, RICO.generalDescription, lit(desc))
        for p in self.refs(r, "dcterms:spatial"):
            self.add(s, DCTERMS.spatial, iri(p))
            self.add(s, RICO.isAssociatedWithPlace, iri(p))  # 문화권 → 주요 장소
        self.add(s, SKOS.inScheme, SCHEMES["group"][0])
        self.add(s, SKOS.topConceptOf, SCHEMES["group"][0])
        self.sources(s, r); self.cites(s, r); self.notes(s, r); self.common(s, r)

    def material(self, r):
        if not self.pending:                          # 필수값(rights·source)이 비어 '검수 전 비공개'로 적힌 자료
            self.skipped.append(f"{r['id']} — 필수값 확인 필요라 제외(--include-pending 으로 포함)")
            return
        s = iri(r["id"])
        self.add(s, RDF.type, RICO.Record)            # 표준 타입: 기록
        self.add(s, RDF.type, DCTYPE[r["class"].split(":")[1]])  # 병기: dctype:StillImage 등
        t = self.values(r, "dcterms:title")[0]
        self.add(s, DCTERMS.title, lit(t)); self.add(s, RICO.title, lit(t))
        for k in ("dcterms:type", "dcterms:date", "dcterms:rights"):
            for v in self.values(r, k):
                self.add(s, DCTERMS[k.split(":")[1]], lit(v))  # '1930년대' 같은 서술형 날짜는 dcterms 층에만
        for t_ in self.refs(r, "dcterms:relation"):
            self.add(s, DCTERMS.relation, iri(t_)); self.add(s, RICO.isRelatedTo, iri(t_))
        self.spatial(s, r)
        self.cites(s, r); self.notes(s, r)
        self.common(s, r, member=False)
        self.add(s, RICO.isOrWasIncludedIn, COL)      # 기록류의 소속 술어

    def reference(self, r):
        s = iri(r["id"])
        self.add(s, RDF.type, RICO.Record)            # 표준 타입: 기록(문헌)
        self.add(s, RDF.type, BIBO[r["class"].split(":")[1]])  # 병기: bibo:AcademicArticle / bibo:Document
        t = self.values(r, "dcterms:title")[0]
        self.add(s, DCTERMS.title, lit(t)); self.add(s, RICO.title, lit(t))
        for v in self.values(r, "dcterms:creator"):
            self.add(s, DCTERMS.creator, lit(v))      # AP: 저자는 문자열(인물 클래스가 없어 rico:hasAuthor 를 쓰지 않음)
        for k in ("dcterms:date", "dcterms:isPartOf", "dcterms:accessRights"):
            for v in self.values(r, k):
                self.add(s, DCTERMS[k.split(":")[1]], lit(v))
        for v in self.values(r, "bibo:uri"):
            self.add(s, BIBO.uri, lit(v))             # bibo:uri 는 자료형 속성이라 문자열
        self.notes(s, r)
        self.common(s, r, member=False)
        self.add(s, RICO.isOrWasIncludedIn, COL)

    def build(self):
        self.collection_and_schemes()
        for r in self.d["scenes"]: self.scene(r)
        for r in self.d["concepts"]: self.concept(r)
        for r in self.d["labels"]: self.label(r)
        for r in self.d["places"]: self.place(r)
        for r in self.d["groups"]: self.group(r)
        for r in self.d["materials"]: self.material(r)
        for r in self.d["references"]:              # 출처는 실제로 근거로 쓰인 것만(쓰이지 않은 문헌은 보고)
            if r["id"] in self.used_refs: self.reference(r)
            else: self.skipped.append(f"{r['id']} — 어떤 개체의 dcterms:source 에도 쓰이지 않아 제외")
        return self.g


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    b = Builder(load(src), "--include-pending" in sys.argv)
    g = b.build()
    header = ("# 한 뿌리, 다른 땅 — AP 그라운딩 가이드 계약에 맞춘 Turtle\n"
              "# 생성: export_ttl.py (원본 site-data/archive.js). 손으로 고치지 말고 원본 데이터를 고친 뒤 다시 만드세요.\n")
    open(out, "w", encoding="utf-8").write(header + g.serialize(format="turtle"))
    print(f"트리플 {len(g)}개 → {out}")
    for s in b.skipped: print("제외:", s)
