"use client";

import { useMemo, useState } from "react";
import FeedbackDrawer from "./FeedbackDrawer";
import type { RecommendationCardData } from "../lib/api";

const categories = [
  "All",
  "Diversification Review",
  "Risk Alert",
  "Watchlist Monitoring",
  "Summary Follow-up",
];

export default function RecommendationFeed({
  cards,
}: {
  cards: RecommendationCardData[];
}) {
  const [category, setCategory] = useState("All");
  const visibleCards = useMemo(
    () => cards.filter((card) => category === "All" || card.category === category),
    [cards, category],
  );

  return (
    <section className="feed-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Persisted recommendations</p>
          <h2>Insight cards</h2>
        </div>
        <label className="filter-control">
          <span className="sr-only">Filter recommendation category</span>
          <select value={category} onChange={(event) => setCategory(event.target.value)}>
            {categories.map((item) => <option key={item}>{item}</option>)}
          </select>
        </label>
      </div>
      {visibleCards.length === 0 ? (
        <div className="empty-panel">No saved recommendation cards in this category for the selected job.</div>
      ) : (
        <div className="cards-grid">
          {visibleCards.map((card) => (
            <article key={card.id} className="recommendation-card">
              <div className="card-topline">
                <span className="category-chip">{card.category}</span>
                <span className={`validation-chip ${card.is_validated ? "valid" : "flagged"}`}>
                  {card.status}
                </span>
              </div>
              <h3>{card.title}</h3>
              <p className="card-rationale">{card.rationale}</p>
              <div className="supporting-metrics">
                <h4>Supporting metrics</h4>
                {card.supporting_metrics.map((metric, index) => (
                  <div className="supporting-metric" key={`${metric.metric_name}-${index}`}>
                    <span>{metric.metric_name}</span>
                    <strong>{formatMetric(metric.metric_value)}</strong>
                  </div>
                ))}
                {card.supporting_metrics.length === 0 && <p className="muted">No supporting values recorded.</p>}
              </div>
              <div className="card-meta">
                <span>Confidence {(card.confidence * 100).toFixed(0)}%</span>
                <span>{card.freshness_timestamp ? new Date(card.freshness_timestamp).toLocaleString() : "Freshness unavailable"}</span>
              </div>
              {card.validation_reason && <p className="flag-note">{card.validation_reason}</p>}
              <p className="disclaimer">{card.disclaimer}</p>
              <FeedbackDrawer cardId={card.id} />
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function formatMetric(value: number) {
  return Number.isFinite(value) ? value.toLocaleString(undefined, { maximumFractionDigits: 3 }) : "—";
}
