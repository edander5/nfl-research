FROM node:22-bookworm-slim
WORKDIR /app
RUN chown node:node /app
USER node
COPY --chown=node:node package*.json ./
RUN if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi
COPY --chown=node:node . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
