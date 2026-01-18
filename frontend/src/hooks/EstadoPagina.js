import ChatService from "../services/ChatService";
const chatService = new ChatService();

const isReloading = async () => {
    return await chatService.eliminarMemoria();
}
export { isReloading };