<?php
/**
 * 한뿌리다른땅.ttl 을 Omeka S Sparql 모듈의 내부 저장소(ARC2, store "triplestore")에
 * 이름 붙은 그래프 하나로 올린다. Omeka 데이터와 섞이지 않게 그래프를 따로 둔다.
 *
 * 주의: Sparql 모듈에서 다시 인덱싱(Index)하면 저장소 전체가 비워지므로, 그 뒤에 이 스크립트를 다시 실행한다.
 *
 * 사용(컨테이너 안에서): php load_ttl.php /tmp/한뿌리다른땅.ttl
 */
require '/var/www/html/modules/Sparql/vendor/autoload.php';

const GRAPH = 'https://yunu-jeon.github.io/DH-Korean-Diaspora/graph/grounding';

$ttl = $argv[1] ?? '';
if (!is_file($ttl)) {
    fwrite(STDERR, "TTL 파일이 없습니다: $ttl\n");
    exit(1);
}

// Omeka 의 DB 접속 정보(database.ini)를 그대로 쓴다
$db = parse_ini_file('/var/www/html/volume/config/database.ini');
$store = ARC2::getStore([
    'db_host' => $db['host'],
    'db_name' => $db['dbname'],
    'db_user' => $db['user'],
    'db_pwd' => $db['password'],
    'store_name' => 'triplestore',  // Sparql 모듈의 내부 엔드포인트가 읽는 저장소
]);
$store->createDBCon();
if (!$store->isSetUp()) {
    $store->setUp();
}

$store->query('DELETE FROM <' . GRAPH . '>');  // 이전에 올린 것을 지우고 새로 올린다
$result = $store->query('LOAD <file://' . $ttl . '> INTO <' . GRAPH . '>');
if ($errors = $store->getErrors()) {
    fwrite(STDERR, implode("\n", $errors) . "\n");
    exit(1);
}

$count = $store->query('SELECT (COUNT(*) AS ?n) FROM <' . GRAPH . '> WHERE { ?s ?p ?o }', 'row');
echo 'graph <' . GRAPH . '>: ' . $result['result']['t_count'] . " triples loaded, {$count['n']} in graph\n";
