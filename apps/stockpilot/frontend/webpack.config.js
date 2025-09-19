/**
 * Webpack 설정 최적화 - Deprecated 경고 해결
 * onAfterSetupMiddleware → setupMiddlewares 마이그레이션
 */

const path = require('path');

module.exports = function override(config, env) {
  // Webpack DevServer 설정 최적화
  if (env === 'development' && config.devServer) {
    // deprecated onAfterSetupMiddleware, onBeforeSetupMiddleware 제거
    delete config.devServer.onAfterSetupMiddleware;
    delete config.devServer.onBeforeSetupMiddleware;
    
    // 새로운 setupMiddlewares 사용
    config.devServer.setupMiddlewares = (middlewares, devServer) => {
      // 기본 미들웨어 설정
      if (!devServer) {
        throw new Error('webpack-dev-server is not defined');
      }

      // 커스텀 미들웨어 추가 (필요시)
      devServer.app.get('/api/health-check', (req, res) => {
        res.json({ status: 'ok', timestamp: new Date().toISOString() });
      });

      return middlewares;
    };

    // 개발 서버 성능 최적화
    config.devServer = {
      ...config.devServer,
      hot: true,
      liveReload: false, // HMR과 충돌 방지
      compress: true,
      historyApiFallback: true,
      client: {
        overlay: {
          errors: true,
          warnings: false, // 경고 오버레이 비활성화
        },
        progress: true,
      },
      devMiddleware: {
        stats: 'minimal', // 로그 최소화
      },
    };
  }

  // 번들 크기 최적화
  config.optimization = {
    ...config.optimization,
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          chunks: 'all',
        },
        mui: {
          test: /[\\/]node_modules[\\/]@mui[\\/]/,
          name: 'mui',
          chunks: 'all',
        },
      },
    },
  };

  // TypeScript 컴파일 성능 개선
  if (config.module && config.module.rules) {
    config.module.rules.forEach(rule => {
      if (rule.test && rule.test.toString().includes('tsx?')) {
        rule.options = {
          ...rule.options,
          transpileOnly: true, // 타입 체크 건너뛰기 (개발 모드)
          compilerOptions: {
            skipLibCheck: true,
          },
        };
      }
    });
  }

  return config;
};