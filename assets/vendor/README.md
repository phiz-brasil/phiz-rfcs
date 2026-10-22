# Vendored libraries

Browser builds committed as they were published on npm (`npm pack <name>@<version>`, file taken from the package's `dist/`), so the
site does not depend on a CDN for rendering RFCs. Update by replacing the file, the version and the hash below.

| file | package | version | license | sha256 |
|---|---|---|---|---|
| `markdown-it.min.js` | [markdown-it](https://github.com/markdown-it/markdown-it) | 14.1.0 | MIT | `38c70a1e7ca91ab40e2d9e6e60129851a717ed1c7d4acbbdd41bf9503791cf68` |
| `markdown-it-container.min.js` | [markdown-it-container](https://github.com/markdown-it/markdown-it-container) | 4.0.0 | MIT | `5bda29f8cc0e613e04c4eb077a363cc86ab8a238f487b7792f2bdeb7a7b27ff4` |
| `purify.min.js` | [DOMPurify](https://github.com/cure53/DOMPurify) | 3.2.4 | Apache-2.0 or MPL-2.0 | `8eb41b658831fab175fad9bcd00fcb2d84e0ed3a25a55053d4ecd4444b8b43a0` |

`mermaid.min.js` (v10.9.1) in the parent folder is vendored the same way.
