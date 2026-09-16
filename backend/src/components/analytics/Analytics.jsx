import React from 'react';
import { BarChart3, TrendingUp } from 'lucide-react';
import EmptyState from '../common/EmptyState';

export const Analytics = () => {
  return (
    <div className="space-y-6 w-full">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Analytics & Insights</h2>
          <p className="text-sm text-slate-400 mt-1">
            Analyze historical adherence patterns, refill forecasts, and health summaries
          </p>
        </div>
      </div>

      {/* Clean Content Area */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
        <EmptyState
          icon={BarChart3}
          title="No analytics recorded yet"
          description="Detailed adherence charts and health trend statistics will be generated as you log medication intakes."
        />
      </div>
    </div>
  );
};

export default Analytics;
