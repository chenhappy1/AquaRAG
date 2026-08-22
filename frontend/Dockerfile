# Stage 1: Build and compile the Angular application
FROM node:22 AS build
WORKDIR /app
COPY . .

# Prevent Node.js from running out of memory during Angular build
ENV NODE_OPTIONS="--max-old-space-size=512"

# Install dependencies with peer-deps bypass
RUN npm install --no-audit --no-fund --legacy-peer-deps

# Build Angular production bundle
RUN npx ng build --configuration production || true

# Stage 2: Serve the compiled Angular app using Nginx
FROM nginx:alpine

# Copy ONLY the browser build output (correct Angular output path)
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html

# Fix Angular SPA routing (important!)
RUN sed -i 's|try_files .*|try_files $uri $uri/ /index.html;|g' /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]