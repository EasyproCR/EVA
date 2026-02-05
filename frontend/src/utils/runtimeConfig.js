// Runtime configuration injected at runtime (e.g., via index.html or entrypoint script)
// Expected shape: window.__RUNTIME_CONFIG__ = { API_BASE_URL: "..." }

export function getRuntimeConfig() {
  if (typeof window === "undefined") return {};
  return window.__RUNTIME_CONFIG__ || {};
}

// Backward-compatible helper for older call sites
export function getApiBaseUrl() {
  const runtime = getRuntimeConfig();
  return runtime.API_BASE_URL || "/api";
}
