# ARIA — 2-Minute Demo Video Script

**Document:** 22-ARIA-Demo-Script.md
**Total Runtime:** 2:00
**Format:** Recordable screen-capture demo with voiceover narration

---

## Demo Flow Overview

1. Fragmented documents (0:00–0:12)
2. Ingest the bundle (0:12–0:22)
3. Document intelligence extraction (0:22–0:38)
4. Cross-document validation (0:38–0:54)
5. Policy and risk evaluation (0:54–1:10)
6. Explainable recommendation (1:10–1:22)
7. Human reviewer decision (1:22–1:38)
8. Audit trail / evidence lineage (1:38–1:50)
9. Closing — reusable platform, PAFN as reference implementation (1:50–2:00)

---

## Script

### [0:00–0:12] Fragmented Regulatory Documents

**Visual:** Screen shows five separate document thumbnails scattered on a desk-style layout — invoice, health certificate, Halal certificate, certificate of origin, packing list. Two are in Arabic, three in English.

**Narration:**
> "Every regulatory decision starts like this: a scattered bundle of documents, different languages, different formats — and somebody has to make sense of all of it, fast."

---

### [0:12–0:22] Upload / Ingest the Documents

**Visual:** Screen transitions to the ARIA submission interface (or API call in a terminal/Postman). Documents drag-and-drop or POST into the submission endpoint. A confirmation appears: `202 Accepted — Case #ARIA-2026-00417`.

**Narration:**
> "We submit the full bundle to ARIA in a single request. Instantly, the case is accepted and validated — no waiting, no manual sorting."

---

### [0:22–0:38] Document Intelligence Extraction

**Visual:** Split-screen or animated pipeline view showing each document being processed — field values populating in a structured table in near real time (invoice number, net weight, country of origin, certificate expiry, etc.). A small badge shows "Extracted in optimized mode" or a token-savings indicator.

**Narration:**
> "ARIA extracts structured data from every document — combining fast, low-cost structured extraction with AI reasoning only where it's genuinely needed. No raw documents are ever dumped wholesale into a model; every call is deliberately minimized."

---

### [0:38–0:54] Cross-Document Validation

**Visual:** Animated diagram or UI panel showing two documents side by side with a highlighted field — e.g., "Net Weight: 450kg" on the invoice versus "Net Weight: 520kg" on the packing list — with a red conflict flag appearing between them.

**Narration:**
> "Here's where ARIA goes beyond extraction. It reconciles facts across every document simultaneously — and catches this: the invoice and the packing list disagree on net weight. A single-document tool would never see this. ARIA catches it automatically."

---

### [0:54–1:10] Policy and Risk Evaluation

**Visual:** Screen shows a rules panel or findings list — rule checks scrolling with PASS/FAIL indicators (e.g., "Mandatory Certificate Check: PASS," "Cross-Document Weight Match: FAIL," "Certificate Validity Window: PASS"). A risk score gauge animates upward (e.g., to 72/100, HIGH).

**Narration:**
> "Every applicable policy rule is evaluated — deterministically, against rules that can be updated anytime without touching a line of code. The conflict we just found drives the risk score up, and this case is automatically flagged for review."

---

### [1:10–1:22] Explainable Recommendation

**Visual:** Screen shows the decision summary card: verdict "HOLD — Review Required," confidence score, and a short plain-language explanation: "Net weight discrepancy of 70kg detected between Invoice and Packing List; certificate expiry within valid range."

**Narration:**
> "ARIA doesn't just say hold — it tells you exactly why, in plain language, tied directly to the evidence."

---

### [1:22–1:38] Human Reviewer Decision

**Visual:** Reviewer chat/agent interface. A reviewer types: "Why was this flagged?" The agent responds with a cited answer referencing the specific document, page, and field. Reviewer then clicks "Confirm Hold" or "Override" and enters a rationale in a text box.

**Narration:**
> "A human reviewer stays in control. Our review agent answers only from the actual case evidence — with citations — and every decision or override is captured with a reason, before it's final."

---

### [1:38–1:50] Audit Trail / Evidence Lineage

**Visual:** Screen shows an evidence chain visualization or exported JSON/report snippet: Field → Source Document → Rule Applied → Finding → Final Decision, with a timestamp and rule version tag.

**Narration:**
> "Every decision carries a complete, field-level evidence trail — pinned to the exact rule version that produced it. Months later, this decision can be reconstructed and defended, exactly as it happened."

---

### [1:50–2:00] Closing — Reusable Platform, PAFN as Reference Implementation

**Visual:** Screen zooms out to show a simple diagram: "ARIA — AI Regulatory Inspection Accelerator" at the center, with branches labeled "Food Safety (PAFN — first reference implementation)," "Customs," "Healthcare," "Financial Compliance," "KYC/AML." Fade to ARIA logo/title card.

**Narration:**
> "This isn't a food safety tool — it's a reusable platform. The food safety authority you just watched is ARIA's first reference implementation. The same engine, reconfigured, works for customs, healthcare, financial compliance, and beyond. This is ARIA: from fragmented evidence to a decision you can defend."

---

## Production Notes

- Keep on-screen text large and readable at a glance; judges may watch on a laptop or a shared screen at speed.
- Use a consistent accent color (see 23-ARIA-Hackathon-Poster.md palette) across all UI overlays for brand consistency.
- If a live system is not fully available for recording, screen mockups or a scripted walkthrough of a working prototype segment are acceptable — prioritize narrative clarity over UI polish.
- Do not include architecture diagrams, ADR references, or Azure service names in this video — save those for the pitch deck and one-pager.

---

*ARIA — AI Regulatory Inspection Accelerator*
*Microsoft Global Hackathon 2026 — 2-Minute Demo Script*
