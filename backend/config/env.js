function parseNumber(value, fallback) {
    const numberValue = Number(value);
    return Number.isFinite(numberValue) ? numberValue : fallback;
}

function parseString(value, fallback) {
    return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function parseCsv(value) {
    if (typeof value !== "string") return [];
    return value
        .split(",")
        .map(v => v.trim())
        .filter(Boolean);
}

export function getEnv() {
    return {
        port: parseNumber(process.env.PORT, 3000),
        maxBodySize: parseString(process.env.MAX_BODY_SIZE, "20kb"),
        openaiApiKey: process.env.OPENAI_API_KEY,
        openaiModel: parseString(process.env.OPENAI_MODEL, "gpt-4.1-mini-2025-04-14"),
        openaiMaxTokens: parseNumber(process.env.OPENAI_MAX_TOKENS, 600),
        trustProxy: parseNumber(process.env.TRUST_PROXY, 1),
        corsOrigins: parseCsv(process.env.CORS_ORIGINS),
        chatRateLimitWindowMs: parseNumber(process.env.CHAT_RATE_LIMIT_WINDOW_MS, 60_000),
        chatRateLimitMax: parseNumber(process.env.CHAT_RATE_LIMIT_MAX, 20),
        deleteRateLimitWindowMs: parseNumber(process.env.DELETE_RATE_LIMIT_WINDOW_MS, 60_000),
        deleteRateLimitMax: parseNumber(process.env.DELETE_RATE_LIMIT_MAX, 60),
        maxTurns: parseNumber(process.env.MAX_TURNS, 20),
        ttlMs: parseNumber(process.env.TTL_MS, 60 * 60_000),
        maxActiveUsers: parseNumber(process.env.MAX_ACTIVE_USERS, 2_000),
    };
}
