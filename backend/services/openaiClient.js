import OpenAI from "openai";

export function createOpenAIClient({ apiKey }) {
    if (!apiKey) {
        // Keep server running (useful for local dev), but warn loudly.
        console.warn("OPENAI_API_KEY no está configurada. /chat fallará.");
    }
    return new OpenAI({ apiKey });
}
