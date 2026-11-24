// 자료에게 묻기 — 자연어 질문 → SPARQL → 지식그래프 검색 → 자연어 답
// 페이지에 <div id="ask-app"></div> 가 있을 때만 동작한다(테마 레이아웃이 모든 페이지에 이 파일을 싣는다).
// 기본 변환기는 '규칙'(질문 유형 + 그래프에서 읽은 개체 이름 사전). 이용자가 원하면 LLM(Anthropic 또는 로컬 Ollama)으로 바꿀 수 있다.
(function () {
  'use strict';                                                               // 엄격 모드: 실수로 만든 전역 변수를 막는다
  const root = document.querySelector('#ask-app, .ask-app');                  // 화면을 그릴 자리(HTML 블록이 id 를 지울 수 있어 class 도 본다)
  if (!root) return;                                                          // 이 페이지가 아니면 아무것도 하지 않는다

  // ===== 설정 =====
  const ENDPOINT = root.dataset.endpoint || '/sparql';                        // Omeka Sparql 모듈의 엔드포인트(같은 서버)
  const GRAPH = root.dataset.graph || 'https://yunu-jeon.github.io/DH-Korean-Diaspora/graph/grounding';  // 그라운딩 결과 그래프
  const ITEM = 'https://yunu-jeon.github.io/DH-Korean-Diaspora/item.html?id=';  // 원 아카이브의 개별 자원 주소
  const PREFIXES = [                                                          // 모든 질의 앞에 붙는 접두어
    'PREFIX dcterms: <http://purl.org/dc/terms/>',
    'PREFIX dia: <https://yunu-jeon.github.io/DH-Korean-Diaspora/ns#>',
    'PREFIX foaf: <http://xmlns.com/foaf/0.1/>',
    'PREFIX rico: <https://www.ica.org/standards/RiC/ontology#>',
    'PREFIX skos: <http://www.w3.org/2004/02/skos/core#>',
    'PREFIX skosxl: <http://www.w3.org/2008/05/skos-xl#>',
    'PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>',
  ].join('\n') + '\n';
  const FROM = 'FROM <' + GRAPH + '>';                                        // 그라운딩 그래프만 검색한다
  const ASPECTS = [                                                           // 측면 값(AP의 dia:aspect)과 질문에 나올 만한 말
    { value: '먹는 것', label: '식(食)', words: ['먹는 것', '먹는', '먹었', '먹던', '음식', '식생활', '밥상', '요리', '식(食)'] },
    { value: '부르는 것', label: '호(呼)', words: ['부르는 것', '호칭', '언어', '이름', '말이 섞', '호(呼)'] },
    { value: '일하는 것', label: '사(事)', words: ['일하는 것', '일하는', '일했', '노동', '생업', '직업', '농사', '가게', '사(事)'] },
    { value: '배우는 것', label: '학(學)', words: ['배우는 것', '배우는', '교육', '학교', '배움', '교과서', '학(學)'] },
  ];
  const LANGS = [                                                             // 기원 언어(ISO 639-3)와 질문에 나올 말
    { code: 'rus', name: '러시아어', words: ['러시아어', '러시아 말', '러시아'] },
    { code: 'jpn', name: '일본어', words: ['일본어', '일본 말'] },
    { code: 'eng', name: '영어', words: ['영어'] },
    { code: 'kor', name: '한국어', words: ['한국어', '우리말', '조선말'] },
  ];
  const GROUP_WORDS = {                                                       // 문화권 이름 밖의 다른 표현
    'group:koryo': ['고려인', '고려 사람', '고려사람', '고려말', '중앙아시아', '카자흐', '우즈베크'],
    'group:zainichi': ['재일조선인', '재일 조선인', '재일한국인', '재일동포', '재일 코리안', '재일코리안', '자이니치', '재일', '일본의 한인', '일본에 사는'],
    'group:hawaii': ['하와이 한인', '하와이', '미주 한인'],
  };
  const EXAMPLES = [                                                          // 예시 질문(눌러서 바로 물어볼 수 있다)
    '고려인은 김치를 뭐라고 불렀어?',
    '바비무리가 무슨 뜻이야?',
    '하와이 한인의 먹는 것 장면을 보여줘',
    '러시아어에서 온 고려인 말은?',
    '문화권별로 측면마다 장면이 몇 개야?',
    '같은 대상을 문화권마다 어떻게 불러?',
    '우슈토베에서는 무슨 일이 있었어?',
    '권기배 논문이 근거인 자료는?',
    '호르몬의 어원은?',
  ];

  // ===== 작은 도구들 =====
  const $ = (tag, attrs, kids) => {                                           // 요소 만들기: $('p', {class:'x'}, ['글'])
    const el = document.createElement(tag);                                   // 태그 생성
    Object.entries(attrs || {}).forEach(([k, v]) => {                         // 속성 붙이기
      if (k === 'text') el.textContent = v;                                   // text: 글자(HTML로 해석하지 않음)
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);        // onclick 등: 이벤트
      else if (v !== false && v != null) el.setAttribute(k, v === true ? '' : v);  // 나머지: 일반 속성
    });
    (kids || []).forEach((c) => c != null && el.append(c));                   // 자식 붙이기(글자 또는 요소)
    return el;                                                                // 완성된 요소
  };
  const squash = (s) => String(s).toLowerCase().replace(/[\s·\-–—_'"‘’“”「」『』()（）\[\]]/g, '');  // 비교용: 공백·문장부호 제거
  const esc = (s) => String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"');   // SPARQL 문자열 안에 넣을 때 따옴표 처리
  const reEsc = (s) => esc(String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));  // REGEX 안에 넣을 때 특수문자 처리
  const uniq = (a) => [...new Set(a.filter((x) => x != null && x !== ''))];  // 중복·빈값 제거
  const local = (iri) => String(iri).split(/[\/#]/).pop();                    // IRI 끝 이름
  function josa(word, pair) {                                                 // 받침에 맞는 조사: josa('고려인','은는') → '고려인은'
    const w = String(word);                                                   // 앞말
    const code = w.replace(/[\s’'」』)\]]+$/, '').slice(-1).charCodeAt(0) - 0xac00;  // 마지막 글자(따옴표·괄호 무시)
    if (code < 0 || code > 11171) return w + (pair === '이라고' ? '(이)라고' : pair === '으로로' ? '(으)로' : pair[0] + '(' + pair[1] + ')');  // 한글이 아니면 둘 다 보인다
    const batchim = code % 28;                                                // 받침 번호(0 = 받침 없음)
    if (pair === '으로로') return w + (batchim && batchim !== 8 ? '으로' : '로');  // ㄹ 받침은 '로'
    if (pair === '이라고') return w + (batchim ? '이라고' : '라고');          // 받침 있으면 '이라고'
    return w + (batchim ? pair[0] : pair[1]);                                 // 받침 있으면 앞, 없으면 뒤
  }

  async function sparql(query) {                                              // 엔드포인트에 질의를 보내고 표로 받는다
    const res = await fetch(ENDPOINT + '?query=' + encodeURIComponent(query), {  // GET 으로 보낸다(모듈이 받는 방식)
      headers: { Accept: 'application/sparql-results+json' },                 // JSON 결과를 달라고 한다
    });
    const text = await res.text();                                            // 응답 글자
    let json;                                                                 // 해석한 JSON
    try { json = JSON.parse(text); } catch (e) {                              // JSON 이 아니면(오류 페이지 등)
      throw new Error('SPARQL 오류(' + res.status + '): ' + text.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').slice(0, 200));
    }
    const vars = json.head.vars;                                              // 열 이름
    const rows = json.results.bindings.map((b) => {                           // 행마다
      const r = {};                                                           // 열 이름 → 값
      vars.forEach((v) => { if (b[v]) r[v] = b[v].value; });                  // 비어 있는 칸은 넣지 않는다
      return r;
    });
    return { vars, rows };                                                    // 열과 행
  }

  function merge(rows, key) {                                                 // OPTIONAL 때문에 늘어난 행을 개체별로 합친다
    const map = new Map();                                                    // key 값 → 합친 행
    rows.forEach((r) => {
      const k = r[key] || JSON.stringify(r);                                  // 합칠 기준
      if (!map.has(k)) map.set(k, {});                                        // 처음 보면 빈 묶음
      const m = map.get(k);                                                   // 이 개체의 묶음
      Object.entries(r).forEach(([c, v]) => { (m[c] = m[c] || new Set()).add(v); });  // 열마다 값 모으기(중복 없이)
    });
    return [...map.values()].map((m) => Object.fromEntries(Object.entries(m).map(([c, s]) => [c, [...s]])));  // 집합 → 배열
  }

  // ===== 개체 이름 사전(그래프에서 읽는다 — 데이터가 늘면 저절로 늘어난다) =====
  const LEX = { groups: [], concepts: [], labels: [], places: [], refs: [] };  // 종류별 목록
  const PLACE_STOP = /^(하와이|섬|오아후|지역|남쪽|농장|인근|캠프|한인|패전|직후|조선인|암시장|러시아|원동|콜호즈|등|포시에트)$/;  // 지명 낱말로 쓰지 않을 말
  function aliases(name, words) {                                             // 이름 하나에서 질문에 나올 만한 표기들을 만든다
    const base = String(name).trim();                                         // 원래 이름
    const parts = base.split(/[()（）,—–\/]/).map((s) => s.trim());           // 괄호·구분자로 나눈 조각('·'로는 나누지 않음: '고기·양배추'의 '고기' 오인 방지)
    const noParen = base.replace(/\s*[(（][^)）]*[)）]/g, '').trim();         // 괄호 뺀 이름
    const toks = words ? base.split(/[\s()（）,·—–\/'‘’]+/).filter((t) => !PLACE_STOP.test(t)) : [];  // 장소: 낱말 하나씩도(예: '코할라')
    return uniq([base, noParen, ...parts, ...toks]).filter((s) => squash(s).length >= 2);  // 두 글자 이상만
  }
  async function loadLexicon() {                                              // 처음 한 번 사전을 읽는다
    const q = (body) => sparql(PREFIXES + body);                              // 접두어 붙여 실행
    const [g, c, l, p, r] = await Promise.all([                               // 다섯 질의를 동시에
      q(`SELECT ?x ?t ?id ${FROM} WHERE { ?x a foaf:Group ; dcterms:title ?t ; rico:identifier ?id }`),
      q(`SELECT ?x ?t ?id ${FROM} WHERE { ?x a skos:Concept ; skos:prefLabel ?t ; dia:aspect ?a . OPTIONAL { ?x rico:identifier ?id } }`),
      q(`SELECT ?x ?t ?v ?id ${FROM} WHERE { ?x skosxl:literalForm ?t ; rico:identifier ?id . OPTIONAL { ?x dia:variantForm ?v } }`),
      q(`SELECT ?x ?t ?id ${FROM} WHERE { ?x a dcterms:Location ; dcterms:title ?t ; rico:identifier ?id }`),
      q(`SELECT ?x ?id ?t ?cr ?d ${FROM} WHERE { ?x a rico:Record ; rico:identifier ?id ; dcterms:title ?t . OPTIONAL { ?x dcterms:creator ?cr } OPTIONAL { ?x dcterms:date ?d } }`),
    ]);
    LEX.groups = g.rows.map((x) => ({ iri: x.x, name: x.t, id: x.id, alias: uniq([...aliases(x.t), ...(GROUP_WORDS[x.id] || [])]) }));
    LEX.concepts = merge(c.rows, 'x').map((x) => ({ iri: x.x[0], name: x.t[0], alias: aliases(x.t[0]) }));
    LEX.labels = merge(l.rows, 'x').map((x) => ({ iri: x.x[0], name: x.t[0], id: x.id[0], alias: uniq([...aliases(x.t[0]), ...(x.v || [])]) }));
    LEX.places = p.rows.map((x) => ({ iri: x.x, name: x.t, alias: aliases(x.t, true).filter((a) => !/^(하와이|하와이 섬|오아후 섬)$/.test(a)) }));  // '하와이'는 문화권으로 읽는다
    LEX.refs = merge(r.rows, 'x').map((x) => {                                // 출처: ID, 저자, 연도
      const author = (x.cr || [''])[0].replace(/\s*\(.*\)$/, '').replace(/\s*편$/, '');  // 저자 이름만
      return { iri: x.x[0], id: x.id[0], name: x.t[0], author, year: (x.d || [''])[0].slice(0, 4),
               alias: uniq([x.id[0], author.length >= 2 ? author : null]) };
    });
  }
  function cite(c) {                                                          // "kwon2020:108" → "권기배(2020) 108쪽"
    const [id, page] = String(c).split(/:(.+)/);                              // 출처 ID 와 쪽
    const ref = LEX.refs.find((r) => r.id === id);                            // 사전에서 출처 찾기
    const who = ref ? `${ref.author}${ref.year ? '(' + ref.year + ')' : ''}` : id;  // 저자(연도)
    return /^\d+$/.test(page || '') ? `${who} ${page}쪽` : `${who} ${page || ''}`.trim();  // 쪽수면 '쪽', 웹 문헌은 절 이름
  }

  // ===== 질문 이해(규칙) =====
  function findIn(list, qs) {                                                 // 질문 속에 나온 개체 찾기(긴 표기 우선)
    const hits = [];                                                          // 찾은 것
    list.forEach((e) => {
      const a = e.alias.filter((x) => qs.includes(squash(x))).sort((x, y) => squash(y).length - squash(x).length)[0];  // 가장 긴 표기
      if (a) hits.push({ ...e, matched: a });                                 // 찾은 표기와 함께
    });
    hits.sort((x, y) => squash(y.matched).length - squash(x.matched).length); // 긴 것부터
    return hits.filter((h, i) => !hits.slice(0, i).some((o) => squash(o.matched).includes(squash(h.matched)) && o.iri !== h.iri));  // 더 긴 표기 안에 든 것은 버림
  }
  const has = (qs, words) => words.some((w) => qs.includes(squash(w)));      // 질문에 낱말이 있나

  function understand(text) {                                                 // 질문 → 유형 + 개체
    const qs = squash(text);                                                  // 비교용 질문
    const ent = {
      group: findIn(LEX.groups, qs)[0],                                       // 문화권
      aspect: ASPECTS.find((a) => has(qs, a.words)),                          // 측면
      lang: LANGS.find((l) => has(qs, l.words) && has(qs, ['에서 온', '온말', '차용', '빌려', '들어온', '기원', '어에서', '출신'])),  // 기원 언어(유래 표현과 함께일 때만)
      concepts: findIn(LEX.concepts, qs),                                     // 생활 대상
      labels: findIn(LEX.labels, qs),                                         // 어휘
      place: findIn(LEX.places, qs)[0],                                       // 장소
      ref: findIn(LEX.refs, qs)[0],                                           // 출처
    };
    if (ent.group && ent.place && squash(ent.group.matched).includes(squash(ent.place.matched))) ent.place = null;  // 문화권 이름 속 지명은 장소로 보지 않음
    const meaningAsked = has(qs, ['뜻', '의미', '무슨 말']);                  // 뜻을 분명히 물었나
    if (!meaningAsked) ent.labels = ent.labels.filter((l) => !ent.concepts.some((c) => squash(c.matched) === squash(l.matched)));  // '김치'처럼 대상 이름과 같은 표기는 대상으로 읽는다
    if (ent.group && !meaningAsked) ent.labels = ent.labels.filter((l) => !squash(ent.group.matched).includes(squash(l.matched)));  // '재일조선인' 같은 호칭 어휘보다 문화권으로 읽는다
    const ask = {
      count: has(qs, ['몇 개', '몇개', '몇 편', '개수', '얼마나 많', '몇 가지', '수는', '통계']),
      naming: has(qs, ['뭐라고', '무엇이라고', '어떻게 불', '어떻게 부르', '부르는 말', '부르던', '불렀', '이름은', '라고 해', '표기']),
      meaning: has(qs, ['뜻', '의미', '무슨 말', '뭐야', '무엇인가', '뭔가', '뭐지', '무엇이야', '이란', '란 무엇']),
      etym: has(qs, ['어원', '유래', '어디서 온', '왜 그렇게']),
      cross: has(qs, ['문화권마다', '여러 문화권', '같은 대상', '공통', '한 뿌리', '다른 이름']),
      words: has(qs, ['말', '어휘', '단어', '낱말']),
      scenes: has(qs, ['장면', '이야기', '생활', '보여', '무슨 일', '있었', '어떤 일', '어떻게 살']),
    };
    let intent;                                                               // 질문 유형(위에서부터 먼저 맞는 것)
    if (ask.count) intent = ask.words && !ask.scenes ? 'countWords' : 'countScenes';
    else if (ask.cross) intent = 'oneRoot';
    else if (ent.ref) intent = 'source';
    else if (ent.lang) intent = 'origin';
    else if (ask.etym) intent = 'etymology';
    else if (ent.labels.length && !(ask.naming && ent.concepts.length && !ent.labels.some((l) => squash(l.matched).length > Math.max(...ent.concepts.map((c) => squash(c.matched).length))))) intent = 'meaning';
    else if (ent.concepts.length && (ask.naming || ask.words || ent.group)) intent = 'naming';
    else if (ent.place) intent = 'scenes';
    else if (ent.concepts.length) intent = 'scenes';
    else if (ent.group || ent.aspect || ask.scenes) intent = 'scenes';
    else intent = 'keyword';
    if (intent === 'meaning' && ask.naming && ent.concepts.length && !ent.labels.length) intent = 'naming';
    return { text, intent, ent, keyword: intent === 'keyword' ? keywordOf(text) : null };
  }
  function keywordOf(text) {                                                  // 아무 개체도 못 찾았을 때 검색어 하나 뽑기
    const stop = /^(무엇|뭐|어떤|어떻게|누가|언제|어디|왜|보여|알려|찾아|있어|있나|있었|관련|대해|대한|자료|정보|주세요|줘)/;  // 질문 말
    const toks = text.split(/[\s?!.,]+/).map((t) => t.replace(/(이란|란|이야|야|은|는|이|가|을|를|의|에서|에게|에|으로|로|와|과|도|만|까지|부터|처럼|한테|이랑|랑)$/, ''))  // 조사 떼기
      .filter((t) => t.length >= 2 && !stop.test(t));                         // 두 글자 이상, 질문 말 아닌 것
    return toks.sort((a, b) => b.length - a.length)[0] || text.trim();        // 가장 긴 낱말
  }

  // ===== 질문 유형별 SPARQL + 답 만들기 =====
  // ARC2 저장소의 제약: 필수 패턴은 4개까지(나머지는 OPTIONAL), REGEX 에는 늘 "i".
  const groupFilter = (v, g) => (g ? ` FILTER(?${v} = <${g.iri}>)` : '');    // 문화권 조건
  const ors = (v, list) => list.map((e) => `?${v} = <${e.iri}>`).join(' || ');  // 여러 개체 중 하나
  const linkTo = (id) => (id ? ITEM + encodeURIComponent(id) : null);         // 원 아카이브 링크

  const BUILD = {
    naming({ ent }) {                                                         // 생활 대상을 문화권마다 뭐라고 부르나
      const c = ent.concepts;
      return {
        title: '대상을 부르는 말',
        query: `SELECT ?l ?obj ?form ?group ?gloss ?var ?cite ?id ${FROM} WHERE {
  ?l dia:denotes ?c ; skosxl:literalForm ?form ; dcterms:spatial ?g .
  ?g dcterms:title ?group .
  OPTIONAL { ?c skos:prefLabel ?obj }
  OPTIONAL { ?l dia:gloss ?gloss }
  OPTIONAL { ?l dia:variantForm ?var }
  OPTIONAL { ?l dia:citation ?cite }
  OPTIONAL { ?l rico:identifier ?id }
  FILTER(${ors('c', c)})${groupFilter('g', ent.group)}
} ORDER BY ?group ?form`,
        answer(rows) {
          const L = merge(rows, 'l');                                         // 말 하나에 한 묶음
          if (!L.length) return { text: `${ent.group ? josa(ent.group.name, '이가') + ' ' : ''}${josa(c.map((x) => `‘${x.name}’`).join(', '), '을를')} 부르던 말은 그래프에 기록되어 있지 않습니다.`, items: [] };
          const byGroup = {};                                                 // 문화권별로 모으기
          L.forEach((x) => (byGroup[x.group[0]] = byGroup[x.group[0]] || []).push(x));
          const parts = Object.entries(byGroup).map(([g, xs]) => `${josa(g, '은는')} ${josa(xs.map((x) => `‘${x.form[0]}’`).join(', '), '이라고')}`);
          return {
            text: `${josa(uniq(L.flatMap((x) => x.obj || [])).map((o) => `‘${o}’`).join(', ') || '이 대상', '을를')} ${parts.join(', ')} 불렀습니다.`,
            items: L.map((x) => ({ head: x.form[0], sub: x.group.join(', '), body: x.gloss ? x.gloss[0] : '', extra: x.var ? '이표기: ' + x.var.join(', ') : '', cites: x.cite || [], link: linkTo(x.id && x.id[0]) })),
          };
        },
      };
    },
    meaning({ ent }) {                                                        // 말의 뜻
      const L = ent.labels;
      return {
        title: '말의 뜻',
        query: `SELECT ?l ?form ?gloss ?group ?obj ?ety ?lang ?var ?cite ?id ${FROM} WHERE {
  ?l skosxl:literalForm ?form ; dia:gloss ?gloss .
  OPTIONAL { ?l dcterms:spatial ?g . ?g dcterms:title ?group }
  OPTIONAL { ?l dia:denotes ?c . ?c skos:prefLabel ?obj }
  OPTIONAL { ?l dia:etymologyNote ?ety }
  OPTIONAL { ?l dia:sourceLanguage ?lang }
  OPTIONAL { ?l dia:variantForm ?var }
  OPTIONAL { ?l dia:citation ?cite }
  OPTIONAL { ?l rico:identifier ?id }
  FILTER(${ors('l', L)})
}`,
        answer(rows) {
          const X = merge(rows, 'l');
          if (!X.length) return { text: '그 말은 그래프에 없습니다.', items: [] };
          const s = X.map((x) => {
            const lang = x.lang ? LANGS.find((l) => l.code === x.lang[0]) : null;
            return `${josa(`‘${x.form[0]}’`, '은는')} ${(x.group || ['어느 문화권']).join('·')} 사이에서 쓰인 말로, 뜻은 “${x.gloss[0].replace(/\.$/, '')}”입니다.` +
              (x.obj ? ` 가리키는 생활 대상은 ‘${x.obj[0]}’입니다.` : '') + (lang ? (lang.code === 'kor' ? ' 기원 언어는 한국어로 기록되어 있습니다.' : ` ${lang.name}에서 온 말로 기록되어 있습니다.`) : '');
          });
          return {
            text: s.join(' '),
            items: X.map((x) => ({ head: x.form[0], sub: (x.group || []).join(', '), body: x.gloss[0], extra: [x.var ? '이표기: ' + x.var.join(', ') : '', x.ety ? '어원(연구자 해석): ' + x.ety[0] : ''].filter(Boolean).join(' · '), cites: x.cite || [], link: linkTo(x.id && x.id[0]) })),
          };
        },
      };
    },
    scenes({ ent }) {                                                         // 문화권·측면·장소·대상으로 장면 찾기
      const req = [];                                                         // 추가 필수 패턴(2개까지)
      if (ent.place) req.push(`?s dcterms:spatial <${ent.place.iri}> .`);
      if (ent.concepts.length && req.length < 2) req.push(`?s dcterms:subject ?c .`);
      if (ent.group && req.length < 2) req.push(`?s dcterms:spatial <${ent.group.iri}> .`);
      const filters = [];
      if (ent.aspect) filters.push(`?aspect = "${ent.aspect.value}"`);
      if (ent.concepts.length) filters.push(`(${ors('c', ent.concepts)})`);
      const what = [ent.group && ent.group.name, ent.place && ent.place.name, ent.aspect && `‘${ent.aspect.value}’`, ent.concepts.length && ent.concepts.map((c) => `‘${c.name}’`).join('·')].filter(Boolean).join(' · ');
      return {
        title: '생활 장면',
        query: `SELECT ?s ?title ?aspect ?group ?temporal ?desc ?cite ?id ${FROM} WHERE {
  ?s dcterms:title ?title ; dia:aspect ?aspect .
  ${req.join('\n  ')}
  OPTIONAL { ?s dcterms:spatial ?g . ?g a foaf:Group ; dcterms:title ?group }
  OPTIONAL { ?s dcterms:temporal ?temporal }
  OPTIONAL { ?s dcterms:description ?desc }
  OPTIONAL { ?s dia:citation ?cite }
  OPTIONAL { ?s rico:identifier ?id }${filters.length ? '\n  FILTER(' + filters.join(' && ') + ')' : ''}
} ORDER BY ?group ?aspect ?title`,
        answer(rows) {
          const S = merge(rows, 's');
          if (!S.length) return { text: `${what || '조건'}에 맞는 생활 장면은 그래프에 없습니다.`, items: [] };
          const top = S.slice(0, 3).map((x) => `「${x.title[0]}」`).join(', ');
          return {
            text: `${what ? what + '에 해당하는 ' : ''}생활 장면은 ${S.length}개입니다. 예를 들어 ${S.length > 3 ? top + ' 등이' : josa(top, '이가')} 있습니다.`,
            items: S.map((x) => ({ head: x.title[0], sub: [(x.group || []).join(', '), x.aspect.join(', '), (x.temporal || [])[0]].filter(Boolean).join(' · '), body: firstSentences(x.desc && x.desc[0], 2), cites: x.cite || [], link: linkTo(x.id && x.id[0]) })),
          };
        },
      };
    },
    countScenes({ ent }) {                                                    // 문화권 × 측면 장면 수
      const f = [ent.group && `?g = <${ent.group.iri}>`, ent.aspect && `?aspect = "${ent.aspect.value}"`].filter(Boolean);
      return {
        title: '장면 수',
        query: `SELECT ?group ?aspect (COUNT(?s) AS ?n) ${FROM} WHERE {
  ?s dia:aspect ?aspect ; dcterms:spatial ?g .
  ?g a foaf:Group ; dcterms:title ?group .${f.length ? '\n  FILTER(' + f.join(' && ') + ')' : ''}
} GROUP BY ?group ?aspect ORDER BY ?group ?aspect`,
        answer(rows) {
          if (!rows.length) return { text: '세어 볼 장면이 없습니다.', items: [] };
          const total = rows.reduce((a, r) => a + Number(r.n), 0);
          const byG = {};
          rows.forEach((r) => (byG[r.group] = byG[r.group] || []).push(`${r.aspect} ${r.n}개`));
          return { text: `모두 ${total}개 장면입니다. ` + Object.entries(byG).map(([g, xs]) => `${g}: ${xs.join(', ')}`).join('. ') + '.', items: [] };
        },
      };
    },
    countWords({ ent }) {                                                     // 문화권별 어휘 수
      return {
        title: '어휘 수',
        query: `SELECT ?group (COUNT(?l) AS ?n) ${FROM} WHERE {
  ?l dia:gloss ?x ; dcterms:spatial ?g .
  ?g a foaf:Group ; dcterms:title ?group .${ent.group ? `\n  FILTER(?g = <${ent.group.iri}>)` : ''}
} GROUP BY ?group ORDER BY ?group`,
        answer(rows) {
          if (!rows.length) return { text: '세어 볼 어휘가 없습니다.', items: [] };
          return { text: '기록된 어휘는 ' + rows.map((r) => `${r.group} ${r.n}개`).join(', ') + '입니다.' + (rows.length > 1 ? ' 두 문화권에서 함께 쓰인 말은 양쪽에 모두 셉니다.' : ''), items: [] };
        },
      };
    },
    origin({ ent }) {                                                         // 다른 언어에서 들어온 말
      const L = ent.lang;
      return {
        title: `${L.name}에서 온 말`,
        query: `SELECT ?l ?form ?gloss ?group ?ety ?cite ?id ${FROM} WHERE {
  ?l dia:sourceLanguage "${L.code}" ; skosxl:literalForm ?form ; dia:gloss ?gloss ; dcterms:spatial ?g .
  OPTIONAL { ?g dcterms:title ?group }
  OPTIONAL { ?l dia:etymologyNote ?ety }
  OPTIONAL { ?l dia:citation ?cite }
  OPTIONAL { ?l rico:identifier ?id }${groupFilter('g', ent.group)}
} ORDER BY ?group ?form`,
        answer(rows) {
          const X = merge(rows, 'l');
          if (!X.length) return { text: `${ent.group ? ent.group.name + '의 ' : ''}${L.name}에서 온 말은 그래프에 없습니다.`, items: [] };
          return {
            text: `${ent.group ? ent.group.name + '의 말 가운데 ' : ''}${L.name}에서 온 말은 ${X.length}개입니다: ${X.map((x) => `‘${x.form[0]}’(${x.gloss[0].replace(/\.$/, '').split(/[.。]/)[0]})`).join(', ')}.`,
            items: X.map((x) => ({ head: x.form[0], sub: (x.group || []).join(', '), body: x.gloss[0], extra: x.ety ? '어원(연구자 해석): ' + x.ety[0] : '', cites: x.cite || [], link: linkTo(x.id && x.id[0]) })),
          };
        },
      };
    },
    etymology({ ent }) {                                                      // 어원 설명(연구자 해석)
      const f = [ent.labels.length && `(${ors('l', ent.labels)})`, ent.group && `?g = <${ent.group.iri}>`].filter(Boolean);
      return {
        title: '어원(연구자 해석)',
        query: `SELECT ?l ?form ?ety ?group ?cite ?id ${FROM} WHERE {
  ?l skosxl:literalForm ?form ; dia:etymologyNote ?ety ; dcterms:spatial ?g .
  ?g dcterms:title ?group .
  OPTIONAL { ?l dia:citation ?cite }
  OPTIONAL { ?l rico:identifier ?id }${f.length ? '\n  FILTER(' + f.join(' && ') + ')' : ''}
} ORDER BY ?group ?form`,
        answer(rows) {
          const X = merge(rows, 'l');
          if (!X.length) return { text: '그 말에는 어원 설명이 기록되어 있지 않습니다.', items: [] };
          return {
            text: X.length === 1 ? `‘${X[0].form[0]}’의 어원에 대해서는 이렇게 기록되어 있습니다. ${X[0].ety[0]} 이것은 문헌이 보고한 사실이 아니라 연구자의 해석입니다.`
              : `어원 설명이 있는 말은 ${X.length}개입니다. 모두 연구자의 해석으로 기록된 값입니다.`,
            items: X.map((x) => ({ head: x.form[0], sub: x.group.join(', '), body: x.ety[0], cites: x.cite || [], link: linkTo(x.id && x.id[0]) })),
          };
        },
      };
    },
    oneRoot({ ent }) {                                                        // 같은 대상을 문화권마다 어떻게 부르나
      return {
        title: '한 뿌리, 다른 이름',
        query: `SELECT ?c ?obj ?group ?form ${FROM} WHERE {
  ?l dia:denotes ?c ; skosxl:literalForm ?form ; dcterms:spatial ?g .
  ?g dcterms:title ?group .
  OPTIONAL { ?c skos:prefLabel ?obj }${ent.concepts.length ? `\n  FILTER(${ors('c', ent.concepts)})` : ''}
} ORDER BY ?obj ?group ?form`,
        answer(rows) {
          const C = merge(rows, 'c');
          if (!C.length) return { text: '대상과 이어진 말이 없습니다.', items: [] };
          const multi = C.filter((x) => x.group.length > 1);
          return {
            text: `말과 이어진 생활 대상은 ${C.length}개이고, 그중 ${multi.length}개는 두 문화권 이상에서 각기 다른 말로 불렸습니다` +
              (multi.length ? `: ${multi.map((x) => `‘${x.obj[0]}’`).join(', ')}.` : '.'),
            items: C.sort((a, b) => b.group.length - a.group.length).map((x) => ({ head: x.obj[0], sub: x.group.join(', '), body: x.form.map((f) => `‘${f}’`).join(', '), cites: [] })),
          };
        },
      };
    },
    source({ ent }) {                                                         // 한 문헌이 근거가 된 자원
      const R = ent.ref;
      return {
        title: '이 문헌이 근거인 자원',
        query: `SELECT ?x ?id ?title ?form ?name ?cite ${FROM} WHERE {
  ?x dcterms:source <${R.iri}> ; rico:identifier ?id .
  OPTIONAL { ?x dcterms:title ?title }
  OPTIONAL { ?x skosxl:literalForm ?form }
  OPTIONAL { ?x skos:prefLabel ?name }
  OPTIONAL { ?x dia:citation ?cite FILTER(REGEX(?cite, "^${reEsc(R.id)}:", "i")) }
} ORDER BY ?id`,
        answer(rows) {
          const X = merge(rows, 'x');
          if (!X.length) return { text: `${josa(`${R.author}(${R.year})`, '을를')} 근거로 한 자원은 없습니다.`, items: [] };
          const kind = (id) => ({ scene: '장면', label: '어휘', concept: '생활 대상', group: '문화권', place: '장소' })[String(id).split(':')[0]] || '자원';
          const counts = {};
          X.forEach((x) => (counts[kind(x.id[0])] = (counts[kind(x.id[0])] || 0) + 1));
          return {
            text: `${R.author}(${R.year}) ${josa(`「${R.name}」`, '을를')} 근거로 한 자원은 ${X.length}개입니다(${Object.entries(counts).map(([k, n]) => `${k} ${n}`).join(', ')}).`,
            items: X.map((x) => ({ head: (x.title || x.form || x.name || x.id)[0], sub: kind(x.id[0]), body: '', cites: x.cite || [], link: linkTo(x.id[0]) })),
          };
        },
      };
    },
    keyword({ keyword }) {                                                    // 어느 유형에도 안 맞을 때: 낱말 검색
      return {
        title: `‘${keyword}’ 낱말 검색`,
        query: `SELECT ?x ?id ?p ?text ${FROM} WHERE {
  ?x rico:identifier ?id ; ?p ?text .
  FILTER(isLiteral(?text) && REGEX(?text, "${reEsc(keyword)}", "i"))
} ORDER BY ?id LIMIT 80`,
        answer(rows) {
          const X = merge(rows, 'x').filter((x) => !String(x.id[0]).startsWith('dia:aspect'));
          if (!X.length) return { text: `${josa(`‘${keyword}’`, '이가')} 들어간 자원은 그래프에 없습니다. 다른 낱말로 물어 보세요.`, items: [] };
          return {
            text: `질문 유형을 알아보지 못해 ${josa(`‘${keyword}’`, '이가')} 들어간 자원을 찾았습니다. 모두 ${X.length}개입니다.`,
            items: X.map((x) => ({ head: x.id[0], sub: x.p.map(local).join(', '), body: snippet(x.text, keyword), cites: [], link: linkTo(x.id[0]) })),
          };
        },
      };
    },
  };
  function firstSentences(s, n) {                                             // 설명에서 앞의 몇 문장만
    if (!s) return '';
    const parts = s.match(/[^.!?。]+[.!?。]?/g) || [s];
    return parts.slice(0, n).join('').trim();
  }
  function snippet(texts, kw) {                                               // 검색어 둘레의 글만 보여 주기
    const t = texts.find((x) => x.toLowerCase().includes(kw.toLowerCase())) || texts[0];
    const i = t.toLowerCase().indexOf(kw.toLowerCase());
    return (i > 40 ? '…' : '') + t.slice(Math.max(0, i - 40), i + 80) + (t.length > i + 80 ? '…' : '');
  }

  // ===== LLM(선택) =====
  const store = {                                                             // 설정은 이 브라우저에만 저장(서버로 보내지 않음)
    get(k, d) { try { return localStorage.getItem('ask.' + k) ?? d; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem('ask.' + k, v); } catch (e) { /* 저장 못 해도 동작은 한다 */ } },
  };
  const SCHEMA = `그래프 ${GRAPH} 의 구조(한인 디아스포라 생활문화·어휘 아카이브):
- 생활 장면 dia:Scene: dcterms:title, dcterms:description, dia:aspect(값: "먹는 것" "부르는 것" "일하는 것" "배우는 것"), dcterms:subject → 생활 대상, dcterms:spatial → 문화권 또는 장소, dcterms:temporal(서술형 문자열), dcterms:source → 출처, dia:citation("출처ID:쪽"), rico:identifier
- 생활 대상 skos:Concept: skos:prefLabel, skos:definition, dia:aspect
- 어휘 skosxl:Label: skosxl:literalForm, dia:variantForm, dia:gloss(뜻), dia:denotes → 생활 대상, dcterms:spatial → 문화권, dia:sourceLanguage("rus" "jpn" "eng" "kor"), dia:etymologyNote, dia:citation, rico:identifier
- 장소 dcterms:Location: dcterms:title, dcterms:isPartOf → 장소
- 문화권 foaf:Group: dcterms:title("고려인" "재일조선인" "하와이 한인"), dcterms:description, dcterms:spatial → 장소
- 출처 rico:Record: dcterms:title, dcterms:creator, dcterms:date, rico:identifier(예: kwon2020)
규칙: SELECT 만. 반드시 "${FROM}" 을 WHERE 앞에 쓴다. 이 저장소(ARC2)는 필수 트리플 패턴이 5개 이상이면 실패하므로 4개까지만 쓰고 나머지는 OPTIONAL 로 감싼다. REGEX 에는 늘 "i" 옵션. 접두어 선언은 쓰지 않는다(자동으로 붙음): dcterms dia foaf rico skos skosxl rdf. 결과에 rico:identifier 를 ?id 로, 근거가 있으면 dia:citation 을 ?cite 로 넣는다.`;

  async function llm(system, user, wantJson) {                                // 선택한 LLM 에 한 번 묻는다
    const provider = store.get('provider', 'anthropic');
    if (provider === 'ollama') {                                              // 로컬 Ollama(키 필요 없음)
      const res = await fetch(store.get('ollamaUrl', 'http://localhost:11434') + '/api/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: store.get('ollamaModel', 'qwen2.5:7b'), stream: false, format: wantJson ? 'json' : undefined,
          messages: [{ role: 'system', content: system }, { role: 'user', content: user }] }),
      });
      if (!res.ok) throw new Error('Ollama 오류 ' + res.status);
      return (await res.json()).message.content;
    }
    const key = store.get('anthropicKey', '');                                // Anthropic: 이용자가 넣은 키
    if (!key) throw new Error('LLM 설정에서 Anthropic API 키를 넣어 주세요.');
    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-api-key': key, 'anthropic-version': '2023-06-01',
                 'anthropic-dangerous-direct-browser-access': 'true' },      // 브라우저에서 직접 부를 때 필요한 머리말
      body: JSON.stringify({ model: store.get('anthropicModel', 'claude-haiku-5-5'), max_tokens: 1200, system,
                             messages: [{ role: 'user', content: user }] }),
    });
    const j = await res.json();
    if (!res.ok) throw new Error('Anthropic 오류 ' + res.status + ': ' + ((j.error && j.error.message) || ''));
    return j.content.map((c) => c.text || '').join('');
  }
  function safeSelect(q) {                                                    // LLM 이 쓴 질의를 실행 전에 검사
    const body = q.replace(/^\s*PREFIX[^\n]*\n/gim, '').trim();               // 접두어 선언 제거(우리가 붙인다)
    if (!/^SELECT\b/i.test(body)) throw new Error('SELECT 질의가 아닙니다.');
    if (/\b(INSERT|DELETE|LOAD|CLEAR|DROP|CREATE|SERVICE)\b/i.test(body)) throw new Error('읽기 외의 명령이 들어 있습니다.');
    return /\bFROM\s*</i.test(body) ? body : body.replace(/\bWHERE\b/i, FROM + ' WHERE');  // 그래프 지정이 없으면 넣는다
  }
  async function llmPlan(u) {                                                 // LLM 이 SPARQL 을 쓴다(규칙이 찾은 개체를 힌트로 준다)
    const hints = [u.ent.group, u.ent.place, u.ent.ref, ...u.ent.concepts, ...u.ent.labels].filter(Boolean).map((e) => `${e.name} = <${e.iri}>`);
    const sys = SCHEMA + '\n질문을 이 그래프의 SPARQL 로 바꾼다. 답은 JSON 하나: {"sparql": "...", "explain": "한 문장 한국어 설명"}';
    const raw = await llm(sys, `질문: ${u.text}\n질문에서 찾은 개체(IRI): ${hints.join('; ') || '없음'}`, true);
    const j = JSON.parse(raw.slice(raw.indexOf('{'), raw.lastIndexOf('}') + 1));
    return { title: 'LLM이 쓴 질의', query: safeSelect(j.sparql), explain: j.explain };
  }
  async function llmAnswer(question, rows) {                                  // LLM 이 결과 표만 보고 답을 쓴다
    const sys = '너는 아카이브 검색 결과를 설명하는 안내자다. 아래 결과 표에 있는 내용만 써라. 표에 없는 사실, 숫자, 해석을 더하지 마라. 결과가 비어 있으면 찾지 못했다고만 말하라. 차분한 -습니다체 한국어 3문장 이내. cite 열의 값은 문장 끝 괄호에 그대로 적는다.';
    return llm(sys, `질문: ${question}\n결과 표(JSON, 최대 40행): ${JSON.stringify(rows.slice(0, 40))}`, false);
  }

  // ===== 화면 =====
  const ui = {};
  function render() {
    root.classList.add('ask');                                                // 스타일 이름표
    ui.form = $('form', { class: 'ask-form', role: 'search', onsubmit: (e) => { e.preventDefault(); run(ui.input.value); } }, [
      $('label', { for: 'ask-q', class: 'sr-only', text: '자료에게 물을 질문' }),
      ui.input = $('input', { id: 'ask-q', type: 'search', placeholder: '예: 고려인은 김치를 뭐라고 불렀어?', autocomplete: 'off' }),
      $('button', { type: 'submit', class: 'btn btn-primary', text: '묻기' }),
    ]);
    ui.examples = $('div', { class: 'ask-examples', 'aria-label': '예시 질문' },
      EXAMPLES.map((q) => $('button', { type: 'button', class: 'chip', text: q, onclick: () => { ui.input.value = q; run(q); } })));
    ui.engine = $('p', { class: 'hint ask-engine' });
    ui.out = $('div', { class: 'ask-out', 'aria-live': 'polite' });            // 결과(화면 낭독기가 읽어 줌)
    root.append(ui.form, ui.examples, ui.engine, settingsPanel(), ui.out);
    updateEngine();
    const q0 = new URLSearchParams(location.search).get('q');                 // 주소의 ?q= 로 바로 묻기(공유용)
    if (q0) { ui.input.value = q0; run(q0); }
  }
  function updateEngine() {                                                   // 지금 어떤 변환기를 쓰는지 표시
    const on = store.get('useLlm', '0') === '1';
    const p = store.get('provider', 'anthropic');
    ui.engine.textContent = on ? `변환기: LLM(${p === 'ollama' ? 'Ollama ' + store.get('ollamaModel', 'qwen2.5:7b') : store.get('anthropicModel', 'claude-haiku-5-5')}) — 실패하면 규칙으로 돌아갑니다`
      : '변환기: 규칙(질문 유형 9가지 + 그래프에서 읽은 이름 사전). 아래 ‘LLM 설정’에서 바꿀 수 있습니다.';
  }
  function settingsPanel() {                                                  // LLM 설정(접혀 있음)
    const field = (label, input) => $('label', { class: 'ask-field' }, [$('span', { text: label }), input]);
    const use = $('input', { type: 'checkbox', onchange: (e) => { store.set('useLlm', e.target.checked ? '1' : '0'); updateEngine(); } });
    use.checked = store.get('useLlm', '0') === '1';
    const prov = $('select', { onchange: (e) => { store.set('provider', e.target.value); updateEngine(); } },
      [$('option', { value: 'anthropic', text: 'Anthropic API(내 키)' }), $('option', { value: 'ollama', text: 'Ollama(이 컴퓨터)' })]);
    prov.value = store.get('provider', 'anthropic');
    const key = $('input', { type: 'password', autocomplete: 'off', placeholder: 'sk-ant-…', onchange: (e) => store.set('anthropicKey', e.target.value.trim()) });
    key.value = store.get('anthropicKey', '');
    const model = $('input', { type: 'text', onchange: (e) => { store.set('anthropicModel', e.target.value.trim()); updateEngine(); } });
    model.value = store.get('anthropicModel', 'claude-haiku-5-5');
    const om = $('input', { type: 'text', onchange: (e) => { store.set('ollamaModel', e.target.value.trim()); updateEngine(); } });
    om.value = store.get('ollamaModel', 'qwen2.5:7b');
    return $('details', { class: 'ask-settings' }, [
      $('summary', { text: 'LLM 설정(선택)' }),
      $('p', { class: 'notice', text: 'API 키는 이 브라우저(localStorage)에만 저장되고 이 서버로 보내지 않습니다. 다른 사람이 쓰는 컴퓨터나 공개 사이트에서는 키를 넣지 마세요. LLM 이 쓴 답은 결과 표와 반드시 대조하세요.' }),
      $('label', { class: 'ask-check' }, [use, $('span', { text: ' 질문을 LLM 으로 SPARQL 로 바꾸고, 답도 LLM 이 쓰게 하기' })]),
      field('제공자', prov), field('Anthropic API 키', key), field('Anthropic 모델', model), field('Ollama 모델', om),
    ]);
  }

  async function run(text, overrideQuery) {                                   // 질문 하나 처리
    text = (text || '').trim();
    if (!text && !overrideQuery) return;
    ui.out.replaceChildren($('p', { class: 'hint', text: '찾는 중…' }));
    try {
      if (!LEX.groups.length) await loadLexicon();                            // 사전이 없으면 먼저 읽기
      const u = understand(text);                                             // 1. 질문 이해
      let plan, how = 'rule';                                                 // 2. SPARQL 만들기
      if (overrideQuery) { plan = { title: '고친 질의', query: safeSelect(overrideQuery) }; how = 'edit'; }
      else if (store.get('useLlm', '0') === '1') {
        try { plan = await llmPlan(u); how = 'llm'; } catch (e) { plan = BUILD[u.intent](u); how = 'rule'; u.llmError = e.message; }
      } else plan = BUILD[u.intent](u);
      let result;                                                             // 3. 실행
      try { result = await sparql(PREFIXES + plan.query); }
      catch (e) {
        if (how !== 'llm') throw e;                                           // 규칙 질의 오류는 그대로 보고
        u.llmError = e.message; plan = BUILD[u.intent](u); how = 'rule';      // LLM 질의가 실패하면 규칙으로
        result = await sparql(PREFIXES + plan.query);
      }
      let ans;                                                                // 4. 자연어 답
      if (how === 'rule') ans = plan.answer(result.rows);
      else {
        let t;
        try { t = await llmAnswer(text, result.rows); } catch (e) { t = `결과 ${result.rows.length}행을 찾았습니다. 표를 확인하세요. (답 쓰기 실패: ${e.message})`; }
        ans = { text: t, items: [] };
      }
      show(u, plan, how, result, ans);
    } catch (e) {
      ui.out.replaceChildren($('p', { class: 'notice', text: '검색하지 못했습니다. ' + e.message }));
    }
  }

  const INTENT_NAME = { naming: '대상을 부르는 말', meaning: '말의 뜻', scenes: '생활 장면 찾기', countScenes: '장면 세기', countWords: '어휘 세기',
    origin: '다른 언어에서 온 말', etymology: '어원', oneRoot: '같은 대상, 다른 이름', source: '문헌이 근거인 자원', keyword: '낱말 검색' };
  function show(u, plan, how, result, ans) {                                  // 결과 그리기
    const chips = [];                                                         // 알아들은 개체
    if (u.ent.group) chips.push(['문화권', u.ent.group.name]);
    if (u.ent.aspect) chips.push(['측면', `${u.ent.aspect.label} ${u.ent.aspect.value}`]);
    if (u.ent.place) chips.push(['장소', u.ent.place.name]);
    u.ent.concepts.forEach((c) => chips.push(['생활 대상', c.name]));
    u.ent.labels.forEach((l) => chips.push(['어휘', l.name]));
    if (u.ent.lang) chips.push(['기원 언어', u.ent.lang.name]);
    if (u.ent.ref) chips.push(['출처', `${u.ent.ref.author}(${u.ent.ref.year})`]);
    if (u.keyword) chips.push(['검색어', u.keyword]);

    const qBox = $('textarea', { class: 'code ask-query', rows: String(Math.min(16, plan.query.split('\n').length + 1)), spellcheck: 'false', 'aria-label': 'SPARQL 질의' });
    qBox.value = PREFIXES + plan.query;                                       // 실제로 보낸 질의 그대로

    ui.out.replaceChildren(
      $('section', { class: 'ask-step' }, [                                   // ① 질문 이해
        $('p', { class: 'eyebrow', text: '① 질문 이해' }),
        $('p', {}, [$('strong', { text: how === 'llm' ? 'LLM 변환' : how === 'edit' ? '직접 고친 질의' : INTENT_NAME[u.intent] }),
          how === 'llm' && plan.explain ? ' — ' + plan.explain : '']),
        chips.length ? $('ul', { class: 'ask-chips' }, chips.map(([k, v]) => $('li', { class: 'chip' }, [$('span', { class: 'chip-k', text: k }), ' ' + v]))) : null,
        u.llmError ? $('p', { class: 'hint', text: 'LLM 변환에 실패해 규칙으로 처리했습니다: ' + u.llmError }) : null,
      ]),
      $('section', { class: 'ask-step ask-answer' }, [                        // ② 답
        $('p', { class: 'eyebrow', text: '② 답' }),
        $('p', { class: 'ask-answer-text', text: ans.text }),
        how === 'rule' ? $('p', { class: 'hint', text: '이 답은 아래 결과 표에서 정해진 문장 틀로 만들었습니다. 그래프에 없는 내용은 더하지 않습니다.' })
          : $('p', { class: 'notice', text: 'LLM 이 결과 표를 보고 쓴 문장입니다. 표에 없는 내용이 섞이지 않았는지 확인하세요.' }),
        ans.items.length ? $('div', { class: 'card-grid ask-cards' }, ans.items.slice(0, 24).map(card)) : null,
        ans.items.length > 24 ? $('p', { class: 'hint', text: `앞의 24개만 카드로 보였습니다. 전체는 결과 표에 있습니다.` }) : null,
      ]),
      $('details', { class: 'ask-step', open: how !== 'rule' }, [            // ③ SPARQL
        $('summary', { text: `③ SPARQL 질의 (${plan.title})` }),
        qBox,
        $('p', {}, [$('button', { type: 'button', class: 'btn', text: '이 질의로 다시 실행', onclick: () => run(u.text || '(직접 고친 질의)', qBox.value) })]),
      ]),
      $('details', { class: 'ask-step' }, [                                   // ④ 결과 표
        $('summary', { text: `④ 결과 표 (${result.rows.length}행)` }),
        table(result),
      ]),
    );
  }
  function card(it) {                                                         // 결과 카드 하나
    return $('article', { class: 'scene-card' }, [
      it.sub ? $('p', { class: 'card-meta', text: it.sub }) : null,
      $('h3', { class: 'card-title' }, [it.link ? $('a', { href: it.link, target: '_blank', rel: 'noopener', text: it.head }) : it.head]),
      it.body ? $('p', { class: 'card-text', text: it.body }) : null,
      it.extra ? $('p', { class: 'hint', text: it.extra }) : null,
      it.cites && it.cites.length ? $('p', { class: 'ask-cite', text: '근거: ' + uniq(it.cites).sort().map(cite).join(' · ') }) : null,
    ]);
  }
  function table({ vars, rows }) {                                            // 결과 표
    if (!rows.length) return $('p', { class: 'hint', text: '결과가 없습니다.' });
    return $('div', { class: 'ask-table-wrap' }, [$('table', { class: 'ask-table' }, [
      $('thead', {}, [$('tr', {}, vars.map((v) => $('th', { scope: 'col', text: v })))]),
      $('tbody', {}, rows.slice(0, 300).map((r) => $('tr', {}, vars.map((v) => $('td', { text: r[v] ? (/^https?:/.test(r[v]) ? local(r[v]) : r[v]) : '' }))))),
    ])]);
  }

  render();                                                                   // 화면 그리기 시작
  loadLexicon().catch((e) => { ui.engine.textContent = '이름 사전을 읽지 못했습니다: ' + e.message; });  // 사전 미리 읽기
})();
