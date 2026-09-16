import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import i18n, { SUPPORTED_LANGUAGES, STORAGE_KEY } from './index';
import LanguageSelector from '../components/common/LanguageSelector';
import { AuthProvider } from '../context/AuthContext';
import authService from '../api/authService';
import profileService from '../api/profileService';

vi.mock('../api/authService', () => ({
  default: {
    getMe: vi.fn(),
  },
  authService: {
    getMe: vi.fn(),
  },
}));

vi.mock('../api/profileService', () => ({
  default: {
    getProfile: vi.fn(),
    updateProfile: vi.fn(),
  },
  profileService: {
    getProfile: vi.fn(),
    updateProfile: vi.fn(),
  },
}));

describe('PillSync Centralized Multi-Language & i18n System', () => {
  beforeEach(async () => {
    localStorage.clear();
    await i18n.changeLanguage('en');
  });

  afterEach(async () => {
    await i18n.changeLanguage('en');
    localStorage.clear();
  });

  it('1. Supports all 11 required Indian languages with correct codes and labels', () => {
    const expectedCodes = ['en', 'hi', 'te', 'ta', 'kn', 'ml', 'mr', 'bn', 'gu', 'pa', 'or'];
    const codes = SUPPORTED_LANGUAGES.map((l) => l.code);
    expect(codes).toEqual(expectedCodes);

    expect(SUPPORTED_LANGUAGES.find((l) => l.code === 'en').label).toBe('English');
    expect(SUPPORTED_LANGUAGES.find((l) => l.code === 'hi').label).toBe('हिन्दी (Hindi)');
    expect(SUPPORTED_LANGUAGES.find((l) => l.code === 'te').label).toBe('తెలుగు (Telugu)');
    expect(SUPPORTED_LANGUAGES.find((l) => l.code === 'ta').label).toBe('தமிழ் (Tamil)');
    expect(SUPPORTED_LANGUAGES.find((l) => l.code === 'kn').label).toBe('ಕನ್ನಡ (Kannada)');
    expect(SUPPORTED_LANGUAGES.find((l) => l.code === 'ml').label).toBe('മലയാളം (Malayalam)');
    expect(SUPPORTED_LANGUAGES.find((l) => l.code === 'mr').label).toBe('मराठी (Marathi)');
    expect(SUPPORTED_LANGUAGES.find((l) => l.code === 'bn').label).toBe('বাংলা (Bengali)');
    expect(SUPPORTED_LANGUAGES.find((l) => l.code === 'gu').label).toBe('ગુજરાતી (Gujarati)');
    expect(SUPPORTED_LANGUAGES.find((l) => l.code === 'pa').label).toBe('ਪੰਜਾਬੀ (Punjabi)');
    expect(SUPPORTED_LANGUAGES.find((l) => l.code === 'or').label).toBe('ଓଡ଼ିଆ (Odia)');
  });

  it('2. Defaults to English initially', () => {
    expect(i18n.language).toBe('en');
    expect(i18n.t('nav.dashboard')).toBe('Dashboard');
    expect(i18n.t('settings.language')).toBe('Language');
  });

  it('3. Dynamically switches to Hindi and updates UI keys', async () => {
    await i18n.changeLanguage('hi');
    expect(i18n.language).toBe('hi');
    expect(i18n.t('nav.dashboard')).toBe('डैशबोर्ड');
    expect(i18n.t('settings.language')).toBe('भाषा');
    expect(i18n.t('common.save')).toBe('सहेजें');
  });

  it('4. Dynamically switches to Telugu and updates UI keys', async () => {
    await i18n.changeLanguage('te');
    expect(i18n.language).toBe('te');
    expect(i18n.t('nav.dashboard')).toBe('డాష్‌బోర్డ్');
    expect(i18n.t('settings.language')).toBe('భాష');
    expect(i18n.t('common.save')).toBe('భద్రపరచు');
  });

  it('5. Dynamically switches to Tamil and updates UI keys', async () => {
    await i18n.changeLanguage('ta');
    expect(i18n.language).toBe('ta');
    expect(i18n.t('nav.dashboard')).toBe('முகப்புப்பலகை');
    expect(i18n.t('settings.language')).toBe('மொழி');
    expect(i18n.t('common.save')).toBe('சேமிக்க');
  });

  it('6. Dynamically switches to Kannada and updates UI keys', async () => {
    await i18n.changeLanguage('kn');
    expect(i18n.language).toBe('kn');
    expect(i18n.t('nav.dashboard')).toBe('ಡ್ಯಾಶ್‌ಬೋರ್ಡ್');
    expect(i18n.t('settings.language')).toBe('ಭಾಷೆ');
  });

  it('7. Dynamically switches to Malayalam and updates UI keys', async () => {
    await i18n.changeLanguage('ml');
    expect(i18n.language).toBe('ml');
    expect(i18n.t('nav.dashboard')).toBe('ഡാഷ്‌ബോർഡ്');
    expect(i18n.t('settings.language')).toBe('ഭാഷ');
  });

  it('8. Dynamically switches to Marathi and updates UI keys', async () => {
    await i18n.changeLanguage('mr');
    expect(i18n.language).toBe('mr');
    expect(i18n.t('nav.dashboard')).toBe('डॅशबोर्ड');
    expect(i18n.t('settings.language')).toBe('भाषा');
  });

  it('9. Dynamically switches to Bengali and updates UI keys', async () => {
    await i18n.changeLanguage('bn');
    expect(i18n.language).toBe('bn');
    expect(i18n.t('nav.dashboard')).toBe('ড্যাশবোর্ড');
    expect(i18n.t('settings.language')).toBe('ভাষা');
  });

  it('10. Dynamically switches to Gujarati and updates UI keys', async () => {
    await i18n.changeLanguage('gu');
    expect(i18n.language).toBe('gu');
    expect(i18n.t('nav.dashboard')).toBe('ડેશબોર્ડ');
    expect(i18n.t('settings.language')).toBe('ભાષા');
  });

  it('11. Dynamically switches to Punjabi and updates UI keys', async () => {
    await i18n.changeLanguage('pa');
    expect(i18n.language).toBe('pa');
    expect(i18n.t('nav.dashboard')).toBe('ਡੈਸ਼ਬੋਰਡ');
    expect(i18n.t('settings.language')).toBe('ਭਾਸ਼ਾ');
  });

  it('12. Dynamically switches to Odia and updates UI keys', async () => {
    await i18n.changeLanguage('or');
    expect(i18n.language).toBe('or');
    expect(i18n.t('nav.dashboard')).toBe('ଡ୍ୟାସବୋର୍ଡ');
    expect(i18n.t('settings.language')).toBe('ଭାଷା');
  });

  it('13. Switching back to English restores English strings cleanly', async () => {
    await i18n.changeLanguage('hi');
    expect(i18n.t('nav.dashboard')).toBe('डैशबोर्ड');

    await i18n.changeLanguage('en');
    expect(i18n.language).toBe('en');
    expect(i18n.t('nav.dashboard')).toBe('Dashboard');
    expect(i18n.t('settings.language')).toBe('Language');
  });

  it('14. Missing keys fall back to English without displaying undefined or blank text', async () => {
    await i18n.changeLanguage('hi');
    // Common keys always present in English
    const fallbackVal = i18n.t('common.appName');
    expect(fallbackVal).toBe('PillSync');
  });

  it('15. LanguageSelector renders and updates active language via user interaction', async () => {
    render(
      <AuthProvider>
        <LanguageSelector variant="default" />
      </AuthProvider>
    );

    // Open language dropdown
    const triggerBtn = screen.getByRole('button', { name: /Language/i });
    fireEvent.click(triggerBtn);

    // Select Telugu
    const teluguOption = screen.getByText('తెలుగు (Telugu)');
    expect(teluguOption).toBeInTheDocument();
    fireEvent.click(teluguOption);

    await waitFor(() => {
      expect(i18n.language).toBe('te');
      expect(localStorage.getItem(STORAGE_KEY)).toBe('te');
    });
  });

  it('16. Preserves dynamic data and template interpolations intact', async () => {
    await i18n.changeLanguage('en');
    const englishNotif = i18n.t('notifications.missedDose', { medicine: 'Metformin 500mg' });
    expect(englishNotif).toContain('Metformin 500mg');

    await i18n.changeLanguage('hi');
    const hindiNotif = i18n.t('notifications.missedDose', { medicine: 'Metformin 500mg' });
    // Dynamic medicine name should remain exactly 'Metformin 500mg'
    expect(hindiNotif).toContain('Metformin 500mg');
  });
});
