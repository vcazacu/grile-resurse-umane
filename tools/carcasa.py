"""Carcasa comună a paginilor generate (tematica/, legislatie/): <head>, navigația aplicației și subsolul.
Navigația e aceeași ca în ../index.html (jos pe telefon, laterală pe desktop) — dacă o schimbi acolo,
schimb-o și aici. Stilurile sunt toate în ../style.css."""
import html

ICON = {
    "teste": '<rect x="4" y="4" width="6" height="6" rx="1.5"></rect><rect x="14" y="4" width="6" height="6" rx="1.5"></rect>'
             '<rect x="4" y="14" width="6" height="6" rx="1.5"></rect><rect x="14" y="14" width="6" height="6" rx="1.5"></rect>',
    "tematica": '<path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H11v16H5.5A1.5 1.5 0 0 1 4 18.5z"></path>'
                '<path d="M20 5.5A1.5 1.5 0 0 0 18.5 4H13v16h5.5a1.5 1.5 0 0 0 1.5-1.5z"></path>',
    "legislatie": '<line x1="12" y1="3" x2="12" y2="21"></line><line x1="5" y1="7" x2="19" y2="7"></line>'
                  '<path d="M5 7l-3 7a3 3 0 0 0 6 0z"></path><path d="M19 7l-3 7a3 3 0 0 0 6 0z"></path><line x1="8" y1="21" x2="16" y2="21"></line>',
    "stanga": '<polyline points="15 6 9 12 15 18"></polyline>',
    "dreapta": '<polyline points="9 6 15 12 9 18"></polyline>',
    "sageata": '<line x1="5" y1="12" x2="19" y2="12"></line><polyline points="13 6 19 12 13 18"></polyline>',
}

def icon(nume, marime=20):
    return ('<svg width="%d" height="%d" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%s</svg>' % (marime, marime, ICON[nume]))

SECTIUNI = [("teste", "../index.html", "Teste"), ("tematica", "../tematica/index.html", "Tematica"),
            ("legislatie", "../legislatie/index.html", "Legislația")]

def nav(activ, pe_index):
    """activ: secțiunea curentă; pe_index: pagina e chiar indexul secțiunii (aria-current="page")."""
    linkuri = []
    for cheie, href, nume in SECTIUNI:
        cur = ' aria-current="%s"' % ("page" if pe_index else "true") if cheie == activ else ""
        linkuri.append('<a class="nav-link" href="%s"%s>%s<span>%s</span></a>' % (href, cur, icon(cheie), nume))
    return ('<nav class="nav-app" aria-label="Secțiuni"><div class="brand"><span class="eyebrow">Examen resurse umane</span>'
            '<span class="brand-nume">Grile Resurse Umane</span></div>%s</nav>' % "".join(linkuri))

def cap(eyebrow, titlu, inapoi=None, meta=""):
    """Antetul paginii: link înapoi (href, text), eticheta de deasupra, titlul și o linie de meta (HTML gata redat)."""
    h = ['<header class="pagina-cap">']
    if inapoi: h.append('<a class="inapoi" href="%s">%s%s</a>' % (inapoi[0], icon("stanga", 16), html.escape(inapoi[1])))
    h.append('<span class="eyebrow">%s</span><h1>%s</h1>' % (html.escape(eyebrow), html.escape(titlu)))
    if meta: h.append('<div class="pagina-meta">%s</div>' % meta)
    h.append("</header>")
    return "".join(h)

def pagina(titlu, corp, activ, pe_index=False, subsol="", script="", cls=""):
    return f"""<!DOCTYPE html>
<html lang="ro"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#F2F4F7" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#0E1320" media="(prefers-color-scheme: dark)">
<link rel="icon" href="../icon-192.png"><link rel="stylesheet" href="../style.css">
<title>{html.escape(titlu)} — Grile Resurse Umane</title></head>
<body><div class="shell">{nav(activ, pe_index)}
<main class="continut lectura{' ' + cls if cls else ''}">{corp}
<footer>{subsol}</footer></main></div>{'<script>' + script + '</script>' if script else ''}</body></html>"""
