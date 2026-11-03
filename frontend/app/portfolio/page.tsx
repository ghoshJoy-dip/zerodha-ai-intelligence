import { Briefcase, TrendingDown, TrendingUp } from 'lucide-react';
import Link from 'next/link';

// Static mock data reflecting the assets analyzed by the backend AI
const portfolioHoldings = [
  { ticker: 'TCS', avgBuyPrice: 3800.0, currentPrice: 2491.0, shares: 50 },
  { ticker: 'RELIANCE', avgBuyPrice: 2800.0, currentPrice: 1292.0, shares: 100 },
  { ticker: 'HDFCBANK', avgBuyPrice: 1600.0, currentPrice: 724.65, shares: 200 },
];

export default function PortfolioPage() {
  return (
    <main className="min-h-screen bg-slate-950 p-8 flex flex-col items-center justify-start font-[family-name:var(--font-geist-sans)]">
      <div className="w-full max-w-4xl mb-8 flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
            <Briefcase className="text-blue-400" />
            Portfolio Holdings
          </h1>
          <p className="text-slate-400">Raw asset allocation and current valuations</p>
        </div>
        <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm font-semibold">
          &larr; Back to AI Insights
        </Link>
      </div>

      <div className="w-full max-w-4xl bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-950 border-b border-slate-800 text-slate-400 text-sm">
              <th className="p-4 font-semibold">Asset / Ticker</th>
              <th className="p-4 font-semibold text-right">Shares</th>
              <th className="p-4 font-semibold text-right">Avg. Buy Price</th>
              <th className="p-4 font-semibold text-right">Current Price</th>
              <th className="p-4 font-semibold text-right">P&L (%)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 text-slate-200">
            {portfolioHoldings.map((asset, idx) => {
              const pnl = ((asset.currentPrice - asset.avgBuyPrice) / asset.avgBuyPrice) * 100;
              const isPositive = pnl >= 0;

              return (
                <tr key={idx} className="hover:bg-slate-800/50 transition-colors">
                  <td className="p-4 font-bold text-white">{asset.ticker}</td>
                  <td className="p-4 text-right font-mono">{asset.shares}</td>
                  <td className="p-4 text-right font-mono">₹{asset.avgBuyPrice.toFixed(2)}</td>
                  <td className="p-4 text-right font-mono">₹{asset.currentPrice.toFixed(2)}</td>
                  <td className={`p-4 text-right font-mono font-medium flex items-center justify-end gap-1 ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                    {isPositive ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                    {pnl.toFixed(2)}%
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </main>
  );
}