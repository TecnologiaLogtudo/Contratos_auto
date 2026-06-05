FROM node:20-alpine AS builder

ARG VITE_APP_BASE_PATH=/contratos/
ARG VITE_API_BASE_URL=/contratos
ENV VITE_APP_BASE_PATH=${VITE_APP_BASE_PATH}
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

WORKDIR /build
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web ./
RUN npm run build

FROM nginx:1.27-alpine

COPY frontend/nginx.conf /etc/nginx/nginx.conf
COPY --from=builder /build/dist /usr/share/nginx/html/contratos
COPY frontend/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh


EXPOSE 80
ENTRYPOINT ["/entrypoint.sh"]
