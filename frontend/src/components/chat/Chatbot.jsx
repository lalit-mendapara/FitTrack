import React, { useState, useEffect, useRef } from 'react';
import { MessageCircle, X, Send, Bot, User, Loader2, ArrowLeft, RefreshCw, History, Plus, MessageSquare, MoreVertical, Pencil, Trash2, Check } from 'lucide-react';
import { chatWithCoach, getChatHistory, getChatSessions, deleteSession, renameSession } from '../../api/chat';
import { toast } from 'react-toastify';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { v4 as uuidv4 } from 'uuid';
import { useAuth } from '../../context/AuthContext';

const Chatbot = () => {
    const { user } = useAuth();
    const firstName = user?.name ? user.name.split(' ')[0] : 'there';
    
    // Core State
    const [isOpen, setIsOpen] = useState(false);
    const [sessionId, setSessionId] = useState(() => localStorage.getItem('chat_session_id') || uuidv4());
    const [input, setInput] = useState('');
    const [messages, setMessages] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    
    // History State
    const [showHistory, setShowHistory] = useState(false);
    const [sessions, setSessions] = useState([]);
    const [historyLoading, setHistoryLoading] = useState(false);

    // Menu & Edit State
    const [activeMenu, setActiveMenu] = useState(null); // session_id of open menu
    const [editingSession, setEditingSession] = useState(null); // session_id being edited
    const [editTitle, setEditTitle] = useState('');
    const [deleteConfirm, setDeleteConfirm] = useState(null); // session_id pending delete
    const menuRef = useRef(null);

    const scrollRef = useRef(null);
    const inputRef = useRef(null);

    // Persist Session ID
    useEffect(() => {
        localStorage.setItem('chat_session_id', sessionId);
    }, [sessionId]);

    const toggleChat = () => setIsOpen(!isOpen);

    const scrollToBottom = () => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    };

    // Initial Load - Check for existing history in this session
    useEffect(() => {
        if (isOpen && messages.length === 0) {
             loadCurrentSessionHistory();
        }
    }, [isOpen]);

    useEffect(() => {
        if (isOpen) {
            scrollToBottom();
            if (window.innerWidth >= 768) {
                setTimeout(() => inputRef.current?.focus(), 100);
            }
        }
    }, [messages, isOpen]);

    const loadCurrentSessionHistory = async () => {
        setIsLoading(true);
        try {
            const history = await getChatHistory(sessionId);
            const formattedHistory = history.map(msg => ({
                type: msg.role === 'assistant' ? 'ai' : 'user',
                text: msg.content
            }));
            
            if (formattedHistory.length > 0) {
                setMessages(formattedHistory);
            } else {
                setMessages([{ type: 'ai', text: `Hi ${firstName}! I'm your Fitness Coach. Ask me about your diet, workout, or just say hello!` }]);
            }
        } catch (error) {
            console.error(error);
            setMessages([{ type: 'ai', text: `Hi ${firstName}! I'm your Fitness Coach. Ask me about your diet, workout, or just say hello!` }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSend = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMsg = input.trim();
        setInput('');
        setMessages(prev => [...prev, { type: 'user', text: userMsg }]);
        setIsLoading(true);

        try {
            const data = await chatWithCoach(userMsg, sessionId);
            setMessages(prev => [...prev, { type: 'ai', text: data.response }]);
            
            // Sync Title if updated
            if (data.title) {
                setSessions(prevSessions => {
                    return prevSessions.map(s => 
                        s.session_id === sessionId && s.title !== data.title 
                            ? { ...s, title: data.title } 
                            : s
                    );
                });
            }
        } catch (error) {
            console.error(error);
            toast.error("Failed to connect to the coach.");
            setMessages(prev => [...prev, { type: 'ai', text: "I'm having trouble connecting right now. Please try again later." }]);
        } finally {
            setIsLoading(false);
        }
    };

    // New Chat
    const handleNewChat = () => {
        const newId = uuidv4();
        setSessionId(newId);
        setMessages([{ type: 'ai', text: `Hi ${firstName}! Starting a new conversation. How can I help?` }]);
        setShowHistory(false);
    };

    // Load History List
    const fetchSessions = async () => {
        setHistoryLoading(true);
        try {
            const data = await getChatSessions();
            setSessions(data);
        } catch (error) {
            console.error(error);
            toast.error("Could not load past sessions");
        } finally {
            setHistoryLoading(false);
        }
    };

    // Switch Session
    const handleSwitchSession = (sid) => {
        setSessionId(sid);
        setMessages([]); // Clear current view
        setShowHistory(false);
        // Effect will trigger loadCurrentSessionHistory due to empty messages + isOpen, 
        // essentially we need to manually trigger load or let effect handle it.
        // Better:
        loadSpecificSession(sid);
    };

    const loadSpecificSession = async (sid) => {
        setIsLoading(true);
        try {
            const history = await getChatHistory(sid);
            const formattedHistory = history.map(msg => ({
                type: msg.role === 'assistant' ? 'ai' : 'user',
                text: msg.content
            }));
            setMessages(formattedHistory);
        } catch (error) {
             toast.error("Failed to load session");
        } finally {
            setIsLoading(false);
        }
    }

    // Close menu on outside click
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (menuRef.current && !menuRef.current.contains(e.target)) {
                setActiveMenu(null);
            }
        };
        if (activeMenu) {
            document.addEventListener('mousedown', handleClickOutside);
        }
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [activeMenu]);

    // Handle Delete Session
    const handleDeleteSession = async (sid) => {
        try {
            await deleteSession(sid);
            setSessions(prev => prev.filter(s => s.session_id !== sid));
            toast.success("Chat deleted");
            
            // If deleted current session, start new chat
            if (sid === sessionId) {
                handleNewChat();
            }
        } catch (error) {
            toast.error("Failed to delete chat");
        } finally {
            setDeleteConfirm(null);
            setActiveMenu(null);
        }
    };

    // Handle Rename Session
    const handleRenameSession = async (sid) => {
        if (!editTitle.trim()) {
            toast.error("Title cannot be empty");
            return;
        }
        try {
            await renameSession(sid, editTitle.trim());
            setSessions(prev => prev.map(s => 
                s.session_id === sid ? { ...s, title: editTitle.trim() } : s
            ));
            toast.success("Chat renamed");
        } catch (error) {
            toast.error("Failed to rename chat");
        } finally {
            setEditingSession(null);
            setEditTitle('');
        }
    };

    // Start editing mode
    const startEditing = (s) => {
        setEditingSession(s.session_id);
        setEditTitle(s.title);
        setActiveMenu(null);
    };

    return (
        <>
            {/* 1. Floating Action Button (Visible when chat is closed) */}
            <button
                onClick={toggleChat}
                className={`fixed bottom-6 right-6 z-40 group bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white p-4 rounded-full shadow-lg hover:shadow-2xl transition-all duration-300 transform hover:scale-110 flex items-center justify-center ${isOpen ? 'scale-0 opacity-0' : 'scale-100 opacity-100'}`}
                aria-label="Open Chat"
            >
                <div className="relative">
                    <MessageCircle size={28} className="group-hover:animate-pulse" />
                    {/* Notification Badge Style (Optional) */}
                    <span className="absolute -top-1 -right-1 flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
                    </span>
                </div>
            </button>

            {/* 2. Chat Interface Container - MOVED TO LEFT */}
            <div 
                className={`fixed z-50 transition-all duration-300 ease-in-out bg-white dark:bg-gray-900 shadow-2xl flex flex-col
                    ${isOpen ? 'translate-x-0 opacity-100 pointer-events-auto' : '-translate-x-full opacity-0 pointer-events-none'}
                    
                    /* Mobile: Full Screen */
                    inset-0 w-full h-full 
                    
                    /* Desktop: LEFT Sidebar */
                    md:top-0 md:left-0 md:right-auto md:bottom-0 md:w-[450px] md:h-full md:border-r md:border-gray-200 dark:md:border-gray-800
                `}
            >
                {/* Header */}
                <div className="bg-emerald-600 p-4 flex justify-between items-center text-white shadow-md z-10">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-white/20 rounded-full">
                            <Bot size={24} />
                        </div>
                        <div>
                            <h3 className="font-bold text-lg leading-tight">Fitness Coach</h3>
                            <div className="flex items-center gap-1.5 opacity-90 text-xs">
                                <span className={`w-2 h-2 rounded-full ${isLoading ? 'bg-amber-400 animate-pulse' : 'bg-green-400'}`}></span>
                                {isLoading ? 'Thinking...' : 'Online'}
                            </div>
                        </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                        <button 
                            onClick={handleNewChat} 
                            title="New Chat" 
                            className="p-2 hover:bg-white/20 rounded-full transition-colors"
                        >
                            <Plus size={20} />
                        </button>
                        <button 
                            onClick={() => {
                                setShowHistory(!showHistory);
                                if (!showHistory) fetchSessions();
                            }} 
                            title="History" 
                            className={`p-2 hover:bg-white/20 rounded-full transition-colors ${showHistory ? 'bg-white/20' : ''}`}
                        >
                            <History size={18} />
                        </button>
                        {/* Desktop Close Button */}
                        <button onClick={toggleChat} className="hidden md:block p-2 hover:bg-white/20 rounded-full transition-colors">
                            <X size={24} />
                        </button>
                    </div>
                </div>

                {/* History Popover */}
                {showHistory && (
                    <div className="absolute top-[70px] right-2 left-2 md:left-auto md:right-[-320px] bg-white dark:bg-gray-800 shadow-xl rounded-xl border border-gray-100 dark:border-gray-700 w-auto md:w-80 max-h-[400px] overflow-hidden flex flex-col z-20 animate-in fade-in slide-in-from-top-2">
                        <div className="p-3 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center bg-gray-50 dark:bg-gray-900">
                             <h4 className="font-bold text-gray-700 dark:text-gray-200 text-sm flex items-center gap-2">
                                <History size={14} /> Previous Sessions
                             </h4>
                             <button onClick={() => setShowHistory(false)} className="text-gray-400 hover:text-gray-600"><X size={14}/></button>
                        </div>
                        <div className="overflow-y-auto flex-1 p-2 space-y-1">
                            {historyLoading ? (
                                <div className="flex justify-center p-4"><Loader2 className="animate-spin text-emerald-600" size={20}/></div>
                            ) : sessions.length === 0 ? (
                                <p className="text-center text-gray-400 text-sm py-4">No history found.</p>
                            ) : (
                                sessions.map((s) => (
                                    <div 
                                        key={s.session_id}
                                        className={`relative w-full p-3 rounded-lg text-sm transition-colors flex items-center gap-2
                                            ${sessionId === s.session_id 
                                                ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 border border-emerald-100 dark:border-emerald-800' 
                                                : 'hover:bg-gray-50 dark:hover:bg-gray-700/50 text-gray-600 dark:text-gray-300 border border-transparent'
                                            }`}
                                    >
                                        {/* Delete Confirmation Mode */}
                                        {deleteConfirm === s.session_id ? (
                                            <div className="flex-1 flex items-center gap-2">
                                                <span className="text-red-600 dark:text-red-400 text-xs flex-1">Delete this chat?</span>
                                                <button 
                                                    onClick={() => handleDeleteSession(s.session_id)}
                                                    className="px-2 py-1 bg-red-500 text-white text-xs rounded hover:bg-red-600 transition-colors"
                                                >
                                                    Yes
                                                </button>
                                                <button 
                                                    onClick={() => setDeleteConfirm(null)}
                                                    className="px-2 py-1 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                                                >
                                                    No
                                                </button>
                                            </div>
                                        ) : editingSession === s.session_id ? (
                                            /* Editing Mode */
                                            <div className="flex-1 flex items-center gap-2">
                                                <input
                                                    type="text"
                                                    value={editTitle}
                                                    onChange={(e) => setEditTitle(e.target.value)}
                                                    onKeyDown={(e) => {
                                                        if (e.key === 'Enter') handleRenameSession(s.session_id);
                                                        if (e.key === 'Escape') { setEditingSession(null); setEditTitle(''); }
                                                    }}
                                                    className="flex-1 px-2 py-1 text-xs border border-emerald-300 dark:border-emerald-600 rounded focus:outline-none focus:ring-1 focus:ring-emerald-500 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100"
                                                    autoFocus
                                                />
                                                <button 
                                                    onClick={() => handleRenameSession(s.session_id)}
                                                    className="p-1 text-emerald-600 hover:bg-emerald-100 dark:hover:bg-emerald-900/50 rounded transition-colors"
                                                >
                                                    <Check size={14} />
                                                </button>
                                                <button 
                                                    onClick={() => { setEditingSession(null); setEditTitle(''); }}
                                                    className="p-1 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                                                >
                                                    <X size={14} />
                                                </button>
                                            </div>
                                        ) : (
                                            /* Normal Mode */
                                            <>
                                                <button 
                                                    onClick={() => handleSwitchSession(s.session_id)}
                                                    className="flex-1 flex items-start gap-2 text-left"
                                                >
                                                    <MessageSquare size={16} className={`mt-0.5 shrink-0 ${sessionId === s.session_id ? 'text-emerald-500' : 'text-gray-400'}`} />
                                                    <div className="flex-1 min-w-0">
                                                        <p className="font-medium truncate">{s.title || `Session ${s.session_id.slice(0,8)}...`}</p>
                                                        <p className="text-xs opacity-70 mt-0.5">{new Date(s.last_active).toLocaleDateString()}</p>
                                                    </div>
                                                </button>
                                                
                                                {/* 3-Dot Menu */}
                                                <div className="relative" ref={activeMenu === s.session_id ? menuRef : null}>
                                                    <button
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            setActiveMenu(activeMenu === s.session_id ? null : s.session_id);
                                                        }}
                                                        className="p-1.5 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
                                                    >
                                                        <MoreVertical size={14} />
                                                    </button>
                                                    
                                                    {/* Dropdown Menu */}
                                                    {activeMenu === s.session_id && (
                                                        <div className="absolute right-0 top-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg py-1 z-30 min-w-[120px] animate-in fade-in slide-in-from-top-1">
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    startEditing(s);
                                                                }}
                                                                className="w-full px-3 py-2 text-left text-xs flex items-center gap-2 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 transition-colors"
                                                            >
                                                                <Pencil size={12} /> Rename
                                                            </button>
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    setDeleteConfirm(s.session_id);
                                                                    setActiveMenu(null);
                                                                }}
                                                                className="w-full px-3 py-2 text-left text-xs flex items-center gap-2 hover:bg-red-50 dark:hover:bg-red-900/30 text-red-600 dark:text-red-400 transition-colors"
                                                            >
                                                                <Trash2 size={12} /> Delete
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                            </>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                )}

                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto p-4 space-y-6 bg-gray-50 dark:bg-gray-950 scroll-smooth relative" ref={scrollRef}>
                    
                    {messages.length === 0 && !isLoading && (
                        <div className="flex flex-col items-center justify-center h-full opacity-50 space-y-4">
                            <div className="p-4 bg-emerald-100 rounded-full text-emerald-600">
                                <Bot size={48} />
                            </div>
                            <p className="text-sm font-medium">Start a new conversation</p>
                        </div>
                    )}
                    
                    {messages.map((msg, idx) => (
                        <div key={idx} className={`flex w-full ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`flex max-w-[85%] md:max-w-[80%] flex-col ${msg.type === 'user' ? 'items-end' : 'items-start'}`}>
                                <div 
                                    className={`relative px-4 py-3 text-sm shadow-sm ${
                                        msg.type === 'user' 
                                            ? 'bg-emerald-600 text-white rounded-2xl rounded-tr-sm' 
                                            : 'bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 border border-gray-100 dark:border-gray-800 rounded-2xl rounded-tl-sm'
                                    }`}
                                >
                                    {msg.type === 'ai' ? (
                                        <div className="prose prose-sm dark:prose-invert max-w-none prose-emerald prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-li:my-0">
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                {msg.text}
                                            </ReactMarkdown>
                                        </div>
                                    ) : (
                                        <span className="whitespace-pre-wrap">{msg.text}</span>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}

                    {/* Loading Indicator */}
                    {isLoading && (
                        <div className="flex justify-start w-full">
                             <div className="bg-white dark:bg-gray-800 px-4 py-3 rounded-2xl rounded-tl-sm border border-gray-100 dark:border-gray-800 shadow-sm flex items-center gap-3">
                                <div className="flex space-x-1">
                                    <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                                    <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                    <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce"></div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Input Area */}
                <div className="bg-white dark:bg-gray-900 border-t border-gray-100 dark:border-gray-800 p-4 pb-6 md:pb-4 shadow-lg shrink-0 z-20">
                    <form onSubmit={handleSend} className="flex gap-3 items-end max-w-4xl mx-auto w-full">
                        <div className="flex-1 bg-gray-100 dark:bg-gray-800 rounded-3xl flex items-center px-4 py-2 focus-within:ring-2 focus-within:ring-emerald-500 focus-within:bg-white dark:focus-within:bg-gray-800 transition-all border border-transparent focus-within:border-emerald-200">
                             <input
                                ref={inputRef}
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                placeholder="Type a message..."
                                className="flex-1 bg-transparent border-none focus:ring-0 text-gray-800 dark:text-gray-100 placeholder-gray-400 text-sm py-2 max-h-32"
                            />
                        </div>
                        <button 
                            type="submit" 
                            disabled={!input.trim() || isLoading}
                            className={`p-3 rounded-full shadow-md transition-all duration-200 flex items-center justify-center shrink-0
                                ${!input.trim() || isLoading 
                                    ? 'bg-gray-200 text-gray-400 cursor-not-allowed' 
                                    : 'bg-emerald-600 hover:bg-emerald-700 text-white hover:scale-105 hover:shadow-lg active:scale-95'
                                }
                            `}
                        >
                            <Send size={20} className={isLoading ? 'opacity-0' : 'opacity-100'} />
                            {isLoading && <Loader2 size={20} className="absolute animate-spin text-emerald-600" />}
                        </button>
                    </form>
                </div>
            </div>

            {/* Backdrop for Desktop */}
            {isOpen && (
                <div 
                    onClick={toggleChat}
                    className="hidden md:block fixed inset-0 bg-black/30 backdrop-blur-[1px] z-40 transition-opacity duration-300"
                ></div>
            )}
        </>
    );
};

export default Chatbot;
