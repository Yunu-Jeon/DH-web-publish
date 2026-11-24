AP 그라운딩 가이드 묶음 — 한 뿌리, 다른 땅 (한인 디아스포라 생활문화·어휘 아카이브)
원본: 「AP 그라운딩 가이드」(구술 AP v2)를 우리 AP(ap/application-profile.md)에 맞춰 고친 판

AP-그라운딩-가이드_한뿌리다른땅.md — 산출 계약(어떻게 적어야 스타터킷 화면에 뜨는가) + AP→스타터킷 대응표
기술규칙.ttl          — 우리 AP + 화면 계약의 SHACL 기술규칙, 커스텀 어휘(dia:) 정의 동봉. LLM 에는 이것을 준다
기술규칙.dctap.csv    — 같은 규칙의 사람용 대조표(Excel). layer 열: AP / 화면 / 근거
한뿌리다른땅.ttl      — 스타터킷에 올릴 데이터(검수된 site-data/archive.js 를 변환한 것)
export_ttl.py        — archive.js → 한뿌리다른땅.ttl 변환기
check_contract.py    — 가이드 §3 「조용한 실패」 기계 검사 + SHACL 검사
build_rules.py       — 기술규칙.ttl 과 .dctap.csv 를 한 표에서 만드는 스크립트

다시 만들기(데이터를 고친 뒤):
  py -m pip install rdflib pyshacl
  py export_ttl.py ..\DH-Korean-Diaspora\site-data\archive.js 한뿌리다른땅.ttl
  py check_contract.py 한뿌리다른땅.ttl 기술규칙.ttl      → "계약 위반 0 건 · SHACL: 적합" 이어야 올린다
올리기: 스타터킷 컬렉션 화면 → 「TTL 올려 컬렉션 더하기」 → 한뿌리다른땅.ttl (컬렉션 이름 칸은 비워 둠)

Omeka S 로 옮기기·검색(2026-11):
  omeka/omeka_import.py  — archive.js → Omeka S 아이템(AP 템플릿 + 값마다 근거 주석: dia:basis, prov:atLocation, prov:wasDerivedFrom)
                           py omeka\omeka_import.py ..\..\DH-Korean-Diaspora\site-data\archive.js <키.json>  (다시 실행해도 중복 없이 갱신)
  sparql/load_ttl.php    — 한뿌리다른땅.ttl 을 Sparql 모듈 저장소의 그래프 하나로 올림(컨테이너 안에서 실행).
                           Sparql 설정에서 Index 를 다시 누르면 저장소가 비워지므로 그 뒤에 다시 실행
  sparql/export_evidence.py — Omeka 값 주석(값 종류·근거 쪽수·근거 출처)을 rdf:Statement 노드로 내보냄 → load_ttl.php 로
                           그래프 https://yunu-jeon.github.io/DH-Korean-Diaspora/graph/evidence 에 올림(Sparql 모듈은 값 주석을 인덱싱하지 않음)
  sparql/queries.json    — 검색 예제 질의 12개(ARC2 제약: 필수 패턴 4개까지, REGEX 에는 "i")
  sparql/build_site.py   — Omeka 사이트 /s/hanppuri 의 'SPARQL 검색' 페이지를 만들거나 고침(테마: ..\..\omeka-themes\hanppuri)
  <키.json> 은 {"key_identity": "…", "key_credential": "…"} 형식의 Omeka API 키. 저장소에 넣지 않는다.

IIIF 뷰어(2026-11-24): 모듈 IIIF Server 3.6.36 · Image Server 3.6.28 · Mirador 3.4.18 · Universal Viewer 3.6.17 (Common 3.4.96)
  omeka/add_media.py     — Commons 사진 2장 → '자료' 아이템(공개, Mirador) / uploads/*.pdf → 같은 ID 출처 아이템에 비공개 미디어(UV)
                           py omeka\add_media.py ..\..\DH-Korean-Diaspora <키.json>  (이미 있으면 건너뜀)
  설정: IIIF Server 의 iiifserver_url_version_add = true (주소를 /iiif/3/{id}/manifest 로. 아이템 ID 2 가 버전 2 로 읽히는 문제)
  omeka/iiif_fields.py   — IIIF 정보를 템플릿으로 관리: '자료'·'출처' 템플릿에 IIIF 묶음, 미디어용 'IIIF 미디어' 템플릿 + 값 채우기
                           IIIF 이용 허락 dcterms:license(CC·RightsStatements URI 를 텍스트로) → 매니페스트 rights
                           IIIF 저작자 표시 dcterms:rightsHolder → requiredStatement · 외부 IIIF 매니페스트 dcterms:hasFormat
                           캔버스 이름 = 미디어의 dcterms:title(없으면 파일 이름)
  IIIF Server 설정(관리자 → Modules → IIIF Server 에서도 바꿀 수 있음):
    iiifserver_manifest_rights_property = ["dcterms:license"]   (URI 값은 문자열로 바꾸면 이름표가 나와서 텍스트로 받음)
    iiifserver_manifest_attribution_property = "dcterms:rightsHolder"
    iiifserver_manifest_canvas_label = "property_or_source", iiifserver_manifest_canvas_label_property = "dcterms:title"
    값을 고쳤는데 매니페스트에 안 보이면 캐시(files/iiif/3/{id}.allowed.manifest.json)를 지운다
  컨테이너에서 손댄 것(컨테이너를 새로 만들면 다시 해야 함):
    - PHP exif 확장 설치: docker exec dh-web-publish-omekas-1 docker-php-ext-install exif  → 컨테이너 재시작
    - /var/www/html/.htaccess 에서 Image Server 의 "fast IIIF tile server" 규칙 제거(vips 가 없고 modules 가 심볼릭 링크라 500)
