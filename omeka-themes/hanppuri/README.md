# 한 뿌리, 다른 땅 — Omeka S 테마

정적 아카이브 사이트(DH-Korean-Diaspora)의 색·글꼴·헤더·카드 디자인을 Omeka S 사이트 `/s/hanppuri`에 옮긴 테마.
Omeka [Default 테마](https://github.com/omeka-s-themes/default) 1.9.3을 바탕으로 했다(GPLv3, `LICENSE`).

- `view/layout/layout.phtml` — 헤더(로고·메뉴·검색창)와 푸터
- `asset/css/style.css` — 전체 스타일(빌드 없음, 직접 고친다)

## 설치·갱신

```bash
docker cp omeka-themes/hanppuri dh-web-publish-omekas-1:/var/www/html/volume/themes/
```

처음이면 관리자 화면 → 사이트 → 테마에서 '한 뿌리, 다른 땅'을 고른다.
