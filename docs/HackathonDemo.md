---
title: ARIA Demo & Walkthrough Guide
description: Quick-start guide for evaluating the ARIA demo hosted on Azure
ms.date: 2026-09-13
ms.topic: how-to
---

# ARIA Demo & Walkthrough Guide

The **AI Regulatory Inspection Accelerator (ARIA)** includes a hosted, interactive **Inspection Workbench** and **Token Analytics Dashboard** designed for rapid evaluation.

> **Note on demo vs. production**: This guide covers the hosted ARIA demo. For enterprise production deployment instructions with Terraform, Key Vault references, and zero-secrets RBAC, see the [Enterprise Production Deployment Guide](DeploymentGuide.md).

---

## Live Hosted Demo Endpoints

* 🌐 **ARIA Inspection Workbench**: <https://stariainfra.z13.web.core.windows.net/index.html>
* 📊 **ARIA Token Analytics**: <https://stariainfra.z13.web.core.windows.net/tokens.html>

---

## Core Demo Features

### 1. Public Synthetic Mode
* **Synthetic Mode (Default)**: Executes locally in the browser with zero token cost or Azure resource consumption. Ideal for public walkthroughs and offline testing.
* **Live Azure Mode (`🔒 Live Azure`)**: Reserved for authorized deployment maintainers. It calls the shared Azure Function, Document Intelligence, Azure OpenAI, and Cosmos DB resources and is not part of the public test path.

### 2. Cross-Industry Sample Scenarios
Choose from 5 pre-configured multi-document inspection scenarios:
1. **Food Safety (English)**: Commercial Invoice, Health Certificate, Halal Certificate.
2. **Food Safety (Arabic / RTL)**: فاتورة تجارية, شهادة صحية, شهادة حلال.
3. **Customs Clearance**: Bill of Lading, Customs Declaration, Certificate of Origin.
4. **KYC Onboarding**: Identity Document, Beneficial Ownership Record, Proof of Address.
5. **Insurance Claim**: Claim Form, Adjuster Report, Repair Invoice.

### 3. Custom File Upload & Reset Workflow
* Drag and drop or select your own custom `.pdf`, `.png`, or `.jpg` evidence bundles.
* Once processing completes, click **`↺ Clear Case for New Inspection`** to reset the workbench state for the next case.

### 4. Platform Architecture & Differentiators Modal
Click **`⚡ Platform Architecture`** in the header to view ARIA's 4 Enterprise Pillars:
* **Probabilistic Extraction vs. 100% Deterministic Code Rules**
* **AI Tokenomics Cost Governance** ($0.15/1M vs $2.50/1M)
* **N-Way Cross-Document Integrity Engine**
* **Immutable Audit Trail & Human Control**

### 5. Token Analytics & Cost Governance Dashboard (`tokens.html`)
* **Live Telemetry Connection**: Real-time token consumption logs fetched directly from Azure Cosmos DB.
* **6 KPI Metrics Cards**: Total Tokens, Avg Tokens/Case, Realized Cost, 30-Day Forecast, Net Money Saved vs. Naive GPT-4o, Cache Hit Rate.
* **ARIA Efficiency Proof Banner**: Highlights ~80.1% cost reduction achieved via micro-model tier routing and prompt prefix caching.
* **Pipeline Activity vs. Model Intensity Heatmap**: Matrix mapping stages to model consumption.
* **Per-Case Traceable Table**: Paged table (10 per page) with popup modal for per-case stage breakdowns.
* **Expandable Floating Insight Tabs**: Bottom toolbar with expandable overlays for Prompt Caching, Accuracy Governance, React Production Roadmap, and Token Saving Strategies.

---

## Running the Demo Locally

```powershell
python -m http.server 4173 --directory reference-implementations/food-inspection/ui
```

Open <http://localhost:4173/index.html> in your browser.
