---
title: "Contenedores (Docker)"
subtitulo: "UT6. Dosier de apuntes"
modulo: "0614. Despliegue de aplicaciones web"
curso: "2026-2027"
profesor: "Dustin Randel de Lara García"
centro: "Sant Josep Obrer"
ut: "UT6"
---

<!--
NOTA PARA EL PROFESOR:
- Fuente: containers.md, dockerfile.md, docker-compose.md y P6.1–P6.3 del original.
- Este módulo no es CONT: aquí Docker sirve para empaquetar lo que ya desplegaste en la UT3
  (Nginx delante, una app detrás) sin pelearte con apt en cada máquina.
- PENDIENTE DE VALIDAR EN LA VM: Docker no está en DAW-debian.ova. Instalar docker.io
  (o el repo oficial) en Debian 13, usuario en el grupo docker, un hello-world.
- El alumnado de Dual tiene CONT aparte; no copies el dosier de CONT, enlaza la idea.
-->

# Cómo se usa este dosier {.nobreak}

En la UT3 instalaste Tomcat, Node y Flask a mano. Un contenedor empaqueta la aplicación **con** su entorno: lo que corre en tu VM corre igual en un VPS.

!!! abstract "Qué vas a aprender en esta UT"
    - Qué es una imagen y qué es un contenedor.
    - El ciclo: `run`, `ps`, `logs`, `exec`, `stop`, `rm`.
    - Un `Dockerfile` mínimo para una app Node o Flask.
    - `docker compose` para Nginx + app, el mismo esquema de la UT3.

## Cómo se organiza esta UT

| Bloque | Teoría | Al terminar |
|---|---|---|
| 1. Imagen y contenedor | Apartados 1 y 2 | `docker run hello-world` y `docker ps -a` |
| 2. El ciclo de vida | Apartado 3 | stop, start, rm |
| 3. Dockerfile | Apartado 4 | Imagen de una app mínima |
| 4. Compose | Apartado 5 | [Práctica 6.1](T6-practica-compose.md) |

## 1. Por qué un contenedor aquí

Un contenedor no es una VM. Comparte el kernel de Debian. Aísla procesos, red y sistema de ficheros.

!!! definicion "Imagen"
    Plantilla de solo lectura: sistema de ficheros + comando por defecto. Se construye por capas.
    Un **contenedor** es una imagen en marcha, con una capa de escritura encima.

`docker pull`, `docker images`, `docker run`.

## 2. El ciclo

```
docker run --name hola -d nginx:alpine
docker ps
docker logs hola
docker exec hola nginx -v
docker stop hola
docker rm hola
```

`-d` es en segundo plano. Sin `-d`, el proceso ocupa la terminal (como `node app.js` sin systemd).

Publicar un puerto: `-p 8080:80` (host:contenedor). En la VM, Nginx del host y el del contenedor no pueden usar el 80 a la vez.

## 3. Dockerfile

```
FROM node:20-bookworm-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY . .
USER node
EXPOSE 3000
CMD ["node", "app.js"]
```

`docker build -t node-saludo .` y `docker run --rm -p 3000:3000 node-saludo`.

!!! ojo "root"
    Por defecto el proceso va como root dentro del contenedor. `USER` no root. No copies secretos en la imagen.

## 4. Compose: Nginx delante, app detrás

El mismo dibujo de la UT3, ahora en un YAML:

```
services:
  app:
    build: .
    expose:
      - "3000"
  proxy:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - app
```

Nginx del compose hace `proxy_pass http://app:3000`. El nombre `app` lo resuelve la red de Compose. El 8080 del host evita pelearse con el Nginx de las prácticas 2.x.

!!! comprueba "Comprueba"
    1. Si paras el contenedor, ¿se pierde la imagen?
    2. ¿`docker exec` crea un contenedor nuevo?
    3. ¿Por qué Compose usa el 8080 y no el 80 en esta VM?

## Referencias

- [Docker: overview](https://docs.docker.com/get-started/docker-overview/)
- [Dockerfile reference](https://docs.docker.com/reference/dockerfile/)
- [Compose specification](https://docs.docker.com/compose/compose-file/)
