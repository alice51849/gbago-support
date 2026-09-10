#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_EMAIL = "hourstag.app@gmail.com"
RTL_LOCALES = {"ar-SA", "he", "ur-PK"}
EXPECTED_LOCALES = {
    "ar-SA",
    "bn-BD",
    "ca",
    "cs",
    "da",
    "de-DE",
    "el",
    "en-AU",
    "en-CA",
    "en-GB",
    "en-US",
    "es-ES",
    "es-MX",
    "fi",
    "fr-CA",
    "fr-FR",
    "gu-IN",
    "he",
    "hi",
    "hr",
    "hu",
    "id",
    "it",
    "ja",
    "kn-IN",
    "ko",
    "ml-IN",
    "mr-IN",
    "ms",
    "nl-NL",
    "no",
    "or-IN",
    "pa-IN",
    "pl",
    "pt-BR",
    "pt-PT",
    "ro",
    "ru",
    "sk",
    "sl-SI",
    "sv",
    "ta-IN",
    "te-IN",
    "th",
    "tr",
    "uk",
    "ur-PK",
    "vi",
    "zh-Hans",
    "zh-Hant",
}
REQUIRED_LOCALE_KEYS = {
    "languageName",
    "nav.support",
    "nav.privacy",
    "support.name",
    "support.subtitle",
    "support.about",
    "support.description",
    "support.importTitle",
    "support.importBody",
    "support.contact",
    "privacy.title",
    "privacy.summaryTitle",
    "privacy.summary",
    "privacy.cloudTitle",
    "privacy.cloud",
    "privacy.retentionDeletionShare",
    "legal.title",
    "legal.authorizedFiles",
    "legal.disclaimer",
}
NO_JS_KEYS = (
    "support.name",
    "support.importTitle",
    "support.importBody",
    "privacy.title",
    "privacy.summary",
    "privacy.cloud",
    "privacy.retentionDeletionShare",
    "legal.title",
    "legal.authorizedFiles",
    "legal.disclaimer",
    "support.contact",
)
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


def fail(message: str) -> None:
    raise AssertionError(message)


def normalize(text: str) -> str:
    return " ".join(html.unescape(text).split())


class FragmentText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def visible_text(fragment: str) -> str:
    parser = FragmentText()
    parser.feed(fragment)
    parser.close()
    return normalize(" ".join(parser.parts))


class SiteHTMLParser(HTMLParser):
    def __init__(self, path: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.path = path
        self.stack: list[str] = []
        self.declarations: list[str] = []
        self.ids: set[str] = set()
        self.links: list[tuple[str, str]] = []
        self.data_keys: set[str] = set()
        self.script_sources: list[str] = []
        self.stylesheets: list[str] = []
        self.noscript_depth = 0
        self.noscript_count = 0
        self.fallback_details: dict[str, dict[str, str]] = {}
        self.current_locale: str | None = None
        self.current_attrs: dict[str, str] = {}
        self.current_text: list[str] = []
        self.in_summary = False
        self.summary_text: list[str] = []

    def handle_decl(self, decl: str) -> None:
        self.declarations.append(decl.lower())

    def handle_starttag(
        self, tag: str, attrs_list: list[tuple[str, str | None]]
    ) -> None:
        tag = tag.lower()
        attrs = {key: value or "" for key, value in attrs_list}
        if tag not in VOID_TAGS:
            self.stack.append(tag)
        element_id = attrs.get("id")
        if element_id:
            if element_id in self.ids:
                fail(f"{self.path.name}: duplicate id {element_id!r}")
            self.ids.add(element_id)
        for attr in ("href", "src"):
            if attrs.get(attr):
                self.links.append((attr, attrs[attr]))
        if attrs.get("data-i18n"):
            self.data_keys.add(attrs["data-i18n"])
        if tag == "script" and attrs.get("src"):
            self.script_sources.append(attrs["src"])
        if tag == "link" and attrs.get("rel") == "stylesheet" and attrs.get("href"):
            self.stylesheets.append(attrs["href"])
        if tag == "noscript":
            self.noscript_depth += 1
            self.noscript_count += 1
        elif tag == "details" and self.noscript_depth:
            if self.current_locale is not None:
                fail(f"{self.path.name}: nested fallback details")
            locale = attrs.get("id", "")
            self.current_locale = locale
            self.current_attrs = attrs
            self.current_text = []
            self.summary_text = []
        elif tag == "summary" and self.current_locale is not None:
            self.in_summary = True
        elif tag == "script" and self.noscript_depth:
            fail(f"{self.path.name}: script found inside no-JavaScript fallback")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "summary" and self.current_locale is not None:
            self.in_summary = False
        elif tag == "details" and self.current_locale is not None:
            locale = self.current_locale
            if not locale:
                fail(f"{self.path.name}: fallback details missing id")
            if locale in self.fallback_details:
                fail(f"{self.path.name}: duplicate fallback locale {locale}")
            self.fallback_details[locale] = {
                "lang": self.current_attrs.get("lang", ""),
                "dir": self.current_attrs.get("dir", ""),
                "summary": normalize(" ".join(self.summary_text)),
                "text": normalize(" ".join(self.current_text)),
            }
            self.current_locale = None
            self.current_attrs = {}
            self.current_text = []
            self.summary_text = []
        elif tag == "noscript":
            self.noscript_depth -= 1
        if tag not in VOID_TAGS:
            if not self.stack or self.stack[-1] != tag:
                fail(f"{self.path.name}: mismatched closing tag </{tag}>")
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        if self.current_locale is not None:
            self.current_text.append(data)
            if self.in_summary:
                self.summary_text.append(data)


def parse_js_constant(source: str, name: str) -> object:
    marker = f"const {name} = "
    start = source.find(marker)
    if start < 0:
        fail(f"site-locales.js: missing {name}")
    start += len(marker)
    try:
        value, _ = json.JSONDecoder().raw_decode(source[start:])
    except json.JSONDecodeError as error:
        fail(f"site-locales.js: invalid {name}: {error}")
    return value


def load_locales() -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    json_payload = json.loads((ROOT / "site-locales.json").read_text())
    js_source = (ROOT / "site-locales.js").read_text()
    js_payload = parse_js_constant(js_source, "SITE_I18N")
    language_names = parse_js_constant(js_source, "SITE_LANGUAGE_NAMES")
    if js_payload != json_payload:
        fail("site-locales.js and site-locales.json differ")
    if set(json_payload) != EXPECTED_LOCALES:
        fail(
            "locale catalog is not exact-50: "
            f"missing={sorted(EXPECTED_LOCALES - set(json_payload))}, "
            f"extra={sorted(set(json_payload) - EXPECTED_LOCALES)}"
        )
    if set(language_names) != EXPECTED_LOCALES:
        fail("SITE_LANGUAGE_NAMES is not exact-50")
    for locale, values in json_payload.items():
        if set(values) != REQUIRED_LOCALE_KEYS:
            fail(
                f"{locale}: locale keys differ: "
                f"missing={sorted(REQUIRED_LOCALE_KEYS - set(values))}, "
                f"extra={sorted(set(values) - REQUIRED_LOCALE_KEYS)}"
            )
        if language_names[locale] != values["languageName"]:
            fail(f"{locale}: language name differs between payloads")
        if values["support.contact"] != PUBLIC_EMAIL:
            fail(f"{locale}: public contact email is not canonical")
    return json_payload, language_names


def parse_page(path: Path) -> SiteHTMLParser:
    parser = SiteHTMLParser(path)
    parser.feed(path.read_text())
    parser.close()
    if parser.stack:
        fail(f"{path.name}: unclosed tags {parser.stack}")
    if parser.noscript_depth:
        fail(f"{path.name}: unclosed noscript")
    if "doctype html" not in parser.declarations:
        fail(f"{path.name}: missing HTML5 doctype")
    return parser


def validate_links(path: Path, parser: SiteHTMLParser) -> None:
    for attr, raw_value in parser.links:
        value = html.unescape(raw_value).strip()
        parsed = urlsplit(value)
        if parsed.scheme in {"http", "https", "data"}:
            continue
        if parsed.scheme == "mailto":
            if parsed.path != PUBLIC_EMAIL:
                fail(f"{path.name}: non-canonical mailto link {value}")
            continue
        if parsed.scheme or value.startswith("//"):
            fail(f"{path.name}: unsupported {attr} URL {value}")
        local_path = unquote(parsed.path)
        if not local_path or local_path.startswith("#"):
            continue
        target = (path.parent / local_path).resolve()
        if ROOT not in target.parents and target != ROOT:
            fail(f"{path.name}: local link escapes repository: {value}")
        if not target.exists():
            fail(f"{path.name}: broken local link {value}")


def validate_page(
    filename: str,
    locales: dict[str, dict[str, str]],
    language_names: dict[str, str],
) -> None:
    path = ROOT / filename
    parser = parse_page(path)
    validate_links(path, parser)
    if parser.script_sources != ["site-locales.js", "i18n.js"]:
        fail(f"{filename}: locale scripts missing or out of order")
    if parser.stylesheets != ["style.css"]:
        fail(f"{filename}: stylesheet link differs")
    if parser.noscript_count != 1:
        fail(f"{filename}: expected one no-JavaScript fallback")
    if set(parser.fallback_details) != EXPECTED_LOCALES:
        fail(f"{filename}: fallback details are not exact-50")
    for locale, detail in parser.fallback_details.items():
        expected_dir = "rtl" if locale in RTL_LOCALES else "ltr"
        if detail["lang"] != locale or detail["dir"] != expected_dir:
            fail(f"{filename}: {locale} fallback lang/dir mismatch")
        if detail["summary"] != normalize(language_names[locale]):
            fail(f"{filename}: {locale} fallback language label mismatch")
        for key in NO_JS_KEYS:
            canonical = visible_text(locales[locale][key])
            if canonical not in detail["text"]:
                fail(f"{filename}: {locale} fallback missing canonical {key}")
    for key in parser.data_keys:
        if any(key not in values for values in locales.values()):
            fail(f"{filename}: data-i18n key {key!r} missing from exact-50 payload")


def validate_public_contact() -> None:
    email_pattern = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
    found: set[str] = set()
    for path in ROOT.rglob("*"):
        if (
            not path.is_file()
            or ".git" in path.parts
            or path.suffix.lower()
            not in {".html", ".js", ".json", ".md", ".css", ".py"}
        ):
            continue
        text = path.read_text(errors="strict")
        found.update(match.lower() for match in email_pattern.findall(text))
    unexpected = found - {PUBLIC_EMAIL}
    if unexpected:
        fail(f"unexpected public email address(es): {sorted(unexpected)}")
    if PUBLIC_EMAIL not in found:
        fail("canonical public email is absent")


def main() -> int:
    try:
        locales, language_names = load_locales()
        validate_page("index.html", locales, language_names)
        validate_page("privacy.html", locales, language_names)
        for filename in ("terms.html",):
            path = ROOT / filename
            parser = parse_page(path)
            validate_links(path, parser)
        validate_public_contact()
    except (AssertionError, json.JSONDecodeError, OSError, UnicodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: exact-50 payload, HTML, no-JavaScript content, links, and contact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
