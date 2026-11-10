# AP 그라운딩 가이드 — 한 뿌리, 다른 땅

**한인 디아스포라 생활문화·어휘 아카이브용으로 고쳐 쓴 판.**
원본 「AP 그라운딩 가이드」(구술 AP v2)의 계약 — *어떻게 적어야 스타터킷 화면에 뜨는가* — 은 그대로 두고,
그 계약을 우리 AP(`ap/application-profile.md`, 클래스 7개)에 대응시켰습니다.
원본의 규칙 번호(§2.1~§2.11)를 그대로 따라가므로 두 문서를 나란히 놓고 볼 수 있습니다.

---

## 1. 이 문서의 쓰임

### 길이 두 개다

| 길 | 언제 | 무엇을 쓰나 |
|---|---|---|
| **① 변환** (권장) | 이미 검수한 데이터(`data/*.json` → `site-data/archive.js`)를 올릴 때 | `export_ttl.py` 로 기계 변환 → `check_contract.py` 로 검사. **새 사실이 생기지 않는다** |
| **② LLM 그라운딩** | 새 문헌(PDF)을 처음 기술할 때 | 이 문서 + `기술규칙.ttl` + 원문 PDF 를 LLM 에 함께 준다. 결과는 반드시 `check_contract.py` 와 원문 대조 |

우리 아카이브는 이미 값마다 근거 쪽수(`cite`)와 성격(`basis`: 보고·해석·문헌 외)을 달아 둔 검수 데이터가 있으므로,
**같은 PDF 를 LLM 에 다시 넣어 그라운딩하는 것은 손해**입니다. 검수된 값을 버리고 검수 안 된 값을 새로 만드는 일이기 때문입니다.
②는 문헌을 새로 추가할 때만 씁니다.

### ②의 프롬프트 (예)

> 첨부한 「AP 그라운딩 가이드 — 한 뿌리, 다른 땅」과 `기술규칙.ttl`, 그리고 문헌 PDF 를 읽고, 가이드의 규칙을 지켜
> 스타터킷에 올릴 Turtle 한 장을 만들어 줘. 컬렉션은 `ric:col-한-뿌리-다른-땅` 하나만 쓰고,
> PDF 에 없는 사실은 만들지 마. 모든 개체에 `dcterms:source`(출처 개체)와 `dia:citation "출처ID:인쇄쪽"`을 달고,
> 연구자의 해석인 문장은 "저자는 …로 본다"처럼 해석임이 드러나게 써 줘. 좌표처럼 문헌에 없는 값은 넣지 말고
> `skos:editorialNote "확인 필요 — …"` 로 남겨 줘.

---

## 2. 반드시 지킬 것

스타터킷은 아래 규칙을 **검사하지 않습니다.** 어기면 오류 대신 화면이 조용히 빕니다.
그래서 이 묶음에는 원본 §3 표를 기계로 흉내 내는 `check_contract.py` 를 넣었습니다.

### 2.1 네임스페이스 — 개체는 `ric:` 안, 우리 어휘는 `dia:`

```turtle
@prefix ric:    <http://archives.nanet.go.kr/id/> .                       # 개체 IRI — 스타터킷이 요구
@prefix rico:   <https://www.ica.org/standards/RiC/ontology#> .           # https · '#'
@prefix skos:   <http://www.w3.org/2004/02/skos/core#> .
@prefix skosxl: <http://www.w3.org/2008/05/skos-xl#> .
@prefix geo:    <http://www.w3.org/2003/01/geo/wgs84_pos#> .
@prefix foaf:   <http://xmlns.com/foaf/0.1/> .
@prefix dcterms:<http://purl.org/dc/terms/> .
@prefix dctype: <http://purl.org/dc/dcmitype/> .
@prefix bibo:   <http://purl.org/ontology/bibo/> .
@prefix dia:    <https://yunu-jeon.github.io/DH-Korean-Diaspora/ns#> .     # AP 1장의 커스텀 어휘
```

- 개체 지역명은 사이트 ID 의 `:` 를 `-` 로 바꿔 씁니다: `scene:koryo-babimuri` → `ric:scene-koryo-babimuri`.
  출처는 `ric:ref-kwon2020` 처럼 `ref-` 를 붙입니다.
- 원래 사이트 ID 는 `rico:identifier` 로, 원 사이트 페이지는 `rdfs:seeAlso` 로 남깁니다(관계망 밖 층).
- **`dia:` 는 관계망 간선 필터의 다섯 네임스페이스(§2.7)에 없습니다.** 그래서 `dia:denotes` 같은 AP 관계는
  화면에 선으로 그려지지 않습니다. 선이 필요한 관계는 §2.7 의 대응 술어를 하나 더 답니다.

> ⚠ `ric:` 는 국회기록원 도메인입니다. 스타터킷에 올리기 위한 **임시 식별자**이지 우리 자원의 영구 식별자가 아닙니다.
> FAIR 의 F1(전역 고유·영구 식별자)을 따지면 우리 것은 `rdfs:seeAlso` 로 남긴 GitHub Pages 주소 쪽입니다.

### 2.2 클래스 — 표준 타입 **정확히 1개** + AP 클래스 병기

| AP 클래스 | AP 표준 클래스 | 스타터킷 표준 타입(화면 표기) | 왜 이것인가 |
|---|---|---|---|
| 생활 장면 | `dia:Scene` | `rico:Activity` (활동) | RiC-O Activity = "the doing of something for some human purpose". 먹고·부르고·일하고·배우는 장면은 '하는 일'이다. 날짜가 서술형이라 Event 로 둬도 연표에는 어차피 안 뜬다 |
| 생활 대상 | `skos:Concept` | `skos:Concept` (개념) | 같은 클래스 |
| 어휘 | `skosxl:Label` | `rico:Concept` (개념) | SKOS-XL 은 `skosxl:Label` 을 `skos:Concept` 와 **서로소(disjoint)**로 정의한다. 그래서 `skos:Concept` 를 붙이면 형식적으로 모순이다. RiC-O 의 Concept("idea, unit of thought, abstract cultural object")로 근사한다 |
| 장소 | `dcterms:Location` | `rico:Place` (장소) | |
| 문화권 | `foaf:Group` | `rico:Concept` (개념) + `rico:DemographicGroup` | 12종에 Group 이 없다. RiC-O CorporateBody 는 "법적·사회적 지위를 가진 조직된 집단"이라 고려인 같은 이주민 범주에 맞지 않는다. RiC-O DemographicGroup("공유된 특성에 따른 사람·집단의 범주")은 Type ⊂ Concept 이므로 표준 타입은 Concept 가 된다 |
| 출처 | `bibo:AcademicArticle` 등 | `rico:Record` (기록) | |
| 자료 | `dctype:StillImage` 등 | `rico:Record` (기록) | |

```turtle
ric:label-babimuri a rico:Concept, skosxl:Label .     # 표준 1개 + AP 클래스
```

- 병기한 AP 클래스의 지역명(`Scene`·`Label`·`Location`·`Group`·`DemographicGroup`·`AcademicArticle`·`StillImage`…)은
  12종과 겹치지 않습니다(원본 §4 주의①). **새 커스텀 클래스를 만들 때 `dia:Place`·`dia:Concept` 같은 이름은 금지.**
- 화면용으로 더한 개체가 둘 있습니다: 측면 개념 4개(`ric:aspect-eat` …, `skos:Concept` + `rico:ActivityType`)와
  개념체계 3개(§2.8 아래).

### 2.3 이름은 표준 타입이 정하는 술어에 — AP 속성은 그대로 두고 하나 더

| AP 클래스 | AP 이름 속성 | 화면 이름 술어(추가) |
|---|---|---|
| 생활 장면 | `dcterms:title` | `rico:name` |
| 생활 대상 | `skos:prefLabel` | (같음) |
| 어휘 | `skosxl:literalForm` | `skos:prefLabel` |
| 장소 | `dcterms:title` | `rico:name` |
| 문화권 | `dcterms:title` | `skos:prefLabel` |
| 출처·자료 | `dcterms:title` | `rico:title` |

`rdfs:label` 은 쓰지 않습니다(스타터킷이 사진 출처 크레딧으로 읽음). 설명도 같은 방식으로
`dcterms:description`·`dia:gloss` 옆에 `rico:generalDescription` 을 하나 더 답니다.

### 2.4 리터럴은 평문 — AP 의 `@ko` 와 충돌한다

AP 는 `skos:prefLabel` 을 "문자열(@ko)", `skosxl:literalForm` 을 "문자열(언어 태그)"로 정했지만,
스타터킷에서는 언어태그가 붙으면 이름 정확일치 질의가 0건이 됩니다. **스타터킷용 내보내기에서는 평문**으로 쓰고,
어휘의 표기 언어는 잃지 않도록 `dcterms:language "en"` 으로 옮깁니다(내보내기 전용 보조 속성).
`기술규칙.ttl` 은 모든 리터럴에 `sh:datatype xsd:string` 을 걸어 `@ko` 가 섞이면 위반으로 잡습니다.

### 2.5 날짜 — 우리 데이터의 날짜는 거의 다 서술형이다

`"1937년 강제 이주 이후 ~ 현재"`, `"1930년대"`, `"초기 이민 2세대"` 같은 값은 `YYYY` 세 정밀도에 들어가지 않습니다.
**이런 값을 `rico:beginningDate`·`rico:date` 에 넣지 않습니다.** 앞 4자가 맞는 값(`"1937년 이후"`)은 연표에는 뜨지만
정렬이 뒤집히는, 원본 §3 이 "더 나쁘다"고 한 사고가 납니다. AP 대로 `dcterms:temporal`(장면)·`dcterms:date`(출처·자료)에만 둡니다.
→ **연표 화면은 비는 것이 정상입니다.** 채우려면 장면마다 문헌이 직접 확인해 주는 연도만 따로 뽑아 `rico:beginningDate "1937"` 처럼
달아야 하는데, 이것은 새 값을 만드는 일이라 검수가 필요합니다(§7).

### 2.6 좌표 — 전부 「문헌 외」 근사값임을 같이 적는다

```turtle
ric:place-kazakhstan a rico:Place, dcterms:Location ;
    geo:lat "48.0000" ; geo:long "67.0000" ;
    skos:editorialNote "좌표는 문헌 외 값 — 나라 중심 근사값. 검수 필요" .
```

18곳 모두 원본 데이터에서 `basis: "문헌 외"` 입니다. 지도 마커는 뜨지만 사실의 근거가 아님을 주기로 남깁니다.

### 2.7 관계 — AP 관계 옆에 「그려지는」 RiC-O 관계를 하나 더

AP 관계는 대부분 `dcterms:`·`dia:` 라 관계망에 그려지지 않습니다. 그래서 같은 사실을 RiC-O/SKOS 술어로 **한 번 더** 적습니다
(한 방향만 — §2.9). 두 줄은 같은 사실이지만 하나는 관계망 밖 층이라 화면에 두 줄로 뜨지 않습니다.

| AP 관계(그대로 둠) | 그려지는 술어(추가) | 근거(RiC-O 1.1 정의 확인) |
|---|---|---|
| 장면 `dcterms:subject` 생활 대상 | `rico:isRelatedTo` | `rico:hasOrHadSubject` 는 domain 이 RecordResource 라 활동에 쓰면 장면이 '기록'으로 추론된다 |
| 장면·어휘·자료 `dcterms:spatial` 문화권 | `rico:isRelatedTo` | 문화권은 장소가 아니다 |
| 장면 `dcterms:spatial` 장소 | `rico:isAssociatedWithPlace` | domain Thing, range Place |
| 문화권 `dcterms:spatial` 장소 | `rico:isAssociatedWithPlace` | |
| 장소 `dcterms:isPartOf` 장소 | `rico:isOrWasContainedBy` | domain·range 모두 Place |
| 어휘 `dia:denotes` 생활 대상 | `rico:isRelatedTo` | `skos:related` 는 양끝을 `skos:Concept` 로 추론시켜 §2.2 의 서로소 문제가 다시 생긴다 |
| 장면 `dia:aspect` "먹는 것" | `rico:hasActivityType` → 측면 개념 | domain Activity, range ActivityType |
| 생활 대상 `dia:aspect` "먹는 것" | `skos:broader` → 측면 개념 | 계층은 하위→상위 broader 만 읽힌다(원본 §3) |
| 자료 `dcterms:relation` 장면 | `rico:isRelatedTo` | |

> `rico:isRelatedTo` 는 RiC-O 에서 가장 일반적인 관계(대칭)입니다. 화면에는 「관련」 정도로만 보이므로,
> 정확한 뜻(다루는 대상인지, 가리키는 말인지)은 같은 자리의 AP 관계와 원 사이트에서 읽어야 합니다.

### 2.8 컬렉션·개념체계

```turtle
ric:col-한-뿌리-다른-땅 a rico:RecordSet ; rico:title "한 뿌리, 다른 땅" .
ric:ref-kwon2020    rico:isOrWasIncludedIn ric:col-한-뿌리-다른-땅 .   # 기록(출처·자료)만
ric:scene-…, ric:label-…, ric:place-…   rico:isOrWasSubjectOf ric:col-한-뿌리-다른-땅 .  # 그 밖 전부
```

주제 화면은 `skos:ConceptScheme` 과 `skos:inScheme` 이 있어야 채워집니다. AP 에는 개념체계가 없으므로 셋을 더합니다.

| 개념체계 | 담는 것 | 최상위 개념 |
|---|---|---|
| `ric:scheme-life-objects` 생활 대상 | 생활 대상 26 + 측면 4 | 먹는 것·부르는 것·일하는 것·배우는 것 |
| `ric:scheme-words` 디아스포라 어휘 | 어휘 34 | — |
| `ric:scheme-cultures` 문화권 | 문화권 3 | 고려인·재일조선인·하와이 한인 |

말(어휘)과 대상(생활 대상)을 다른 체계에 둔 것은 AP 의 「말과 대상 분리」 설계를 화면에서도 지키기 위해서입니다.

### 2.9 방향 — 개체에서 나가는 한 방향

우리 데이터에는 원본 §2.9 의 역속성 9쌍 중 `isOrWasSubjectOf`(→컬렉션)와 `isOrWasIncludedIn`(→컬렉션)만 쓰이고,
둘 다 개체 → 컬렉션 한 방향입니다. 장소는 늘 개체 → 장소(`isAssociatedWithPlace`), 계층은 하위 → 상위(`broader`,
`isOrWasContainedBy`)입니다.

### 2.10 근거는 관계망 밖 층에

| 무엇 | 술어 | 예 |
|---|---|---|
| 근거 출처(AP) | `dcterms:source` → 출처 개체 IRI | `dcterms:source ric:ref-kwon2020` |
| 근거 쪽수(AP) | `dia:citation` | `"kwon2020:108"` — 인쇄 쪽. 웹 문헌은 절 이름 |
| 검수 주기 | `skos:editorialNote` | `"확인 필요 — dcterms:temporal: 연도 숫자 판독 불가"` |

출처 13건이 관계망에서 외톨이 점으로 보이는 것은 **정상**입니다. 근거 간선을 `rico:` 로 그리면 성좌가 뭉개집니다.

### 2.11 구술자 한 명 — 해당 없음

구술 기록이 아니고 인물 클래스도 없으므로 `rico:hasCreator` 를 쓰지 않습니다. 출처의 저자는 AP 대로 `dcterms:creator` 문자열입니다.

### 2.12 (추가) 「확인 필요」·「해석」·「문학 속 재현」을 숨기지 않는다

| 원본 데이터 | Turtle |
|---|---|
| `status: "확인 필요"`(값 비어 있음) | 값은 내보내지 않고 `skos:editorialNote "확인 필요 — <속성>: <메모>"` |
| 관계 값의 `basis: "해석"` + note (짐치→김치, Man Doo→만두, 朝鮮漬→재일 등) | `skos:editorialNote "해석 — <속성> → <대상>: <메모>"` |
| 장면 `representation: "문학 속 재현"` | `skos:editorialNote "문학 속 재현"` + 화면 설명 맨 앞에 `(문학 속 재현)` |
| 설명 문장의 `basis: "해석"` | 문장 자체가 "저자는 …로 본다"로 쓰여 있어 그대로 둔다 |

### 2.13 (추가) 설명은 문장 배열을 이은 **하나**

AP 는 장면·문화권의 `dcterms:description` 을 **1개(필수)**로 정했는데, 원본 데이터는 근거가 다른 문장들의 배열입니다.
Turtle 에서는 AP 대로 순서대로 이어 하나로 냅니다. 문장별 근거는 `dia:citation`(합집합)과 원본 JSON·근거대조표에 남습니다.

---

## 3. 어기면 무엇이 비는가 — 우리 데이터에서 생기기 쉬운 것만

원본 §3 표가 전부 적용됩니다. 그중 우리 데이터에서 실제로 걸리기 쉬운 것:

| 실수 | 결과 | 막는 곳 |
|---|---|---|
| 어휘에 `skos:Concept` 를 붙임 | 화면은 뜨지만 SKOS-XL 과 형식적으로 모순 | 이 가이드 §2.2 |
| 문화권을 `foaf:Group` 하나로만 | 12종 밖 → 문화권 3개와 거기 닿던 간선이 **전부** 사라짐 | `check_contract.py` §2.2 |
| `dcterms:temporal "1937년 이후"` 를 `rico:beginningDate` 로 | 연표에 뜨지만 정렬이 뒤집힘 | §2.5 |
| `skos:prefLabel "김치"@ko` (AP 그대로) | 이름 질의 0건 | SHACL `sh:datatype xsd:string` |
| `dia:denotes` 만 적음 | 말과 대상 사이 선이 관계망에 없음 | §2.7 |
| 좌표를 `"76,89"` 로 | 지도 「곳」 수에는 들고 마커만 깨짐 | SHACL 패턴 |
| `concept-…` 에 `skos:inScheme` 빠짐 | 주제 목록에 안 뜸 | `check_contract.py` §3 |

---

## 4. 커스텀 어휘(`dia:`)

정의는 `기술규칙.ttl` 끝에 동봉했습니다(`dia:Scene`, `dia:aspect`, `dia:citation`, `dia:variantForm`, `dia:gloss`,
`dia:denotes`, `dia:sourceLanguage`, `dia:etymologyNote`). 원본 §4 주의②와 달리 **`dia:` 술어는 관계망 필터에 들어 있지 않으므로**
선이 필요한 관계는 §2.7 처럼 RiC-O 술어를 함께 답니다.

---

## 5. 최소 예시 — 실제 데이터에서 잘라 낸 것

장면 1 · 생활 대상 1 · 측면 1 · 어휘 1 · 문화권 1 · 장소 1 · 출처 1 · 개념체계 3 · 컬렉션 1. `check_contract.py`·SHACL 모두 통과합니다.

```turtle
@prefix ric:     <http://archives.nanet.go.kr/id/> .
@prefix rico:    <https://www.ica.org/standards/RiC/ontology#> .
@prefix skos:    <http://www.w3.org/2004/02/skos/core#> .
@prefix skosxl:  <http://www.w3.org/2008/05/skos-xl#> .
@prefix geo:     <http://www.w3.org/2003/01/geo/wgs84_pos#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix bibo:    <http://purl.org/ontology/bibo/> .
@prefix foaf:    <http://xmlns.com/foaf/0.1/> .
@prefix dia:     <https://yunu-jeon.github.io/DH-Korean-Diaspora/ns#> .

# ① 컬렉션과 개념체계
ric:col-한-뿌리-다른-땅 a rico:RecordSet ; rico:title "한 뿌리, 다른 땅" .
ric:scheme-life-objects a skos:ConceptScheme ; skos:prefLabel "생활 대상" ; rico:identifier "scheme-life-objects" ;
    rico:isOrWasSubjectOf ric:col-한-뿌리-다른-땅 .
ric:scheme-words a skos:ConceptScheme ; skos:prefLabel "디아스포라 어휘" ; rico:identifier "scheme-words" ;
    rico:isOrWasSubjectOf ric:col-한-뿌리-다른-땅 .
ric:scheme-cultures a skos:ConceptScheme ; skos:prefLabel "문화권" ; rico:identifier "scheme-cultures" ;
    rico:isOrWasSubjectOf ric:col-한-뿌리-다른-땅 .

# ② 측면 — 생활 대상 체계의 최상위 개념이자 장면의 활동 유형
ric:aspect-eat a skos:Concept, rico:ActivityType ;
    skos:prefLabel "먹는 것" ; skos:altLabel "식(食)" ; rico:identifier "dia:aspect=먹는 것" ;
    skos:inScheme ric:scheme-life-objects ; skos:topConceptOf ric:scheme-life-objects ;
    rico:isOrWasSubjectOf ric:col-한-뿌리-다른-땅 .

# ③ 생활 장면 — 표준 Activity + AP Scene, 이름 두 자리, AP 관계 + 그려지는 관계
ric:scene-koryo-babimuri a rico:Activity, dia:Scene ;
    rico:identifier "scene:koryo-babimuri" ;
    dcterms:title "물에 만 밥으로 끼니를 때우던 날들" ;
    rico:name     "물에 만 밥으로 끼니를 때우던 날들" ;
    dcterms:description "일은 많고 먹을 것이 모자랄 때 고려인들은 밥을 물에 말아 서둘러 끼니를 해결했고, 이를 고려인 말로 따로 불렀다. 강제 이주 뒤 생계를 위해 멀리 땅을 빌려 짓는 농사(고본질)가 생기면서 더 자주 먹게 되었고, 지금도 밥상에 자주 오른다." ;
    rico:generalDescription "일은 많고 먹을 것이 모자랄 때 고려인들은 밥을 물에 말아 서둘러 끼니를 해결했고, 이를 고려인 말로 따로 불렀다. 강제 이주 뒤 생계를 위해 멀리 땅을 빌려 짓는 농사(고본질)가 생기면서 더 자주 먹게 되었고, 지금도 밥상에 자주 오른다." ;
    dcterms:subject ric:concept-rice-in-water ;  rico:isRelatedTo ric:concept-rice-in-water ;
    dcterms:spatial ric:place-kazakhstan ;       rico:isAssociatedWithPlace ric:place-kazakhstan ;
    dcterms:spatial ric:group-koryo ;            rico:isRelatedTo ric:group-koryo ;   # 문화권은 장소가 아니다
    dcterms:temporal "1937년 강제 이주 이후 ~ 현재" ;
    dia:aspect "먹는 것" ;                        rico:hasActivityType ric:aspect-eat ;
    dcterms:source ric:ref-kwon2020 ;            dia:citation "kwon2020:108" ;
    rico:isOrWasSubjectOf ric:col-한-뿌리-다른-땅 .

# ④ 생활 대상
ric:concept-rice-in-water a skos:Concept ;
    rico:identifier "concept:rice-in-water" ;
    skos:prefLabel "물에 만 밥" ; skos:definition "밥을 물에 말아 빠르게 먹는 끼니." ;
    dia:aspect "먹는 것" ; skos:broader ric:aspect-eat ; skos:inScheme ric:scheme-life-objects ;
    dcterms:source ric:ref-kwon2020 ; dia:citation "kwon2020:108" ;
    rico:isOrWasSubjectOf ric:col-한-뿌리-다른-땅 .

# ⑤ 어휘 — 표준 rico:Concept(skos:Concept 아님) + AP skosxl:Label
ric:label-babimuri a rico:Concept, skosxl:Label ;
    rico:identifier "label:babimuri" ;
    skosxl:literalForm "바비무리" ; skos:prefLabel "바비무리" ; dcterms:language "ko" ;
    dia:gloss "밥을 물에 말아 먹는 것을 이르는 고려인 말." ;
    rico:generalDescription "밥을 물에 말아 먹는 것을 이르는 고려인 말." ;
    dia:denotes ric:concept-rice-in-water ; rico:isRelatedTo ric:concept-rice-in-water ;
    dcterms:spatial ric:group-koryo ; rico:isRelatedTo ric:group-koryo ;
    dia:sourceLanguage "kor" ; skos:inScheme ric:scheme-words ;
    dcterms:source ric:ref-kwon2020 ; dia:citation "kwon2020:108" ;
    rico:isOrWasSubjectOf ric:col-한-뿌리-다른-땅 .

# ⑥ 문화권 — 표준 rico:Concept + RiC-O DemographicGroup + AP foaf:Group
ric:group-koryo a rico:Concept, rico:DemographicGroup, foaf:Group ;
    rico:identifier "group:koryo" ;
    dcterms:title "고려인" ; skos:prefLabel "고려인" ;
    dcterms:description "19세기 중엽(1863년 무렵) 함북 출신 한인들이 러시아 원동 연해주로 옮겨 가 마을을 이루었다. 1937년 중앙아시아로 강제 이주되었다. 1937년 8월 약 17만 명이 연해주 등지에서 우즈베키스탄·카자흐스탄 등 중앙아시아로 집단 이주되었다. 이들의 말(고려말)은 모국어와 떨어진 언어섬으로 따로 변해 왔고, 러시아어의 영향을 받았다고 연구자는 본다. '고려', '고려말', '고려사람' 같은 명칭은 1920년대에 이미 쓰였다고 한다. 고려말은 함경도 방언에 바탕을 둔 한국어로, 지금은 주로 소수의 노년층이 쓴다. 러시아어 차용어가 매우 많다." ;
    dcterms:spatial ric:place-kazakhstan ; rico:isAssociatedWithPlace ric:place-kazakhstan ;   # 예시용으로 6곳 중 1곳만
    skos:inScheme ric:scheme-cultures ; skos:topConceptOf ric:scheme-cultures ;
    dcterms:source ric:ref-kwon2020 ;    # 예시용으로 3건 중 1건만(실제는 kwak2007·nara2017·ency_koryomal)
    rico:isOrWasSubjectOf ric:col-한-뿌리-다른-땅 .

# ⑦ 장소 — 근사 좌표임을 주기로
ric:place-kazakhstan a rico:Place, dcterms:Location ;
    rico:identifier "place:kazakhstan" ;
    dcterms:title "카자흐스탄" ; rico:name "카자흐스탄" ;
    geo:lat "48.0000" ; geo:long "67.0000" ;
    skos:editorialNote "좌표는 문헌 외 값 — 나라 중심 근사값. 검수 필요" ;
    dia:citation "kwon2020:104" ;
    rico:isOrWasSubjectOf ric:col-한-뿌리-다른-땅 .

# ⑧ 출처 — 기록류라 소속 술어가 다르다
ric:ref-kwon2020 a rico:Record, bibo:AcademicArticle ;
    rico:identifier "kwon2020" ;
    dcterms:title "카자흐스탄 고려인 문화 연구: 음식과 명절을 중심으로" ;
    rico:title    "카자흐스탄 고려인 문화 연구: 음식과 명절을 중심으로" ;
    dcterms:creator "권기배" ; dcterms:date "2020" ; dcterms:isPartOf "『러시아어문학연구논집』 69" ;
    dcterms:accessRights "학교 DB 경유" ;
    rico:isOrWasIncludedIn ric:col-한-뿌리-다른-땅 .
```

---

## 6. 스타터킷에 적재하는 법

원본 §6 그대로입니다. **길 A(컬렉션 화면에서 TTL 올리기)**를 권장합니다 — 컬렉션 이름 칸은 비워 두면 파일 안의
`rico:RecordSet` 이름 「한 뿌리, 다른 땅」이 쓰입니다. 올리기 경로가 `data/ontology.rdf` 에 등재되지 않은 술어
(`dia:`·`skosxl:`·`dcterms:` 등)를 **경고**하는 것은 예상된 일이며 싣는 데는 지장이 없습니다.

함께 나가지 않는 것: 원문 코퍼스(「언어」 화면은 「원문 없음」), 이미지(`foaf:depiction` 없음), 원 사이트의 화면 문안
(`display_text.json`)·큐레이터 해설·장면-어휘 연결표(`sceneLabels`). 마지막 것은 AP 참조(어휘 → 대상 ← 장면)로 다시
계산되는 값이라 관계망에서는 「어휘 — 생활 대상 — 장면」 두 단계로 보입니다.

---

## 7. 한계와 도화 님이 정할 것

**이 Turtle 은 형식만 보증합니다.** 값은 이미 검수한 JSON 에서 그대로 옮겼고(813개 값 대조 누락 0), 새 사실은 만들지 않았습니다.
다만 아래는 *해석이 들어간 대응*이라 검토가 필요합니다.

1. **문화권 = `rico:Concept`+`DemographicGroup`.** 대안은 `rico:CorporateBody`(단체)입니다. 단체로 두면 RiC-O 정의(조직·법적 지위)와
   어긋나고, 개념으로 두면 FOAF 의 Group(행위자)과 결이 달라집니다. 저는 전자의 어긋남이 더 크다고 봤습니다.
2. **장면 = `rico:Activity`.** 문학 속 재현 장면(시 「キムチ」 등)은 실제로 '행해진 일'이 아니라 재현입니다. Activity 로 두되
   주기와 설명 머리말로 재현임을 밝혔습니다.
3. **`rico:isRelatedTo` 를 많이 씁니다(147건).** 스타터킷 쪽 AP 는 활동에 `rico:hasOrHadSubject` 를 쓰지만, RiC-O 1.1 에서 그 술어의
   domain 은 RecordResource 라 저는 쓰지 않았습니다. 화면의 간선 이름이 일반적이 되는 대가가 있습니다.
4. **개념체계·측면이 허브가 됩니다.** 연결 수 상위가 고려인(43)·먹는 것(43)·디아스포라 어휘(34)·생활 대상(34)입니다. `col-` 허브만큼은
   아니지만 관계망 상위 노드 선정에 영향을 줍니다. 측면을 개념으로 만들지 않으면(`dia:aspect` 문자열만) 「먹는 것」 허브는 사라지지만
   주제 화면에서 측면별로 볼 수 없게 됩니다.
5. **AP 밖 보조 속성**을 더했습니다: `rico:identifier`, `rdfs:seeAlso`, `dcterms:language`, `skos:editorialNote`, 화면 이름·설명 술어,
   측면 개념, 개념체계. 모두 *내보내기 층*이며 AP 원문은 바꾸지 않았습니다. 기획안에 「AP → 스타터킷 대응(crosswalk)」으로 적을 수 있습니다.
6. **제외한 것**: 자료 1건(다이아몬드 케이 김치 광고 — 필수값 `rights`·`source` 가 확인 필요라 데이터에 "검수 전 비공개"로 적힘),
   어떤 개체의 근거로도 쓰이지 않은 출처 4건(kimjh2015·nara_mou·han2022·kookminbo_xml).
7. **연표는 빕니다**(§2.5). 채우려면 문헌이 직접 주는 연도를 장면별로 뽑는 검수가 따로 필요합니다.
