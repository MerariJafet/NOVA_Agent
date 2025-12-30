import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, Bot, User, Cpu, Activity, Clock, AlertTriangle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

function App() {
    const [messages, setMessages] = useState([
        { role: 'assistant', content: '¡Hola! Soy NOVA. ¿En qué puedo ayudarte hoy?', meta: null }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [sessionId, setSessionId] = useState(`webui_${Date.now()}`);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const sendMessage = async () => {
        if (!input.trim() || loading) return;

        const userMsg = { role: 'user', content: input, meta: null };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            const response = await axios.post('/api/chat', {
                message: userMsg.content,
                session_id: sessionId
            });

            const data = response.data;
            // Handle standardized schema
            const text = data.text || data.response || "No response text";
            const meta = data.meta || null;

            setMessages(prev => [...prev, {
                role: 'assistant',
                content: text,
                meta: meta
            }]);
        } catch (error) {
            console.error("Chat error:", error);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: 'Error al conectar con el servidor.',
                meta: { error: true }
            }]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    return (
        <div className="flex flex-col h-screen bg-gray-900 text-gray-100 font-sans">
            {/* Header */}
            <header className="bg-gray-800 border-b border-gray-700 p-4 shadow-lg flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center p-1">
                    <Bot className="w-6 h-6 text-white" />
                </div>
                <div>
                    <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-400">NOVA Agent</h1>
                    <p className="text-xs text-gray-400">Intelligent Routing Enabled</p>
                </div>
            </header>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6">
                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[85%] md:max-w-[75%] rounded-2xl p-4 shadow-md ${msg.role === 'user'
                                ? 'bg-blue-600 text-white rounded-tr-none'
                                : 'bg-gray-800 border border-gray-700 rounded-tl-none'
                            }`}>

                            {/* Message Content */}
                            <div className="prose prose-invert max-w-none text-sm md:text-base">
                                <ReactMarkdown
                                    components={{
                                        code({ node, inline, className, children, ...props }) {
                                            const match = /language-(\w+)/.exec(className || '')
                                            return !inline && match ? (
                                                <SyntaxHighlighter
                                                    {...props}
                                                    style={atomDark}
                                                    language={match[1]}
                                                    PreTag="div"
                                                >{String(children).replace(/\n$/, '')}</SyntaxHighlighter>
                                            ) : (
                                                <code {...props} className={className}>
                                                    {children}
                                                </code>
                                            )
                                        }
                                    }}
                                >
                                    {msg.content}
                                </ReactMarkdown>
                            </div>

                            {/* Metadata Panel (Only for assistant) */}
                            {msg.role === 'assistant' && msg.meta && !msg.meta.error && (
                                <div className="mt-4 pt-3 border-t border-gray-700/50 flex flex-wrap gap-3 text-xs text-gray-400 bg-gray-900/30 -mx-4 -mb-4 p-3 rounded-b-2xl">
                                    <div className="flex items-center gap-1.5" title="Router Used">
                                        <Activity className="w-3.5 h-3.5 text-blue-400" />
                                        <span className="font-medium text-blue-200">{msg.meta.router}</span>
                                    </div>
                                    <div className="flex items-center gap-1.5" title="Model Selected">
                                        <Cpu className="w-3.5 h-3.5 text-purple-400" />
                                        <span className="font-medium text-purple-200">{msg.meta.model_selected}</span>
                                    </div>
                                    {msg.meta.latency_ms && (
                                        <div className="flex items-center gap-1.5" title="Latency">
                                            <Clock className="w-3.5 h-3.5 text-green-400" />
                                            <span>{msg.meta.latency_ms}ms</span>
                                        </div>
                                    )}
                                    {msg.meta.reason && (
                                        <div className="w-full mt-1 border-l-2 border-gray-600 pl-2 italic text-gray-500">
                                            "{msg.meta.reason}"
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                ))}
                {loading && (
                    <div className="flex justify-start">
                        <div className="bg-gray-800 rounded-2xl p-4 rounded-tl-none border border-gray-700 flex items-center gap-2">
                            <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></span>
                            <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce delay-75"></span>
                            <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce delay-150"></span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="bg-gray-800 border-t border-gray-700 p-4">
                <div className="max-w-4xl mx-auto flex gap-2">
                    <input
                        type="text"
                        className="flex-1 bg-gray-900 text-white border border-gray-700 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-500"
                        placeholder="Escribe tu mensaje..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={loading}
                    />
                    <button
                        onClick={sendMessage}
                        disabled={loading || !input.trim()}
                        className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl px-6 transition-colors flex items-center gap-2 font-medium"
                    >
                        <Send className="w-5 h-5" />
                    </button>
                </div>
            </div>
        </div>
    );
}

export default App;
