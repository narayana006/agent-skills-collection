---
name: seo-audit
description: Audit a static site or a built Next.js site for on-page SEO problems such as missing titles, meta descriptions, headings, alt text and canonical links. Use when the user asks for an SEO audit or review, or wants to know why pages are not indexed or look wrong in search results.
---

# On-page SEO audit

Audit the HTML that search engines receive, not the source templates. For a framework site that
means the build output.

## Steps

1. **Find the HTML.**
   - Static site: the folder that gets deployed (`public/`, `dist/`, `_site/`, `out/`).
   - Next.js: run the build first. With static export the pages are in `out/`; otherwise the
     prerendered pages are under `.next/server/app/` or `.next/server/pages/`.
   - If pages are rendered only on request, save a few with `curl -s URL -o page.html` and audit
     those files.
2. **Run the audit script** on that folder:

   ```bash
   python3 scripts/audit_html.py out/
   ```

   It checks every `.html` file and prints one line per problem, then a summary. It exits with
   status 1 if there are errors. Use `--format json` to post-process. The rules and their limits
   are listed in [rules.md](rules.md).
3. **Check what the script cannot see:**
   - `robots.txt` exists and does not block pages that should be indexed.
   - `sitemap.xml` exists, lists the canonical URLs and is referenced from `robots.txt`.
   - Titles and descriptions are specific to each page and describe it accurately. The script
     catches duplicates, not vague or misleading text.
   - Internal links use real `<a href>` elements, and important pages are reachable in a few
     clicks from the home page.
   - Structured data (JSON-LD), where present, matches the visible content.
4. **Fix at the source.** Map each problem back to the template, layout or metadata export that
   generates it. In Next.js that is usually the `metadata` export or `generateMetadata` in the
   route's `layout` or `page` file. Fix it there, rebuild and rerun the script.
5. **Report** errors first, then warnings, grouped by cause rather than by page: "12 product
   pages share one title because the layout sets it" is more useful than twelve lines.

## Rules

- Do not recommend keyword stuffing, hidden text, or doorway pages.
- Do not promise rankings. On-page fixes remove obstacles; they do not guarantee position.
