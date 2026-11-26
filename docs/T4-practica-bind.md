---
title: "Práctica 4.1: BIND9 en la máquina virtual"
---

<!--
NOTA PARA EL PROFESOR:
- Sustituye P4.1 original (BIND en EC2 + Amazon Linux + Windows). Aquí: la misma VM Debian .10.
- PENDIENTE DE VALIDAR EN LA VM: paquetes bind9 bind9utils bind9-dnsutils en Debian 13.7;
  nombre del servicio (named o bind9); listen-on y allow-query; named-checkzone;
  resolución desde Windows con dig.exe o nslookup contra 192.168.56.10.
- PENDIENTE DE CAPTURA: docs/img/T4-dig-vm.png (dig @127.0.0.1 web1.apellido.test con status NOERROR)
  y docs/img/T4-dig-win.png (mismo nombre desde el portátil, sin línea en hosts).
- El alumnado tiene que borrar *.tuapellido.test de hosts ANTES de fiarse del DNS.
-->

# Práctica 4.1: BIND9 en la máquina virtual

!!! tip "Cuándo se hace"
    Al terminar el bloque 4 de la [teoría del Tema 4](T4-dns.md). Se hace en la máquina principal (`192.168.56.10`).

!!! abstract "Objetivos"
    1. Quitar los nombres de `/etc/hosts` para no enmascarar el DNS.
    2. Instalar BIND9 en Debian y declarar una zona `tuapellido.test`.
    3. Servir los A de `web1`, `web2`, `java`, `node` y `flask` hacia `.10`.
    4. Comprobar con `dig` en la VM y desde el portátil, sin hosts.

## 1. Quita el hosts

En la VM y en el portátil, comenta o borra las líneas `*.tuapellido.test` de `/etc/hosts` (en Windows: `C:\Windows\System32\drivers\etc\hosts`).

Comprueba que ya no resuelve:

```
getent hosts web1.tuapellido.test
```

Tiene que salir vacío. Si sigue saliendo `.10`, el hosts aún gana.

## 2. Instala BIND9

<!-- PENDIENTE DE VALIDAR EN LA VM: nombres de paquete y del servicio -->

```
sudo apt update
sudo apt install bind9 bind9utils bind9-dnsutils
```

Comprueba el servicio:

```
systemctl status named
```

Si el unit se llama `bind9`, usa ese nombre a partir de aquí.

## 3. Opciones: a quién escuchas

Copia de seguridad y edita `/etc/bind/named.conf.options`.

En el aula solo tienen que preguntarte las máquinas de Host-Only y la propia VM:

```
acl aula {
    127.0.0.0/8;
    192.168.56.0/24;
};

options {
    directory "/var/cache/bind";
    listen-on { 127.0.0.1; 192.168.56.10; };
    allow-query { aula; };
    recursion no;
    dnssec-validation auto;
};
```

`recursion no`: este BIND es autoritativo de tu zona, no un resolver de Internet.

<!-- VALIDAR VM: si Debian 13 trae listen-on-v6 y dnssec distintos, ajustar. -->

## 4. La zona

En `/etc/bind/named.conf.local`:

```
zone "tuapellido.test" {
    type master;
    file "/etc/bind/db.tuapellido.test";
};
```

Crea `/etc/bind/db.tuapellido.test` a partir del esqueleto del [apartado 6 del dosier](T4-dns.md). Cambia `garcia` por tu apellido y el serial a la fecha de hoy (`YYYYMMDD01`).

Comprueba **antes** de recargar:

```
sudo named-checkconf
sudo named-checkzone tuapellido.test /etc/bind/db.tuapellido.test
```

Si sale `OK`:

```
sudo systemctl reload named
```

## 5. Comprueba

En la VM:

```
dig @127.0.0.1 web1.tuapellido.test +short
dig @127.0.0.1 www.tuapellido.test +short
```

La primera tiene que dar `192.168.56.10`. La segunda, si pusiste el CNAME, el nombre canónico y luego la IP.

Desde el portátil (PowerShell), sin línea en hosts:

```
dig.exe @192.168.56.10 web1.tuapellido.test +short
```

Si no tienes `dig.exe`, `nslookup web1.tuapellido.test 192.168.56.10`.

Abre `http://web1.tuapellido.test` (el Nginx de la práctica 2.1). Si el DNS responde y Nginx sigue, la página sale **sin** hosts.

## 6. Qué entregar

Un PDF `UT4-P4.1-Apellido-Nombre.pdf` con:

1. Captura de `getent hosts` vacío (apartado 1).
2. Salida de `named-checkzone` con `OK`.
3. `dig @127.0.0.1 web1.tuapellido.test` (status `NOERROR`).
4. La misma consulta desde el portátil.
5. Captura del navegador en `http://web1.tuapellido.test` con las iniciales `<ini>` visibles.

Iniciales en cada captura.
