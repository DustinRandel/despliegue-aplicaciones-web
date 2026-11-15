---
title: 'Práctica 3.3 - Aplicación Flask con Gunicorn'
---

<!--
NOTA PARA EL PROFESOR (no se muestra al alumnado):

Reescrita a partir de P3.5-Flask.md (en el original era la 3.5; la 3.3 y la 3.4 eran el clúster de Tomcat y
Netlify, que no se adaptan). Cambios:
  - pipenv -> python3 -m venv + requirements.txt con versiones fijas. pipenv sigue en Debian 13, pero el
    entorno virtual estándar es lo que hay debajo de todas las herramientas y no necesita paquetes extra.
    Se explica el error externally-managed-environment (PEP 668) en la teoría.
  - Corregido: "chmod -R 775 para que pueda ser leído por todo el mundo" (775 da ESCRITURA al grupo; para leer
    basta r). Aquí la carpeta es del alumno y el servicio (www-data) solo lee.
  - Corregido: los workers de Gunicorn son procesos, no hilos, y no "como en Node Express".
  - Corregido: el original arrancaba Gunicorn en 0.0.0.0:5000 en el ejercicio y luego configuraba Nginx contra un
    socket que no existía. Ahora: socket Unix en /run/flask/ creado por systemd (RuntimeDirectory), servicio con
    www-data, sin Group=www-data "para que Nginx pueda": el socket lo crea www-data y Nginx es www-data.
  - Corregido: "nginx -t" sin sudo no funciona en Debian (/usr/sbin fuera del PATH). Bloque nginx marcado como
    yaml en el original. Fuera las referencias al "grupo de seguridad" de AWS.
  - HALLAZGO DE LA VALIDACIÓN: Gunicorn 26 abre un "socket de control" en ~/.gunicorn. www-data tiene como HOME
    /var/www, donde no puede escribir: el servicio arranca pero registra
    "Control server error: [Errno 13] Permission denied: '/var/www/.gunicorn'". Se usa --no-control-socket.
    Con versiones antiguas de Gunicorn esa opción no existe: por eso requirements.txt fija gunicorn==26.2.0.
  - Añadido: /api/lenta para VER que cada worker sync atiende una petición (3 peticiones, 2 workers -> la tercera
    tarda el doble), el worker que muere y el maestro que lo repone, y el 502 con el socket ausente.
  - El ejercicio final del original (repo raul-profesor/Practica-3.5) no se incluye.

VALIDADA el 27/10/2026 en contenedor Debian 13 con systemd. Salidas reales; adaptadas solo las IP, el usuario
(alumno -> garcia), la zona horaria de las líneas de Gunicorn lanzado a mano y la ruta CGroup.
PENDIENTE DE VALIDAR EN LA VM: si python3-venv ya viene instalado en la .ova; los curl.exe desde Windows.
-->

# Práctica 3.3 - Aplicación Flask con Gunicorn por un socket Unix

!!! tip "Cuándo se hace"
    Al terminar el **bloque 4** de la [teoría del Tema 3](T3-servidores-aplicaciones.md), con la [práctica 3.2](T3-practica-node.md) terminada. En la **máquina principal**.

!!! abstract "Objetivos"
    Al terminar esta práctica deberás ser capaz de:

    1. Crear un entorno virtual de Python e instalar en él dependencias con versiones fijas.
    2. Distinguir el servidor de desarrollo de Flask de un servidor WSGI de producción.
    3. Ejecutar Gunicorn como servicio de `systemd`, escuchando en un socket Unix.
    4. Publicar la aplicación detrás de Nginx a través del socket.
    5. Comprobar cómo reparte Gunicorn el trabajo entre sus procesos.

---

## 1. Qué vas a montar

```
 Tu ordenador         debian-tuapellido (192.168.56.10)
 192.168.56.1  ───►   Nginx :80  ── flask.tuapellido.test ──►  /run/flask/flask.sock  ──►  Gunicorn
                                                                                            ├── trabajador
                                                                                            └── trabajador
```

Esta vez la aplicación no abre ningún puerto: Nginx y Gunicorn se hablan por un fichero especial, el socket.

## 2. El entorno virtual

```sh
sudo apt install python3-venv
sudo mkdir /var/www/flask.garcia.test
sudo chown $USER:$USER /var/www/flask.garcia.test
cd /var/www/flask.garcia.test
python3 -m venv .venv
source .venv/bin/activate
```

El *prompt* empieza ahora por `(.venv)`. Comprueba qué `python` y qué `pip` estás usando:

```sh
which python pip
```

```
/var/www/flask.garcia.test/.venv/bin/python
/var/www/flask.garcia.test/.venv/bin/pip
```

Ya no son los del sistema: todo lo que instales irá dentro de `.venv`. Crea el fichero de dependencias, con versiones fijas:

```sh
nano requirements.txt
```

```
Flask==3.1.3
gunicorn==26.2.0
```

```sh
pip install -r requirements.txt
pip freeze
```

```
Successfully installed Flask-3.1.3 blinker-1.9.0 click-8.5.0 gunicorn-26.2.0 itsdangerous-2.2.0 jinja2-3.1.6 markupsafe-3.0.4 werkzeug-3.1.9
```

```
blinker==1.9.0
click==8.5.0
Flask==3.1.3
gunicorn==26.2.0
itsdangerous==2.2.0
Jinja2==3.1.6
MarkupSafe==3.0.4
Werkzeug==3.1.9
```

Has pedido dos paquetes y hay ocho: Flask depende de otros seis. `pip freeze` muestra todo lo instalado en el entorno, con su versión exacta.

!!! tip "Si `pip` dice `externally-managed-environment`"
    Es que el entorno virtual no está activado y estás usando el `pip` del sistema (apartado 6 de la teoría). Vuelve a la carpeta y haz `source .venv/bin/activate`.

## 3. La aplicación

```sh
nano app.py
```

```python
import os
import socket
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/")
def inicio():
    return (f"<h1>Aplicación Flask</h1>"
            f"<p>Servida por <b>{socket.gethostname()}</b>. "
            f"Prueba <a href='/api/hora'>/api/hora</a>.</p>")


@app.route("/api/hora")
def hora():
    return jsonify(
        hora=datetime.now(ZoneInfo("Europe/Madrid")).strftime("%H:%M:%S"),
        servidor=socket.gethostname(),
        pid=os.getpid(),
        cliente=request.headers.get("X-Real-IP", request.remote_addr),
    )


@app.route("/api/lenta")
def lenta():
    time.sleep(3)                       # simula una consulta lenta
    return jsonify(pid=os.getpid(), espera="3 s")
```

- `app = Flask(__name__)` es la aplicación WSGI. Gunicorn la buscará como `app:app`: el objeto `app` del módulo `app.py`.
- `/api/hora` devuelve el PID del proceso que atiende y la IP del cliente: la toma de la cabecera `X-Real-IP` que pone Nginx, o de la conexión si no la hay.
- `/api/lenta` tarda tres segundos en responder, como una consulta pesada a una base de datos. La usarás en el apartado 7.

## 4. Primero, en desarrollo

```sh
flask --app app run --host 0.0.0.0
```

```
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.56.10:5000
Press CTRL+C to quit
```

Entra en `http://192.168.56.10:5000/api/hora` desde tu navegador. Funciona, pero lee el aviso: es un servidor para programar, sin la robustez ni el rendimiento de uno de producción. Para con `Ctrl+C`.

## 5. Gunicorn, a mano

Prueba el servidor de producción, todavía en un puerto y desde tu terminal:

```sh
gunicorn --workers 2 --bind 0.0.0.0:8000 app:app
```

```
[2026-10-27 12:38:59 +0100] [707] [INFO] Starting gunicorn 26.2.0
[2026-10-27 12:38:59 +0100] [707] [INFO] Listening at: http://0.0.0.0:8000 (707)
[2026-10-27 12:38:59 +0100] [707] [INFO] Using worker: sync
[2026-10-27 12:38:59 +0100] [709] [INFO] Booting worker with pid: 709
[2026-10-27 12:38:59 +0100] [710] [INFO] Booting worker with pid: 710
[2026-10-27 12:38:59 +0100] [707] [INFO] Control socket listening at /home/garcia/.gunicorn/gunicorn.ctl
```

Lee las líneas: el maestro (PID 707) escucha en el puerto 8000, usa trabajadores `sync` y arranca dos (709 y 710). La última línea es el **socket de control** de las versiones recientes de Gunicorn, que permite administrarlo mientras funciona; lo crea en la carpeta personal del usuario. Volverás a él en el apartado 6.

Entra en `http://192.168.56.10:8000/api/hora` y recarga varias veces: el `pid` es el de uno de los trabajadores. Para con `Ctrl+C` y sal del entorno virtual:

```sh
deactivate
```

## 6. Gunicorn como servicio

```sh
sudo nano /etc/systemd/system/flask-app.service
```

```ini
[Unit]
Description=Aplicación Flask de flask.garcia.test (Gunicorn)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/flask.garcia.test
RuntimeDirectory=flask
ExecStart=/var/www/flask.garcia.test/.venv/bin/gunicorn --workers 2 --no-control-socket --bind unix:/run/flask/flask.sock app:app
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

- `ExecStart` llama directamente al `gunicorn` del entorno virtual: no hace falta activarlo.
- `--bind unix:/run/flask/flask.sock`: en lugar de un puerto, un socket Unix.
- `RuntimeDirectory=flask`: al arrancar, `systemd` crea `/run/flask`, propiedad de `www-data`, y la borra al parar. `/run` se vacía en cada arranque, así que no puedes crearla tú a mano una vez y olvidarte.
- `--no-control-socket`: el socket de control del apartado 5 se crea en la carpeta personal del usuario, y la de `www-data` es `/var/www`, donde no puede escribir. Sin esta opción, el servicio funciona pero registra `Control server error: [Errno 13] Permission denied: '/var/www/.gunicorn'`.

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now flask-app
systemctl status flask-app
```

```
● flask-app.service - Aplicación Flask de flask.garcia.test (Gunicorn)
     Loaded: loaded (/etc/systemd/system/flask-app.service; enabled; preset: enabled)
     Active: active (running) since Tue 2026-10-27 12:53:57 CET; 1s ago
   Main PID: 1199 (gunicorn)
     Memory: 46.5M (peak: 47M)
        CPU: 456ms
     CGroup: /system.slice/flask-app.service
             ├─1199 /var/www/flask.garcia.test/.venv/bin/python3 /var/www/flask.garcia.test/.venv/bin/gunicorn --workers 2 --no-control-socket --bind unix:/run/flask/flask.sock app:app
             ├─1202 /var/www/flask.garcia.test/.venv/bin/python3 /var/www/flask.garcia.test/.venv/bin/gunicorn --workers 2 --no-control-socket --bind unix:/run/flask/flask.sock app:app
             └─1203 /var/www/flask.garcia.test/.venv/bin/python3 /var/www/flask.garcia.test/.venv/bin/gunicorn --workers 2 --no-control-socket --bind unix:/run/flask/flask.sock app:app

Oct 27 12:53:57 debian-garcia systemd[1]: Started flask-app.service - Aplicación Flask de flask.garcia.test (Gunicorn).
Oct 27 12:53:58 debian-garcia gunicorn[1199]: [2026-10-27 12:53:58 +0100] [1199] [INFO] Starting gunicorn 26.2.0
Oct 27 12:53:58 debian-garcia gunicorn[1199]: [2026-10-27 12:53:58 +0100] [1199] [INFO] Listening at: unix:/run/flask/flask.sock (1199)
Oct 27 12:53:58 debian-garcia gunicorn[1199]: [2026-10-27 12:53:58 +0100] [1199] [INFO] Using worker: sync
Oct 27 12:53:58 debian-garcia gunicorn[1202]: [2026-10-27 12:53:58 +0100] [1202] [INFO] Booting worker with pid: 1202
Oct 27 12:53:58 debian-garcia gunicorn[1203]: [2026-10-27 12:53:58 +0100] [1203] [INFO] Booting worker with pid: 1203
```

Tres procesos: el maestro y dos trabajadores. Mira el socket:

```sh
ls -l /run/flask
```

```
srwxrwxrwx 1 www-data www-data 0 Oct 27 12:53 flask.sock
```

La `s` del principio indica que es un socket. Lo ha creado Gunicorn, como `www-data`, que es también el usuario de los trabajadores de Nginx.

## 7. Publicar con Nginx

```sh
sudo nano /etc/nginx/sites-available/flask.garcia.test
```

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name flask.garcia.test;

    access_log /var/log/nginx/flask.access.log;
    error_log  /var/log/nginx/flask.error.log;

    location / {
        proxy_pass http://unix:/run/flask/flask.sock;
        include proxy_params;
    }
}
```

`http://unix:` le dice a Nginx que hable HTTP, pero por el socket en lugar de por TCP. Actívalo, `sudo nginx -t`, recarga y añade `flask.garcia.test` a tu `hosts`. Desde tu ordenador:

```powershell
curl.exe http://flask.garcia.test/api/hora
```

```
{"cliente":"192.168.56.1","hora":"12:54:19","pid":1214,"servidor":"debian-garcia"}
```

### Cómo se reparten las peticiones

Repite la petición varias veces: casi siempre contesta el mismo `pid`. Gunicorn no reparte por turnos como el balanceador de la práctica 2.5: la petición se la queda el primer trabajador libre que la recoge del socket. Con peticiones rápidas, el primero casi siempre está libre.

Para ver el límite, lanza tres peticiones **lentas a la vez**. Desde la propia máquina (en bash, `&` lanza cada `curl` en segundo plano y `wait` espera a que acaben todos):

```sh
for i in 1 2 3; do
  curl -s -o /dev/null -w "petición $i: %{http_code} en %{time_total} s\n" -H "Host: flask.garcia.test" http://127.0.0.1/api/lenta &
done; wait
```

```
petición 1: 200 en 3.003430 s
petición 3: 200 en 3.003360 s
petición 2: 200 en 6.004739 s
```

Dos trabajadores `sync`, dos peticiones a la vez: la tercera espera a que uno quede libre y tarda el doble. Cambia `--workers 2` por `--workers 3` en el servicio, haz `sudo systemctl daemon-reload` y `sudo systemctl restart flask-app`, y repite:

```
petición 3: 200 en 3.003671 s
petición 2: 200 en 3.003586 s
petición 1: 200 en 3.003692 s
```

Deja después el servicio otra vez con `--workers 2`. Más trabajadores atienden más peticiones a la vez, pero cada uno es un proceso con su propia memoria: no se puede subir sin límite.

## 8. Cuando algo falla

### Un trabajador muere

Mata uno de los trabajadores (no el maestro):

```sh
sudo kill -9 1202       # el PID de un trabajador de tu systemctl status
sudo journalctl -u flask-app -n 2
```

```
Oct 27 12:53:59 debian-garcia gunicorn[1199]: [2026-10-27 12:53:59 +0100] [1199] [ERROR] Worker (pid:1202) was sent SIGKILL! Perhaps out of memory?
Oct 27 12:53:59 debian-garcia gunicorn[1214]: [2026-10-27 12:53:59 +0100] [1214] [INFO] Booting worker with pid: 1214
```

El maestro lo ha detectado y ha arrancado otro (1214) al momento. El «*Perhaps out of memory?*» es solo una suposición de Gunicorn: el motivo más habitual de que alguien mate un trabajador con `SIGKILL` es que el sistema se quede sin memoria. `systemd` ni se ha enterado: el servicio sigue en marcha. Es la segunda red de seguridad, por debajo de `Restart=on-failure`.

### El servicio está parado

```sh
sudo systemctl stop flask-app
ls -l /run/flask
```

```
ls: cannot access '/run/flask': No such file or directory
```

Al parar, `systemd` ha borrado la carpeta y el socket. Recarga `http://flask.garcia.test/api/hora`: `502 Bad Gateway`. En el registro de errores del sitio:

```sh
sudo tail -n 1 /var/log/nginx/flask.error.log
```

```
2026/10/27 12:51:51 [crit] 104#104: *29 connect() to unix:/run/flask/flask.sock failed (2: No such file or directory) while connecting to upstream, client: 192.168.56.1, server: flask.garcia.test, request: "GET /api/hora HTTP/1.1", upstream: "http://unix:/run/flask/flask.sock:/api/hora", host: "flask.garcia.test"
```

Compáralo con el de la práctica 3.1: allí era `Connection refused` (el puerto existe, pero nadie escucha); aquí, `No such file or directory` (el socket ni siquiera existe). Arranca otra vez el servicio con `sudo systemctl start flask-app`.

## 9. Haz la instantánea

Apaga la máquina y toma una instantánea: `p3.3-flask`.

---

## Cuestiones finales

!!! question "Cuestión 1"
    ¿Qué es un entorno virtual y qué problema resuelve? ¿Por qué el servicio no necesita hacer `source .venv/bin/activate`?

!!! question "Cuestión 2"
    En `requirements.txt` has escrito dos paquetes, pero `pip freeze` muestra ocho. ¿Por qué? ¿Qué ventaja tiene fijar las versiones con `==`?

!!! question "Cuestión 3"
    Explica qué hacen `RuntimeDirectory=flask` y `--no-control-socket`. ¿Qué pasaría con el socket si crearas la carpeta `/run/flask` a mano y reiniciaras la máquina?

!!! question "Cuestión 4"
    Explica el resultado de las tres peticiones lentas con dos trabajadores. ¿En qué se diferencia un trabajador de Gunicorn de un trabajador de Nginx?

!!! question "Cuestión 5"
    Compara los dos `502` de las prácticas 3.1 y 3.3. ¿Qué te dice cada mensaje de error sobre dónde está el problema?

## Entrega

Igual que en las prácticas anteriores: **documento de evidencias (40 %)** y **demostración en clase (60 %)**.

### Parte 1 — Documento de evidencias (40 %)

Un **PDF** llamado `P3.3-Apellido-Nombre.pdf` con portada, las evidencias (en texto, con comando y *prompt*) y las respuestas a las cuestiones.

| # | Qué hay que demostrar | Dónde | Comando cuya salida se pega |
|---|---|---|---|
| 1 | El entorno virtual | Principal | `which python pip` con el entorno activado |
| 2 | Las dependencias | Principal | `cat requirements.txt` y `pip freeze` |
| 3 | La aplicación | Principal | `cat app.py` |
| 4 | El servidor de desarrollo y su aviso | Principal | La salida de `flask --app app run --host 0.0.0.0` |
| 5 | El servicio | Principal | `cat /etc/systemd/system/flask-app.service` y `systemctl status flask-app` |
| 6 | El socket | Principal | `ls -l /run/flask` y la línea de `flask.sock` en `sudo ss -xlp` |
| 7 | La configuración de Nginx | Principal | `cat /etc/nginx/sites-available/flask.tuapellido.test` |
| 8 | La aplicación a través del proxy, con la IP real | Tu ordenador | `curl.exe http://flask.tuapellido.test/api/hora` |
| 9 | Las tres peticiones lentas, con 2 y con 3 trabajadores | Principal | El bucle del apartado 7, las dos veces |
| 10 | El trabajador que muere y se repone | Principal | `sudo journalctl -u flask-app -n 2` tras el `kill -9` |
| 11 | El `502` y su causa | Principal | La última línea de `flask.error.log` con el servicio parado |

### Parte 2 — Demostración en clase (60 %)

Mini entrevista individual en la mesa del profesor, con la máquina encendida: muestras la aplicación en `flask.tuapellido.test`, haces la tarea que se te pida (por ejemplo, añadir una dependencia o una ruta y desplegarla) y explicas una decisión o un concepto.

### Criterios de evaluación

| Parte | Criterio | Peso |
|---|---|---|
| Documento | Las once evidencias están completas, en texto y explicadas | 25 % |
| Documento | Las cinco cuestiones están respondidas con corrección y criterio propio | 15 % |
| Demostración | Gunicorn funciona como servicio con `www-data` por el socket, y la aplicación se ve en `flask.tuapellido.test` | 20 % |
| Demostración | Realizas la tarea que se te pide y explicas lo que haces | 20 % |
| Demostración | Explicas una decisión o un concepto con tus palabras | 20 % |

### Antes de entregar, comprueba que…

- ☐ `requirements.txt` fija las versiones de Flask y Gunicorn.
- ☐ El servicio `flask-app` está `enabled` y `active (running)`, con `www-data` y dos trabajadores.
- ☐ Gunicorn no escucha en ningún puerto TCP: `sudo ss -tlnp` no muestra el 8000 ni el 5000.
- ☐ `http://flask.tuapellido.test/api/hora` muestra tu IP real.
- ☐ Existe la instantánea `p3.3-flask`.
- ☐ El archivo se llama `P3.3-Apellido-Nombre.pdf`.

## Referencias

- [Python — `venv`: creación de entornos virtuales](https://docs.python.org/es/3/library/venv.html)
- [Flask — Gunicorn](https://flask.palletsprojects.com/en/stable/deploying/gunicorn/)
- [Flask — Nginx](https://flask.palletsprojects.com/en/stable/deploying/nginx/)
- [Gunicorn — Configuración](https://docs.gunicorn.org/en/stable/settings.html)
- [Gunicorn — Despliegue con Nginx y systemd](https://docs.gunicorn.org/en/stable/deploy.html)
- [`systemd.exec` — `RuntimeDirectory=`](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html#RuntimeDirectory=)
