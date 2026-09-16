import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Globe, Check, ChevronDown } from 'lucide-react';
import { SUPPORTED_LANGUAGES, STORAGE_KEY } from '../../i18n';
import { useAuth } from '../../context/AuthContext';

export const LanguageSelector = ({ variant = 'default', className = '' }) => {
  const { i18n, t } = useTranslation();
  const { user, updateProfile } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const dropdownRef = useRef(null);

  const rawLangCode = (i18n.resolvedLanguage || i18n.language || 'en');
  const currentLangCode = rawLangCode.split('-')[0].split('_')[0].toLowerCase();
  const currentLang = SUPPORTED_LANGUAGES.find((l) => l.code === currentLangCode) || SUPPORTED_LANGUAGES[0];

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLanguageSelect = async (langCode) => {
    if (langCode === currentLangCode) {
      setIsOpen(false);
      return;
    }

    try {
      setIsSaving(true);
      // 1. Immediately apply the language change in i18next
      await i18n.changeLanguage(langCode);

      // 2. Persist in client localStorage
      try {
        localStorage.setItem(STORAGE_KEY, langCode);
      } catch {
        // Ignore localStorage error
      }

      // 3. Asynchronously persist to backend user profile if authenticated (non-blocking)
      if (user && updateProfile) {
        updateProfile({ language: langCode }).catch((err) => {
          console.warn('Backend language persistence failed (continuing with local language):', err);
        });
      }
    } catch (err) {
      console.error('Failed to change language:', err);
    } finally {
      setIsSaving(false);
      setIsOpen(false);
    }
  };

  // Compact Header / Nav bar variant
  if (variant === 'compact') {
    return (
      <div className={`relative ${className}`} ref={dropdownRef}>
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          aria-expanded={isOpen}
          aria-label={t('settings.language')}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/60 text-slate-200 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-teal-500/30"
        >
          <Globe className="w-3.5 h-3.5 text-teal-400" />
          <span>{currentLang.nativeName}</span>
          <ChevronDown className={`w-3 h-3 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {isOpen && (
          <div className="absolute right-0 mt-2 w-52 bg-slate-900 border border-slate-800 rounded-2xl shadow-xl py-1.5 z-50 animate-in fade-in slide-in-from-top-2 duration-150 max-h-72 overflow-y-auto scrollbar-thin">
            <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800/60">
              {t('settings.language')}
            </div>
            {SUPPORTED_LANGUAGES.map((lang) => {
              const isSelected = lang.code === currentLangCode;
              return (
                <button
                  key={lang.code}
                  type="button"
                  onClick={() => handleLanguageSelect(lang.code)}
                  className={`w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-left transition-colors ${
                    isSelected
                      ? 'bg-teal-500/10 text-teal-300 font-semibold'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <span className="text-slate-200">{lang.label}</span>
                  </span>
                  {isSelected && <Check className="w-3.5 h-3.5 text-teal-400 shrink-0" />}
                </button>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // Default Settings / Dashboard section variant
  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <div className="relative">
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          aria-expanded={isOpen}
          aria-label={t('settings.language')}
          className="w-full flex items-center justify-between px-4 py-3 bg-slate-900/80 hover:bg-slate-800/80 border border-slate-700/60 rounded-xl text-slate-200 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-teal-500/30"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400">
              <Globe className="w-4 h-4" />
            </div>
            <div className="text-left">
              <div className="text-xs text-slate-400">{t('settings.language')}</div>
              <div className="text-sm font-semibold text-white">{currentLang.label}</div>
            </div>
          </div>
          <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {isOpen && (
          <div className="absolute left-0 right-0 mt-2 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl py-2 z-50 animate-in fade-in slide-in-from-top-2 duration-150 max-h-80 overflow-y-auto scrollbar-thin">
            {SUPPORTED_LANGUAGES.map((lang) => {
              const isSelected = lang.code === currentLangCode;
              return (
                <button
                  key={lang.code}
                  type="button"
                  onClick={() => handleLanguageSelect(lang.code)}
                  className={`w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-left transition-colors ${
                    isSelected
                      ? 'bg-teal-500/15 text-teal-300 font-bold border-l-2 border-teal-400'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <span className="text-sm font-semibold">{lang.label}</span>
                  </div>
                  {isSelected && <Check className="w-4 h-4 text-teal-400 shrink-0" />}
                </button>
              );
            })}
          </div>
        )}
      </div>
      {isSaving && (
        <p className="text-[11px] text-teal-400 mt-1.5 animate-pulse">{t('common.saving')}</p>
      )}
    </div>
  );
};

export default LanguageSelector;
