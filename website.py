#!/usr/bin/env python3
"""Site generator for isaev.cc. Python standard library only (3.8+), no other dependencies.

    python3 website.py build     render the site into _site/ (GitHub Actions runs this on every push)
    python3 website.py serve     optional local preview at http://127.0.0.1:8000, rebuilt on every change

Where things live (see README.md for how to edit them):
    content/      pages in Markdown; front matter between --- lines sets title, permalink, lang, …
    data/         site.yml (name, menu, contact icons), publications.yml, software.yml, papers/ (PDFs)
    templates/    base.html, the HTML shell around every page
    static/       copied as-is to the site root (stylesheet, icons, photo, CV, CNAME, favicon)

A Markdown line that is only {{ hero }}, {{ publications }} or {{ software }} is replaced by
the generated block (home-page header, publication list, package list).
"""

import html
import re
import shutil
import subprocess
import sys
import time
from datetime import date
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT, DATA, TEMPLATES, STATIC = (ROOT / d for d in ("content", "data", "templates", "static"))
PAPERS = DATA / "papers"   # PDFs; only those named by `pdf:` in publications.yml are published, at /papers/
OUT = ROOT / "_site"



# --------------------------------------------------------------------------------------
# Minimal YAML subset: nested mappings, lists of scalars / mappings, > and | blocks,
# quoted strings, comments, true/false/numbers. Enough for front matter and data files.
# --------------------------------------------------------------------------------------

def _scalar(v):
    v = v.strip()
    if not v:
        return ""
    if v[0] in "\"'" and v[-1] == v[0] and len(v) > 1:
        s = v[1:-1]
        return s.replace('\\"', '"') if v[0] == '"' else s.replace("''", "'")
    v = re.sub(r"\s+#.*$", "", v)  # trailing comment (needs a space before #)
    low = v.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "~"):
        return None
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return v


def parse_yaml(text):
    lines = []
    for raw in text.splitlines():
        if raw.strip().startswith("#") or not raw.strip():
            lines.append((None, raw))  # keep blanks for block scalars
        else:
            lines.append((len(raw) - len(raw.lstrip(" ")), raw))
    pos = 0

    def next_content(i):
        while i < len(lines) and lines[i][0] is None:
            i += 1
        return i

    def block_scalar(indent, style):
        nonlocal pos
        body = []
        while pos < len(lines):
            ind, raw = lines[pos]
            if ind is not None and ind <= indent:
                break
            body.append(raw)
            pos += 1
        while body and not body[-1].strip():
            body.pop()
        strip = min((len(l) - len(l.lstrip(" ")) for l in body if l.strip()), default=0)
        body = [l[strip:] for l in body]
        if style == "|":
            return "\n".join(body) + "\n"
        paras, cur = [], []
        for l in body:
            if l.strip():
                cur.append(l.strip())
            else:
                paras.append(" ".join(cur)); cur = []
        paras.append(" ".join(cur))
        return "\n".join(p for p in paras if p)

    def value_after_key(rest, indent):
        nonlocal pos
        rest = rest.strip()
        if rest in (">", "|", ">-", "|-"):
            return block_scalar(indent, rest[0])
        if rest and not rest.startswith("#"):
            return _scalar(rest)
        j = next_content(pos)
        if j < len(lines) and lines[j][0] > indent or (
            j < len(lines) and lines[j][0] == indent and lines[j][1].lstrip().startswith("- ")
        ):
            pos = j
            return parse_node(lines[j][0])
        return None

    def parse_node(indent):
        nonlocal pos
        pos = next_content(pos)
        if pos >= len(lines):
            return None
        is_list = lines[pos][1].lstrip().startswith("- ") or lines[pos][1].strip() == "-"
        result = [] if is_list else {}
        while True:
            pos = next_content(pos)
            if pos >= len(lines):
                break
            ind, raw = lines[pos]
            stripped = raw.strip()
            if ind < indent or (ind > indent):
                break
            if is_list:
                if not (stripped.startswith("- ") or stripped == "-"):
                    break
                item = stripped[1:].strip()
                m = re.match(r"^([\w.-]+):(\s+.*|)$", item)
                if m and not item.startswith(("'", '"')):
                    # list of mappings: rewrite "- key: v" as a mapping at indent+2
                    sub_indent = ind + (len(raw) - len(raw.lstrip(" -")) - ind)
                    lines[pos] = (sub_indent, " " * sub_indent + item)
                    result.append(parse_node(sub_indent))
                else:
                    pos += 1
                    result.append(_scalar(item))
            else:
                m = re.match(r"^([^:#][^:]*?):(\s+.*|)$", stripped)
                if not m:
                    raise ValueError("Cannot parse line: %r" % raw)
                pos += 1
                result[m.group(1).strip()] = value_after_key(m.group(2), ind)
        return result

    node = parse_node(next_content(0) < len(lines) and lines[next_content(0)][0] or 0)
    return node if node is not None else {}


def split_front_matter(text):
    if text.startswith("---"):
        m = re.match(r"^---\s*\n(.*?)\n---\s*(\n|$)", text, re.S)
        if m:
            return parse_yaml(m.group(1)) or {}, text[m.end():]
    return {}, text


# --------------------------------------------------------------------------------------
# Markdown: headings, paragraphs, nested lists, GFM tables, blockquotes, fenced code,
# horizontal rules, raw HTML lines; inline code, links, images, emphasis, strikethrough.
# --------------------------------------------------------------------------------------

_LIST_RE = re.compile(r"^( *)([-*+]|\d{1,9}[.)])( +|$)(.*)$")
_HR_RE = re.compile(r"^ {0,3}([-*_])( *\1){2,} *$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
_SHORTCODE_RE = re.compile(r"^\{\{\s*([\w-]+)\s*\}\}$")


def slugify(text):
    text = re.sub(r"<[^>]+>", "", text).lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.U)
    return re.sub(r"[\s_]+", "-", text).strip("-") or "section"


def inline(text):
    """Render inline Markdown to HTML."""
    stash = []

    def keep(s):
        stash.append(s)
        return "\x00%d\x00" % (len(stash) - 1)

    # backslash escapes and code spans first, so nothing inside them is touched
    text = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|~<>])", lambda m: keep(html.escape(m.group(1))), text)
    text = re.sub(r"(`+)(.+?)\1", lambda m: keep("<code>%s</code>" % html.escape(m.group(2).strip())), text)
    # raw inline HTML tags and autolinks
    text = re.sub(r"<(https?://[^>\s]+)>", lambda m: keep('<a href="%s">%s</a>' % (
        html.escape(m.group(1)), html.escape(m.group(1)))), text)
    text = re.sub(r"</?[a-zA-Z][a-zA-Z0-9-]*(\s[^<>]*)?/?>", lambda m: keep(m.group(0)), text)
    # images and links; URL may contain one level of balanced parentheses
    url = r"\(\s*<?((?:[^()\s<>]|\([^()\s]*\))+)>?(?:\s+\"([^\"]*)\")?\s*\)"
    text = re.sub(r"!\[([^\]]*)\]" + url, lambda m: keep('<img src="%s" alt="%s"%s loading="lazy">' % (
        html.escape(m.group(2)), html.escape(m.group(1)),
        ' title="%s"' % html.escape(m.group(3)) if m.group(3) else "")), text)

    def link(m):
        href = m.group(2)
        attrs = ' title="%s"' % html.escape(m.group(3)) if m.group(3) else ""
        if re.match(r"https?://", href) and "isaev.cc" not in href:
            attrs += ' rel="noopener"'
        return keep('<a href="%s"%s>' % (html.escape(href), attrs)) + m.group(1) + keep("</a>")

    text = re.sub(r"\[((?:[^\[\]]|\[[^\]]*\])*)\]" + url, link, text)
    # escape what is left, but keep existing entities like &nbsp;
    text = re.sub(r"&(?!#?\w+;)", "&amp;", text).replace("<", "&lt;").replace(">", "&gt;")
    # emphasis
    text = re.sub(r"\*\*\*(?=\S)(.+?)(?<=\S)\*\*\*", r"<em><strong>\1</strong></em>", text)
    text = re.sub(r"\*\*(?=[^\s*])(.+?)(?<=[^\s*])\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\w)__(?=\S)(.+?)(?<=\S)__(?!\w)", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![*\w])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![*\w])", r"<em>\1</em>", text)
    text = re.sub(r"(?<![\w_])_(?=\S)(.+?)(?<=\S)_(?![\w_])", r"<em>\1</em>", text)
    text = re.sub(r"~~(?=\S)(.+?)(?<=\S)~~", r"<del>\1</del>", text)
    # hard line breaks
    text = re.sub(r"( {2,}|\\)\n", "<br>\n", text)
    while "\x00" in text:
        text = re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], text)
    return text


def _split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line)]


def markdown(text, shortcodes=None):
    lines = text.replace("\t", "    ").replace("\r\n", "\n").split("\n")
    return "\n".join(_blocks(lines, shortcodes or {}))


def _starts_block(line):
    s = line.strip()
    return (not s or s.startswith(("#", ">", "```", "~~~", "<")) or _HR_RE.match(line)
            or _LIST_RE.match(line) and _LIST_RE.match(line).group(4).strip()
            or _SHORTCODE_RE.match(s))


def _blocks(lines, shortcodes):
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        m = _SHORTCODE_RE.match(s)
        if m:
            name = m.group(1)
            out.append(shortcodes[name]() if name in shortcodes else
                       "<!-- unknown shortcode %s -->" % html.escape(name))
            i += 1
            continue
        if s.startswith(("```", "~~~")):
            fence, lang = s[:3], s[3:].strip()
            i += 1
            body = []
            while i < n and not lines[i].strip().startswith(fence):
                body.append(lines[i]); i += 1
            i += 1
            cls = ' class="language-%s"' % html.escape(lang) if lang else ""
            out.append("<pre><code%s>%s</code></pre>" % (cls, html.escape("\n".join(body))))
            continue
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", s)
        if m:
            level, content = len(m.group(1)), inline(m.group(2))
            ident = ' id="%s"' % slugify(content) if level > 1 else ""
            out.append("<h%d%s>%s</h%d>" % (level, ident, content, level))
            i += 1
            continue
        if _HR_RE.match(line):
            out.append("<hr>")
            i += 1
            continue
        if s.startswith("<"):
            while i < n and lines[i].strip():
                out.append(lines[i]); i += 1
            continue
        if s.startswith(">"):
            body = []
            while i < n and lines[i].strip().startswith(">"):
                body.append(re.sub(r"^\s*> ?", "", lines[i])); i += 1
            out.append("<blockquote>\n%s\n</blockquote>" % "\n".join(_blocks(body, shortcodes)))
            continue
        if "|" in s and i + 1 < n and _TABLE_SEP_RE.match(lines[i + 1]) and "-" in lines[i + 1]:
            head = _split_row(line)
            aligns = []
            for c in _split_row(lines[i + 1]):
                a = "center" if c.startswith(":") and c.endswith(":") else "right" if c.endswith(":") else \
                    "left" if c.startswith(":") else ""
                aligns.append(' style="text-align:%s"' % a if a else "")
            i += 2
            rows = []
            while i < n and lines[i].strip() and "|" in lines[i]:
                rows.append(_split_row(lines[i])); i += 1
            al = lambda k: aligns[k] if k < len(aligns) else ""
            t = ["<div class=\"table-wrap\"><table>", "<thead><tr>"]
            t += ["<th%s>%s</th>" % (al(k), inline(c)) for k, c in enumerate(head)]
            t.append("</tr></thead><tbody>")
            for r in rows:
                r = (r + [""] * len(head))[:len(head)]
                t.append("<tr>" + "".join("<td%s>%s</td>" % (al(k), inline(c)) for k, c in enumerate(r)) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("\n".join(t))
            continue
        m = _LIST_RE.match(line)
        if m and m.group(4).strip():
            i = _list(lines, i, out, shortcodes)
            continue
        para = [line.lstrip()]
        i += 1
        while i < n and not _starts_block(lines[i]):
            para.append(lines[i].lstrip())
            i += 1
        out.append("<p>%s</p>" % inline("\n".join(para).rstrip()))
    return out


def _list(lines, i, out, shortcodes):
    first = _LIST_RE.match(lines[i])
    base = len(first.group(1))
    ordered = first.group(2)[0].isdigit()
    items, loose, n = [], False, len(lines)
    while i < n:
        m = _LIST_RE.match(lines[i])
        if not (m and len(m.group(1)) == base and m.group(2)[0].isdigit() == ordered):
            break
        content_indent = len(m.group(1)) + len(m.group(2)) + max(1, len(m.group(3)))
        body = [m.group(4)]
        i += 1
        while i < n:
            l = lines[i]
            if not l.strip():
                j = i + 1
                while j < n and not lines[j].strip():
                    j += 1
                if j < n and (len(lines[j]) - len(lines[j].lstrip()) >= content_indent):
                    loose = True
                    body += [""] * (j - i)
                    i = j
                    continue
                nm = _LIST_RE.match(lines[j]) if j < n else None
                if nm and len(nm.group(1)) == base and nm.group(2)[0].isdigit() == ordered:
                    loose = True
                i = j
                break
            ind = len(l) - len(l.lstrip())
            lm = _LIST_RE.match(l)
            if lm and len(lm.group(1)) <= base:
                break
            if ind < content_indent and not lm and _starts_block(l):
                break
            body.append(l[content_indent:] if ind >= content_indent else l.strip())
            i += 1
        items.append(body)
    tag = "ol" if ordered else "ul"
    start = int(re.match(r"\d+", first.group(2)).group(0)) if ordered else 1
    html_items = []
    for body in items:
        inner = _blocks(body, shortcodes)
        if not loose and inner and inner[0].startswith("<p>"):
            inner[0] = inner[0][3:-4]
        html_items.append("<li>%s</li>" % "\n".join(inner))
    out.append("<%s%s>\n%s\n</%s>" % (tag, ' start="%d"' % start if start != 1 else "",
                                     "\n".join(html_items), tag))
    return i


# --------------------------------------------------------------------------------------
# Site: load content + data, render shortcodes and pages
# --------------------------------------------------------------------------------------


def esc(v):
    return html.escape(str(v if v is not None else ""), quote=True)


def load_data():
    return {p.stem: parse_yaml(p.read_text(encoding="utf-8")) for p in sorted(DATA.glob("*.yml"))}


def load_pages():
    pages = []
    for p in sorted(CONTENT.rglob("*.md")):
        meta, body = split_front_matter(p.read_text(encoding="utf-8"))
        rel = p.relative_to(CONTENT).with_suffix("")
        meta.setdefault("permalink", "/" if str(rel) == "index" else "/%s/" % rel.as_posix())
        if not meta["permalink"].endswith(("/", ".html")):
            meta["permalink"] += "/"
        pages.append((meta, body))
    return pages


def last_updated():
    """Date of the last commit (falls back to the newest content file outside a git checkout)."""
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs"], cwd=ROOT, capture_output=True,
                             text=True, timeout=5).stdout.strip()
        if out:
            return date.fromisoformat(out)
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return date.fromtimestamp(max(p.stat().st_mtime for p in CONTENT.rglob("*.md")))


def icon(name):
    """An icon from static/assets/icons/<name>.svg, drawn in the current text colour.
    The ?v= timestamp makes browsers fetch a replaced icon instead of a cached one."""
    path = STATIC / "assets" / "icons" / ("%s.svg" % name)
    version = int(path.stat().st_mtime) if path.exists() else 0
    return ('<span class="icon" style="--icon:url(/assets/icons/%s.svg?v=%d)" aria-hidden="true"></span>'
            % (esc(name), version))


# ----- generated blocks ({{ hero }}, {{ publications }}, {{ software }}) -----

def render_hero(data):
    site = data.get("site") or {}
    items = []
    for link in site.get("links") or []:
        url, label = str(link.get("url")), esc(link.get("label"))
        if url.startswith("mailto:"):   # e-mail: written as HTML entities against address harvesters
            attrs = ' href="%s"' % "".join("&#%d;" % ord(ch) for ch in url)
        else:                           # profiles open in a new tab
            attrs = ' href="%s" target="_blank" rel="noopener"' % esc(url)
        items.append('<li><a%s class="icon-link" aria-label="%s" title="%s">%s</a></li>'
                     % (attrs, label, label, icon(link.get("icon"))))
    first, last = str(site.get("first_name", "")), str(site.get("last_name", ""))
    return ('<section class="hero">\n'
            '  <div class="id">\n'
            '    <h1 class="name">%s <b>%s</b></h1>\n'
            '    <ul class="links">%s</ul>\n'
            '  </div>\n'
            '  <img class="portrait" src="%s" alt="Portrait of %s %s" width="512" height="512">\n'
            '</section>' % (esc(first.lower()), esc(last.lower()), "".join(items),
                            esc(site.get("photo")), esc(first), esc(last)))


def render_publications(data):
    me = (data.get("site") or {}).get("author_names") or []
    out, year = ['<ol class="pubs" reversed>'], None
    for p in data.get("publications") or []:
        authors = esc(p.get("authors"))
        for name in me:
            authors = authors.replace(esc(name), "<b>%s</b>" % esc(name))
        title = esc(p.get("title"))
        if p.get("url"):
            title = '<a href="%s">%s</a>' % (esc(p["url"]), title)
        extras = ""
        if p.get("type"):
            extras += '<span class="badge">%s</span>' % esc(p["type"])
        if p.get("note"):
            extras += '<span class="note">%s</span>' % esc(p["note"])
        if p.get("pdf") and (PAPERS / str(p["pdf"])).is_file():
            extras += ('<a class="pub-pdf" href="/papers/%s" target="_blank" rel="noopener" aria-label="PDF" '
                       'title="PDF">%s</a>' % (esc(p["pdf"]), icon("pdf")))
        new_year = p.get("year") != year
        year = p.get("year")
        out.append('<li class="pub%s"><span class="pub-year">%s</span><div>'
                   '<p class="pub-title">%s</p><p class="pub-authors">%s</p>'
                   '<p class="pub-venue"><i>%s</i>%s</p></div></li>'
                   % (" new-year" if new_year else "", esc(year) if new_year else "",
                      title, authors, esc(p.get("venue")), extras))
    out.append("</ol>")
    return "\n".join(out)


def render_software(data):
    out = ['<ul class="software">']
    for s in data.get("software") or []:
        name = esc(s.get("name"))
        if s.get("url"):
            name = '<a href="%s">%s</a>' % (esc(s["url"]), name)
        links = " ".join('<a href="%s">%s</a>' % (esc(l.get("url")), esc(l.get("label")))
                         for l in s.get("links") or [])
        out.append('<li><p class="sw-name"><code>%s</code><span class="sw-years">%s</span></p>'
                   '<p class="sw-desc">%s</p>%s</li>'
                   % (name, esc(s.get("years")), inline(str(s.get("description") or "")),
                      '<p class="sw-links">%s</p>' % links if links else ""))
    out.append("</ul>")
    return "\n".join(out)


SHORTCODES = {"hero": render_hero, "publications": render_publications, "software": render_software}


# ----- pages -----

def render_page(meta, body, data, template, updated):
    site = data.get("site") or {}
    permalink = meta["permalink"]
    if meta.get("redirect"):   # old addresses (e.g. /cv/) forward to their new place
        target = esc(meta["redirect"])
        return ('<!doctype html><meta charset="utf-8"><title>Redirecting</title>'
                '<meta http-equiv="refresh" content="0; url=%s"><link rel="canonical" href="%s">'
                '<a href="%s">%s</a>' % (target, target, target, target))
    nav = []
    for item in site.get("nav") or []:
        url = str(item.get("url"))
        current = ' aria-current="page"' if permalink.startswith(url) else ""
        nav.append('<a href="%s"%s>%s</a>' % (esc(url), current, esc(item.get("label"))))
    first, last = str(site.get("first_name", "")), str(site.get("last_name", ""))
    name = "%s %s" % (first, last)
    base = str(site.get("url", "")).rstrip("/")
    title = meta.get("title")
    shortcodes = {key: partial(func, data) for key, func in SHORTCODES.items()}
    values = {
        "lang": esc(meta.get("lang") or site.get("lang") or "en"),
        "title": esc(name if permalink == "/" or not title else "%s | %s" % (str(title)[:1].upper() + str(title)[1:], name)),
        "description": esc(meta.get("description") or site.get("description")),
        "url": esc(base + permalink),
        "image": esc(base + str(site.get("photo", ""))),
        "name": esc(name),
        "brand": "%s <b>%s</b>" % (esc(first.lower()), esc(last.lower())),
        "nav": "\n      ".join(nav),
        "content": markdown(body, shortcodes),
        "body_class": esc(meta.get("layout") or "page"),
        "year": str(updated.year),
        "updated": "%d %s" % (updated.day, updated.strftime("%B %Y")),
        "updated_iso": updated.isoformat(),
        "version": str(int(time.time())),
    }
    return re.sub(r"\{\{\s*(\w+)\s*\}\}", lambda m: values.get(m.group(1), m.group(0)), template)


def published_papers(data):
    return sorted({str(p["pdf"]) for p in data.get("publications") or []
                   if p.get("pdf") and (PAPERS / str(p["pdf"])).is_file()})


def build():
    """Render everything into _site/: pages, static files, published PDFs, sitemap, robots.txt."""
    t0 = time.time()
    data, updated = load_data(), last_updated()
    template = (TEMPLATES / "base.html").read_text(encoding="utf-8")
    base = str((data.get("site") or {}).get("url", "")).rstrip("/")
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT)
    sitemap = []
    pages = load_pages()
    for meta, body in pages:
        link = meta["permalink"]
        target = OUT / link.lstrip("/")
        if link.endswith("/"):
            target = target / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_page(meta, body, data, template, updated), encoding="utf-8")
        if not meta.get("redirect") and meta.get("sitemap", True):
            sitemap.append("  <url><loc>%s%s</loc></url>" % (esc(base), esc(link)))
    for name in published_papers(data):
        (OUT / "papers").mkdir(exist_ok=True)
        shutil.copy2(PAPERS / name, OUT / "papers" / name)
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                                     '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                     + "\n".join(sorted(sitemap)) + "\n</urlset>\n", encoding="utf-8")
    (OUT / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % base)
    (OUT / ".nojekyll").write_text("")   # tells GitHub Pages to serve the files as they are
    print("Built %d pages into _site/ in %.1f s" % (len(pages), time.time() - t0))


# ----- local preview -----

def source_stamp():
    files = [p for d in (CONTENT, DATA, TEMPLATES, STATIC) for p in d.rglob("*") if p.is_file()]
    return len(files), max((p.stat().st_mtime_ns for p in files), default=0)


class PreviewHandler(SimpleHTTPRequestHandler):
    """Serves _site/ exactly as GitHub Pages would, rebuilding first if any source file changed."""
    stamp = None

    def do_GET(self):
        stamp = source_stamp()
        if stamp != PreviewHandler.stamp:
            PreviewHandler.stamp = stamp
            build()
        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_error(self, code, message=None, explain=None):
        page = OUT / "404.html"
        if code != 404 or not page.exists():
            return super().send_error(code, message, explain)
        body = page.read_bytes()
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(port=8000):
    build()
    PreviewHandler.stamp = source_stamp()
    print("Preview at http://127.0.0.1:%d — edit files and reload the page (Ctrl+C to stop)" % port)
    handler = partial(PreviewHandler, directory=str(OUT))
    ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "build":
        build()
    elif command == "serve":
        serve(int(sys.argv[2]) if len(sys.argv) > 2 else 8000)
    else:
        sys.exit(__doc__)
