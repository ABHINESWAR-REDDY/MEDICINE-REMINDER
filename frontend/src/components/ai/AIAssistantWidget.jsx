import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../context/AuthContext';
import { aiService } from '../../api/aiService';
import FormattedMessage from './FormattedMessage';
import {
  Bot,
  Sparkles,
  Send,
  X,
  Minimize2,
  Maximize2,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  Info,
  Check,
  Copy,
  Trash2,
  Loader2,
  Pill,
  ChevronDown,
  ChevronUp,
  HelpCircle,
  Stethoscope,
  Activity,
  HeartPulse,
} from 'lucide-react';

export const AIAssistantWidget = () => {
  const { t, i18n } = useTranslation();
  const { user, isAuthenticated } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [expandedSources, setExpandedSources] = useState({});
  const [suggestedCategories, setSuggestedCategories] = useState([]);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Initial welcome message
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([
        {
          role: 'assistant',
          content: `Hello ${user?.name ? user.name : 'there'}! 👋 I am your **PillSync Healthcare & Medication AI Assistant**.\n\nI can help you with:\n- 💊 **Tablet Indications**: Which medicine is used for which health condition\n- ⚖️ **Dosage & Administration**: Standard dosing guidelines, food timing, and precautions\n- 🔬 **Drug Interactions**: Cross-checking combinations and adverse side effects\n- 📸 **Prescription OCR & Reminders**: Navigating PillSync features and schedules\n\nAll clinical answers are verified against authoritative medical sources (**FDA, MedlinePlus, DailyMed, NHS**). How can I assist your health journey today?`,
          verification: null,
          suggested_prompts: [
            'Which tablet can be used for headache or mild fever?',
            'What is Metformin used for and how does it manage blood glucose?',
            'What is the standard dosage for Paracetamol 500mg?',
            'Can I take my active PillSync medications together?',
            'How do I scan a doctor\'s prescription with OCR?'
          ],
        },
      ]);
    }
  }, [user?.name, messages.length]);

  // Fetch suggested questions once
  useEffect(() => {
    const fetchSuggestions = async () => {
      try {
        const res = await aiService.getSuggestions();
        if (res && res.categories) {
          setSuggestedCategories(res.categories);
        }
      } catch (err) {
        // Fallback silently
      }
    };
    if (isAuthenticated) {
      fetchSuggestions();
    }
  }, [isAuthenticated]);

  // Auto scroll to bottom
  useEffect(() => {
    if (isOpen && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading, isOpen]);

  // Auto focus input on open
  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen]);

  const handleSendMessage = async (textToSend = null) => {
    const query = (textToSend || inputMessage).trim();
    if (!query || loading) return;

    const userMsg = {
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setLoading(true);

    try {
      // Build history excluding greeting
      const historyPayload = messages
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .map((m) => ({ role: m.role, content: m.content }));

      const response = await aiService.sendMessage(query, historyPayload, true, null, i18n.language);

      const assistantMsg = {
        role: 'assistant',
        content: response.message,
        is_medical: response.is_medical,
        is_out_of_scope: response.is_out_of_scope,
        is_emergency: response.is_emergency,
        verification: response.verification,
        suggested_prompts: response.suggested_prompts || [],
        disclaimer: response.disclaimer,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      console.error('AI Chat error:', err);
      const errorText =
        err.response?.data?.detail?.message ||
        err.response?.data?.detail ||
        'Unable to connect to AI Assistant. Please verify network connectivity and try again.';

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `⚠️ **Connection Error**: ${typeof errorText === 'string' ? errorText : JSON.stringify(errorText)}`,
          suggested_prompts: [
            'Which tablet can be used for headache?',
            'What is the dosage for Paracetamol 500mg?',
            'How do I scan a prescription with OCR?'
          ],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleCopyMessage = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const toggleSources = (idx) => {
    setExpandedSources((prev) => ({
      ...prev,
      [idx]: !prev[idx],
    }));
  };

  const handleClearChat = () => {
    setMessages([
      {
        role: 'assistant',
        content: `Chat history cleared. What healthcare or medication question would you like to explore?`,
        verification: null,
        suggested_prompts: [
          'Which tablet can be used for headache or mild fever?',
          'What is Metformin used for and how does it work?',
          'Can I take my current medications together?',
          'How do I upload a prescription?'
        ],
      },
    ]);
  };

  if (!isAuthenticated) return null;

  return (
    <>
      {/* Floating Trigger Button */}
      {!isOpen && (
        <div className="fixed bottom-6 right-6 z-40">
          <button
            onClick={() => setIsOpen(true)}
            aria-label="Open PillSync AI Healthcare Assistant"
            className="group relative flex items-center gap-2.5 px-4 py-3 bg-gradient-to-r from-teal-500 via-teal-600 to-emerald-600 text-slate-950 font-bold text-xs rounded-2xl shadow-xl shadow-teal-500/25 hover:shadow-teal-500/40 hover:scale-105 active:scale-95 transition-all duration-200 border border-teal-300/40"
          >
            <div className="relative">
              <Sparkles className="w-4 h-4 animate-spin-slow text-slate-950" />
              <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-300 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-400"></span>
              </span>
            </div>
            <span className="tracking-wide">AI Healthcare Assistant</span>
            <span className="text-[10px] bg-slate-950/20 text-slate-950 font-bold px-1.5 py-0.5 rounded-full uppercase tracking-wider">
              Verified
            </span>
          </button>
        </div>
      )}

      {/* Interactive AI Assistant Modal / Drawer */}
      {isOpen && (
        <div
          className={`fixed z-50 transition-all duration-300 ${
            isMaximized
              ? 'inset-3 sm:inset-6 max-w-none'
              : 'bottom-4 right-4 sm:bottom-6 sm:right-6 w-full max-w-lg h-[620px] max-h-[88vh]'
          } bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in-50 zoom-in-95`}
          role="dialog"
          aria-label="PillSync AI Healthcare Assistant"
        >
          {/* Header */}
          <div className="p-4 bg-slate-950 border-b border-slate-800 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-teal-500/20 to-emerald-500/20 border border-teal-500/30 flex items-center justify-center text-teal-400 relative">
                <Bot className="w-5 h-5" />
                <span className="absolute -top-1 -right-1 flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-teal-500"></span>
                </span>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-bold text-white tracking-tight">PillSync AI Assistant</h2>
                  <span className="inline-flex items-center gap-1 text-[10px] font-bold text-teal-400 bg-teal-500/10 px-2 py-0.5 rounded-full border border-teal-500/20">
                    <ShieldCheck className="w-3 h-3 text-teal-400" />
                    FDA & NLM Verified
                  </span>
                </div>
                <p className="text-[11px] text-slate-400">
                  Clinical medication education & prescription guidance
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={handleClearChat}
                title="Clear conversation"
                aria-label="Clear conversation"
                className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setIsMaximized(!isMaximized)}
                title={isMaximized ? 'Restore size' : 'Maximize'}
                aria-label={isMaximized ? 'Restore size' : 'Maximize'}
                className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors hidden sm:block"
              >
                {isMaximized ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </button>
              <button
                onClick={() => setIsOpen(false)}
                title="Close"
                aria-label="Close Assistant"
                className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* User Context Banner */}
          <div className="px-4 py-2 bg-slate-950/60 border-b border-slate-800/80 flex items-center justify-between text-[11px]">
            <div className="flex items-center gap-2 text-teal-400 font-medium">
              <Activity className="w-3.5 h-3.5" />
              <span>Personalized PillSync patient context connected</span>
            </div>
            <span className="text-slate-500 text-[10px]">Gemini 3.6 Flash</span>
          </div>

          {/* Messages Feed */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-900/50">
            {messages.map((msg, idx) => {
              const isAssistant = msg.role === 'assistant';
              const isCopied = copiedIndex === idx;
              const hasSources = msg.verification && msg.verification.sources && msg.verification.sources.length > 0;
              const isSourcesOpen = expandedSources[idx];

              return (
                <div
                  key={idx}
                  className={`flex flex-col ${isAssistant ? 'items-start' : 'items-end'} animate-in fade-in-50`}
                >
                  <div className="flex items-center gap-1.5 text-[10px] text-slate-400 mb-1 px-1">
                    {isAssistant ? (
                      <>
                        <Sparkles className="w-3 h-3 text-teal-400" />
                        <span className="font-semibold text-teal-300">PillSync Healthcare AI</span>
                      </>
                    ) : (
                      <>
                        <span className="font-semibold text-slate-300">You</span>
                      </>
                    )}
                  </div>

                  <div className="max-w-[92%] sm:max-w-[85%] group relative">
                    <div
                      className={`p-4 rounded-2xl text-xs leading-relaxed shadow-md ${
                        isAssistant
                          ? msg.is_emergency
                            ? 'bg-rose-950/50 border border-rose-500/40 text-rose-100 rounded-tl-none'
                            : msg.is_out_of_scope
                            ? 'bg-amber-950/30 border border-amber-500/30 text-amber-100 rounded-tl-none'
                            : 'bg-slate-950 border border-slate-800 text-slate-100 rounded-tl-none'
                          : 'bg-gradient-to-br from-teal-500 to-teal-600 text-slate-950 font-medium rounded-tr-none'
                      }`}
                    >
                      {/* Formatted Markdown rendering with rich tables & badges */}
                      {isAssistant ? (
                        <FormattedMessage
                          content={msg.content}
                          isEmergency={msg.is_emergency}
                          isOutOfScope={msg.is_out_of_scope}
                        />
                      ) : (
                        <p className="text-slate-950 font-medium text-xs sm:text-sm whitespace-pre-wrap">
                          {msg.content}
                        </p>
                      )}

                      {/* Verified Sources Accordion */}
                      {isAssistant && hasSources && (
                        <div className="mt-3 pt-3 border-t border-slate-800">
                          <button
                            type="button"
                            onClick={() => toggleSources(idx)}
                            className="w-full flex items-center justify-between p-2 rounded-xl bg-slate-900/80 hover:bg-slate-900 border border-slate-800 text-[11px] font-semibold text-teal-400 transition-colors"
                          >
                            <div className="flex items-center gap-1.5">
                              <ShieldCheck className="w-3.5 h-3.5 text-teal-400" />
                              <span>
                                Verified against {msg.verification.sources.length}{' '}
                                {msg.verification.sources.length === 1 ? 'medical source' : 'medical sources'}
                              </span>
                              <span className="text-[9px] bg-teal-500/20 text-teal-300 px-1.5 py-0.2 rounded font-mono">
                                {msg.verification.evidence_status}
                              </span>
                            </div>
                            {isSourcesOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                          </button>

                          {isSourcesOpen && (
                            <div className="mt-2 space-y-2 animate-in fade-in-50">
                              {msg.verification.sources.map((src, sIdx) => (
                                <div
                                  key={sIdx}
                                  className="p-2.5 rounded-xl bg-slate-900 border border-slate-800/80 text-[11px] space-y-1"
                                >
                                  <div className="flex items-center justify-between gap-2">
                                    <span className="font-bold text-white flex items-center gap-1">
                                      <Check className="w-3 h-3 text-emerald-400" />
                                      {src.name}
                                    </span>
                                    <a
                                      href={src.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-teal-400 hover:text-teal-300 inline-flex items-center gap-1 text-[10px] font-semibold"
                                    >
                                      <span>Official Source</span>
                                      <ExternalLink className="w-2.5 h-2.5" />
                                    </a>
                                  </div>
                                  <p className="text-slate-400 text-[10px] leading-relaxed">
                                    {src.relevant_excerpt}
                                  </p>
                                  <span className="text-[9px] text-slate-500 block">
                                    Verified: {src.retrieval_timestamp}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Disclaimer footer */}
                      {isAssistant && msg.disclaimer && (
                        <div className="mt-2 pt-2 border-t border-slate-800/60 text-[10px] text-slate-500 flex items-start gap-1">
                          <Info className="w-3 h-3 text-slate-500 shrink-0 mt-0.5" />
                          <span>{msg.disclaimer}</span>
                        </div>
                      )}
                    </div>

                    {/* Copy Button */}
                    {isAssistant && (
                      <button
                        onClick={() => handleCopyMessage(msg.content, idx)}
                        title="Copy message"
                        className="opacity-0 group-hover:opacity-100 absolute -bottom-3 right-2 p-1 rounded-lg bg-slate-800 text-slate-400 hover:text-white border border-slate-700 shadow transition-all text-[10px] flex items-center gap-1"
                      >
                        {isCopied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        <span>{isCopied ? 'Copied' : 'Copy'}</span>
                      </button>
                    )}
                  </div>

                  {/* Predefined Interactive Suggested Prompts Chips */}
                  {isAssistant && msg.suggested_prompts && msg.suggested_prompts.length > 0 && (
                    <div className="mt-2.5 w-full pl-2">
                      <div className="text-[10px] font-semibold text-slate-400 flex items-center gap-1 mb-1.5">
                        <Sparkles className="w-3 h-3 text-teal-400" />
                        <span>Suggested Follow-ups:</span>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {msg.suggested_prompts.map((prompt, pIdx) => (
                          <button
                            key={pIdx}
                            onClick={() => handleSendMessage(prompt)}
                            className="px-2.5 py-1.5 rounded-xl bg-slate-950 hover:bg-slate-800 border border-slate-800 hover:border-teal-500/40 text-[11px] text-slate-300 hover:text-white text-left transition-all active:scale-95 shadow-sm"
                          >
                            {prompt}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}

            {/* Loading Indicator */}
            {loading && (
              <div className="flex items-start gap-2 animate-in fade-in-50">
                <div className="w-8 h-8 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400 flex items-center justify-center">
                  <Loader2 className="w-4 h-4 animate-spin" />
                </div>
                <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 text-slate-300 text-xs flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse"></span>
                  <span>Searching FDA & MedlinePlus authoritative sources...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Predefined Categories Dock */}
          {messages.length <= 2 && suggestedCategories.length > 0 && (
            <div className="px-4 py-2 bg-slate-950/80 border-t border-slate-800/80 overflow-x-auto flex gap-2">
              {suggestedCategories.map((cat, cIdx) => (
                <button
                  key={cIdx}
                  onClick={() => handleSendMessage(cat.questions[0])}
                  className="px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-[10px] font-semibold text-teal-300 whitespace-nowrap transition-colors flex items-center gap-1.5 shrink-0"
                >
                  <Pill className="w-3 h-3 text-teal-400" />
                  <span>{cat.category}</span>
                </button>
              ))}
            </div>
          )}

          {/* Input Bar */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="p-3.5 bg-slate-950 border-t border-slate-800 flex items-center gap-2 shrink-0"
          >
            <input
              ref={inputRef}
              type="text"
              required
              placeholder="Ask tablet uses, dosages, side effects, or OCR..."
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500/30 transition-all"
            />
            <button
              type="submit"
              disabled={loading || !inputMessage.trim()}
              className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-teal-500 to-teal-600 hover:from-teal-400 hover:to-teal-500 text-slate-950 font-bold text-xs transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 shadow-lg shadow-teal-500/20 shrink-0"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <span className="hidden sm:inline">Ask AI</span>
                  <Send className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </form>
        </div>
      )}
    </>
  );
};

export default AIAssistantWidget;
