"use strict";

const RapidMetaConfig = {
  schema: "rapidmeta.project.v1",
  status: "release_prepared_single_study_primary",
  project: {
    slug: "benralizumab-hes",
    title: "Benralizumab for hypereosinophilic syndrome",
    created: "2026-06-04",
    summary: "RapidMeta-style review of randomized benralizumab evidence in FIP1L1::PDGFRA-negative hypereosinophilic syndrome."
  },
  data_sources: [{
    id: "aact_20260604_flatfiles",
    type: "aact_flatfile_zip",
    path: "data/aact/20260604_export_ctgov.zip",
    exported: "2026-06-04",
    publisher: "Clinical Trials Transformation Initiative",
    citation: "Aggregate Analysis of ClinicalTrials.gov (AACT) Database. Clinical Trials Transformation Initiative (CTTI). Available at: https://aact.ctti-clinicaltrials.org/",
    integrity: { zip_crc_test: "passed", file_count: 49 }
  }],
  review_question: {
    population: "FIP1L1::PDGFRA-negative hypereosinophilic syndrome",
    intervention: "Benralizumab 30 mg subcutaneous add-on therapy",
    comparator: "Placebo plus background therapy",
    outcome: "Time to first HES flare",
    study_design: "randomized controlled trials"
  },
  analysis_plan: {
    effect_measure: "hazard_ratio",
    scale: "log",
    primary_model: "random_effects",
    tau2_estimator: "dersimonian_laird_for_dashboard_preview",
    small_sample_adjustment: "planned_hartung_knapp_when_k_ge_3",
    heterogeneity: ["Q", "I2", "tau2"]
  },
  aact_query_contract: {
    required_tables: [
      "studies.txt",
      "interventions.txt",
      "conditions.txt",
      "outcomes.txt",
      "outcome_measurements.txt",
      "outcome_counts.txt",
      "reported_events.txt"
    ],
    rules: [
      "Lowercase intervention types before filtering.",
      "Verify every referenced column exists before use.",
      "Search by drug or intervention name rather than therapeutic class.",
      "Validate NCT IDs, dates, PMIDs, DOIs, and effect data against source records before analysis."
    ]
  },
  release_gates: [
    "No simulated or placeholder effect data.",
    "All identifiers and dates validated against source records.",
    "All important numeric claims trace to extracted data and reproducible code.",
    "Dashboard and manuscript agree on study count, effect estimate, confidence interval, and conclusion.",
    "Sentinel scan passes before push.",
    "Overmind pass required before submission-ready status."
  ],
  default_effect_csv: `study,effect,ci_lower,ci_upper
NATRON,0.35,0.18,0.69`
};

function fmt(value, digits = 2) {
  if (!Number.isFinite(value)) return "Not ready";
  return value.toFixed(digits);
}

function effectLabel(result) {
  if (!result || !Number.isFinite(result.estimate)) return "Not ready";
  return `${fmt(result.estimate)} (${fmt(result.ci_lower)}-${fmt(result.ci_upper)})`;
}

function analysisLabel(result) {
  if (!result || result.status !== "ok") return "No pooled estimate";
  return result.k === 1 ? `Single-study effect ${effectLabel(result.random)}` : `Random-effects pool ${effectLabel(result.random)}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function splitDelimitedLine(line) {
  if (line.includes("\t")) return line.split("\t");
  if (line.includes("|")) return line.split("|");
  return line.split(",");
}

function parseEffects(text) {
  const lines = String(text || "")
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(Boolean);
  if (lines.length === 0) return [];

  const headers = splitDelimitedLine(lines[0]).map(h => h.trim().toLowerCase());
  const required = ["study", "effect", "ci_lower", "ci_upper"];
  const missing = required.filter(name => !headers.includes(name));
  if (missing.length > 0) {
    throw new Error(`Missing required column(s): ${missing.join(", ")}`);
  }

  return lines.slice(1).map((line, index) => {
    const cells = splitDelimitedLine(line).map(c => c.trim());
    const row = Object.fromEntries(headers.map((header, i) => [header, cells[i] ?? ""]));
    const effect = Number(row.effect);
    const ciLower = Number(row.ci_lower);
    const ciUpper = Number(row.ci_upper);
    if (!row.study) throw new Error(`Row ${index + 2}: study is required`);
    if (![effect, ciLower, ciUpper].every(Number.isFinite)) {
      throw new Error(`Row ${index + 2}: effect and CI values must be numeric`);
    }
    if (effect <= 0 || ciLower <= 0 || ciUpper <= 0 || ciLower >= ciUpper) {
      throw new Error(`Row ${index + 2}: effects must be positive and CI lower must be below upper`);
    }
    const se = (Math.log(ciUpper) - Math.log(ciLower)) / (2 * 1.96);
    return {
      study: row.study,
      effect,
      ci_lower: ciLower,
      ci_upper: ciUpper,
      log_effect: Math.log(effect),
      se,
      variance: se * se
    };
  });
}

function poolEffects(studies) {
  if (!Array.isArray(studies) || studies.length === 0) {
    return { status: "not_ready", k: 0 };
  }

  const fixedWeights = studies.map(study => 1 / study.variance);
  const sumW = fixedWeights.reduce((a, b) => a + b, 0);
  const fixedMu = studies.reduce((sum, study, i) => sum + fixedWeights[i] * study.log_effect, 0) / sumW;
  const q = studies.reduce((sum, study, i) => {
    const diff = study.log_effect - fixedMu;
    return sum + fixedWeights[i] * diff * diff;
  }, 0);
  const df = Math.max(studies.length - 1, 0);
  const c = sumW - fixedWeights.reduce((sum, w) => sum + w * w, 0) / sumW;
  const tau2 = df > 0 && c > 0 ? Math.max(0, (q - df) / c) : 0;
  const randomWeights = studies.map(study => 1 / (study.variance + tau2));
  const sumWr = randomWeights.reduce((a, b) => a + b, 0);
  const randomMu = studies.reduce((sum, study, i) => sum + randomWeights[i] * study.log_effect, 0) / sumWr;
  const randomSe = Math.sqrt(1 / sumWr);
  const i2 = q > 0 && df > 0 ? Math.max(0, ((q - df) / q) * 100) : 0;

  return {
    status: "ok",
    k: studies.length,
    fixed: intervalFromLog(fixedMu, Math.sqrt(1 / sumW)),
    random: intervalFromLog(randomMu, randomSe),
    heterogeneity: { q, df, tau2, i2 },
    weights: randomWeights.map(w => w / sumWr)
  };
}

function intervalFromLog(mu, se) {
  return {
    estimate: Math.exp(mu),
    ci_lower: Math.exp(mu - 1.96 * se),
    ci_upper: Math.exp(mu + 1.96 * se),
    log_effect: mu,
    se
  };
}

function renderDefinitionList(id, entries) {
  const node = document.getElementById(id);
  node.innerHTML = entries.map(([key, value]) => (
    `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value ?? "Not specified")}</dd>`
  )).join("");
}

function renderList(id, items) {
  const node = document.getElementById(id);
  node.innerHTML = items.map(item => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderConfig() {
  const q = RapidMetaConfig.review_question;
  renderDefinitionList("pico-list", [
    ["Population", q.population],
    ["Intervention", q.intervention],
    ["Comparator", q.comparator],
    ["Outcome", q.outcome],
    ["Study design", q.study_design]
  ]);

  const plan = RapidMetaConfig.analysis_plan;
  renderDefinitionList("analysis-plan", [
    ["Primary model", plan.primary_model],
    ["Tau2 estimator", plan.tau2_estimator],
    ["Small sample adjustment", plan.small_sample_adjustment],
    ["Heterogeneity", plan.heterogeneity.join(", ")]
  ]);

  const source = RapidMetaConfig.data_sources[0];
  renderDefinitionList("source-list", [
    ["Source", source.publisher],
    ["Exported", source.exported],
    ["Local path", source.path],
    ["Zip test", source.integrity.zip_crc_test],
    ["File count", source.integrity.file_count]
  ]);

  renderList("release-gates", RapidMetaConfig.release_gates);
  renderList("query-rules", RapidMetaConfig.aact_query_contract.rules);
}

function renderEffects(studies, result) {
  const rows = document.getElementById("effect-rows");
  if (!studies.length) {
    rows.innerHTML = `<tr><td colspan="5" class="empty">No extracted effects loaded.</td></tr>`;
    return;
  }
  rows.innerHTML = studies.map((study, i) => `
    <tr>
      <td>${escapeHtml(study.study)}</td>
      <td>${fmt(study.effect)}</td>
      <td>${fmt(study.ci_lower)}</td>
      <td>${fmt(study.ci_upper)}</td>
      <td>${result.status === "ok" ? `${fmt(result.weights[i] * 100, 1)}%` : "Not ready"}</td>
    </tr>
  `).join("");
}

function renderForest(studies, result) {
  const forest = document.getElementById("forest");
  if (!studies.length || result.status !== "ok") {
    forest.innerHTML = `<div class="empty">Load at least one source-validated effect to render the forest plot.</div>`;
    return;
  }

  const allValues = studies.flatMap(s => [s.ci_lower, s.ci_upper]).concat([result.random.ci_lower, result.random.ci_upper]);
  const minLog = Math.log(Math.min(...allValues) * 0.9);
  const maxLog = Math.log(Math.max(...allValues) * 1.1);
  const pos = value => Math.max(0, Math.min(100, ((Math.log(value) - minLog) / (maxLog - minLog)) * 100));

  forest.innerHTML = studies.map(study => `
    <div class="forest-row">
      <strong>${escapeHtml(study.study)}</strong>
      <div class="forest-axis">
        <span class="forest-ci" style="left:${pos(study.ci_lower)}%;width:${Math.max(1, pos(study.ci_upper) - pos(study.ci_lower))}%"></span>
        <span class="forest-point" style="left:${pos(study.effect)}%"></span>
      </div>
      <span>${fmt(study.effect)} (${fmt(study.ci_lower)}-${fmt(study.ci_upper)})</span>
    </div>
  `).join("") + `
    <div class="forest-row">
      <strong>Random-effects pool</strong>
      <div class="forest-axis">
        <span class="forest-ci" style="left:${pos(result.random.ci_lower)}%;width:${Math.max(1, pos(result.random.ci_upper) - pos(result.random.ci_lower))}%"></span>
        <span class="forest-point" style="left:${pos(result.random.estimate)}%"></span>
      </div>
      <span>${effectLabel(result.random)}</span>
    </div>
  `;
}

function renderReadiness(studies, result) {
  const checks = [
    `AACT source registered: ${RapidMetaConfig.data_sources[0].path}`,
    `Extracted effects loaded: ${studies.length > 0 ? "yes" : "no"}`,
    `PICO complete: ${Object.values(RapidMetaConfig.review_question).slice(0, 4).every(Boolean) ? "yes" : "no"}`,
    `Pool computed: ${result.status === "ok" ? "yes" : "no"}`,
    "Identifier/date/statistical claim audit: required before release"
  ];
  renderList("readiness-list", checks);
}

function renderState(studies, result) {
  document.getElementById("study-count").textContent = `${studies.length} ${studies.length === 1 ? "study" : "studies"}`;
  document.getElementById("analysis-state").textContent = analysisLabel(result);
  document.getElementById("metric-k").textContent = String(studies.length);
  document.getElementById("metric-random").textContent = result.status === "ok" ? effectLabel(result.random) : "Not ready";
  document.getElementById("metric-i2").textContent = result.status === "ok" ? `${fmt(result.heterogeneity.i2, 1)}%` : "Not ready";
  document.getElementById("model-json").textContent = JSON.stringify(result, null, 2);
  const pill = document.getElementById("status-pill");
  pill.textContent = result.status === "ok" ? "Analysis preview" : "Draft";
  pill.className = result.status === "ok" ? "pill good" : "pill warn";
  renderEffects(studies, result);
  renderForest(studies, result);
  renderReadiness(studies, result);
}

function initTabs() {
  document.querySelectorAll(".tab").forEach(button => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach(tab => tab.classList.remove("active"));
      document.querySelectorAll(".panel").forEach(panel => panel.classList.remove("active"));
      button.classList.add("active");
      document.getElementById(button.dataset.tab).classList.add("active");
    });
  });
}

function initApp() {
  let studies = parseEffects(RapidMetaConfig.default_effect_csv);
  let result = poolEffects(studies);
  renderConfig();
  document.getElementById("effect-csv").value = RapidMetaConfig.default_effect_csv;
  renderState(studies, result);
  initTabs();

  document.getElementById("load-effects").addEventListener("click", () => {
    try {
      studies = parseEffects(document.getElementById("effect-csv").value);
      result = poolEffects(studies);
      renderState(studies, result);
    } catch (error) {
      alert(error.message);
    }
  });

  document.getElementById("clear-effects").addEventListener("click", () => {
    document.getElementById("effect-csv").value = "";
    studies = [];
    result = poolEffects(studies);
    renderState(studies, result);
  });
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", initApp);
}

if (typeof module !== "undefined") {
  module.exports = { parseEffects, poolEffects, intervalFromLog, RapidMetaConfig };
}
