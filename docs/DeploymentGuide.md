# Production Deployment Guide — ARIA Platform

This guide provides the authoritative, production-grade instructions for deploying the **AI Regulatory Inspection Accelerator (ARIA)** into an enterprise Azure environment.

Unlike the quick-start browser demo (which runs synthetic data locally), this guide details the full multi-tenant or single-tenant enterprise deployment topology using **Azure Durable Functions, Azure AI Document Intelligence, Azure OpenAI, Azure Cosmos DB, Azure Key Vault, Managed Identity, and Azure API Management (APIM)**.

---

## 1. Production Architecture Overview

The production ARIA deployment adheres to Microsoft’s **Zero-Secrets Security Architecture** and **AI Tokenomics Cost Governance** standards:

```
+---------------------------------------------------------------------------------------------------------+
|                                    ENTERPRISE API GATEWAY / PORTAL                                      |
|                                     Azure API Management (APIM)                                         |
+---------------------------------------------------+-----------------------------------------------------+
                                                    |
                                       HTTPS (Server-Side Key Injection)
                                                    v
+---------------------------------------------------------------------------------------------------------+
|                                  AZURE DURABLE FUNCTIONS ORCHESTRATION                                  |
|                                       func-aria-pipeline (Flex)                                         |
|  +---------------------+   +---------------------+   +---------------------+   +-------------------+  |
|  | Pre-Validation      |-->| Document Extraction |-->| Cross-Doc Reasoning |-->| Policy & Risk     |  |
|  | Activity            |   | Activity            |   | Activity            |   | Activity          |  |
|  +---------------------+   +---------------------+   +---------------------+   +-------------------+  |
+---------+----------------------------+-------------------------+--------------------------+-------------+
          |                            |                         |                          |
          v                            v                         v                          v
+-------------------+      +-----------------------+   +-------------------+      +-------------------+
|  Azure Key Vault  |      | Azure AI Document     |   |  Azure OpenAI     |      | Azure Cosmos DB   |
|  kv-aria-infra    |      | Intelligence          |   |  oai-aria-infra   |      | cosmos-aria-tele  |
|  (Zero Secrets)   |      | (Layout & Extraction) |   | (Mini & Vision)   |      | (Audit & Telem)   |
+-------------------+      +-----------------------+   +-------------------+      +-------------------+
```

---

## 2. Prerequisites & Tools

Before commencing an enterprise deployment, ensure you have the following prerequisites in place:

### Azure Subscription Requirements
* **Active Azure Subscription** with quota for:
  * Azure OpenAI Service (`gpt-4o-mini` / `gpt-4.1-nano` and `gpt-4o` models).
  * Azure AI Document Intelligence (`prebuilt-layout`).
  * Azure Cosmos DB (Serverless or Provisioned SQL API).
* **Required Azure RBAC Roles** for the deploying engineer/pipeline:
  * `Owner` or `Contributor` + `User Access Administrator` on the target Resource Group.
  * `Key Vault Secrets Officer` on the Key Vault resource.

### Workstation / CI/CD Runner Dependencies
* **Azure CLI** (`az`) v2.60.0 or higher.
* **Python 3.10** or **3.11** runtime environment.
* **Azure Functions Core Tools v4** (`func`).
* **Git** and standard archive tools (`zip` / PowerShell `Compress-Archive`).

---

## 3. Production Resource Footprint

An enterprise ARIA deployment provisions the following resource set within a single resource group (e.g. `rg-aria-prod`):

| Service | Resource Name Pattern | SKU / Tier | Purpose |
|---|---|---|---|
| **API Management** | `apim-aria-infra` | Consumption / Standard | Public gateway, CORS policy, rate-limiting, and Function Key injection |
| **Azure Function App** | `func-aria-pipeline` | Flex Consumption / Premium | Python 3.10 Durable Functions orchestrator and activity handlers |
| **Azure OpenAI** | `oai-aria-infra` | Standard (`S0`) | Text extraction (`aria-text-mini`) and multimodal vision fallback (`aria-vision`) |
| **Document Intelligence** | `di-aria-infra` | Standard (`S0`) | Layout, table, and OCR extraction |
| **Key Vault** | `kv-aria-infra` | Standard | Zero-secrets storage for model API keys and service connection strings |
| **Cosmos DB** | `cosmos-aria-telemetry` | Serverless (SQL API) | Immutable token consumption records, risk evaluations, and reviewer overrides |
| **Storage Account** | `stariainfra` | Standard LRS | Raw document uploads, normalized markdown blobs, and Static Web App hosting |
| **Managed Identity** | `id-aria-pipeline` | User-Assigned | Passwordless RBAC authentication between Function App and Azure services |

---

## 4. Step-by-Step Production Deployment Protocol

### Step 1: Resource Group & Identity Provisioning
Create the resource group and user-assigned managed identity:

```bash
az group create --name rg-aria-prod --location eastus2
az identity create --name id-aria-pipeline --resource-group rg-aria-prod
```

### Step 2: Key Vault & Zero-Secrets Wiring
Provision Azure Key Vault and store the Azure OpenAI secret:

```bash
# Provision Key Vault
az keyvault create --name kv-aria-prod --resource-group rg-aria-prod --location eastus2

# Grant deploying identity Secrets Officer role
AZ_USER_ID=$(az ad signed-in-user show --query id -o tsv)
az role assignment create --assignee $AZ_USER_ID --role "Key Vault Secrets Officer" --scope /subscriptions/<sub-id>/resourceGroups/rg-aria-prod/providers/Microsoft.KeyVault/vaults/kv-aria-prod

# Store Azure OpenAI API Key in Key Vault
az keyvault secret set --vault-name kv-aria-prod --name "AZURE-OPENAI-API-KEY" --value "<your-azure-openai-key>"
```

### Step 3: Deploy Azure OpenAI Models
Deploy the primary micro-extraction model (`aria-text-mini`) and multimodal fallback (`aria-vision`):

```bash
# Provision Cognitive Services Account
az cognitiveservices account create --name oai-aria-prod --resource-group rg-aria-prod --location eastus2 --kind OpenAI --sku S0

# Deploy Primary Text Model (aria-text-mini)
az cognitiveservices account deployment create \
  --name oai-aria-prod \
  --resource-group rg-aria-prod \
  --deployment-name aria-text-mini \
  --model-name gpt-4o-mini \
  --model-version "2024-07-18" \
  --model-format OpenAI \
  --sku-name Standard \
  --capacity 50

# Deploy Multimodal Vision Fallback Model (aria-vision)
az cognitiveservices account deployment create \
  --name oai-aria-prod \
  --resource-group rg-aria-prod \
  --deployment-name aria-vision \
  --model-name gpt-4o \
  --model-version "2024-11-20" \
  --model-format OpenAI \
  --sku-name Standard \
  --capacity 20
```

### Step 4: Provision Cosmos DB Telemetry Store
Provision Cosmos DB with Serverless capability, database `aria`, and container `token_telemetry`:

```bash
az cosmosdb create --name cosmos-aria-prod --resource-group rg-aria-prod --locations regionName=eastus2 --capabilities EnableServerless
az cosmosdb sql database create --resource-group rg-aria-prod --account-name cosmos-aria-prod --name aria
az cosmosdb sql container create --resource-group rg-aria-prod --account-name cosmos-aria-prod --database-name aria --name token_telemetry --partition-key-path /caseId
```

### Step 5: Configure Function App AppSettings & Key Vault References
Wire environment settings and Key Vault references into `func-aria-pipeline`:

```bash
# Retrieve Key Vault Secret URI
SECRET_URI=$(az keyvault secret show --vault-name kv-aria-prod --name "AZURE-OPENAI-API-KEY" --query id -o tsv)

# Configure Function App AppSettings
az functionapp config appsettings set --resource-group rg-aria-prod --name func-aria-pipeline --settings \
  "AZURE_OPENAI_ENDPOINT=https://oai-aria-prod.openai.azure.com/" \
  "AZURE_OPENAI_DEPLOYMENT=aria-text-mini" \
  "AZURE_OPENAI_VISION_DEPLOYMENT=aria-vision" \
  "AZURE_OPENAI_API_KEY=@Microsoft.KeyVault(SecretUri=$SECRET_URI/)" \
  "DOCUMENT_INTELLIGENCE_ENDPOINT=https://di-aria-prod.cognitiveservices.azure.com/" \
  "COSMOS_ENDPOINT=https://cosmos-aria-prod.documents.azure.com:443/" \
  "COSMOS_DATABASE=aria" \
  "COSMOS_CONTAINER=token_telemetry" \
  "RAW_UPLOADS_STORAGE_URL=https://stariaprod.blob.core.windows.net/"
```

### Step 6: Deploy Python Function App Artifact
Package and deploy the production Function code:

```bash
# Package function code
python -c "import zipfile, os; src = '.'; zf = zipfile.ZipFile('aria-func.zip', 'w', zipfile.ZIP_DEFLATED); [zf.write(os.path.join(r, f), os.path.relpath(os.path.join(r, f), src)) for r, d, fs in os.walk(src) if not any(x.startswith('.') or x in ('__pycache__', 'venv') for x in r.split(os.sep)) for f in fs if not f.endswith('.zip')]; zf.close()"

# Zip deploy to Azure Function App
az functionapp deployment source config-zip --resource-group rg-aria-prod --name func-aria-pipeline --src aria-func.zip
```

### Step 7: Configure APIM Gateway Routes & CORS Security
Set up APIM proxy operations and inject Function keys server-side:

```powershell
# Set APIM backend base URL
$base = "https://management.azure.com/subscriptions/<sub-id>/resourceGroups/rg-aria-prod/providers/Microsoft.ApiManagement/service/apim-aria-prod"
# Operations: POST /aria-demo/live/inspections & GET /aria-demo/telemetry
```

---

## 5. Verification & Health Audit

Verify production pipeline readiness:

```powershell
# Test Live Inspection Route via APIM
$body = '{ "requestId": "PROD-AUDIT-001", "documents": [{ "documentId": "1", "name": "Invoice.pdf", "type": "Commercial Invoice", "text": "Commodity: Poultry. Net Weight: 12400 kg. Origin: Brazil" }, { "documentId": "2", "name": "Certificate.pdf", "type": "Health Certificate", "text": "Commodity: Poultry. Net Weight: 12400 kg. Origin: Brazil" }] }'
Invoke-WebRequest -Uri "https://apim-aria-prod.azure-api.net/aria-demo/live/inspections" -Method Post -ContentType "application/json" -Body $body

# Verify Cosmos DB Telemetry Persistence
Invoke-WebRequest -Uri "https://apim-aria-prod.azure-api.net/aria-demo/telemetry" -Method Get
```

---

## 6. Enterprise Security & Governance Checklist

- [x] **Zero Plaintext Secrets**: OpenAI keys stored in Key Vault; Function App uses Key Vault References.
- [x] **Managed Identity Authentication**: Internal calls between Function App, Blob Storage, and Cosmos DB use Azure User-Assigned Managed Identity.
- [x] **APIM Inbound Gateway Guardrails**: Client calls pass through APIM with CORS restricted to approved domain origins and server-side key injection.
- [x] **Deterministic Regulatory Decisions**: LLM extractions map to strictly code-evaluated policy rules. Zero hallucinated risk scores.
- [x] **Cosmos DB Telemetry Audit**: Every execution event, prompt token count, and reviewer override is logged immutably.
