import ValidationUser from "../validation/ValidationUser.js";
export class ChatService {
    constructor({ openai, prompt, store, model, maxTokens }) {
        this.openai = openai;
        this.prompt = prompt;
        this.store = store;
        this.model = model;
        this.maxTokens = maxTokens;
        this.validationUser = new ValidationUser();
    }

    async chat({ id, nombre, mensaje }) {
        // Best-effort cleanup to avoid unbounded user map growth.
        this.store.cleanupExpired();
        this.validationUser.determinarDepartamento(id);
        this.store.appendUserMessage(id, mensaje);

        const messages = [
            {
                role: "system",
                content: `${this.prompt.getInitialPrompt()}\n\nEl nombre del usuario es: ${nombre}.`,
            },
            ...this.store.getMessages(id).map(m => ({
                role: m.role,
                content: m.content,
            })),
        ];

        const completion = await this.openai.chat.completions.create({
            model: this.model,
            messages,
            tools,
            toolchoice: "auto",
            max_tokens: this.maxTokens,
        });

        const respuestaBot = completion?.choices?.[0]?.message?.content ?? "";
        this.store.appendAssistantMessage(id, respuestaBot);
        return respuestaBot;
    }

    async  consultasPropiedades(args) {
        // Implementación de la función para buscar propiedades 
    }

    async consultasIntranet(args) {
        
    }





}
