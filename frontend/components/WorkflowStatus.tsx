"use client";

const steps = [
  { label: "Submitted", statuses: ["submitted"] },
  { label: "Data fetch", statuses: ["fetching_data"] },
  { label: "MCP tools", statuses: ["mcp_tools"] },
  { label: "Analytics", statuses: ["mcp_tools"] },
  { label: "LLM analysis", statuses: ["llm_analysis"] },
  { label: "Validation", statuses: ["insight_generated"] },
  { label: "Complete", statuses: ["completed"] },
];

const order = [
  "submitted",
  "fetching_data",
  "mcp_tools",
  "llm_analysis",
  "insight_generated",
  "recommendations",
  "completed",
];

export default function WorkflowStatus({ status }: { status: string }) {
  const currentIndex = order.indexOf(status);
  const failed = status === "failed";
  const empty = status === "empty_portfolio";
  return (
    <section className="panel" aria-label="Portfolio analysis workflow">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Pipeline</p>
          <h2>Analysis workflow</h2>
        </div>
        <span className={`status-pill ${failed ? "status-error" : ""}`}>
          {empty ? "Empty portfolio" : status.replaceAll("_", " ")}
        </span>
      </div>
      {failed || empty ? (
        <p className="muted mt-4">
          {failed
            ? "This analysis failed. Submit a new job to retry."
            : "No holdings were available for this job."}
        </p>
      ) : (
        <ol className="workflow-steps">
          {steps.map((step, index) => {
            const stepIndex = Math.max(...step.statuses.map((value) => order.indexOf(value)));
            const active = step.statuses.includes(status);
            const complete = currentIndex > stepIndex || status === "completed";
            return (
              <li
                key={step.label}
                className={`workflow-step ${active ? "is-active" : ""} ${complete ? "is-complete" : ""}`}
                aria-current={active ? "step" : undefined}
              >
                <span className="workflow-dot">{complete ? "✓" : index + 1}</span>
                <span>{step.label}</span>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
