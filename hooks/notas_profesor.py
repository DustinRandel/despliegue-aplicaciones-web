"""Quita los comentarios HTML (<!-- ... -->) de las páginas antes de construir la web.

Las notas para el profesor van en comentarios HTML dentro de los .md. Sin este hook,
MkDocs los copia tal cual al HTML publicado y cualquiera los ve con "Ver código fuente".
Los comentarios dentro de bloques de código no se tocan.
"""
import re

_BLOQUE_CODIGO = re.compile(r"(^```.*?^```)", re.S | re.M)
_COMENTARIO = re.compile(r"<!--.*?-->\n?", re.S)


def on_page_markdown(markdown, **kwargs):
    partes = _BLOQUE_CODIGO.split(markdown)
    # Las posiciones impares son bloques de código: se dejan intactas
    return "".join(p if i % 2 else _COMENTARIO.sub("", p) for i, p in enumerate(partes))
