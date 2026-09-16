/**
 * Unified Date & Time Utilities for PillSync
 * Ensures accurate display of user's local screen time across all dashboards and chat.
 */

/**
 * Safely parse date strings into a local JavaScript Date object.
 * All backend timestamps represent UTC instants; handles naive UTC timestamps,
 * ISO strings, standard SQL datetime strings, and pure date strings without timezone distortion.
 */
export function parseToLocalDate(dateInput) {
  if (!dateInput) return null;
  if (dateInput instanceof Date) return isNaN(dateInput.getTime()) ? null : dateInput;
  if (typeof dateInput === 'number') {
    const ts = dateInput < 10000000000 ? dateInput * 1000 : dateInput;
    const d = new Date(ts);
    return isNaN(d.getTime()) ? null : d;
  }

  let str = String(dateInput).trim();
  if (!str) return null;

  // Handle pure date 'YYYY-MM-DD' (e.g. birth dates, calendar dates)
  const dateOnlyMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(str);
  if (dateOnlyMatch) {
    const year = parseInt(dateOnlyMatch[1], 10);
    const month = parseInt(dateOnlyMatch[2], 10) - 1;
    const day = parseInt(dateOnlyMatch[3], 10);
    const d = new Date(year, month, day);
    return isNaN(d.getTime()) ? null : d;
  }

  // Handle standard 'YYYY-MM-DD HH:mm:ss' format by converting space to 'T'
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}/.test(str)) {
    str = str.replace(' ', 'T');
  }

  // Handle ISO strings with timezone offsets (Z or +HH:mm / -HH:mm)
  if (/(?:Z|[+-]\d{2}:?\d{2})$/i.test(str)) {
    const d = new Date(str);
    if (!isNaN(d.getTime())) return d;
  }

  // Parse ISO / Datetime strings preserving the recorded wall-clock time components
  const dtMatch = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?(?:\.(\d+))?/.exec(str);
  if (dtMatch) {
    const year = parseInt(dtMatch[1], 10);
    const month = parseInt(dtMatch[2], 10) - 1;
    const day = parseInt(dtMatch[3], 10);
    const hour = parseInt(dtMatch[4], 10);
    const minute = parseInt(dtMatch[5], 10);
    const second = dtMatch[6] ? parseInt(dtMatch[6], 10) : 0;
    const ms = dtMatch[7] ? parseInt(dtMatch[7].padEnd(3, '0').slice(0, 3), 10) : 0;
    const d = new Date(year, month, day, hour, minute, second, ms);
    if (!isNaN(d.getTime())) return d;
  }

  const d = new Date(str);
  return isNaN(d.getTime()) ? null : d;
}

/**
 * Format timestamp as Local Screen Time (e.g., "09:20 AM" or "21:20")
 */
export function formatLocalTime(dateInput, { hour12 = true } = {}) {
  if (!dateInput) return '';

  // Support time-only strings like "08:00" or "20:00"
  const str = String(dateInput).trim();
  const timeOnlyMatch = /^(\d{1,2}):(\d{2})(?::(\d{2}))?$/.exec(str);
  if (timeOnlyMatch) {
    let hour = parseInt(timeOnlyMatch[1], 10);
    const minute = parseInt(timeOnlyMatch[2], 10);
    if (hour12) {
      const ampm = hour >= 12 ? 'pm' : 'am';
      hour = hour % 12 || 12;
      return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')} ${ampm}`;
    }
    return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
  }

  const d = parseToLocalDate(dateInput);
  if (!d) return '';
  return d.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    hour12,
  });
}

/**
 * Format timestamp as Local Date (e.g., "Aug 28, 2026")
 */
export function formatLocalDate(dateInput, options = {}) {
  const d = parseToLocalDate(dateInput);
  if (!d) return '';
  const defaultOptions = {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    ...options,
  };
  return d.toLocaleDateString(undefined, defaultOptions);
}

/**
 * Format timestamp as Date and Time in Local Screen Time (e.g., "Aug 28, 2026, 09:20 PM")
 */
export function formatLocalDateTime(dateInput, { hour12 = true } = {}) {
  const d = parseToLocalDate(dateInput);
  if (!d) return '';
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12,
  });
}

/**
 * Format relative message time (e.g., "Just now", "5m ago", "Today at 9:20 PM")
 */
export function formatRelativeOrTime(dateInput) {
  const d = parseToLocalDate(dateInput);
  if (!d) return '';

  const now = new Date();
  const diffSec = Math.floor((now.getTime() - d.getTime()) / 1000);

  if (diffSec < 45 && diffSec >= -30) return 'Just now';
  if (diffSec >= 45 && diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;

  const isToday =
    d.getDate() === now.getDate() &&
    d.getMonth() === now.getMonth() &&
    d.getFullYear() === now.getFullYear();

  const timeStr = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true });

  if (isToday) return timeStr;

  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  const isYesterday =
    d.getDate() === yesterday.getDate() &&
    d.getMonth() === yesterday.getMonth() &&
    d.getFullYear() === yesterday.getFullYear();

  if (isYesterday) return `Yesterday, ${timeStr}`;

  return `${d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}, ${timeStr}`;
}

