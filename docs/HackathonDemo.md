---
title: ARIA Hackathon Demo
description: Run the browser demo locally or from the Azure static website
ms.date: 2026-09-12
ms.topic: how-to
---

## Hosted demo

The current Azure-hosted browser demo is:

<https://stariainfra.z13.web.core.windows.net/>

It is a browser-local demonstration. It does not send uploaded sample files to
Azure. The public configuration points at the deployed ARIA APIM gateway for
future backend mode:

* APIM base: `https://apim-aria-infra.azure-api.net`
* Inspection API: `POST https://apim-aria-infra.azure-api.net/inspections`
* Function App: `https://func-aria-pipeline.azurewebsites.net`

No secrets are embedded in the browser demo. APIM subscription/authentication
is required for live backend submissions.

## Local demo

```powershell
python -m http.server 4173 --directory reference-implementations/food-inspection/ui
```

Open <http://localhost:4173/index.html>, load the sample case, and run the
inspection walkthrough.

## Demo path

1. Load the sample evidence bundle.
2. Review the document viewer and extracted evidence.
3. Run the five-stage walkthrough.
4. Review the risk band, recommendation, findings, and decision trace.
5. Open Token analytics for the token/cost view.

The hackathon demo uses deterministic browser-local sample data. Azure backend
integration remains an optional authenticated deployment path.

## Vision strategy

AI vision is not the default path for ordinary printed documents. ARIA uses a
hybrid strategy:

* Python preprocessing and deterministic quality checks run first.
* Azure Document Intelligence handles OCR and layout for printed evidence.
* Template-driven extraction and normalization fill structured fields.
* Vision is reserved for handwritten, mixed-script, low-quality, or ambiguous
	evidence where OCR confidence is insufficient.

This keeps the common path cheaper and more reproducible while preserving a
fallback for evidence that conventional OCR cannot read reliably.
