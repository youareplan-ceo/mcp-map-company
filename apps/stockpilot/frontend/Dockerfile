# Node.js 18 알파인 이미지 사용
FROM node:18-alpine

# 작업 디렉토리 설정
WORKDIR /app

# package.json과 yarn.lock 복사
COPY package*.json ./

# 의존성 설치
RUN npm install

# 애플리케이션 코드 복사
COPY . .

# 포트 3000 노출
EXPOSE 3000

# 개발 서버 시작 명령
CMD ["npm", "start"]