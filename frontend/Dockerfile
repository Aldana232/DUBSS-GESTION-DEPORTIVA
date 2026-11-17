# ─── Imagen de PRODUCCIÓN del frontend (Next.js en modo «standalone») ───
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system dubss && adduser --system --ingroup dubss dubss

COPY --from=builder --chown=dubss:dubss /app/public ./public
COPY --from=builder --chown=dubss:dubss /app/.next/standalone ./
COPY --from=builder --chown=dubss:dubss /app/.next/static ./.next/static

USER dubss
EXPOSE 3000
CMD ["node", "server.js"]
