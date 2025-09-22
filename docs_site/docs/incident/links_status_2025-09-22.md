# 링크 상태 주간 보고서

**검사 일시**: 2025-09-22 07:09:50 UTC
**워크플로**: weekly_monitor.yml
**상태**: 자동 검사 완료

## 📋 검사 결과

```
=== README.md 링크 검사 ===
/opt/hostedtoolcache/node/18.20.8/x64/lib/node_modules/markdown-link-check/node_modules/undici/lib/web/webidl/index.js:531
webidl.is.File = webidl.util.MakeTypeAssertion(File)
                                               ^

ReferenceError: File is not defined
    at Object.<anonymous> (/opt/hostedtoolcache/node/18.20.8/x64/lib/node_modules/markdown-link-check/node_modules/undici/lib/web/webidl/index.js:531:48)
    at Module._compile (node:internal/modules/cjs/loader:1364:14)
    at Module._extensions..js (node:internal/modules/cjs/loader:1422:10)
    at Module.load (node:internal/modules/cjs/loader:1203:32)
    at Module._load (node:internal/modules/cjs/loader:1019:12)
    at Module.require (node:internal/modules/cjs/loader:1231:19)
    at require (node:internal/modules/helpers:177:18)
    at Object.<anonymous> (/opt/hostedtoolcache/node/18.20.8/x64/lib/node_modules/markdown-link-check/node_modules/undici/lib/web/fetch/util.js:12:20)
    at Module._compile (node:internal/modules/cjs/loader:1364:14)
    at Module._extensions..js (node:internal/modules/cjs/loader:1422:10)

Node.js v18.20.8
README 링크 검사 완료 (오류 포함)
=== REPORTS 디렉토리 링크 검사 (curl 기반) ===
GitHub 링크 상태 검사:
- Actions 페이지: HTTP 200
- Workflow 배지: HTTP 200
- 릴리스 페이지: HTTP 200
REPORTS 링크 검사 완료 (curl 기반)
```

## 📊 요약

- **README.md**: 0
0개 링크 정상
- **REPORTS**: curl 기반 GitHub 링크 검사 완료
- **검사 시각**: 2025-09-22 07:09:50 UTC

---

**자동 생성**: GitHub Actions weekly_monitor.yml
