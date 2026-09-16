import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  Pill, 
  AlertTriangle, 
  Info, 
  CheckCircle2, 
  ShieldCheck, 
  Stethoscope, 
  Calendar, 
  Clock, 
  Scale, 
  Activity 
} from 'lucide-react';

/**
 * Enhanced Clinical Markdown Message Renderer
 * Formats AI healthcare replies with beautiful typography, high-contrast tables,
 * styled callouts, and clean section headers.
 */
export default function FormattedMessage({ content, isEmergency, isOutOfScope }) {
  if (!content) return null;

  return (
    <div className="formatted-ai-response text-slate-100 text-sm leading-relaxed space-y-3.5">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-base sm:text-lg font-extrabold text-white mt-4 mb-2.5 pb-2 border-b border-slate-700/80 flex items-center gap-2 tracking-tight text-teal-300">
              <Activity className="w-5 h-5 text-teal-400 shrink-0" />
              <span>{children}</span>
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-sm sm:text-base font-bold text-teal-200 mt-4 mb-2 pb-1.5 border-b border-slate-800 flex items-center gap-2 tracking-tight">
              <Scale className="w-4 h-4 text-teal-400 shrink-0" />
              <span>{children}</span>
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-xs sm:text-sm font-bold text-white mt-3.5 mb-1.5 flex items-center gap-2 text-teal-300">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-teal-400"></span>
              <span>{children}</span>
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-xs font-semibold text-slate-200 mt-2.5 mb-1">
              {children}
            </h4>
          ),
          p: ({ children }) => (
            <p className="text-xs sm:text-sm text-slate-200 leading-relaxed my-2">
              {children}
            </p>
          ),
          strong: ({ children }) => (
            <strong className="font-bold text-white bg-slate-800/80 px-1 py-0.5 rounded text-[13px] border border-slate-700/60 text-teal-100">
              {children}
            </strong>
          ),
          em: ({ children }) => (
            <em className="text-slate-300 italic not-italic text-slate-400 font-medium">
              ({children})
            </em>
          ),
          ul: ({ children }) => (
            <ul className="my-2.5 space-y-1.5 pl-1">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="my-2.5 space-y-1.5 pl-4 list-decimal list-outside text-slate-200 text-xs sm:text-sm">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="flex items-start gap-2 text-xs sm:text-sm text-slate-200 leading-relaxed">
              <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-teal-400 shrink-0"></span>
              <span className="flex-1">{children}</span>
            </li>
          ),
          blockquote: ({ children }) => (
            <blockquote className="my-3 p-3 rounded-xl bg-teal-950/40 border-l-4 border-teal-500 text-xs sm:text-sm text-teal-100 shadow-inner">
              {children}
            </blockquote>
          ),
          // Sleek Clinical Data Table
          table: ({ children }) => (
            <div className="my-3.5 overflow-x-auto rounded-2xl border border-slate-700/80 bg-slate-950/90 shadow-xl">
              <table className="w-full text-left border-collapse text-xs sm:text-sm min-w-[520px]">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-gradient-to-r from-teal-950/80 via-slate-900 to-slate-950 border-b border-slate-700/90 text-teal-300">
              {children}
            </thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-slate-800/80 text-slate-200">
              {children}
            </tbody>
          ),
          tr: ({ children }) => (
            <tr className="hover:bg-slate-800/40 transition-colors">
              {children}
            </tr>
          ),
          th: ({ children }) => (
            <th className="px-3.5 py-2.5 font-bold uppercase tracking-wider text-[11px] text-teal-300">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-3.5 py-2.5 text-xs sm:text-sm leading-relaxed align-top">
              {children}
            </td>
          ),
          hr: () => (
            <hr className="my-3 border-slate-800" />
          ),
          code: ({ children }) => (
            <code className="px-1.5 py-0.5 rounded-md bg-slate-800 border border-slate-700 text-teal-300 font-mono text-xs">
              {children}
            </code>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
