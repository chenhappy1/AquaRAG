# ============================
# Stage 1: Build Angular App
# ============================
FROM node:22 AS build
WORKDIR /app

COPY package*.json ./
ENV NODE_OPTIONS="--max-old-space-size=512"
RUN npm install --no-audit --no-fund --legacy-peer-deps

COPY . .
RUN npx ng build --configuration production

# ============================
# Stage 2: Serve with Nginx
# ============================
FROM nginx:alpine

# Copy Angular build output (your folder name is "frontend")
COPY --from=build /app/dist/frontend /usr/share/nginx/html

# Fix Angular SPA routing
RUN sed -i 's|try_files .*|try_files $uri $uri/ /index.html;|g' /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
