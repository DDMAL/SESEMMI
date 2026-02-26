# Stage 1 — Install dependencies
FROM node:22-alpine AS deps
RUN apk upgrade --no-cache
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# Stage 2 — Development (source mounted at runtime via volume)
FROM node:22-alpine AS dev
WORKDIR /app
ENV NODE_ENV=development
# Copy node_modules from deps; source is bind-mounted at runtime.
COPY --from=deps /app/node_modules ./node_modules
COPY package.json package-lock.json* ./
EXPOSE 3000
ENV PORT=3000
# Required on macOS Docker Desktop — inotify events don't propagate
# reliably from the VM; polling ensures file changes trigger recompilation.
ENV WATCHPACK_POLLING=true
CMD ["npm", "run", "dev"]

# Stage 3 — Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Provide a placeholder URL so Zod env validation passes at build time.
# Server-side env vars are read from the runtime container environment, not baked in.
ARG VIRTUOSO_ENDPOINT=http://placeholder:8890/sparql
ENV VIRTUOSO_ENDPOINT=$VIRTUOSO_ENDPOINT
ARG LLM_API_KEY=placeholder
ENV LLM_API_KEY=$LLM_API_KEY
RUN npm run build

# Stage 4 — Production runner
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
CMD ["node", "server.js"]
