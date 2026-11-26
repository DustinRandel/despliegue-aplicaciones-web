#!/usr/bin/env python3
"""Genera el PDF de un dosier a partir del MISMO .md que publica la web (MkDocs).

Uso (desde la raíz del repo, con el entorno de requirements-pdf.txt instalado):
    python3 pdf/generar_pdf.py docs/UT1-dosier.md            -> pdf/salida/UT1-Dosier.pdf
    python3 pdf/generar_pdf.py docs/UT1-dosier.md otro.pdf   -> otro.pdf

Basado en generar_pdf.py del dosier de CONT:
  1. Lee la cabecera YAML del .md (title, modulo, ut, subtitulo, curso, profesor, centro).
  2. Quita las notas para el profesor (comentarios HTML), igual que el hook de la web.
  3. Convierte el Markdown a HTML con las mismas extensiones que mkdocs.yml, así que
     las cajas (!!! definicion, ejemplo, ojo, comprueba, predice) salen igual.
  4. Imprime con Chrome (Playwright): portada sin cabecera ni pie y cuerpo con cabecera y pie.
  5. Une las dos partes y pone autor y título en los metadatos del PDF.
Las imágenes se buscan relativas al .md (docs/imagenes/...).
"""
import asyncio, html, os, re, sys, tempfile
from pathlib import Path
import markdown, yaml, pikepdf
from playwright.async_api import async_playwright

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'hooks'))
from notas_profesor import on_page_markdown as quitar_notas  # mismo filtro que la web

if len(sys.argv) < 2:
    sys.exit(__doc__)
MD = Path(sys.argv[1]).resolve()
CSS = Path(__file__).resolve().parent / 'dosier-pdf.css'
CHROME = os.environ.get('CHROME')  # opcional: ruta a Chrome; si no, el Chromium de Playwright

src = MD.read_text(encoding='utf8')
m = re.match(r'^---\n(.*?)\n---\n', src, re.S)
meta = yaml.safe_load(m.group(1)) if m else {}
cuerpo_md = quitar_notas(src[m.end():] if m else src)
ut = meta.get('ut', 'UT')
PDF = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else RAIZ / 'pdf' / 'salida' / f'{ut}-Dosier.pdf'
PDF.parent.mkdir(parents=True, exist_ok=True)
AUTOR = meta.get('profesor', 'Dustin Randel de Lara García')
e = lambda k, d='': html.escape(str(meta.get(k, d)))

cuerpo = markdown.markdown(cuerpo_md, extensions=[
    'tables', 'admonition', 'attr_list', 'md_in_html', 'footnotes', 'pymdownx.details',
    'pymdownx.superfences', 'pymdownx.inlinehilite', 'pymdownx.keys', 'pymdownx.tabbed',
    'pymdownx.highlight'], extension_configs={'pymdownx.highlight': {'use_pygments': False}})

LOGO = RAIZ / 'docs' / 'assets' / 'logo-claro.png'  # variante azul marino: la portada es clara
logo_html = f'<img class="logo" src="{LOGO.as_uri()}" alt="">' if LOGO.exists() else ''
portada = f'''<section class="cover">
<div class="top"><div class="mod">{e("modulo")}</div>{logo_html}</div>
<div class="mid"><div class="sub">{e("subtitulo", "Dosier de apuntes")}</div>
<h1 class="ctitle">{e("title")}</h1><div class="rule"></div></div>
<table class="meta"><tr><td>Curso</td><td>{e("curso")}</td></tr><tr><td>Profesor</td><td>{e("profesor")}</td></tr><tr><td>Centro</td><td>{e("centro")}</td></tr></table>
</section>'''
cabeza = (f'<!doctype html><html lang="es"><head><meta charset="utf-8">'
          f'<base href="{MD.parent.as_uri()}/"><title>{e("title")}</title>'
          f'<style>{CSS.read_text(encoding="utf8")}</style></head><body>')
estilo = 'font-family:Carlito,Calibri,sans-serif;font-size:8pt;color:#5B6776;width:100%;padding:0 18mm;display:flex;justify-content:space-between'
CABECERA = f'<div style="{estilo}"><span>{e("modulo")}</span><span>{e("title")}</span></div>'
PIE = f'<div style="{estilo}"><span>{e("centro")}, curso {e("curso")}</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>'

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    (tmp / 'portada.html').write_text(cabeza + portada + '</body></html>', encoding='utf8')
    (tmp / 'cuerpo.html').write_text(cabeza + '<main>' + cuerpo + '</main></body></html>', encoding='utf8')

    async def imprimir():
        async with async_playwright() as p:
            kw = {'args': ['--no-sandbox']}
            if CHROME: kw['executable_path'] = CHROME
            nav = await p.chromium.launch(**kw); pg = await nav.new_page()
            await pg.goto((tmp / 'portada.html').as_uri()); await pg.wait_for_timeout(300)
            await pg.pdf(path=str(tmp / 'portada.pdf'), format='A4', print_background=True,
                         margin={'top': '0', 'bottom': '0', 'left': '0', 'right': '0'})
            await pg.goto((tmp / 'cuerpo.html').as_uri()); await pg.wait_for_timeout(800)
            await pg.pdf(path=str(tmp / 'cuerpo.pdf'), format='A4', print_background=True,
                         display_header_footer=True, header_template=CABECERA, footer_template=PIE,
                         margin={'top': '22mm', 'bottom': '20mm', 'left': '18mm', 'right': '18mm'})
            await nav.close()
    asyncio.run(imprimir())

    out = pikepdf.new()
    partes = [pikepdf.open(tmp / f) for f in ('portada.pdf', 'cuerpo.pdf')]
    for s in partes: out.pages.extend(s.pages)
    out.docinfo['/Title'] = str(meta.get('title', '')); out.docinfo['/Author'] = AUTOR; out.docinfo['/Creator'] = AUTOR
    out.docinfo['/Producer'] = AUTOR
    with out.open_metadata(set_pikepdf_as_editor=False) as x:
        x['dc:creator'] = [AUTOR]; x['dc:title'] = str(meta.get('title', ''))
    out.save(PDF)
    for s in partes: s.close()
print('PDF generado:', PDF)
