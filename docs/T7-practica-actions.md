---
title: "Práctica 7.1: Actions y GitHub Pages"
---

<!--
NOTA PARA EL PROFESOR:
- Sustituye P7.1 original (más Jenkins). Pages + Actions, sin cuenta Netlify.
- PENDIENTE DE VALIDAR: Settings del repo (Pages, source GitHub Actions) y el primer deploy.
-->

# Práctica 7.1: Actions y GitHub Pages

!!! tip "Cuándo se hace"
    Al terminar el [Tema 7](T7-cicd.md). Usa el repo `deaw` de la práctica 5.1.

!!! abstract "Objetivos"
    1. Un workflow que compruebe que existe `README.md`.
    2. Un `index.html` mínimo publicado en GitHub Pages.
    3. Ver el job en verde y la URL pública.

## 1. CI

En `deaw`, `.github/workflows/ci.yml` como en el apartado 3 del dosier. Push a `main`. Captura de Actions en verde.

## 2. Una página

`index.html` con tu nombre, el módulo 0614 y las iniciales `<ini>` visibles. Commit.

## 3. Publicar

Workflow `pages.yml` que, en push a `main`:

1. Checkout.
2. Sube `index.html` como artefacto de Pages (o genera una carpeta `site/` con ese fichero).
3. Despliega a GitHub Pages.

En el repo: Settings, Pages, source **GitHub Actions**.

La URL será `https://TUUSUARIO.github.io/deaw/`.

## 4. Qué entregar

PDF `UT7-P7.1-Apellido-Nombre.pdf` con:

1. Actions del `ci.yml` en verde.
2. Actions del deploy en verde.
3. Captura del sitio público con `<ini>` en el HTML.
4. El YAML (texto).
