import InsightCard from '../components/InsightCard';

// Next.js Server Component fetching directly from FastAPI
async function getInsight() {
  const res = await fetch('http://127.0.0.1:8000/api/insight/user_123', {
    cache: 'no-store' // Ensure we get fresh AI data on every reload
  });
  
  if (!res.ok) {
    throw new Error('Failed to fetch AI insight');
  }
  return res.json();
}

export default async function Home() {
  const insightData = await getInsight();

  return (
    <main className="min-h-screen bg-slate-950 p-8 flex flex-col items-center justify-center font-[family-name:var(--font-geist-sans)]">
      <div className="w-full max-w-3xl mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Zerodha Intelligence Platform</h1>
        <p className="text-slate-400">Autonomous Portfolio Analysis & Recommendations</p>
      </div>
      
      <InsightCard data={insightData} />
    </main>
  );
}