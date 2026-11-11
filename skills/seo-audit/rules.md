# Rules checked by `scripts/audit_html.py`

| Rule | Level | Triggered when |
| --- | --- | --- |
| `title-missing` | error | no `<title>` or it is empty |
| `title-length` | warning | title longer than 60 characters |
| `title-duplicate` | warning | two or more pages share the same title |
| `description-missing` | error | no `<meta name="description">` or it is empty |
| `description-length` | warning | description shorter than 50 or longer than 160 characters |
| `description-duplicate` | warning | two or more pages share the same description |
| `h1-missing` | error | no `<h1>` |
| `h1-multiple` | warning | more than one `<h1>` |
| `img-alt-missing` | error | an `<img>` has no `alt` attribute (an empty `alt=""` is allowed for decoration) |
| `lang-missing` | warning | `<html>` has no `lang` attribute |
| `viewport-missing` | warning | no `<meta name="viewport">` |
| `canonical-missing` | warning | no `<link rel="canonical">` |
| `noindex` | warning | a robots meta tag contains `noindex` (fine if intended) |

Length limits are common rules of thumb for what fits in a search result, not hard limits.

The script reads files only. It does not execute JavaScript, follow links, fetch URLs or measure
performance, so content injected in the browser is invisible to it.
