---
title: "Servidores de aplicaciones"
subtitulo: "UT3. Dosier de apuntes"
modulo: "0614. Despliegue de aplicaciones web"
curso: "2026-2027"
profesor: "Dustin Randel de Lara García"
centro: "Sant Josep Obrer"
ut: "UT3"
---

<!--
NOTA PARA EL PROFESOR (no se muestra al alumnado):
- Página reescrita a partir de ServAplic.md del repo original (~9.500 palabras). Recortada a lo que usan las
  prácticas 3.1-3.3. Fuera: cifras de mercado (CAGR 2020-2026), "el mejor amigo del servidor web", despliegue
  de metadatos/contenidos (era específico del CMS Umbraco), "a qué hora desplegar" en detalle, observabilidad,
  PaaS/Serverless y CI/CD (quedan en un desplegable final; CI/CD es el Tema 7 y los contenedores el Tema 6).
- Corregido respecto al original:
  * Definición: "marco mixto de software que permite la creación de aplicaciones" no define nada. Ahora: programa
    que mantiene cargado el código de la aplicación y genera una respuesta en cada petición.
  * "El servidor web traduce la respuesta [del de aplicaciones] y pasa una respuesta HTTP": falso en los tres casos
    de las prácticas. Tomcat, Node y Gunicorn ya responden en HTTP; Nginx solo la reenvía.
  * "Con un servidor de aplicaciones la inyección SQL es mucho más difícil": falso. La inyección se evita en el
    código (consultas parametrizadas), no con la arquitectura. Eliminado.
  * "Un proxy inverso colocado delante de sus bases de datos": la base de datos no se publica nunca; el proxy va
    delante del servidor web/de aplicaciones.
  * PHP: "con el módulo de Apache cada petición arrancaba un nuevo proceso". Eso era CGI; mod_php mete el
    intérprete dentro de los procesos de Apache. Se explica CGI -> servidor de aplicaciones persistente.
  * Node: "por sí mismo no sabe servir archivos ni manejar peticiones HTTP": falso (tiene el módulo http).
    "Express sirve para aplicaciones móviles multiplataforma": falso. Eliminado lo de Yarn "más rápido".
  * Maven: "POM (Project Object Module)" -> Project Object Model. "La build consiste en mvn install": el
    artefacto lo genera "mvn package"; "install" lo copia además a ~/.m2. Es lo que se usa en la P3.1.
  * Gunicorn (P3.5 original): los workers son PROCESOS, no hilos, y no "como en Node Express" (Node es un solo
    hilo con bucle de eventos). Se explica en el apartado 6.
  * javax -> jakarta: cualquier tutorial antiguo con javax.servlet NO funciona en Tomcat 10. Recuadro en el 4.
- DECISIÓN A CONFIRMAR: la P3.1 original es WildFly (descarga manual, servicio a mano, más RAM). Se sustituye
  por Tomcat 10 de los repositorios de Debian 13 (paquete tomcat10, servicio systemd ya hecho, ~145 MB
  de RAM con la aplicación, medidos en la VM). WildFly queda explicado en la tabla del apartado 4. Si se prefiere
  WildFly, rehacer la P3.1.
- La P3.4 original (React en Netlify) no se adapta: necesita cuentas externas y la parte de despliegue continuo
  encaja mejor en el Tema 7. Queda mencionada en el desplegable final.
- ESCENARIO: las tres prácticas en la máquina principal .10 (sin clones). Nginx delante de tres servidores de
  aplicaciones: java. (Tomcat 127.0.0.1:8080), node. (127.0.0.1:3000) y flask. (socket Unix) .tuapellido.test.
- VALIDACIÓN (27/10/2026): todos los comandos y salidas se han ejecutado en un contenedor Debian 13 (trixie) con
  systemd y los mismos paquetes que la VM (nginx 1.26.3, tomcat10 10.1.55, openjdk 21.0.12.1, maven 3.9.9,
  nodejs 20.19.2, npm 9.2.0, python 3.13.5; de PyPI/npm: Flask 3.1.3, gunicorn 26.2.0, express 5.3.0, nodemon
  3.1.14).
- Validado en VM el 15/11/2026: VM importada de DAW-debian.ova (Debian 13.7, kernel 6.12.107, 2 GB) con el estado
  final del Tema 2 (Nginx con web1 por HTTPS y web2) y las tres prácticas hechas en orden en la misma máquina.
  Versiones de hoy: openjdk 21.0.13 y tomcat10 10.1.60 (el resto, igual). Todas las salidas de esta página son ya
  de la VM. Cambios:
  * Actividad del bloque 1 comprobada: ss -tlnp muestra nginx (80 y 443) y sshd (22, escucha directamente, sin
    activación por socket); ps muestra el maestro de Nginx como root y los trabajadores como www-data.
  * Apartado 2: "Solo Nginx está en 0.0.0.0" era falso (sshd también, y Nginx en 443 tras la P2.2). Salida de
    ss real y texto corregido.
  * systemctl status SIN sudo no enseña las líneas del registro (el usuario no está en adm ni en systemd-journal):
    ahora "sudo systemctl status" y se explica por qué. Lo mismo en P3.2 y P3.3.
  * Flask de desarrollo anuncia la IP del NAT (10.0.2.15), no la .10. Salida real; se explica en la P3.3.
  * Debian no trae pip para el sistema ("pip: command not found"); el externally-managed-environment solo sale
    con python3-pip instalado. Texto corregido y salida completa real.
-->

# Cómo se usa este dosier {.nobreak}

Este dosier es la teoría de la unidad. Las prácticas 3.1 a 3.3 están en páginas aparte y se enlazan al final de cada bloque.

!!! abstract "Qué vas a aprender en esta UT"
    - Qué es un servidor de aplicaciones y por qué casi siempre tiene un Nginx delante.
    - Cómo se comunican el servidor web y el de aplicaciones: HTTP, sockets Unix, FastCGI y WSGI.
    - Qué significa desplegar una aplicación y qué pasos se repiten en cualquier tecnología.
    - Cómo convertir una aplicación en un servicio del sistema con `systemd`.
    - Cómo se empaqueta y se despliega una aplicación Java (Maven, WAR, Tomcat), una de Node.js (npm, Express) y una de Python (entornos virtuales, Flask, Gunicorn).

## Cómo se organiza este tema

La teoría y las prácticas van intercaladas, en cuatro bloques. Cada bloque termina con unas cuestiones de repaso y un recuadro **Ahora toca** que indica la práctica que se hace en ese momento.

| Bloque | Teoría | Al terminar |
|---|---|---|
| 1. Del servidor web al de aplicaciones | Apartados 1, 2 y 3 | Actividad en clase con `ss` y `systemctl` |
| 2. Java | Apartado 4 | [Práctica 3.1](T3-practica-tomcat.md): Maven y Tomcat detrás de Nginx |
| 3. Node.js | Apartado 5 | [Práctica 3.2](T3-practica-node.md): Express como servicio detrás de Nginx |
| 4. Python | Apartado 6 | [Práctica 3.3](T3-practica-flask.md): Flask y Gunicorn por un socket Unix |

Las tres prácticas se hacen en tu máquina principal (`192.168.56.10`), la del Tema 2. Al final tendrás un solo Nginx delante de tres servidores de aplicaciones distintos:

```
                                  ┌──► Tomcat    127.0.0.1:8080          java.tuapellido.test
 Tu ordenador ──► Nginx :80 ──────┼──► Node.js   127.0.0.1:3000          node.tuapellido.test
 192.168.56.1    192.168.56.10    └──► Gunicorn  /run/flask/flask.sock   flask.tuapellido.test
```


## 1. Qué es un servidor de aplicaciones

En el Tema 2 viste la diferencia entre contenido **estático** (ficheros que ya existen) y **dinámico** (una respuesta que se genera en cada petición). Nginx es excelente con lo estático, pero no ejecuta código Java, JavaScript ni Python. Para eso está el **servidor de aplicaciones**: un programa que mantiene **cargado en memoria** el código de la aplicación y, en cada petición, lo ejecuta y genera la respuesta.

Lo de "cargado en memoria" es la clave. En los inicios de la web, el servidor ejecutaba un programa nuevo en cada petición (**CGI**): arrancar el proceso, cargar el intérprete, conectar con la base de datos, responder y morir. Con decenas de peticiones por segundo era insostenible. Un servidor de aplicaciones arranca **una vez** y atiende peticiones sin parar.

| | Servidor web | Servidor de aplicaciones |
|---|---|---|
| Qué hace | Sirve ficheros y reenvía peticiones | Ejecuta el código de la aplicación |
| Contenido | Estático: HTML, CSS, imágenes, JavaScript del navegador | Dinámico: JSON de una API, páginas generadas, sesiones |
| Ejemplos | Nginx, Apache, Caddy | Tomcat, WildFly, Gunicorn, PHP-FPM, Node.js |
| Dónde escucha | Puertos públicos 80 y 443 | Un puerto interno (8080, 3000…) o un socket Unix |
| Coste por petición | Muy bajo | Mayor: ejecuta código y suele consultar una base de datos |

Cada lenguaje tiene los suyos:

| Lenguaje | Servidor de aplicaciones | Lo verás en |
|---|---|---|
| Java | Tomcat, Jetty, WildFly, GlassFish | Práctica 3.1 |
| JavaScript | Node.js: la propia aplicación es el servidor | Práctica 3.2 |
| Python | Gunicorn, uWSGI (y Uvicorn para aplicaciones asíncronas) | Práctica 3.3 |
| PHP | PHP-FPM | Desplegable final |

### Por qué un Nginx delante

Tomcat, Node.js y Gunicorn saben responder HTTP directamente. Aun así, en producción casi siempre tienen un servidor web delante haciendo de **proxy inverso**, como en la práctica 2.4:

- **Un único punto de entrada.** Un solo servicio escucha en los puertos 80 y 443 y reparte por nombre (`java.`, `node.`, `flask.`) entre aplicaciones que escuchan en puertos internos.
- **HTTPS en un solo sitio.** El certificado se configura en Nginx (práctica 2.2), no en cada aplicación.
- **Estáticos rápidos.** Nginx sirve imágenes y CSS sin molestar a la aplicación.
- **Protección.** Los clientes lentos o maliciosos se los come Nginx; la aplicación solo recibe peticiones completas.
- **Escalar.** Con varias copias de la aplicación, Nginx las balancea (práctica 2.5).

Por eso el servidor de aplicaciones escucha **solo en local**: nadie de fuera debe poder saltarse el proxy.

## 2. Cómo se hablan el servidor web y el de aplicaciones

### Dos conversaciones distintas

En cada petición hay **dos** conversaciones, y conviene no mezclarlas:

1. **Nginx ↔ servidor de aplicaciones.** Viajan peticiones completas, por la red local o por un socket. Normalmente en **HTTP**; en PHP, en **FastCGI**.
2. **Servidor de aplicaciones ↔ tu código.** Dentro del mismo proceso: el servidor llama a tu código siguiendo una interfaz estándar de su lenguaje.

| Tecnología | Nginx → servidor de aplicaciones | Servidor de aplicaciones → tu código |
|---|---|---|
| Java (Tomcat) | HTTP, `proxy_pass http://127.0.0.1:8080` | API de **servlets** de Jakarta EE |
| Node.js | HTTP, `proxy_pass http://127.0.0.1:3000` | No hay intermediario: tu código abre el puerto |
| Python (Gunicorn) | HTTP por un socket Unix, `proxy_pass http://unix:…` | **WSGI** |
| PHP (PHP-FPM) | FastCGI, `fastcgi_pass unix:/run/php/…` | El intérprete PHP ejecuta el script |

Gracias a esas interfaces estándar puedes cambiar de servidor sin tocar la aplicación: un servlet funciona igual en Tomcat que en Jetty, y una aplicación Flask igual con Gunicorn que con uWSGI.

### Dónde escucha: `0.0.0.0`, `127.0.0.1` o un socket

Un servicio que escucha en un puerto lo hace en una dirección concreta de la máquina:

| Escucha en | Quién puede conectarse | Uso |
|---|---|---|
| `0.0.0.0:3000` (o `*:3000`) | Cualquiera que llegue a la máquina, por cualquier interfaz | Solo para probar desde tu ordenador |
| `127.0.0.1:3000` | Solo programas de la propia máquina | Aplicación detrás de un proxy en la misma máquina |
| `/run/flask/flask.sock` | Procesos de la máquina con permiso sobre el fichero | Igual, sin pasar por TCP |

Un **socket Unix** es un fichero especial por el que dos procesos de la misma máquina se comunican. Es algo más rápido que TCP y se protege con permisos de ficheros normales. Para Nginx da igual: le hablas HTTP en los dos casos.

Al final del tema, esto es lo que escucha en tu máquina (`sudo ss -tlnxp`, recortado):

```
u_str LISTEN 0  2048  /run/flask/flask.sock   users:(("gunicorn",pid=15698,fd=3),("gunicorn",pid=15697,fd=3),("gunicorn",pid=15694,fd=3))
tcp   LISTEN 0  511   127.0.0.1:3000          users:(("node",pid=14867,fd=21))
tcp   LISTEN 0  511   0.0.0.0:443             users:(("nginx",pid=15479,fd=7),…)
tcp   LISTEN 0  511   0.0.0.0:80              users:(("nginx",pid=15479,fd=5),…)
tcp   LISTEN 0  128   0.0.0.0:22              users:(("sshd",pid=709,fd=6))
tcp   LISTEN 0  100   [::ffff:127.0.0.1]:8080 users:(("java",pid=3445,fd=39))
```

Hacia fuera solo están abiertos Nginx (80 y 443) y SSH (22), que es por donde administras la máquina. Las tres aplicaciones son solo locales. Tomcat aparece como `[::ffff:127.0.0.1]` porque Java escucha en IPv6 con una dirección que representa la `127.0.0.1` de IPv4: sigue siendo solo local.

!!! info "Puertos por encima de 1024"
    En Linux, solo `root` puede abrir los puertos por debajo de 1024. Por eso los servidores de aplicaciones usan 8080, 3000 u 8000: así se ejecutan con un usuario sin privilegios, y el único que necesita el 80 y el 443 es Nginx.

## 3. Qué es desplegar

**Desplegar** es llevar una versión concreta de una aplicación desde el entorno donde se desarrolla hasta el servidor donde la usan, y dejarla **funcionando y comprobada**. No es "copiar ficheros": incluye preparar el entorno, instalar dependencias, configurar y arrancar.

### Artefacto y entornos

Lo que se lleva al servidor se llama **artefacto**, y depende de la tecnología:

| Tecnología | Se construye con | Artefacto | Dependencias |
|---|---|---|---|
| Java | Maven (`mvn package`) | Un fichero `.war` (o un `.jar` ejecutable) | Ya van dentro del artefacto |
| Node.js | No se compila | El código + `package.json` + `package-lock.json` | Se instalan en el servidor con `npm ci` |
| Python | No se compila | El código + `requirements.txt` | Se instalan en el servidor con `pip`, en un entorno virtual |

Una aplicación pasa normalmente por varios **entornos** antes de llegar a los usuarios: **desarrollo** (el portátil de quien programa), **pruebas** o **preproducción** (una copia del servidor real) y **producción** (el servidor de verdad). En desarrollo se usan servidores cómodos que se recargan solos y muestran errores detallados; en producción, servidores robustos que no enseñan nada interno. Lo verás en las tres prácticas: `nodemon` frente a `node`, el servidor de pruebas de Flask frente a Gunicorn.

### Los pasos de un despliegue

Las tres prácticas siguen **el mismo guion**, con herramientas distintas:

| Paso | Java (P3.1) | Node.js (P3.2) | Python (P3.3) |
|---|---|---|---|
| 1. Entorno de ejecución | `apt install default-jdk-headless maven tomcat10` | `apt install nodejs npm` | `apt install python3-venv` |
| 2. Código | Proyecto Maven | `package.json` + `app.js` | `requirements.txt` + `app.py` |
| 3. Dependencias | Maven, al construir | `npm ci --omit=dev` | `pip install -r requirements.txt` |
| 4. Artefacto | `mvn package` → `saludo.war` | no hay (se ejecuta el código) | no hay (se ejecuta el código) |
| 5. Servicio | Lo trae el paquete: `tomcat10` | Lo escribes tú: `node-app.service` | Lo escribes tú: `flask-app.service` |
| 6. Publicar | Nginx → `127.0.0.1:8080` | Nginx → `127.0.0.1:3000` | Nginx → socket Unix |
| 7. Comprobar | `curl`, `journalctl`, registros de Nginx | Igual | Igual |

Si entiendes el guion, desplegar en una tecnología nueva es buscar qué herramienta hace cada paso.

### Que la aplicación siga viva: servicios con `systemd`

Si arrancas una aplicación desde tu sesión SSH (`node app.js`), muere al cerrar la terminal, no arranca sola al reiniciar la máquina y, si falla, nadie la levanta. Para eso está **`systemd`**, el gestor de servicios de Debian, el mismo que arranca SSH y Nginx. Un servicio se describe en un fichero de **unidad** en `/etc/systemd/system/`:

```ini
[Unit]
Description=Aplicación Node.js de node.garcia.test
After=network.target                       # (1)!

[Service]
User=www-data                              # (2)!
Group=www-data
WorkingDirectory=/var/www/node.garcia.test # (3)!
Environment=NODE_ENV=production            # (4)!
ExecStart=/usr/bin/node app.js             # (5)!
Restart=on-failure                         # (6)!

[Install]
WantedBy=multi-user.target                 # (7)!
```

1. Arranca después de que la red esté lista.
2. Con qué usuario se ejecuta. Nunca `root`: si alguien explota un fallo de la aplicación, tendrá los permisos de este usuario.
3. Desde qué carpeta (la que contiene la aplicación).
4. Variables de entorno que recibe la aplicación.
5. El comando que arranca la aplicación, con **ruta absoluta**.
6. Si el proceso muere por un error, `systemd` lo vuelve a arrancar.
7. Qué hace `enable`: arrancarlo en el arranque normal del sistema.

Los comandos son siempre los mismos:

```sh
sudo systemctl daemon-reload              # tras crear o editar un fichero de unidad
sudo systemctl enable --now node-app      # arrancar ahora y en cada arranque
sudo systemctl status node-app            # estado y últimas líneas del registro
sudo systemctl restart node-app           # tras desplegar una versión nueva
sudo journalctl -u node-app -n 20         # registro del servicio
```

Lo que imprime la aplicación (`console.log` en Node, `print` en Python, el registro de Tomcat) va al **diario** de `systemd`, y se lee con `journalctl`. Tu usuario no puede leer el diario del sistema: por eso `journalctl` lleva `sudo`, y `systemctl status` también si quieres ver las líneas del registro (sin `sudo` solo enseña el estado). Así se ve un servicio sano (`sudo systemctl status`, recortado):

```
● node-app.service - Aplicación Node.js de node.garcia.test
     Loaded: loaded (/etc/systemd/system/node-app.service; enabled; preset: enabled)
     Active: active (running) since Sun 2026-11-15 18:44:20 CET; 2s ago
   Main PID: 14728 (node)
     Memory: 20.9M (peak: 21.3M)

Nov 15 18:44:20 debian-garcia systemd[1]: Started node-app.service - Aplicación Node.js de node.garcia.test.
Nov 15 18:44:20 debian-garcia node[14728]: Escuchando en http://127.0.0.1:3000
```

`enabled` significa que arrancará con la máquina; `active (running)`, que está en marcha ahora. Son cosas distintas: un servicio puede estar en marcha pero no habilitado, y al revés.

### Buenas prácticas de despliegue

- **El código sale de Git**, no de un pendrive ni de "la versión buena de mi portátil". Así sabes exactamente qué versión hay en producción.
- **No se edita en producción.** Un cambio hecho a mano en el servidor se pierde en el siguiente despliegue y nadie sabe que existió.
- **Poder volver atrás.** Guarda la versión anterior del artefacto antes de sustituirla. Si la nueva falla, restaurar debe ser un paso, no una tarde.
- **Comprueba después de desplegar**: una petición real y un vistazo al registro. "El comando no ha dado error" no significa que la aplicación funcione.
- **Los secretos, fuera del código.** Contraseñas y claves van en variables de entorno o ficheros de configuración del servidor, nunca en el repositorio.
- **Despliega cuando haya poco uso y alguien pueda arreglarlo.** Un viernes por la tarde no es buen momento.


## Cierre del bloque 1

!!! question "Cuestión 1"
    ¿Por qué una aplicación en producción escucha en `127.0.0.1` y no en `0.0.0.0`? ¿Quién recibe entonces las peticiones de los usuarios?

!!! question "Cuestión 2"
    Explica la diferencia entre `systemctl enable` y `systemctl start`. ¿Qué pasaría al reiniciar la máquina si solo hicieras `start`?

!!! example "Ahora toca: actividad en clase (sin entrega)"
    En tu máquina principal, tal como quedó tras el Tema 2:

    1. `sudo ss -tlnp`. ¿Qué programas escuchan, en qué puertos y en qué direcciones? ¿Cuáles aceptan conexiones de fuera?
    2. `systemctl cat nginx`. Localiza `ExecStart`. ¿Por qué Nginx no necesita `User=`? (Pista: busca la directiva `user` en `/etc/nginx/nginx.conf` y mira con qué usuario corren sus procesos con `ps -o user,cmd -C nginx`).
    3. `sudo journalctl -u nginx -n 5` y `systemctl is-enabled ssh`.


## 4. Aplicaciones Java: servlets, Maven y Tomcat

### Servlets y contenedores

Java se compila a **bytecode** (ficheros `.class`), que ejecuta la máquina virtual de Java (**JVM**). Una aplicación web Java clásica está formada por **servlets**: clases que atienden peticiones HTTP. Un servlet no abre ningún puerto; lo hace el **contenedor de servlets**, que recibe la petición, decide qué servlet la atiende según la URL, lo ejecuta en uno de sus hilos y devuelve la respuesta.

```java
@WebServlet("/api/saludo")                      // URL que atiende
public class SaludoServlet extends HttpServlet {
    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        resp.setContentType("application/json;charset=UTF-8");
        resp.getWriter().println("{\"mensaje\": \"Hola\"}");
    }
}
```

`doGet` atiende el método `GET`; habría un `doPost` para `POST`, etc. Todo lo demás (puerto, hilos, cabeceras) es cosa del contenedor.

El estándar se llama **Jakarta EE** (antes Java EE) y tiene dos niveles de servidor:

| | Contenedor de servlets | Servidor Jakarta EE completo |
|---|---|---|
| Ejemplos | **Tomcat**, Jetty | WildFly (antes JBoss), GlassFish, Payara |
| Qué incluye | Servlets, JSP, WebSocket | Además: transacciones, persistencia (JPA), mensajería, servicios REST… |
| Consumo | Ligero | Más pesado |
| Cuándo | Aplicaciones web y API sencillas; base de Spring Boot | Aplicaciones empresariales que usan esos servicios |

Tomcat es, con diferencia, el más usado, y es el que trae Debian en sus repositorios.

!!! warning "`javax` o `jakarta`: el error del tutorial antiguo"
    En 2017, Oracle cedió Java EE a la Fundación Eclipse, que lo rebautizó como Jakarta EE, y desde Jakarta EE 9 (2020) los paquetes se llaman `jakarta.servlet…` en lugar de `javax.servlet…`. **Tomcat 10 y posteriores solo entienden `jakarta`**. Un servlet de un tutorial antiguo con `import javax.servlet…` compila contra la librería antigua, se despliega sin un solo error en el registro… y su URL devuelve `404`, porque Tomcat no lo reconoce como servlet. Los ficheros estáticos del mismo WAR sí se sirven, lo que despista todavía más. Si copias código de Internet, mira los `import`.

### La aplicación empaquetada: WAR

Una aplicación web Java se distribuye en un fichero **WAR** (*Web Application Archive*): un ZIP con una estructura fija. Estos son los ficheros del de la práctica 3.1 (`jar tf saludo.war`, sin las carpetas):

```
META-INF/MANIFEST.MF
WEB-INF/classes/es/sjo/daw/SaludoServlet.class      ← el código compilado
index.html                                          ← estáticos, en la raíz
META-INF/maven/es.sjo.daw/saludo/pom.xml
META-INF/maven/es.sjo.daw/saludo/pom.properties
```

- Lo que está en la raíz se sirve tal cual: `index.html`, CSS, imágenes.
- `WEB-INF/` **nunca** se sirve al navegador. Contiene `classes/` (tu código compilado), `lib/` (las librerías que necesite) y, opcionalmente, `web.xml` (configuración; con anotaciones como `@WebServlet` ya no hace falta).

En el servidor, cada WAR es un **contexto**: una aplicación independiente con su propia URL. El nombre del fichero decide la ruta: `saludo.war` se publica en `/saludo/`, y `ROOT.war` (o la carpeta `ROOT/`) en `/`.

### Maven

Construir un WAR a mano (compilar con las librerías correctas, colocar cada fichero en su sitio, comprimir) es tedioso y fácil de hacer mal. **Maven** lo automatiza a partir de un fichero que describe el proyecto, el **`pom.xml`** (*Project Object Model*):

```xml
<groupId>es.sjo.daw</groupId>              <!-- quién: normalmente un dominio al revés -->
<artifactId>saludo</artifactId>            <!-- qué: el nombre del proyecto -->
<version>1.0</version>
<packaging>war</packaging>                 <!-- qué artefacto generar -->

<dependency>
  <groupId>jakarta.servlet</groupId>
  <artifactId>jakarta.servlet-api</artifactId>
  <version>6.0.0</version>
  <scope>provided</scope>                  <!-- la pone Tomcat: no se mete en el WAR -->
</dependency>
```

Maven aporta tres cosas:

- **Una estructura fija.** El código va en `src/main/java`, los ficheros web en `src/main/webapp` y el resultado aparece en `target/`. Cualquiera que conozca Maven entiende cualquier proyecto.
- **Dependencias automáticas.** Declaras qué librerías necesitas y Maven las descarga de **Maven Central** y las guarda en `~/.m2/repository`. La primera construcción descarga mucho; las siguientes, nada.
- **Un ciclo de vida.** Fases en orden: `validate` → `compile` → `test` → `package` → `verify` → `install` → `deploy`. Pedir una fase ejecuta todas las anteriores: `mvn package` valida, compila, pasa las pruebas y empaqueta.

!!! info "`package` no es `install`, y `deploy` no es desplegar"
    `mvn package` deja el artefacto en `target/`: es lo que necesitas. `mvn install` además lo copia a tu repositorio local `~/.m2` para que lo usen **otros proyectos** como dependencia. Y `mvn deploy` lo sube a un repositorio de artefactos de la empresa; **no** lo instala en ningún servidor de aplicaciones.

### Tomcat en Debian

El paquete `tomcat10` de Debian 13 deja Tomcat 10.1 instalado como servicio, ejecutándose con el usuario `tomcat` y escuchando en el puerto 8080. Reparte sus ficheros así:

| Qué | Dónde |
|---|---|
| Programa (`CATALINA_HOME`) | `/usr/share/tomcat10` |
| Instancia (`CATALINA_BASE`) | `/var/lib/tomcat10` |
| Aplicaciones desplegadas | `/var/lib/tomcat10/webapps` |
| Configuración (`server.xml`, usuarios…) | `/etc/tomcat10` |
| Registros | `journalctl -u tomcat10` y `/var/log/tomcat10/` |

Desplegar es **copiar el WAR a `webapps/`**: Tomcat vigila esa carpeta, descomprime el WAR y lo publica en unos segundos. Si sustituyes el fichero por una versión nueva, retira la antigua y despliega la nueva sin reiniciar. Lo verás en el diario:

```
Nov 15 16:48:13 debian-garcia tomcat10[3445]: Undeploying context [/saludo]
Nov 15 16:48:13 debian-garcia tomcat10[3445]: Deploying web application archive [/var/lib/tomcat10/webapps/saludo.war]
Nov 15 16:48:15 debian-garcia tomcat10[3445]: Deployment of web application archive [/var/lib/tomcat10/webapps/saludo.war] has finished in [1,268] ms
```

### El modelo moderno: Spring Boot

Hoy muchos proyectos Java usan **Spring Boot**, que da la vuelta al modelo: en lugar de instalar un Tomcat y desplegar WAR dentro, cada aplicación **lleva su Tomcat embebido** en un único `.jar` ejecutable que se arranca con `java -jar app.jar`. Es el mismo modelo de Node.js y de Gunicorn: un servicio de `systemd` por aplicación y un Nginx delante. El modelo del WAR sigue muy presente en empresas con un servidor que aloja muchas aplicaciones, y es el que entenderás primero.


## Cierre del bloque 2

!!! question "Cuestión 3"
    Un compañero copia un servlet de un tutorial de 2017, lo empaqueta y lo despliega en tu Tomcat 10. El despliegue no da errores, pero su URL devuelve `404`. ¿Qué es lo primero que miras en su código, y por qué?

!!! question "Cuestión 4"
    ¿Por qué la dependencia `jakarta.servlet-api` lleva `<scope>provided</scope>`? ¿Qué pasaría si se metiera dentro del WAR?

!!! example "Ahora toca: Práctica 3.1 - Aplicación Java en Tomcat"
    **[Ir a la práctica 3.1](T3-practica-tomcat.md).** Construirás un WAR con Maven, lo desplegarás en Tomcat, lo publicarás en `java.tuapellido.test` a través de Nginx y harás que Tomcat solo acepte conexiones locales. Usa los apartados 2, 3 y 4.


## 5. Node.js y Express

### Node.js

**Node.js** es un entorno de ejecución de JavaScript fuera del navegador, construido sobre V8, el motor de JavaScript de Chrome. No es un lenguaje ni un framework: es el programa que ejecuta tu JavaScript en el servidor.

Su diferencia con Java es de fondo. Tomcat atiende cada petición en **un hilo** de un grupo de hilos. Node ejecuta tu código en **un solo hilo** con un **bucle de eventos**: cuando una petición tiene que esperar (leer un fichero, consultar una base de datos), Node no se queda parado, sino que atiende otras y vuelve cuando llegan los datos. Funciona muy bien con muchas conexiones que esperan mucho y calculan poco. La contrapartida: un cálculo largo bloquea **todas** las peticiones, y un proceso de Node usa un solo núcleo. Para aprovechar varios núcleos se arrancan varias copias y se balancean, como en la práctica 2.5.

Otra diferencia: en Node **la aplicación es el servidor**. No hay un Tomcat donde desplegarla; tu propio código abre el puerto.

### Express

Node trae el módulo `http`, suficiente para responder peticiones, pero obliga a analizar a mano cada URL y cada cabecera. **Express** es el framework mínimo más usado para eso: asocia rutas a funciones y encadena funciones intermedias (*middleware*).

```js
const express = require('express');
const app = express();

app.get('/api/hora', (req, res) => {           // método GET, ruta /api/hora
  res.json({ hora: new Date().toLocaleTimeString('es-ES') });
});

app.listen(3000, '127.0.0.1', (err) => {       // el puerto lo abre tu código
  if (err) throw err;
});
```

### npm y `package.json`

**npm** es el gestor de paquetes de Node: descarga librerías del registro público `npmjs.com`. Cada proyecto se describe en **`package.json`**:

```json
{
  "name": "node.garcia.test",
  "version": "1.0.0",
  "main": "app.js",
  "scripts": {
    "start": "node app.js",
    "dev": "nodemon app.js"
  },
  "dependencies": {
    "express": "^5.3.0"
  },
  "devDependencies": {
    "nodemon": "^3.1.14"
  }
}
```

| Campo o fichero | Para qué sirve |
|---|---|
| `dependencies` | Lo que la aplicación necesita para **funcionar** (Express) |
| `devDependencies` | Lo que solo se necesita para **desarrollar** (nodemon, que reinicia la aplicación al guardar) |
| `^5.3.0` | Cualquier versión `5.x.y` igual o superior: admite mejoras, no cambios incompatibles |
| `package-lock.json` | Las versiones **exactas** que se instalaron, de todas las librerías y de sus dependencias. Va al repositorio |
| `node_modules/` | Las librerías descargadas. **No** va al repositorio: se regenera |

Dos comandos que parecen iguales:

- `npm install`: instala lo que diga `package.json` y **actualiza** `package-lock.json` si hace falta. Para desarrollar.
- `npm ci`: borra `node_modules` e instala **exactamente** lo que dice `package-lock.json`, sin tocarlo. Para desplegar: el servidor tendrá las mismas versiones que probaste. Con `--omit=dev` no instala las de desarrollo.

### Scripts de npm

`npm start` y `npm run dev` ejecutan el comando que diga `scripts`. Al ejecutarlo, npm añade `node_modules/.bin` al `PATH`, y ahí están los ejecutables de las librerías instaladas. Por eso `"dev": "nodemon app.js"` funciona sin instalar nodemon en el sistema… siempre que esté en `node_modules`. Si no lo está:

```
> node.garcia.test@1.0.0 dev
> nodemon app.js

sh: 1: nodemon: not found
```

La solución no es instalarlo para todo el sistema, sino instalar las dependencias del proyecto (`npm install`).

### Variables de entorno

La misma aplicación debe funcionar en tu portátil y en producción sin tocar el código. Lo que cambia entre entornos (puerto, contraseña de la base de datos, modo) se le pasa en **variables de entorno**, que en Node se leen con `process.env`:

```js
const PORT = process.env.PORT || 3000;
```

`NODE_ENV=production` es una convención: Express y muchas librerías la leen para desactivar mensajes de depuración y activar cachés. En el servicio de `systemd` se ponen con `Environment=`.


## Cierre del bloque 3

!!! question "Cuestión 5"
    ¿Qué diferencia hay entre `dependencies` y `devDependencies`? ¿Por qué en el servidor se usa `npm ci --omit=dev` y no `npm install`?

!!! question "Cuestión 6"
    Node atiende todas las peticiones en un solo hilo. ¿Por qué aun así aguanta muchas conexiones a la vez? ¿Qué tipo de código lo bloquearía?

!!! example "Ahora toca: Práctica 3.2 - Aplicación Node.js con Express"
    **[Ir a la práctica 3.2](T3-practica-node.md).** Crearás una aplicación con Express, la convertirás en un servicio de `systemd` con el usuario `www-data` y la publicarás en `node.tuapellido.test`. Usa los apartados 3 y 5.


## 6. Python: Flask, WSGI y Gunicorn

### Flask

**Flask** es un *microframework* de Python: rutas, plantillas y poco más. Si necesitas base de datos, formularios o autenticación, añades librerías. En el otro extremo está **Django**, que lo trae todo.

```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/api/hora")
def hora():
    return jsonify(hora="12:00:00")
```

Flask incluye un servidor para desarrollar, y él mismo avisa de que no es para producción:

```
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://10.0.2.15:5000
Press CTRL+C to quit
```

### WSGI y Gunicorn

**WSGI** (*Web Server Gateway Interface*, PEP 3333) es el estándar que dice cómo un servidor de Python llama a una aplicación: la aplicación es un objeto al que el servidor invoca en cada petición pasándole los datos de la petición, y que devuelve la respuesta. Un objeto `Flask` cumple ese estándar, así que cualquier servidor WSGI puede ejecutarlo. Es el equivalente Python de la API de servlets.

**Gunicorn** es el servidor WSGI más usado. Al arrancar con `gunicorn --workers 2 app:app` (el objeto `app` del fichero `app.py`) crea un proceso **maestro** que no atiende peticiones, sino que vigila a los **trabajadores** (*workers*). Así se ven con `ps -o user,pid,ppid,cmd -C gunicorn` (el primero es el maestro; los otros dos, sus hijos):

```
USER         PID    PPID CMD
www-data   15694       1 /var/www/flask.garcia.test/.venv/bin/python3 /var/www/flask.garcia.test/.venv/bin/gunicorn --workers 2 --no-control-socket --bind unix:/run/flask/flask.sock app:app
www-data   15697   15694 /var/www/flask.garcia.test/.venv/bin/python3 /var/www/flask.garcia.test/.venv/bin/gunicorn --workers 2 --no-control-socket --bind unix:/run/flask/flask.sock app:app
www-data   15698   15694 /var/www/flask.garcia.test/.venv/bin/python3 /var/www/flask.garcia.test/.venv/bin/gunicorn --workers 2 --no-control-socket --bind unix:/run/flask/flask.sock app:app
```

Los trabajadores son **procesos**, no hilos. Con el tipo de trabajador por defecto (`sync`), cada uno atiende **una petición cada vez**: con dos trabajadores, como mucho dos peticiones simultáneas. Si un trabajador muere, el maestro arranca otro. La recomendación de partida de la documentación es `(2 × núcleos) + 1` trabajadores; en una máquina virtual pequeña, 2 bastan.

!!! info "El paralelo con Nginx"
    Es el mismo esquema que viste en el Tema 2 con Nginx: un proceso maestro que gestiona y varios trabajadores que atienden. La diferencia es que un trabajador de Nginx atiende miles de conexiones a la vez y uno `sync` de Gunicorn, una sola.

### Entornos virtuales

Cada aplicación Python necesita sus propias versiones de sus librerías, y no pueden mezclarse con las del sistema (Debian usa Python para sus propias herramientas). Por eso Debian 13 ni siquiera trae `pip` para el sistema (`pip: command not found`), y, aunque instales el paquete `python3-pip`, te impide usarlo para instalar librerías en todo el sistema:

```
error: externally-managed-environment

× This environment is externally managed
╰─> To install Python packages system-wide, try apt install
    python3-xyz, where xyz is the package you are trying to
    install.
    
    If you wish to install a non-Debian-packaged Python package,
    create a virtual environment using python3 -m venv path/to/venv.
    Then use path/to/venv/bin/python and path/to/venv/bin/pip. Make
    sure you have python3-full installed.
    
    If you wish to install a non-Debian packaged Python application,
    it may be easiest to use pipx install xyz, which will manage a
    virtual environment for you. Make sure you have pipx installed.
    
    See /usr/share/doc/python3.13/README.venv for more information.

note: If you believe this is a mistake, please contact your Python installation or OS distribution provider. You can override this, at the risk of breaking your Python installation or OS, by passing --break-system-packages.
hint: See PEP 668 for the detailed specification.
```

La solución es un **entorno virtual**: una carpeta (por convención, `.venv`) con su propio `python`, su propio `pip` y sus propias librerías.

```sh
python3 -m venv .venv             # crearlo (paquete python3-venv)
source .venv/bin/activate         # activarlo: python y pip pasan a ser los de .venv
pip install -r requirements.txt   # instalar las dependencias dentro
deactivate                        # salir
```

Activar solo cambia el `PATH` de tu terminal. Un servicio no necesita activarlo: basta con llamar directamente a `/ruta/.venv/bin/gunicorn`.

Las dependencias se declaran en **`requirements.txt`**, con versiones fijas para que producción tenga lo mismo que probaste (es el equivalente de `package-lock.json`):

```
Flask==3.1.3
gunicorn==26.2.0
```

!!! tip "Otras herramientas"
    `pipenv`, `poetry` o `uv` hacen lo mismo (entorno virtual + fichero de dependencias con versiones exactas) con más comodidades. Por debajo, todas crean un entorno virtual como este.

### Gunicorn por un socket Unix

En la práctica 3.3, Gunicorn no abrirá ningún puerto: escuchará en un socket Unix, `/run/flask/flask.sock`, y Nginx le hablará por ahí:

```nginx
location / {
    proxy_pass http://unix:/run/flask/flask.sock;
    include proxy_params;
}
```

`/run` se borra en cada arranque, así que la carpeta del socket la crea `systemd` al arrancar el servicio con `RuntimeDirectory=flask`, con el usuario del servicio como propietario. Si el servicio está parado, el socket no existe, y Nginx responde `502`:

```
[crit] 15478#15478: *71 connect() to unix:/run/flask/flask.sock failed (2: No such file or directory) while connecting to upstream, client: 192.168.56.1, server: flask.garcia.test, request: "GET /api/hora HTTP/1.1", upstream: "http://unix:/run/flask/flask.sock:/api/hora", host: "flask.garcia.test"
```


## Cierre del bloque 4

!!! question "Cuestión 7"
    ¿Qué es WSGI y qué problema resuelve? ¿Cuál es su equivalente en Java?

!!! question "Cuestión 8"
    Gunicorn arranca con `--workers 2` y el trabajador es `sync`. Llegan tres peticiones lentas a la vez. ¿Qué pasa con la tercera? ¿Qué harías para atender más?

!!! example "Ahora toca: Práctica 3.3 - Aplicación Flask con Gunicorn"
    **[Ir a la práctica 3.3](T3-practica-flask.md).** Crearás un entorno virtual, instalarás Flask y Gunicorn, convertirás Gunicorn en un servicio que escucha en un socket Unix y lo publicarás en `flask.tuapellido.test`. Usa los apartados 2, 3 y 6.


??? info "Para saber más: PHP-FPM, PaaS y lo que viene"
    **PHP-FPM.** PHP sigue el mismo modelo con otro protocolo. PHP-FPM (*FastCGI Process Manager*) mantiene un grupo de procesos PHP ya arrancados, y Nginx le pasa cada petición a un fichero `.php` por **FastCGI** (`fastcgi_pass unix:/run/php/php8.4-fpm.sock;`) en vez de por HTTP. Es la *P* de LEMP. Con Apache existía además `mod_php`, que mete el intérprete dentro de los propios procesos de Apache.

    **Plataformas como servicio (PaaS).** Servicios como Render, Railway, Heroku o Google App Engine hacen por ti los pasos 1, 3, 5 y 6 del guion: subes el código (normalmente conectando un repositorio de GitHub) y ellos instalan el entorno, las dependencias, lo arrancan y lo publican con HTTPS. Para sitios estáticos, Netlify, Vercel o GitHub Pages. Cómodo… y una caja negra si no sabes qué hace por dentro.

    **Serverless (FaaS).** Un paso más: subes funciones sueltas (AWS Lambda, Cloud Functions) que se ejecutan solo cuando llega una petición y se cobran por uso. Sigue habiendo servidores; simplemente no los gestionas tú.

    **Contenedores (Tema 6).** Empaquetar la aplicación **con** su entorno de ejecución en una imagen, para que el paso 1 del guion desaparezca: lo que funciona en tu máquina funciona igual en el servidor.

    **Integración y despliegue continuos (Tema 7).** Automatizar el guion entero: cada vez que se sube código al repositorio, un sistema lo construye, lo prueba y, si todo va bien, lo despliega sin intervención manual.

## Referencias

- [Apache Tomcat 10.1: documentación](https://tomcat.apache.org/tomcat-10.1-doc/index.html)
- [Apache Maven: introducción al ciclo de vida](https://maven.apache.org/guides/introduction/introduction-to-the-lifecycle.html)
- [Jakarta EE: Jakarta Servlet 6.0](https://jakarta.ee/specifications/servlet/6.0/)
- [Node.js: introducción](https://nodejs.org/es/learn/getting-started/introduction-to-nodejs)
- [Express: guía de enrutamiento](https://expressjs.com/es/guide/routing.html)
- [npm: `npm ci`](https://docs.npmjs.com/cli/commands/npm-ci)
- [Flask: despliegue en producción](https://flask.palletsprojects.com/en/stable/deploying/)
- [Gunicorn: diseño (maestro y trabajadores)](https://docs.gunicorn.org/en/stable/design.html)
- [PEP 668: entornos gestionados externamente](https://peps.python.org/pep-0668/)
- [`systemd.service`: manual](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
