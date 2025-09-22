# 🔒 Sprint-2 Secrets Management

## Required GitHub Secrets
- `RENDER_DEPLOY_HOOK`: Render deploy hook URL
- `VERCEL_TOKEN`: Vercel CLI access token

## 관리 원칙
1. 절대 코드 레포에 직접 노출하지 않는다.
2. GitHub Settings → Secrets → Actions 경로로만 등록한다.
3. 변경 시 PR 템플릿에 `Secrets updated` 라벨 추가한다.
