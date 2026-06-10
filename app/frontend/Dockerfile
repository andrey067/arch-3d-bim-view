FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx-https.conf /etc/nginx/conf.d/default.conf
COPY 192.168.68.51.pem 192.168.68.51-key.pem /etc/nginx/certs/
EXPOSE 3000 443
CMD ["nginx", "-g", "daemon off;"]
