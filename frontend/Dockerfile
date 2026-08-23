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

# Copy Angular build output
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html

# Copy custom Nginx config (THIS IS THE KEY)
COPY default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]