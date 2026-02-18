import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, Bot, User, Loader2, History, Plus, MessageSquare, Copy, Check, MoreVertical, Pencil, Trash2, X } from 'lucide-react';
import { chatWithCoach, getChatHistory, getChatSessions, deleteSession, renameSession, addChatMessage } from '../api/chat';
import { feastModeService } from '../api/feastModeService';
import FeastSetupCard from '../components/chat/FeastSetupCard';
import FeastProposalCard from '../components/common/FeastProposalCard';
import FeastDeactivePreviewCard from '../components/chat/FeastDeactivePreviewCard';
import { toast } from 'react-toastify';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { v4 as uuidv4 } from 'uuid';
import { useAuth } from '../context/AuthContext';
import feastLogo from '../images/Feast-logo98_png586.png';

import { useDietPlan } from '../hooks/useDietPlan';

const AICoach = () => {
    const { user } = useAuth();
    const { plan } = useDietPlan(); // Access current diet plan
    const navigate = useNavigate();
    const firstName = user?.name ? user.name.split(' ')[0] : 'there';
    
    // Core State
    // unique storage key for each user to prevent session collision
    const storageKey = user?.id ? `chat_session_id_${user.id}` : 'chat_session_id_guest';
    const [sessionId, setSessionId] = useState(() => localStorage.getItem(storageKey) || uuidv4());
    const [input, setInput] = useState('');
    const [messages, setMessages] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    
    // Feast Mode State
    const [feastStatus, setFeastStatus] = useState(null); // { is_active: boolean, ... }
    const [feastLoading, setFeastLoading] = useState(false);

    // History State
    const [showHistory, setShowHistory] = useState(false);
    const [sessions, setSessions] = useState([]);
    const [historyLoading, setHistoryLoading] = useState(false);
    const [copiedIndex, setCopiedIndex] = useState(null);

    // Menu & Edit State
    const [activeMenu, setActiveMenu] = useState(null);
    const [editingSession, setEditingSession] = useState(null);
    const [editTitle, setEditTitle] = useState('');
    const [deleteConfirm, setDeleteConfirm] = useState(null);
    const menuRef = useRef(null);

    const scrollRef = useRef(null);
    const inputRef = useRef(null);

    // Persist Session ID (User Scoped)
    useEffect(() => {
        if (user?.id) {
            localStorage.setItem(storageKey, sessionId);
        }
    }, [sessionId, user?.id, storageKey]);

    const scrollToBottom = () => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    };

    // Initial Load - Check for existing history in this session
    useEffect(() => {
        if (messages.length === 0) {
            loadCurrentSessionHistory();
        }
        checkFeastStatus();
    }, []);

    useEffect(() => {
        scrollToBottom();
        setTimeout(() => inputRef.current?.focus(), 100);
    }, [messages]);

    const checkFeastStatus = async () => {
        try {
            const status = await feastModeService.getStatus();
            setFeastStatus(status);
        } catch (error) {
            console.error("Failed to check feast status", error);
        }
    };

    const formatTime = (dateString) => {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    const handleCopy = (text, index) => {
        navigator.clipboard.writeText(text);
        setCopiedIndex(index);
        setTimeout(() => setCopiedIndex(null), 2000);
    };

    const loadCurrentSessionHistory = async () => {
        setIsLoading(true);
        try {
            const history = await getChatHistory(sessionId);
            const formattedHistory = history.map(msg => ({
                type: msg.role === 'assistant' ? 'ai' : 'user',
                text: msg.content,
                timestamp: msg.timestamp || new Date().toISOString()
            }));
            
            if (formattedHistory.length > 0) {
                setMessages(formattedHistory);
            } else {
                setMessages([{ 
                    type: 'ai', 
                    text: `Hi ${firstName}! I'm your Fitness Coach. Ask me about your diet, workout, or just say hello!`,
                    timestamp: new Date().toISOString()
                }]);
            }
        } catch (error) {
            console.error(error);
            setMessages([{ 
                type: 'ai', 
                text: `Hi ${firstName}! I'm your Fitness Coach. Ask me about your diet, workout, or just say hello!`,
                timestamp: new Date().toISOString()
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    // --- FEAST MODE HANDLERS ---

    const startFeastActivation = () => {
        // Add User Message
        const userText = "I want to activate Feast Mode";
        setMessages(prev => [...prev, { type: 'user', text: userText, timestamp: new Date().toISOString() }]);
        addChatMessage(sessionId, 'user', userText);

        // Add AI Message with Setup Card
        setTimeout(() => {
            const aiText = "Great! Let's get that set up. When is your big event?";
            setMessages(prev => [...prev, { 
                type: 'ai', 
                text: aiText,
                timestamp: new Date().toISOString(),
                customContent: { type: 'feast_setup' }
            }]);
            addChatMessage(sessionId, 'assistant', aiText); // We can't save customContent perfectly yet, but saving text helps context
        }, 500);
    };

    const startFeastDeactivation = async () => {
        const userText = "I want to deactivate Feast Mode";
        setMessages(prev => [...prev, { type: 'user', text: userText, timestamp: new Date().toISOString() }]);
        addChatMessage(sessionId, 'user', userText);
        setIsLoading(true);

        try {
            const preview = await feastModeService.getDeactivationPreview();
            const aiText = "Here is what will happen if you cancel Feast Mode now:";
            setMessages(prev => [...prev, { 
                type: 'ai', 
                text: aiText,
                timestamp: new Date().toISOString(),
                customContent: { type: 'feast_deactivate_preview', data: preview }
            }]);
             // We persist the text part so history makes sense
            addChatMessage(sessionId, 'assistant', aiText);
        } catch (error) {
            setMessages(prev => [...prev, { 
                type: 'ai', 
                text: "I couldn't fetch the deactivation details. Please try again.",
                timestamp: new Date().toISOString()
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleFeastProposal = async ({ eventName, eventDate, selectedMeals }) => {
        setFeastLoading(true);
        try {
            const proposal = await feastModeService.proposeStrategy(eventName, eventDate, null, selectedMeals);
            setMessages(prev => [...prev, { 
                type: 'ai', 
                text: `I've calculated a strategy for ${eventName}. Check it out:`,
                timestamp: new Date().toISOString(),
                customContent: { type: 'feast_proposal', data: proposal }
            }]);
        } catch (error) {
            toast.error(error.response?.data?.detail || "Failed to propose strategy");
            setMessages(prev => [...prev, { 
                type: 'ai', 
                text: "Sorry, I couldn't generate a proposal. Please check the date and try again.",
                timestamp: new Date().toISOString()
            }]);
        } finally {
            setFeastLoading(false);
        }
    };

    const handleActivateFeast = async (proposalData) => {
        setFeastLoading(true);
        try {
            await feastModeService.activate(proposalData, true);
            
            // Success Message
            const successText = `🎉 **Feast Mode Activated!**`;
            setMessages(prev => [...prev, { 
                type: 'ai', 
                text: successText,
            }]);
            addChatMessage(sessionId, 'assistant', successText);
            
            // Refresh Status
            await checkFeastStatus();
            
        } catch (error) {
           toast.error("Failed to activate");
        } finally {
            setFeastLoading(false);
        }
    };

    const handleCancelFeast = async () => {
        setFeastLoading(true);
        try {
            await feastModeService.cancel();
            const cancelText = "Feast Mode has been cancelled. Your original plan is restored.";
            setMessages(prev => [...prev, { 
                type: 'ai', 
                text: cancelText,
                timestamp: new Date().toISOString()
            }]);
            addChatMessage(sessionId, 'assistant', cancelText);
            await checkFeastStatus();
        } catch (error) {
            toast.error("Failed to cancel");
        } finally {
            setFeastLoading(false);
        }
    };

    const cancelInteraction = () => {
        setMessages(prev => [...prev, { type: 'ai', text: "Okay, cancelled.", timestamp: new Date().toISOString() }]);
    };

    const handleSend = async (e, manualText = null) => {
        e?.preventDefault();
        
        const userMsg = manualText || input.trim();
        if (!userMsg || isLoading) return;

        if (!manualText) {
            setInput('');
        }
        
        // Add user message immediately
        const userMessageObj = { 
            type: 'user', 
            text: userMsg,
            timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, userMessageObj]);
        setIsLoading(true);

        // Intercept text commands for Feast Mode
        if (userMsg.toLowerCase().includes('activate feast mode')) {
            setIsLoading(false);
            addChatMessage(sessionId, 'user', userMsg); // Save the trigger message
            
            // Wait a tick to allow state update
            setTimeout(() => {
                 const aiText = "Great! Let's get that set up. When is your big event?";
                 setMessages(prev => [...prev, { 
                    type: 'ai', 
                    text: aiText,
                    timestamp: new Date().toISOString(),
                    customContent: { type: 'feast_setup' }
                }]);
                addChatMessage(sessionId, 'assistant', aiText);
            }, 100);
            return;
        }

        try {
            const data = await chatWithCoach(userMsg, sessionId);
            // Add AI response
            setMessages(prev => [...prev, { 
                type: 'ai', 
                text: data.response,
                timestamp: new Date().toISOString() 
            }]);

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
            setMessages(prev => [...prev, { 
                type: 'ai', 
                text: "I'm having trouble connecting right now. Please try again later.",
                timestamp: new Date().toISOString()
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleNewChat = () => {
        const newId = uuidv4();
        setSessionId(newId);
        setMessages([{ 
            type: 'ai', 
            text: `Hi ${firstName}! Starting a new conversation. How can I help?`,
            timestamp: new Date().toISOString()
        }]);
        setShowHistory(false);
    };

    const fetchSessions = async () => {
        setHistoryLoading(true);
        try {
            const data = await getChatSessions();
            setSessions(data);
        } catch (error) {
            console.error(error);
            toast.error("Failed to load session history.");
        } finally {
            setHistoryLoading(false);
        }
    };

    const handleShowHistory = () => {
        setShowHistory(!showHistory);
        if (!showHistory) {
            fetchSessions();
        }
    };

    const loadSpecificSession = async (sid) => {
        setIsLoading(true);
        try {
            const history = await getChatHistory(sid);
            const formattedHistory = history.map(msg => ({
                type: msg.role === 'assistant' ? 'ai' : 'user',
                text: msg.content,
                timestamp: msg.timestamp || new Date().toISOString()
            }));
            setMessages(formattedHistory.length > 0 ? formattedHistory : [{ 
                type: 'ai', 
                text: `Hi ${firstName}! This is an old conversation.`,
                timestamp: new Date().toISOString()
            }]);
        } catch (error) {
            console.error(error);
            toast.error("Failed to load session.");
        } finally {
            setIsLoading(false);
        }
    };

    const handleSwitchSession = (sid) => {
        setSessionId(sid);
        setMessages([]); 
        setShowHistory(false);
        loadSpecificSession(sid);
    };

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
        setEditTitle(s.title || '');
        setActiveMenu(null);
    };

    return (
        <div className="h-[calc(100vh-8rem)] md:h-[calc(100vh-5rem)] flex flex-col bg-white rounded-2xl shadow-xl overflow-hidden">
            {/* Header */}
            <div className="bg-linear-to-r from-indigo-600 to-purple-600 px-6 py-4 flex items-center justify-between shadow-lg shrink-0">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-sm">
                        <Bot className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h2 className="text-white font-bold text-lg">AI Fitness Coach</h2>
                        <p className="text-white/80 text-xs">Here to help you achieve your goals</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={handleShowHistory}
                        className="p-2 hover:bg-white/20 rounded-lg transition-all"
                        title="View History"
                    >
                        <History className="w-5 h-5 text-white" />
                    </button>
                    <button
                        onClick={handleNewChat}
                        className="p-2 hover:bg-white/20 rounded-lg transition-all"
                        title="New Chat"
                    >
                        <Plus className="w-5 h-5 text-white" />
                    </button>
                </div>
            </div>

            <div className="flex-1 flex overflow-hidden">
                {/* History Sidebar */}
                {showHistory && (
                    <div className="w-80 border-r border-gray-200 bg-gray-50 flex flex-col">
                        <div className="p-4 border-b border-gray-200 bg-white">
                            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                                <MessageSquare className="w-4 h-4" />
                                Chat History
                            </h3>
                        </div>
                        <div className="flex-1 overflow-y-auto p-3 space-y-2">
                            {historyLoading ? (
                                <div className="flex justify-center py-8">
                                    <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
                                </div>
                            ) : sessions.length === 0 ? (
                                <p className="text-sm text-gray-500 text-center py-8">No previous sessions</p>
                            ) : (
                                sessions.map((session) => (
                                    <div
                                        key={session.session_id}
                                        className={`relative p-3 rounded-lg transition-all ${
                                            session.session_id === sessionId
                                                ? 'bg-indigo-50 border border-indigo-200'
                                                : 'bg-white hover:bg-gray-100 border border-gray-200'
                                        }`}
                                    >
                                        {/* Delete Confirmation */}
                                        {deleteConfirm === session.session_id ? (
                                            <div className="flex items-center gap-2">
                                                <span className="text-red-600 text-xs flex-1">Delete this chat?</span>
                                                <button 
                                                    onClick={() => handleDeleteSession(session.session_id)}
                                                    className="px-2 py-1 bg-red-500 text-white text-xs rounded hover:bg-red-600"
                                                >
                                                    Yes
                                                </button>
                                                <button 
                                                    onClick={() => setDeleteConfirm(null)}
                                                    className="px-2 py-1 bg-gray-200 text-gray-700 text-xs rounded hover:bg-gray-300"
                                                >
                                                    No
                                                </button>
                                            </div>
                                        ) : editingSession === session.session_id ? (
                                            /* Editing Mode */
                                            <div className="flex items-center gap-2">
                                                <input
                                                    type="text"
                                                    value={editTitle}
                                                    onChange={(e) => setEditTitle(e.target.value)}
                                                    onKeyDown={(e) => {
                                                        if (e.key === 'Enter') handleRenameSession(session.session_id);
                                                        if (e.key === 'Escape') { setEditingSession(null); setEditTitle(''); }
                                                    }}
                                                    className="flex-1 px-2 py-1 text-sm border border-indigo-300 rounded focus:outline-none focus:ring-1 focus:ring-indigo-500"
                                                    autoFocus
                                                />
                                                <button 
                                                    onClick={() => handleRenameSession(session.session_id)}
                                                    className="p-1 text-indigo-600 hover:bg-indigo-100 rounded"
                                                >
                                                    <Check size={16} />
                                                </button>
                                                <button 
                                                    onClick={() => { setEditingSession(null); setEditTitle(''); }}
                                                    className="p-1 text-gray-400 hover:bg-gray-100 rounded"
                                                >
                                                    <X size={16} />
                                                </button>
                                            </div>
                                        ) : (
                                            /* Normal Mode */
                                            <div className="flex items-start gap-2">
                                                <button 
                                                    onClick={() => handleSwitchSession(session.session_id)}
                                                    className="flex-1 text-left"
                                                >
                                                    <p className="text-xs text-gray-500 mb-1">
                                                        {new Date(session.last_active).toLocaleDateString()}
                                                    </p>
                                                    <p className="text-sm font-medium text-gray-900 truncate">
                                                        {session.title || `Session ${session.session_id.slice(0, 8)}...`}
                                                    </p>
                                                </button>
                                                
                                                {/* 3-Dot Menu */}
                                                <div className="relative" ref={activeMenu === session.session_id ? menuRef : null}>
                                                    <button
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            setActiveMenu(activeMenu === session.session_id ? null : session.session_id);
                                                        }}
                                                        className="p-1.5 rounded-full hover:bg-gray-200 text-gray-400 hover:text-gray-600 transition-colors"
                                                    >
                                                        <MoreVertical size={16} />
                                                    </button>
                                                    
                                                    {/* Dropdown Menu */}
                                                    {activeMenu === session.session_id && (
                                                        <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-30 min-w-30">
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    startEditing(session);
                                                                }}
                                                                className="w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-gray-50 text-gray-700"
                                                            >
                                                                <Pencil size={14} /> Rename
                                                            </button>
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    setDeleteConfirm(session.session_id);
                                                                    setActiveMenu(null);
                                                                }}
                                                                className="w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-red-50 text-red-600"
                                                            >
                                                                <Trash2 size={14} /> Delete
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                )}

                {/* Chat Area */}
                <div className="flex-1 flex flex-col">
                    {/* Messages */}
                    <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-4 bg-linear-to-b from-gray-50 to-white">
                        {messages.map((msg, idx) => (
                            <div key={idx} className={`flex gap-3 ${msg.type === 'user' ? 'flex-row-reverse' : ''}`}>
                                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                                    msg.type === 'ai' 
                                        ? 'bg-linear-to-br from-indigo-500 to-purple-600' 
                                        : 'bg-linear-to-br from-blue-500 to-cyan-600'
                                }`}>
                                    {msg.type === 'ai' ? (
                                        <Bot className="w-5 h-5 text-white" />
                                    ) : (
                                        <User className="w-5 h-5 text-white" />
                                    )}
                                </div>
                                <div className={`flex-1 max-w-3xl ${msg.type === 'user' ? 'text-right' : ''}`}>
                                    <div className={`inline-block px-4 py-3 rounded-2xl shadow-sm ${
                                        msg.type === 'ai'
                                            ? 'bg-white border border-gray-200 text-gray-800'
                                            : 'bg-linear-to-r from-blue-600 to-cyan-600 text-white'
                                    }`}>
                                        {msg.customContent ? (
                                            <>
                                                <p className="mb-3">{msg.text}</p>
                                                {msg.customContent.type === 'feast_setup' && (
                                                    <FeastSetupCard 
                                                        onSubmit={handleFeastProposal} 
                                                        onCancel={cancelInteraction} 
                                                        dietPlan={plan}
                                                    />
                                                )}
                                                {msg.customContent.type === 'feast_proposal' && (
                                                    <FeastProposalCard 
                                                        proposal={msg.customContent.data}
                                                        onConfirm={handleActivateFeast}
                                                        onCancel={cancelInteraction}
                                                        loading={feastLoading}
                                                    />
                                                )}
                                                {msg.customContent.type === 'feast_deactivate_preview' && (
                                                    <FeastDeactivePreviewCard
                                                        preview={msg.customContent.data}
                                                        onConfirm={handleCancelFeast}
                                                        onCancel={cancelInteraction}
                                                        loading={feastLoading}
                                                    />
                                                )}
                                            </>
                                        ) : msg.type === 'ai' ? (
                                            <>
                                                <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-800 prose-li:text-gray-800 prose-strong:text-gray-900">
                                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                        {msg.text}
                                                    </ReactMarkdown>
                                                </div>
                                                {/* AI Message Footer: Copy & Time */}
                                                <div className="mt-2 flex items-center justify-end gap-2 border-t border-gray-100 pt-1">
                                                     <button 
                                                        onClick={() => handleCopy(msg.text, idx)}
                                                        className="p-1 hover:bg-gray-100 rounded text-gray-400 hover:text-gray-600 transition-colors"
                                                        title="Copy response"
                                                    >
                                                        {copiedIndex === idx ? (
                                                            <Check className="w-3.5 h-3.5 text-green-500" />
                                                        ) : (
                                                            <Copy className="w-3.5 h-3.5" />
                                                        )}
                                                    </button>
                                                    <span className="text-[10px] text-gray-400 font-medium">
                                                        {formatTime(msg.timestamp)}
                                                    </span>
                                                </div>
                                            </>
                                        ) : (
                                            <div className="text-sm whitespace-pre-wrap flex flex-col items-end">
                                                <span>{msg.text}</span>
                                                {/* User Message Time */}
                                                <span className="text-[10px] text-blue-100 mt-1">
                                                    {formatTime(msg.timestamp)}
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                        {isLoading && (
                            <div className="flex gap-3">
                                <div className="w-8 h-8 rounded-full bg-linear-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                                    <Bot className="w-5 h-5 text-white" />
                                </div>
                                <div className="bg-white border border-gray-200 px-4 py-3 rounded-2xl shadow-sm">
                                    <Loader2 className="w-5 h-5 animate-spin text-indigo-600" />
                                </div>
                            </div>
                        )}
                    </div>
                    
                    {/* Quick Actions / FAQ Chips */}
                    <div className="px-6 py-2 flex gap-2 overflow-x-auto no-scrollbar bg-white border-t border-gray-100">
                         {feastStatus ? (
                             <button 
                                onClick={startFeastDeactivation}
                                className="whitespace-nowrap px-3 py-1.5 bg-red-50 text-red-700 text-xs font-semibold rounded-full hover:bg-red-100 transition-colors border border-red-100 inline-flex items-center gap-1.5"
                             >
                                <img src={feastLogo} alt="Feast Mode" className="h-4 w-4 object-contain" />
                                Cancel Feast Mode
                             </button>
                         ) : (
                             <button 
                                onClick={startFeastActivation}
                                className="whitespace-nowrap px-3 py-1.5 bg-purple-50 text-purple-700 text-xs font-semibold rounded-full hover:bg-purple-100 transition-colors border border-purple-100 inline-flex items-center gap-1.5"
                             >
                                <img src={feastLogo} alt="Feast Mode" className="h-4 w-4 object-contain" />
                                Feast Mode
                             </button>
                         )}
                         <button 
                            onClick={() => handleSend(null, "What should I eat today?")}
                            className="whitespace-nowrap px-3 py-1.5 bg-indigo-50 text-indigo-700 text-xs font-semibold rounded-full hover:bg-indigo-100 transition-colors border border-indigo-100"
                         >
                            📅 Today's Plan
                         </button>
                    </div>

                    {/* Input Area */}
                    <div className="border-t border-gray-200 p-4 bg-white shrink-0">
                        <form onSubmit={handleSend} className="flex gap-3">
                            <input
                                ref={inputRef}
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                placeholder="Ask me anything..."
                                disabled={isLoading}
                                className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed text-gray-900 placeholder-gray-500"
                            />
                            <button
                                type="submit"
                                disabled={!input.trim() || isLoading}
                                className="px-6 py-3 bg-linear-to-r from-indigo-600 to-purple-600 text-white rounded-xl hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-medium"
                            >
                                <Send className="w-4 h-4" />
                                Send
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AICoach;
