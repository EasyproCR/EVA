import EasyProService from "./EasyProService";

const BASE_URL = import.meta.env.VITE_API_BASE_URL;
class ChatService {
    id = null;
    nombre = "";

    constructor() {
        this.easyProService = new EasyProService();
        this.ready = this.initializeUser();
    }


    async initializeUser() {
        const user = await this.easyProService.getUserData();
        this.id = user.id;
        this.nombre = user.nombre;
    }

    async ensureReady() {
        await this.ready;
        if (!this.id || !this.nombre) {
            // If user data didn't populate for any reason, try once more.
            this.ready = this.initializeUser();
            await this.ready;
        }
        if (this.id === null || this.id === undefined || this.id === "") {
            throw new Error("No user id available (EasyPro /api/user)");
        }
        if (this.nombre === null || this.nombre === undefined || this.nombre === "") {
            throw new Error("No user nombre available (EasyPro /api/user)");
        }
    }

    async comunicacion(mensaje) {
        await this.ensureReady();

        if (!BASE_URL) {
            throw new Error("Missing env var: VITE_API_BASE_URL");
        }

        const token = localStorage.getItem('chat_token');
        const headers = {
            'Content-Type': 'application/json',
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const comunicacion = await fetch(`${BASE_URL}/chat`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                // id and nombre are now extracted from token in backend, 
                // but we keep sending them for now if backend expects something,
                // though backend validation only checks 'mensaje'.
                // Ideally we can stop sending them, but to be safe and consistent with previous code:
                // id: this.id,
                // nombre: this.nombre, 
                // Wait, backend logic changed to use req.user.id. 
                // So the body id/nombre are ignored.
                mensaje: mensaje,
            }),
        });

        if (!comunicacion.ok) {
            const errorText = await comunicacion.text().catch(() => "");
            throw new Error(`Backend /chat failed: ${comunicacion.status} ${comunicacion.statusText}${errorText ? ` - ${errorText}` : ""}`);
        }

        const data = await comunicacion.json();
        return data.respuesta;
    }

    async getPrimerMensaje() {
        const bienvenida = await fetch(`${BASE_URL}/saludo`);
        const data = await bienvenida.json();
        return data.saludo;

    }


    async eliminarMemoria() {
        await this.ensureReady();
        if (!BASE_URL) {
            throw new Error("Missing env var: VITE_API_BASE_URL");
        }

        const token = localStorage.getItem('chat_token');
        const headers = {
            'Content-Type': 'application/json',
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const eliminar = await fetch(`${BASE_URL}/eliminarMemoria`, {
            method: 'DELETE',
            headers: headers,
            body: JSON.stringify({
                // id: this.id, // Not needed, backend uses token
            }),
        });

        if (!eliminar.ok) {
            const errorText = await eliminar.text().catch(() => "");
            throw new Error(`Backend /eliminarMemoria failed: ${eliminar.status} ${eliminar.statusText}${errorText ? ` - ${errorText}` : ""}`);
        }
        const data = await eliminar.json();
        console.log(data);
        return data.mensaje;
    }

}

export default ChatService;