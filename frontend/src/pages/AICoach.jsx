import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, Bot, User, Loader2, History, Plus, MessageSquare, Copy, Check, MoreVertical, Pencil, Trash2, X, Drumstick, Utensils, Dumbbell, BatteryLow, TrendingUp, Target, PanelRight } from 'lucide-react';
import { chatWithCoach, getChatHistory, getChatSessions, deleteSession, renameSession, addChatMessage, updateChatMessage, deleteChatMessage } from '../api/chat';
import { feastModeService } from '../api/feastModeService';
import FeastSetupCard from '../components/chat/FeastSetupCard';
import FeastProposalCard from '../components/common/FeastProposalCard';
import FeastDeactivePreviewCard from '../components/chat/FeastDeactivePreviewCard';
import FeastModePanel from '../components/chat/FeastModePanel';
import { toast } from 'react-toastify';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { v4 as uuidv4 } from 'uuid';
import { useAuth } from '../context/AuthContext';
import feastLogo from '../images/Feast-logo98_png586.png';

import { useDietPlan } from '../hooks/useDietPlan';
import { useWorkoutPlan } from '../hooks/useWorkoutPlan';

const AICoach = () => {
    const { user } = useAuth();
    const { plan } = useDietPlan(); // Access current diet plan
    const { plan: workoutPlan } = useWorkoutPlan();
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
    const [feastActivating, setFeastActivating] = useState(false);
    const [activationProposal, setActivationProposal] = useState(null);

    // History State
    const [showHistory, setShowHistory] = useState(false);
    const [sessions, setSessions] = useState([]);
    const [historyLoading, setHistoryLoading] = useState(false);
    const [copiedIndex, setCopiedIndex] = useState(null);

    // Right Panel Toggle (mobile)
    const [showRightPanel, setShowRightPanel] = useState(false);

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
                id: msg.id,
                type: msg.role === 'assistant' ? 'ai' : 'user',
                text: msg.content,
                customContent: msg.custom_content,
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

    const updateCustomContent = (type, updates = null) => {
        setMessages(prev => prev.map(msg => {
            if (msg.customContent && msg.customContent.type === type) {
                if (updates === null) {
                    // Remove if updates is null
                    const { customContent, ...rest } = msg;

                    // If message is persisted, we should probably update it too, 
                    // but removing customContent via API might mean setting it to null
                    if (msg.id) {
                        updateChatMessage(msg.id, null);
                    }
                    return rest;
                }
                
                // Otherwise update val
                const newCustomContent = { ...msg.customContent, ...updates };
                
                // Persist to backend if message has ID
                if (msg.id) {
                    updateChatMessage(msg.id, newCustomContent);
                }

                return {
                    ...msg,
                    customContent: newCustomContent
                };
            }
            return msg;
        }));
    };

    // --- FEAST MODE HANDLERS ---

    const startFeastActivation = async () => {
        // Add User Message
        const userText = "I want to activate Feast Mode";
        const userMsgDesc = { type: 'user', text: userText, timestamp: new Date().toISOString() };
        
        // Optimistically add user msg
        setMessages(prev => [...prev, userMsgDesc]);
        
        // Persist user msg
        await addChatMessage(sessionId, 'user', userText);

        // Add AI Message with Setup Card
        setTimeout(async () => {
            const aiText = "Great! Let's get that set up. When is your big event?";
            const customContent = { type: 'feast_setup' };
            
            // Persist AI msg first to get ID
            const savedMsg = await addChatMessage(sessionId, 'assistant', aiText, customContent);
            
            setMessages(prev => [...prev, { 
                id: savedMsg?.id, // Important for updates
                type: 'ai', 
                text: aiText,
                timestamp: new Date().toISOString(),
                customContent: customContent
            }]);
        }, 500);
    };

    const startFeastDeactivation = async () => {
        const userText = "I want to deactivate Feast Mode";
        setMessages(prev => [...prev, { type: 'user', text: userText, timestamp: new Date().toISOString() }]);
        await addChatMessage(sessionId, 'user', userText);
        setIsLoading(true);

        try {
            const preview = await feastModeService.getDeactivationPreview();
            const aiText = "Here is what will happen if you cancel Feast Mode now:";
            const customContent = { type: 'feast_deactivate_preview', data: preview };

            const savedMsg = await addChatMessage(sessionId, 'assistant', aiText, customContent);

            setMessages(prev => [...prev, { 
                id: savedMsg?.id,
                type: 'ai', 
                text: aiText,
                timestamp: new Date().toISOString(),
                customContent: customContent
            }]);
        } catch (error) {
            const errorText = "I couldn't fetch the deactivation details. Please try again.";
            setMessages(prev => [...prev, { 
                type: 'ai', 
                text: errorText,
                timestamp: new Date().toISOString()
            }]);
            await addChatMessage(sessionId, 'assistant', errorText);
        } finally {
            setIsLoading(false);
        }
    };

    const handleFeastProposal = async ({ eventName, eventDate, selectedMeals }) => {
        setFeastLoading(true);
        try {
            // Mark setup as static (completed) locally
            updateCustomContent('feast_setup', { isStatic: true, selectedData: { eventName, eventDate, selectedMeals } });

            // Robust persistence - SWEEP ALL SETUP CARDS
            try {
                const history = await getChatHistory(sessionId);
                const interactiveMsgs = history.filter(m => 
                    m.custom_content?.type === 'feast_setup' && !m.custom_content.isStatic
                );
                
                for (const msg of interactiveMsgs) {
                    await updateChatMessage(msg.id, {
                        ...msg.custom_content,
                        isStatic: true,
                        selectedData: { eventName, eventDate, selectedMeals }
                    });
                }
            } catch (e) { console.error("Persist setup sweep failed", e); }

            const proposal = await feastModeService.proposeStrategy(eventName, eventDate, null, selectedMeals);
            
            const aiText = `I've calculated a strategy for ${eventName}. Check it out:`;
            const customContent = { type: 'feast_proposal', data: proposal };

            const savedMsg = await addChatMessage(sessionId, 'assistant', aiText, customContent);

            setMessages(prev => [...prev, { 
                id: savedMsg?.id,
                type: 'ai', 
                text: aiText,
                timestamp: new Date().toISOString(),
                customContent: customContent
            }]);
        } catch (error) {
            const errorText = error.response?.data?.detail || "Sorry, I couldn't generate a proposal. Please check the date and try again.";
            toast.error(errorText);
            setMessages(prev => [...prev, { 
                type: 'ai', 
                text: errorText,
                timestamp: new Date().toISOString()
            }]);
            await addChatMessage(sessionId, 'assistant', errorText);
        } finally {
            setFeastLoading(false);
        }
    };

    const handleActivateFeast = async (proposalData) => {
        setFeastLoading(true);
        try {
            await feastModeService.activate(proposalData, true);
            
            // Mark proposal as static (activated) locally and save USER CHOICES
            updateCustomContent('feast_proposal', { 
                isStatic: true,
                data: proposalData 
            });

            // Robust persistence - SWEEP ALL PROPOSAL CARDS
            try {
                const history = await getChatHistory(sessionId);
                const interactiveMsgs = history.filter(m => 
                    m.custom_content?.type === 'feast_proposal' && !m.custom_content.isStatic
                );
                
                for (const msg of interactiveMsgs) {
                    await updateChatMessage(msg.id, {
                        ...msg.custom_content,
                        isStatic: true,
                        data: proposalData
                    });
                }

                // Sweep and delete setup cards from backend history
                const setupMsgs = history.filter(m => m.custom_content?.type === 'feast_setup');
                for (const msg of setupMsgs) {
                    await deleteChatMessage(msg.id);
                }
            } catch (e) { console.error("Persist activation sweep failed", e); }

            // Remove the setup card entirely from the chat view locally
            setMessages(prev => prev.filter(msg => msg.customContent?.type !== 'feast_setup'));

            // Store real proposal data for the right panel
            setActivationProposal(proposalData);

            // Trigger right panel activation animation
            setFeastActivating(true);

            // Refresh Status
            await checkFeastStatus();
            
        } catch (error) {
           toast.error("Failed to activate");
        } finally {
            setFeastLoading(false);
        }
    };

    const handleFeastActivationComplete = async () => {
        // Send final confirmation message in chat using real proposal data
        const banked = activationProposal?.total_banked ?? activationProposal?.daily_deduction * activationProposal?.days_remaining ?? 750;
        const confirmText = `🎉 **Feast Mode is now active!** Your ${banked} kcal bank is confirmed. On party day, forget calorie counting — just enjoy! I'll remind you with a meal plan the morning of. You've got this! 💪`;
        const savedMsg = await addChatMessage(sessionId, 'assistant', confirmText);
        setMessages(prev => [...prev, {
            id: savedMsg?.id,
            type: 'ai',
            text: confirmText,
            timestamp: new Date().toISOString()
        }]);
    };

    const handleCancelFeast = async () => {
        setFeastLoading(true);
        try {
            await feastModeService.cancel();
            
            // Mark preview as static locally
            updateCustomContent('feast_deactivate_preview', { isStatic: true });

            // ROBUST FIX: SWEEP ALL PREVIEW CARDS
            try {
                const history = await getChatHistory(sessionId);
                const interactiveMsgs = history.filter(m => 
                    m.custom_content?.type === 'feast_deactivate_preview' && !m.custom_content.isStatic
                );
                
                for (const msg of interactiveMsgs) {
                    await updateChatMessage(msg.id, {
                        ...msg.custom_content,
                        isStatic: true
                    });
                }
            } catch (err) {
                console.error("Failed to persist static state", err);
            }

            const cancelText = "Feast Mode has been cancelled. Your original plan is restored.";
            const savedMsg = await addChatMessage(sessionId, 'assistant', cancelText);
            
            setMessages(prev => [...prev, { 
                id: savedMsg?.id,
                type: 'ai', 
                text: cancelText,
                timestamp: new Date().toISOString()
            }]);
            
            await checkFeastStatus();
            // Reset right panel to default (feast ended)
            setFeastActivating(false);
            setActivationProposal(null);
        } catch (error) {
            toast.error("Failed to cancel");
        } finally {
            setFeastLoading(false);
        }
    };

    const cancelInteraction = async () => {
        // Find messages to delete (active cards)
        const messagesToDelete = messages.filter(msg => 
            msg.customContent && (
                (msg.customContent.type === 'feast_setup' && !msg.customContent.isStatic) ||
                (msg.customContent.type === 'feast_proposal' && !msg.customContent.isStatic) ||
                (msg.customContent.type === 'feast_deactivate_preview' && !msg.customContent.isStatic)
            )
        );

        // Delete from backend
        for (const msg of messagesToDelete) {
            if (msg.id) {
                await deleteChatMessage(msg.id);
            }
        }

        // Remove from local state
        setMessages(prev => prev.filter(msg => 
            !msg.customContent || (
                msg.customContent.type !== 'feast_setup' && 
                msg.customContent.type !== 'feast_proposal' && 
                msg.customContent.type !== 'feast_deactivate_preview'
            ) || msg.customContent.isStatic
        ));

        // Optional: Add a small toast or just transient message?
        // User asked for messages to disappear, so maybe no "Okay cancelled" message needed?
        // But some feedback is good. unique id for this system msg prevents persisted history clutter?
        // actually let's just show a toast
        toast.info("Feast interaction cancelled");
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
            setTimeout(async () => {
                 const aiText = "Great! Let's get that set up. When is your big event?";
                 setMessages(prev => [...prev, { 
                    type: 'ai', 
                    text: aiText,
                    timestamp: new Date().toISOString(),
                    customContent: { type: 'feast_setup' }
                }]);
                await addChatMessage(sessionId, 'assistant', aiText);
                
                // Refresh sessions to get the new title (generated in background)
                fetchSessions();
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

            // Sync Title if updated and Move to Top (Optimistic Update)
            if (data.title) {
                setSessions(prevSessions => {
                    const updated = prevSessions.map(s => 
                        s.session_id === sessionId 
                            ? { ...s, title: data.title, last_active: new Date().toISOString() } 
                            : s
                    );
                    const current = updated.find(s => s.session_id === sessionId);
                    const others = updated.filter(s => s.session_id !== sessionId);
                    
                    return current ? [current, ...others] : updated;
                });
            } else {
                // Even if no title update, move current session to top
                setSessions(prevSessions => {
                    const current = prevSessions.find(s => s.session_id === sessionId);
                    const others = prevSessions.filter(s => s.session_id !== sessionId);
                    
                    if (current) {
                        return [{ ...current, last_active: new Date().toISOString() }, ...others];
                    }
                    return prevSessions;
                });
            }
            
            // Refresh sessions list immediately and then delayed to catch background title generation
            fetchSessions();
            setTimeout(() => fetchSessions(), 3000);
            setTimeout(() => fetchSessions(), 8000);
            setTimeout(() => fetchSessions(), 15000);

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
                id: msg.id,
                type: msg.role === 'assistant' ? 'ai' : 'user',
                text: msg.content,
                customContent: msg.custom_content,
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

    const handleBackToSetup = (proposalData) => {
        // Revert the last message (Proposal) back to Setup
        setMessages(prev => {
            let newMsgs = [...prev];
            const lastMsg = newMsgs[newMsgs.length - 1];
            
            // Check if the message before the last one is a static setup card
            if (newMsgs.length >= 2) {
                const prevMsg = newMsgs[newMsgs.length - 2];
                if (prevMsg.customContent?.type === 'feast_setup' && prevMsg.customContent.isStatic) {
                    // Remove the static setup card
                    newMsgs.splice(newMsgs.length - 2, 1);
                }
            }

            // Now update the last message (which might have shifted index if we removed one)
            const targetIndex = newMsgs.length - 1;
            const targetMsg = newMsgs[targetIndex];

            if (targetMsg.customContent?.type === 'feast_proposal') {
                // We want to go back to feast_setup
                // The proposal data contains the event info we need to restore
                newMsgs[targetIndex] = {
                    ...targetMsg,
                    text: "Let's adjust the details.",
                    customContent: { 
                        type: 'feast_setup',
                        // We need to pass back the original inputs, which confusingly are mixed in proposalData
                        // proposalData has event_name, event_date, etc.
                        initialData: {
                            eventName: proposalData.event_name,
                            eventDate: proposalData.event_date.split('T')[0], // ensure YYYY-MM-DD
                            selectedMeals: proposalData.selected_meals
                        }
                    }
                };
            }
            return newMsgs;
        });
    };

    const handleTodaysWorkout = async () => {
        if (!workoutPlan?.weekly_schedule) {
            handleSend(null, "What is my workout for today?");
            return;
        }

        // Calculate today's workout day
        const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        const today = new Date();
        const todayName = days[today.getDay()];

        // Find which day in the schedule matches today
        const scheduleEntries = Object.entries(workoutPlan.weekly_schedule);
        const todayEntry = scheduleEntries.find(([_, dayData]) => 
            dayData.day_name?.toLowerCase() === todayName.toLowerCase()
        );

        if (!todayEntry) {
            handleSend(null, "What is my workout for today?");
            return;
        }

        const [dayKey, dayData] = todayEntry;
        const workoutType = dayData.workout_name || dayData.focus || 'Workout';
        const exerciseCount = dayData.exercises?.length || 0;

        // Create link to today's exercises
        const workoutLink = `/dashboard?tab=workout-plan&day=${dayKey}`;

        // Add user message
        const userText = "What is my workout for today?";
        setMessages(prev => [...prev, { type: 'user', text: userText, timestamp: new Date().toISOString() }]);
        await addChatMessage(sessionId, 'user', userText);

        // Add AI response with link
        setTimeout(async () => {
            // Build exercise list
            const exerciseList = dayData.exercises?.slice(0, 3).map(ex => {
                const exerciseName = ex.exercise || ex.name || 'Exercise';
                const sets = ex.sets ? ` – ${ex.sets}×${ex.reps || ex.rep_range || ''}` : '';
                return `- ${exerciseName}${sets}`;
            }).join('\n') || '- No exercises listed';

            const aiText = `Hey ${firstName}! Since today is **${todayName}**, you're on a **${workoutType}** day. Here's the full lineup:\n\n${exerciseList}${exerciseCount > 3 ? `\n- ...and ${exerciseCount - 3} more exercises` : ''}\n\n[**View Today's Full Workout →**](${workoutLink})`;
            
            const savedMsg = await addChatMessage(sessionId, 'assistant', aiText);
            
            setMessages(prev => [...prev, { 
                id: savedMsg?.id,
                type: 'ai', 
                text: aiText,
                timestamp: new Date().toISOString()
            }]);
        }, 500);
    };

    return (
        <div className="h-[calc(100vh-8rem)] md:h-[calc(100vh-5rem)] flex flex-col overflow-hidden" style={{ background: '#f0f2f5' }}>
            {/* ── HEADER ── */}
            <div className="aicoach-header shrink-0 flex items-center gap-3 z-10" style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', boxShadow: '0 2px 20px rgba(99,102,241,0.3)' }}>
                <div className="aicoach-bot-avatar flex items-center justify-center shrink-0" style={{ background: 'rgba(255,255,255,0.2)', borderRadius: 12, fontSize: 20 }}>
                    🤖
                </div>
                <div className="flex-1 min-w-0">
                    <div className="aicoach-header-title" style={{ color: 'white', fontWeight: 700 }}>AI Fitness Coach</div>
                    <div className="flex items-center gap-1.5 aicoach-header-sub" style={{ color: 'rgba(255,255,255,0.7)' }}>
                        <div className="feast-status-dot shrink-0" />
                        <span className="truncate">Online · Here to help you achieve your goals</span>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <button onClick={handleShowHistory} title="History" className="cursor-pointer shrink-0" style={{ color: 'rgba(255,255,255,0.75)', background: 'none', border: 'none' }}>
                        <History className="w-5 h-5" />
                    </button>
                    <button onClick={handleNewChat} title="New chat" className="cursor-pointer shrink-0" style={{ color: 'rgba(255,255,255,0.75)', background: 'none', border: 'none' }}>
                        <Plus className="w-5 h-5" />
                    </button>
                    <button
                        onClick={() => setShowRightPanel(prev => !prev)}
                        title="Toggle Feast Panel"
                        className="cursor-pointer lg:hidden shrink-0"
                        style={{ color: 'rgba(255,255,255,0.75)', background: 'none', border: 'none', position: 'relative' }}
                    >
                        <PanelRight className="w-5 h-5" />
                        {feastStatus && (
                            <span style={{ position: 'absolute', top: -2, right: -2, width: 8, height: 8, borderRadius: '50%', background: '#4ade80', border: '2px solid #6366f1' }} />
                        )}
                    </button>
                </div>
            </div>

            {/* ── MAIN BODY ── */}
            <div className="flex flex-1 overflow-hidden">

                {/* History Sidebar (overlay) */}
                {showHistory && (
                    <div className="w-72 border-r border-gray-200 bg-gray-50 flex flex-col shrink-0 z-20">
                        <div className="p-4 border-b border-gray-200 bg-white flex items-center justify-between">
                            <h3 className="font-semibold text-gray-900 flex items-center gap-2 text-sm">
                                <MessageSquare className="w-4 h-4" />
                                Chat History
                            </h3>
                            <button onClick={() => setShowHistory(false)} className="p-1 hover:bg-gray-100 rounded">
                                <X size={16} className="text-gray-400" />
                            </button>
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
                                        {deleteConfirm === session.session_id ? (
                                            <div className="flex items-center gap-2">
                                                <span className="text-red-600 text-xs flex-1">Delete this chat?</span>
                                                <button onClick={() => handleDeleteSession(session.session_id)} className="px-2 py-1 bg-red-500 text-white text-xs rounded hover:bg-red-600">Yes</button>
                                                <button onClick={() => setDeleteConfirm(null)} className="px-2 py-1 bg-gray-200 text-gray-700 text-xs rounded hover:bg-gray-300">No</button>
                                            </div>
                                        ) : editingSession === session.session_id ? (
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
                                                <button onClick={() => handleRenameSession(session.session_id)} className="p-1 text-indigo-600 hover:bg-indigo-100 rounded"><Check size={16} /></button>
                                                <button onClick={() => { setEditingSession(null); setEditTitle(''); }} className="p-1 text-gray-400 hover:bg-gray-100 rounded"><X size={16} /></button>
                                            </div>
                                        ) : (
                                            <div className="flex items-start gap-2">
                                                <button onClick={() => handleSwitchSession(session.session_id)} className="flex-1 text-left">
                                                    <p className="text-xs text-gray-500 mb-1">{new Date(session.last_active).toLocaleDateString()}</p>
                                                    <p className="text-sm font-medium text-gray-900 truncate">{session.title || `Session ${session.session_id.slice(0, 8)}...`}</p>
                                                </button>
                                                <div className="relative" ref={activeMenu === session.session_id ? menuRef : null}>
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); setActiveMenu(activeMenu === session.session_id ? null : session.session_id); }}
                                                        className="p-1.5 rounded-full hover:bg-gray-200 text-gray-400 hover:text-gray-600 transition-colors"
                                                    >
                                                        <MoreVertical size={16} />
                                                    </button>
                                                    {activeMenu === session.session_id && (
                                                        <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-30 min-w-30">
                                                            <button onClick={(e) => { e.stopPropagation(); startEditing(session); }} className="w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-gray-50 text-gray-700">
                                                                <Pencil size={14} /> Rename
                                                            </button>
                                                            <button onClick={(e) => { e.stopPropagation(); setDeleteConfirm(session.session_id); setActiveMenu(null); }} className="w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-red-50 text-red-600">
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

                {/* ══ CHAT AREA (70% on desktop with panel, 100% on mobile) ══ */}
                <div className="flex flex-col bg-white flex-1 min-w-0 lg:w-[70%] overflow-hidden" style={{ borderRight: '1px solid #e8eaed' }}>
                    {/* Messages */}
                    <div
                        ref={scrollRef}
                        className="aicoach-messages flex-1 overflow-y-auto overflow-x-hidden flex flex-col gap-4"
                    >
                        {messages.map((msg, idx) => (
                            <div
                                key={idx}
                                className={`aicoach-msg flex gap-2.5 feast-slide-up ${msg.type === 'user' ? 'self-end flex-row-reverse' : 'self-start'}`}
                            >
                                {/* Avatar */}
                                {msg.type === 'ai' ? (
                                    <div
                                        className="shrink-0 flex items-center justify-center"
                                        style={{
                                            width: 32, height: 32, borderRadius: 10,
                                            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                                            fontSize: 15,
                                        }}
                                    >
                                        🤖
                                    </div>
                                ) : user?.profile_picture_url ? (
                                    <img src={user.profile_picture_url} alt={user.name} className="shrink-0 object-cover" style={{ width: 32, height: 32, borderRadius: 10 }} />
                                ) : (
                                    <div
                                        className="shrink-0 flex items-center justify-center"
                                        style={{ width: 32, height: 32, borderRadius: 10, background: '#f3f4f6', fontSize: 15 }}
                                    >
                                        👤
                                    </div>
                                )}

                                {/* Bubble */}
                                <div className="flex flex-col min-w-0">
                                    <div
                                        className="aicoach-bubble"
                                        style={{
                                            borderRadius: 16,
                                            fontSize: 13,
                                            lineHeight: 1.55,
                                            wordBreak: 'break-word',
                                            overflowWrap: 'break-word',
                                            ...(msg.type === 'ai'
                                                ? {
                                                    background: '#f7f8fc',
                                                    border: '1px solid #eaecf0',
                                                    color: '#1f2937',
                                                    borderTopLeftRadius: 4,
                                                  }
                                                : {
                                                    background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                                                    color: 'white',
                                                    borderTopRightRadius: 4,
                                                  }),
                                        }}
                                    >
                                        {msg.customContent ? (
                                            <>
                                                <p className="mb-3" style={{ fontSize: 13 }}>{msg.text}</p>
                                                {msg.customContent.type === 'feast_setup' && (
                                                    <FeastSetupCard
                                                        onSubmit={handleFeastProposal}
                                                        onCancel={cancelInteraction}
                                                        dietPlan={plan}
                                                        isStatic={msg.customContent.isStatic}
                                                        staticData={msg.customContent.selectedData}
                                                        initialData={msg.customContent.initialData}
                                                    />
                                                )}
                                                {msg.customContent.type === 'feast_proposal' && (
                                                    <FeastProposalCard
                                                        proposal={msg.customContent.data}
                                                        onConfirm={handleActivateFeast}
                                                        onCancel={cancelInteraction}
                                                        onBack={() => handleBackToSetup(msg.customContent.data)}
                                                        loading={feastLoading}
                                                        isStatic={msg.customContent.isStatic}
                                                    />
                                                )}
                                                {msg.customContent.type === 'feast_deactivate_preview' && (
                                                    <FeastDeactivePreviewCard
                                                        preview={msg.customContent.data}
                                                        onConfirm={handleCancelFeast}
                                                        onCancel={cancelInteraction}
                                                        loading={feastLoading}
                                                        isStatic={msg.customContent.isStatic}
                                                    />
                                                )}
                                            </>
                                        ) : msg.type === 'ai' ? (
                                            <>
                                                <div className="aicoach-prose prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-800 prose-li:text-gray-800 prose-strong:text-gray-900">
                                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                        {msg.text}
                                                    </ReactMarkdown>
                                                </div>
                                                <div className="mt-2 flex items-center justify-end gap-2 pt-1" style={{ borderTop: '1px solid #eaecf0' }}>
                                                    <button
                                                        onClick={() => handleCopy(msg.text, idx)}
                                                        className="p-1 hover:bg-gray-100 rounded text-gray-400 hover:text-gray-600 transition-colors"
                                                        title="Copy response"
                                                    >
                                                        {copiedIndex === idx ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
                                                    </button>
                                                    <span style={{ fontSize: 10, color: '#9ca3af', fontWeight: 500 }}>{formatTime(msg.timestamp)}</span>
                                                </div>
                                            </>
                                        ) : (
                                            <div className="flex flex-col items-end" style={{ fontSize: 13 }}>
                                                <span className="whitespace-pre-wrap">{msg.text}</span>
                                                <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.6)', marginTop: 4 }}>{formatTime(msg.timestamp)}</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}

                        {/* Typing indicator */}
                        {isLoading && (
                            <div className="flex gap-2.5 self-start feast-slide-up" style={{ maxWidth: '85%' }}>
                                <div
                                    className="shrink-0 flex items-center justify-center"
                                    style={{ width: 32, height: 32, borderRadius: 10, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', fontSize: 15 }}
                                >
                                    🤖
                                </div>
                                <div className="feast-typing-bubble">
                                    <span /><span /><span />
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Quick Replies */}
                    <div className="aicoach-quick-replies flex gap-1.5 overflow-x-auto shrink-0" style={{ borderTop: '1px solid #f0f2f5' }}>
                        {feastStatus ? (
                            <div className="shrink-0 flex items-center gap-1.5" style={{ whiteSpace: 'nowrap', padding: '7px 13px', borderRadius: 20, border: '1px solid #22c55e', background: 'rgba(34,197,94,0.1)', fontSize: 11, color: '#16a34a', fontFamily: 'inherit', fontWeight: 600 }}>
                                <Drumstick className="w-3.5 h-3.5" />
                                Feast Mode Active
                            </div>
                        ) : (
                            <button
                                onClick={startFeastActivation}
                                className="shrink-0 cursor-pointer flex items-center gap-1.5"
                                style={{
                                    whiteSpace: 'nowrap', padding: '7px 13px', borderRadius: 20,
                                    border: '1px solid transparent',
                                    background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                                    fontSize: 11, color: 'white', fontFamily: 'inherit',
                                }}
                            >
                                <Drumstick className="w-3.5 h-3.5" />
                                Feast Mode
                            </button>
                        )}
                        <button onClick={() => handleSend(null, "What should I eat today?")} className="shrink-0 cursor-pointer flex items-center gap-1.5" style={{ whiteSpace: 'nowrap', padding: '7px 13px', borderRadius: 20, border: '1px solid #e5e7eb', background: 'white', fontSize: 11, color: '#374151', fontFamily: 'inherit' }}>
                            <Utensils className="w-3.5 h-3.5" />
                            What should I eat?
                        </button>
                        <button onClick={handleTodaysWorkout} className="shrink-0 cursor-pointer flex items-center gap-1.5" style={{ whiteSpace: 'nowrap', padding: '7px 13px', borderRadius: 20, border: '1px solid #e5e7eb', background: 'white', fontSize: 11, color: '#374151', fontFamily: 'inherit' }}>
                            <Dumbbell className="w-3.5 h-3.5" />
                            Today's Workout
                        </button>
                        <button onClick={() => handleSend(null, "I'm feeling low energy today, suggest a lighter workout or rest")} className="shrink-0 cursor-pointer flex items-center gap-1.5" style={{ whiteSpace: 'nowrap', padding: '7px 13px', borderRadius: 20, border: '1px solid #e5e7eb', background: 'white', fontSize: 11, color: '#374151', fontFamily: 'inherit' }}>
                            <BatteryLow className="w-3.5 h-3.5" />
                            I'm too tired today
                        </button>
                        <button onClick={() => handleSend(null, "Give me a summary of my progress this week")} className="shrink-0 cursor-pointer flex items-center gap-1.5" style={{ whiteSpace: 'nowrap', padding: '7px 13px', borderRadius: 20, border: '1px solid #e5e7eb', background: 'white', fontSize: 11, color: '#374151', fontFamily: 'inherit' }}>
                            <TrendingUp className="w-3.5 h-3.5" />
                            My Progress
                        </button>
                        <button onClick={() => handleSend(null, "Am I on track to reach my goal based on my recent activity?")} className="shrink-0 cursor-pointer flex items-center gap-1.5" style={{ whiteSpace: 'nowrap', padding: '7px 13px', borderRadius: 20, border: '1px solid #e5e7eb', background: 'white', fontSize: 11, color: '#374151', fontFamily: 'inherit' }}>
                            <Target className="w-3.5 h-3.5" />
                            Am I on track?
                        </button>
                    </div>

                    {/* Input Bar */}
                    <div className="aicoach-input-bar shrink-0 flex gap-2.5 items-center" style={{ borderTop: '1px solid #f0f2f5' }}>
                        <form onSubmit={handleSend} className="flex gap-2.5 items-center w-full">
                            <input
                                ref={inputRef}
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                placeholder="Ask me anything..."
                                disabled={isLoading}
                                className="flex-1 outline-none"
                                style={{
                                    padding: '11px 16px',
                                    borderRadius: 24,
                                    border: '1.5px solid #e5e7eb',
                                    fontFamily: 'inherit',
                                    fontSize: 13,
                                    color: '#1f2937',
                                    background: '#fafafa',
                                    transition: 'border-color 0.2s',
                                }}
                                onFocus={(e) => { e.target.style.borderColor = '#6366f1'; e.target.style.background = 'white'; }}
                                onBlur={(e) => { e.target.style.borderColor = '#e5e7eb'; e.target.style.background = '#fafafa'; }}
                            />
                            <button
                                type="submit"
                                disabled={!input.trim() || isLoading}
                                className="shrink-0 flex items-center justify-center cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                                style={{
                                    width: 42, height: 42,
                                    background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                                    border: 'none', borderRadius: '50%',
                                    fontSize: 16, transition: 'transform 0.15s',
                                    color: 'white',
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.08)'}
                                onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                            >
                                <Send className="w-4 h-4" />
                            </button>
                        </form>
                    </div>
                </div>

                {/* ══ RIGHT PANEL (30%) — desktop: inline, mobile: slide-over ══ */}

                {/* Desktop panel (always visible, part of flex layout) */}
                <div className="feast-panel-desktop">
                    <FeastModePanel
                        isActivating={feastActivating}
                        proposalData={activationProposal}
                        feastStatus={feastStatus}
                        onActivationComplete={handleFeastActivationComplete}
                    />
                </div>

                {/* Mobile overlay panel */}
                {showRightPanel && (
                    <div className="feast-panel-mobile-backdrop" onClick={() => setShowRightPanel(false)} />
                )}
                <div className={`feast-panel-mobile ${showRightPanel ? 'open' : ''}`}>
                    <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                        <span style={{ color: 'white', fontWeight: 700, fontSize: 13 }}>Feast Mode Panel</span>
                        <button
                            onClick={() => setShowRightPanel(false)}
                            className="cursor-pointer"
                            style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.5)' }}
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                    <FeastModePanel
                        isActivating={feastActivating}
                        proposalData={activationProposal}
                        feastStatus={feastStatus}
                        onActivationComplete={handleFeastActivationComplete}
                    />
                </div>
            </div>
        </div>
    );
};

export default AICoach;
