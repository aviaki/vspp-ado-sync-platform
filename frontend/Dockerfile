# ---------- build stage ----------
FROM node:20-alpine AS builder
WORKDIR /app

COPY package.json vite.config.js tailwind.config.js postcss.config.js ./
COPY src ./src
COPY index.html .

RUN npm install --no-audit --no-fund && npm run build

# ---------- runtime stage ----------
FROM nginx:alpine

# remove default site
RUN rm /etc/nginx/conf.d/default.conf

# custom API-proxy / SPA fallback config
COPY nginx/api.conf /etc/nginx/conf.d/api.conf

# static assets
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

