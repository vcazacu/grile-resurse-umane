#!/usr/bin/env python3
"""Descarcă forma consolidată LA ZI a unui act de pe legislatie.just.ro și o
transformă în text structurat, pe linii, potrivit pentru verificări automate.

Utilizare:
    python3 descarca.py <id_DetaliiDocument> <nume_fisier_fara_extensie> [--dir ../legislatie]

Pornind de la ORICE id al actului (original sau o consolidare veche), scriptul
citește lista „istoric consolidări" și alege consolidarea cea mai recentă.
Scrie două fișiere în --dir:
    <nume>.html  — HTML-ul brut, așa cum a fost descărcat (arhivă, sursa de adevăr)
    <nume>.txt   — textul structurat:
        • linia 1: antet cu id-ul, data consolidării și data descărcării
        • „Articolul N" pe linie proprie (titlu real de articol)
        • fiecare alineat / literă / liniuță pe linie proprie
        • notele de modificare și notele portalului încep cu „§NOTA§ " —
          NU sunt text normativ și sunt ignorate la verificarea citatelor
        • „§ANEXA§ <titlu>" marchează începutul unei anexe (numerotare separată)
"""
import html.parser, re, sys, time, subprocess, datetime, pathlib

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"
BASE = "https://legislatie.just.ro/Public/DetaliiDocument/"


def fetch(url):
    # curl, nu urllib: Python-ul de pe această mașină nu are lanțul de certificate SSL
    r = subprocess.run(["curl", "-sSL", "--max-time", "120", "-A", UA, url], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("curl a eșuat pentru %s: %s" % (url, r.stderr.decode(errors="replace")))
    return r.stdout.decode("utf-8", errors="replace")


def consolidari(h):
    """Întoarce lista [(data, id sau None dacă e cea afișată)] din „istoric consolidări"."""
    blk = re.search(r'id="istoric_fa".*?</div>', h, re.S)
    if not blk:
        return []
    out = []
    for m in re.finditer(r"<a title='Consolidarea din ([\d.]+)'([^>]*)>", blk.group(0)):
        h2 = re.search(r"DetaliiDocument/(\d+)", m.group(2))
        out.append((m.group(1), h2.group(1) if h2 else None))
    return out


class Extractor(html.parser.HTMLParser):
    """Parcurge HTML-ul și emite linii de text pentru elementele S_*."""
    BLOCK_SUFFIX = ("_TTL", "_DEN", "_PAR", "_BDY")
    BLOCK_EXACT = {"S_PAR", "S_DEN", "S_HDR"}
    # titluri care se lipesc în fața corpului: „(1) text", „a) text", „– text", „1. text"
    PREFIX_TTL = {"S_ALN_TTL", "S_LIT_TTL", "S_LIN_TTL", "S_PCT_TTL", "S_PAR_TTL"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines = []
        self.stack = []      # [ [cls, buf(list), hidden(bool)] ]
        self.prefix = ""     # „a)" în așteptarea corpului literei
        self.skip_depth = 0  # în interiorul script/style
        self.hidden_depth = 0

    def is_block(self, cls):
        return cls in self.BLOCK_EXACT or (cls.startswith("S_") and cls.endswith(self.BLOCK_SUFFIX))

    VOID = {"br", "img", "input", "meta", "link", "hr", "col", "area", "base", "param", "source", "track", "wbr"}

    def handle_startendtag(self, tag, attrs):
        if tag in self.VOID:
            self.handle_starttag(tag, attrs)
        else:
            self.handle_starttag(tag, attrs)
            self.handle_endtag(tag)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.VOID:
            if tag == "br":
                for fr in reversed(self.stack):
                    if fr[1] is not None:
                        fr[1].append(" "); break
            return
        if tag in ("script", "style"):
            self.skip_depth += 1
        cls = (a.get("class") or "").split()[0] if a.get("class") else ""
        hidden = "display:none" in (a.get("style") or "").replace(" ", "")
        if cls.endswith("_SHORT"):
            hidden = True
        if self.hidden_depth or hidden:
            self.hidden_depth += 1
            self.stack.append([cls, [], True])
            return
        if self.is_block(cls):
            self.flush_top()
            self.stack.append([cls, [], False])
        else:
            self.stack.append([cls, None, False])

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip_depth = max(0, self.skip_depth - 1)
        if tag in self.VOID or not self.stack:
            return
        cls, buf, hidden = self.stack.pop()
        if hidden:
            self.hidden_depth = max(0, self.hidden_depth - 1)
            return
        if buf is not None:
            self.emit(cls, "".join(buf))

    def handle_data(self, data):
        if self.skip_depth or self.hidden_depth:
            return
        # datele merg în cel mai apropiat bloc deschis
        for fr in reversed(self.stack):
            if fr[1] is not None:
                fr[1].append(data)
                return

    def flush_top(self):
        # când începe un bloc nou în interiorul altuia, scriem ce s-a strâns până acum;
        # „nota" se judecă doar după strămoșii blocului golit, nu după elementele
        # deschise sub el (altfel un alineat ar deveni notă doar pentru că notă începe în el)
        for idx in range(len(self.stack) - 1, -1, -1):
            fr = self.stack[idx]
            if fr[1] is not None:
                if "".join(fr[1]).strip():
                    self.emit(fr[0], "".join(fr[1]), self.in_nota(self.stack[:idx]))
                fr[1] = []
                return

    def in_nota(self, cadre=None):
        cadre = self.stack if cadre is None else cadre
        return any(fr[0].startswith("S_NTA") for fr in cadre)

    def emit(self, cls, text, nota_stramosi=None):
        t = re.sub(r"\s+", " ", text).strip()
        if not t or t == "+":   # „+" este butonul de pliere al portalului
            return
        if cls in self.PREFIX_TTL:
            self.prefix = t
            return
        if self.prefix:
            t = self.prefix + " " + t
            self.prefix = ""
        if nota_stramosi is None:
            nota_stramosi = self.in_nota()   # la end-tag cadrul e deja scos: stiva = strămoșii
        nota = (cls.startswith("S_NTA") or nota_stramosi
                or re.match(r"^\(la \d{2}-\d{2}-\d{4},", t) or re.match(r"^\(?la data de \d", t)
                # istoric în stil vechi (acte republicate): „Alin. (2) al art. 5 a fost modificat de ...", „Art. 11 a fost ..."
                or re.match(r"^(Alineatul|Alineatele|Articolul|Articolele|Litera|Literele|Punctul|Punctele|Partea introductivă|Alin\.|Art\.|Lit\.|Pct\.|Anexa|Capitolul|Sec[țt]iunea|Titlul)\s.*\b(a fost|au fost) (modificat|abrogat|introdus|completat|eliminat|suspendat)", t)
                or re.match(r"^-{5,}$", t))
        if nota:
            t = "§NOTA§ " + t          # notele au prioritate: o anexă citată într-o notă rămâne notă
        elif cls.startswith("S_ANX") and cls.endswith("_TTL"):
            t = "§ANEXA§ " + t
        elif cls.endswith("_TTL") and cls not in ("S_ART_TTL",):
            t = "## " + t   # capitol/secțiune/titlu — doar orientare
        self.lines.append(t)


def extrage(h):
    p = Extractor()
    p.feed(h)
    p.flush_top()
    # eliminăm dublurile consecutive (antetul apare de două ori în HTML)
    out = []
    for l in p.lines:
        if out and out[-1] == l:
            continue
        out.append(l)
    return out


def main():
    argv = sys.argv[1:]
    ddir = pathlib.Path("../../legislatie")
    offline = "--din-html" in argv          # reface .txt din .html-ul salvat, fără rețea
    if offline:
        argv.remove("--din-html")
    if "--dir" in argv:
        i = argv.index("--dir")
        ddir = pathlib.Path(argv[i + 1])
        del argv[i:i + 2]
    args = argv
    if len(args) != 2:
        print(__doc__); sys.exit(2)
    seed, nume = args
    if offline:
        h = (ddir / (nume + ".html")).read_text(encoding="utf-8")
        lst = consolidari(h)
        lst = [(lst[0][0], None)] if lst else []   # nu mai urmărim alte consolidări
    else:
        h = fetch(BASE + seed)
        lst = consolidari(h)
    ales, data = seed, "necunoscută"
    if lst:
        data, idn = lst[0]           # prima intrare = cea mai recentă consolidare
        if idn and idn != seed:
            time.sleep(1.5)
            ales = idn
            h = fetch(BASE + idn)
    titlu = re.search(r"<title>(.*?)</title>", h, re.S)
    titlu = re.sub(r"\s+", " ", titlu.group(1)).strip() if titlu else ""
    ddir.mkdir(parents=True, exist_ok=True)
    (ddir / (nume + ".html")).write_text(h, encoding="utf-8")
    linii = extrage(h)
    antet = "§SURSA§ legislatie.just.ro/Public/DetaliiDocument/%s | %s | consolidarea din %s | descărcat %s" % (
        ales, titlu, data, datetime.date.today().isoformat())
    (ddir / (nume + ".txt")).write_text(antet + "\n" + "\n".join(linii) + "\n", encoding="utf-8")
    nart = sum(1 for l in linii if re.match(r"^Articolul \S+$", l))
    print("%s: id %s, %s, %d linii, %d titluri de articol, consolidări disponibile: %s" % (
        nume, ales, data, len(linii), nart, ", ".join(d for d, _ in lst[:3]) or "-"))


if __name__ == "__main__":
    main()
