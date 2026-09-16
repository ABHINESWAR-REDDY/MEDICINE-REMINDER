import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import en from './locales/en.json';
import hi from './locales/hi.json';
import te from './locales/te.json';
import ta from './locales/ta.json';
import kn from './locales/kn.json';
import ml from './locales/ml.json';
import mr from './locales/mr.json';
import bn from './locales/bn.json';
import gu from './locales/gu.json';
import pa from './locales/pa.json';
import or from './locales/or.json';

export const SUPPORTED_LANGUAGES = [
  { code: 'en', name: 'English', nativeName: 'English', label: 'English' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी', label: 'हिन्दी (Hindi)' },
  { code: 'te', name: 'Telugu', nativeName: 'తెలుగు', label: 'తెలుగు (Telugu)' },
  { code: 'ta', name: 'Tamil', nativeName: 'தமிழ்', label: 'தமிழ் (Tamil)' },
  { code: 'kn', name: 'Kannada', nativeName: 'ಕನ್ನಡ', label: 'ಕನ್ನಡ (Kannada)' },
  { code: 'ml', name: 'Malayalam', nativeName: 'മലയാളം', label: 'മലയാളം (Malayalam)' },
  { code: 'mr', name: 'Marathi', nativeName: 'मराठी', label: 'मराठी (Marathi)' },
  { code: 'bn', name: 'Bengali', nativeName: 'বাংলা', label: 'বাংলা (Bengali)' },
  { code: 'gu', name: 'Gujarati', nativeName: 'ગુજરાતી', label: 'ગુજરાતી (Gujarati)' },
  { code: 'pa', name: 'Punjabi', nativeName: 'ਪੰਜਾਬੀ', label: 'ਪੰਜਾਬੀ (Punjabi)' },
  { code: 'or', name: 'Odia', nativeName: 'ଓଡ଼ିଆ', label: 'ଓଡ଼ିଆ (Odia)' },
];

export const STORAGE_KEY = 'pillsync_language';

const getInitialLanguage = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && SUPPORTED_LANGUAGES.some((lang) => lang.code === saved)) {
      return saved;
    }
    const browserLang = navigator.language?.split('-')[0]?.toLowerCase();
    if (browserLang && SUPPORTED_LANGUAGES.some((lang) => lang.code === browserLang)) {
      return browserLang;
    }
  } catch {
    // Fallback if localStorage or navigator is unavailable
  }
  return 'en';
};

const resources = {
  en: { translation: en },
  hi: { translation: hi },
  te: { translation: te },
  ta: { translation: ta },
  kn: { translation: kn },
  ml: { translation: ml },
  mr: { translation: mr },
  bn: { translation: bn },
  gu: { translation: gu },
  pa: { translation: pa },
  or: { translation: or },
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: getInitialLanguage(),
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false, // React already escapes values
    },
    react: {
      useSuspense: false,
    },
  });

export default i18n;
