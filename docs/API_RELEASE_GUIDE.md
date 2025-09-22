# API Release & Deploy Pipeline (Sprint-3)
- GHCR 이미지: `ghcr.io/<owner>/mcp-api`
- 워크플로: `.github/workflows/api-release.yml`

## 필수 시크릿(GitHub → Settings → Secrets → Actions)
- `GHCR_TOKEN` : GitHub Packages(ghcr) write 권한 토큰
- `RENDER_API_DEPLOY_HOOK` : Render 서비스 Deploy Hook URL

## 릴리즈 방법
1) 태그로 릴리즈:
   - `make api-tag V=v0.1.0` → tag push → 워크플로 자동 실행
2) 수동 실행:
   - Actions → "API Release & Deploy" → **Run workflow** → version 입력

> GHCR_TOKEN이 없으면 **이미지 빌드만** 하고 **푸시는 생략**됩니다.
