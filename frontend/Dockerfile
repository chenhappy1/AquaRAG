# 1. 编译构建阶段
FROM node:22 AS build
WORKDIR /app
COPY . .
# 开启限流保护防止撑爆内存，并执行 Angular 编译
ENV NODE_OPTIONS="--max-old-space-size=512"
RUN npm install --no-audit --no-fund
RUN npx ng build --configuration production

# 2. 运行阶段：使用我们之前配置过的 Nginx 服务器作为载体
FROM nginx:alpine
# 把 Angular 编译出来的前端静态文件，复制到 Nginx 的网页托管目录
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]