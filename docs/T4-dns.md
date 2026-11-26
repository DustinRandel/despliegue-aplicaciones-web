---
title: "Servicios de red (DNS)"
subtitulo: "UT4. Dosier de apuntes"
modulo: "0614. Despliegue de aplicaciones web"
curso: "2026-2027"
profesor: "Dustin Randel de Lara García"
centro: "Sant Josep Obrer"
ut: "UT4"
---

<!--
NOTA PARA EL PROFESOR:
- Fuente: dns.md y P4.1-DNS.md del original (raul-profesor). Reescrito para el escenario de este curso:
  VM Debian 13 Host-Only (.10), nombres .tuapellido.test, sin cuentas AWS.
- La P4.1 original montaba BIND9 en EC2 y usaba Amazon Linux + Windows. Aquí la práctica es BIND9
  en la misma VM, sustituyendo /etc/hosts. P4.2 (Route 53) no se adapta: pide cuenta AWS.
- PENDIENTE DE VALIDAR EN LA VM: paquetes bind9 en Debian 13, rutas de named.conf.options y
  named.conf.local, named-checkzone, resolución desde el portátil (no solo desde la VM).
- Imágenes del original no están en este repo: el dosier se entiende sin ellas.
-->

# Cómo se usa este dosier {.nobreak}

Hasta ahora tus sitios `web1.tuapellido.test` existen porque los escribiste a mano en `/etc/hosts` (en la VM y en el portátil). Eso es un sistema de nombres plano: un fichero, una lista, sin jerarquía. En Internet no hay un `/etc/hosts` mundial. Hay DNS.

Este dosier explica qué hay detrás de ese nombre, qué tipos de registro importan al desplegar, y cómo un servidor DNS (BIND9 en Debian) puede sustituir el fichero de hosts.

!!! abstract "Qué vas a aprender en esta UT"
    - Por qué `/etc/hosts` no escala y qué problema resuelve el DNS.
    - Cómo se lee un nombre: raíz, TLD, dominio, FQDN.
    - Qué es una zona y qué registros usas al desplegar: A, CNAME, NS, MX, PTR.
    - Cómo se resuelve una consulta (recursiva frente a autoritativa).
    - Cómo montar BIND9 en Debian para servir `tuapellido.test` en el aula.

## Cómo se organiza esta UT

| Bloque | Teoría | Al terminar |
|---|---|---|
| 1. El problema | Apartados 1 y 2 | Actividad: `getent hosts` y el fichero de hosts |
| 2. El espacio de nombres | Apartados 3 y 4 | Preguntas de FQDN, zona y registros |
| 3. Cómo se pregunta | Apartado 5 | Actividad: `dig` contra un servidor público |
| 4. Un DNS en el aula | Apartado 6 | [Práctica 4.1](T4-practica-bind.md): BIND9 en la VM |

## 1. Lo que ya haces con `/etc/hosts`

En las prácticas 2.x y 3.x has puesto líneas del estilo:

```
192.168.56.10  web1.garcia.test web2.garcia.test java.garcia.test
```

Cuando el navegador (o `curl`) pide `http://web1.garcia.test`, el sistema **no pregunta a Internet**. Mira primero `/etc/hosts`. Si el nombre está, usa esa IP y listo.

!!! definicion "Sistema de nombres plano"
    Una lista nombre-IP sin jerarquía. El ejemplo clásico es `/etc/hosts` (antes, el `HOSTS.TXT` de ARPANET).
    Sirve en una red pequeña. No sirve cuando hay millones de nombres o cuando la IP cambia.

Tres límites que ya has notado, aunque no los hayas llamado así:

1. **Hay que tocar dos sitios.** El hosts de la VM y el del portátil. Si se te olvida uno, «no resuelve».
2. **No hay un dueño del nombre.** Cualquiera puede escribir `google.com` apuntando a tu `.10`. El fichero no es autoridad de nada.
3. **Si la IP cambia, hay que avisar a todo el mundo.** En un VPS de verdad la IP pública no es tuya para siempre.

El DNS resuelve eso: un sistema jerárquico, con dueños por zona, que se puede consultar desde cualquier máquina.

## 2. Qué es el DNS

!!! definicion "DNS (Domain Name System)"
    Servicio que traduce nombres (como `www.santjosepobrer.es`) a datos de red, casi siempre una IP.
    También hace lo inverso (IP a nombre) y guarda otros datos: servidores de correo, alias, texto.

No solo «nombre a IP». Un dominio puede tener varias IP (redundancia o balanceo), puede cambiar de IP sin cambiar de nombre, y puede declarar qué máquina recibe el correo.

En clase nos importa sobre todo la **resolución directa**: que `java.tuapellido.test` llegue a `192.168.56.10` sin escribirlo en el hosts del portátil.

## 3. El árbol de nombres

Los nombres no son una lista: son un árbol invertido. Se leen **de derecha a izquierda**.

```
.                  raíz (root)
└── test.          TLD
    └── garcia.test.
        ├── web1.garcia.test.
        ├── java.garcia.test.
        └── node.garcia.test.
```

!!! definicion "FQDN (Fully Qualified Domain Name)"
    Nombre completo, con todas las etiquetas hasta la raíz. En los ficheros de zona se escribe con un punto final: `web1.garcia.test.`
    Sin el punto, el servidor DNS puede añadir el origen de la zona y montarte un nombre que no querías.

La raíz es un punto. Los que cuelgan de la raíz son los **TLD** (`.es`, `.com`, `.test`). `.test` está reservado para pruebas: no se publica en Internet. Por eso lo usamos en el aula.

Un **dominio** es un subárbol (`garcia.test.`). Un **subdominio** cuelga de él (`java.garcia.test.`).

### Zona y autoridad

!!! definicion "Zona"
    Trozo del árbol del que un servidor DNS es responsable. Se guarda en un fichero (o una base de datos).
    El servidor que la tiene completa es **autoritativo** para esa zona.

Zona y dominio no son lo mismo. Un dominio grande puede estar partido en varias zonas (el dueño **delega** un subdominio a otro servidor).

En el aula: tu VM será autoritativa para `tuapellido.test`. El resto de Internet no se entera: es un DNS de laboratorio.

## 4. Registros de recurso (RR)

Cada línea del fichero de zona es un **registro**. Formato general:

```
nombre    [TTL]    IN    tipo    dato
```

`IN` es la clase (Internet). El **TTL** dice cuántos segundos puede cachear la respuesta quien pregunte. Un TTL de 300 son 5 minutos: si cambias la IP, los clientes pueden seguir yendo a la antigua hasta que caduque.

Los tipos que vas a usar:

| Tipo | Qué guarda | Ejemplo en el aula |
|---|---|---|
| **SOA** | De quién es la zona, un número de serie, tiempos | Obligatorio al inicio del fichero |
| **NS** | Qué servidores DNS son autoritativos | `garcia.test. IN NS ns.garcia.test.` |
| **A** | Nombre → IPv4 | `web1 IN A 192.168.56.10` |
| **AAAA** | Nombre → IPv6 | En el aula no lo necesitamos |
| **CNAME** | Un nombre es alias de otro | `www IN CNAME web1` |
| **MX** | Quién recibe el correo del dominio | Fuera de este módulo |
| **PTR** | IP → nombre (resolución inversa) | `10.56.168.192.in-addr.arpa.` |
| **TXT** | Texto libre (SPF, claves, notas) | Diagnóstico |

!!! ojo "CNAME"
    Un CNAME no puede convivir con otros registros en el mismo nombre. No pongas CNAME en el ápex de la zona (`garcia.test.`). Para `www` sí.

El **SOA** lleva un **serial**. Cada vez que cambias la zona, lo subes (costumbre: `YYYYMMDDNN`). Los esclavos miran el serial para saber si tienen que copiar la zona. Aunque no montemos esclavo, BIND se queja si el SOA está mal.

## 5. Cómo se resuelve una pregunta

Hay dos papeles, y el mismo programa puede hacer los dos:

| Papel | Qué hace |
|---|---|
| **Autoritativo** | Tiene la zona. Si le preguntan por un nombre suyo, responde con seguridad. Si no es suyo, no inventa. |
| **Recursivo (resolver)** | Pregunta en tu nombre: raíz → TLD → autoritativo, y cachea la respuesta (TTL). |

Tu portátil no pregunta a la raíz cada vez. Pregunta al resolver de Windows (o al de la red), y ese sí hace el trabajo (o se lo pasa a otro).

!!! definicion "Consulta recursiva"
    El cliente pide «dame la respuesta final». El resolver se encarga de preguntar a quien haga falta.
    Una consulta **iterativa** es «dime a quién pregunto ahora»: así hablan los servidores entre ellos.

En el aula, con `dig`, vas a ver la diferencia:

```
dig web1.garcia.test @192.168.56.10
```

`@` dice **a qué servidor** preguntas. Si preguntas al BIND de tu VM, estás hablando con el autoritativo de tu zona. Si preguntas a `1.1.1.1`, ese resolver no conoce `garcia.test` y fallará (no está en Internet).

!!! comprueba "Comprueba"
    1. Si borras `web1.garcia.test` del hosts del portátil y BIND aún no está, ¿qué hará `curl`?
    2. ¿Por qué `.test` no se resuelve en Cloudflare?
    3. ¿Qué registro usarías para que `www.garcia.test` sea el mismo sitio que `web1.garcia.test`?

## 6. BIND9 en Debian

BIND es el servidor DNS clásico de Unix (`named`). En Debian 13 el paquete es `bind9`.

<!-- PENDIENTE DE VALIDAR EN LA VM: apt install bind9 bind9utils; rutas de Debian 13;
     named-checkconf / named-checkzone; systemctl status named o bind9 -->

Idea de la práctica 4.1 (en la misma VM `.10`, sin AWS):

1. Quitar de `/etc/hosts` (VM y portátil) los nombres `*.tuapellido.test`. Si no, el hosts gana y creerás que el DNS funciona cuando no.
2. Instalar `bind9` y `bind9utils`.
3. Declarar la zona `tuapellido.test` en `named.conf.local` y escribir el fichero de zona con SOA, NS y los A de `web1`, `web2`, `java`, `node`, `flask`, `ns`.
4. Comprobar con `named-checkconf` y `named-checkzone` **antes** de recargar.
5. `dig @127.0.0.1 web1.tuapellido.test` en la VM. Luego, en el portátil, poner como DNS `192.168.56.10` (o preguntar con `dig @192.168.56.10`) y entrar a `http://web1.tuapellido.test` **sin** hosts.

!!! ojo "El hosts gana"
    El orden habitual es: fichero de hosts, luego DNS. Si dejas las líneas de las prácticas 2.x, BIND puede estar mal y tú no te enteras.

!!! ejemplo "Esqueleto de zona (nombres de ejemplo)"
    ```
    $TTL 300
    @   IN SOA ns.garcia.test. profesor.garcia.test. (
            2026112601 ; serial
            3600       ; refresh
            600        ; retry
            86400      ; expire
            300 )      ; negative TTL
        IN NS  ns.garcia.test.
    ns      IN A  192.168.56.10
    web1    IN A  192.168.56.10
    web2    IN A  192.168.56.10
    java    IN A  192.168.56.10
    node    IN A  192.168.56.10
    flask   IN A  192.168.56.10
    www     IN CNAME web1
    ```

    `@` es el origen de la zona (`garcia.test.`). `profesor.garcia.test.` en el SOA es el correo del administrador, con el `@` escrito como punto.

## Referencias

- [RFC 1034: Domain names, concepts and facilities](https://www.rfc-editor.org/rfc/rfc1034)
- [RFC 1035: Domain names, implementation and specification](https://www.rfc-editor.org/rfc/rfc1035)
- [Debian: BIND9](https://wiki.debian.org/Bind9)
- [dig(1)](https://manpages.debian.org/trixie/bind9-dnsutils/dig.1.en.html)
