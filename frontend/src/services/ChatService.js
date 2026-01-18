import EasyProService from "./EasyProService";

const BASE_URL = import.meta.env.VITE_API_BASE_URL;
class ChatService {
    constructor() {
        this.easyProService = new EasyProService();
    }

    getUserData() {
        return this.easyProService.getUserData();
    }

    async comunicacion(mensaje){
        
        const comunicacion= await fetch(`${BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                id: this.getUserData().id, 
                nombre: this.getUserData().nombre, 
                mensaje: mensaje,
            }),
        })
        const data = await comunicacion.json();
        return data.respuesta;
    }

    async getPrimerMensaje(){
        const bienvenida =  await fetch(`${BASE_URL}/saludo`);
        const data = await bienvenida.json();
        return data.saludo  ;
        
    }


    async eliminarMemoria(){
        const eliminar =  await fetch(`${BASE_URL}/eliminarMemoria`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                id: this.getUserData().id, 
            }),
        });
        const data = await eliminar.json();
        return data.mensaje;
    }

}

export default ChatService;