# Frontend Dockerfile for Diet Planner UI
# Development mode with hot-reload (HMR)

FROM node:22-slim

# Set working directory
WORKDIR /app

# Copy package files first for better layer caching
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5173 || exit 1

# Start Vite dev server
# --host 0.0.0.0 is required for Docker networking
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
