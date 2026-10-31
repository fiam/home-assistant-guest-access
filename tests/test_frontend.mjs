import assert from "node:assert/strict";
import { test } from "node:test";
import {
  translations,
  languageFor,
  actionName,
  labelFor,
} from "../custom_components/guest_access/frontend/translations.js";
import { actionIcon } from "../custom_components/guest_access/frontend/icons.js";

test("browser language preference, regional variants and English fallback", () => {
  for (const [languages, expected] of [
    [[], "en"],
    [["fr-FR"], "en"],
    [["pt-PT", "en-US"], "pt"],
    [["pt-BR"], "pt"],
    [["es-MX"], "es"],
    [["en-GB", "pt-PT"], "en"],
    [["fr-FR", "es-ES"], "es"],
  ])
    assert.equal(languageFor(languages).lang, expected);
  assert.equal(languageFor(["pt-PT"]).locale, "pt-PT");
});
test("all translated states and errors are complete", () => {
  for (const lang of ["pt", "es"]) {
    assert.deepEqual(
      Object.keys(translations[lang]).sort(),
      Object.keys(translations.en).sort(),
    );
    for (const field of ["actions", "errors", "labels", "states"])
      assert.deepEqual(
        Object.keys(translations[lang][field]).sort(),
        Object.keys(translations.en[field]).sort(),
      );
    assert.match(translations[lang].until, /\{date\}/);
  }
  assert.equal(actionName("lock.open", translations.en), "Open door");
  assert.equal(actionName("lock.open", translations.pt), "Abrir porta");
  assert.equal(actionName("lock.open", translations.es), "Abrir puerta");
  assert.equal(actionName("unknown", translations.en), translations.en.tap);
});
test("door, lock and unlock have distinct SVG icons", () => {
  assert.equal(actionIcon("lock.open"), "door");
  assert.equal(actionIcon("lock.lock"), "lock");
  assert.equal(actionIcon("lock.unlock"), "unlock");
});

test("standard door labels translate; custom names remain unchanged", () => {
  assert.equal(labelFor("Apartment door", translations.pt), "Porta de casa");
  assert.equal(
    labelFor("Building entrance", translations.es),
    "Entrada del edificio",
  );
  assert.equal(labelFor("My side gate", translations.pt), "My side gate");
});
