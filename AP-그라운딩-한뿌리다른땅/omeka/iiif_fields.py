# -*- coding: utf-8 -*-
"""IIIF 정보를 리소스 템플릿으로 관리하게 한다(다시 실행해도 같은 결과).

설계
- 아이템: 별도 템플릿을 만들지 않고 미디어가 붙는 '자료'·'출처' 템플릿에 'IIIF' 묶음을 더한다.
  (Omeka 아이템은 템플릿이 하나뿐이라, 따로 두면 AP 속성과 IIIF 속성 중 하나를 버려야 한다.)
    dcterms:license      이용 허락 URI  → 매니페스트 rights (CC 또는 RightsStatements.org URI)
    dcterms:rightsHolder 저작자 표시    → 매니페스트 requiredStatement
    dcterms:hasFormat    외부 IIIF 매니페스트 URI(소장처가 IIIF 를 줄 때) → Mirador·UV 가 그 매니페스트를 연다
- 미디어: 템플릿이 없던 미디어에 'IIIF 미디어' 템플릿을 새로 만든다.
    dcterms:title        캔버스 이름    → 매니페스트 canvas label
    dcterms:license, dcterms:rightsHolder  캔버스(이미지)별 권리
- IIIF Server 설정: requiredStatement ← dcterms:rightsHolder, 캔버스 이름 ← dcterms:title(없으면 파일 이름)

값: Commons 사진 2장(CC BY-SA 4.0, Naokijp), 원문 PDF 10편(In Copyright, 비공개 열람)
사용: py iiif_fields.py <키 JSON>
"""
import sys, json, urllib.request, urllib.parse
from pathlib import Path

KEY = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
BASE = "http://localhost:8000/api"
IN_COPYRIGHT = "http://rightsstatements.org/vocab/InC/1.0/"


def api(method, path, data=None, params=None):
    url = f"{BASE}/{path}?{urllib.parse.urlencode({**(params or {}), **KEY}, doseq=True)}"
    req = urllib.request.Request(url, method=method, headers={"Content-Type": "application/json"},
                                 data=json.dumps(data).encode() if data is not None else None)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} → {e.code}: {e.read().decode('utf-8')[:600]}")


_p = {}
def pid(term):
    if term not in _p:
        _p[term] = api("GET", "properties", params={"term": term})[0]["o:id"]
    return _p[term]


# IIIF Server 는 rights 속성 값을 문자열로 읽는데, Omeka 의 URI 값은 문자열로 바꾸면 이름표(label)가 나온다.
# 그래서 이용 허락은 URI 를 '텍스트'로 적고 형식을 검사한다.
LICENSE_PATTERN = r"https?://(creativecommons\.org|rightsstatements\.org)/.+"


def field(term, label, comment, dtype, mx=None):
    d = {}
    if mx: d["max_values"] = mx
    if term == "dcterms:license": d["input_control"] = LICENSE_PATTERN
    return {"o:property": {"o:id": pid(term)}, "o:alternate_label": label, "o:alternate_comment": comment,
            "o:data_type": [dtype], "o:is_required": False, "o:is_private": False, "o:default_lang": None,
            "o:data": [d] if d else []}


ITEM_IIIF = [
    ("dcterms:license", "IIIF 이용 허락", "매니페스트 rights. Creative Commons 또는 RightsStatements.org URI 하나를 텍스트로 "
     "(예: https://creativecommons.org/licenses/by-sa/4.0/, http://rightsstatements.org/vocab/InC/1.0/).", "literal", 1),
    ("dcterms:rightsHolder", "IIIF 저작자 표시", "매니페스트 requiredStatement(뷰어에 늘 보이는 표기). 예: 촬영자, CC BY-SA 4.0, 소장처.", "literal", None),
    ("dcterms:hasFormat", "외부 IIIF 매니페스트", "소장처가 IIIF 매니페스트를 주면 그 URI. 있으면 뷰어가 이 매니페스트를 연다.", "uri", None),
]
MEDIA_IIIF = [
    ("dcterms:title", "캔버스 이름", "뷰어의 캔버스(쪽·이미지) 이름. 비우면 파일 이름.", "literal", 1),
    ("dcterms:license", "IIIF 이용 허락", "이 이미지·파일의 이용 허락 URI(텍스트, 아이템과 다를 때).", "literal", 1),
    ("dcterms:rightsHolder", "IIIF 저작자 표시", "이 이미지·파일의 저작자 표시.", "literal", None),
]


def add_item_group(label):
    t = next(t for t in api("GET", "resource_templates", params={"per_page": 100}) if t["o:label"] == label)
    rtps = t["o:resource_template_property"]
    have = {r["o:property"]["o:id"] for r in rtps}
    for term, lab, com, dt, mx in ITEM_IIIF:
        if pid(term) in have:  # 이미 있는 속성은 IIIF 정의로 맞춘다
            r = next(r for r in rtps if r["o:property"]["o:id"] == pid(term))
            r.update({k: v for k, v in field(term, lab, com, dt, mx).items() if k != "o:property"})
        else:
            rtps.append(field(term, lab, com, dt, mx))
    data = dict(t.get("o:data") or {})
    groups = dict(data.get("groups") or {})
    if not groups:  # ART 묶음: 기존 속성은 '기술', IIIF 속성은 'IIIF'
        terms = [api("GET", f"properties/{r['o:property']['o:id']}")["o:term"] for r in rtps]
        groups["기술"] = [x for x in terms if x not in [i[0] for i in ITEM_IIIF]]
    groups["IIIF"] = [i[0] for i in ITEM_IIIF]
    data["groups"] = groups
    payload = {k: t[k] for k in ("o:label", "o:resource_class", "o:title_property", "o:description_property") if t.get(k)}
    payload.update({"o:resource_template_property": rtps, "o:data": data})
    api("PUT", f"resource_templates/{t['o:id']}", payload)
    print("템플릿", label, "← IIIF 묶음", [i[0] for i in ITEM_IIIF])


def media_template():
    found = [t for t in api("GET", "resource_templates", params={"per_page": 100}) if t["o:label"] == "IIIF 미디어"]
    payload = {"o:label": "IIIF 미디어", "o:title_property": {"o:id": pid("dcterms:title")},
               "o:resource_template_property": [field(*f) for f in MEDIA_IIIF],
               "o:data": {"use_for_resources": ["media"]}}
    t = api("PUT", f"resource_templates/{found[0]['o:id']}", payload) if found else api("POST", "resource_templates", payload)
    print("템플릿 IIIF 미디어", t["o:id"])
    return t["o:id"]


def lit(term, v):
    return {"type": "literal", "property_id": pid(term), "@value": v}


def set_values(kind, rid, values, extra=None):
    """PATCH: 주어진 속성만 바꾼다. 템플릿 필수값 검사가 보낸 값만 보므로 기존 값도 모두 함께 보낸다
    (PATCH 라 o:media 등 다른 것은 그대로 남는다)."""
    current = api("GET", f"{kind}/{rid}")
    merged = {k: v for k, v in current.items() if ":" in k and isinstance(v, list) and v
              and isinstance(v[0], dict) and "property_id" in v[0]}
    merged.update(values)
    api("PATCH", f"{kind}/{rid}", {**merged, **(extra or {})})


def fill(media_tid):
    # 미디어가 있는 아이템 = Commons 사진(자료)과 PDF 가 붙은 출처
    items = [i for i in api("GET", "items", params={"per_page": 200, "has_media": 1}) if i.get("o:media")]
    for it in items:
        ident = it["dcterms:identifier"][0]["@value"]
        if ident.startswith("record:commons"):
            holder = "Naokijp · CC BY-SA 4.0 · Wikimedia Commons(크기를 줄임)"
            lic = (it.get("dcterms:license") or [{}])[0]  # 기록에서 온 이용 허락(URI 값이었을 수 있음)을 텍스트로
            media_license = lic.get("@id") or lic.get("@value")
        else:
            holder = "저작권은 저자·발행처에 있음 — 연구·수업용 비공개 열람"
            media_license = IN_COPYRIGHT
        item_vals = {"dcterms:license": [lit("dcterms:license", media_license)],
                     "dcterms:rightsHolder": [lit("dcterms:rightsHolder", holder)]}
        set_values("items", it["o:id"], item_vals)
        for m in it["o:media"]:
            media = api("GET", f"media/{m['o:id']}")
            label = it["o:title"] if not media.get("o:media_type", "").endswith("pdf") else "원문 PDF"
            vals = {"dcterms:title": [lit("dcterms:title", label)],
                    "dcterms:rightsHolder": [lit("dcterms:rightsHolder", holder)]}
            if media_license:
                vals["dcterms:license"] = [lit("dcterms:license", media_license)]
            set_values("media", m["o:id"], vals, {"o:resource_template": {"o:id": media_tid}})
        print("값", it["o:id"], ident, "· 미디어", [m["o:id"] for m in it["o:media"]])


add_item_group("자료")
add_item_group("출처")
fill(media_template())
