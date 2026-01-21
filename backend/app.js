import Prompt from "./data/Prompt.js";
import express from "express";
import dotenv from "dotenv";

import { getEnv } from "./config/env.js";
import { createCorsMiddleware } from "./middleware/cors.js";
import { createChatLimiter, createDeleteLimiter } from "./middleware/rateLimit.js";
import { bodyParserErrorHandler } from "./middleware/errorHandler.js";

import { ConversationStore } from "./stores/conversationStore.js";
import { createOpenAIClient } from "./services/openaiClient.js";
import { ChatService } from "./services/chatService.js";
import { createChatController } from "./controllers/chat.controller.js";
import { createChatRouter } from "./routes/chat.routes.js";

dotenv.config();

const env = getEnv();

const app = express();
app.set("trust proxy", env.trustProxy);

app.use(createCorsMiddleware({ origins: env.corsOrigins }));
app.use(express.json({ limit: env.maxBodySize }));

const openai = createOpenAIClient({ apiKey: env.openaiApiKey});
const prompt = new Prompt();
const store = new ConversationStore({
    maxTurns: env.maxTurns,
    ttlMs: env.ttlMs,
    maxActiveUsers: env.maxActiveUsers,
});

const chatService = new ChatService({
    openai,
    prompt,
    store,
    model: env.openaiModel,
    maxTokens: env.openaiMaxTokens,
});

const controller = createChatController({ chatService, store });
const chatLimiter = createChatLimiter({ windowMs: env.chatRateLimitWindowMs, limit: env.chatRateLimitMax });
const deleteLimiter = createDeleteLimiter({
    windowMs: env.deleteRateLimitWindowMs,
    limit: env.deleteRateLimitMax,
});

app.use(createChatRouter({ controller, chatLimiter, deleteLimiter }));
app.use( '/api',createChatRouter({ controller, chatLimiter, deleteLimiter }));

// Manejo de errores del body parser (por ejemplo, JSON inválido o demasiado grande)
app.use(bodyParserErrorHandler({ maxBodySize: env.maxBodySize }));

app.listen(env.port, () => {
    console.log(`Server is running on port ${env.port}`);
});