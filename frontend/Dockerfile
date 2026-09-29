# Frontend production image: build the Vite PWA, serve static files via nginx.

# ---- Build stage ----
FROM node:20-alpine AS build
WORKDIR /app

# VITE_API_BASE is baked in at build time. Pass with:
#   docker build --build-arg VITE_API_BASE=https://api.example.com .
ARG VITE_API_BASE=/api
ENV VITE_API_BASE=$VITE_API_BASE

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- Serve stage ----
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
