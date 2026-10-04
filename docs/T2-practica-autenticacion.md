---
title: 'Práctica 2.3 - Autenticación y control de acceso'
---

<!--
NOTA PARA EL PROFESOR (no se muestra al alumnado):

Reescrita a partir de old.P1.2.md ("Práctica 2.2 – Autenticación en Nginx"). Cambios:
  - Va DESPUÉS de HTTPS (P2.2): la autenticación básica manda usuario y contraseña en base64, que no es cifrado.
    Se demuestra con curl -v (cabecera Authorization) y base64 -d.
  - htpasswd (paquete apache2-utils, solo utilidades: no instala Apache) con -B (bcrypt) en lugar del truco
    echo + openssl passwd -apr1 del original, que dejaba ficheros mal formados con facilidad.
  - Permisos del .htpasswd: root:www-data 640. Con 600, los trabajadores (www-data) no lo pueden leer y Nginx
    responde 500 (comprobado; sale "Permission denied" en el error.log). Es un buen ejercicio de diagnóstico.
  - Proteger solo una página: elements.html de la plantilla Phantom (web2), con location exacta (=).
    El original usaba contact.html de otra plantilla.
  - Restricción por IP con la IP REAL del anfitrión en la red Host-only (192.168.56.1), comprobada desde
    Windows (bloqueado) y desde la propia VM (permitido).
  - Cuestiones finales: las 3 de allow/deny/satisfy del original, corregidas (la 2 del original tenía un
    título roto). La 4 (web de Jeff Bezos) se sustituye por una sobre base64.

VALIDADA el 05/10/2026 (VM Debian 13.7, nginx 1.26.3). htpasswd -B genera bcrypt ($2y$05$) y nginx lo acepta.
  Comprobado: 600 en .htpasswd -> 500 + "Permission denied"; 640 root:www-data -> 200.
PENDIENTE: captura de la ventana de usuario y contraseña del navegador.
-->

# Práctica 2.3 - Autenticación y control de acceso en Nginx

!!! tip "Cuándo se hace"
    En el **bloque 4** de la [teoría del Tema 2](T2-arquitectura-web.md), con la [práctica 2.2](T2-practica-https.md) terminada: tus dos sitios ya funcionan por HTTPS.

!!! abstract "Objetivos"
    Al terminar esta práctica deberás ser capaz de:

    1. Crear un fichero de usuarios y contraseñas para Nginx, con los permisos correctos.
    2. Proteger un sitio entero, o solo una parte, con autenticación básica de HTTP.
    3. Explicar por qué la autenticación básica solo es aceptable sobre HTTPS.
    4. Permitir o denegar el acceso según la IP del cliente.
    5. Combinar las dos condiciones (IP y contraseña) con `satisfy`.

---

## 1. Autenticación básica: qué es y qué no es

La **autenticación básica** de HTTP es la forma más sencilla de pedir usuario y contraseña. No necesita programar nada: el servidor responde `401 Unauthorized` con la cabecera `WWW-Authenticate`, el navegador muestra una ventana para pedir los datos y, a partir de ahí, los envía **en cada petición** en la cabecera `Authorization`.

!!! danger "Base64 no es cifrado"
    El navegador manda usuario y contraseña en **base64**, que es solo otra forma de escribir el texto, no un cifrado: cualquiera lo deshace en un segundo. Por eso la autenticación básica **solo** se usa sobre HTTPS, y por eso esta práctica va después de la 2.2. Lo comprobarás en el apartado 4.

## 2. Crear los usuarios

Las contraseñas se guardan en un fichero, cada una con su **hash**: un resumen del que no se puede recuperar la contraseña. Lo crea la herramienta `htpasswd`, del paquete `apache2-utils` (solo trae utilidades: no instala Apache):

```sh
sudo apt install apache2-utils
```

Crea el fichero con un primer usuario, **tu nombre** en minúsculas (`-c` crea el fichero; `-B` usa el algoritmo bcrypt):

```sh
sudo htpasswd -c -B /etc/nginx/.htpasswd ana
```

Te pedirá la contraseña dos veces. Añade un segundo usuario, **tu primer apellido**, esta vez **sin** `-c` (si lo pones, borra el fichero y empieza de cero):

```sh
sudo htpasswd -B /etc/nginx/.htpasswd garcia
```

Mira el fichero:

```sh
sudo cat /etc/nginx/.htpasswd
```

```
ana:$2y$05$dDHxyJNUs7HbizkUys8ceeM2TWFAnJaot3V3RJVUm9qrXmnwRm8aG
garcia:$2y$05$vsyk6nY.pJo5w8Wj.tU6r.oRQVQubpSVVCkcs4HI3pCgR78UXwqEq
```

Una línea por usuario: el nombre y el hash. La contraseña no aparece en ningún sitio.

### Permisos del fichero

Nginx lee este fichero desde sus trabajadores, que son `www-data`. Que lo pueda leer `www-data`, pero nadie más:

```sh
sudo chown root:www-data /etc/nginx/.htpasswd
sudo chmod 640 /etc/nginx/.htpasswd
ls -l /etc/nginx/.htpasswd
```

```
-rw-r----- 1 root www-data 133 Oct  5 00:06 /etc/nginx/.htpasswd
```

## 3. Proteger un sitio entero

Edita `web2`, el bloque de HTTPS, y añade dos líneas dentro del `location /`:

```sh
sudo nano /etc/nginx/sites-available/web2.garcia.test
```

```nginx
    location / {
        auth_basic           "Zona privada de web2";   # (1)!
        auth_basic_user_file /etc/nginx/.htpasswd;      # (2)!
        try_files $uri $uri/ =404;
    }
```

1. Activa la autenticación. El texto es el nombre de la zona, el *realm*; algunos navegadores lo muestran en la ventana.
2. El fichero de usuarios que acabas de crear.

```sh
sudo nginx -t && sudo systemctl reload nginx
```

Entra en `https://web2.garcia.test` desde el navegador. Te pedirá usuario y contraseña.

<!-- PENDIENTE: captura de la ventana de usuario y contraseña -->

!!! tip "El navegador recuerda la contraseña"
    Una vez que entras, el navegador guarda las credenciales y no te las vuelve a pedir. Para volver a probar, abre una **ventana de incógnito** nueva.

Pruébalo también con `curl`, desde PowerShell:

```powershell
curl.exe -kI https://web2.garcia.test
curl.exe -kI -u ana:contraseña_mala https://web2.garcia.test
curl.exe -kI -u ana:tu_contraseña https://web2.garcia.test
```

```
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Basic realm="Zona privada de web2"
...
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Basic realm="Zona privada de web2"
...
HTTP/1.1 200 OK
...
```

Sin credenciales, `401` y la cabecera `WWW-Authenticate`, que es la que hace que el navegador muestre la ventana. Con una contraseña mala, otra vez `401`. Con la buena, `200`.

### Qué queda en los registros

```sh
sudo tail -n 3 /var/log/nginx/web2.access.log
sudo tail -n 2 /var/log/nginx/web2.error.log
```

```
192.168.56.1 - ana [05/Oct/2026:00:07:00 +0200] "HEAD /elements.html HTTP/1.1" 401 0 "-" "curl/8.21.0"
192.168.56.1 - ana [05/Oct/2026:00:07:01 +0200] "HEAD /elements.html HTTP/1.1" 200 0 "-" "curl/8.21.0"
192.168.56.1 - nadie [05/Oct/2026:00:07:11 +0200] "HEAD /elements.html HTTP/1.1" 401 0 "-" "curl/8.21.0"

2026/10/05 00:07:00 [error] 1857#1857: *33 user "ana": password mismatch, client: 192.168.56.1, server: web2.garcia.test, request: "HEAD /elements.html HTTP/1.1", host: "web2.garcia.test"
2026/10/05 00:07:11 [error] 1857#1857: *35 user "nadie" was not found in "/etc/nginx/.htpasswd", client: 192.168.56.1, server: web2.garcia.test, request: "HEAD /elements.html HTTP/1.1", host: "web2.garcia.test"
```

*(Estas líneas son de una prueba sobre `elements.html`, la página que protegerás en el apartado 5; en tu registro verás la ruta que hayas pedido.)*

El registro de accesos guarda ahora el **usuario** en el tercer campo, donde antes había un `-`: el que se intentó, aunque la contraseña fuera mala. El de errores dice qué ha fallado: una contraseña que no coincide (`password mismatch`) o un usuario que no existe (`was not found`).

## 4. Lo que viaja por la red

Pídele a `curl` que te enseñe lo que envía:

```sh
curl -vsk -u ana:tu_contraseña https://web2.garcia.test -o /dev/null 2>&1 | grep -i '> authorization'
```

```
> Authorization: Basic YW5hOkNsYXZlLUFuYTE=
```

Copia lo que va después de `Basic` y descodifícalo (en el ejemplo, el usuario es `ana` y la contraseña `Clave-Ana1`):

```sh
echo 'YW5hOkNsYXZlLUFuYTE=' | base64 -d; echo
```

```
ana:Clave-Ana1
```

Ahí está tu usuario y tu contraseña, legibles. Si esta petición viajara por HTTP, cualquiera que escuchara la red los tendría. Viaja dentro de TLS, y por eso no los ve nadie más que el servidor.

## 5. Proteger solo una parte

Normalmente no se protege una web entera, sino una zona. Quita las dos líneas de `auth_basic` del `location /` de `web2` y añade, debajo de él, un `location` nuevo solo para la página `elements.html`:

```nginx
    location / {
        try_files $uri $uri/ =404;
    }

    location = /elements.html {
        auth_basic           "Zona privada de web2";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
```

El `=` hace que este bloque se aplique **solo** a esa URL exacta. Recarga Nginx y compruébalo:

```powershell
curl.exe -k -o NUL -w "%{http_code}\n" https://web2.garcia.test/
curl.exe -k -o NUL -w "%{http_code}\n" https://web2.garcia.test/elements.html
```

```
200
401
```

La portada entra sin contraseña; `elements.html` la pide. En el navegador, la página **Elements** está en el menú de la plantilla.

## 6. Control de acceso por IP

Nginx también puede permitir o denegar según la IP del cliente, con `allow` y `deny`. Se evalúan **en orden** y gana la primera que coincide.

Tu ordenador, visto desde la máquina virtual, tiene la IP `192.168.56.1` (la has visto en los registros desde la práctica 2.1). Deniégale el acceso a `web1`, y deja pasar al resto:

```nginx
    location / {
        deny  192.168.56.1;
        allow all;
        try_files $uri $uri/ =404;
    }
```

Recarga y prueba **desde tu ordenador** y **desde la propia máquina virtual**:

```powershell
curl.exe -k -o NUL -w "%{http_code}\n" https://web1.garcia.test/
```

```sh
curl -sk --resolve web1.garcia.test:443:127.0.0.1 -o /dev/null -w "%{http_code}\n" https://web1.garcia.test/
```

```
403     ← desde tu ordenador
200     ← desde la propia máquina virtual
```

Desde tu ordenador, `403`. Desde la máquina, que se conecta a sí misma (`127.0.0.1`), `200`. Mira el registro de errores de `web1`: dice que el acceso está prohibido "por regla" (*by rule*).

!!! info "`--resolve`"
    La máquina virtual no tiene tu fichero `hosts`, así que no sabe que `web1.garcia.test` es ella misma. `--resolve` le dice a `curl` a qué IP conectar para ese nombre, sin tocar ningún fichero.

### Combinar IP y contraseña

Cuando un `location` tiene a la vez reglas de IP y `auth_basic`, la directiva `satisfy` decide cómo se combinan:

| `satisfy` | Se permite el acceso si… |
|---|---|
| `all` (por defecto) | La IP está permitida **y** el usuario es válido |
| `any` | La IP está permitida **o** el usuario es válido |

!!! question "Tarea"
    Configura `web1` para que desde tu ordenador haya que cumplir **las dos** condiciones a la vez: IP permitida **y** usuario válido. Comprueba que entras con tu usuario, y que te rechaza con una contraseña mala. Después cámbialo para que baste con **una** de las dos, y explica qué cambia.

    Al terminar, deja `web1` como estaba al principio de la práctica, sin restricciones.

## 7. Haz una instantánea

Apaga la máquina con `sudo poweroff` y toma la instantánea `p2.3-auth`.

---

## Cuestiones finales

!!! question "Cuestión 1"
    El cliente con IP `172.1.10.15` entra en `/web_muy_guay` y se equivoca de contraseña. ¿Puede acceder? ¿Por qué?

    ```nginx
    location /web_muy_guay {
        satisfy all;
        deny  172.1.10.6;
        allow 172.1.10.15;
        allow 172.1.3.14;
        deny  all;
        auth_basic "Cuestión 1";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
    ```

!!! question "Cuestión 2"
    El mismo cliente, con la contraseña **correcta**. ¿Puede acceder? ¿Por qué?

    ```nginx
    location /web_muy_guay {
        satisfy all;
        deny  all;
        deny  172.1.10.6;
        allow 172.1.10.15;
        allow 172.1.3.14;
        auth_basic "Cuestión 2";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
    ```

!!! question "Cuestión 3"
    El mismo cliente, con la contraseña correcta. ¿Puede acceder? ¿Por qué?

    ```nginx
    location /web_muy_guay {
        satisfy any;
        deny  172.1.10.6;
        deny  172.1.10.15;
        allow 172.1.3.14;
        auth_basic "Cuestión 3";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
    ```

!!! question "Cuestión 4"
    Un compañero dice que su web es segura porque "la contraseña va codificada en base64". ¿Qué le contestas? ¿En qué condiciones es aceptable usar autenticación básica?

!!! question "Cuestión 5"
    Pon el fichero `.htpasswd` con permisos `600` y entra en la zona protegida. ¿Qué código devuelve Nginx y qué dice el registro de errores? ¿Por qué? Deja los permisos como estaban.

## Entrega

Igual que en las prácticas anteriores: **documento de evidencias (40 %)** y **demostración en clase (60 %)**.

### Parte 1 — Documento de evidencias (40 %)

Un **PDF** llamado `P2.3-Apellido-Nombre.pdf` con portada, las evidencias (en texto, con comando y *prompt*) y las respuestas a las cuestiones.

| # | Qué hay que demostrar | Dónde | Comando cuya salida se pega |
|---|---|---|---|
| 1 | Los dos usuarios existen, con hash | Debian | `sudo cat /etc/nginx/.htpasswd` |
| 2 | Permisos del fichero de usuarios | Debian | `ls -l /etc/nginx/.htpasswd` |
| 3 | La configuración de `web2` con `elements.html` protegida | Debian | `cat /etc/nginx/sites-available/web2.tuapellido.test` |
| 4 | Sin credenciales, `401`; con ellas, `200` | Tu ordenador | Los tres `curl.exe -kI` del apartado 3, sobre `elements.html` |
| 5 | El usuario queda registrado | Debian | `sudo tail -n 5 /var/log/nginx/web2.access.log` |
| 6 | Un usuario inexistente y una contraseña mala, en el registro de errores | Debian | `sudo tail -n 5 /var/log/nginx/web2.error.log` |
| 7 | La contraseña viaja en base64 | Debian | El `curl -v` y el `base64 -d` del apartado 4 |
| 8 | Denegación por IP | Los dos | Los dos `curl` del apartado 6 (`403` y `200`) |
| 9 | La tarea de `satisfy` | Debian | La configuración del `location` con `satisfy all` y con `satisfy any`, y una frase sobre cada una |

### Parte 2 — Demostración en clase (60 %)

Mini entrevista individual en la mesa del profesor: muestras la zona protegida en una ventana de incógnito, haces la tarea que se te pida y explicas una decisión o un concepto.

### Criterios de evaluación

| Parte | Criterio | Peso |
|---|---|---|
| Documento | Las nueve evidencias están completas, en texto y explicadas | 25 % |
| Documento | Las cinco cuestiones están respondidas con corrección y criterio propio | 15 % |
| Demostración | `elements.html` pide usuario y contraseña, y el resto de la web no | 20 % |
| Demostración | Realizas la tarea que se te pide y explicas lo que haces | 20 % |
| Demostración | Explicas una decisión o un concepto con tus palabras | 20 % |

### Antes de entregar, comprueba que…

- ☐ `.htpasswd` tiene tus dos usuarios y permisos `640` con grupo `www-data`.
- ☐ Solo `elements.html` de `web2` pide contraseña.
- ☐ `web1` ha vuelto a quedar sin restricciones.
- ☐ `sudo nginx -t` no da errores.
- ☐ Existe la instantánea `p2.3-auth`.
- ☐ El archivo se llama `P2.3-Apellido-Nombre.pdf`.

## Referencias

- [Documentación de Nginx — Restringir el acceso con autenticación básica](https://docs.nginx.com/nginx/admin-guide/security-controls/configuring-http-basic-authentication/)
- [Módulo `ngx_http_access_module` (allow, deny)](https://nginx.org/en/docs/http/ngx_http_access_module.html)
- [Directiva `satisfy`](https://nginx.org/en/docs/http/ngx_http_core_module.html#satisfy)
- [MDN — Autenticación HTTP](https://developer.mozilla.org/es/docs/Web/HTTP/Guides/Authentication)
