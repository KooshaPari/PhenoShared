# =============================================================================
# Build Stage
# =============================================================================
FROM --platform=$BUILDPLATFORM node:20-alpine AS builder

WORKDIR /build

# Install dependencies
COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build
RUN pnpm run build

# =============================================================================
# Runtime Stage
# =============================================================================
FROM --platform=$BUILDPLATFORM node:20-alpine

WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache ca-certificates

# Copy built application
COPY --from=builder /build/dist ./dist
COPY --from=builder /build/package.json ./

# Set environment
ENV NODE_ENV=production

# Set entrypoint
ENTRYPOINT ["node", "dist/main.js"]
CMD ["--help"]
