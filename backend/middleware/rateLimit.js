import rateLimit, { ipKeyGenerator } from "express-rate-limit";

function createJsonRateLimit({ windowMs, limit }) {
    return rateLimit({
        windowMs,
        limit,
        standardHeaders: true,
        legacyHeaders: false,
        message: { error: "Demasiadas solicitudes, intenta de nuevo más tarde." },
    });
}

export function createChatLimiter({ windowMs, limit }) {
    // Key by user id if provided; fallback to IP.
    return rateLimit({
        windowMs,
        limit,
        standardHeaders: true,
        legacyHeaders: false,
        keyGenerator: (req, res) => {
            const bodyId = typeof req.body?.id === "string" ? req.body.id.trim() : "";
            return bodyId ? `user:${bodyId}` : ipKeyGenerator(req, res);
        },
        message: { error: "Demasiadas solicitudes al chat. Intenta de nuevo más tarde." },
    });
}

export function createDeleteLimiter({ windowMs, limit }) {
    return createJsonRateLimit({ windowMs, limit });
}
