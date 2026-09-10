# GBAGo Support Site

Static support / privacy / terms site for **GBAGo — Retro Game Emulator** (iOS, paid, fully on-device).

Live: https://alice51849.github.io/gbago-support/

## Files
- `index.html` — support home with exact-50 localized content and an inline no-JavaScript fallback
- `privacy.html` — exact-50 privacy, file-rights, iCloud sync, retention/deletion, sharing, and legal disclosures with an inline no-JavaScript fallback
- `terms.html` — terms of use + legal notice (Nintendo non-affiliation, mGBA MPL-2.0 attribution)
- `style.css` — Aurora theme (#FC67AA → #CE5FE8 → #8980F7 → #5A9EFA, gold #E7A95A)
- `site-locales.js` / `site-locales.json` — matching canonical exact-50 support/privacy payloads
- `i18n.js` — client-side locale selection for all 50 locales; `?lang=<locale>` takes precedence and unknown languages fall back to `en-US`
- `lumi-orbit.gba` — reviewer-only original test ROM owned by Lumi Studio
  (262,144 bytes; SHA-256
  `c1f7ec17c7d4641a5e1143ae589264836487a847b85106f1da695dee14d51fa2`);
  it is not linked from the app or support pages

No frameworks, no external resources, no analytics.

## Validation

```sh
python3 tests/validate_site.py
node tests/validate_i18n.js
node --check site-locales.js
node --check i18n.js
```

## App Store Connect URLs
- Support URL: `https://alice51849.github.io/gbago-support/`
- Privacy Policy URL: `https://alice51849.github.io/gbago-support/privacy.html`
- Marketing URL (optional): `https://alice51849.github.io/gbago-support/`

Contact: hourstag.app@gmail.com
