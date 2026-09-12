// Public, non-secret deployment configuration for the ARIA hackathon demo.
window.ARIA_CONFIG = Object.freeze({
  apiBaseUrl: "https://apim-aria-infra.azure-api.net/inspections",
  functionAppBaseUrl: "https://func-aria-pipeline.azurewebsites.net",
  liveEndpoint: "https://func-aria-pipeline.azurewebsites.net/api/live/inspections",
  apiKey: "",
  mode: "demo",
});