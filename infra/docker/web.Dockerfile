FROM node:24-alpine AS build

RUN corepack enable

WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
COPY packages ./packages
RUN corepack prepare pnpm@10.17.1 --activate && pnpm install --frozen-lockfile

COPY apps/web ./apps/web
RUN pnpm --filter @ai-vastu/web build

EXPOSE 3000
CMD ["pnpm", "--filter", "@ai-vastu/web", "start"]
