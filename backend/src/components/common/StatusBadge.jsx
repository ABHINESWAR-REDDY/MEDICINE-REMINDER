import React from 'react';

const statusStyles = {
  healthy: 'bg-emerald-950/80 text-emerald-400 border-emerald-800/60',
  operational: 'bg-emerald-950/80 text-emerald-400 border-emerald-800/60',
  connected: 'bg-emerald-950/80 text-emerald-400 border-emerald-800/60',
  degraded: 'bg-amber-950/80 text-amber-400 border-amber-800/60',
  unhealthy: 'bg-rose-950/80 text-rose-400 border-rose-800/60',
  offline: 'bg-rose-950/80 text-rose-400 border-rose-800/60',
  error: 'bg-rose-950/80 text-rose-400 border-rose-800/60',
  pending: 'bg-slate-800 text-slate-400 border-slate-700',
};

const dotStyles = {
  healthy: 'bg-emerald-400',
  operational: 'bg-emerald-400',
  connected: 'bg-emerald-400',
  degraded: 'bg-amber-400',
  unhealthy: 'bg-rose-400',
  offline: 'bg-rose-400',
  error: 'bg-rose-400',
  pending: 'bg-slate-400',
};

export const StatusBadge = ({ status = 'pending', label, className = '' }) => {
  const normalizedStatus = String(status).toLowerCase();
  const badgeStyle = statusStyles[normalizedStatus] || statusStyles.pending;
  const dotStyle = dotStyles[normalizedStatus] || dotStyles.pending;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${badgeStyle} ${className}`}
      data-testid={`status-badge-${normalizedStatus}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dotStyle} animate-pulse`} />
      <span className="capitalize">{label || status}</span>
    </span>
  );
};

export default StatusBadge;
