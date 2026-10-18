# isaev.cc

Personal website of Sergey Isaev. Everything is plain text files in this repository: change a file
on GitHub, and the site at [isaev.cc](https://isaev.cc) updates by itself about a minute later.

## Editing on GitHub

- **Change a file:** open it on github.com → pencil icon (*Edit this file*) → make the change →
  *Commit changes…* → *Commit changes* (straight to `main`).
- **Add or replace a file** (PDF, photo, icon): open the folder → *Add file* → *Upload files* →
  *Commit changes*. A file with the same name replaces the old one.
- **Check that it went live:** *Actions* tab → *deploy*. A green tick means the site is updated
  (give the browser a refresh). A red cross means the build failed; open it to see the error,
  which is almost always a typo in a `.yml` file. The live site stays as it was until a build succeeds.

Every commit to `main` triggers the update, whatever file it touches.

## What is where

| To change | Edit |
|---|---|
| Bio on the home page | `content/index.md` |
| Name, search-engine description, menu, contact icons | `data/site.yml` |
| Publications | `data/publications.yml` (PDFs go into `data/papers/`) |
| Packages on the code page | `data/software.yml` |
| Subtitle of the publications / code page | `content/publications.md`, `content/code.md` |
| Course pages (`/bf.msu.2026/` and others) | `content/courses/*.md` |
| CV | upload a new `static/assets/pdf/cv.pdf` |
| Photo | upload a new `static/assets/img/portrait.webp` (square) |
| Contact icons | `static/assets/icons/*.svg` |
| Site logo in the browser tab | `static/favicon.svg`, plus PNG copies `static/favicon-32.png` and `static/apple-touch-icon.png` (180 px, for Safari / iPhone home screen) |
| Colours, sizes, spacing | `static/assets/css/site.css` (colours are the variables at the top) |
| Page shell: `<head>`, menu, footer | `templates/base.html` |

## Common tasks

**Add a paper.** In `data/publications.yml`, copy an existing block to the top and edit it. For an
open-access paper or a preprint, upload the PDF into `data/papers/` and add `pdf: file-name.pdf` to
its block; a PDF icon appears next to it. Only PDFs named this way are linked on the site, but
the repository is public, so don't upload PDFs you are not allowed to share (two publisher PDFs
are kept out of the repository by `.gitignore`).

**New year of a course.** Copy `content/courses/bf_2026.md` to `content/courses/bf_2027.md`, change
`permalink: /bf.msu.2026/` to `/bf.msu.2027/` and edit the text. Schedules are ordinary Markdown
tables: one row per line, columns separated by `|`.

**New page.** Create `content/name.md` starting with

```
---
title: name
---
```

It appears at `isaev.cc/name/`. To put it in the menu, add it under `nav:` in `data/site.yml`.

**Redirect an old address.** A page with only front matter forwards visitors, e.g. `content/cv.md`:
`permalink: /cv/` and `redirect: /assets/pdf/cv.pdf`.

## File formats

- **`.yml` files** use simple YAML: `key: value`, lists start with `- `, nesting by two-space
  indentation, `#` starts a comment. Put a value in quotes if it starts with `*`, `†` or `"`,
  or contains `: ` or ` #`.
- **Pages** are Markdown: headings, paragraphs, lists, tables, links, images, `**bold**`, `*italic*`,
  `` `code` ``, code blocks, quotes, raw HTML. The front matter between the `---` lines can set
  `title`, `permalink`, `description`, `lang` (e.g. `ru`), `redirect` and `sitemap: false`.
- A line containing only `{{ hero }}`, `{{ publications }}` or `{{ software }}` inserts the
  generated block. They are used in `index.md`, `publications.md` and `code.md`.

## How it works

`website.py` turns `content/` and `data/` into a static site in `_site/` using Python's standard
library only. There is nothing to install, no packages and no frameworks. On every push,
`.github/workflows/deploy.yml` runs it on GitHub's servers and puts the result on the `gh-pages`
branch, which GitHub Pages serves. The workflow uses no third-party actions.

GitHub Pages setting (one time; already set for this repository): *Settings → Pages → Build and
deployment → Source: Deploy from a branch, Branch: `gh-pages` / `(root)`*, custom domain `isaev.cc`,
*Enforce HTTPS* on. `static/CNAME` keeps the domain attached after each deploy.

Repository layout:

```
website.py              the generator: Markdown, the YAML subset, page rendering, preview server
content/                pages (Markdown)
data/                   site.yml, publications.yml, software.yml, papers/ (PDFs)
templates/base.html     HTML shell of every page
static/                 copied as-is: stylesheet, icons, photo, CV, favicon, CNAME
.github/workflows/      the deploy workflow
```

## Preview on your computer (optional)

```
python3 website.py serve
```

Open <http://127.0.0.1:8000>. The page is rebuilt whenever a file changes; reload to see it.
`python3 website.py build` only writes `_site/`. Both work with the Python that comes with macOS.
