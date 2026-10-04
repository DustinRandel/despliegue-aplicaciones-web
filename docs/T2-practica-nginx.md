---
title: 'Práctica 2.1 - Servidor web Nginx'
---

<!--
NOTA PARA EL PROFESOR (no se muestra al alumnado):

Reescrita a partir de P1.1.md del repo original ("Pràctica 2.1"). Cambios respecto al original:
  - Fuera de esta práctica: HTTPS y redirección 80->443. Pasan a la P2.2 (guiada). Orden previsto:
    2.2 HTTPS, 2.3 autenticación (ya sobre HTTPS: la básica manda la contraseña en base64),
    2.4 proxy inverso, 2.5 balanceo. Parten de old.P1.2 a old.P1.5.
  - Fuera las referencias a AWS/EC2 e IP pública. Se trabaja sobre la VM de la P1.1 (Host-only 192.168.56.10).
  - Dominios con TLD .test (reservado por la RFC 6761, nunca existirá en Internet) y con el apellido:
    web1.tuapellido.test y web2.tuapellido.test. Firman la entrega igual que el hostname.
    NO usar .dev (es un TLD real con HSTS precargado: el navegador fuerza HTTPS) ni .local (mDNS).
  - Propietario de /var/www/<sitio>: el usuario del alumno, NO www-data (el original hacía chown www-data
    y chmod -R 755 a todo). Mínimo privilegio, y además así SFTP sube directamente sin sudo.
    Permisos con chmod -R u=rwX,go=rX (carpetas 755, ficheros 644).
  - NUEVO apartado 5: el .git clonado queda expuesto (http://web1.../.git/config devuelve 200 con la URL
    del repo). Es un fallo real y frecuente. Se cierra con location ~ /\.git { deny all; } -> 403.
  - Segundo sitio: plantilla "Phantom" de HTML5 UP (CC BY 3.0), descarga html5up-phantom.zip, con el
    index.html en la raíz del zip (unzip -d html funciona sin mover nada). El original hablaba de un .zip
    "que os he proporcionado" que no estaba en el repo.
  - SFTP: FileZilla (con clave, porque en la P1.1 se desactivó la contraseña) o sftp/scp de OpenSSH.
  - Logs por sitio (web1.access.log...), y diagnóstico guiado de 404 y de 403 por permisos.
  - Añadidos objetivos, cuestiones, entrega 40/60 con mini entrevista, criterios y checklist (como P1.1).

VALIDADA DE PRINCIPIO A FIN el 04/10/2026 en una VM importada de DAW-debian.ova
  (Debian 13.7, kernel 6.12, nginx 1.26.3), desde el Windows anfitrión (curl 8.21, Chrome).
  Hallazgos de la validación:
  - git, unzip y curl NO vienen instalados en la Debian de la P1.1: se instalan en el paso 1.
  - Debian 13 trae umask 002: lo clonado sale 775/664. El chmod u=rwX,go=rX lo deja en 755/644.
  - El usuario no está en el grupo adm: los logs de /var/log/nginx necesitan sudo.
  - Un 404 con try_files NO deja línea en error.log (solo en access.log). Un 403 por permisos sí
    ("Permission denied"). Un 403 por "deny" deja "access forbidden by rule".
  - reload con la configuración rota falla y Nginx sigue sirviendo la anterior (comprobado).
  - Si se borra el enlace "default", por IP responde web1 (primer server cargado).
  - P1.1: "hostnamectl set-hostname" sin tocar /etc/hosts provoca "sudo: unable to resolve host".
    Corregido también en la P1.1 (paso 3 y recuadro de la máquina de respaldo).
  - Justo tras un reload, una petición inmediata puede llegar aún a los workers viejos (milisegundos).

PENDIENTE: capturas de FileZilla (Gestor de sitios con "Archivo de claves" y la transferencia). El texto
  describe los menús de FileZilla 3.x en español; conviene revisarlos con la versión del aula.
AULA: editar el hosts de Windows exige ser administrador. Si en los PC del aula no lo son, que lo hagan en
  su portátil, o que usen curl.exe -H "Host: ..." / --resolve (apartado 3.4), que no necesita permisos.
-->

# Práctica 2.1 - Servidor web Nginx: sitios virtuales y transferencia por SFTP

!!! abstract "Objetivos"
    Al terminar esta práctica deberás ser capaz de:

    1. Instalar el servidor web Nginx y comprobar que funciona.
    2. Configurar **dos sitios virtuales** en el mismo servidor, cada uno con su nombre de dominio.
    3. Publicar una web clonándola de un repositorio Git, y otra subiéndola por **SFTP**.
    4. Asignar propietarios y permisos correctos a los ficheros de una web.
    5. Detectar y corregir un fallo de seguridad real: la exposición de la carpeta `.git`.
    6. Diagnosticar problemas con los registros (*logs*) de Nginx.

!!! info "Antes de empezar"
    - Tienes la **práctica 1.1** terminada: la máquina virtual con IP `192.168.56.10` y acceso por SSH con clave.
    - La máquina tiene **acceso a Internet** (adaptador NAT).
    - En tu ordenador tienes **permisos de administrador**, que harán falta para editar el fichero `hosts` (apartado 4).

    Todos los comandos de la Debian se ejecutan **desde tu sesión SSH**, nunca desde la ventana de VirtualBox.

### Tus nombres de dominio

En esta práctica crearás dos sitios web, y sus nombres llevan tu apellido, igual que el *hostname*:

```
web1.tuapellido.test
web2.tuapellido.test
```

en minúsculas, sin acentos y sin la ñ (por ejemplo, `web1.garcia.test`). En los ejemplos de esta página aparece `garcia`: **tú escribe el tuyo** en todos los comandos y ficheros.

!!! info "¿Por qué `.test`?"
    `.test` es un dominio de primer nivel **reservado** para pruebas ([RFC 6761](https://www.rfc-editor.org/rfc/rfc6761)): nunca existirá en Internet, así que no chocarás con ninguna web real. No uses `.dev`, que sí existe y obliga al navegador a usar HTTPS, ni `.local`, que tiene un uso especial en las redes locales.

---

## 1. Instalar Nginx

Actualiza la lista de paquetes e instala Nginx, junto con tres herramientas que necesitarás y que no vienen en la instalación mínima de Debian:

```sh
sudo apt update
sudo apt install nginx git unzip curl
```

Nginx arranca solo al instalarse y queda habilitado para arrancar con la máquina. Compruébalo:

```sh
systemctl status nginx
```

Debe aparecer `active (running)` y, en la línea `Loaded`, `enabled`. Sal de la vista con **q**.

Comprueba también que escucha en el puerto 80, y la versión instalada:

```sh
sudo ss -tlnp | grep nginx
nginx -v
```

```
LISTEN 0      511          0.0.0.0:80        0.0.0.0:*    users:(("nginx",pid=1911,fd=5),("nginx",pid=1908,fd=5),("nginx",pid=1087,fd=5))
LISTEN 0      511             [::]:80           [::]:*    users:(("nginx",pid=1911,fd=6),("nginx",pid=1908,fd=6),("nginx",pid=1087,fd=6))
nginx version: nginx/1.26.3
```

Por último, abre el navegador de **tu ordenador** y entra en `http://192.168.56.10`. Verás la página de bienvenida de Nginx:

![](img/T2-nginx-default.png)

!!! question "Comprueba antes de seguir"
    Si el navegador no carga la página, revisa en este orden: que la máquina esté encendida, que respondas al `ping 192.168.56.10` desde PowerShell y que `systemctl status nginx` diga `active`. Es el mismo orden que seguirás siempre que algo no cargue: **¿está la máquina?, ¿está el servicio?, ¿escucha en el puerto?**

## 2. Un vistazo a la configuración

Antes de tocar nada, mira cómo está organizada la configuración (lo tienes explicado en el apartado 7 de la teoría):

```sh
ls /etc/nginx
ls -l /etc/nginx/sites-available/ /etc/nginx/sites-enabled/
```

```
/etc/nginx/sites-available/:
-rw-r--r-- 1 root root 2412 Jun 27 22:25 default

/etc/nginx/sites-enabled/:
lrwxrwxrwx 1 root root   34 Oct  4 19:43 default -> /etc/nginx/sites-available/default
```

En `sites-available` está el fichero `default`, que es el sitio que acabas de ver en el navegador. En `sites-enabled` hay un **enlace simbólico** que apunta a él (la `l` del principio y la flecha `->`): por eso está activo.

Mira cómo es ese sitio, sin los comentarios:

```sh
grep -vE '^\s*#|^\s*$' /etc/nginx/sites-available/default
```

```nginx
server {
	listen 80 default_server;
	listen [::]:80 default_server;
	root /var/www/html;
	index index.html index.htm index.nginx-debian.html;
	server_name _;
	location / {
		try_files $uri $uri/ =404;
	}
}
```

Fíjate en `default_server`: es el sitio que responde cuando una petición no va dirigida a ningún otro. El fichero que has visto en el navegador es `/var/www/html/index.nginx-debian.html`.

**No vamos a modificar este fichero.** Cada sitio nuevo tendrá su propio fichero de configuración.

## 3. Primer sitio: `web1`, desde un repositorio Git

### 3.1 La carpeta y el contenido

Crea la carpeta del sitio y haz que **tu usuario** sea su propietario:

```sh
sudo mkdir -p /var/www/web1.garcia.test
sudo chown -R $USER:$USER /var/www/web1.garcia.test
```

`$USER` es una variable que contiene tu nombre de usuario, así que no tienes que escribirlo.

Ahora clona dentro, en la subcarpeta `html`, una web de ejemplo. Como la carpeta es tuya, **no necesitas `sudo`**:

```sh
git clone https://github.com/cloudacademy/static-website-example /var/www/web1.garcia.test/html
```

Y deja los permisos bien definidos:

```sh
chmod -R u=rwX,go=rX /var/www/web1.garcia.test
ls -la /var/www/web1.garcia.test/html
```

Ese `chmod` significa: el propietario (`u`) puede leer y escribir; el grupo y el resto (`go`), solo leer. La `X` **mayúscula** da permiso de ejecución **solo a las carpetas**, que lo necesitan para poder entrar en ellas. El resultado son carpetas con `755` (`drwxr-xr-x`) y ficheros con `644` (`-rw-r--r--`).

!!! warning "¿Por qué no `www-data` como propietario?"
    Muchos tutoriales, y la versión anterior de esta práctica, hacen `chown www-data:www-data` sobre la web. **No lo hagas.** Nginx se ejecuta como `www-data` y solo necesita **leer** los ficheros. Si `www-data` fuera el dueño, también podría modificarlos, y un fallo en el servidor permitiría a un atacante cambiar tu web. El dueño eres tú; `www-data` lee gracias a los permisos del "resto" (`r-x` en las carpetas y `r--` en los ficheros). Es el principio de **mínimo privilegio**.

### 3.2 El fichero de configuración del sitio

Crea el fichero del sitio en `sites-available`. Es costumbre llamarlo igual que el dominio:

```sh
sudo nano /etc/nginx/sites-available/web1.garcia.test
```

Con este contenido (cambia `garcia` en las cuatro líneas en las que aparece):

```nginx
server {
    listen 80;
    listen [::]:80;

    server_name web1.garcia.test;

    root /var/www/web1.garcia.test/html;
    index index.html;

    access_log /var/log/nginx/web1.access.log;
    error_log  /var/log/nginx/web1.error.log;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

| Directiva | Qué hace |
|---|---|
| `listen 80;` / `listen [::]:80;` | Escucha en el puerto 80, por IPv4 y por IPv6 |
| `server_name` | El nombre del sitio. Nginx lo compara con la cabecera `Host` de cada petición |
| `root` | La carpeta donde está la web: la que contiene el `index.html` |
| `index` | Qué fichero servir cuando se pide una carpeta, como `/` |
| `access_log` / `error_log` | Registros propios de este sitio, separados de los generales |
| `try_files $uri $uri/ =404;` | Busca un fichero con ese nombre; si no, una carpeta; si no, responde `404` |

!!! tip "Si trabajas con VS Code"
    Con la extensión **Remote - SSH** (la viste en la práctica 1.1) puedes abrir y editar estos ficheros con el editor de VS Code, con colores. Para guardar los que pertenecen a `root`, VS Code te ofrecerá reintentar con `sudo`.

### 3.3 Activar el sitio

Para activarlo, crea el enlace simbólico en `sites-enabled`:

```sh
sudo ln -s /etc/nginx/sites-available/web1.garcia.test /etc/nginx/sites-enabled/
```

Comprueba que la configuración no tiene errores y, solo si está bien, recárgala:

```sh
sudo nginx -t && sudo systemctl reload nginx
```

```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

!!! danger "`nginx -t` antes de aplicar. Siempre."
    Si te equivocas, `nginx -t` te dice **qué** está mal y **en qué línea**. Por ejemplo, si te dejas el `;` al final de `root`:

    ```
    nginx: [emerg] invalid number of arguments in "root" directive in /etc/nginx/sites-enabled/web1.garcia.test:8
    nginx: configuration file /etc/nginx/nginx.conf test failed
    ```

    Con `reload`, si la configuración es incorrecta, Nginx sigue funcionando con la anterior. Con `restart`, se para y no vuelve a arrancar. Por eso usamos `nginx -t && reload`: el `&&` solo recarga si la comprobación ha ido bien.

### 3.4 Probar el sitio sin DNS

Tu ordenador todavía no sabe que `web1.garcia.test` es `192.168.56.10`. Pero recuerda cómo elige Nginx el sitio: por la cabecera `Host`. Puedes enviarla tú a mano con `curl`. Desde **PowerShell, en tu ordenador**:

```powershell
curl.exe -s http://192.168.56.10/ | Select-String "<title>"
curl.exe -s -H "Host: web1.garcia.test" http://192.168.56.10/ | Select-String "<title>"
```

```
<title>Welcome to nginx!</title>
		<title>Welcome</title>
```

**Misma IP, mismo puerto, respuestas distintas.** Sin la cabecera, `curl` envía `Host: 192.168.56.10`, que no coincide con ningún `server_name`, y responde el sitio por defecto. Con la cabecera, responde tu sitio. Esto es exactamente lo que es un *virtual host*.

!!! info "`curl.exe`, no `curl`"
    Escribe la extensión `.exe`. En Windows PowerShell, `curl` a secas es un alias de `Invoke-WebRequest`, un comando distinto que no entiende estas opciones.

## 4. Resolver los nombres: el fichero `hosts`

Para usar el navegador hace falta que tu ordenador traduzca el nombre a la IP. De eso se encarga el DNS, que montarás en el Tema 4. Mientras tanto, lo haremos **a mano** con el fichero `hosts`, que el sistema consulta **antes** que el DNS.

=== "Windows"

    Editar este fichero requiere permisos de administrador. Pulsa **Win + X** y elige **Terminal (Administrador)** (o **Windows PowerShell (Administrador)**). En esa ventana:

    ```powershell
    notepad C:\Windows\System32\drivers\etc\hosts
    ```

    Al final del fichero, añade una línea con tus dos nombres:

    ```
    192.168.56.10    web1.garcia.test    web2.garcia.test
    ```

    Guarda (**Ctrl+S**) y cierra el Bloc de notas. Si al guardar te dice que no tienes permiso, es que no lo abriste desde una terminal de administrador.

=== "Linux / macOS"

    ```sh
    sudo nano /etc/hosts
    ```

    Y añade al final:

    ```
    192.168.56.10    web1.garcia.test    web2.garcia.test
    ```

Ya puedes añadir el segundo nombre aunque todavía no exista el sitio: lo crearás en el apartado 6.

Comprueba que el nombre se resuelve:

```powershell
ping web1.garcia.test
```

```
Haciendo ping a web1.garcia.test [192.168.56.10] con 32 bytes de datos:
Respuesta desde 192.168.56.10: bytes=32 tiempo<1m TTL=64
```

Ahora abre el navegador y escribe la dirección **completa, con `http://`**:

```
http://web1.garcia.test
```

![](img/T2-web1.jpg)

!!! tip "Si el navegador no te lleva a tu web"
    - **Escribe siempre `http://`.** Sin él, el navegador puede pensar que `web1.garcia.test` es una búsqueda y mandarte a Google.
    - Si te redirige a `https://` y falla, es una función de seguridad del navegador: vuelve a escribir `http://` o prueba en una **ventana de incógnito**.
    - Si ves la página de bienvenida de Nginx en vez de tu web, la petición no coincide con tu `server_name`: revisa que el nombre del fichero `hosts` y el de la configuración sean idénticos.

!!! warning "Si no tienes permisos de administrador"
    Sin ellos no puedes editar el fichero `hosts`. Puedes hacer todas las comprobaciones con `curl.exe -H "Host: ..."` como en el apartado 3.4, pero la evidencia del navegador tendrás que hacerla en un equipo donde sí los tengas (tu portátil, por ejemplo).

## 5. Un fallo de seguridad real: la carpeta `.git`

Has publicado la web clonando un repositorio, y `git clone` no solo descarga la web: también crea la carpeta **`.git`**, con **toda la historia del repositorio**. Y está dentro de `root`, así que… prueba desde PowerShell:

```powershell
curl.exe http://web1.garcia.test/.git/config
```

```
[core]
	repositoryformatversion = 0
	filemode = true
	bare = false
	logallrefupdates = true
[remote "origin"]
	url = https://github.com/cloudacademy/static-website-example
	fetch = +refs/heads/*:refs/remotes/origin/*
[branch "master"]
	remote = origin
	merge = refs/heads/master
```

**Tu servidor está regalando el repositorio.** Con herramientas automáticas, cualquiera puede descargar la carpeta `.git` entera y reconstruir todo el código fuente, incluidas las versiones antiguas. Si alguna vez se subió al repositorio una contraseña o una clave, aunque luego se borrara, sigue en la historia. No es un caso de laboratorio: es uno de los fallos más frecuentes en webs reales, y los robots que rastrean Internet lo buscan a diario.

Ciérralo. Edita la configuración del sitio:

```sh
sudo nano /etc/nginx/sites-available/web1.garcia.test
```

Y añade este bloque **dentro** del bloque `server`, después del `location /`:

```nginx
    location ~ /\.git {
        deny all;
    }
```

`location ~` indica que lo que sigue es una **expresión regular**: se aplica a cualquier URL que contenga `/.git`. Y `deny all` prohíbe el acceso a todo el mundo.

```sh
sudo nginx -t && sudo systemctl reload nginx
```

Vuelve a probar con `curl.exe` y en el navegador. Ahora el servidor responde **`403 Forbidden`**:

![](img/T2-git-403.png)

!!! info "En un despliegue profesional"
    Lo correcto es que la carpeta `.git` ni siquiera llegue al servidor, o que la web publicada esté fuera del repositorio. Lo verás cuando automatices los despliegues en el Tema 7. La regla `deny` es una red de seguridad que conviene tener igualmente.

## 6. Segundo sitio: `web2`, subido por SFTP

En el mundo real no siempre hay un repositorio del que clonar: a veces tienes los ficheros en tu ordenador y hay que subirlos. Lo harás por **SFTP**, que funciona dentro de SSH. No hay que instalar nada en el servidor: tu servidor SSH ya lo incluye.

### 6.1 Preparar la carpeta en el servidor

```sh
sudo mkdir -p /var/www/web2.garcia.test/html
sudo chown -R $USER:$USER /var/www/web2.garcia.test
```

### 6.2 Descargar la web en tu ordenador

Descarga en tu ordenador la plantilla **Phantom** de HTML5 UP desde [https://html5up.net/phantom](https://html5up.net/phantom) (botón **Download**). Obtendrás el fichero `html5up-phantom.zip`, que quedará en tu carpeta **Descargas**. No lo descomprimas: subirás el `.zip` y lo descomprimirás en el servidor.

### 6.3 Subir el fichero

=== "FileZilla"

    Descarga el **cliente** de FileZilla desde [filezilla-project.org](https://filezilla-project.org/download.php?type=client).

    !!! warning "Cuidado con el instalador"
        El botón de descarga principal ofrece un instalador que incluye programas patrocinados. Pulsa en **Show additional download options** y descarga el instalador normal, o fíjate bien en cada pantalla y rechaza las ofertas.

    En la práctica 1.1 desactivaste el acceso por contraseña, así que FileZilla tendrá que usar **tu clave privada**. Abre **Archivo → Gestor de sitios… → Nuevo sitio** y rellena:

    | Campo | Valor |
    |---|---|
    | **Protocolo** | `SFTP - SSH File Transfer Protocol` |
    | **Servidor** | `192.168.56.10` |
    | **Puerto** | `22` |
    | **Modo de acceso** | `Archivo de claves` |
    | **Usuario** | tu usuario de la Debian |
    | **Archivo de claves** | `C:\Users\tuusuario\.ssh\id_ed25519` |

    Al elegir el archivo de claves, cambia el filtro del explorador a **Todos los archivos**, porque FileZilla busca por defecto ficheros `.ppk` (el formato de PuTTY). Te preguntará si quieres **convertir** la clave a ese formato: acepta y guarda la copia convertida junto a la original.

    Pulsa **Conectar**. La primera vez, FileZilla te mostrará la **huella** del servidor y te preguntará si confías en él: es la misma comprobación que hiciste en la práctica 1.1 con `ssh`, y debe coincidir con aquella.

    Una vez conectado, verás tu ordenador a la izquierda y el servidor a la derecha. En el campo **Sitio remoto** de la derecha escribe `/var/www/web2.garcia.test` y pulsa Enter. A la izquierda, busca tu carpeta de Descargas y **arrastra** `html5up-phantom.zip` al panel derecho.

=== "Línea de comandos (sftp)"

    Desde PowerShell, colócate en tu carpeta de Descargas y abre una sesión SFTP. Usará tu clave, igual que `ssh`:

    ```powershell
    cd $env:USERPROFILE\Downloads
    sftp usuario@192.168.56.10
    ```

    Dentro de la sesión, el *prompt* cambia a `sftp>`. Los comandos se parecen a los de la terminal: `cd` y `ls` actúan sobre el **servidor**, y `lcd` y `lls` sobre **tu ordenador**:

    ```
    sftp> cd /var/www/web2.garcia.test
    sftp> put html5up-phantom.zip
    sftp> ls -l
    sftp> bye
    ```

    `put` sube un fichero; `get` haría lo contrario, descargarlo.

    !!! tip "En una sola línea: `scp`"
        Para copiar un fichero suelto, `scp` es aún más directo:

        ```powershell
        scp html5up-phantom.zip usuario@192.168.56.10:/var/www/web2.garcia.test/
        ```

!!! info "¿Por qué has podido subirlo sin `sudo`?"
    SFTP entra con **tu** usuario y solo puede escribir donde **tú** puedes escribir. Has podido subir el fichero porque eres el propietario de `/var/www/web2.garcia.test`. Si intentas subirlo directamente a `/var/www`, que es de `root`, obtendrás `Permission denied`. Es el comportamiento correcto.

### 6.4 Descomprimir en el servidor

De vuelta en tu sesión SSH:

```sh
cd /var/www/web2.garcia.test
unzip html5up-phantom.zip -d html
rm html5up-phantom.zip
chmod -R u=rwX,go=rX /var/www/web2.garcia.test
ls -la html
```

Debe aparecer el `index.html` directamente dentro de `html`.

### 6.5 Configurar y activar `web2`

Esta vez **lo haces tú**. Parte de la configuración de `web1` como plantilla:

```sh
sudo cp /etc/nginx/sites-available/web1.garcia.test /etc/nginx/sites-available/web2.garcia.test
sudo nano /etc/nginx/sites-available/web2.garcia.test
```

Cambia lo que haga falta para que sea el sitio `web2` (el nombre, la carpeta y los dos registros), actívalo con su enlace simbólico, comprueba la configuración y recarga. El bloque `location ~ /\.git` puede quedarse: no estorba, y protege el sitio si algún día lo despliegas con Git.

Si tu fichero `hosts` ya tiene `web2.garcia.test`, entra en `http://web2.garcia.test`:

![](img/T2-web2.png)

Comprueba que **cada nombre muestra su web**, y que `http://192.168.56.10` sigue mostrando la página de bienvenida de Nginx.

## 7. Los registros

Los registros son la herramienta de diagnóstico más importante que tienes. Cuando alguien te diga "la web no funciona", lo primero que miráis juntos es esto.

Los ficheros de `/var/log/nginx` solo los pueden leer `root` y el grupo `adm`, así que necesitas `sudo`. Deja el registro de accesos de `web1` abierto en directo:

```sh
sudo tail -f /var/log/nginx/web1.access.log
```

Navega por `http://web1.garcia.test` desde el navegador y observa cómo aparece una línea por cada petición: el HTML, las hojas de estilo, las imágenes… Pulsa **Ctrl+C** para salir.

!!! tip "Si no aparece nada al recargar"
    El navegador guarda en caché lo que ya ha descargado y puede no volver a pedirlo, o pedirlo y recibir un `304 Not Modified`. Prueba con **Ctrl+F5** (recarga forzada) o en una **ventana de incógnito**.

### 7.1 Un 404

Pide una página que no existe, por ejemplo `http://web1.garcia.test/noexiste.html`:

![](img/T2-404.png)

Busca la petición en el registro de accesos:

```sh
sudo tail -n 5 /var/log/nginx/web1.access.log
```

```
192.168.56.1 - - [04/Oct/2026:19:47:48 +0200] "GET /noexiste.html HTTP/1.1" 404 146 "-" "Mozilla/5.0 (...)"
```

La IP `192.168.56.1` es tu ordenador visto desde la red Host-only. Ahora mira el registro de errores:

```sh
sudo tail -n 5 /var/log/nginx/web1.error.log
```

Un `404` **no** es un error del servidor: el cliente ha pedido algo que no existe, y el servidor ha respondido correctamente. Por eso solo deja rastro en el registro de accesos.

### 7.2 Un 403 por permisos

Ahora provoca tú un fallo. Quita a todos, menos a ti, el permiso para entrar en la carpeta de la web:

```sh
chmod 700 /var/www/web1.garcia.test/html
```

Recarga `http://web1.garcia.test` (con **Ctrl+F5**). Aparecerá un **403 Forbidden**. Mira el registro de errores:

```sh
sudo tail -n 3 /var/log/nginx/web1.error.log
```

```
2026/10/04 19:55:10 [error] 1908#1908: *74 "/var/www/web1.garcia.test/html/index.html" is forbidden (13: Permission denied), client: 192.168.56.1, server: web1.garcia.test, request: "GET / HTTP/1.1", host: "web1.garcia.test"
```

El registro te dice exactamente qué ha pasado: el usuario `www-data` no tiene permiso para llegar al fichero (`Permission denied`). Tú sigues pudiendo leerlo, porque eres el propietario, y por eso este error despista tanto.

Restaura los permisos y comprueba que la web vuelve a funcionar:

```sh
chmod 755 /var/www/web1.garcia.test/html
```

!!! tip "Diagnosticar en tres pasos"
    Cuando una web no carga, pregúntate en este orden:

    1. **¿Está el servicio funcionando?** `systemctl status nginx`
    2. **¿Escucha donde debe?** `sudo ss -tlnp | grep nginx`
    3. **¿Qué dicen los registros?** `sudo tail /var/log/nginx/*error.log`, y `journalctl -u nginx` si el servicio no arranca.

    Si el navegador muestra un **403**, piensa en permisos o en una regla `deny`. Si muestra un **404**, revisa la directiva `root`. Si muestra la **página de bienvenida** en lugar de tu web, revisa el `server_name` y el fichero `hosts`.

## 8. Haz una instantánea

Apaga la máquina desde tu sesión SSH:

```sh
sudo poweroff
```

En VirtualBox, en la pestaña **Snapshots**, pulsa **Take** y llama a la instantánea `p2.1-nginx`. La siguiente práctica parte de aquí.

---

## Cuestiones finales

!!! question "Cuestión 1"
    ¿Qué ocurre si creas el fichero de un sitio en `sites-available` pero no haces el enlace simbólico en `sites-enabled`? ¿Qué ventaja tiene este sistema de dos carpetas frente a tener un único directorio de configuración?

!!! question "Cuestión 2"
    En esta práctica, el propietario de las carpetas de las webs eres tú y no `www-data`. Explica por qué. ¿Qué permisos concretos necesita `www-data` sobre las carpetas y sobre los ficheros? ¿Qué ves en el navegador y en qué registro, si le faltan?

!!! question "Cuestión 3"
    Entra en `http://192.168.56.10`. ¿Qué sitio responde, y por qué? Ahora desactiva el sitio `default` (borra **solo el enlace** de `sites-enabled`), recarga Nginx y vuelve a entrar por IP. ¿Qué responde ahora y por qué? Vuelve a activar `default` al terminar.

!!! question "Cuestión 4"
    En el apartado 3.4 viste tu web con `curl.exe -H "Host: ..."` sin haber tocado el fichero `hosts`. ¿Qué demuestra eso sobre cómo elige Nginx el sitio? Y entonces, ¿para qué sirve el fichero `hosts`?

!!! question "Cuestión 5"
    Para subir `web2` no has instalado ningún servidor FTP. ¿Por qué no ha hecho falta? Si hubieras usado FTP sin cifrar desde la wifi del aula, ¿qué podría ver un compañero que estuviera capturando el tráfico?

## Entrega

Como en la práctica 1.1, lo que entregas son **las pruebas** de que tu servidor funciona y está bien
configurado. La entrega tiene dos partes, y las dos son obligatorias.

### Parte 1 — Documento de evidencias (40 %)

Un único **PDF** llamado `P2.1-Apellido-Nombre.pdf` que contenga, en este orden:

1. **Portada** con tu nombre, el grupo, el *hostname* de tu máquina y tus dos dominios.
2. **Las evidencias** de la tabla de abajo.
3. **Las respuestas a las cinco cuestiones finales**, con tus palabras.

!!! danger "Texto, no capturas"
    La salida de los comandos se entrega **copiada como texto**, junto con el comando y el *prompt*
    (`usuario@debian-tuapellido:~$ ...`), dentro de un bloque o con tipografía de ancho fijo.

    Solo hay una excepción, porque ahí sí hace falta ver la pantalla: las dos webs en el navegador.

Evidencias que debe contener el documento:

| # | Qué hay que demostrar | Dónde | Comando cuya salida se pega |
|---|---|---|---|
| 1 | Nginx está instalado y funcionando, en tu máquina | Debian | `hostname`, `nginx -v` y `systemctl status nginx --no-pager` |
| 2 | Hay tres sitios activos | Debian | `ls -l /etc/nginx/sites-enabled/` |
| 3 | La configuración de `web1`, con la regla de `.git` | Debian | `cat /etc/nginx/sites-available/web1.tuapellido.test` |
| 4 | La configuración es correcta | Debian | `sudo nginx -t` |
| 5 | Propietarios y permisos de las webs | Debian | `ls -la /var/www/` y `ls -la /var/www/web2.tuapellido.test/html` |
| 6 | Tu ordenador resuelve los dos nombres | Tu ordenador | `ping -n 1 web1.tuapellido.test` y `ping -n 1 web2.tuapellido.test` |
| 7 | Cada nombre devuelve su web | Tu ordenador | Los dos comandos que hay debajo de esta tabla |
| 8 | La carpeta `.git` está protegida | Tu ordenador | `curl.exe -sI http://web1.tuapellido.test/.git/config` (debe responder `403`) |
| 9 | Has subido `web2` por SFTP | Tu ordenador | La sesión de `sftp` completa o, con FileZilla, el texto del panel de mensajes de la transferencia |
| 10 | Los registros muestran tus pruebas | Debian | `sudo tail -n 8 /var/log/nginx/web1.access.log` (con peticiones `200`, `404` y `403`) y `sudo tail -n 3 /var/log/nginx/web1.error.log` (con el `Permission denied`) |
| 11 | Las dos webs, en el navegador | Tu ordenador | **Captura** de cada una con la barra de direcciones visible |

Comandos de la evidencia 7, en PowerShell:

```powershell
curl.exe -s http://web1.tuapellido.test | Select-String "<title>"
curl.exe -s http://web2.tuapellido.test | Select-String "<title>"
```

Cada evidencia debe ir acompañada de **una frase tuya** explicando qué demuestra.
Una tanda de comandos pegados sin explicar no puntúa.

### Parte 2 — Demostración en clase (60 %)

Es una mini entrevista individual. Cuando se te llame, vienes a la mesa del profesor con
**tu ordenador** y la máquina virtual preparada para arrancar. En unos dos o tres minutos:

1. Te conectas por SSH a tu máquina y abres tus dos webs en el navegador, por su nombre.
2. Haces la tarea que se te pida en ese momento. Por ejemplo: desactivar un sitio y volver a activarlo, encontrar en el registro una petición concreta, o diagnosticar un error que se te provoque.
3. Explicas en voz alta **una** de tus decisiones (por qué los ficheros son tuyos y no de `www-data`, para qué sirve el enlace simbólico, por qué hay que proteger `.git`…).

!!! info "Cómo se califica"
    La demostración pesa más que el documento porque es lo que de verdad acredita el
    resultado de aprendizaje. **Una demostración que no funciona no se compensa con un
    documento impecable**: en ese caso la práctica queda pendiente hasta que el servidor
    funcione, y se vuelve a demostrar.

### Criterios de evaluación

| Parte | Criterio | Peso |
|---|---|---|
| Documento | Las once evidencias están completas, en texto (salvo las capturas) y cada una con su frase explicativa | 25 % |
| Documento | Las cinco cuestiones finales están respondidas con corrección y criterio propio | 15 % |
| Demostración | Los dos sitios responden por su nombre desde tu equipo, con `.git` protegido | 20 % |
| Demostración | Realizas la tarea que se te pide y explicas lo que estás haciendo | 20 % |
| Demostración | Explicas una de tus decisiones con tus palabras y respondes a las preguntas sobre ella | 20 % |

Si en la demostración o en el documento aparecen una máquina o unos dominios que no son los tuyos (el *hostname*, el apellido de los dominios), la parte correspondiente cuenta como no superada.

### Antes de entregar, comprueba que…

- ☐ `http://web1.tuapellido.test` y `http://web2.tuapellido.test` muestran **cada uno su web**.
- ☐ `http://192.168.56.10` sigue mostrando la página de bienvenida de Nginx.
- ☐ Las carpetas de las webs son de tu usuario, con carpetas `755` y ficheros `644`.
- ☐ `http://web1.tuapellido.test/.git/config` responde `403`.
- ☐ Cada sitio tiene sus propios registros en `/var/log/nginx/`.
- ☐ `sudo nginx -t` no da errores.
- ☐ Existe la instantánea `p2.1-nginx`.
- ☐ Las once evidencias están en el PDF, en texto y comentadas.
- ☐ Las cinco cuestiones están respondidas.
- ☐ El archivo se llama `P2.1-Apellido-Nombre.pdf`.

## Referencias

- [Documentación de Nginx — Beginner's Guide](https://nginx.org/en/docs/beginners_guide.html)
- [Documentación de Nginx — Nombres de servidor (`server_name`)](https://nginx.org/en/docs/http/server_names.html)
- [Documentación de Nginx — Cómo procesa Nginx una petición](https://nginx.org/en/docs/http/request_processing.html)
- [Debian Wiki — Nginx](https://wiki.debian.org/Nginx)
- [RFC 6761 — Nombres de dominio de uso especial (`.test`)](https://www.rfc-editor.org/rfc/rfc6761)
- [FileZilla](https://filezilla-project.org/) · [WinSCP](https://winscp.net/), una alternativa a FileZilla para Windows
- Webs de ejemplo: [cloudacademy/static-website-example](https://github.com/cloudacademy/static-website-example) y [Phantom, de HTML5 UP](https://html5up.net/phantom) (licencia CC BY 3.0)
