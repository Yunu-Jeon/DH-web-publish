# -*- coding: utf-8 -*-
"""Omeka S 에 IIIF 뷰어로 볼 미디어를 붙인다(다시 실행해도 이미 있는 것은 건너뜀).
1) 정적 사이트 기록 갤러리의 Commons 사진 2장 → '자료' 템플릿 아이템을 만들고 이미지를 붙인다(공개, Mirador).
2) 원문 PDF → 같은 이름(출처 ID)의 '출처' 아이템에 비공개 미디어로 붙인다(로그인한 사람만, Universal Viewer).
   PDF 는 저작권 때문에 공개하지 않는다(정적 사이트에서도 uploads/ 는 올리지 않음).
사용: py add_media.py <DH-Korean-Diaspora 폴더> <키 JSON>
"""
import sys, json, uuid, mimetypes, urllib.request, urllib.parse
from pathlib import Path

REPO, KEY = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
BASE = "http://localhost:8000/api"
ITEM_SET, SITE = 1, 1  # 「한 뿌리, 다른 땅」 아이템 세트와 사이트


def api(method, path, data=None, params=None, files=None):
    url = f"{BASE}/{path}?{urllib.parse.urlencode({**(params or {}), **KEY}, doseq=True)}"
    if files:  # Omeka 파일 업로드: multipart 의 data(JSON) + file[n]
        b = uuid.uuid4().hex
        body = f'--{b}\r\nContent-Disposition: form-data; name="data"\r\n\r\n{json.dumps(data)}\r\n'.encode()
        for i, f in enumerate(files):
            ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
            body += (f'--{b}\r\nContent-Disposition: form-data; name="file[{i}]"; filename="{f.name}"\r\n'
                     f"Content-Type: {ctype}\r\n\r\n").encode() + f.read_bytes() + b"\r\n"
        body += f"--{b}--\r\n".encode()
        headers = {"Content-Type": f"multipart/form-data; boundary={b}"}
    else:
        body = json.dumps(data).encode() if data is not None else None
        headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} → {e.code}: {e.read().decode('utf-8')[:600]}")


_ids = {}
def pid(term):
    if term not in _ids:
        _ids[term] = api("GET", "properties", params={"term": term})[0]["o:id"]
    return _ids[term]


def cid(term):
    return api("GET", "resource_classes", params={"term": term})[0]["o:id"]


def tid(label):
    return next(t["o:id"] for t in api("GET", "resource_templates", params={"per_page": 100}) if t["o:label"] == label)


def find_item(identifier):
    got = api("GET", "items", params={"property[0][property]": pid("dcterms:identifier"),
                                      "property[0][type]": "eq", "property[0][text]": identifier})
    return got[0] if got else None


def lit(term, value, lang=None, ann=None):
    v = {"type": "literal", "property_id": pid(term), "@value": value}
    if lang: v["@language"] = lang
    if ann: v["@annotation"] = ann
    return v


def res(term, item_id, ann=None):
    v = {"type": "resource:item", "property_id": pid(term), "value_resource_id": item_id}
    if ann: v["@annotation"] = ann
    return v


def uri(term, value):
    return {"type": "uri", "property_id": pid(term), "@id": value}


def first(x):
    return x[0] if isinstance(x, list) else x


def add_records():
    s = (REPO / "site-data" / "archive.js").read_text(encoding="utf-8")
    data = json.loads(s[s.index("{"):s.rindex("}") + 1])
    template, klass = tid("자료"), cid("dctype:StillImage")
    for r in data.get("records", []):
        img = REPO / (r.get("dia:image") or {}).get("path", "")
        if not img.is_file() or find_item(r["id"]):
            continue  # 이미지가 저장소에 없는 기록(소장처 링크만 있는 것)이나 이미 만든 것은 건너뜀
        refs = {}
        for x in r.get("dcterms:spatial", []) + r.get("dcterms:subject", []):
            it = find_item(x["ref"])
            if it: refs[x["ref"]] = it["o:id"]
        def ann(x):  # 기록의 basis '해석' 만 값 종류로 옮긴다(나머지는 원본 기록 그대로라 주석 없음)
            if x.get("basis") == "해석":
                a = {"dia:basis": [lit("dia:basis", "해석")]}
                if x.get("note"): a["skos:editorialNote"] = [lit("skos:editorialNote", x["note"])]
                return a
            return None
        alt = r.get("dcterms:alternative") or {}
        payload = {
            "o:resource_template": {"o:id": template}, "o:resource_class": {"o:id": klass},
            "o:item_set": [{"o:id": ITEM_SET}], "o:site": [{"o:id": SITE}], "o:is_public": True,
            "dcterms:identifier": [lit("dcterms:identifier", r["id"])],
            "dcterms:title": [lit("dcterms:title", first(r["dcterms:title"])["value"])],
            "dcterms:alternative": [lit("dcterms:alternative", alt["value"], alt.get("lang"))] if alt else [],
            "dcterms:type": [lit("dcterms:type", first(r["dcterms:type"])["value"])],
            "dcterms:creator": [lit("dcterms:creator", c["value"]) for c in r.get("dcterms:creator", [])],
            "dcterms:date": [lit("dcterms:date", first(r["dcterms:date"])["value"])],
            "dcterms:description": [lit("dcterms:description", d["value"]) for d in r.get("dcterms:description", [])],
            "dcterms:rights": [lit("dcterms:rights", first(r["dcterms:rights"])["value"])],
            "dcterms:license": [uri("dcterms:license", r["dcterms:license"]["value"])] if r.get("dcterms:license") else [],
            "dcterms:source": [uri("dcterms:source", r["dcterms:source"]["value"])],
            "dcterms:spatial": [res("dcterms:spatial", refs[x["ref"]], ann(x)) for x in r.get("dcterms:spatial", [])
                                if x["ref"].startswith("group:") and x["ref"] in refs],
            "dcterms:subject": [res("dcterms:subject", refs[x["ref"]]) for x in r.get("dcterms:subject", []) if x["ref"] in refs],
            "o:media": [{"o:ingester": "upload", "file_index": 0, "o:is_public": True,
                         "dcterms:title": [lit("dcterms:title", img.name)],
                         "dcterms:rights": [lit("dcterms:rights", r.get("dia:attribution", {}).get("value", ""))]}],
        }
        payload = {k: v for k, v in payload.items() if v != []}
        it = api("POST", "items", payload, files=[img])
        print("자료", it["o:id"], r["id"], "· 미디어", [m["o:id"] for m in it["o:media"]])


def add_pdfs():
    for pdf in sorted((REPO / "uploads").glob("*.pdf")):
        item = find_item(pdf.stem)
        if not item:
            print("건너뜀", pdf.name, "— 같은 ID 의 출처 아이템 없음"); continue
        if item.get("o:media"):
            print("건너뜀", pdf.name, "— 이미 미디어 있음"); continue
        m = api("POST", "media", {"o:ingester": "upload", "file_index": 0, "o:item": {"o:id": item["o:id"]},
                                  "o:is_public": False, "dcterms:title": [lit("dcterms:title", pdf.name)]}, files=[pdf])
        print("PDF", pdf.name, "→ 출처", item["o:id"], "· 미디어", m["o:id"], "(비공개)")


add_records()
add_pdfs()
