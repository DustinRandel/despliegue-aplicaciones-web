---
title: "Práctica 6.1: Nginx y una app con Compose"
---

<!--
NOTA PARA EL PROFESOR:
- P6.1–P6.3 originales (Juicy Shop, cluster). Aquí: una app mínima (Node o Flask)
  detrás de Nginx en Compose, en la VM .10, puerto 8080 para no tumbar el Nginx del host.
- PENDIENTE DE VALIDAR EN LA VM: instalar Docker en Debian 13, grupo docker, compose plugin.
-->

# Práctica 6.1: Nginx y una app con Compose

!!! tip "Cuándo se hace"
    Al terminar el bloque 4 de la [teoría del Tema 6](T6-docker.md). VM principal `.10`. El Nginx de las prácticas 2.x se deja en el 80.

!!! abstract "Objetivos"
    1. Instalar Docker y comprobar `hello-world`.
    2. Un `Dockerfile` de una app mínima (la de la P3.2 o una de 20 líneas).
    3. Un `compose.yml` con `app` y `proxy` (Nginx).
    4. Entrar por `http://192.168.56.10:8080` desde el portátil.

## 1. Docker en Debian

<!-- PENDIENTE DE VALIDAR EN LA VM -->

```
sudo apt update
sudo apt install docker.io docker-compose-v2
sudo adduser alumno docker
```

Cierra sesión SSH y vuelve a entrar. `docker run --rm hello-world`.

## 2. La app

Carpeta `~/deaw-compose/` con la app (Node en 3000 o Flask). `Dockerfile` del dosier. `docker build -t saludo .` y `docker run --rm -p 3000:3000 saludo` para probar. Luego `docker stop` / `rm`.

## 3. Nginx del compose

`nginx.conf` con `proxy_pass http://app:3000;` (o el nombre del servicio). `compose.yml` del dosier, puerto **8080:80**.

```
docker compose up -d --build
curl -sS http://127.0.0.1:8080/
```

Desde el portátil: `http://192.168.56.10:8080`. El 80 sigue siendo el Nginx de la UT2.

## 4. Qué entregar

PDF `UT6-P6.1-Apellido-Nombre.pdf` con:

1. `docker run --rm hello-world`.
2. `docker compose ps`.
3. `curl` al 8080 (VM) y captura del navegador en el portátil, con `<ini>`.
4. El `Dockerfile` y el `compose.yml` (texto, no captura borrosa).
