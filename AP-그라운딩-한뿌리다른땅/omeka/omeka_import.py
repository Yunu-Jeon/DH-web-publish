# -*- coding: utf-8 -*-
"""archive.js(검수 데이터)를 AP 리소스 템플릿에 맞춰 Omeka S 로 옮긴다.
값마다 붙은 basis·cite·note 는 값 주석(근거 템플릿: dia:basis, prov:atLocation, prov:wasDerivedFrom, skos:editorialNote)으로 남긴다.
제외 규칙은 export_ttl.py 와 같다(검수 전 자료 제외). 출처는 dcterms:source 나 cite 로 쓰인 것만 넣는다.
다시 실행해도 같은 템플릿·아이템을 새로 만들지 않고 갱신한다(dcterms:identifier 로 찾음).
사용: py omeka_import.py <archive.js> <키 JSON> [--dry-run]
"""
import sys, json, urllib.request, urllib.parse, urllib.error
from pathlib import Path

ARCHIVE, KEYFILE = Path(sys.argv[1]), Path(sys.argv[2])
DRY = "--dry-run" in sys.argv
BASE = "http://localhost:8000/api"
KEY = json.loads(KEYFILE.read_text(encoding="utf-8"))
SET_TITLE = "한 뿌리, 다른 땅"


def api(method, path, data=None, params=None, auth=True):
    q = dict(params or {})
    if auth:
        q.update(KEY)
    url = f"{BASE}/{path}?{urllib.parse.urlencode(q, doseq=True)}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} → {e.code}: {e.read().decode('utf-8')[:800]}")


_ids = {}
def pid(term):  # 속성 ID
    if ("p", term) not in _ids:
        _ids[("p", term)] = api("GET", "properties", params={"term": term}, auth=False)[0]["o:id"]
    return _ids[("p", term)]


def cid(term):  # 클래스 ID
    if ("c", term) not in _ids:
        _ids[("c", term)] = api("GET", "resource_classes", params={"term": term}, auth=False)[0]["o:id"]
    return _ids[("c", term)]


# ---------------------------------------------------------------- 템플릿
PAT = {
    "basis": "보고|해석|문헌 외",
    "aspect": "먹는 것|부르는 것|일하는 것|배우는 것",
    "citation": "[^:]+:.+",
    "lang3": "[a-z]{3}",
    "lat": "-?[0-9]{1,2}\\.[0-9]+",
    "long": "-?[0-9]{1,3}\\.[0-9]+",
}


def P(term, label, comment, dtype="literal", req=False, mn=None, mx=None, **art):
    """템플릿 속성 한 줄. art 는 ART 설정(input_control, resource_query 등)."""
    d = dict(art)
    if mn: d["min_values"] = mn
    if mx: d["max_values"] = mx
    return {"term": term, "label": label, "comment": comment,
            "dtype": dtype if isinstance(dtype, list) else [dtype], "req": req, "data": d}


def classes_q(*terms):
    return "&".join(f"resource_class_id[]={cid(t)}" for t in terms)


def ident():
    return P("dcterms:identifier", "식별자", "원 사이트 ID(예: scene:koryo-daily-table). 바꾸지 않는다.",
             req=True, mn=1, mx=1, unique_value="yes", locked_value="yes")


def note():
    return P("skos:editorialNote", "검수 메모", "'확인 필요'로 비어 있는 값, 문학 속 재현 여부 등 사람이 다시 볼 것.")


def source_req():
    return P("dcterms:source", "근거 출처", "이 자원을 뒷받침하는 출처 아이템.", "resource:item", req=True, mn=1,
             resource_query=classes_q("bibo:AcademicArticle", "bibo:Thesis", "bibo:Document"))


def citation_req():
    return P("dia:citation", "근거 쪽수", "\"출처ID:쪽\" 문자열(예: kwon2020:108). 인쇄된 쪽수, 웹 문헌은 절 이름.",
             req=True, mn=1, input_control=PAT["citation"])


def templates():
    T = []
    T.append(dict(label="근거(provenance)", old="근거(값 주석)", cls=None, title=None, desc=None,
                  use=["value_annotations"], props=[
        P("dia:basis", "값 종류", "보고 / 해석 / 문헌 외 중 하나. PROV-O 에 대응 속성이 없어 dia:basis 를 쓴다.",
          req=True, mn=1, mx=1, input_control=PAT["basis"]),
        P("prov:atLocation", "근거 쪽수", "\"출처ID:쪽\". 이 값이 문헌 안에서 있는 자리(PROV 의 비지리적 위치).",
          input_control=PAT["citation"]),
        P("prov:wasDerivedFrom", "근거 출처", "이 값이 나온 문헌(출처 아이템).", "resource:item",
          resource_query=classes_q("bibo:AcademicArticle", "bibo:Thesis", "bibo:Document")),
        P("skos:editorialNote", "값 메모", "이 값에 대한 검수·해석 메모."),
    ]))
    T.append(dict(label="자료", cls="dctype:StillImage", title="dcterms:title", desc=None, props=[
        ident(),
        P("dcterms:title", "제목", "", req=True, mn=1, mx=1),
        P("dcterms:type", "유형", "신문 지면 / 사진 / 문서 / 영상", req=True, mn=1, mx=1),
        P("dcterms:date", "생산 연도", "연도 미상이면 비운다.", mx=1),
        P("dcterms:rights", "이용 조건", "IIIF·재배포 가능 여부 판단의 기준", req=True, mn=1, mx=1),
        P("dcterms:source", "원 소장처 링크", "", "uri", req=True, mn=1, mx=1),
        P("dcterms:spatial", "문화권", "", "resource:item", req=True, mn=1, resource_query=classes_q("foaf:Group")),
        P("dcterms:relation", "관련 생활 장면", "", "resource:item", resource_query=classes_q("dia:Scene")),
        P("dia:citation", "근거 출처와 쪽수", "문헌 속에 인용된 자료일 때 \"출처ID:쪽\".", input_control=PAT["citation"]),
        note(),
    ]))
    T.append(dict(label="생활 장면", cls="dia:Scene", title="dcterms:title", desc="dcterms:description", props=[
        ident(),
        P("dcterms:title", "장면 제목", "", req=True, mn=1, mx=1),
        P("dcterms:description", "설명", "원문을 옮기지 않고 바꿔 쓴다. 문장마다 값 하나(문장별 근거를 남기려고).", req=True, mn=1),
        P("dcterms:subject", "다루는 생활 대상", "", "resource:item", resource_query=classes_q("skos:Concept")),
        P("dcterms:spatial", "장소·문화권", "", "resource:item", req=True, mn=1,
          resource_query=classes_q("dcterms:Location", "foaf:Group")),
        P("dcterms:temporal", "시기", "서술형 시기(예: 1937년 이후).", mx=1),
        P("dia:aspect", "생활문화의 측면", "먹는 것 / 부르는 것 / 일하는 것 / 배우는 것", req=True, mn=1, mx=1,
          input_control=PAT["aspect"]),
        source_req(), citation_req(), note(),
    ]))
    T.append(dict(label="생활 대상", cls="skos:Concept", title="skos:prefLabel", desc="skos:definition", props=[
        ident(),
        P("skos:prefLabel", "대표 이름(한국어)", "", req=True, mn=1, mx=1),
        P("skos:definition", "설명", "", mx=1),
        P("dia:aspect", "생활문화의 측면", "먹는 것 / 부르는 것 / 일하는 것 / 배우는 것", req=True, mn=1, mx=1,
          input_control=PAT["aspect"]),
        P("skos:exactMatch", "외부 전거(Wikidata)", "", "uri", mx=1),
        source_req(), note(),
    ]))
    T.append(dict(label="어휘", cls="skosxl:Label", title="skosxl:literalForm", desc="dia:gloss", props=[
        ident(),
        P("skosxl:literalForm", "표기", "값마다 언어를 단다(ko, en, ja, ru).", req=True, mn=1, mx=1),
        P("dia:variantForm", "이표기", "Kim Chee / 김치처럼 검색에 필요한 다른 표기."),
        P("dia:gloss", "뜻", "", req=True, mn=1, mx=1),
        P("dia:denotes", "가리키는 생활 대상", "활동·호칭처럼 가리키는 사물이 없는 말은 비운다.", "resource:item", mx=1,
          resource_query=classes_q("skos:Concept")),
        P("dcterms:spatial", "쓰인 문화권", "", "resource:item", req=True, mn=1, resource_query=classes_q("foaf:Group")),
        P("dia:sourceLanguage", "기원 언어", "ISO 639-3 코드(rus, jpn, eng, kor).", mx=1, input_control=PAT["lang3"]),
        P("dia:etymologyNote", "어원 설명(연구자 해석)", "", mx=1),
        source_req(), citation_req(), note(),
    ]))
    T.append(dict(label="장소", cls="dcterms:Location", title="dcterms:title", desc=None, props=[
        ident(),
        P("dcterms:title", "이름", "", req=True, mn=1, mx=1),
        P("geo:lat", "위도", "십진수 문자열(예: 44.8500).", req=True, mn=1, mx=1, input_control=PAT["lat"]),
        P("geo:long", "경도", "십진수 문자열(예: 65.5100).", req=True, mn=1, mx=1, input_control=PAT["long"]),
        P("dcterms:isPartOf", "상위 장소", "", "resource:item", mx=1, resource_query=classes_q("dcterms:Location")),
        P("skos:exactMatch", "외부 전거(GeoNames/Wikidata)", "", "uri", mx=1),
        note(),
    ]))
    T.append(dict(label="문화권", cls="foaf:Group", title="dcterms:title", desc="dcterms:description", props=[
        ident(),
        P("dcterms:title", "이름", "", req=True, mn=1, mx=1),
        P("dcterms:description", "이동 개요", "문장마다 값 하나(문장별 근거를 남기려고).", req=True, mn=1),
        P("dcterms:spatial", "주요 장소", "", "resource:item", req=True, mn=1, resource_query=classes_q("dcterms:Location")),
        source_req(), note(),
    ]))
    T.append(dict(label="출처", cls="bibo:AcademicArticle", title="dcterms:title", desc=None, props=[
        ident(),
        P("dcterms:creator", "저자", "문자열(AP에 인물 클래스 없음).", req=True, mn=1),
        P("dcterms:title", "제목", "", req=True, mn=1, mx=1),
        P("dcterms:date", "발행 연도", "", mx=1),
        P("dcterms:isPartOf", "수록 학술지·단행본", "", mx=1),
        P("bibo:uri", "링크", "", mx=1),
        P("dcterms:accessRights", "접근 조건", "원문 공개 여부", req=True, mn=1, mx=1),
        note(),
    ]))
    return T


def template_payload(t, va_id):
    data = {"use_for_resources": t.get("use", ["items"])}
    if t["cls"]:
        data["require_resource_class"] = "yes"
    if va_id:
        data["value_annotations_template"] = str(va_id)
    rtps = []
    for p in t["props"]:
        rtps.append({
            "o:property": {"o:id": pid(p["term"])},
            "o:alternate_label": p["label"], "o:alternate_comment": p["comment"] or None,
            "o:data_type": p["dtype"], "o:is_required": p["req"], "o:is_private": False,
            "o:default_lang": None,
            "o:data": [p["data"]] if p["data"] else [],
        })
    out = {"o:label": t["label"], "o:resource_template_property": rtps, "o:data": data}
    if t["cls"]:
        out["o:resource_class"] = {"o:id": cid(t["cls"])}
    if t["title"]:
        out["o:title_property"] = {"o:id": pid(t["title"])}
    if t["desc"]:
        out["o:description_property"] = {"o:id": pid(t["desc"])}
    return out


def ensure_templates():
    existing = {t["o:label"]: t["o:id"] for t in api("GET", "resource_templates", params={"per_page": 100})}
    ids, va = {}, None
    for t in templates():
        payload = template_payload(t, va if t.get("use") != ["value_annotations"] else None)
        found = existing.get(t["label"]) or existing.get(t.get("old"))  # 이름을 바꾼 템플릿은 옛 이름으로 찾는다
        if found:
            ids[t["label"]] = found
            if not DRY:
                api("PUT", f"resource_templates/{found}", payload)
        elif not DRY:
            ids[t["label"]] = api("POST", "resource_templates", payload)["o:id"]
        if t.get("use") == ["value_annotations"]:
            va = ids.get(t["label"])
    return ids


# ---------------------------------------------------------------- 데이터 → 값
def as_list(v):
    return v if isinstance(v, list) else ([v] if v else [])


class Builder:
    def __init__(self, data, ids, ref_ids):
        self.d, self.ids, self.ref_ids = data, ids, ref_ids  # ids: 원 ID → Omeka 아이템 ID

    def lit(self, term, value, lang=None, ann=None):
        v = {"type": "literal", "property_id": pid(term), "@value": str(value)}
        if lang: v["@language"] = lang
        if ann: v["@annotation"] = ann
        return v

    def res(self, term, rid, ann=None):
        v = {"type": "resource:item", "property_id": pid(term), "value_resource_id": self.ids[rid]}
        if ann: v["@annotation"] = ann
        return v

    def ann(self, x):
        """값 하나의 basis·cite·note → 값 주석."""
        if not isinstance(x, dict):
            return None
        a = {}
        if x.get("basis"):
            a["dia:basis"] = [self.lit("dia:basis", x["basis"])]
        cites = [c for c in x.get("cite", []) if c]
        if cites:
            a["prov:atLocation"] = [self.lit("prov:atLocation", c) for c in cites]
            srcs = []
            for c in cites:
                r = c.split(":", 1)[0]
                if r in self.ref_ids and r not in srcs:
                    srcs.append(r)
            if srcs:
                a["prov:wasDerivedFrom"] = [self.res("prov:wasDerivedFrom", r) for r in srcs]
        if x.get("note"):
            a["skos:editorialNote"] = [self.lit("skos:editorialNote", x["note"])]
        return a or None

    def values(self, r, key, term=None, kind="lit"):
        """r[key] 의 값들을 Omeka 값으로. 확인 필요로 빈 값은 건너뛰고 메모로 돌린다."""
        out, term = [], term or key
        for x in as_list(r.get(key)):
            if isinstance(x, dict) and x.get("status") == "확인 필요":
                continue
            if kind == "ref":
                if x.get("ref") in self.ids:
                    out.append(self.res(term, x["ref"], self.ann(x)))
            elif kind == "uri":
                out.append({"type": "uri", "property_id": pid(term), "@id": x["value"], "@annotation": self.ann(x)})
            else:
                out.append(self.lit(term, x["value"], x.get("lang"), self.ann(x)))
        return out

    def notes(self, r):
        out = []
        for k, v in r.items():
            for x in as_list(v):
                if isinstance(x, dict) and x.get("status") == "확인 필요":
                    out.append(self.lit("skos:editorialNote", f"확인 필요 — {k}: {x.get('note', '')}".strip()))
        if r.get("representation"):
            out.append(self.lit("skos:editorialNote", r["representation"]))
        if r.get("note"):
            out.append(self.lit("skos:editorialNote", r["note"]))
        return out

    def citations(self, r):  # 자원 단위 dia:citation(원 데이터의 목록 그대로)
        return [self.lit("dia:citation", c) for c in r.get("dia:citation", [])]

    def item(self, r, kind):
        V = {"dcterms:identifier": [self.lit("dcterms:identifier", r["id"])]}
        def put(term, vals):
            if vals: V.setdefault(term, []).extend(vals)
        if kind == "생활 장면":
            for k in ("dcterms:title", "dcterms:description", "dcterms:temporal", "dia:aspect"):
                put(k, self.values(r, k))
            for k in ("dcterms:subject", "dcterms:spatial", "dcterms:source"):
                put(k, self.values(r, k, kind="ref"))
            put("dia:citation", self.citations(r))
        elif kind == "생활 대상":
            for k in ("skos:prefLabel", "skos:definition", "dia:aspect"):
                put(k, self.values(r, k))
            put("skos:exactMatch", self.values(r, "skos:exactMatch", kind="uri"))
            put("dcterms:source", self.values(r, "dcterms:source", kind="ref"))
        elif kind == "어휘":
            for k in ("skosxl:literalForm", "dia:variantForm", "dia:gloss", "dia:sourceLanguage", "dia:etymologyNote"):
                put(k, self.values(r, k))
            for k in ("dia:denotes", "dcterms:spatial", "dcterms:source"):
                put(k, self.values(r, k, kind="ref"))
            put("dia:citation", self.citations(r))
        elif kind == "장소":
            put("dcterms:title", self.values(r, "dcterms:title"))
            c = r.get("coords") or {}
            if "lat" in c and "lon" in c:
                a = self.ann(c)
                put("geo:lat", [self.lit("geo:lat", f"{float(c['lat']):.4f}", ann=a)])
                put("geo:long", [self.lit("geo:long", f"{float(c['lon']):.4f}", ann=a)])
            put("dcterms:isPartOf", self.values(r, "dcterms:isPartOf", kind="ref"))
        elif kind == "문화권":
            for k in ("dcterms:title", "dcterms:description"):
                put(k, self.values(r, k))
            for k in ("dcterms:spatial", "dcterms:source"):
                put(k, self.values(r, k, kind="ref"))
        elif kind == "출처":
            for k in ("dcterms:creator", "dcterms:title", "dcterms:date", "dcterms:isPartOf", "bibo:uri",
                      "dcterms:accessRights"):
                put(k, self.values(r, k))
        put("skos:editorialNote", self.notes(r))
        return V


KINDS = [("references", "출처"), ("places", "장소"), ("groups", "문화권"), ("concepts", "생활 대상"),
         ("labels", "어휘"), ("scenes", "생활 장면")]


def main():
    s = ARCHIVE.read_text(encoding="utf-8")
    data = json.loads(s[s.index("{"):s.rindex("}") + 1])
    # 출처: dcterms:source 로 쓰였거나 어떤 값의 cite 에 나온 것만
    used = set()
    def walk(x):
        if isinstance(x, dict):
            for c in x.get("cite", []) or []:
                used.add(c.split(":", 1)[0])
            for k, v in x.items():
                if k == "dcterms:source":
                    for y in as_list(v):
                        if isinstance(y, dict) and y.get("ref"): used.add(y["ref"])
                walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    for t, _ in KINDS[1:]:
        walk(data[t])
    refs = [r for r in data["references"] if r["id"] in used]
    skipped = [r["id"] for r in data["references"] if r["id"] not in used]
    rows = [(r, "출처") for r in refs] + [(r, k) for t, k in KINDS[1:] for r in data[t]]
    print(f"아이템 {len(rows)}개 예정 · 제외 출처 {skipped} · 제외 자료 {[m['id'] for m in data['materials']]}")
    if DRY:
        return

    tids = ensure_templates()
    print("템플릿", tids)
    sets = [x for x in api("GET", "item_sets", params={"per_page": 100}) if x.get("o:title") == SET_TITLE]
    set_id = sets[0]["o:id"] if sets else api("POST", "item_sets", {
        "o:is_public": True,
        "dcterms:title": [{"type": "literal", "property_id": pid("dcterms:title"), "@value": SET_TITLE}],
        "dcterms:description": [{"type": "literal", "property_id": pid("dcterms:description"),
                                 "@value": "한인 디아스포라 생활문화·어휘 아카이브. 원본: site-data/archive.js(검수 데이터)."}],
    })["o:id"]

    # 기존 아이템(식별자로) 찾기
    ids, page = {}, 1
    while True:
        got = api("GET", "items", params={"item_set_id": set_id, "per_page": 100, "page": page})
        for it in got:
            for v in it.get("dcterms:identifier", []):
                ids[v["@value"]] = it["o:id"]
        if len(got) < 100: break
        page += 1

    def base(r, kind):
        cls = r.get("class") if kind == "출처" else next(t["cls"] for t in templates() if t["label"] == kind)
        return {"o:resource_template": {"o:id": tids[kind]}, "o:resource_class": {"o:id": cid(cls)},
                "o:item_set": [{"o:id": set_id}], "o:is_public": True}

    # 1차: 링크 대상이 되도록 식별자만 가진 아이템을 먼저 만든다(ART 검사를 피하려고 템플릿 없이)
    for r, kind in rows:
        if r["id"] not in ids:
            p = base(r, kind); p.pop("o:resource_template")
            p["dcterms:identifier"] = [{"type": "literal", "property_id": pid("dcterms:identifier"), "@value": r["id"]}]
            ids[r["id"]] = api("POST", "items", p)["o:id"]
    # 2차: 전체 값과 값 주석을 채운다(PUT 은 값 전체를 바꾼다)
    b = Builder(data, ids, {r["id"] for r in refs})
    for r, kind in rows:
        p = base(r, kind); p.update(b.item(r, kind))
        api("PUT", f"items/{ids[r['id']]}", p)
    print(f"완료: 아이템 {len(rows)}개, 아이템 세트 {set_id}")


main()
