import React from 'react';
import { useTranslation } from 'react-i18next';
import { Layers } from 'lucide-react';

export const EmptyState = ({
  icon: Icon = Layers,
  title,
  description,
  className = '',
}) => {
  const { t } = useTranslation();
  const displayTitle = title || t('common.noData');
  const displayDescription = description || t('common.noResults');

  return (
    <div
      className={`flex flex-col items-center justify-center p-8 text-center rounded-xl border border-dashed border-slate-800 bg-slate-900/40 ${className}`}
      data-testid="empty-state"
    >
      <div className="p-3 rounded-xl bg-slate-800/80 text-slate-400 mb-3">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-sm font-semibold text-slate-200">{displayTitle}</h3>
      <p className="mt-1 text-xs text-slate-400 max-w-sm">{displayDescription}</p>
    </div>
  );
};

export default EmptyState;
