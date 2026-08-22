# ============================
# Stage 1: Build Angular App
# ============================
FROM node:22 AS build
WORKDIR /app

# Copy package files first (better caching)
COPY package*.json ./

# Install dependencies
ENV NODE_OPTIONS="--max-old-space-size=512"
RUN npm install --no-audit --no-fund --legacy-peer-deps

# Copy the rest of the Angular project
COPY . .

# Build Angular production bundle (no || true)
RUN npx ng build --configuration production

# ============================
# Stage 2: Serve with Nginx
# ============================
FROM nginx:alpine

# Copy Angular build output (auto-detect project name)
# This will copy ANY folder inside dist/ to Nginx
COPY --from=build /app/dist/* /usr/share/nginx/html

# Fix Angular SPA routing
RUN sed -i 's|try_files .*|try_files $uri $uri/ /index.html;|g' /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon