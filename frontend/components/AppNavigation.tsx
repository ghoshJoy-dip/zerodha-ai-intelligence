"use client";

import Link from "next/link";

const adminRole = process.env.NEXT_PUBLIC_APP_ROLE === "admin";

export default function AppNavigation() {
  return (
    <nav className="app-nav" aria-label="Main navigation">
      <Link href="/" className="brand">Zerodha Intelligence</Link>
      <div className="nav-links">
        <Link href="/">Dashboard</Link>
        <Link href="/insights">Insights</Link>
        {adminRole && (
          <>
            <Link href="/operations">Operations</Link>
            <Link href="/compliance">Compliance</Link>
          </>
        )}
      </div>
      <span className="role-label">{adminRole ? "Operator view" : "Investor view"}</span>
    </nav>
  );
}
