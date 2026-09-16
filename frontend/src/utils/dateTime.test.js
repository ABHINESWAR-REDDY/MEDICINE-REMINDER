import { describe, it, expect } from 'vitest';
import {
  parseToLocalDate,
  formatLocalTime,
  formatLocalDate,
  formatLocalDateTime,
  formatRelativeOrTime,
} from './dateTime';

describe('dateTime utility functions', () => {
  it('correctly parses ISO timestamp from backend into local Date matching screen time', () => {
    const d = parseToLocalDate('2026-08-29T11:29:49');
    expect(d).not.toBeNull();
    expect(d.getFullYear()).toBe(2026);
    expect(d.getMonth()).toBe(7); // August
    expect(d.getDate()).toBe(29);
    expect(d.getHours()).toBe(11);
    expect(d.getMinutes()).toBe(29);
  });

  it('correctly parses SQL space-separated datetime string', () => {
    const d = parseToLocalDate('2026-08-28 21:20:21.547252');
    expect(d).not.toBeNull();
    expect(d.getHours()).toBe(21);
    expect(d.getMinutes()).toBe(20);
  });

  it('correctly formats local time in 12-hour format', () => {
    const timeStr = formatLocalTime('2026-08-29T11:29:49', { hour12: true });
    expect(timeStr.toLowerCase()).toBe('11:29 am');
    const eveningTime = formatLocalTime('2026-08-28T22:50:38', { hour12: true });
    expect(eveningTime.toLowerCase()).toBe('10:50 pm');
  });

  it('handles time-only strings like 08:00 and 20:00', () => {
    expect(formatLocalTime('08:00', { hour12: true }).toLowerCase()).toBe('08:00 am');
    expect(formatLocalTime('20:00', { hour12: true }).toLowerCase()).toBe('08:00 pm');
    expect(formatLocalTime('08:00', { hour12: false })).toBe('08:00');
  });

  it('formats pure date YYYY-MM-DD correctly without timezone shifts', () => {
    const dateStr = formatLocalDate('2026-08-29');
    expect(dateStr).toContain('2026');
    expect(dateStr).toContain('29');
  });

  it('formats relative or local time', () => {
    const nowIso = new Date().toISOString();
    expect(formatRelativeOrTime(nowIso)).toBe('Just now');
  });
});
