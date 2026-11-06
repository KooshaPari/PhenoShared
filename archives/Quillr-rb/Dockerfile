# TypeScript/Node.js Multi-Stage Build
FROM node:26-slim as builder

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tsconfig.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY src ./src

# Build the project
RUN npm run build

# Runtime stage
FROM node:26-slim

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install production dependencies only
RUN npm ci --only=production

# Copy built files from builder
COPY --from=builder /app/dist ./dist

# Set non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
USER appuser

CMD ["node", "dist/index.js"]
