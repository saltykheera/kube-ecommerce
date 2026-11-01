# Stage 1: Build Frontend Assets
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
# These values are intentionally public in the demo login page and JS bundle.
ARG VITE_DEMO_ADMIN_PASSWORD
ARG VITE_DEMO_MEMBER_PASSWORD
RUN npm run build

# Stage 2: Serve with Nginx Alpine
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
