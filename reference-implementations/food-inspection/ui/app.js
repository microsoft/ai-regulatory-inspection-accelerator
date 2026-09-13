const state = {
  documents: [],
  selectedId: null,
  zoom: 1,
  processing: false,
  scenario: "food-en",
  mode: "synthetic",
  liveUnlocked: false,
};

const els = {
  fileInput: document.querySelector("#fileInput"), dropZone: document.querySelector("#dropZone"),
  sampleButton: document.querySelector("#sampleButton"), analyzeButton: document.querySelector("#analyzeButton"),
  resetButton: document.querySelector("#resetButton"), documentList: document.querySelector("#documentList"),
  documentCount: document.querySelector("#documentCount"), viewer: document.querySelector("#viewer"),
  viewerHeading: document.querySelector("#viewerHeading"), zoomLabel: document.querySelector("#zoomLabel"),
  zoomIn: document.querySelector("#zoomIn"), zoomOut: document.querySelector("#zoomOut"),
  processingStrip: document.querySelector("#processingStrip"), progressBar: document.querySelector("#progressBar"),
  progressPercent: document.querySelector("#progressPercent"), processingLabel: document.querySelector("#processingLabel"),
  processingDetail: document.querySelector("#processingDetail"), caseId: document.querySelector("#caseId"),
  caseStatus: document.querySelector("#caseStatus"), decisionEmpty: document.querySelector("#decisionEmpty"),
  decisionContent: document.querySelector("#decisionContent"), recommendationHeading: document.querySelector("#recommendationHeading"),
  riskBadge: document.querySelector("#riskBadge"), verdictText: document.querySelector("#verdictText"),
  verdictIcon: document.querySelector("#verdictIcon"), verdictSummary: document.querySelector("#verdictSummary"),
  caseReference: document.querySelector("#caseReference"),
  confidenceValue: document.querySelector("#confidenceValue"), confidenceBar: document.querySelector("#confidenceBar"),
  findingCount: document.querySelector("#findingCount"), findingsList: document.querySelector("#findingsList"),
  traceList: document.querySelector("#traceList"),
  comparisonCount: document.querySelector("#comparisonCount"), comparisonList: document.querySelector("#comparisonList"),
  scenarioSelect: document.querySelector("#scenarioSelect"),
  clearCaseBtn: document.querySelector("#clearCaseBtn"),
};

const scenarios = {
  "food-en": {
    label: "Food safety · English",
    caseId: "FOOD-EN-2408",
    docs: [
      { name: "Commercial_Invoice.pdf", type: "Commercial Invoice", size: 482000, title: "COMMERCIAL INVOICE", rows: [["Reference", "INV-2026-1842"], ["Commodity", "Frozen poultry products"], ["Net weight", "12,400 kg"], ["Origin", "Brazil"]] },
      { name: "Health_Certificate.pdf", type: "Health Certificate", size: 735000, title: "HEALTH CERTIFICATE", rows: [["Reference", "HC-BR-88219"], ["Commodity", "Frozen poultry products"], ["Net weight", "12,400 kg"], ["Validity", "2026-11-30"]] },
      { name: "Halal_Certificate.pdf", type: "Halal Certificate", size: 364000, title: "HALAL CERTIFICATE", rows: [["Reference", "HAL-77218"], ["Commodity", "Frozen poultry products"], ["Net weight", "12,150 kg"], ["Validity", "2026-10-18"]] },
    ],
    result: { risk: "MEDIUM", confidence: 87, verdict: "Hold for review", summary: "A material weight mismatch requires inspector confirmation before release.", comparisons: [["Net weight", "Commercial Invoice · Health Certificate · Halal Certificate", "Mismatch · 12,150 kg vs 12,400 kg"], ["Commodity", "Commercial Invoice ↔ Health Certificate ↔ Halal Certificate", "Match · Frozen poultry products", true]], findings: [["Weight discrepancy", "Halal certificate states 12,150 kg; invoice and health certificate state 12,400 kg."], ["Certificate authority verified", "Issuer appears in the approved authority reference list.", true], ["Dates remain valid", "All certificate expiry dates extend beyond the inspection date.", true]] },
  },
  "food-ar": {
    label: "سلامة الغذاء · العربية",
    caseId: "FOOD-AR-2409",
    docs: [
      { name: "فاتورة_تجارية.pdf", type: "فاتورة تجارية", size: 512000, title: "فاتورة تجارية", rows: [["رقم الفاتورة", "INV-AR-7721"], ["وصف المنتج", "منتجات دواجن مجمدة"], ["الوزن الصافي", "8,200 كجم"], ["بلد المنشأ", "البرازيل"]], rtl: true },
      { name: "شهادة_صحية.pdf", type: "شهادة صحية", size: 684000, title: "شهادة صحية", rows: [["رقم الشهادة", "HC-AR-4412"], ["وصف المنتج", "منتجات دواجن مجمدة"], ["الوزن الصافي", "8,200 كجم"], ["الصلاحية", "2027-01-20"]], rtl: true },
      { name: "شهادة_الحلال.pdf", type: "شهادة حلال", size: 401000, title: "شهادة حلال", rows: [["رقم الشهادة", "HAL-AR-1188"], ["وصف المنتج", "قطع لحم مجمدة"], ["الوزن الصافي", "8,200 كجم"], ["الصلاحية", "2026-12-14"]], rtl: true },
    ],
    result: {
      risk: "MEDIUM",
      confidence: 86,
      verdict: "احتجاز للمراجعة",
      summary: "تفاوت في وصف المنتج بين الفاتورة وشهادة الحلال يتطلب مراجعة المفتش قبل الإفراج.",
      comparisons: [
        ["وصف المنتج", "الفاتورة التجارية · الشهادة الصحية · شهادة الحلال", "غير مطابق · منتجات دواجن مجمدة مقابل قطع لحم مجمدة", false],
        ["الوزن الصافي", "الفاتورة ↔ الشهادة الصحية ↔ شهادة الحلال", "مطابق · 8,200 كجم", true]
      ],
      findings: [
        ["تفاوت في وصف المنتج", "تشير شهادة الحلال إلى 'قطع لحم مجمدة' بينما تنص الفاتورة والشهادة الصحية على 'منتجات دواجن مجمدة'."],
        ["تطبيق معايير اللغة العربية والأرقام الشرقية", "تم توحيد خانات النص العربي والأرقام وعلامات الاتجاه (RTL) تلقائياً قبل المقارنة.", true],
        ["صلاحية الشهادات", "جميع تواريخ انتهاء الشهادات سارية وتتجاوز تاريخ التفتيش الحالي.", true]
      ]
    },
  },
  customs: {
    label: "Customs clearance",
    caseId: "CUSTOMS-1182",
    docs: [
      { name: "Bill_of_Lading.pdf", type: "Bill of Lading", size: 611000, title: "BILL OF LADING", rows: [["Bill number", "BL-88421"], ["Consignee", "Northstar Imports"], ["Packages", "240 cartons"], ["Origin", "Vietnam"]] },
      { name: "Customs_Declaration.pdf", type: "Customs Declaration", size: 758000, title: "CUSTOMS DECLARATION", rows: [["Declaration", "CD-99102"], ["Consignee", "Northstar Imports"], ["Packages", "240 cartons"], ["HS code", "1905.90"]] },
      { name: "Certificate_of_Origin.pdf", type: "Certificate of Origin", size: 449000, title: "CERTIFICATE OF ORIGIN", rows: [["Certificate", "CO-VN-5521"], ["Exporter", "Mekong Foods"], ["Origin", "Vietnam"], ["Issue date", "2026-08-22"]] },
    ],
    result: { risk: "MEDIUM", confidence: 89, verdict: "Hold for review", summary: "The declared HS code needs a policy reviewer before clearance.", comparisons: [["Package count", "Bill of Lading ↔ Customs Declaration", "Match · 240 cartons", true], ["Country of origin", "Declaration ↔ Certificate of Origin", "Match · Vietnam", true]], findings: [["HS classification review", "The declaration uses a code requiring controlled-list verification."], ["Package count matches", "Bill of lading and declaration both list 240 cartons.", true], ["Origin consistent", "The origin certificate and declaration agree.", true]] },
  },
  kyc: {
    label: "KYC onboarding",
    caseId: "KYC-7730",
    docs: [
      { name: "Identity_Document.pdf", type: "Identity Document", size: 323000, title: "IDENTITY DOCUMENT", rows: [["Full name", "Amina Rahman"], ["Document number", "ID-884120"], ["Nationality", "Canada"], ["Expiry", "2030-04-12"]] },
      { name: "Ownership_Record.pdf", type: "Ownership Record", size: 512000, title: "OWNERSHIP RECORD", rows: [["Full name", "Amina Rahman"], ["Entity", "Northstar Holdings"], ["Ownership", "75%"], ["Issued", "2026-08-04"]] },
      { name: "Proof_of_Address.pdf", type: "Proof of Address", size: 285000, title: "PROOF OF ADDRESS", rows: [["Full name", "Amina Rahman"], ["Address", "18 Harbour Street"], ["Country", "Canada"], ["Issued", "2026-08-28"]] },
    ],
    result: { risk: "LOW", confidence: 96, verdict: "Recommend approval", summary: "Identity, ownership, and address evidence are consistent for reviewer approval.", comparisons: [["Full name", "Identity ↔ Ownership ↔ Address", "Match · Amina Rahman", true], ["Nationality / country", "Identity ↔ Address", "Match · Canada", true]], findings: [["Identity verified", "Name and document number are present and internally consistent.", true], ["Ownership relationship mapped", "Beneficial ownership is linked to the entity record.", true], ["Address evidence current", "Proof of address is within the configured recency window.", true]] },
  },
  insurance: {
    label: "Insurance claim",
    caseId: "CLAIM-4820",
    docs: [
      { name: "Claim_Form.pdf", type: "Claim Form", size: 390000, title: "CLAIM FORM", rows: [["Claim number", "CL-4820"], ["Claimant", "Jordan Lee"], ["Incident", "Water damage"], ["Amount", "$14,800"]] },
      { name: "Adjuster_Report.pdf", type: "Adjuster Report", size: 620000, title: "ADJUSTER REPORT", rows: [["Claim number", "CL-4820"], ["Claimant", "Jordan Lee"], ["Assessment", "Covered damage"], ["Amount", "$12,800"]] },
      { name: "Repair_Invoice.pdf", type: "Repair Invoice", size: 298000, title: "REPAIR INVOICE", rows: [["Invoice", "REP-1184"], ["Customer", "Jordan Lee"], ["Work", "Water remediation"], ["Amount", "$12,800"]] },
    ],
    result: { risk: "MEDIUM", confidence: 88, verdict: "Refer to adjuster", summary: "The claimed amount differs from the assessed and invoiced amount.", comparisons: [["Claim amount", "Claim Form ↔ Adjuster Report ↔ Repair Invoice", "Mismatch · $14,800 vs $12,800"], ["Claimant", "Claim Form ↔ Adjuster Report ↔ Repair Invoice", "Match · Jordan Lee", true]], findings: [["Amount discrepancy", "The claim requests $14,800 while the report and invoice support $12,800."], ["Claim identity matches", "Claim number and claimant agree across documents.", true], ["Repair scope supported", "Invoice work is consistent with the adjuster report.", true]] },
  },
};

function id() { return `${Date.now()}-${Math.random().toString(16).slice(2)}`; }
function prettySize(bytes) { return bytes < 1e6 ? `${Math.max(1, Math.round(bytes / 1000))} KB` : `${(bytes / 1e6).toFixed(1)} MB`; }
function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[character]);
}
function inferType(name) {
  const value = name.toLowerCase();
  if (value.includes("halal")) return "Halal Certificate";
  if (value.includes("health")) return "Health Certificate";
  if (value.includes("invoice")) return "Commercial Invoice";
  if (value.includes("declaration")) return "Customs Declaration";
  return "Supporting Evidence";
}

function addFiles(files) {
  const accepted = [...files].filter(file => /pdf|png|jpeg|jpg|tiff/i.test(file.type) || /\.(pdf|png|jpe?g|tiff?)$/i.test(file.name));
  accepted.forEach(file => state.documents.push({ id: id(), name: file.name, type: inferType(file.name), size: file.size, file, url: URL.createObjectURL(file) }));
  if (!state.selectedId && state.documents.length) state.selectedId = state.documents[0].id;
  if (els.fileInput) els.fileInput.value = "";
  renderDocuments(); renderViewer();
}

function loadSample() {
  reset(false);
  const scenario = scenarios[state.scenario];
  state.documents = scenario.docs.map(doc => ({ ...doc, sample: true, id: id() }));
  state.selectedId = state.documents[0].id;
  els.caseId.textContent = `Case ${scenario.caseId}`;
  renderDocuments(); renderViewer();
}

function renderDocuments() {
  els.documentList.innerHTML = "";
  state.documents.forEach(doc => {
    const safeName = escapeHtml(doc.name);
    const safeType = escapeHtml(doc.type);
    const card = document.createElement("div");
    card.className = `document-row${doc.id === state.selectedId ? " active" : ""}`;
    card.innerHTML = `<button class="document-select" type="button" data-select="${doc.id}">
      <span class="file-icon">${doc.name.split(".").pop().slice(0, 4).toUpperCase()}</span>
      <span><strong title="${safeName}">${safeName}</strong><small>${safeType} · ${prettySize(doc.size)}</small></span></button>
      <button class="remove-file" type="button" data-remove="${doc.id}" aria-label="Remove ${safeName}">×</button>`;
    card.querySelector("[data-select]").addEventListener("click", () => { state.selectedId = doc.id; renderDocuments(); renderViewer(); });
    card.querySelector("[data-remove]").addEventListener("click", () => removeDocument(doc.id));
    els.documentList.appendChild(card);
  });
  els.documentCount.textContent = state.documents.length;
  els.analyzeButton.disabled = state.documents.length === 0 || state.processing;
}

function removeDocument(documentId) {
  const doc = state.documents.find(item => item.id === documentId);
  if (doc?.url) URL.revokeObjectURL(doc.url);
  state.documents = state.documents.filter(item => item.id !== documentId);
  if (state.selectedId === documentId) state.selectedId = state.documents[0]?.id || null;
  renderDocuments(); renderViewer();
}

function sampleMarkup(doc) {
  const rows = doc.rows.map(([label, value]) => `<tr><td>${escapeHtml(label)}</td><td><strong>${escapeHtml(value)}</strong></td></tr>`).join("");
  return `<article class="sample-document"${doc.rtl ? ' dir="rtl"' : ""}><div class="doc-top"><div><h3>${escapeHtml(doc.title)}</h3><p>ARIA synthetic evidence</p></div><span class="seal">VERIFIED</span></div>
    <p>Structured evidence prepared for the ARIA hackathon walkthrough.</p><table>${rows}</table><span class="document-stamp">SAMPLE CASE</span></article>`;
}

function renderViewer() {
  const doc = state.documents.find(item => item.id === state.selectedId);
  els.zoomLabel.textContent = `${Math.round(state.zoom * 100)}%`;
  if (!doc) {
    els.viewerHeading.textContent = "Select a document";
    els.viewer.className = "viewer-empty";
    els.viewer.innerHTML = `<div><div class="empty-visual" aria-hidden="true"><span></span><span></span><span></span></div><h3>Evidence appears here</h3><p>Upload a bundle or load the sample case to begin.</p></div>`;
    return;
  }
  els.viewerHeading.textContent = doc.name;
  els.viewer.className = "";
  if (doc.sample) els.viewer.innerHTML = sampleMarkup(doc);
  else if (doc.file.type.startsWith("image/")) els.viewer.innerHTML = `<img class="preview-image" src="${doc.url}" alt="Preview of ${doc.name}">`;
  else els.viewer.innerHTML = `<iframe class="preview-frame" src="${doc.url}" title="Preview of ${doc.name}"></iframe>`;
  const preview = els.viewer.firstElementChild;
  if (preview) preview.style.transform = `scale(${state.zoom})`;
}

function delay(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }
async function analyze() {
  if (!state.documents.length || state.processing) return;
  if (state.mode === "live" && window.ARIA_CONFIG?.liveEndpoint) {
    return analyzeLive();
  }
  state.processing = true; renderDocuments();
  els.processingStrip.hidden = false; els.caseStatus.textContent = "Processing";
  if (els.caseId.textContent === "Case —") els.caseId.textContent = `Case DEMO-${String(Date.now()).slice(-4)}`;
  const stages = [
    [12, "Bundle validation", "Checking document inventory and integrity"],
    [34, "Document intelligence", "Extracting structured fields and confidence"],
    [58, "Cross-document reasoning", "Reconciling facts across the evidence bundle"],
    [78, "Policy evaluation", "Applying food inspection rules"],
    [100, "Decision synthesis", "Building recommendation and evidence trace"],
  ];
  for (const [progress, label, detail] of stages) {
    els.processingLabel.textContent = label; els.processingDetail.textContent = detail;
    els.progressBar.style.width = `${progress}%`; els.progressPercent.textContent = `${progress}%`;
    await delay(620);
  }
  const scenario = scenarios[state.scenario];
  const baseTokens = state.documents.length * 860;
  const tokenEvents = [
    ["Quality assessment", 420, 72, 260],
    ["Field extraction", baseTokens, 540, Math.round(baseTokens * 0.42)],
    ["Cross-document reasoning", 980, 210, 620],
    ["Policy evaluation", 180, 80, 120],
    ["Decision summary", 260, 96, 180],
  ].map(([activity, promptTokens, completionTokens, cachedTokens], index) => ({
    caseId: scenario?.caseId || els.caseId.textContent.replace("Case ", ""),
    tenant: scenario?.label || "Uploaded evidence",
    activity,
    model: index === 1 ? "gpt-4.1-mini" : "gpt-4.1",
    promptTokens,
    completionTokens,
    cachedTokens,
    latencyMs: 180 + index * 130,
  }));
  localStorage.setItem("ariaTokenEvents", JSON.stringify(tokenEvents));
  showDecision();
  state.processing = false; renderDocuments(); els.caseStatus.textContent = "Review ready";
  await delay(300); els.processingStrip.hidden = true;
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const res = reader.result;
      const base64 = typeof res === "string" && res.includes(",") ? res.split(",")[1] : res;
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function analyzeLive() {
  state.processing = true; renderDocuments(); els.processingStrip.hidden = false; els.caseStatus.textContent = "Live Azure processing";
  const processingStarted = performance.now();
  const updateLiveProgress = () => {
    const elapsedSeconds = Math.floor((performance.now() - processingStarted) / 1000);
    let phase = "Sending evidence to Azure";
    let detail = `${state.documents.length} document${state.documents.length === 1 ? "" : "s"} queued`;
    if (elapsedSeconds >= 3) {
      phase = "Azure is processing the evidence bundle";
      detail = "Document extraction and model reasoning are still running";
    }
    if (elapsedSeconds >= 30) {
      phase = "Waiting for the slowest document extraction";
      detail = "The other documents continue in parallel; the result will appear when all finish";
    }
    if (elapsedSeconds >= 60) {
      phase = "Azure is completing the inspection";
      detail = "Finalizing cross-document checks and the recommendation";
    }
    els.processingLabel.textContent = phase;
    els.processingDetail.textContent = `${detail} · ${elapsedSeconds}s elapsed`;
    els.progressBar.style.width = `${Math.min(92, 18 + (elapsedSeconds % 12) * 6)}%`;
    els.progressPercent.textContent = `${elapsedSeconds}s`;
  };
  updateLiveProgress();
  const progressTimer = window.setInterval(updateLiveProgress, 1000);
  const documents = await Promise.all(state.documents.map(async doc => {
    const item = {
      documentId: doc.id,
      name: doc.name,
      type: doc.type,
      text: doc.rows ? doc.rows.map(([label, value]) => `${label}: ${value}`).join("\n") : "",
    };
    if (doc.file) {
      item.contentBase64 = await fileToBase64(doc.file);
    }
    return item;
  }));
  try {
    const response = await fetch(window.ARIA_CONFIG.liveEndpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(window.ARIA_CONFIG.apiKey ? { "x-functions-key": window.ARIA_CONFIG.apiKey } : {}),
      },
      body: JSON.stringify({ requestId: `LIVE-${Date.now()}`, documents }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.message || "Live inspection failed");
    els.caseId.textContent = `Case ${result.requestId}`;
    els.caseReference.textContent = `Case reference: ${result.requestId}`;
    els.processingLabel.textContent = "Azure pipeline complete"; els.processingDetail.textContent = `${result.modelNames.text} · ${result.stages.length} stages`;
    els.progressBar.style.width = "100%"; els.progressPercent.textContent = "100%";
    state.liveResult = result;

    if (result.tokenUsage && Array.isArray(result.tokenUsage) && result.tokenUsage.length) {
      const scenario = scenarios[state.scenario];
      const caseId = result.requestId || scenario?.caseId || `LIVE-${Date.now()}`;
      const tenant = scenario?.label || "Food Safety · Live Azure";
      const liveEvents = result.tokenUsage.map(tu => {
        const p = tu.promptTokens || 0;
        const c = tu.completionTokens || 0;
        return {
          caseId,
          tenant,
          activity: tu.stage === "document-intelligence" ? "Document Intelligence Extraction" : (tu.stage || "Pipeline Activity"),
          model: tu.model || result.modelNames?.text || "aria-text-mini",
          promptTokens: p,
          completionTokens: c,
          cachedTokens: Math.round(p * 0.25),
          latencyMs: Math.round(1100 + Math.random() * 300),
          isLive: true,
          date: new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "short" }),
        };
      });
      const existing = JSON.parse(localStorage.getItem("ariaTokenEvents") || "[]");
      localStorage.setItem("ariaTokenEvents", JSON.stringify([...liveEvents, ...existing]));
    }

    showLiveDecision(result);
    els.caseStatus.textContent = "Live review ready";
  } catch (error) {
    els.caseStatus.textContent = "Live unavailable · demo fallback";
    state.processing = false; els.processingStrip.hidden = true;
    showDecision();
  } finally {
    window.clearInterval(progressTimer);
    state.processing = false; renderDocuments(); await delay(300); els.processingStrip.hidden = true;
  }
}

function formatEvidence(obj) {
  if (!obj || typeof obj !== "object") return String(obj);
  return Object.entries(obj).map(([docKey, value]) => {
    const doc = state.documents.find(d => d.id === docKey || d.name === docKey);
    const label = doc ? doc.name : docKey;
    return `${label}: "${value}"`;
  }).join(" · ");
}

function safeText(value, fallback = "—") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function formatStageTrace(stages) {
  if (!Array.isArray(stages) || !stages.length) return "";

  let previousTs = null;
  return stages.map(stage => {
    const name = safeText(stage.name || "Stage");
    const status = safeText(stage.status || "updated");
    const detail = safeText(stage.detail || "");
    const currentTs = stage.timestamp ? new Date(stage.timestamp).getTime() : null;
    const elapsedMs = previousTs && currentTs ? Math.max(0, currentTs - previousTs) : 0;
    previousTs = currentTs ?? previousTs;
    const elapsed = elapsedMs > 0 ? ` · ${Math.round(elapsedMs / 100) / 10}s` : "";
    return `<li><strong>${escapeHtml(name)}</strong> · ${escapeHtml(status)}${elapsed}${detail ? ` · ${escapeHtml(detail)}` : ""}</li>`;
  }).join("");
}

function showLiveDecision(result) {
  const risk = result.riskEvaluation || {};
  const comparisons = result.comparisons || [];
  const findings = result.findings || [];
  els.decisionEmpty.hidden = true; els.decisionContent.hidden = false;
  els.recommendationHeading.textContent = "Azure inspection complete";
  els.riskBadge.textContent = risk.aiRiskLevel || "REVIEW"; els.riskBadge.className = `risk-badge ${risk.aiRiskLevel === "Low" ? "low" : "medium"}`;
  els.verdictText.textContent = risk.recommendationLabel || risk.recommendation || "Review required";
  els.caseReference.textContent = `Case reference: ${result.requestId || "—"}`;
  els.verdictIcon.textContent = risk.aiRiskLevel === "Low" ? "✓" : "!";
  els.verdictSummary.textContent = `Live models: ${result.modelNames.text}; ${result.delivery.status}.`;

  let confidencePct = 90;
  if (result.extractedFields && typeof result.extractedFields === "object") {
    let sumConf = 0, countConf = 0;
    Object.values(result.extractedFields).forEach(doc => {
      if (doc && doc.fields && typeof doc.fields === "object") {
        Object.values(doc.fields).forEach(f => {
          if (f && typeof f.confidence === "number") {
            sumConf += f.confidence;
            countConf++;
          }
        });
      }
    });
    if (countConf > 0) {
      confidencePct = Math.round((sumConf / countConf) * 100);
    }
  }
  els.confidenceValue.textContent = `${confidencePct}%`;
  els.confidenceBar.style.width = `${confidencePct}%`;

  els.findingCount.textContent = findings.length;
  els.findingsList.innerHTML = findings.map(item => {
    const status = String(item.result || "FAIL").toUpperCase();
    const pass = status === "PASS";
    const title = safeText(item.title || item.ruleCode || "Finding");
    const message = safeText(item.message || item.summary || formatEvidence(item.evidence), "No details provided.");
    const action = safeText(item.suggestedAction || "Review the discrepancy before release.");
    return `<article class="finding${pass ? " pass" : ""}"><strong>${pass ? "✓" : "!"} ${escapeHtml(title)}</strong><p><strong>${escapeHtml(status)}</strong> · ${escapeHtml(message)}</p><p class="finding-action"><strong>Action:</strong> ${escapeHtml(action)}</p></article>`;
  }).join("");

  els.comparisonCount.textContent = comparisons.length;
  els.comparisonList.innerHTML = comparisons.map(item => {
    const status = String(item.result || "FAIL").toUpperCase();
    const pass = status === "PASS";
    const label = safeText(item.fieldLabel || item.field || "Check");
    const text = safeText(item.message || formatEvidence(item.values), "No comparison details available.");
    const action = safeText(item.suggestedAction || "Review and reconcile the variance before release.");
    return `<article class="finding${pass ? " pass" : ""}"><strong>${pass ? "✓" : "!"} ${escapeHtml(label)}</strong><p>${escapeHtml(text)}</p><p class="finding-action"><strong>Action:</strong> ${escapeHtml(action)}</p></article>`;
  }).join("");
  els.traceList.innerHTML = formatStageTrace(result.stages || []);
}

function showDecision() {
  const scenario = state.documents.some(doc => doc.sample || doc.rows) ? scenarios[state.scenario] : null;
  const result = scenario?.result || { risk: "MEDIUM", confidence: 82, verdict: "Hold for review", summary: "Uploaded evidence requires reviewer attention.", findings: [["Evidence uploaded", "The document bundle is ready for backend processing."]] };
  els.decisionEmpty.hidden = true; els.decisionContent.hidden = false;
  els.recommendationHeading.textContent = "Inspection complete";
  els.riskBadge.textContent = result.risk; els.riskBadge.className = `risk-badge ${result.risk === "LOW" ? "low" : "medium"}`;
  els.verdictText.textContent = result.verdict; els.verdictIcon.textContent = result.risk === "LOW" ? "✓" : "!";
  els.caseReference.textContent = `Case reference: ${scenario?.caseId || els.caseId.textContent.replace("Case ", "")}`;
  els.verdictSummary.textContent = result.summary;
  els.confidenceValue.textContent = `${result.confidence}%`; els.confidenceBar.style.width = `${result.confidence}%`;
  const findings = result.findings.map(([title, detail, pass]) => ({ title, detail, pass }));
  els.findingCount.textContent = findings.length;
  els.findingsList.innerHTML = findings.map(item => `<article class="finding${item.pass ? " pass" : ""}"><strong>${item.pass ? "✓ " : "! "}${item.title}</strong><p>${item.detail}</p></article>`).join("");
  const comparisons = result.comparisons || [];
  els.comparisonCount.textContent = comparisons.length;
  els.comparisonList.innerHTML = comparisons.map(([field, sources, outcome, pass]) => `<article class="finding${pass ? " pass" : ""}"><strong>${pass ? "✓ " : "! "}${escapeHtml(field)}</strong><p>${escapeHtml(sources)}</p><p><strong>${escapeHtml(outcome)}</strong></p></article>`).join("");
  els.traceList.innerHTML = [
    { name: "Bundle accepted", detail: "Input validated", elapsed: 0.2 },
    { name: "Documents extracted", detail: `${state.documents.length} files processed`, elapsed: 0.8 },
    { name: "Evidence reconciled", detail: "Cross-document facts aligned", elapsed: 1.4 },
    { name: "Policy evaluated", detail: "Inspection rules applied", elapsed: 2.1 },
    { name: "Recommendation prepared", detail: result.risk === "LOW" ? "Approval recommendation ready" : "Human review threshold applied", elapsed: 2.8 },
  ].map(item => `<li><strong>${escapeHtml(item.name)}</strong> · ${item.elapsed.toFixed(1)}s${item.detail ? ` · ${escapeHtml(item.detail)}` : ""}</li>`).join("");
}

function reset(clearFiles = true) {
  if (clearFiles) state.documents.forEach(doc => doc.url && URL.revokeObjectURL(doc.url));
  state.documents = []; state.selectedId = null; state.zoom = 1; state.processing = false;
  if (els.fileInput) els.fileInput.value = "";
  els.caseId.textContent = "Case —"; els.caseStatus.textContent = "Ready"; els.caseReference.textContent = "Case reference: —"; els.processingStrip.hidden = true;
  els.decisionEmpty.hidden = false; els.decisionContent.hidden = true; els.recommendationHeading.textContent = "Awaiting evidence";
  els.riskBadge.textContent = "—"; els.riskBadge.className = "risk-badge neutral";
  renderDocuments(); renderViewer();
}

els.fileInput.addEventListener("change", event => addFiles(event.target.files));
els.dropZone.addEventListener("dragover", event => { event.preventDefault(); els.dropZone.classList.add("dragging"); });
els.dropZone.addEventListener("dragleave", () => els.dropZone.classList.remove("dragging"));
els.dropZone.addEventListener("drop", event => { event.preventDefault(); els.dropZone.classList.remove("dragging"); addFiles(event.dataTransfer.files); });
els.sampleButton.addEventListener("click", loadSample); els.analyzeButton.addEventListener("click", analyze); els.resetButton.addEventListener("click", () => reset());
if (els.clearCaseBtn) els.clearCaseBtn.addEventListener("click", () => reset());
els.zoomIn.addEventListener("click", () => { state.zoom = Math.min(1.5, state.zoom + 0.1); renderViewer(); });
els.zoomOut.addEventListener("click", () => { state.zoom = Math.max(0.7, state.zoom - 0.1); renderViewer(); });
Object.entries(scenarios).forEach(([key, scenario]) => {
  const option = document.createElement("option"); option.value = key; option.textContent = scenario.label; els.scenarioSelect.appendChild(option);
});
els.scenarioSelect.value = state.scenario;
els.scenarioSelect.addEventListener("change", event => { state.scenario = event.target.value; loadSample(); });

const diffTrigger = document.querySelector("#differentiatorTrigger");
const diffModal = document.querySelector("#differentiatorsModal");
const diffClose = document.querySelector("#diffModalCloseBtn");

if (diffTrigger && diffModal && diffClose) {
  diffTrigger.addEventListener("click", e => {
    e.preventDefault();
    diffModal.hidden = false;
  });
  diffClose.addEventListener("click", () => {
    diffModal.hidden = true;
  });
  diffModal.addEventListener("click", e => {
    if (e.target === diffModal) diffModal.hidden = true;
  });
}

// Mode Toggle & Password Lock Controls
const btnSyntheticMode = document.querySelector("#btnSyntheticMode");
const btnLiveMode = document.querySelector("#btnLiveMode");
const envBadge = document.querySelector("#envBadge");
const liveAuthModal = document.querySelector("#liveAuthModal");
const authModalCloseBtn = document.querySelector("#authModalCloseBtn");
const authCancelBtn = document.querySelector("#authCancelBtn");
const authForm = document.querySelector("#authForm");
const passcodeInput = document.querySelector("#passcodeInput");
const authError = document.querySelector("#authError");

function updateModeUI() {
  const isLive = state.mode === "live";
  if (btnSyntheticMode) {
    btnSyntheticMode.classList.toggle("active", !isLive);
  }
  if (btnLiveMode) {
    btnLiveMode.classList.toggle("active", isLive);
    btnLiveMode.classList.toggle("live-active", isLive);
    btnLiveMode.textContent = state.liveUnlocked ? (isLive ? "🟢 Live Azure" : "🔓 Live Azure") : "🔒 Live Azure";
  }
  if (envBadge) {
    if (isLive) {
      envBadge.textContent = "LIVE AZURE · DURABLE FUNCTIONS";
      envBadge.className = "environment live";
    } else {
      envBadge.textContent = "DEMO · SYNTHETIC (LOCAL)";
      envBadge.className = "environment synthetic";
    }
  }
}

if (btnSyntheticMode) {
  btnSyntheticMode.addEventListener("click", () => {
    state.mode = "synthetic";
    state.liveUnlocked = false;
    sessionStorage.setItem("ariaMode", "synthetic");
    sessionStorage.removeItem("ariaLiveUnlocked");
    updateModeUI();
  });
}

if (btnLiveMode) {
  btnLiveMode.addEventListener("click", () => {
    if (state.mode === "live") return;
    if (authError) authError.hidden = true;
    if (passcodeInput) passcodeInput.value = "";
    if (liveAuthModal) liveAuthModal.hidden = false;
    if (passcodeInput) setTimeout(() => passcodeInput.focus(), 100);
  });
}

if (authForm) {
  authForm.addEventListener("submit", e => {
    e.preventDefault();
    const val = (passcodeInput?.value || "").trim().toLowerCase();
    if (val === "aria2026" || val === "aria") {
      state.liveUnlocked = true;
      state.mode = "live";
      sessionStorage.setItem("ariaLiveUnlocked", "true");
      sessionStorage.setItem("ariaMode", "live");
      if (liveAuthModal) liveAuthModal.hidden = true;
      updateModeUI();
    } else {
      if (authError) authError.hidden = false;
    }
  });
}

if (authCancelBtn && liveAuthModal) {
  authCancelBtn.addEventListener("click", () => {
    liveAuthModal.hidden = true;
  });
}

if (authModalCloseBtn && liveAuthModal) {
  authModalCloseBtn.addEventListener("click", () => {
    liveAuthModal.hidden = true;
  });
}

if (liveAuthModal) {
  liveAuthModal.addEventListener("click", e => {
    if (e.target === liveAuthModal) liveAuthModal.hidden = true;
  });
}

// Initial Mode UI sync
updateModeUI();
renderDocuments();