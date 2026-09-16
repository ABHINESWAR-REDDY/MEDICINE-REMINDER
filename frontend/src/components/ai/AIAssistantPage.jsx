import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../context/AuthContext';
import { aiService } from '../../api/aiService';
import { medicationService } from '../../api/medicationService';
import FormattedMessage from './FormattedMessage';
import {
  Bot,
  Sparkles,
  Send,
  ExternalLink,
  ShieldCheck,
  Info,
  Check,
  Copy,
  Trash2,
  Loader2,
  Pill,
  ChevronDown,
  ChevronUp,
  Activity,
  Download,
  Search,
  BookOpen,
  Scale,
  ShieldAlert,
  CalendarCheck,
  RefreshCw
} from 'lucide-react';

export const AIAssistantPage = () => {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [expandedSources, setExpandedSources] = useState({});
  const [categories, setCategories] = useState([]);
  const [patientMeds, setPatientMeds] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Initialize messages
  useEffect(() => {
    setMessages([
      {
        role: 'assistant',
        content: `Welcome to the **PillSync AI Healthcare & Clinical Assistant Studio**, ${user?.name || 'User'}! 🩺\n\nI provide **clinically verified medication guidance**, tablet indications, safe dosage ranges, and drug interaction analysis grounded directly on authoritative medical sources (**U.S. FDA, MedlinePlus / NLM, DailyMed, and NHS UK**).\n\nSelect a topic from the left sidebar or ask any specific medication or prescription question below!`,
        verification: null,
        suggested_prompts: [
          'Which tablet can be used for acute headache or fever?',
          'What is Metformin used for in type 2 diabetes management?',
          'What is the standard adult dosage guideline for Paracetamol 500mg?',
          'Can I take my active PillSync medications together?',
          'How do I scan a doctor\'s prescription with OCR?'
        ],
      },
    ]);
  }, [user?.name]);

  // Fetch categorized prompts and patient medications
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const [suggRes, medsRes] = await Promise.all([
          aiService.getSuggestions().catch(() => null),
          medicationService.getMedicines().catch(() => []),
        ]);

        if (suggRes?.categories) {
          setCategories(suggRes.categories);
          setSelectedCategory(suggRes.categories[0]);
        }
        if (Array.isArray(medsRes)) {
          setPatientMeds(medsRes.filter((m) => m.is_active));
        }
      } catch (err) {
        console.error('Error loading initial data:', err);
      }
    };
    loadInitialData();
  }, []);

  // Auto scroll to bottom
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading]);

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
      console.error('AI Chat Error:', err);
      const errorText =
        err.response?.data?.detail?.message ||
        err.response?.data?.detail ||
        'Unable to complete request. Please verify network connectivity and try again.';

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `⚠️ **Connection Error**: ${typeof errorText === 'string' ? errorText : JSON.stringify(errorText)}`,
          suggested_prompts: [
            'Which tablet can be used for fever?',
            'What is the dosage for Paracetamol 500mg?',
            'How do I scan a prescription with OCR?'
          ],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (text, idx) => {
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

  const handleExportTranscript = () => {
    const lines = messages.map((m) => {
      const roleName = m.role === 'assistant' ? 'PillSync Healthcare AI' : (user?.name || 'User');
      return `[${m.timestamp || new Date().toISOString()}] ${roleName}:\n${m.content}\n\n`;
    });
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `pillsync-ai-transcript-${new Date().toISOString().slice(0, 10)}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const getCategoryIcon = (name) => {
    switch (name) {
      case 'Tablet Uses & Disease Indications':
        return <Pill className="w-4 h-4 text-teal-400" />;
      case 'Dosages & Safe Administration':
        return <Scale className="w-4 h-4 text-emerald-400" />;
      case 'Drug Interactions & Side Effects':
        return <ShieldAlert className="w-4 h-4 text-amber-400" />;
      default:
        return <Sparkles className="w-4 h-4 text-purple-400" />;
    }
  };

  return (
    <div className="flex flex-col lg:flex-row gap-6 max-w-7xl mx-auto h-[calc(100vh-140px)] min-h-[600px]">
      {/* Left Sidebar: Categories & Patient Regimen */}
      <div className="w-full lg:w-80 flex flex-col gap-4 shrink-0 overflow-y-auto pr-1">
        {/* Assistant Profile Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-xl space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-teal-500/20 to-emerald-500/20 border border-teal-500/30 flex items-center justify-center text-teal-400">
              <Bot className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">AI Clinical Assistant</h2>
              <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                <ShieldCheck className="w-3 h-3 text-emerald-400" />
                Multi-Source Verified
              </span>
            </div>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Medication intelligence engine powered by Google Gemini 3.6 Flash & official regulatory clinical databases (FDA, MedlinePlus, DailyMed, NHS).
          </p>
        </div>

        {/* Connected Patient Regimen Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-4 shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-bold text-white">
              <Activity className="w-4 h-4 text-teal-400" />
              <span>Your Active Medications</span>
            </div>
            <span className="text-[10px] bg-teal-500/10 text-teal-300 font-bold px-2 py-0.5 rounded-full">
              {patientMeds.length} Active
            </span>
          </div>

          {patientMeds.length === 0 ? (
            <p className="text-xs text-slate-500 italic">No active medications registered in PillSync.</p>
          ) : (
            <div className="space-y-1.5 max-h-36 overflow-y-auto">
              {patientMeds.map((med) => (
                <button
                  key={med.id}
                  onClick={() => handleSendMessage(`What is ${med.name} used for and what are its key precautions?`)}
                  className="w-full text-left p-2 rounded-xl bg-slate-950/70 hover:bg-slate-800 border border-slate-800/80 text-xs flex items-center justify-between group transition-colors"
                >
                  <span className="font-semibold text-slate-200 group-hover:text-teal-300 truncate">
                    {med.name}
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {med.dosage_amount}{med.dosage_unit}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Categorized Prompt Explorer */}
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-4 shadow-xl flex-1 flex flex-col space-y-3">
          <div className="flex items-center gap-2 text-xs font-bold text-white">
            <BookOpen className="w-4 h-4 text-teal-400" />
            <span>Predefined Topic Questions</span>
          </div>

          <div className="space-y-2 flex-1 overflow-y-auto">
            {categories.map((cat, idx) => (
              <div key={idx} className="space-y-1.5">
                <div className="flex items-center gap-2 text-[11px] font-bold text-slate-300 px-1 pt-1">
                  {getCategoryIcon(cat.category)}
                  <span>{cat.category}</span>
                </div>
                <div className="space-y-1 pl-2">
                  {cat.questions.map((q, qIdx) => (
                    <button
                      key={qIdx}
                      onClick={() => handleSendMessage(q)}
                      className="w-full text-left p-2 rounded-xl bg-slate-950/50 hover:bg-slate-800 text-[11px] text-slate-400 hover:text-white transition-colors block border border-transparent hover:border-slate-700"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right: Main Conversation Studio */}
      <div className="flex-1 bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl flex flex-col overflow-hidden min-h-[500px]">
        {/* Studio Header */}
        <div className="p-4 bg-slate-950 border-b border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-3 h-3 rounded-full bg-emerald-400 animate-pulse"></div>
            <span className="text-xs font-bold text-white">Live AI Healthcare Consultation</span>
            <span className="text-[10px] text-slate-500 font-mono hidden sm:inline">| Gemini 3.6 Flash</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleExportTranscript}
              title="Export chat transcript"
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-slate-300 font-semibold flex items-center gap-1.5 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Export</span>
            </button>
            <button
              onClick={() => setMessages([])}
              title="Clear transcript"
              className="p-2 rounded-xl bg-slate-800 hover:bg-rose-500/20 text-slate-400 hover:text-rose-300 border border-slate-700 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Message Feed */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 bg-slate-900/40">
          {messages.map((msg, idx) => {
            const isAssistant = msg.role === 'assistant';
            const isCopied = copiedIndex === idx;
            const hasSources = msg.verification?.sources?.length > 0;
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
                    <span className="font-semibold text-slate-300">You</span>
                  )}
                </div>

                <div className="max-w-[95%] sm:max-w-[85%] group relative">
                  <div
                    className={`p-4 sm:p-5 rounded-2xl text-xs leading-relaxed shadow-lg ${
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
                      <div className="mt-4 pt-3 border-t border-slate-800">
                        <button
                          type="button"
                          onClick={() => toggleSources(idx)}
                          className="w-full flex items-center justify-between p-2.5 rounded-xl bg-slate-900/90 hover:bg-slate-900 border border-slate-800 text-xs font-semibold text-teal-400 transition-colors"
                        >
                          <div className="flex items-center gap-2">
                            <ShieldCheck className="w-4 h-4 text-teal-400" />
                            <span>
                              Verified against {msg.verification.sources.length} authoritative medical sources
                            </span>
                            <span className="text-[10px] bg-teal-500/20 text-teal-300 px-2 py-0.5 rounded font-mono">
                              {msg.verification.evidence_status}
                            </span>
                          </div>
                          {isSourcesOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>

                        {isSourcesOpen && (
                          <div className="mt-2.5 space-y-2.5 animate-in fade-in-50">
                            {msg.verification.sources.map((src, sIdx) => (
                              <div
                                key={sIdx}
                                className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-xs space-y-1.5"
                              >
                                <div className="flex items-center justify-between gap-2">
                                  <span className="font-bold text-white flex items-center gap-1.5">
                                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                                    {src.name}
                                  </span>
                                  <a
                                    href={src.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-teal-400 hover:text-teal-300 inline-flex items-center gap-1 text-[11px] font-semibold"
                                  >
                                    <span>Official Monograph</span>
                                    <ExternalLink className="w-3 h-3" />
                                  </a>
                                </div>
                                <p className="text-slate-400 text-[11px] leading-relaxed">
                                  {src.relevant_excerpt}
                                </p>
                                <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1">
                                  <span>{src.publication_date || 'Official Health Authority'}</span>
                                  <span>Verified: {src.retrieval_timestamp}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Disclaimer Footer */}
                    {isAssistant && msg.disclaimer && (
                      <div className="mt-3 pt-2.5 border-t border-slate-800/70 text-[10px] text-slate-500 flex items-start gap-1.5">
                        <Info className="w-3.5 h-3.5 text-slate-500 shrink-0 mt-0.5" />
                        <span>{msg.disclaimer}</span>
                      </div>
                    )}
                  </div>

                  {/* Copy Button */}
                  {isAssistant && (
                    <button
                      onClick={() => handleCopy(msg.content, idx)}
                      title="Copy response"
                      className="opacity-0 group-hover:opacity-100 absolute -bottom-3 right-2 p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white border border-slate-700 shadow transition-all text-xs flex items-center gap-1"
                    >
                      {isCopied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      <span>{isCopied ? 'Copied' : 'Copy'}</span>
                    </button>
                  )}
                </div>

                {/* Follow up Prompts */}
                {isAssistant && msg.suggested_prompts && msg.suggested_prompts.length > 0 && (
                  <div className="mt-3 w-full pl-2">
                    <div className="text-[10px] font-semibold text-slate-400 flex items-center gap-1 mb-1.5">
                      <Sparkles className="w-3 h-3 text-teal-400" />
                      <span>Suggested Follow-ups:</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {msg.suggested_prompts.map((p, pIdx) => (
                        <button
                          key={pIdx}
                          onClick={() => handleSendMessage(p)}
                          className="px-3 py-1.5 rounded-xl bg-slate-950 hover:bg-slate-800 border border-slate-800 hover:border-teal-500/40 text-xs text-slate-300 hover:text-white transition-all shadow-sm active:scale-95"
                        >
                          {p}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {/* Loading state */}
          {loading && (
            <div className="flex items-start gap-2.5 animate-in fade-in-50">
              <div className="w-9 h-9 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400 flex items-center justify-center">
                <Loader2 className="w-4 h-4 animate-spin" />
              </div>
              <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 text-slate-300 text-xs flex items-center gap-2.5">
                <span className="w-2.5 h-2.5 rounded-full bg-teal-400 animate-pulse"></span>
                <span>Searching FDA, MedlinePlus & NLM databases and cross-checking clinical evidence...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="p-4 bg-slate-950 border-t border-slate-800 flex items-center gap-3 shrink-0"
        >
          <input
            ref={inputRef}
            type="text"
            required
            placeholder={t('aiAssistant.placeholder')}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            className="flex-1 bg-slate-900 border border-slate-800 rounded-2xl px-5 py-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500/30 transition-all"
          />
          <button
            type="submit"
            disabled={loading || !inputMessage.trim()}
            className="px-6 py-3 rounded-2xl bg-gradient-to-r from-teal-500 to-teal-600 hover:from-teal-400 hover:to-teal-500 text-slate-950 font-bold text-xs transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2 shadow-xl shadow-teal-500/20 shrink-0"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <span>{t('aiAssistant.send')}</span>
                <Send className="w-4 h-4" />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

export default AIAssistantPage;
