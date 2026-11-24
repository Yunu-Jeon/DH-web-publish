# IIIF Info — Omeka S 모듈

관리자 화면에 IIIF 정보를 더하는 작은 모듈. 주소는 IIIF Server 모듈이 만드는 것을 그대로 보여 준다
(IIIF Server 설정 `iiifserver_url_version_add` 를 켠 `/iiif/3/{id}/manifest` 형식).

- 아이템 보기: 'IIIF' 탭(매니페스트 ID 3.0·2.1, 아이템 ID·식별자, 캔버스별 미디어 ID·이미지 서비스·info.json) + 오른쪽 정보 칸의 매니페스트 링크
- 미디어 보기: 오른쪽 정보 칸에 이미지 서비스와 이 미디어가 든 매니페스트

공개 사이트 쪽 같은 정보는 테마 `omeka-themes/hanppuri` 의 `view/omeka/site/item/show.phtml` 이 보여 준다.

## 설치

```bash
docker cp omeka-modules/IiifInfo dh-web-publish-omekas-1:/var/www/html/volume/modules/
```

관리자 → Modules 에서 'IIIF Info' 를 설치한다.
