# Usa una imagen base de Node.js 24 LTS
FROM node:24.18.0

# instalar un simple servidor http para servir nuestro contenido estático
RUN npm install -g http-server

# Establece el directorio de trabajo en el contenedor
WORKDIR /app

# Copia el archivo package.json y package-lock.json al contenedor
COPY package*.json ./

RUN npm ci --silent

# Copia el resto de los archivos de la aplicación al contenedor
COPY . .

# Genera archivos de auto-imports y componentes antes del build
RUN npm run generate-types

# construir aplicación para producción minificada
RUN NODE_OPTIONS="--max-old-space-size=4096" npm run build

RUN NODE_OPTIONS="--max-old-space-size=4096" npm run build-storybook

FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf

RUN mkdir -p /usr/share/nginx/html/dist
RUN mkdir -p /usr/share/nginx/html/storybook

COPY --from=0 /app/dist /usr/share/nginx/html/dist
COPY --from=0 /app/storybook-static /usr/share/nginx/html/storybook

EXPOSE 8080 8081
CMD ["nginx", "-g", "daemon off;"]
