const state = { documents: [], selectedId: null, zoom: 1, processing: false };

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
  confidenceValue: document.querySelector("#confidenceValue"), confidenceBar: document.querySelector("#confidenceBar"),
  findingCount: document.querySelector("#findingCount"), findingsList: document.querySelector("#findingsList"),
  traceList: document.querySelector("#traceList"),
};

const sampleDocs = [
  { name: "Commercial_Invoice.pdf", type: "Commercial Invoice", size: 482000, sample: "invoice" },
  { name: "Health_Certificate.pdf", type: "Health Certificate", size: 735000, sample: "health" },
  { name: "Halal_Certificate.pdf", type: "Halal Certificate", size: 364000, sample: "halal" },
];

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
  renderDocuments(); renderViewer();
}

function loadSample() {
  reset(false);
  state.documents = sampleDocs.map(doc => ({ ...doc, id: id() }));
  state.selectedId = state.documents[0].id;
  els.caseId.textContent = "Case DEMO-2408";
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
  const values = {
    invoice: ["COMMERCIAL INVOICE", "INV-2026-1842", "Frozen poultry products", "12,400 kg", "Brazil", "BR-2048-77"],
    health: ["HEALTH CERTIFICATE", "HC-BR-88219", "Frozen poultry products", "12,400 kg", "Brazil", "2026-11-30"],
    halal: ["HALAL CERTIFICATE", "HAL-77218", "Frozen poultry products", "12,150 kg", "Brazil", "2026-10-18"],
  }[doc.sample];
  return `<article class="sample-document"><div class="doc-top"><div><h3>${values[0]}</h3><p>Official shipment evidence</p></div><span class="seal">VERIFIED</span></div>
    <p>This certificate confirms the details of the regulated shipment described below.</p><table>
    <tr><td>Reference</td><td><strong>${values[1]}</strong></td></tr><tr><td>Commodity</td><td>${values[2]}</td></tr>
    <tr><td>Declared net weight</td><td>${values[3]}</td></tr><tr><td>Country of origin</td><td>${values[4]}</td></tr>
    <tr><td>Certificate / validity</td><td>${values[5]}</td></tr></table><span class="document-stamp">AUTHORIZED COPY</span></article>`;
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
  showDecision();
  state.processing = false; renderDocuments(); els.caseStatus.textContent = "Review ready";
  await delay(300); els.processingStrip.hidden = true;
}

function showDecision() {
  const hasHalal = state.documents.some(doc => /halal/i.test(doc.name));
  const isSample = state.documents.some(doc => doc.sample);
  const hold = isSample || !hasHalal;
  const findings = hold ? [
    { title: "Weight discrepancy", detail: "Halal certificate states 12,150 kg; invoice and health certificate state 12,400 kg." },
    { title: "Certificate authority verified", detail: "Issuer appears in the approved authority reference list.", pass: true },
    { title: "Dates remain valid", detail: "All certificate expiry dates extend beyond the inspection date.", pass: true },
  ] : [
    { title: "Document bundle complete", detail: "Required evidence types are present and readable.", pass: true },
    { title: "No cross-document conflicts", detail: "Key shipment facts are consistent across submitted evidence.", pass: true },
  ];
  els.decisionEmpty.hidden = true; els.decisionContent.hidden = false;
  els.recommendationHeading.textContent = "Inspection complete";
  els.riskBadge.textContent = hold ? "MEDIUM" : "LOW"; els.riskBadge.className = `risk-badge ${hold ? "medium" : "low"}`;
  els.verdictText.textContent = hold ? "Hold for review" : "Recommend release"; els.verdictIcon.textContent = hold ? "!" : "✓";
  els.verdictSummary.textContent = hold ? "A material weight mismatch requires inspector confirmation before release." : "Submitted evidence is complete and consistent with configured policy rules.";
  const confidence = hold ? 87 : 94; els.confidenceValue.textContent = `${confidence}%`; els.confidenceBar.style.width = `${confidence}%`;
  els.findingCount.textContent = findings.length;
  els.findingsList.innerHTML = findings.map(item => `<article class="finding${item.pass ? " pass" : ""}"><strong>${item.pass ? "✓ " : "! "}${item.title}</strong><p>${item.detail}</p></article>`).join("");
  els.traceList.innerHTML = ["Bundle accepted", `${state.documents.length} documents extracted`, "Shipment facts reconciled", "47 policy rules evaluated", "Human review threshold applied"].map(item => `<li>${item}</li>`).join("");
}

function reset(clearFiles = true) {
  if (clearFiles) state.documents.forEach(doc => doc.url && URL.revokeObjectURL(doc.url));
  state.documents = []; state.selectedId = null; state.zoom = 1; state.processing = false;
  els.caseId.textContent = "Case —"; els.caseStatus.textContent = "Ready"; els.processingStrip.hidden = true;
  els.decisionEmpty.hidden = false; els.decisionContent.hidden = true; els.recommendationHeading.textContent = "Awaiting evidence";
  els.riskBadge.textContent = "—"; els.riskBadge.className = "risk-badge neutral";
  renderDocuments(); renderViewer();
}

els.fileInput.addEventListener("change", event => addFiles(event.target.files));
els.dropZone.addEventListener("dragover", event => { event.preventDefault(); els.dropZone.classList.add("dragging"); });
els.dropZone.addEventListener("dragleave", () => els.dropZone.classList.remove("dragging"));
els.dropZone.addEventListener("drop", event => { event.preventDefault(); els.dropZone.classList.remove("dragging"); addFiles(event.dataTransfer.files); });
els.sampleButton.addEventListener("click", loadSample); els.analyzeButton.addEventListener("click", analyze); els.resetButton.addEventListener("click", () => reset());
els.zoomIn.addEventListener("click", () => { state.zoom = Math.min(1.5, state.zoom + 0.1); renderViewer(); });
els.zoomOut.addEventListener("click", () => { state.zoom = Math.max(0.7, state.zoom - 0.1); renderViewer(); });
renderDocuments();