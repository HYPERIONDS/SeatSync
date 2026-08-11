FROM node:22-alpine AS build
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
ARG NODE_TLS_REJECT_UNAUTHORIZED=1
ENV NODE_TLS_REJECT_UNAUTHORIZED=$NODE_TLS_REJECT_UNAUTHORIZED
ARG PNPM_STRICT_SSL=true
ENV npm_config_strict_ssl=$PNPM_STRICT_SSL
RUN corepack enable && corepack prepare pnpm@11.16.0 --activate
RUN --mount=type=cache,id=seatsync-pnpm,target=/pnpm/store \
    pnpm config set store-dir /pnpm/store && \
    pnpm config set strict-ssl "$PNPM_STRICT_SSL" && \
    pnpm install --frozen-lockfile --reporter=append-only
COPY . .
ARG VITE_API_URL=http://localhost:8000/api/v1
ENV VITE_API_URL=$VITE_API_URL
RUN pnpm build
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
