import {useEffect,useState } from 'react'
import ChatService from '../services/ChatService';
import { Bot, Send } from "lucide-react";
import { isReloading } from '../hooks/EstadoPagina';
import LoadingDots from './LoadingDots';
import AudioPlayer from './audioEffect/AudioPlayer';
import Pop from "../../src/assets/Audio/Pop.wav";
<<<<<<< Updated upstream

=======
import Robot from "./Robot";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
>>>>>>> Stashed changes

const chatService = new ChatService();
const nav = performance.getEntriesByType?.("navigation")?.[0];

const initialConversation = [];


const comunication = async (mensaje) => {
    return await chatService.comunicacion(mensaje);
};

function ChatMenu() {
    
    useEffect(() => {
    chatService.getPrimerMensaje().then((mensaje) => {
        setConversation([{
            id: Date.now().toString(),
            text: mensaje,
            sender: "bot",
            timestamp: new Date(),
        }]);
    });
    }, []);

    useEffect(() => {
        chatService.ensureReady();
    }, []);



    const [conversation, setConversation] = useState(initialConversation)
    const [input, setInput] = useState("")
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        if (nav && typeof nav.type === "string" && nav.type === "reload") {
            isReloading();
        }
    }, []);

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (input.trim()) {
            const userMessage = {
                id: Date.now().toString(),
                text: input,
                sender: "user",
                timestamp: new Date(),
            };
            setConversation(prev => [...prev, userMessage]);
            setInput("");

            // Mostrar mensaje de cargando
            setLoading(true);
            setConversation(prev => [...prev, {
                id: (Date.now() + 1).toString(),
                text: <LoadingDots />,
                sender: "bot",
                timestamp: new Date(),
                loading: true
            }]);

            try {
                const respuesta = await comunication(input);
                setConversation(prev => {
                    AudioPlayer(Pop);
                    // Elimina el mensaje de cargando
                    const sinLoading = prev.filter(m => !m.loading);
                    return [...sinLoading, {
                        id: (Date.now() + 1).toString(),
                        text: respuesta,
                        sender: "bot",
                        timestamp: new Date()
                    }];
                });
            } catch (error) {
                setConversation(prev => {
                    AudioPlayer(Pop);
                    const sinLoading = prev.filter(m => !m.loading);
                    return [...sinLoading, {
                        id: (Date.now() + 1).toString(),
                        text: "Hubo un error al comunicarse con el asistente.",
                        sender: "bot",
                        timestamp: new Date()
                    }];
                });
            }
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-background flex flex-col">
            <header className="bg-accent border-b border-border fixed top-0 left-0 w-full z-20">
                <div className="px-4 sm:px-6 lg:px-8 py-6">
                    <div className="flex items-center gap-3 justify-center">
                        <div className="h-10 w-10 rounded-lg bg-primary flex items-center justify-center">
                            <Bot size={40} />
                        </div>
                        <div>
                            <h1 className="text-3xl font-bold text-accent-foreground">EVA</h1>
                            <p className="text-sm text-accent-foreground/70">Asistente Virtual con IA</p>
                        </div>
                    </div>
                </div>
            </header>

            <div className="flex-1 flex flex-col bg-card relative pt-24">
                {/* Mensajes con scroll */}
                <div className="flex-1 overflow-y-auto p-8 space-y-6 max-w-5xl w-full mx-auto pb-32">
                    {conversation.map((message) => (
                        <div
                            key={message.id}
                            className={`flex gap-5 ${message.sender === "user" ? "flex-row-reverse" : "flex-row"}`}
                        >
                            {message.sender === "bot" && (
                                <div className="h-14 w-14 rounded-full bg-primary flex items-center justify-center text-primary-foreground shrink-0">
                                    <Bot size={40} />
                                </div>
                            )}
                            <div
                                className={`max-w-[75%] rounded-2xl px-8 py-5 ${message.sender === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-card-foreground"
                                    }`}
                            >
                                <div className="text-xl leading-relaxed">
                                    {typeof message.text === "string" ? (
                                        <div className="markdown-body">
                                            <Markdown
                                                remarkPlugins={[remarkGfm]}
                                                skipHtml={true}
                                                
                                                components={{
                                                    p: ({ children }) => <p className="whitespace-pre-wrap">{children}</p>,
                                                    strong: ({ children }) => <strong className="font-bold">{children}</strong>,
                                                    a: ({ children, ...props }) => (
                                                        <a {...props} rel="noreferrer" className="underline">
                                                            {children}
                                                        </a>
                                                    ),
                                                    ul: ({ children }) => <ul className="list-disc pl-6">{children}</ul>,
                                                    ol: ({ children }) => <ol className="list-decimal pl-6">{children}</ol>,
                                                    code: ({ children }) => (
                                                        <code className="font-mono text-base whitespace-pre-wrap">{children}</code>
                                                    ),
                                                    pre: ({ children }) => (
                                                        <pre className="overflow-x-auto whitespace-pre-wrap">{children}</pre>
                                                    ),
                                                }}
                                            >
                                                {message.text}
                                            </Markdown>
                                        </div>
                                    ) : (
                                        message.text
                                    )}
                                </div>
                                <span
                                    className={`text-base mt-2 block ${message.sender === "user" ? "text-primary-foreground/70" : "text-muted-foreground"
                                        }`}
                                >
                                    {message.timestamp.toLocaleTimeString("es-ES", {
                                        hour: "2-digit",
                                        minute: "2-digit",
                                    })}
                                </span>
                            </div>
                            {message.sender === "user" && (
                                <div className="h-14 w-14 rounded-full bg-secondary flex items-center justify-center text-secondary-foreground font-bold text-lg shrink-0">
                                    TÚ
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                
                <form onSubmit={handleSubmit} className="p-4 border-t border-border bg-card w-full fixed bottom-0 left-0 z-10">
                    <div className="flex gap-2 max-w-5xl mx-auto">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            disabled={loading}
                            placeholder="Escribe un mensaje..."
                            className="flex-1 rounded-md border border-border bg-background px-4 py-4 text-lg focus:outline-none focus:ring-2 focus:ring-primary min-h-14"
                        />
                        <button
                            type="submit"
                            className="h-15 w-15 rounded-lg bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 transition-colors shrink-0 text-2xl"
                        >
                            <Send size={40} />
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
export default ChatMenu;
