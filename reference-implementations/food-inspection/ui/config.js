// Public, non-secret deployment configuration for the ARIA hackathon demo.
window.ARIA_CONFIG = Object.freeze({
  apiBaseUrl: "https://apim-aria-infra.azure-api.net/inspections",
  functionAppBaseUrl: "https://func-aria-pipeline.azurewebsites.net",
  liveEndpoint: "https://apim-aria-infra.azure-api.net/aria-demo/live/inspections",
  telemetryEndpoint: "https://apim-aria-infra.azure-api.net/aria-demo/telemetry",
  apiKey: "",
  mode: "live",
});