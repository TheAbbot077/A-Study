FROM node:22-slim

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./

RUN npm ci
RUN npx playwright install --with-deps chromium

COPY frontend/ ./

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "3000"]
