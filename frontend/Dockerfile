# Stage 1: Build and compile the Angular application
FROM node:22 AS build
WORKDIR /app
COPY . .

# Set memory limit flag to prevent Node.js from running out of RAM during compilation
ENV NODE_OPTIONS="--max-old-space-size=512"

# Install packages smoothly and execute production build
RUN npm install --no-audit --no-fund
RUN npx ng build --configuration production

# Stage 2: Serve the compiled application static assets via Nginx
FROM nginx:alpine

# Copy the generated production build files into the default Nginx public server directory
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]