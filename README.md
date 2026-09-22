# Despliegue de aplicaciones web (0614)

Apuntes y prácticas del módulo **Despliegue de aplicaciones web**, 2º del ciclo de grado superior de **Desarrollo de Aplicaciones Web (DAW)**.

Sitio generado con [MkDocs](https://www.mkdocs.org/) y el tema [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/).

## Ver la web en local

```sh
pip install -r requirements.txt
mkdocs serve
```

Abre <http://127.0.0.1:8000>. Cada vez que guardes un fichero de `docs/`, la página se recarga sola.

## Publicar

Al hacer `push` a la rama `main`, GitHub Actions construye y publica la web automáticamente
(ver `.github/workflows/deploy.yml`). También puede publicarse a mano con:

```sh
mkdocs gh-deploy
```

## Estructura

| Carpeta / fichero | Qué es |
|---|---|
| `docs/*.md` | El contenido: un fichero por página |
| `docs/.pages` | El menú lateral: qué páginas hay y en qué orden |
| `docs/img/` | Imágenes y capturas de pantalla |
| `mkdocs.yml` | Configuración del sitio |
| `site/` | Web generada. **No se sube al repositorio** |

## Créditos y licencia

Este material parte del repositorio [raul-profesor/Despliegue](https://github.com/raul-profesor/Despliegue)
y de los talleres del [Aula de Software Libre de la Universidad de Córdoba](https://www.uco.es/aulasoftwarelibre).
Los detalles están en [docs/creditos.md](docs/creditos.md) y se muestran también en la web.
