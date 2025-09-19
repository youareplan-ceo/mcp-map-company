/**
 * CRACO 설정 - Create React App 설정 오버라이드
 * Webpack deprecated 경고 해결 및 성능 최적화
 */

const path = require('path');

module.exports = {
  // Webpack 설정 최적화
  webpack: {
    configure: (webpackConfig, { env, paths }) => {
      // 개발 서버 설정 최적화 (deprecated 경고 해결)
      if (env === 'development' && webpackConfig.devServer) {
        // 기존 deprecated 속성 제거
        delete webpackConfig.devServer.onAfterSetupMiddleware;
        delete webpackConfig.devServer.onBeforeSetupMiddleware;
        
        // 새로운 setupMiddlewares 방식 적용
        webpackConfig.devServer.setupMiddlewares = (middlewares, devServer) => {
          if (!devServer) {
            throw new Error('webpack-dev-server is not defined');
          }

          // 헬스체크 엔드포인트 추가
          devServer.app.get('/health', (req, res) => {
            res.json({ 
              status: 'healthy', 
              service: 'StockPilot Frontend',
              timestamp: new Date().toISOString() 
            });
          });

          return middlewares;
        };

        // 개발 서버 성능 향상 설정
        webpackConfig.devServer = {
          ...webpackConfig.devServer,
          hot: true,
          liveReload: false,
          compress: true,
          client: {
            overlay: {
              errors: true,
              warnings: false, // 경고 오버레이 비활성화로 성능 향상
            },
            progress: false, // 진행률 표시 비활성화
          },
          devMiddleware: {
            stats: 'errors-warnings', // 로그 최소화
          },
        };
      }

      // 번들 분할 최적화
      webpackConfig.optimization = {
        ...webpackConfig.optimization,
        splitChunks: {
          chunks: 'all',
          minSize: 20000,
          maxSize: 244000,
          cacheGroups: {
            default: {
              minChunks: 2,
              priority: -20,
              reuseExistingChunk: true,
            },
            vendor: {
              test: /[\\/]node_modules[\\/]/,
              name: 'vendors',
              priority: -10,
              chunks: 'all',
            },
            mui: {
              test: /[\\/]node_modules[\\/]@mui[\\/]/,
              name: 'mui-core',
              priority: 10,
              chunks: 'all',
            },
            recharts: {
              test: /[\\/]node_modules[\\/]recharts[\\/]/,
              name: 'recharts',
              priority: 10,
              chunks: 'all',
            },
          },
        },
      };

      // 소스맵 최적화 (개발 환경)
      if (env === 'development') {
        webpackConfig.devtool = 'eval-cheap-module-source-map';
      }

      // 프로덕션 빌드 최적화
      if (env === 'production') {
        webpackConfig.devtool = 'source-map';
        
        // 불필요한 소스맵 제거
        webpackConfig.optimization.minimizer = webpackConfig.optimization.minimizer.map(plugin => {
          if (plugin.constructor.name === 'TerserPlugin') {
            plugin.options.sourceMap = false;
          }
          return plugin;
        });
      }

      return webpackConfig;
    },
  },

  // TypeScript 설정 최적화
  typescript: {
    enableTypeChecking: true,
  },

  // ESLint 설정
  eslint: {
    enable: true,
    mode: 'extends',
    configure: {
      rules: {
        // TypeScript 경고 완화
        '@typescript-eslint/no-unused-vars': 'warn',
        '@typescript-eslint/no-explicit-any': 'warn',
        'react-hooks/exhaustive-deps': 'warn',
      },
    },
  },

  // 개발 서버 프록시 설정
  devServer: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
};