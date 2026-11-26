---
title: "Práctica 5.1: Git y GitHub"
---

<!--
NOTA PARA EL PROFESOR:
- Parte de P5.1 original (repo DEAW, README, gitignore, tag, 2FA, seguir compañeros).
- No se pide colaborador raul-profesor. SSH ed25519, no RSA.
- PENDIENTE DE VALIDAR EN LA VM: git no instalado; hacerlo en el portátil es válido
  (GitHub se usa desde Windows). Si lo hacen en la VM, apt install git.
-->

# Práctica 5.1: Git y GitHub

!!! tip "Cuándo se hace"
    Al terminar el bloque 4 de la [teoría del Tema 5](T5-git.md). Se puede hacer en el portátil (Git for Windows) o en la VM.

!!! abstract "Objetivos"
    1. Crear un repositorio `deaw` en tu GitHub, vacío, privado o público.
    2. Clonarlo por SSH, no por HTTPS.
    3. README, `.gitignore`, un commit y un push.
    4. Activar 2FA y poner foto de perfil.

## 1. Cuenta y clave

Foto de perfil. 2FA (Settings, Password and authentication). Clave ed25519 y pública en SSH and GPG keys. Comprueba:

```
ssh -T git@github.com
```

## 2. Repositorio

En GitHub: New repository, nombre `deaw`, sin README (lo harás en local). Clona:

```
git clone git@github.com:TUUSUARIO/deaw.git
cd deaw
```

Si ya lo creaste con README, clona igual y sigue.

## 3. README e identidad

```
git config user.name "Nombre Apellido"
git config user.email "tu correo de GitHub"
```

`README.md`: dos o tres frases sobre el módulo 0614 y tu apellido. Commit:

```
git add README.md
git commit -m "Primer commit: README del repo de prácticas"
git push -u origin main
```

Si la rama se llama `master`, `git branch -M main` antes del push.

## 4. Ignorar

Crea `privado.txt` y la carpeta `privada/` con un fichero dentro. `.gitignore`:

```
privado.txt
privada/
```

Commit del gitignore (no de lo privado) y push. `git status` tiene que ignorarlos.

## 5. Tag

Un fichero `1.txt` con tu nombre. Commit. Tag `v0.1` y súbelo:

```
git tag v0.1
git push origin v0.1
```

## 6. Compañeros

Sigue a dos compañeros. Estrella a su `deaw` si lo tienen público. En el README, una tabla con tres nombres y el enlace a su GitHub.

## 7. Qué entregar

PDF `UT5-P5.1-Apellido-Nombre.pdf` con:

1. Captura de `ssh -T git@github.com` (éxito).
2. La URL del repo.
3. `git log --oneline` y `git status` (limpio, privado ignorado).
4. El tag `v0.1` visible en GitHub.
5. 2FA activado (captura de Settings, sin secretos).

Iniciales `<ini>` en las capturas.
