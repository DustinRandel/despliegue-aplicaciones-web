"""Hook de MkDocs de la plantilla común de dosieres (y filtro del PDF).

1. Quita los comentarios HTML (<!-- ... -->), que son las notas para el profesor: sin esto, MkDocs los copia al HTML
   publicado y cualquiera los ve con «Ver código fuente». Los de dentro de bloques de código no se tocan.
2. Solo en la web: si la página tiene varios títulos de nivel 1 (en el dosier, cada bloque es un «# Bloque N…»), los
   baja un nivel y pone un único título arriba («UT3. El modelo relacional», con «ut» y «title» de la cabecera).
   Con varios H1, el tema Material esconde la página en el menú de la izquierda y la tabla de la derecha pierde los
   subapartados. El PDF (pdf/generar_pdf.py) llama a esta función sin «page» y se queda con los # originales, que
   es lo que usa su CSS para empezar cada bloque en página nueva.
"""
import re

_BLOQUE_CODIGO = re.compile(r"(^```.*?^```)", re.S | re.M)
_COMENTARIO = re.compile(r"<!--.*?-->\n?", re.S)
_H1 = re.compile(r"^# ", re.M)
_ENCABEZADO = re.compile(r"^(#{1,5}) ", re.M)


def _fuera_de_codigo(markdown, funcion):
    partes = _BLOQUE_CODIGO.split(markdown)
    # Las posiciones impares son bloques de código: se dejan intactas
    return "".join(p if i % 2 else funcion(p) for i, p in enumerate(partes))


def quitar_notas(markdown):
    return _fuera_de_codigo(markdown, lambda p: _COMENTARIO.sub("", p))


def on_page_markdown(markdown, page=None, **kwargs):
    texto = quitar_notas(markdown)
    if page is None:  # PDF: solo quitar las notas
        return texto
    h1 = sum(len(_H1.findall(p)) for i, p in enumerate(_BLOQUE_CODIGO.split(texto)) if not i % 2)
    if h1 <= 1:
        return texto
    texto = _fuera_de_codigo(texto, lambda p: _ENCABEZADO.sub(lambda m: "#" + m.group(1) + " ", p))
    meta = page.meta or {}
    titulo = meta.get("title") or page.title or ""
    if meta.get("ut") and titulo and not str(titulo).startswith(str(meta["ut"])):
        titulo = f"{meta['ut']}. {titulo}"
    return (f"# {titulo}\n\n" if titulo else "") + texto
