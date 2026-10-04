// Copy this file to config.local.js and use endpoints from your own Azure deployment.
// Keep credentials and subscription keys out of browser configuration.
window.ARIA_CONFIG = Object.freeze({
  liveEndpoint: "https://<your-apim-name>.azure-api.net/<inspection-route>",
  telemetryEndpoint: "https://<your-apim-name>.azure-api.net/<telemetry-route>",
  mode: "synthetic",
});