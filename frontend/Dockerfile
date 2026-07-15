FROM oven/bun:1 AS build
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile
COPY . .
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN bun run build

FROM oven/bun:1-slim AS runtime
WORKDIR /app
COPY --from=build /app/.output ./.output
EXPOSE 3000
ENV PORT=3000 HOST=0.0.0.0
CMD ["bun", ".output/server/index.mjs"]
