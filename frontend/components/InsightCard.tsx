import { CheckCircle, Info } from 'lucide-react';

interface Metric {
  metric_name: string;
  metric_value: number;
}

interface InsightProps {
  data: {
    category: string;
    title: string;
    explanation: string;
    rationale: string;
    supporting_metrics: Metric[];
    is_validated: boolean;
  };
}

export default function InsightCard({ data }: InsightProps) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg text-slate-200 w-full max-w-3xl">
      <div className="flex items-center justify-between mb-4">
        <span className="px-3 py-1 bg-blue-900 text-blue-300 text-xs font-semibold rounded-full uppercase tracking-wider">
          {data.category}
        </span>
        {data.is_validated && (
          <div className="flex items-center gap-1 text-emerald-400 text-sm font-medium">
            <CheckCircle size={16} />
            <span>AI Validated</span>
          </div>
        )}
      </div>

      <h2 className="text-2xl font-bold text-white mb-3">{data.title}</h2>
      
      <p className="text-slate-400 mb-6 leading-relaxed">
        {data.explanation}
      </p>

      <div className="bg-slate-950 rounded-lg p-4 mb-6 border border-slate-800">
        <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
          <Info size={16} className="text-blue-400" />
          AI Rationale
        </h3>
        <p className="text-sm text-slate-400">{data.rationale}</p>
      </div>

      <div>
        <h3 className="text-sm font-semibold text-slate-300 mb-3">Supporting Metrics</h3>
        <div className="grid grid-cols-2 gap-3">
          {data.supporting_metrics.map((metric, idx) => (
            <div key={idx} className="bg-slate-800/50 rounded-md p-3 flex justify-between items-center border border-slate-700/50">
              <span className="text-sm text-slate-400">{metric.metric_name}</span>
              <span className="font-mono text-sm text-white font-medium">{metric.metric_value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}