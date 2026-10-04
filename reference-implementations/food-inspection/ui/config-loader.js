const loaderScript = document.currentScript;
const applicationScript = loaderScript?.dataset.application;
const query = new URLSearchParams(window.location.search);
const useLocalConfiguration = query.get("config") === "local";

async function loadOptionalConfiguration() {
  if (!useLocalConfiguration) return;

  try {
    await new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "config.local.js";
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  } catch (error) {
    console.warn("Local UI configuration could not be loaded:", error);
  }
}

async function startApplication() {
  await loadOptionalConfiguration();
  if (!applicationScript) throw new Error("Application script is not configured");

  if (useLocalConfiguration) {
    document.querySelectorAll('a[href="index.html"], a[href="tokens.html"]').forEach(link => {
      link.search = "?config=local";
    });
  }

  const script = document.createElement("script");
  script.src = applicationScript;
  document.body.appendChild(script);
}

startApplication();
