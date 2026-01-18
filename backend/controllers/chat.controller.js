export function createChatController({ chatService, store }) {
    return {
        saludo: (req, res) => {
            res.json({
                saludo: "Hola, soy EVA, tu asistente de inteligencia artificial. ¿En qué puedo ayudarte hoy?",
            });
        },

        chat: async (req, res) => {
            const { id, nombre, mensaje } = req.chatInput;
            try {
                const respuesta = await chatService.chat({ id, nombre, mensaje });
                res.json({ respuesta });
            } catch (error) {
                res.status(500).json({ error: "Error comunicando con OpenAI" });
            }
        },

        eliminarMemoria: (req, res) => {
            const { id } = req.deleteInput;
            store.deleteUser(id);
            res.json({ mensaje: "Memoria eliminada para el usuario con id: " + id });
        },
    };
}
