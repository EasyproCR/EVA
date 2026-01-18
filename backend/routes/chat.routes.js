import { Router } from "express";
import { validateChatRequest, validateDeleteRequest } from "../middleware/validators.js";

export function createChatRouter({ controller, chatLimiter, deleteLimiter }) {
    const router = Router();

    router.get("/saludo", controller.saludo);
    router.post("/chat", chatLimiter, validateChatRequest, controller.chat);
    router.post("/eliminarMemoria", deleteLimiter, validateDeleteRequest, controller.eliminarMemoria);

    return router;
}
