FROM node:20-bookworm-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends chromium ca-certificates fonts-liberation && rm -rf /var/lib/apt/lists/*
COPY package.json /app/package.json
RUN npm install --omit=dev
COPY server.js /app/server.js
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
CMD ["node", "server.js"]
