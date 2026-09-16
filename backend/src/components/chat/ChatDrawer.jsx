import React, { useState, useEffect, useRef } from 'react';
import { chatService } from '../../api/chatService';
import { useAuth } from '../../context/AuthContext';
import {
  MessageSquare,
  Send,
  X,
  Loader2,
  RefreshCw,
  User,
  Shield,
  Clock,
  CheckCheck,
  Smile,
  Sparkles,
  Trash2,
  AlertTriangle,
  Info,
} from 'lucide-react';

const QUICK_PROMPTS_PATIENT = [
  'I have taken my scheduled medication.',
  'Can we adjust my dose timing?',
  'I am experiencing slight nausea.',
  'When should I refill my prescription?',
];

const QUICK_PROMPTS_CAREGIVER = [
  'Please remember to take your scheduled dose on time.',
  'How are you feeling after today’s medication?',
  'Please confirm when you have taken your morning dose.',
  'Your adherence looks excellent this week!',
];

export const ChatDrawer = ({ isOpen, onClose, targetUser, currentUser }) => {
  let authUser = null;
  try {
    const auth = useAuth();
    authUser = auth?.user;
  } catch (e) {
    authUser = null;
  }
  const user = currentUser || authUser;

  const [contacts, setContacts] = useState([]);
  const [activeContact, setActiveContact] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [deleteModal, setDeleteModal] = useState(null); // { type: 'message'|'conversation', id: number }
  const [deleting, setDeleting] = useState(false);
  const messagesEndRef = useRef(null);

  const targetId = targetUser?.id || targetUser?.user_id;
  const targetName = targetUser?.name;
  const targetEmpId = targetUser?.employee_id || targetUser?.patient_employee_id || targetUser?.caregiver_employee_id;
  const targetEmail = targetUser?.email;

  // Fetch contacts whenever drawer opens
  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;

    const loadContacts = async () => {
      try {
        const contactList = await chatService.getContacts();
        if (!isMounted) return;
        setContacts(contactList);

        if (targetUser) {
          const tId = targetId;
          const match = contactList.find(
            (c) =>
              (tId && c.user_id === tId) ||
              (targetEmpId && c.employee_id === targetEmpId) ||
              (targetEmail && c.email === targetEmail) ||
              (targetName && c.name === targetName)
          );

          if (match) {
            setActiveContact(match);
          } else if (tId) {
            setActiveContact({
              user_id: tId,
              name: targetName || 'Contact',
              employee_id: targetEmpId,
              role: targetUser.role || (user?.role === 'PATIENT' ? 'CAREGIVER' : 'PATIENT'),
              email: targetEmail,
            });
          } else if (contactList.length > 0) {
            setActiveContact(contactList[0]);
          }
        } else if (contactList.length > 0) {
          setActiveContact((prev) => {
            if (prev && contactList.some((c) => c.user_id === prev.user_id)) {
              return prev;
            }
            return contactList[0];
          });
        }
      } catch (err) {
        console.error('Failed to load contacts:', err);
      }
    };

    loadContacts();

    return () => {
      isMounted = false;
    };
  }, [isOpen, targetId, targetName, targetEmpId, targetEmail]);

  // Load conversation and poll every 1.5 seconds when an active contact is selected
  useEffect(() => {
    if (!isOpen || !activeContact?.user_id) return;

    let isMounted = true;

    const fetchConversation = async (showSpinner = false) => {
      if (showSpinner) setLoading(true);
      try {
        const data = await chatService.getConversation(activeContact.user_id);
        if (isMounted && Array.isArray(data)) {
          setMessages(data);
        }
      } catch (err) {
        console.error('Failed to load messages:', err);
      } finally {
        if (showSpinner && isMounted) setLoading(false);
      }
    };

    fetchConversation(true);

    const interval = setInterval(() => {
      fetchConversation(false);
    }, 1500);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [isOpen, activeContact?.user_id]);

  // Auto-scroll to latest message safely
  useEffect(() => {
    if (typeof messagesEndRef.current?.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleSend = async (e) => {
    if (e) e.preventDefault();
    if (!newMessage.trim() || !activeContact?.user_id || sending) return;

    const textToSend = newMessage.trim();
    setSending(true);
    setErrorMessage(null);

    try {
      const sent = await chatService.sendMessage(activeContact.user_id, textToSend);
      setNewMessage('');
      setMessages((prev) => {
        if (prev.some((m) => m.id === sent.id)) return prev;
        return [...prev, sent];
      });
    } catch (err) {
      console.error('Failed to send message:', err);
      const backendError =
        err.response?.data?.detail?.message ||
        err.response?.data?.detail ||
        err.message ||
        'Failed to send message. Please try again.';
      setErrorMessage(typeof backendError === 'string' ? backendError : JSON.stringify(backendError));
    } finally {
      setSending(false);
    }
  };

  const handleQuickPrompt = (promptText) => {
    setNewMessage(promptText);
  };

  const handleConfirmDelete = async () => {
    if (!deleteModal) return;
    setDeleting(true);
    setErrorMessage(null);

    try {
      if (deleteModal.type === 'message') {
        await chatService.deleteMessage(deleteModal.id);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === deleteModal.id
              ? { ...m, is_deleted: true, message: 'This message was deleted.' }
              : m
          )
        );
      } else if (deleteModal.type === 'conversation') {
        await chatService.deleteConversation(deleteModal.id);
        setMessages([]);
        const updatedContacts = await chatService.getContacts().catch(() => []);
        setContacts(updatedContacts);
      }
      setDeleteModal(null);
    } catch (err) {
      console.error('Failed to delete:', err);
      const backendError =
        err.response?.data?.detail?.message ||
        err.response?.data?.detail ||
        err.message ||
        'Delete operation failed.';
      setErrorMessage(typeof backendError === 'string' ? backendError : JSON.stringify(backendError));
    } finally {
      setDeleting(false);
    }
  };

  if (!isOpen) return null;

  const quickPrompts = user?.role === 'PATIENT' ? QUICK_PROMPTS_PATIENT : QUICK_PROMPTS_CAREGIVER;

  const formatMessageTime = (dateStr) => {
    if (!dateStr) return '';
    let str = typeof dateStr === 'string' ? dateStr : String(dateStr);
    if (!str.endsWith('Z') && !/[+-]\d{2}(:\d{2})?$/.test(str)) {
      str = `${str}Z`;
    }
    const d = new Date(str);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-950/70 backdrop-blur-sm flex justify-end transition-opacity">
      <div
        className="w-full max-w-lg bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col h-full animate-in slide-in-from-right duration-300 relative"
        role="dialog"
        aria-modal="true"
      >
        {/* Drawer Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-teal-500/10 border border-teal-500/20 text-teal-400 flex items-center justify-center relative">
              <MessageSquare className="w-5 h-5" />
              <span className="absolute -top-1 -right-1 flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
              </span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-white flex items-center gap-2">
                  <span>Care Communication Chat</span>
                </h2>
                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  LIVE CHAT
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Direct live messaging between Patient and Caregiver
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {activeContact && (
              <button
                onClick={() =>
                  setDeleteModal({
                    type: 'conversation',
                    id: activeContact.user_id,
                  })
                }
                title="Delete Conversation"
                aria-label="Delete Conversation"
                className="p-2 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={onClose}
              aria-label="Close Chat"
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Contacts Switcher (if multiple contacts exist) */}
        {contacts.length > 1 && (
          <div className="px-4 py-2 bg-slate-950/40 border-b border-slate-800 flex items-center gap-2 overflow-x-auto">
            <span className="text-[10px] uppercase font-bold text-slate-500 shrink-0">Contacts:</span>
            {contacts.map((c) => {
              const isSelected = activeContact?.user_id === c.user_id;
              return (
                <button
                  key={c.user_id}
                  onClick={() => setActiveContact(c)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold shrink-0 transition-all flex items-center gap-1.5 border ${
                    isSelected
                      ? 'bg-teal-500 text-slate-950 border-teal-400 font-bold'
                      : 'bg-slate-800/80 text-slate-300 border-slate-700 hover:bg-slate-700'
                  }`}
                >
                  <span>{c.name}</span>
                  {c.unread_count > 0 && (
                    <span className="w-4 h-4 rounded-full bg-rose-500 text-white text-[10px] flex items-center justify-center">
                      {c.unread_count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}

        {/* Active Contact Information Card */}
        {activeContact ? (
          <div className="px-4 py-3 bg-slate-950/60 border-b border-slate-800/80 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-teal-500/20 text-teal-300 font-bold text-xs flex items-center justify-center border border-teal-500/30">
                {activeContact.name?.charAt(0).toUpperCase()}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-white">{activeContact.name}</span>
                  <span className="font-mono text-[10px] text-teal-400 font-semibold bg-teal-500/10 px-1.5 py-0.5 rounded border border-teal-500/20">
                    {activeContact.employee_id || (activeContact.role === 'PATIENT' ? `PT${String(activeContact.user_id).padStart(6, '0')}` : `CG${String(activeContact.user_id).padStart(6, '0')}`)}
                  </span>
                </div>
                <span className="text-[10px] text-slate-400 block">{activeContact.email}</span>
              </div>
            </div>
            <div className="text-right">
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                Active Contact
              </span>
            </div>
          </div>
        ) : (
          <div className="p-6 text-center text-slate-400 text-xs">
            <p>No active caregiver or patient assignment found.</p>
            <p className="text-[11px] text-slate-500 mt-1">An administrator must first link patient and caregiver accounts.</p>
          </div>
        )}

        {/* Message Thread Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-900/40">
          {loading ? (
            <div className="h-full flex flex-col items-center justify-center gap-2 text-slate-400">
              <Loader2 className="w-6 h-6 animate-spin text-teal-400" />
              <p className="text-xs">Loading conversation history...</p>
            </div>
          ) : !activeContact ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-400">
              <MessageSquare className="w-10 h-10 text-slate-600 mb-2" />
              <p className="text-sm font-semibold text-slate-300">No Authorized Contact</p>
              <p className="text-xs text-slate-500 mt-1 max-w-xs">
                Patients can message their assigned caregiver, and caregivers can message their supervised patients.
              </p>
            </div>
          ) : messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-400">
              <Sparkles className="w-8 h-8 text-teal-400/60 mb-2" />
              <p className="text-sm font-semibold text-slate-300">Start the Conversation</p>
              <p className="text-xs text-slate-500 mt-1 max-w-xs">
                Send a message to <strong>{activeContact.name}</strong> to discuss dosage schedules, health updates, or questions.
              </p>
            </div>
          ) : (
            messages.map((m) => {
              const isMine = m.sender_id === user?.id;
              const isDeleted = m.is_deleted;
              return (
                <div
                  key={m.id}
                  className={`flex flex-col group ${isMine ? 'items-end' : 'items-start'}`}
                >
                  <div className="flex items-center gap-1.5 text-[10px] text-slate-400 mb-1 px-1">
                    <span className="font-semibold">{isMine ? 'You' : m.sender_name}</span>
                    <span className="font-mono text-[9px] text-slate-500">
                      ({m.sender_employee_id || (m.sender_role === 'PATIENT' ? 'PT' : 'CG')})
                    </span>
                    <span>·</span>
                    <span>{formatMessageTime(m.created_at)}</span>
                  </div>

                  <div className="flex items-center gap-1.5 max-w-[85%]">
                    {/* Delete button for sender's own non-deleted message */}
                    {isMine && !isDeleted && (
                      <button
                        onClick={() => setDeleteModal({ type: 'message', id: m.id })}
                        title="Delete message"
                        aria-label="Delete message"
                        className="opacity-0 group-hover:opacity-100 p-1 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-slate-800 transition-all"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}

                    <div
                      className={`rounded-2xl px-4 py-2.5 text-xs leading-relaxed shadow-md ${
                        isDeleted
                          ? 'bg-slate-950/60 border border-slate-800/80 text-slate-500 italic'
                          : isMine
                          ? 'bg-gradient-to-br from-teal-500 to-teal-600 text-slate-950 font-medium rounded-br-none'
                          : 'bg-slate-950 border border-slate-800 text-slate-100 rounded-bl-none'
                      }`}
                    >
                      {m.message}
                    </div>
                  </div>
                </div>
              );
            })
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Suggestion Chips */}
        {activeContact && (
          <div className="px-4 py-2 bg-slate-950/80 border-t border-slate-800/80">
            <div className="flex items-center gap-1.5 mb-1.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
              <Sparkles className="w-3 h-3 text-teal-400" />
              <span>Quick Replies:</span>
            </div>
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
              {quickPrompts.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleQuickPrompt(prompt)}
                  className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-[11px] text-slate-300 hover:text-white whitespace-nowrap transition-colors"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Error Alert Display */}
        {errorMessage && (
          <div className="px-4 py-2 bg-rose-500/10 border-t border-rose-500/20 text-rose-400 text-xs flex items-center justify-between">
            <span>{errorMessage}</span>
            <button
              onClick={() => setErrorMessage(null)}
              aria-label="Dismiss Error"
              className="text-rose-400 hover:text-rose-300 p-0.5"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Input Bar */}
        {activeContact && (
          <form
            onSubmit={handleSend}
            className="p-4 bg-slate-950 border-t border-slate-800 flex items-center gap-2"
          >
            <input
              type="text"
              required
              placeholder={`Message ${activeContact.name}...`}
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500/30 transition-all"
            />
            <button
              type="submit"
              disabled={sending || !newMessage.trim()}
              className="px-4 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 shadow-lg shadow-teal-500/10 shrink-0"
            >
              {sending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <span>Send</span>
                  <Send className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </form>
        )}

        {/* Confirmation Modal for Delete Message / Delete Conversation */}
        {deleteModal && (
          <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-20 animate-in fade-in-50">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 max-w-sm w-full shadow-2xl space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center shrink-0">
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">
                    {deleteModal.type === 'message' ? 'Delete this message?' : 'Delete this conversation?'}
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {deleteModal.type === 'message'
                      ? 'This message will be marked as deleted.'
                      : 'Your medication and patient records will not be affected.'}
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-2">
                <button
                  onClick={() => setDeleteModal(null)}
                  disabled={deleting}
                  className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmDelete}
                  disabled={deleting}
                  className="px-3.5 py-1.5 rounded-xl bg-rose-500 hover:bg-rose-400 text-white text-xs font-bold transition-colors flex items-center gap-1.5 disabled:opacity-50"
                >
                  {deleting ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Trash2 className="w-3.5 h-3.5" />
                  )}
                  <span>{deleteModal.type === 'message' ? 'Delete Message' : 'Delete Conversation'}</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatDrawer;

