# Local Development & Testing Workflow Guide

This guide details the setup for developing, running, and testing the **AI Regulatory Inspection Accelerator (ARIA)** platform locally.

---

## 1. Local Environment Requirements

* **Python 3.10** or **3.11**
* **Azure Functions Core Tools v4** (`func`)
* **Git**
* **Node.js 18+** (for previewing local static web assets)

---

## 2. Python Virtual Environment Setup

Create and activate a Python virtual environment, then install dependencies:

```bash
# Navigate to repository root
cd dstoolkit-document-inspection-agent

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Upgrade pip & install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Local Test Suite & Linting

Run automated unit tests and linter checks locally:

```bash
# Run all unit tests
pytest -v

# Run specific test modules
pytest tests/test_token_efficiency.py -v
pytest tests/test_review_service.py -v
pytest tests/test_audit_service.py -v
pytest tests/test_risk_assessment.py -v
pytest tests/test_cross_document.py -v

# Run Ruff linter
ruff check .
```

---

## 4. Local Azure Functions Execution

1. Create a `local.settings.json` file in the project root:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AZURE_OPENAI_ENDPOINT": "https://oai-aria-infra.openai.azure.com/",
    "AZURE_OPENAI_DEPLOYMENT": "aria-text-mini",
    "AZURE_OPENAI_VISION_DEPLOYMENT": "aria-vision",
    "AZURE_OPENAI_API_KEY": "<your-dev-key>",
    "DOCUMENT_INTELLIGENCE_ENDPOINT": "https://di-aria-infra.cognitiveservices.azure.com/",
    "COSMOS_ENDPOINT": "https://cosmos-aria-telemetry.documents.azure.com:443/",
    "COSMOS_KEY": "<your-cosmos-key>",
    "COSMOS_DATABASE": "aria",
    "COSMOS_CONTAINER": "token_telemetry"
  }
}
```

2. Start the local Azure Functions runtime:

```bash
func start
```

---

## 5. Local Workbench UI Preview

To serve and test the static Workbench UI locally:

```bash
python -m http.server 4173 --directory reference-implementations/food-inspection/ui
```

Open `http://localhost:4173/index.html` in your browser. You can toggle between **Synthetic Mode** (local browser mock) and **Live Mode** (pointing at your local or dev Azure Functions endpoints).
