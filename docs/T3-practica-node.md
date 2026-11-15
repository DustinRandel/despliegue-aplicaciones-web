---
title: 'Práctica 3.2 - Aplicación Node.js con Express'
---

<!--
NOTA PARA EL PROFESOR (no se muestra al alumnado):

Reescrita a partir de P3.2-NodeJS-Express.md. Cambios:
  - El original era para Debian 11, mandaba parar tomcat9 (en Debian 13 es tomcat10 y ya no choca: escucha en
    8080 y Node en 3000), hablaba de "grupo de seguridad" (AWS) y enlazaba a un repositorio (react-weather-app)
    distinto del que luego clonaba (Shopping-Cart-Application). Se sustituye por una aplicación propia mínima.
  - Se conserva la idea buena del original: el "nodemon: not found" al hacer npm run dev. Ahora se explica por
    qué pasa (node_modules/.bin y devDependencies) en lugar de dejarlo como tarea abierta.
  - Añadido: npm ci --omit=dev, servicio systemd con www-data (no root ni el usuario del alumno), Restart, Nginx
    delante con trust proxy, X-Powered-By, y desplegar una versión = reiniciar el servicio.
  - HALLAZGO DE LA VALIDACIÓN: con Express 5, si el puerto está ocupado, app.listen NO lanza el error: se lo pasa
    al callback. Con el callback típico "() => console.log('Escuchando')" la aplicación dice que escucha y
    termina sin error (nodemon: "clean exit"). Por eso el código lleva (err) => { if (err) throw err; }.
  - nodejs 20.19.2 y npm 9.2.0 de Debian 13; npm descarga express 5.3.0 y nodemon 3.1.14 (versiones de hoy:
    pueden subir, el material no depende de la versión exacta).

VALIDADA el 27/10/2026 en contenedor Debian 13 con systemd. Salidas reales; adaptadas solo las IP del contenedor
al escenario y la ruta CGroup (en el contenedor lleva delante /docker/<id>).
PENDIENTE DE VALIDAR EN LA VM: curl.exe desde Windows; tamaño de "apt install nodejs npm" (npm de Debian arrastra
muchos paquetes node-*).
-->

# Práctica 3.2 - Aplicación Node.js con Express como servicio

!!! tip "Cuándo se hace"
    Al terminar el **bloque 3** de la [teoría del Tema 3](T3-servidores-aplicaciones.md), con la [práctica 3.1](T3-practica-tomcat.md) terminada. En la **máquina principal**.

!!! abstract "Objetivos"
    Al terminar esta práctica deberás ser capaz de:

    1. Crear un proyecto de Node.js con npm y distinguir dependencias de producción y de desarrollo.
    2. Escribir una aplicación mínima con Express que lea su configuración de variables de entorno.
    3. Instalar las dependencias en el servidor de forma reproducible con `npm ci`.
    4. Convertir la aplicación en un servicio de `systemd` con un usuario sin privilegios.
    5. Publicarla detrás de Nginx y desplegar una versión nueva.

---

## 1. Qué vas a montar

```
 Tu ordenador         debian-tuapellido (192.168.56.10)
 192.168.56.1  ───►   Nginx :80  ──── node.tuapellido.test ───►  node app.js  127.0.0.1:3000
                                                                  (servicio node-app, usuario www-data)
```

A diferencia de la práctica 3.1, aquí no hay un servidor donde desplegar: tu aplicación **es** el servidor.

## 2. Instalar Node.js y npm

```sh
sudo apt install nodejs npm
node -v
npm -v
```

```
v20.19.2
9.2.0
```

## 3. Crear el proyecto

La aplicación vivirá en `/var/www`, como las webs del Tema 2, y será **tuya** (el servicio solo necesitará leerla):

```sh
sudo mkdir /var/www/node.garcia.test
sudo chown $USER:$USER /var/www/node.garcia.test
cd /var/www/node.garcia.test
npm init -y
```

```
Wrote to /var/www/node.garcia.test/package.json:

{
  "name": "node.garcia.test",
  "version": "1.0.0",
  "description": "",
  "main": "index.js",
  "scripts": {
    "test": "echo \"Error: no test specified\" && exit 1"
  },
  "keywords": [],
  "author": "",
  "license": "ISC"
}
```

`npm init -y` crea un `package.json` con valores por defecto. Instala Express:

```sh
npm install express
```

```
added 65 packages, and audited 66 packages in 931ms

29 packages are looking for funding
  run `npm fund` for details

found 0 vulnerabilities
```

Has pedido un paquete y se han instalado 65: Express y todas sus dependencias, y las dependencias de estas. Mira qué ha cambiado:

```sh
ls
npm ls
```

```
node_modules  package-lock.json  package.json
node.garcia.test@1.0.0 /var/www/node.garcia.test
`-- express@5.3.0
```

- `package.json` tiene ahora `"dependencies": { "express": "^5.3.0" }`.
- `package-lock.json` guarda la versión exacta de los 65 paquetes.
- `node_modules/` contiene los 65 paquetes.

## 4. La aplicación

```sh
nano app.js
```

```js
const express = require('express');
const os = require('os');

const app = express();
const PORT = process.env.PORT || 3000;          // (1)!
const HOST = process.env.HOST || '127.0.0.1';

app.set('trust proxy', 'loopback');             // (2)!

app.get('/', (req, res) => {
  res.send(`<h1>Aplicación Node.js con Express</h1>
<p>Servida por <b>${os.hostname()}</b>. Prueba <a href="/api/hora">/api/hora</a>.</p>`);
});

app.get('/api/hora', (req, res) => {            // (3)!
  res.json({
    hora: new Date().toLocaleTimeString('es-ES', { timeZone: 'Europe/Madrid' }),
    servidor: os.hostname(),
    pid: process.pid,
    entorno: process.env.NODE_ENV || 'sin definir',
    cliente: req.ip
  });
});

app.listen(PORT, HOST, (err) => {               // (4)!
  if (err) throw err;
  console.log(`Escuchando en http://${HOST}:${PORT}`);
});
```

1. Puerto y dirección salen de variables de entorno, con un valor por defecto. Por defecto, **solo local**.
2. Le dice a Express que, si la conexión viene de la propia máquina (el Nginx local), se crea la cabecera `X-Forwarded-For` para saber la IP del cliente. Es lo mismo que `set_real_ip_from` en Nginx o `RemoteIpValve` en Tomcat.
3. Una ruta que responde JSON. `pid` es el número de proceso: te servirá para ver cuándo se reinicia la aplicación.
4. Abre el puerto. Si no puede (por ejemplo, porque ya está ocupado), termina con el error.

!!! warning "Por qué el `if (err) throw err`"
    En Express 5, si el puerto está ocupado, `app.listen` no lanza el error, sino que se lo pasa a la función. Con el típico `() => console.log('Escuchando')` de los tutoriales, la aplicación **dice que escucha y termina en silencio**. Con esta línea, verás el error de verdad:

    ```
    Error: listen EADDRINUSE: address already in use 127.0.0.1:3000
    ```

Ahora edita `package.json` para que `main` apunte a `app.js` y para tener dos scripts, uno para producción y otro para desarrollo:

```json
  "main": "app.js",
  "scripts": {
    "start": "node app.js",
    "dev": "nodemon app.js"
  },
```

## 5. Probar en desarrollo

Arranca en modo desarrollo:

```sh
npm run dev
```

```
> node.garcia.test@1.0.0 dev
> nodemon app.js

sh: 1: nodemon: not found
```

`npm run` ejecuta el comando con `node_modules/.bin` en el `PATH`, y `nodemon` no está ahí: nunca lo has instalado. Es una herramienta **de desarrollo** (reinicia la aplicación cada vez que guardas un fichero), así que se instala como tal:

```sh
npm install --save-dev nodemon
npm run dev
```

```
[nodemon] 3.1.14
[nodemon] to restart at any time, enter `rs`
[nodemon] watching path(s): *.*
[nodemon] watching extensions: js,mjs,cjs,json
[nodemon] starting `node app.js`
Escuchando en http://127.0.0.1:3000
```

Mira el `package.json`: ha aparecido `"devDependencies": { "nodemon": "^3.1.14" }`. Desde **otra terminal** SSH:

```sh
curl http://127.0.0.1:3000/api/hora
```

```
{"hora":"12:38:20","servidor":"debian-garcia","pid":583,"entorno":"sin definir","cliente":"127.0.0.1"}
```

Desde tu navegador, `http://192.168.56.10:3000` **no** responde: la aplicación escucha solo en local. Para probarla desde fuera, para con `Ctrl+C` y arráncala con otra dirección, sin tocar el código:

```sh
HOST=0.0.0.0 npm start
```

```
> node.garcia.test@1.0.0 start
> node app.js

Escuchando en http://0.0.0.0:3000
```

Ahora sí: entra en `http://192.168.56.10:3000/api/hora`. Esto es para probar; en producción irá detrás de Nginx. Para con `Ctrl+C`.

## 6. Preparar las dependencias de producción

En un servidor de verdad no copiarías tu `node_modules`: instalarías desde `package-lock.json`, sin lo de desarrollo. Simúlalo:

```sh
rm -rf node_modules
npm ci --omit=dev
ls node_modules/.bin
```

```
added 65 packages, and audited 66 packages in 358ms

29 packages are looking for funding
  run `npm fund` for details

found 0 vulnerabilities
ls: cannot access 'node_modules/.bin': No such file or directory
```

Vuelven a ser 65 paquetes, las versiones exactas del `package-lock.json`, y nodemon no está.

## 7. La aplicación como servicio

```sh
sudo nano /etc/systemd/system/node-app.service
```

```ini
[Unit]
Description=Aplicación Node.js de node.garcia.test
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/node.garcia.test
Environment=NODE_ENV=production
Environment=PORT=3000
ExecStart=/usr/bin/node app.js
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Se ejecuta con `www-data`, que puede **leer** la aplicación pero no modificarla, porque los ficheros son tuyos: si alguien encontrara un fallo en ella, no podría cambiar su código. Es la misma decisión que en la práctica 2.1. Fíjate también en que el servicio usa `node app.js` directamente y no `npm start`: así `systemd` vigila el proceso de Node y no el de npm.

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now node-app
systemctl status node-app
```

```
● node-app.service - Aplicación Node.js de node.garcia.test
     Loaded: loaded (/etc/systemd/system/node-app.service; enabled; preset: enabled)
     Active: active (running) since Tue 2026-10-27 12:51:17 CET; 1s ago
   Main PID: 1012 (node)
     Memory: 21.5M (peak: 22.5M)
        CPU: 203ms
     CGroup: /system.slice/node-app.service
             └─1012 /usr/bin/node app.js

Oct 27 12:51:17 debian-garcia systemd[1]: Started node-app.service - Aplicación Node.js de node.garcia.test.
Oct 27 12:51:17 debian-garcia node[1012]: Escuchando en http://127.0.0.1:3000
```

Unos 22 MB, frente a los 200 de Tomcat. Comprueba que ahora el entorno es `production`:

```sh
curl http://127.0.0.1:3000/api/hora
```

```
{"hora":"12:51:18","servidor":"debian-garcia","pid":1012,"entorno":"production","cliente":"127.0.0.1"}
```

!!! tip "Si el servicio falla al arrancar"
    Mira `sudo journalctl -u node-app -n 20`. Si dice `EADDRINUSE`, tienes todavía un `npm start` o `npm run dev` abierto en otra terminal ocupando el puerto 3000.

### Si la aplicación muere, `systemd` la levanta

Mata el proceso a la fuerza, como si hubiera fallado:

```sh
sudo kill -9 1012       # usa el Main PID de tu systemctl status
sudo journalctl -u node-app -n 5
```

```
Oct 27 12:51:18 debian-garcia systemd[1]: node-app.service: Main process exited, code=killed, status=9/KILL
Oct 27 12:51:18 debian-garcia systemd[1]: node-app.service: Failed with result 'signal'.
Oct 27 12:51:18 debian-garcia systemd[1]: node-app.service: Scheduled restart job, restart counter is at 1.
Oct 27 12:51:18 debian-garcia systemd[1]: Started node-app.service - Aplicación Node.js de node.garcia.test.
Oct 27 12:51:19 debian-garcia node[1028]: Escuchando en http://127.0.0.1:3000
```

Al instante vuelve a estar en marcha, con otro PID. Es lo que hace `Restart=on-failure`. Si la paras tú con `systemctl stop`, no la levanta: eso no es un fallo.

## 8. Publicar con Nginx

```sh
sudo nano /etc/nginx/sites-available/node.garcia.test
```

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name node.garcia.test;

    access_log /var/log/nginx/node.access.log;
    error_log  /var/log/nginx/node.error.log;

    location / {
        proxy_pass http://127.0.0.1:3000;
        include proxy_params;
    }
}
```

Actívalo, `sudo nginx -t`, recarga, y añade `node.garcia.test` a tu `hosts`. Desde tu ordenador:

```powershell
curl.exe http://node.garcia.test/api/hora
curl.exe -I http://node.garcia.test/api/hora
```

```
{"hora":"12:51:21","servidor":"debian-garcia","pid":1028,"entorno":"production","cliente":"192.168.56.1"}
```

```
HTTP/1.1 200 OK
Server: nginx
Date: Tue, 27 Oct 2026 11:51:21 GMT
Content-Type: application/json; charset=utf-8
Content-Length: 103
Connection: keep-alive
X-Powered-By: Express
ETag: W/"67-XHrwdUjTRur8yRzCTZNr2Vutj+k"
```

El cliente es tu IP real gracias a `trust proxy`. Y fíjate en `X-Powered-By: Express`: la aplicación anuncia a cualquiera con qué está hecha, lo que facilita buscar fallos conocidos de esa tecnología. Lo quitarás en el siguiente apartado.

## 9. Desplegar una versión nueva

En `app.js`, justo debajo de `const app = express();`, añade:

```js
app.disable('x-powered-by');          // no anunciar qué tecnología hay detrás
```

Recarga `http://node.garcia.test/api/hora`: la cabecera **sigue ahí**. Node carga el código al arrancar y no vuelve a leerlo; nodemon reiniciaba solo, pero en producción no hay nodemon. Desplegar una versión nueva en Node es **reiniciar el servicio**:

```sh
sudo systemctl restart node-app
sudo journalctl -u node-app -n 3
```

```
Oct 27 12:51:21 debian-garcia systemd[1]: Stopped node-app.service - Aplicación Node.js de node.garcia.test.
Oct 27 12:51:21 debian-garcia systemd[1]: Started node-app.service - Aplicación Node.js de node.garcia.test.
Oct 27 12:51:22 debian-garcia node[1045]: Escuchando en http://127.0.0.1:3000
```

```powershell
curl.exe -I http://node.garcia.test/api/hora
```

```
HTTP/1.1 200 OK
Server: nginx
Date: Tue, 27 Oct 2026 11:51:23 GMT
Content-Type: application/json; charset=utf-8
Content-Length: 103
Connection: keep-alive
ETag: W/"67-1hECdryAO8ylJjZs6eVS+EprvUQ"
```

Si un despliegue nuevo añadiera dependencias, el orden sería: actualizar el código, `npm ci --omit=dev`, `sudo systemctl restart node-app`, y comprobar.

!!! info "Reiniciar es cortar"
    Mientras el proceso se reinicia, Nginx no tiene a quién pasar las peticiones y responde `502`. Aquí es un instante, pero en producción se evita con varias copias de la aplicación detrás de un balanceador (práctica 2.5): se reinician de una en una y siempre queda alguna atendiendo.

## 10. Haz la instantánea

Apaga la máquina y toma una instantánea: `p3.2-node`.

---

## Cuestiones finales

!!! question "Cuestión 1"
    ¿Por qué `npm run dev` decía `nodemon: not found` si el script estaba bien escrito? ¿Qué cambió en `package.json` al solucionarlo?

!!! question "Cuestión 2"
    ¿Qué diferencia hay entre `npm install` y `npm ci`? ¿Cuál de los ficheros del proyecto subirías a un repositorio de Git y cuál no?

!!! question "Cuestión 3"
    Explica qué hace cada línea de la sección `[Service]` de `node-app.service`. ¿Por qué `www-data` y no tu usuario?

!!! question "Cuestión 4"
    Has arrancado la aplicación de tres formas: `npm run dev`, `HOST=0.0.0.0 npm start` y el servicio. ¿En qué dirección escuchaba en cada caso, y por qué la aplicación es la misma sin cambiar el código?

!!! question "Cuestión 5"
    Compara cómo se despliega una versión nueva en Tomcat (práctica 3.1) y en Node. ¿Por qué en Node hay que reiniciar?

## Entrega

Igual que en las prácticas anteriores: **documento de evidencias (40 %)** y **demostración en clase (60 %)**.

### Parte 1 — Documento de evidencias (40 %)

Un **PDF** llamado `P3.2-Apellido-Nombre.pdf` con portada, las evidencias (en texto, con comando y *prompt*) y las respuestas a las cuestiones.

| # | Qué hay que demostrar | Dónde | Comando cuya salida se pega |
|---|---|---|---|
| 1 | Las versiones instaladas | Principal | `node -v` y `npm -v` |
| 2 | El proyecto | Principal | `cat package.json` y `cat app.js` |
| 3 | El error de nodemon y su solución | Principal | `npm run dev` antes y después de instalarlo |
| 4 | Las dependencias de producción | Principal | `npm ci --omit=dev` y `npm ls` |
| 5 | El servicio | Principal | `cat /etc/systemd/system/node-app.service` y `systemctl status node-app` |
| 6 | El reinicio automático | Principal | `sudo journalctl -u node-app -n 5` tras el `kill -9` |
| 7 | Quién ejecuta la aplicación y dónde escucha | Principal | `ps -o user,pid,cmd -C node` y `sudo ss -tlnp` (líneas de los puertos 80 y 3000) |
| 8 | La configuración de Nginx | Principal | `cat /etc/nginx/sites-available/node.tuapellido.test` |
| 9 | La aplicación a través del proxy, con la IP real | Tu ordenador | `curl.exe http://node.tuapellido.test/api/hora` |
| 10 | La versión nueva, sin `X-Powered-By` | Tu ordenador | `curl.exe -I http://node.tuapellido.test/api/hora` |

### Parte 2 — Demostración en clase (60 %)

Mini entrevista individual en la mesa del profesor, con la máquina encendida: muestras la aplicación en `node.tuapellido.test`, haces la tarea que se te pida (por ejemplo, añadir una ruta y desplegarla) y explicas una decisión o un concepto.

### Criterios de evaluación

| Parte | Criterio | Peso |
|---|---|---|
| Documento | Las diez evidencias están completas, en texto y explicadas | 25 % |
| Documento | Las cinco cuestiones están respondidas con corrección y criterio propio | 15 % |
| Demostración | La aplicación funciona como servicio con `www-data`, solo en local, y se ve a través de `node.tuapellido.test` | 20 % |
| Demostración | Realizas la tarea que se te pide y explicas lo que haces | 20 % |
| Demostración | Explicas una decisión o un concepto con tus palabras | 20 % |

### Antes de entregar, comprueba que…

- ☐ `package.json` tiene `express` en `dependencies` y `nodemon` en `devDependencies`.
- ☐ El servicio `node-app` está `enabled` y `active (running)`, con el usuario `www-data`.
- ☐ La aplicación escucha en `127.0.0.1:3000`, no en `0.0.0.0`.
- ☐ `http://node.tuapellido.test/api/hora` muestra `"entorno":"production"` y tu IP real.
- ☐ La respuesta ya no lleva `X-Powered-By`.
- ☐ Existe la instantánea `p3.2-node`.
- ☐ El archivo se llama `P3.2-Apellido-Nombre.pdf`.

## Referencias

- [Node.js — Introducción](https://nodejs.org/es/learn/getting-started/introduction-to-nodejs)
- [Express — Hola mundo](https://expressjs.com/es/starter/hello-world.html)
- [Express — Detrás de un proxy (`trust proxy`)](https://expressjs.com/en/guide/behind-proxies.html)
- [Express — Buenas prácticas de seguridad en producción](https://expressjs.com/es/advanced/best-practice-security.html)
- [npm — `npm ci`](https://docs.npmjs.com/cli/commands/npm-ci)
- [`systemd.service` — Manual](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
