# ARIA Platform Troubleshooting & Diagnostics Guide

This guide details common deployment, runtime, and API issue resolution procedures for the **AI Regulatory Inspection Accelerator (ARIA)**.

---

## 1. Deployment & Infrastructure Issues

### Issue: Cosmos DB Account Provisioning Failure (`ServiceUnavailable`)
* **Symptom**: `az cosmosdb create` fails with high-demand quota errors in region `eastus`.
* **Resolution**: Deploy the Cosmos DB account in an adjacent region supporting Serverless capability (e.g. `eastus2` or `westus3`):
  ```bash
  az cosmosdb create --name <your-cosmos-account> --resource-group <your-resource-group> --locations regionName=eastus2 --capabilities EnableServerless
  ```

### Issue: APIM Policy Error — `rate-limit-by-key is not allowed in Consumption SKU`
* **Symptom**: Applying standard rate limiting policies fails on APIM Consumption tier.
* **Resolution**: Use IP-based or header-based CORS and backend routing policies compatible with the APIM Consumption tier:
  ```xml
  <policies>
    <inbound>
      <base />
      <set-backend-service backend-id="inspector-live-demo-backend" />
      <cors allow-credentials="false">
        <allowed-origins><origin>https://<your-workbench-origin></origin></allowed-origins>
        <allowed-methods><method>POST</method><method>GET</method><method>OPTIONS</method></allowed-methods>
        <allowed-headers><header>*</header></allowed-headers>
      </cors>
    </inbound>
    <backend><forward-request timeout="230" follow-redirects="false" /></backend>
  </policies>
  ```

---

## 2. Azure Functions Runtime & Orchestration Issues

### Issue: Function Load Error (`Parameter 'request' not recognized`)
* **Symptom**: Function App logs report indexing failures for HTTP triggers on Azure Functions v4 Python worker.
* **Resolution**: In Azure Functions v4 Python worker, HTTP trigger parameters must be named `req: func.HttpRequest` (not `request`).

### Issue: HTTP 500 / Timeout on Multi-Document Live Extractions
* **Symptom**: Processing large multi-document bundles takes longer than the default 120-second APIM gateway timeout.
* **Resolution**: Increase the APIM `<forward-request timeout="230" />` value to allow the Durable Functions orchestrator sufficient time for parallel OCR and extraction.

---

## 3. Extraction & Policy Validation Issues

### Issue: False Cross-Document Mismatches (`CROSS_TITLE` or `CROSS_REFERENCE` FAIL)
* **Symptom**: Cross-document checks fail because unique document references (e.g. Invoice # vs Certificate #) are incorrectly compared against each other.
* **Resolution**: Cross-document comparison must only evaluate shared trade/inspection claims (`commodity`, `net_weight`, `origin`, `consignee`, `importer`, `exporter`, `hs_code`). Document-unique metadata (`invoice_number`, `certificate_number`, `issue_date`) is categorized under `document_metadata` and excluded from equality checks.

---

## 4. Security & Authentication Issues

### Issue: Live Azure is unavailable in the Workbench
* **Symptom**: The **Set up Azure** control is disabled and document upload is unavailable.
* **Resolution**: Confirm that `config.js` contains the current public APIM routes. For another deployment, copy `reference-implementations/food-inspection/ui/config.local.example.js` to `reference-implementations/food-inspection/ui/config.local.js`, configure its APIM routes, and open the workbench with `?config=local`. Do not place Function keys, client secrets, subscription keys, or access tokens in browser code.

---

## 5. Getting Further Support

* Review open or closed issues in the [GitHub Repository](https://github.com/microsoft/ai-regulatory-inspection-accelerator/issues).
* See the [Technical Architecture Guide](architecture/TechnicalArchitecture.md) for full component specifications.
