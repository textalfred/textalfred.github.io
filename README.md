# Alfred landing page

Waitlist page for **Alfred**, the AI butler on WhatsApp. A small Jekyll 3.9 site: black background, monospace, one red accent.

## Run it

```sh
export PATH="$(ruby -e 'print Gem.user_dir')/bin:$PATH"
bundle _2.4.22_ exec jekyll serve --port 4001
```

`jekyll build` writes the static site to `_site/`.

## Where things live

- **Copy:** `_data/alfred.yml` (landing copy, menu, subpage CTA; keep the keys, edit the values), `_handles/*.md` (one page per capability), `rule.md`, `manor.md`.
- **Pages:** `/` (landing), `/handles/` (`handles/index.html`, every handle by `order`), `/handles/<slug>.html`, `/rule.html`, `/manor.html`. Handles with `featured: true` appear on the landing page.
- **Layout:** `_layouts/home.html` renders the landing sections; `_layouts/page.html` renders subpages (`..` back link, title, `exchange` chat, body, more handles, CTA); `_layouts/default.html` holds the hero art (landing only), footer and the mobile sticky CTA.
- **Includes:** `chat.html` (a you/alfred exchange), `menu_item.html` (nested menu), `back_link.html`, `subpage_cta.html`, `waitlist_form.html`.
- **JS:** `assets/js/sticky.js` hides the mobile sticky CTA while a CTA or the form is on screen.
- **Styles:** `_sass/colors.scss` (`$fg-color` for art, rules and large type; `$text-red` for small text) and `_sass/no-style-please.scss`.
- **Art:** `assets/alfred-holo.png`, `assets/bat-holo.png`, `assets/bat.svg`, `favicon.png`. The hologram script and source images are in `art/`.
- **Form:** `_includes/waitlist_form.html`, posting to Formspree (`formspree_id` in `_config.yml`). The `@formspree/ajax` CDN script is loaded in `_includes/head.html`; without JavaScript the form still posts normally.

## Credit

Built on the [no style, please!](https://github.com/riggraz/no-style-please) Jekyll theme by riggraz, MIT licensed (see `LICENSE.txt`).
