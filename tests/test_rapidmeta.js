const assert = require("node:assert/strict");
const fs = require("node:fs");
const { parseEffects, poolEffects, RapidMetaConfig } = require("../rapidmeta.js");

const rows = parseEffects(`study,effect,ci_lower,ci_upper
Trial A,0.80,0.70,0.92
Trial B,0.90,0.82,0.99
`);

assert.equal(rows.length, 2);
assert.equal(rows[0].study, "Trial A");
assert.ok(rows[0].variance > 0);

const result = poolEffects(rows);
assert.equal(result.status, "ok");
assert.equal(result.k, 2);
assert.ok(result.random.estimate > 0);
assert.ok(result.random.ci_lower < result.random.estimate);
assert.ok(result.random.ci_upper > result.random.estimate);
assert.ok(result.heterogeneity.i2 >= 0);

assert.throws(
  () => parseEffects("study,effect,ci_lower\nTrial A,0.8,0.7"),
  /Missing required column/
);

assert.equal(RapidMetaConfig.data_sources[0].path, "data/aact/20260604_export_ctgov.zip");
assert.equal(RapidMetaConfig.data_sources[0].integrity.zip_crc_test, "passed");
assert.equal(RapidMetaConfig.release_gates.some(gate => gate.includes("No simulated")), true);
assert.equal(RapidMetaConfig.project.slug, "benralizumab-hes");
assert.equal(RapidMetaConfig.review_question.intervention.includes("Benralizumab"), true);

const defaultRows = parseEffects(RapidMetaConfig.default_effect_csv);
assert.equal(defaultRows.length, 1);
assert.equal(defaultRows[0].study, "NATRON");
assert.equal(defaultRows[0].effect, 0.35);

const effectCsv = fs.readFileSync("data/extracted/benralizumab_hes_effects.csv", "utf8");
assert.match(effectCsv, /NCT04191304/);
assert.match(effectCsv, /NCT02130882/);
assert.match(effectCsv, /pooled_include/);

console.log("rapidmeta tests passed");
