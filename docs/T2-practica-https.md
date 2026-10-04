---
title: 'Práctica 2.2 - HTTPS en Nginx'
---

<!--
NOTA PARA EL PROFESOR (no se muestra al alumnado):

Práctica nueva. Parte del apartado "HTTPS" y "Redirección HTTP a HTTPS" del P1.1.md original (que solo decía
"apoyaos en una búsqueda en Internet") y de la parte de certificados de old.P1.5.md. Cambios:
  - Guiada paso a paso, sobre los dos sitios de la P2.1 (web1/web2.apellido.test), en la máquina principal .10.
  - Un certificado POR SITIO, con subjectAltName (los navegadores actuales ignoran el CN: sin SAN el certificado
    falla aunque aceptes la excepción). Clave RSA 2048 (Chrome no acepta certificados Ed25519).
  - openssl s_client para ver TLS 1.3, el grupo de intercambio (X25519 = Diffie-Hellman efímero, enlaza con la
    teoría) y SNI en acción (-servername web1/web2 devuelve certificados distintos).
  - http2 on (sintaxis de nginx >= 1.25.1; la antigua "listen 443 ssl http2" da aviso de obsoleta).
  - Redirección con return 301 https://$host$request_uri en un server block aparte.
  - Sin HSTS a propósito: con un certificado autofirmado, HSTS impide aceptar la excepción del navegador.

VALIDADA el 05/10/2026 (VM Debian 13.7, nginx 1.26.3, OpenSSL 3.5.7, curl 8.21 de Windows, Chrome 154).
  OpenSSL 3.5 negocia el grupo híbrido post-cuántico X25519MLKEM768: explicado en un recuadro.
  El curl.exe de Windows (Schannel) habla HTTP/1.1; el navegador, HTTP/2 (se ve en el registro).
PENDIENTE: capturas del aviso del navegador y del visor de certificados (las hará el profesor con su VM).
-->

# Práctica 2.2 - HTTPS en Nginx

!!! tip "Cuándo se hace"
    Al terminar el **bloque 3** de la [teoría del Tema 2](T2-arquitectura-web.md) (apartado 8, HTTPS), con la [práctica 2.1](T2-practica-nginx.md) terminada.

!!! abstract "Objetivos"
    Al terminar esta práctica deberás ser capaz de:

    1. Generar un certificado autofirmado y su clave privada con `openssl`, y leer lo que contiene.
    2. Configurar un sitio de Nginx para que sirva por HTTPS.
    3. Redirigir automáticamente las peticiones HTTP a HTTPS.
    4. Comprobar el saludo TLS desde la terminal: versión, intercambio de claves y certificado.
    5. Explicar por qué el navegador avisa con un certificado autofirmado y qué significa aceptar la excepción.

!!! info "Antes de empezar"
    - Tu máquina principal (`192.168.56.10`) tiene la práctica 2.1 funcionando: `web1` y `web2` responden por su nombre.
    - Tienes la instantánea `p2.1-nginx`. Si algo se rompe sin remedio, vuelves a ella.

    En los ejemplos aparece `garcia`: escribe **tu** apellido en todos los comandos y ficheros.

---

## 1. Dónde van los certificados

Cada sitio HTTPS necesita dos ficheros:

| Fichero | Qué es | ¿Secreto? |
|---|---|---|
| `web1.garcia.test.crt` | El **certificado**: la clave pública del sitio, su nombre y quién lo firma | No. Se envía a todo el que se conecta |
| `web1.garcia.test.key` | La **clave privada** del certificado | **Sí.** Si alguien la obtiene, puede hacerse pasar por tu sitio |

Crea una carpeta para ellos que solo pueda leer `root`:

```sh
sudo mkdir -p /etc/nginx/ssl
sudo chmod 700 /etc/nginx/ssl
```

Nginx puede leerla aunque sus trabajadores sean `www-data`: los certificados los lee el **proceso maestro**, que se ejecuta como `root` (lo viste en el apartado 6 de la teoría).

## 2. Generar un certificado autofirmado

Genera el certificado y la clave de `web1` con un solo comando (es una sola orden partida en varias líneas: cópiala entera):

```sh
sudo openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
  -keyout /etc/nginx/ssl/web1.garcia.test.key \
  -out /etc/nginx/ssl/web1.garcia.test.crt \
  -subj "/C=ES/O=2DAW/OU=Despliegue - Garcia/CN=web1.garcia.test" \
  -addext "subjectAltName=DNS:web1.garcia.test"
```

| Opción | Qué hace |
|---|---|
| `req -x509` | Crea un certificado **autofirmado**, en lugar de una solicitud para que lo firme una CA |
| `-newkey rsa:2048` | Genera a la vez una clave privada nueva, RSA de 2048 bits |
| `-nodes` | No cifra la clave privada con contraseña. Si la tuviera, Nginx no podría arrancar solo: te la pediría en cada reinicio |
| `-days 365` | El certificado caduca en un año |
| `-keyout` / `-out` | Dónde guardar la clave privada y el certificado |
| `-subj` | Los datos del titular: país, organización, unidad y **nombre común** (`CN`) |
| `-addext "subjectAltName=…"` | Los nombres para los que vale el certificado. **Los navegadores actuales solo miran este campo**: sin él, el certificado no vale para tu dominio aunque el `CN` coincida |

Repite el comando para `web2`, cambiando `web1` por `web2` en las **cuatro** líneas en las que aparece.

Comprueba que tienes los cuatro ficheros:

```sh
sudo ls -l /etc/nginx/ssl
```

```
total 16
-rw-r--r-- 1 root root 1330 Oct  5 00:05 web1.garcia.test.crt
-rw------- 1 root root 1704 Oct  5 00:05 web1.garcia.test.key
-rw-r--r-- 1 root root 1330 Oct  5 00:05 web2.garcia.test.crt
-rw------- 1 root root 1704 Oct  5 00:05 web2.garcia.test.key
```

### Qué hay dentro de un certificado

```sh
sudo openssl x509 -in /etc/nginx/ssl/web1.garcia.test.crt -noout -subject -issuer -dates -ext subjectAltName
```

```
subject=C=ES, O=2DAW, OU=Despliegue - Garcia, CN=web1.garcia.test
issuer=C=ES, O=2DAW, OU=Despliegue - Garcia, CN=web1.garcia.test
notBefore=Oct  4 22:05:58 2026 GMT
notAfter=Oct  4 22:05:58 2027 GMT
X509v3 Subject Alternative Name:
    DNS:web1.garcia.test
```

Fíjate en que **`subject` e `issuer` son iguales**: el titular del certificado y quien lo firma son la misma persona, tú. Eso es exactamente lo que significa "autofirmado", y es la razón por la que el navegador no se va a fiar.

## 3. Configurar HTTPS en el sitio

Edita la configuración de `web1`:

```sh
sudo nano /etc/nginx/sites-available/web1.garcia.test
```

Vas a dejarla con **dos** bloques `server`: uno que solo redirige lo que llega por HTTP, y otro que sirve la web por HTTPS. Quedará así (cambia `garcia` por tu apellido):

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name web1.garcia.test;

    access_log /var/log/nginx/web1.access.log;

    return 301 https://$host$request_uri;  # (1)!
}

server {
    listen 443 ssl;                          # (2)!
    listen [::]:443 ssl;
    http2 on;                                # (3)!

    server_name web1.garcia.test;

    ssl_certificate     /etc/nginx/ssl/web1.garcia.test.crt;   # (4)!
    ssl_certificate_key /etc/nginx/ssl/web1.garcia.test.key;

    root /var/www/web1.garcia.test/html;
    index index.html;

    access_log /var/log/nginx/web1.access.log;
    error_log  /var/log/nginx/web1.error.log;

    location / {
        try_files $uri $uri/ =404;
    }

    location ~ /\.git {
        deny all;
    }
}
```

1. Responde `301 Moved Permanently` y manda al cliente a la misma dirección, pero con `https://`. `$host` es el nombre que pidió y `$request_uri` la ruta: `http://web1.garcia.test/css/a.css` pasa a `https://web1.garcia.test/css/a.css`.
2. Escucha en el puerto 443 y activa TLS en él.
3. Permite HTTP/2. Como viste en la teoría, los navegadores solo lo usan sobre HTTPS.
4. El certificado y la clave privada de **este** sitio.

El segundo bloque es tu configuración de la práctica 2.1, con tres cambios: el puerto, la línea `http2` y las dos líneas del certificado.

Haz lo mismo con `web2`, con sus propios ficheros de certificado. Después, comprueba y recarga:

```sh
sudo nginx -t && sudo systemctl reload nginx
```

Y comprueba que Nginx escucha ahora también en el 443:

```sh
sudo ss -tlnp | grep nginx
```

```
LISTEN 0  511  0.0.0.0:80   0.0.0.0:*  users:(("nginx",pid=1611,fd=5),("nginx",pid=1610,fd=5),("nginx",pid=1522,fd=5))
LISTEN 0  511  0.0.0.0:443  0.0.0.0:*  users:(("nginx",pid=1611,fd=21),("nginx",pid=1610,fd=21),("nginx",pid=1522,fd=21))
LISTEN 0  511     [::]:80      [::]:*  users:(...)
LISTEN 0  511     [::]:443     [::]:*  users:(...)
```

## 4. Probar desde tu ordenador

### La redirección

```powershell
curl.exe -I http://web1.garcia.test
```

```
HTTP/1.1 301 Moved Permanently
Server: nginx
Date: Sun, 04 Oct 2026 22:06:05 GMT
Content-Type: text/html
Content-Length: 162
Connection: keep-alive
Location: https://web1.garcia.test/
```

El servidor responde `301` y la cabecera `Location` dice adónde ir.

### HTTPS con `curl`

```powershell
curl.exe -I https://web1.garcia.test
```

```
curl: (60) schannel: SEC_E_UNTRUSTED_ROOT (0x80090325) - The certificate chain was issued by an authority that is not trusted.
```

`curl` se niega: no conoce a quien ha firmado el certificado. Es el comportamiento correcto. Para probar a pesar de ello, la opción `-k` le dice que no compruebe el certificado (**solo** para pruebas con certificados propios):

```powershell
curl.exe -kI https://web1.garcia.test
```

```
HTTP/1.1 200 OK
Server: nginx
Content-Type: text/html
Content-Length: 14522
```

### HTTPS en el navegador

Entra en `http://web1.garcia.test`. El navegador te llevará solo a `https://` y te mostrará un aviso a pantalla completa: **"La conexión no es privada"**.

<!-- PENDIENTE: captura del aviso -->

El aviso dice exactamente lo que ya sabes: el certificado no lo firma ninguna autoridad en la que el navegador confíe. Como lo has generado tú y sabes que es tuyo, puedes continuar: **Configuración avanzada → Acceder a web1.garcia.test (sitio no seguro)**.

Ya dentro, pulsa en el icono de la izquierda de la barra de direcciones y abre los datos del certificado. Comprueba que son los tuyos: el nombre del sitio, tu apellido en la unidad organizativa y las fechas de validez.

<!-- PENDIENTE: captura del visor de certificados -->

!!! warning "En el mundo real, nunca"
    Aceptar la excepción tiene sentido aquí porque **tú** has creado el certificado. En una web ajena, ese aviso puede significar que alguien se ha puesto en medio de tu conexión. Es el mismo caso que la huella de SSH de la práctica 1.1: si no sabes por qué cambia, no continúes.

## 5. El saludo TLS, visto desde dentro

`openssl s_client` hace de cliente TLS y te enseña lo que se negocia. Desde la sesión SSH de tu máquina:

```sh
openssl s_client -connect localhost:443 -servername web1.garcia.test </dev/null 2>/dev/null | grep -E '^subject|^issuer|Protocol|Cipher is|Negotiated TLS1.3 group'
```

```
subject=C=ES, O=2DAW, OU=Despliegue - Garcia, CN=web1.garcia.test
issuer=C=ES, O=2DAW, OU=Despliegue - Garcia, CN=web1.garcia.test
Protocol: TLSv1.3
Negotiated TLS1.3 group: X25519MLKEM768
New, TLSv1.3, Cipher is TLS_AES_256_GCM_SHA384
```

| Línea | Qué te dice | Dónde está en la teoría |
|---|---|---|
| `Protocol: TLSv1.3` | La versión negociada | El saludo TLS 1.3 |
| `Negotiated TLS1.3 group` | El algoritmo de **Diffie-Hellman efímero** con el que se ha acordado la clave | Lo que ya sabes de SSH |
| `Cipher is` | El cifrado **simétrico** que protege los datos | Cifrado simétrico para todo lo demás |
| `subject` / `issuer` | El certificado que ha presentado el servidor | Certificados |

!!! info "`X25519MLKEM768`: un intercambio de claves para el futuro"
    El grupo negociado combina dos algoritmos: **X25519**, el Diffie-Hellman efímero sobre curvas elípticas que viste en la teoría, y **ML-KEM**, un algoritmo nuevo diseñado para resistir a los futuros ordenadores cuánticos. Si algún día se rompiera uno de los dos, el otro seguiría protegiendo la clave. Las versiones recientes de OpenSSL y de los navegadores ya lo usan por defecto.

### SNI: un certificado para cada nombre

Las dos webs están en la misma IP y el mismo puerto 443. ¿Cómo sabe Nginx qué certificado enviar, si todavía no ha visto la cabecera `Host`? Porque el cliente lo anuncia en el primer mensaje del saludo (SNI). La opción `-servername` es justo eso:

```sh
openssl s_client -connect localhost:443 -servername web2.garcia.test </dev/null 2>/dev/null | grep '^subject'
openssl s_client -connect localhost:443 -noservername </dev/null 2>/dev/null | grep '^subject'
```

```
subject=C=ES, O=2DAW, OU=Despliegue - Garcia, CN=web2.garcia.test
subject=C=ES, O=2DAW, OU=Despliegue - Garcia, CN=web1.garcia.test
```

Con `web2` llega el certificado de `web2`. Sin nombre (`-noservername`), Nginx no sabe qué sitio quieres y presenta el del sitio por defecto del puerto 443.

## 6. Los registros

Entra en `http://web1.garcia.test` desde el navegador (con `http://`) y mira el registro:

```sh
sudo tail -n 3 /var/log/nginx/web1.access.log
```

```
192.168.56.1 - - [05/Oct/2026:00:06:18 +0200] "GET / HTTP/1.1" 301 162 "-" "Mozilla/5.0 (...)"
192.168.56.1 - - [05/Oct/2026:00:06:18 +0200] "GET / HTTP/2.0" 200 3875 "-" "Mozilla/5.0 (...)"
```

Primero la petición que llegó por HTTP y recibió el `301`; después la que llegó por HTTPS y recibió el `200`. Fíjate en la versión: la primera es `HTTP/1.1` y la segunda `HTTP/2.0`. En cuanto hay cifrado, el navegador pasa a HTTP/2.

## 7. Haz una instantánea

```sh
sudo poweroff
```

En VirtualBox, toma la instantánea `p2.2-https`.

---

## Cuestiones finales

!!! question "Cuestión 1"
    ¿Por qué el navegador avisa con tu certificado si cifra exactamente igual de bien que uno de Let's Encrypt? ¿Qué tendrías que hacer para que tu navegador dejara de avisar, y por qué no sirve para los visitantes de una web pública?

!!! question "Cuestión 2"
    Tu clave privada está en `/etc/nginx/ssl` con permisos `700`. ¿Qué podría hacer alguien que la copiara? ¿Y si copiara solo el `.crt`?

!!! question "Cuestión 3"
    En el resultado de `openssl s_client`, ¿qué línea corresponde al Diffie-Hellman efímero de la teoría, y cuál al cifrado simétrico? ¿Por qué hacen falta los dos?

!!! question "Cuestión 4"
    Explica qué es SNI con el resultado de la prueba del apartado 5. ¿Qué pasaría con tus dos webs si los clientes no enviaran el nombre?

!!! question "Cuestión 5"
    ¿Por qué la redirección usa el código `301` y no `200`? ¿Qué hace el navegador con la cabecera `Location`?

## Entrega

Igual que en las prácticas anteriores: **documento de evidencias (40 %)** y **demostración en clase (60 %)**.

### Parte 1 — Documento de evidencias (40 %)

Un **PDF** llamado `P2.2-Apellido-Nombre.pdf` con portada, las evidencias de la tabla (en texto, con el comando y el *prompt*) y las respuestas a las cuestiones.

| # | Qué hay que demostrar | Dónde | Comando cuya salida se pega |
|---|---|---|---|
| 1 | Los certificados y claves existen, y la carpeta está protegida | Debian | `sudo ls -la /etc/nginx/ssl` |
| 2 | El certificado de `web1` es tuyo y autofirmado | Debian | `sudo openssl x509 -in /etc/nginx/ssl/web1.tuapellido.test.crt -noout -subject -issuer -dates -ext subjectAltName` |
| 3 | La configuración de `web1` con los dos bloques | Debian | `cat /etc/nginx/sites-available/web1.tuapellido.test` |
| 4 | La configuración es correcta | Debian | `sudo nginx -t` |
| 5 | Nginx escucha en 80 y 443 | Debian | `sudo ss -tlnp` (las líneas de `nginx`) |
| 6 | HTTP redirige a HTTPS en los dos sitios | Tu ordenador | `curl.exe -I http://web1.tuapellido.test` y lo mismo con `web2` |
| 7 | HTTPS responde en los dos sitios | Tu ordenador | `curl.exe -kI https://web1.tuapellido.test` y lo mismo con `web2` |
| 8 | TLS 1.3 y SNI | Debian | Los dos `openssl s_client` del apartado 5, con `web1` y con `web2` |
| 9 | El registro muestra la redirección | Debian | `sudo tail -n 3 /var/log/nginx/web1.access.log` (un `301` seguido de un `200`) |
| 10 | El certificado en el navegador | Tu ordenador | **Captura** del visor de certificados con tus datos |

Cada evidencia, con **una frase tuya** explicando qué demuestra.

### Parte 2 — Demostración en clase (60 %)

Mini entrevista individual en la mesa del profesor, con tu ordenador:

1. Abres `http://web1.tuapellido.test` en el navegador y muestras que acaba en HTTPS con tu certificado.
2. Haces la tarea que se te pida en ese momento.
3. Explicas en voz alta una de tus decisiones o uno de los conceptos de la práctica.

!!! info "Cómo se califica"
    **Una demostración que no funciona no se compensa con un documento impecable**: la práctica queda pendiente hasta que funcione.

### Criterios de evaluación

| Parte | Criterio | Peso |
|---|---|---|
| Documento | Las diez evidencias están completas, en texto (salvo la captura) y explicadas | 25 % |
| Documento | Las cinco cuestiones están respondidas con corrección y criterio propio | 15 % |
| Demostración | Los dos sitios sirven por HTTPS con su certificado y HTTP redirige | 20 % |
| Demostración | Realizas la tarea que se te pide y explicas lo que haces | 20 % |
| Demostración | Explicas una decisión o un concepto con tus palabras | 20 % |

### Antes de entregar, comprueba que…

- ☐ `http://web1.tuapellido.test` y `http://web2.tuapellido.test` terminan en `https://`.
- ☐ Cada sitio presenta **su** certificado, con tu apellido en la unidad organizativa.
- ☐ `/etc/nginx/ssl` tiene permisos `700` y las claves no salen de ahí.
- ☐ `sudo nginx -t` no da errores.
- ☐ Existe la instantánea `p2.2-https`.
- ☐ El archivo se llama `P2.2-Apellido-Nombre.pdf`.

## Referencias

- [Documentación de Nginx — Configurar servidores HTTPS](https://nginx.org/en/docs/http/configuring_https_servers.html)
- [OpenSSL — `req`](https://docs.openssl.org/master/man1/openssl-req/) y [`s_client`](https://docs.openssl.org/master/man1/openssl-s_client/)
- [MDN — Strict-Transport-Security (HSTS)](https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Headers/Strict-Transport-Security), para cuando tengas un certificado de verdad
