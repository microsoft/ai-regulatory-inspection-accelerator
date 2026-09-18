// Azure OpenAI Global Standard list prices in USD per 1M tokens.
// Verified against the Azure pricing page on 2026-09-17. These estimates are
// not a substitute for the customer's negotiated price or Azure invoice.
const modelCatalog = {
  "gpt-4.1-nano": {
    displayName: "GPT-4.1 nano",
    version: "2025-04-14",
    input: 0.10,
    cachedInput: 0.025,
    output: 0.40,
  },
  "gpt-4o": {
    displayName: "GPT-4o",
    version: "2024-11-20",
    input: 2.50,
    cachedInput: 1.25,
    output: 10.00,
  },
};

function resolveModel(model) {
  const value = String(model || "").toLowerCase();
  if (value === "aria-text-mini" || value.includes("gpt-4.1-nano")) return modelCatalog["gpt-4.1-nano"];
  if (value === "aria-vision" || value.includes("gpt-4o")) return modelCatalog["gpt-4o"];
  return null;
}

function getModelLabel(model) {
  const resolved = resolveModel(model);
  return resolved ? `${resolved.displayName} (${resolved.version})` : String(model || "Unknown model");
}

function getRowCost(model, promptTokens, completionTokens, cachedTokens = 0) {
  const r = resolveModel(model);
  if (!r) return null;
  const uncachedPrompt = Math.max(0, promptTokens - cachedTokens);
  const cachedPromptCost = (cachedTokens / 1_000_000) * r.cachedInput;
  const uncachedPromptCost = (uncachedPrompt / 1_000_000) * r.input;
  const completionCost = (completionTokens / 1_000_000) * r.output;
  return uncachedPromptCost + cachedPromptCost + completionCost;
}

function generateSyntheticCases() {
  const annualReviewVolume = 122_433;
  const cohortCount = 365;
  const activities = [
    "Document extraction",
    "Cross-document reasoning",
    "Field validation",
    "Decision summary",
  ];
  const scenarios = ["Food safety", "Customs clearance", "Healthcare authorization", "Insurance claims"];
  const records = [];
  const now = new Date();

  for (let index = 0; index < cohortCount; index++) {
    const projectedCases = Math.floor(annualReviewVolume / cohortCount) + (index < annualReviewVolume % cohortCount ? 1 : 0);
    const promptTokensPerCase = 6500 + ((index * 977) % 9000);
    const completionTokensPerCase = 700 + ((index * 211) % 1800);
    const projectedCacheRate = 0.94 + ((index % 5) * 0.01);
    const cachedTokensPerCase = Math.round(promptTokensPerCase * projectedCacheRate);
    const promptTokens = promptTokensPerCase * projectedCases;
    const completionTokens = completionTokensPerCase * projectedCases;
    const cachedTokens = cachedTokensPerCase * projectedCases;
    const date = new Date(now);
    date.setDate(now.getDate() - index);
    const modelKey = "gpt-4.1-nano";

    records.push({
      id: `PROJECTION-${index + 1}`,
      caseId: `COHORT-${String(index + 1).padStart(3, "0")}`,
      tenant: `${scenarios[index % scenarios.length]} · Projected`,
      activity: activities[index % activities.length],
      model: getModelLabel(modelKey),
      modelKey,
      promptTokens,
      completionTokens,
      cachedTokens,
      totalTokens: promptTokens + completionTokens,
      cost: getRowCost(modelKey, promptTokens, completionTokens, cachedTokens),
      latencyMs: 650 + ((index * 173) % 1700),
      projectedCases,
      date,
      isLive: false,
      cacheMeasured: false,
      cacheProvenance: "projected",
      dataSource: "synthetic",
    });
  }

  return records.sort((left, right) => right.date - left.date);
}

const syntheticCases = generateSyntheticCases();

// State Management
const state = {
  cases: syntheticCases,
  liveCases: [],
  cosmosLoaded: false,
  telemetryError: null,
  mode: sessionStorage.getItem("ariaMode") === "live" ? "live" : "synthetic",
  currentPage: 1,
  pageSize: 10,
  chartMode: "daily", // "daily" | "accumulated"
};

if (state.mode === "live") state.cases = [];

// Fetch persistent telemetry from Cosmos DB
async function fetchCosmosTelemetry() {
  const cosmosRecords = [];
  const endpoint = window.ARIA_CONFIG?.telemetryEndpoint;
  if (!endpoint) {
    state.telemetryError = "Telemetry endpoint is not configured";
  } else {
    try {
      const res = await fetch(endpoint, { method: "GET" });
      if (!res.ok) throw new Error(`Telemetry request failed with HTTP ${res.status}`);
      const data = await res.json();
      if (!Array.isArray(data.items)) throw new Error("Telemetry response has an invalid format");
      const items = data.items;
      items.forEach(item => {
          const model = item.model || "Unknown model";
          const p = item.promptTokens || 0;
          const c = item.completionTokens || 0;
          const cacheMeasurement = item.cacheMeasurement || "unavailable";
          const cacheMeasured = cacheMeasurement === "provider";
          const reportedCachedTokens = item.cachedTokens || 0;
          const cached = cacheMeasured ? reportedCachedTokens : 0;
          const d = item.timestamp ? new Date(item.timestamp) : (item._ts ? new Date(item._ts * 1000) : new Date());

          cosmosRecords.push({
            id: item.id || `COSMOS-${item.caseId}`,
            caseId: item.caseId || "LIVE-DEMO",
            tenant: item.tenant || "Food Safety · Live Azure",
            activity: item.activity || "Document Intelligence Extraction",
            model: getModelLabel(model),
            modelKey: model,
            promptTokens: p,
            completionTokens: c,
            cachedTokens: cached,
            reportedCachedTokens,
            cacheMeasurement,
            totalTokens: p + c,
            cost: getRowCost(model, p, c, cached),
            latencyMs: item.latencyMs || null,
            date: d,
            isLive: true,
            cacheMeasured,
            cacheProvenance: cacheMeasurement,
          });
      });
      state.cosmosLoaded = true;
      state.telemetryError = null;
    } catch (e) {
      state.telemetryError = e instanceof Error ? e.message : "Telemetry request failed";
      console.warn("Cosmos DB telemetry fetch failed:", e);
    }
  }

  // Deduplicate by ID
  const map = new Map();
  cosmosRecords.forEach(item => {
    if (!map.has(item.id)) map.set(item.id, item);
  });

  state.liveCases = Array.from(map.values()).sort((a, b) => b.date - a.date);
  if (state.mode === "live") {
    state.cases = state.liveCases;
  }
  populateCaseFilter(state.cases);
}

const $ = selector => document.querySelector(selector);
const formatTokens = value => {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return Math.round(value).toLocaleString();
};
const formatUsd = value => `$${value.toFixed(value >= 1 ? 2 : value < 0.01 ? 6 : 4)}`;
const formatCachedTokens = row => {
  if (row.cacheProvenance === "projected") return `${row.cachedTokens.toLocaleString()} projected`;
  if (row.cacheMeasured) return row.cachedTokens.toLocaleString();
  return `${(row.reportedCachedTokens || 0).toLocaleString()} ${row.cacheProvenance || "unavailable"}`;
};
const escapeHtml = val => String(val).replace(/[&<>'"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[c]);
const csvCell = value => {
  let text = String(value ?? "");
  if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`;
  return `"${text.replaceAll('"', '""')}"`;
};

function getPeriodDateRange() {
  const periodVal = $("#periodFilter").value;
  let fromDate, toDate;
  let periodLabel = "Last 7 days";

  if (periodVal === "custom") {
    fromDate = $("#fromDateFilter").value ? new Date($("#fromDateFilter").value) : new Date(0);
    toDate = $("#toDateFilter").value ? new Date($("#toDateFilter").value) : new Date();
    const fStr = fromDate.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
    const tStr = toDate.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
    periodLabel = `Custom Range (${fStr} – ${tStr})`;
  } else if (periodVal === "1") {
    const now = new Date();
    toDate = new Date(now);
    fromDate = new Date(now);
    fromDate.setHours(0, 0, 0, 0);
    periodLabel = "Today (Last 24h)";
  } else if (periodVal === "30") {
    const now = new Date();
    toDate = new Date(now);
    fromDate = new Date(now);
    fromDate.setDate(now.getDate() - 29);
    fromDate.setHours(0, 0, 0, 0);
    periodLabel = "Last 30 days";
  } else if (periodVal === "365") {
    const now = new Date();
    toDate = new Date(now);
    fromDate = new Date(now);
    fromDate.setDate(now.getDate() - 364);
    fromDate.setHours(0, 0, 0, 0);
    periodLabel = "Full annual projection";
  } else {
    const now = new Date();
    toDate = new Date(now);
    fromDate = new Date(now);
    fromDate.setDate(now.getDate() - 6);
    fromDate.setHours(0, 0, 0, 0);
    periodLabel = "Last 7 days";
  }

  return { fromDate, toDate, periodLabel };
}

function populateCaseFilter(casesInPeriod) {
  const caseSelect = $("#caseFilter");
  if (!caseSelect) return;
  const currentVal = caseSelect.value || "all";

  const uniqueCasesMap = new Map();
  casesInPeriod.forEach(c => {
    if (c.caseId) {
      const existing = uniqueCasesMap.get(c.caseId);
      if (!existing || c.date > existing.latestDate) {
        uniqueCasesMap.set(c.caseId, {
          tenant: c.tenant || "Food Safety",
          latestDate: c.date,
        });
      }
    }
  });

  const projectedVolume = casesInPeriod.reduce((sum, item) => sum + (item.projectedCases || 0), 0);
  const allLabel = state.mode === "live"
    ? `All Cases & Tenants (${casesInPeriod.length} in timeframe)`
    : `All Projection Cohorts (${projectedVolume.toLocaleString()} reviews)`;
  let html = `<option value="all">${allLabel}</option>`;
  Array.from(uniqueCasesMap.entries())
    .sort(([, left], [, right]) => right.latestDate - left.latestDate)
    .forEach(([caseId, details]) => {
      const record = casesInPeriod.find(item => item.caseId === caseId);
      const volume = state.mode === "live" ? "" : ` · ${(record?.projectedCases || 0).toLocaleString()} reviews`;
      html += `<option value="${escapeHtml(caseId)}">${escapeHtml(caseId)} · ${escapeHtml(details.tenant)}${volume}</option>`;
    });

  caseSelect.innerHTML = html;

  if (currentVal !== "all" && Array.from(caseSelect.options).some(o => o.value === currentVal)) {
    caseSelect.value = currentVal;
  } else {
    caseSelect.value = "all";
  }
}

function toLocalDateTimeString(d) {
  const pad = num => String(num).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function initDateDefaults() {
  const now = new Date();
  const from = new Date(now);
  from.setDate(now.getDate() - 7);

  $("#fromDateFilter").value = toLocalDateTimeString(from);
  $("#toDateFilter").value = toLocalDateTimeString(now);
}

function getFilteredCases() {
  const { fromDate, toDate, periodLabel } = getPeriodDateRange();

  // Filter state.cases by date window
  const casesInPeriod = state.cases.filter(c => c.date >= fromDate && c.date <= toDate);

  // Dynamically populate Case / Tenant filter for this time period
  populateCaseFilter(casesInPeriod);

  const caseVal = ($("#caseFilter").value || "all").toLowerCase();
  const searchVal = ($("#caseSearch").value || "").toLowerCase();

  const filteredCases = casesInPeriod.filter(c => {
    if (caseVal !== "all") {
      if (c.caseId.toLowerCase() !== caseVal && !c.tenant.toLowerCase().includes(caseVal)) {
        return false;
      }
    }
    if (searchVal) {
      const matchSearch = c.caseId.toLowerCase().includes(searchVal) ||
                          c.tenant.toLowerCase().includes(searchVal) ||
                          c.activity.toLowerCase().includes(searchVal) ||
                          c.model.toLowerCase().includes(searchVal);
      if (!matchSearch) return false;
    }
    return true;
  });

  return { filteredCases, casesInPeriod, periodLabel, caseVal, fromDate, toDate };
}

function render() {
  const { filteredCases: filtered, casesInPeriod, periodLabel, caseVal, fromDate, toDate } = getFilteredCases();
  const isAnnualProjection = state.mode === "synthetic" && $("#periodFilter").value === "365";

  // Dynamic Titles Update
  const caseSelect = $("#caseFilter");
  const selectedOptionText = caseSelect && caseSelect.selectedIndex > 0 ? caseSelect.options[caseSelect.selectedIndex].text : null;
  const activeSelectionLabel = selectedOptionText && caseVal !== "all" ? selectedOptionText : periodLabel;

  if ($("#pageSubtitle")) {
    const source = state.mode === "live" ? "Measured Cosmos DB telemetry" : "Projected workload from synthetic document-evaluation profiles";
    $("#pageSubtitle").textContent = state.mode === "live" && state.telemetryError
      ? `Live telemetry unavailable: ${state.telemetryError}.`
      : `${source} and usage attribution for ${activeSelectionLabel}.`;
  }

  if ($("#chartTitle")) {
    const chartPrefix = state.chartMode === "accumulated" ? "Accumulated Token Growth" : "Daily Token Usage Trend";
    $("#chartTitle").textContent = `${chartPrefix} (${activeSelectionLabel})`;
  }

  if ($("#caseTableTitle")) {
    const callType = state.mode === "live" ? "Provider Call Usage" : "Projected Evaluation Cohorts";
    $("#caseTableTitle").textContent = `${callType} (${activeSelectionLabel})`;
  }

  if (state.mode === "synthetic") {
    $("#costKpiLabel").textContent = isAnnualProjection ? "Projected Annual Model Cost" : "Projected Period Model Cost";
    $("#bannerTitle").textContent = isAnnualProjection
      ? "What could the annual evaluation workload cost?"
      : "What could the selected evaluation workload cost?";
    $("#bannerDescription").innerHTML = isAnnualProjection
      ? `This projection distributes <strong>122,433 annual reviews</strong> across 365 daily cohorts using verified GPT-4.1 nano list rates and a 94–98% reusable-input target. Projected same-model savings: <strong id="bannerSavingsPct">0%</strong>.`
      : `This view selects the proportional review volume from a <strong>122,433-review annual projection</strong>. It uses verified GPT-4.1 nano list rates and a 94–98% reusable-input target. Projected same-model savings: <strong id="bannerSavingsPct">0%</strong>.`;
  }

  // Aggregates
  const totalPrompt = filtered.reduce((s, c) => s + c.promptTokens, 0);
  const totalCompletion = filtered.reduce((s, c) => s + c.completionTokens, 0);
  const totalTokens = totalPrompt + totalCompletion;
  const actualCostVal = filtered.reduce((s, c) => s + (c.cost ?? 0), 0);
  const pricedRecords = filtered.filter(c => c.cost !== null).length;
  const cacheRecords = state.mode === "live" ? filtered.filter(c => c.cacheMeasured) : filtered;
  const measuredPrompt = cacheRecords.reduce((s, c) => s + c.promptTokens, 0);
  const measuredCached = cacheRecords.reduce((s, c) => s + c.cachedTokens, 0);
  const cacheRate = Math.round(measuredCached / Math.max(1, measuredPrompt) * 100);
  const uniqueCases = new Set(filtered.map(c => c.caseId)).size;
  const caseCount = state.mode === "live"
    ? uniqueCases
    : filtered.reduce((sum, item) => sum + (item.projectedCases || 0), 0);
  const avgTokens = caseCount ? Math.round(totalTokens / caseCount) : 0;

  // Same workload and same deployed model, priced without provider cache discounts.
  const baselineCostVal = filtered.reduce((sum, item) => {
    const noCacheCost = getRowCost(item.modelKey, item.promptTokens, item.completionTokens, 0);
    return sum + (noCacheCost ?? 0);
  }, 0);
  const moneySavedVal = Math.max(0, baselineCostVal - actualCostVal);
  const savingsPctVal = baselineCostVal > 0 ? ((moneySavedVal / baselineCostVal) * 100).toFixed(1) : "0.0";
  const cacheCoveragePct = filtered.length ? Math.round(cacheRecords.length / filtered.length * 100) : 0;

  // Update KPI Cards
  if ($("#totalTokens")) $("#totalTokens").textContent = formatTokens(totalTokens);
  if ($("#tokenBreakdown")) $("#tokenBreakdown").textContent = `${formatTokens(totalPrompt)} in · ${formatTokens(totalCompletion)} out`;

  if ($("#avgTokens")) $("#avgTokens").textContent = formatTokens(avgTokens);
  if ($("#caseCount")) $("#caseCount").textContent = state.mode === "live"
    ? `${caseCount.toLocaleString()} cases in selected period`
    : `${caseCount.toLocaleString()} projected ${isAnnualProjection ? "annual reviews" : "reviews in selected period"}`;

  if ($("#actualCost")) $("#actualCost").textContent = formatUsd(actualCostVal);
  if ($("#costModelRates")) $("#costModelRates").textContent = state.mode === "live"
    ? `${pricedRecords}/${filtered.length} calls priced from Azure list rates`
    : `${isAnnualProjection ? "Annual" : "Selected-period"} projection · verified Azure list rates`;

  if ($("#uncachedCost")) $("#uncachedCost").textContent = formatUsd(baselineCostVal);
  if ($("#uncachedCostDetail")) $("#uncachedCostDetail").textContent = `Same models and tokens, cache disabled`;

  if ($("#costSaved")) $("#costSaved").textContent = formatUsd(moneySavedVal);
  if ($("#costSavingsPct")) $("#costSavingsPct").textContent = `${savingsPctVal}% ${state.mode === "live" ? "measured" : "projected"} same-model reduction`;

  if ($("#cacheRate")) $("#cacheRate").textContent = `${cacheRate}%`;
  if ($("#cachedTokens")) $("#cachedTokens").textContent = state.mode === "live"
    ? `${formatTokens(measuredCached)} reused · ${cacheCoveragePct}% telemetry coverage`
    : `${formatTokens(measuredCached)} projected reuse · ${cacheCoveragePct}% profile coverage`;

  if (state.mode === "live" && state.telemetryError) {
    ["totalTokens", "avgTokens", "actualCost", "uncachedCost", "costSaved", "cacheRate"].forEach(id => {
      if ($(`#${id}`)) $(`#${id}`).textContent = "Unavailable";
    });
    if ($("#tokenBreakdown")) $("#tokenBreakdown").textContent = "Telemetry request failed";
    if ($("#caseCount")) $("#caseCount").textContent = "No current telemetry result";
    if ($("#costModelRates")) $("#costModelRates").textContent = "Pricing requires provider usage data";
    if ($("#uncachedCostDetail")) $("#uncachedCostDetail").textContent = "Baseline requires provider usage data";
    if ($("#costSavingsPct")) $("#costSavingsPct").textContent = "Savings cannot be calculated";
    if ($("#cachedTokens")) $("#cachedTokens").textContent = "Cache coverage unavailable";
  }

  // Update Efficiency Banner
  if ($("#bannerSavingsPct")) $("#bannerSavingsPct").textContent = `${savingsPctVal}%`;
  if ($("#baselineCost")) $("#baselineCost").textContent = formatUsd(baselineCostVal);
  if ($("#ariaCost")) $("#ariaCost").textContent = formatUsd(actualCostVal);
  if ($("#ariaMoneySaved")) $("#ariaMoneySaved").textContent = formatUsd(moneySavedVal);
  if ($("#ariaPctSaved")) $("#ariaPctSaved").textContent = `${savingsPctVal}% same-model reduction`;

  renderDailyChart(filtered, fromDate, toDate, activeSelectionLabel);
  renderActivities(filtered);
  renderModelBreakdown(filtered, actualCostVal, totalTokens);
  renderEfficiency(savingsPctVal, cacheRate, cacheCoveragePct, totalCompletion, totalTokens, filtered);
  renderAnomalies(filtered);
  renderHeatmap(filtered);
  renderCasesTable(filtered);
}

function renderDailyChart(cases, fromDate, toDate, periodLabel) {
  const buckets = {};
  const rangeDays = Math.max(1, Math.ceil((toDate - fromDate) / 86_400_000));
  const granularity = rangeDays > 90 ? "monthly" : rangeDays > 31 ? "weekly" : "daily";

  const getBucket = date => {
    const bucketDate = new Date(date);
    if (granularity === "monthly") {
      bucketDate.setDate(1);
      return {
        key: bucketDate.toISOString().slice(0, 7),
        label: bucketDate.toLocaleDateString("en-GB", { month: "short", year: "2-digit" }),
      };
    }
    if (granularity === "weekly") {
      const dayOffset = (bucketDate.getDay() + 6) % 7;
      bucketDate.setDate(bucketDate.getDate() - dayOffset);
    }
    return {
      key: bucketDate.toISOString().slice(0, 10),
      label: bucketDate.toLocaleDateString("en-GB", { day: "2-digit", month: "short" }),
    };
  };

  cases.forEach(c => {
    const { key, label } = getBucket(c.date);
    if (!buckets[key]) buckets[key] = { label, prompt: 0, output: 0, cached: 0, total: 0 };
    buckets[key].prompt += c.promptTokens;
    buckets[key].output += c.completionTokens;
    buckets[key].cached += c.cachedTokens;
    buckets[key].total += c.totalTokens;
  });

  let entries = Object.entries(buckets)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([, value]) => [value.label, value]);

  if (state.chartMode === "accumulated") {
    let runPrompt = 0, runOutput = 0, runCached = 0, runTotal = 0;
    entries = entries.map(([day, d]) => {
      runPrompt += d.prompt;
      runOutput += d.output;
      runCached += d.cached;
      runTotal += d.total;
      return [day, { prompt: runPrompt, output: runOutput, cached: runCached, total: runTotal }];
    });
    if ($("#chartTitle")) $("#chartTitle").textContent = `Accumulated Token Growth (${periodLabel})`;
  } else {
    const label = granularity[0].toUpperCase() + granularity.slice(1);
    if ($("#chartTitle")) $("#chartTitle").textContent = `${label} Token Usage (${periodLabel})`;
  }

  const maxTotal = Math.max(1, ...entries.map(([, v]) => v.total));

  $("#usageChart").innerHTML = entries.map(([day, d]) => {
    const heightPx = Math.round((d.total / maxTotal) * 180);
    const pPct = d.total ? (d.prompt / d.total) * 100 : 0;
    const oPct = d.total ? (d.output / d.total) * 100 : 0;
    const cPx = d.prompt ? Math.max(2, (d.cached / d.prompt) * 22) : 0;

    return `<div class="day-column" title="${day} (${state.chartMode}): ${formatTokens(d.total)} total (${formatTokens(d.prompt)} prompt, ${formatTokens(d.output)} output)"><div class="bar-stack" style="height:${Math.max(10, heightPx)}px"><span class="bar-prompt" style="height:${pPct}%"></span><span class="bar-output" style="height:${oPct}%"></span><span class="bar-cache" style="height:${cPx}px"></span></div><small>${day}</small></div>`;
  }).join("");
}

function renderActivities(cases) {
  const actMap = {};
  cases.forEach(c => {
    actMap[c.activity] = (actMap[c.activity] || 0) + c.totalTokens;
  });

  const sorted = Object.entries(actMap).sort((a, b) => b[1] - a[1]);
  const maxTokens = sorted.length ? sorted[0][1] : 1;

  $("#activityList").innerHTML = sorted.length ? sorted.map(([name, tokens]) => `<div><div class="activity-head"><strong>${escapeHtml(name)}</strong><span>${formatTokens(tokens)}</span></div><div class="activity-track"><span style="width:${(tokens / maxTokens) * 100}%"></span></div></div>`).join("") : "<p style='color:var(--muted);font-size:11px'>No activity recorded for filter</p>";
}

function renderModelBreakdown(cases, globalCost, globalTokens) {
  const modelMap = {};
  cases.forEach(c => {
    if (!modelMap[c.model]) {
      modelMap[c.model] = { prompt: 0, output: 0, cached: 0, total: 0, cost: 0, count: 0 };
    }
    modelMap[c.model].prompt += c.promptTokens;
    modelMap[c.model].output += c.completionTokens;
    modelMap[c.model].cached += c.cachedTokens;
    modelMap[c.model].total += c.totalTokens;
    modelMap[c.model].cost += c.cost;
    modelMap[c.model].count += 1;
  });

  const sorted = Object.entries(modelMap).sort((a, b) => b[1].cost - a[1].cost);

  $("#modelBreakdownList").innerHTML = sorted.length ? sorted.map(([mName, data]) => {
    const costPct = globalCost ? Math.round((data.cost / globalCost) * 100) : 0;
    const tokenPct = globalTokens ? Math.round((data.total / globalTokens) * 100) : 0;

    return `<div class="model-card"><div class="model-card-head"><span class="model-tag">${escapeHtml(mName)}</span><strong class="model-cost">$${data.cost.toFixed(4)}</strong></div><div class="model-card-sub"><span>In: ${formatTokens(data.prompt)} · Out: ${formatTokens(data.output)} · Cached: ${formatTokens(data.cached)}</span><span>${tokenPct}% tokens · ${costPct}% cost</span></div><div class="activity-track"><span style="width:${costPct}%"></span></div></div>`;
  }).join("") : "<p style='color:var(--muted);font-size:11px'>No model usage recorded</p>";
}

function renderEfficiency(savingsPct, cachePct, cacheCoveragePct, output, total, cases) {
  const outputPct = (output / Math.max(1, total) * 100).toFixed(1);
  const score = Math.round(Number(savingsPct));
  const activityTotals = {};
  cases.forEach(item => {
    activityTotals[item.activity] = (activityTotals[item.activity] || 0) + item.totalTokens;
  });
  const highestActivity = Object.entries(activityTotals).sort(([, left], [, right]) => right - left)[0]?.[0] || "No data";

  $("#efficiencyValue").textContent = `${score}%`;
  $("#efficiencyRing").style.background = `conic-gradient(var(--pine) 0 ${score}%, #e8eeeb ${score}%)`;
  $("#cacheFact").textContent = `${cachePct}% of ${state.mode === "live" ? "measured" : "projected reusable"} input`;
  $("#outputRatio").textContent = `${outputPct}% of total`;
  $("#highestActivity").textContent = highestActivity;
  if ($("#cacheCoverage")) $("#cacheCoverage").textContent = `${cacheCoveragePct}% of calls`;
}

function renderAnomalies(filtered) {
  const measuredCount = filtered.filter(c => c.cacheMeasured).length;
  const unknownPriceCount = filtered.filter(c => c.cost === null).length;
  const sourceFact = state.mode === "live" && state.telemetryError ? {
    title: "Live telemetry unavailable",
    body: `${state.telemetryError}. No provider usage result is available for this view.`,
  } : state.mode === "live" ? {
    title: "Live telemetry only",
    body: `${filtered.length} provider usage events loaded from Cosmos DB. Generated demonstration rows are excluded.`,
  } : {
    title: "Annual synthetic projection",
    body: `${filtered.reduce((sum, item) => sum + (item.projectedCases || 0), 0).toLocaleString()} projected document reviews are modeled across ${filtered.length} cohorts. These values are not measured Azure telemetry.`,
  };
  const list = [
    sourceFact,
    state.mode === "live" ? {
      title: "Cache evidence",
      body: `${measuredCount} events include provider-reported cache usage. Legacy events without that field are treated as uncached, not estimated.`,
    } : {
      title: "Cache assumption",
      body: "Reusable input is a modeled 94–98% target for projected cohorts, not provider-reported cache usage.",
    },
    {
      title: "Cost interpretation",
      body: `Costs are estimates from published Azure Global Standard list prices, not invoice charges.${unknownPriceCount ? ` ${unknownPriceCount} events use an unrecognized model and are excluded from cost totals.` : ""}`,
    },
  ];

  $("#anomalyCount").textContent = list.length;
  $("#anomalyList").innerHTML = list.map(a => `<article class="anomaly"><strong>${escapeHtml(a.title)}</strong><p>${escapeHtml(a.body)}</p></article>`).join("");
}

function renderCasesTable(cases) {
  const totalItems = cases.length;
  const pageSize = state.pageSize;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));

  if (state.currentPage > totalPages) state.currentPage = totalPages;
  if (state.currentPage < 1) state.currentPage = 1;

  const startIdx = (state.currentPage - 1) * pageSize;
  const endIdx = Math.min(totalItems, startIdx + pageSize);
  const pagedItems = cases.slice(startIdx, endIdx);

  $("#pageInfo").textContent = totalItems ? `Showing ${startIdx + 1}–${endIdx} of ${totalItems} calls` : "0 calls";
  $("#currentPageDisplay").textContent = `Page ${state.currentPage} of ${totalPages}`;

  $("#btnFirst").disabled = state.currentPage === 1;
  $("#btnPrev").disabled = state.currentPage === 1;
  $("#btnNext").disabled = state.currentPage === totalPages;
  $("#btnLast").disabled = state.currentPage === totalPages;

  const emptyMessage = state.mode === "live" && state.telemetryError
    ? `Live telemetry unavailable: ${escapeHtml(state.telemetryError)}`
    : "No cases match the selected range and filters";
  $("#caseRows").innerHTML = pagedItems.length ? pagedItems.map(row => {
    const sourceBadge = row.isLive ? `<span class="live-badge">LIVE AZURE</span>` : `<span class="synthetic-badge">PROJECTED</span>`;
    const dateFormatted = row.date.toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
    const cost = row.cost === null ? "Unavailable" : formatUsd(row.cost);
    const latency = row.latencyMs === null ? "Not captured" : `${row.latencyMs.toLocaleString()} ms`;
    const cached = formatCachedTokens(row);
    const dateOrVolume = row.isLive ? dateFormatted : `${row.projectedCases.toLocaleString()} projected reviews`;
    return `<tr class="case-row" data-case-id="${escapeHtml(row.caseId)}"><td class="case-link"><a href="#" class="case-open">${escapeHtml(row.caseId)}</a>${sourceBadge}<div style="font-size:9px;color:var(--muted)">${dateOrVolume}</div></td><td>${escapeHtml(row.tenant)}</td><td>${escapeHtml(row.activity)}</td><td><span class="model-tag">${escapeHtml(row.model)}</span></td><td class="numeric">${row.promptTokens.toLocaleString()}</td><td class="numeric">${row.completionTokens.toLocaleString()}</td><td class="numeric">${cached}</td><td class="numeric ${row.totalTokens > 25000 ? "high-usage" : ""}">${row.totalTokens.toLocaleString()}</td><td class="numeric">${cost}</td><td class="numeric">${latency}</td></tr>`;
  }).join("") : `<tr><td colspan="10" style="text-align:center;color:var(--muted);padding:24px">${emptyMessage}</td></tr>`;

  $("#visibleRows").textContent = `${totalItems} ${state.mode === "live" ? "provider calls" : "projection cohorts"}`;
}

function openCaseModal(caseId) {
  const caseRecords = state.cases.filter(c => c.caseId === caseId);
  if (!caseRecords.length) return;

  const first = caseRecords[0];
  const totalTokens = caseRecords.reduce((s, c) => s + c.totalTokens, 0);
  const totalCost = caseRecords.reduce((s, c) => s + (c.cost ?? 0), 0);

  $("#modalCaseId").textContent = `Case ${caseId}`;
  $("#modalTenant").textContent = first.tenant;
  $("#modalTotalTokens").textContent = formatTokens(totalTokens);
  $("#modalCost").textContent = formatUsd(totalCost);
  $("#modalModel").textContent = first.model;

  let html = `<table style="width:100%;margin-top:10px;border-collapse:collapse;font-size:11px"><thead><tr style="background:#eef2ef;text-align:left"><th>Activity / Stage</th><th>Model</th><th>Input</th><th>Output</th><th>Cached</th><th>Cost</th></tr></thead><tbody>`;

  caseRecords.forEach(r => {
    const cached = formatCachedTokens(r);
    const cost = r.cost === null ? "Unavailable" : formatUsd(r.cost);
    html += `<tr style="border-bottom:1px solid #dbe2de"><td><strong>${escapeHtml(r.activity)}</strong></td><td><span class="model-tag">${escapeHtml(r.model)}</span></td><td>${r.promptTokens.toLocaleString()}</td><td>${r.completionTokens.toLocaleString()}</td><td>${cached}</td><td>${cost}</td></tr>`;
  });
  html += `</tbody></table>`;

  $("#modalBreakdownList").innerHTML = html;
  $("#caseModal").hidden = false;
}

function updateModeUI() {
  const isLive = state.mode === "live";
  $("#btnSyntheticMode").classList.toggle("active", !isLive);
  $("#btnLiveMode").classList.toggle("active", isLive);
  $("#btnLiveMode").classList.toggle("live-active", isLive);
  $("#envBadge").className = `environment ${isLive ? "live" : "synthetic"}`;
  $("#envBadge").textContent = isLive ? "LIVE AZURE · COSMOS TELEMETRY" : "PROJECTED · SYNTHETIC DATA";
  $("#scopeLabelText").textContent = isLive ? "Measured provider telemetry" : "Annual evaluation projection";
  $("#costKpiLabel").textContent = isLive ? "Estimated Model Cost" : "Projected Annual Model Cost";
  $("#savingsKpiLabel").textContent = isLive ? "Measured Cache Savings" : "Projected Cache Savings";
  $("#cacheKpiLabel").textContent = isLive ? "Measured Cache Reuse" : "Projected Cache Reuse";
  $("#bannerTag").textContent = isLive ? "VERIFIABLE TOKEN ECONOMICS" : "PROJECTED TOKEN ECONOMICS";
  $("#bannerTitle").textContent = isLive ? "What did the observed model calls cost?" : "What could the annual evaluation workload cost?";
  $("#bannerDescription").innerHTML = isLive
    ? `ARIA uses the deployed <strong>GPT-4.1 nano 2025-04-14 Global Standard</strong> model. The comparison holds model and token volume constant, then removes only provider-reported cache discounts. Measured same-model savings: <strong id="bannerSavingsPct">0%</strong>.`
    : `This projection scales synthetic document-evaluation profiles to <strong>122,433 annual reviews</strong> using verified GPT-4.1 nano list rates. The comparison holds model and token volume constant, then removes projected cache reuse. Projected same-model savings: <strong id="bannerSavingsPct">0%</strong>.`;
  $("#baselineDetail").textContent = isLive ? "GPT-4.1 nano · same observed tokens" : "GPT-4.1 nano · same generated tokens";
  $("#workloadLabel").textContent = isLive ? "Observed ARIA Workload" : "Generated ARIA Workload";
  $("#workloadDetail").textContent = isLive ? "Provider token telemetry · cache when reported" : "Synthetic tokens · generated cache reuse";
  $("#comparisonSavingsLabel").textContent = isLive ? "Measured Cache Savings" : "Projected Cache Savings";
  $("#cacheExplainerNote").textContent = isLive
    ? "Legacy generated cache estimates are shown for audit history but treated as uncached. Only provider-reported cache tokens reduce measured cost."
    : "The projection assumes 94–98% reusable input after stable prompt templates, schemas, and policy context are cached. This is an optimization target, not measured performance or an invoice charge.";
  $("#provenanceBadge").textContent = isLive ? "Live Cosmos DB telemetry" : "Annual synthetic projection";
  $("#provenanceTitle").textContent = isLive ? "Provider token counts" : "Generated token counts";
  $("#provenanceText").textContent = isLive
    ? "Input, output, and cached-input values come from Azure OpenAI response metadata persisted in Cosmos DB. No generated dashboard rows are included."
    : "Daily review volume is projected from 122,433 annual evaluations. Token profiles and 94–98% reusable input are synthetic targets isolated from measured Cosmos DB telemetry.";
  $("#efficiencyEyebrow").textContent = isLive ? "Measured efficiency" : "Projected efficiency";
  $("#cacheCoverageLabel").textContent = isLive ? "Cache data coverage" : "Target profile coverage";
  $("#efficiencyMethod").textContent = isLive
    ? "Calculated as (same-model uncached estimate − observed estimate) ÷ same-model uncached estimate. It is not an accuracy score."
    : "Calculated as (same-model uncached estimate − projected estimate) ÷ same-model uncached estimate. It is not an accuracy score.";
  $("#tableEyebrow").textContent = isLive ? "Traceable spend by provider call" : "Projected spend by evaluation cohort";
  $("#footerSource").textContent = isLive ? "Cosmos DB persistent telemetry metadata" : "Projected from synthetic evaluation profiles";
}

function resetModeView() {
  state.currentPage = 1;
  $("#caseSearch").value = "";
  $("#caseFilter").value = "all";
  populateCaseFilter(state.cases);
  updateModeUI();
  render();
}

function useSyntheticMode() {
  state.mode = "synthetic";
  state.cases = syntheticCases;
  sessionStorage.setItem("ariaMode", "synthetic");
  $("#periodFilter").value = "365";
  resetModeView();
}

async function useLiveMode() {
  state.mode = "live";
  state.cases = state.liveCases;
  sessionStorage.setItem("ariaMode", "live");
  $("#periodFilter").value = "7";
  resetModeView();
  if (!state.cosmosLoaded) await fetchCosmosTelemetry();
  if (state.mode !== "live") return;
  state.cases = state.liveCases;
  resetModeView();
}

// Event Listeners
$("#btnSyntheticMode").addEventListener("click", useSyntheticMode);
$("#btnLiveMode").addEventListener("click", useLiveMode);

$("#caseRows").addEventListener("click", event => {
  const link = event.target.closest(".case-open");
  if (!link) return;
  event.preventDefault();
  openCaseModal(link.closest(".case-row").dataset.caseId);
});

$("#caseSearch").addEventListener("input", () => {
  state.currentPage = 1;
  render();
});

$("#caseFilter").addEventListener("change", () => {
  state.currentPage = 1;
  render();
});
$("#periodFilter").addEventListener("change", event => {
  const val = event.target.value;
  if (val !== "custom") {
    initDateDefaults();
  }
  state.currentPage = 1;
  render();
});

$("#fromDateFilter").addEventListener("change", () => {
  $("#periodFilter").value = "custom";
  state.currentPage = 1;
  render();
});

$("#toDateFilter").addEventListener("change", () => {
  $("#periodFilter").value = "custom";
  state.currentPage = 1;
  render();
});

$("#pageSizeSelect").addEventListener("change", event => {
  state.pageSize = parseInt(event.target.value, 10) || 10;
  state.currentPage = 1;
  render();
});

$("#btnFirst").addEventListener("click", () => {
  state.currentPage = 1;
  render();
});

$("#btnPrev").addEventListener("click", () => {
  if (state.currentPage > 1) {
    state.currentPage--;
    render();
  }
});

$("#btnNext").addEventListener("click", () => {
  state.currentPage++;
  render();
});

$("#btnLast").addEventListener("click", () => {
  const { filteredCases } = getFilteredCases();
  state.currentPage = Math.max(1, Math.ceil(filteredCases.length / state.pageSize));
  render();
});

$("#modalCloseBtn").addEventListener("click", () => {
  $("#caseModal").hidden = true;
});

// Floating Insights Toolbar & Modals Handler
document.querySelectorAll(".insight-tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const targetId = btn.getAttribute("data-target");
    const modal = document.getElementById(targetId);
    if (modal) modal.hidden = false;
  });
});

document.querySelectorAll(".insight-modal-close").forEach(btn => {
  btn.addEventListener("click", () => {
    const modal = btn.closest(".insight-modal");
    if (modal) modal.hidden = true;
  });
});

document.querySelectorAll(".insight-modal").forEach(modal => {
  modal.addEventListener("click", event => {
    if (event.target === modal) modal.hidden = true;
  });
});

if ($("#btnDailyGranular")) {
  $("#btnDailyGranular").addEventListener("click", () => {
    state.chartMode = "daily";
    $("#btnDailyGranular").classList.add("active");
    $("#btnAccumulatedGranular").classList.remove("active");
    render();
  });
}

if ($("#btnAccumulatedGranular")) {
  $("#btnAccumulatedGranular").addEventListener("click", () => {
    state.chartMode = "accumulated";
    $("#btnAccumulatedGranular").classList.add("active");
    $("#btnDailyGranular").classList.remove("active");
    render();
  });
}

$("#caseModal").addEventListener("click", event => {
  if (event.target === $("#caseModal")) {
    $("#caseModal").hidden = true;
  }
});

$("#exportButton").addEventListener("click", () => {
  const { filteredCases } = getFilteredCases();
  const csv = [
    "case_id,tenant,activity,model,projected_cases,prompt_tokens,completion_tokens,cached_tokens,cache_provenance,total_tokens,estimated_list_cost_usd,latency_ms,is_live,timestamp",
    ...filteredCases.map(r => [
      r.caseId,
      r.tenant,
      r.activity,
      r.model,
      r.projectedCases || "",
      r.promptTokens,
      r.completionTokens,
      r.cachedTokens,
      r.cacheProvenance || (r.cacheMeasured ? "provider" : "unavailable"),
      r.totalTokens,
      r.cost === null ? "" : r.cost.toFixed(5),
      r.latencyMs ?? "",
      r.isLive,
      r.date.toISOString(),
    ].map(csvCell).join(",")),
  ].join("\n");

  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  link.download = `aria-token-usage.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
});

// Initial Setup
initDateDefaults();
$("#periodFilter").value = state.mode === "live" ? "7" : "365";
updateModeUI();
render();
if (state.mode === "live") useLiveMode();

function renderHeatmap(cases) {
  const activities = [...new Set(cases.map(item => item.activity))];
  const models = [...new Set(cases.map(item => item.model))];

  if (!activities.length || !models.length) {
    $("#heatmapGrid").innerHTML = "<p style='color:var(--muted);font-size:11px'>No provider telemetry recorded for this filter</p>";
    return;
  }

  const matrix = {};
  activities.forEach(a => {
    matrix[a] = {};
    models.forEach(m => {
      matrix[a][m] = { prompt: 0, output: 0, cost: 0, count: 0 };
    });
  });

  cases.forEach(c => {
    matrix[c.activity][c.model].prompt += c.promptTokens;
    matrix[c.activity][c.model].output += c.completionTokens;
    matrix[c.activity][c.model].cost += c.cost ?? 0;
    matrix[c.activity][c.model].count += 1;
  });

  let html = `<table class="heatmap-table"><thead><tr><th>Pipeline Stage</th>${models.map(m => `<th>${escapeHtml(m)}</th>`).join("")}</tr></thead><tbody>`;

  activities.forEach(act => {
    html += `<tr><td class="stage-name">${escapeHtml(act)}</td>`;
    models.forEach(mod => {
      const cell = matrix[act][mod];
      const totalTok = cell.prompt + cell.output;
      let heatClass = "cell-zero";
      if (totalTok > 100000) heatClass = "cell-high";
      else if (totalTok > 25000) heatClass = "cell-med";
      else if (totalTok > 0) heatClass = "cell-low";

      const tooltip = escapeHtml(`${act} × ${mod}: ${formatTokens(totalTok)} tokens (${formatUsd(cell.cost)})`);
      html += `<td class="heat-cell ${heatClass}" title="${tooltip}"><div><strong>${totalTok ? formatTokens(totalTok) : "—"}</strong><small>${cell.cost ? "$" + cell.cost.toFixed(3) : ""}</small></div></td>`;
    });
    html += `</tr>`;
  });
  html += `</tbody></table>`;

  $("#heatmapGrid").innerHTML = html;
}