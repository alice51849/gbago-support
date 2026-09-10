"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..");
const SITE_SOURCE = fs.readFileSync(path.join(ROOT, "site-locales.js"), "utf8");
const I18N_SOURCE = fs.readFileSync(path.join(ROOT, "i18n.js"), "utf8");
const RTL_LOCALES = new Set(["ar-SA", "he", "ur-PK"]);
const PAGE_KEYS = [
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
];

function render(search) {
  const callbacks = {};
  const options = [];
  const elements = PAGE_KEYS.map((key) => ({
    key,
    innerHTML: "",
    getAttribute(name) {
      return name === "data-i18n" ? key : null;
    },
  }));
  const select = {
    value: "",
    appendChild(option) {
      options.push({ value: option.value, textContent: option.textContent });
    },
    addEventListener() {},
  };
  const storage = new Map();
  const context = {
    URLSearchParams,
    console,
    navigator: { language: "en-US", languages: ["en-US"] },
    localStorage: {
      getItem(key) {
        return storage.get(key) || null;
      },
      setItem(key, value) {
        storage.set(key, value);
      },
    },
    window: { location: { search } },
    document: {
      documentElement: { lang: "", dir: "" },
      addEventListener(name, callback) {
        callbacks[name] = callback;
      },
      createElement() {
        return { value: "", textContent: "" };
      },
      getElementById(id) {
        return id === "langSelect" ? select : null;
      },
      querySelectorAll(selector) {
        return selector === "[data-i18n]" ? elements : [];
      },
    },
  };
  context.globalThis = context;
  vm.createContext(context);
  vm.runInContext(
    `${SITE_SOURCE}\n;globalThis.__site = SITE_I18N; globalThis.__names = SITE_LANGUAGE_NAMES;`,
    context,
    { filename: "site-locales.js" }
  );
  vm.runInContext(I18N_SOURCE, context, { filename: "i18n.js" });
  assert.equal(typeof callbacks.DOMContentLoaded, "function");
  callbacks.DOMContentLoaded();
  return { context, elements, options, select };
}

const catalog = render("?lang=en-US").context.__site;
const locales = Object.keys(catalog);
assert.equal(locales.length, 50);

for (const locale of locales) {
  const { context, elements, options, select } = render(
    `?lang=${encodeURIComponent(locale)}`
  );
  assert.equal(context.document.documentElement.lang, locale);
  assert.equal(
    context.document.documentElement.dir,
    RTL_LOCALES.has(locale) ? "rtl" : "ltr"
  );
  assert.equal(select.value, locale);
  assert.equal(options.length, 50);
  assert.deepEqual(
    new Set(options.map((option) => option.value)),
    new Set(locales)
  );
  for (const element of elements) {
    assert.equal(
      element.innerHTML,
      catalog[locale][element.key],
      `${locale}: ${element.key}`
    );
  }
}

const fallback = render("?lang=not-a-real-locale");
assert.equal(fallback.context.document.documentElement.lang, "en-US");
assert.equal(fallback.select.value, "en-US");

console.log("PASS: exact-50 query selection and canonical JavaScript rendering");
