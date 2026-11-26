---
title: "Control de versiones (Git y GitHub)"
subtitulo: "UT5. Dosier de apuntes"
modulo: "0614. Despliegue de aplicaciones web"
curso: "2026-2027"
profesor: "Dustin Randel de Lara García"
centro: "Sant Josep Obrer"
ut: "UT5"
---

<!--
NOTA PARA EL PROFESOR:
- Fuente: git.md, github.md y P5.1–P5.3 del original. Reescrito para este curso:
  Git en Debian y en Windows, GitHub con SSH (ed25519, no RSA), el flujo que ya usa
  la web del módulo (push a main).
- P5.1 original: repo DEAW, tags, seguir compañeros, colaborador raul-profesor.
  La práctica de este curso pide un repo propio, .gitignore, push por SSH y 2FA.
  No se pide añadir a raul-profesor.
- PENDIENTE DE VALIDAR EN LA VM: git no viene instalado en DAW-debian.ova (CLAUDE.md).
  apt install git. ssh-keygen ed25519 desde el portátil, clave pública en GitHub.
-->

# Cómo se usa este dosier {.nobreak}

Hasta ahora el código de las prácticas vive en la VM. Si la rascas, se pierde. Git guarda la historia. GitHub es la copia remota y, más adelante, el sitio desde el que se despliega (Tema 7).

La web de este módulo se publica así: un `git push` a `main` y GitHub Actions genera las páginas. En esta UT aprendes la parte de Git; el «y entonces se despliega solo» es la UT7.

!!! abstract "Qué vas a aprender en esta UT"
    - Qué problema resuelve Git que no cubre una carpeta con fecha.
    - El ciclo diario: status, add, commit, log, diff.
    - Ramas: para no romper `main`.
    - Remoto: GitHub por SSH, push y pull.
    - Qué no se sube: `.gitignore`.

## Cómo se organiza esta UT

| Bloque | Teoría | Al terminar |
|---|---|---|
| 1. Por qué Git | Apartados 1 y 2 | Identidad (`user.name`) y primer commit |
| 2. El ciclo diario | Apartado 3 | Actividad: status, add, commit, log |
| 3. Ramas | Apartado 4 | Una rama, un merge |
| 4. GitHub | Apartados 5 y 6 | [Práctica 5.1](T5-practica-github.md) |

## 1. El problema

Sin Git, «la versión que funciona» es un zip en el escritorio. No sabes qué cambió el martes ni cómo volver atrás.

!!! definicion "Repositorio"
    Carpeta donde Git guarda la historia de los ficheros (el directorio oculto `.git`).
    Cada **commit** es una foto de ese estado, con autor, fecha y mensaje.

Git trabaja en local. GitHub es un servidor con repositorios Git, issues y, en este módulo, Actions.

## 2. Identidad e instalación

En la VM Git no viene de serie:

```
sudo apt install git
git --version
```

En Windows, Git for Windows (incluye `git` en PowerShell). La identidad va en cada máquina:

```
git config --global user.name "Nombre Apellido"
git config --global user.email "tuusuario@github.com"
git config --global init.defaultBranch main
```

El nombre y el correo quedan grabados en cada commit. Usa el correo de GitHub (o el noreply que te da la cuenta).

## 3. El ciclo diario

```
git init
git status
git add README.md
git commit -m "Primer commit: README del repo de prácticas"
git log --oneline
```

!!! definicion "Área de preparación (staging)"
    Lo que `git add` marca para el próximo commit. `status` te dice qué está sin seguir, qué está preparado y qué ya está confirmado.

`git diff` (sin add) es lo que has tocado. `git diff --staged` es lo que va a entrar en el commit.

Mensajes: una frase que diga el qué. «Primer commit: README del repo de prácticas», no «cambios» ni «fix».

## 4. Ramas

`main` es la línea que funciona. Para probar, ramas:

```
git branch prueba
git switch prueba
# cambias ficheros, commit
git switch main
git merge prueba
```

Si el merge no se puede hacer solo, Git te deja el conflicto en el fichero (`<<<<<<<`). Lo editas, `add` y `commit`.

En GitHub, el mismo gesto es un *pull request*. En el aula basta con ramas locales y, en la práctica, una rama remota.

## 5. GitHub por SSH

La clave es la misma idea que en SSH de la UT1: un par ed25519. La privada no sale del portátil.

```
ssh-keygen -t ed25519 -C "tuusuario@github.com"
```

La pública (`~/.ssh/id_ed25519.pub`) se pega en GitHub: Settings, SSH and GPG keys. Prueba:

```
ssh -T git@github.com
```

El remoto se añade con SSH, no con HTTPS (HTTPS te pedirá tokens a cada push):

```
git remote add origin git@github.com:TUUSUARIO/deaw.git
git push -u origin main
```

!!! ojo "HTTPS frente a SSH"
    `https://github.com/usuario/deaw.git` funciona para clonar en público. Para subir, en este módulo usamos `git@github.com:usuario/deaw.git`.

2FA en la cuenta: obligatorio. Foto de perfil: para que en clase se sepa quién es quién.

## 6. Qué no se sube

`.gitignore` lista lo que Git no tiene que ver: secretos, `node_modules`, `.env`, la carpeta `privada/`.

```
privado.txt
privada/
.env
```

Si ya hiciste add de un secreto, ignorarlo después no lo saca de la historia. No subas contraseñas. Nunca.

!!! comprueba "Comprueba"
    1. ¿`git status` limpio significa que GitHub está al día?
    2. ¿La clave privada se pega en GitHub?
    3. Si ignoras `privado.txt` después de un commit, ¿desaparece del remoto?

## Referencias

- [Pro Git (libro, en español)](https://git-scm.com/book/es/v2)
- [GitHub: conectar con SSH](https://docs.github.com/es/authentication/connecting-to-github-with-ssh)
- [gitignore(5)](https://git-scm.com/docs/gitignore)
