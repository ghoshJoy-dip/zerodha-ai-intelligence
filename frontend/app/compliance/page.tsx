import ComplianceDashboard from "./ComplianceDashboard";

export default function CompliancePage() {
  if (process.env.NEXT_PUBLIC_APP_ROLE !== "admin") {
    return (
      <main className="app-shell">
        <section className="access-denied">
          <h1>Compliance view is restricted</h1>
          <p>Set NEXT_PUBLIC_APP_ROLE=admin for this local operator build.</p>
        </section>
      </main>
    );
  }
  return <ComplianceDashboard />;
}
