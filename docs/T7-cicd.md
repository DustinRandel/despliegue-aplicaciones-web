---
title: "CI/CD"
subtitulo: "UT7. Dosier de apuntes"
modulo: "0614. Despliegue de aplicaciones web"
curso: "2026-2027"
profesor: "Dustin Randel de Lara García"
centro: "Sant Josep Obrer"
ut: "UT7"
---

<!--
NOTA PARA EL PROFESOR:
- Fuente: cicd.md y P7.1 del original (Jenkins, más teórico). Aquí el hilo es GitHub Actions,
  el mismo mecanismo que publica la web de este módulo (mkdocs gh-deploy en push a main).
- P3.4 Netlify se rechazó: no se recupera. Un Pages + Actions cubre la idea sin cuenta extra.
- PENDIENTE DE VALIDAR: un repo de alumno con Actions y GitHub Pages (entorno github-pages).
-->

# Cómo se usa este dosier {.nobreak}

En la UT5 empujas a GitHub a mano. CI/CD es que **cada push** construya, compruebe y, si quieres, despliegue. La web de este módulo ya lo hace: push a `main` y en unos minutos está GitHub Pages.

!!! abstract "Qué vas a aprender en esta UT"
    - Qué es integrar continuo y qué es desplegar continuo.
    - Un flujo: commit, prueba, artefacto, publicar.
    - GitHub Actions: un YAML en `.github/workflows/`.
    - Cómo se publica un sitio estático en Pages (el mismo patrón que MkDocs).

## Cómo se organiza esta UT

| Bloque | Teoría | Al terminar |
|---|---|---|
| 1. Las palabras | Apartado 1 | CI, CD, entrega continua, en una frase cada una |
| 2. El flujo | Apartado 2 | Dibujo: push → Actions → Pages |
| 3. Actions | Apartado 3 | Un workflow mínimo que falla si no hay README |
| 4. Publicar | Apartado 4 | [Práctica 7.1](T7-practica-actions.md) |

## 1. Las palabras

!!! definicion "Integración continua (CI)"
    Cada vez que entra código al repositorio, un sistema lo construye y lanza pruebas.
    Si algo se rompe, te enteras en minutos, no el viernes.

**Despliegue continuo**: si las pruebas pasan, se publica (a un entorno de pruebas o a producción). **Entrega continua**: el artefacto queda listo; alguien pulsa el botón.

En el aula usamos CI + publicar a GitHub Pages. No hay botón: el push a `main` publica. Eso es más «despliegue continuo» que «entrega».

## 2. El flujo, con lo que ya sabes

```
commit y push (UT5)
    → Actions instala, construye, prueba
    → si va bien, publica el artefacto
    → GitHub Pages (o un servidor tuyo)
```

Es el guion de la UT3 (entorno, construir, servicio, comprobar) **sin hacerlo tú a mano**. Docker (UT6) encaja como forma de construir el mismo entorno en Actions y en producción.

## 3. Un workflow mínimo

`.github/workflows/ci.yml`:

```
name: ci
on:
  push:
    branches: [main]
  pull_request:
jobs:
  comprobar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: README presente
        run: test -f README.md
```

Cada push lanza un *job* en una VM de GitHub. Los registros se ven en la pestaña Actions. Si `test -f README.md` falla, el check queda rojo.

La web de este módulo hace más: instala MkDocs y ejecuta `mkdocs gh-deploy`. Misma idea, otro comando.

## 4. Publicar un sitio estático

GitHub Pages sirve HTML. Un workflow puede:

1. Construir (`mkdocs build`, `npm run build`, copiar `index.html`).
2. Subir el resultado con `actions/upload-pages-artifact` y `actions/deploy-pages`, o con `peaceiris/actions-gh-pages`.

El sitio queda en `https://USUARIO.github.io/REPO/`.

!!! ojo "Secretos"
    Un token no se escribe en el YAML. Va en Settings, Secrets. El registro de Actions es público si el repo lo es: no imprimas claves.

!!! comprueba "Comprueba"
    1. ¿Un push a una rama que no es `main` publica Pages, con el YAML de arriba?
    2. ¿CI sustituye a `nginx -t` en tu VM?
    3. ¿Por qué Netlify no está en esta práctica?

## Referencias

- [GitHub Actions: understanding GitHub Actions](https://docs.github.com/es/actions/get-started/understand-github-actions)
- [GitHub Pages](https://docs.github.com/es/pages)
- Workflow de este módulo: `.github/workflows/deploy.yml` en el repo `despliegue-aplicaciones-web`
