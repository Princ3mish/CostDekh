import React, { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid
} from "recharts";
import "./App.css";

function App() {
  const [routes, setRoutes] = useState([]);
  const [expandedIndex, setExpandedIndex] = useState(null);
  const [historyCache, setHistoryCache] = useState({});
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [qaQuestion, setQaQuestion] = useState("");
  const [qaAnswer, setQaAnswer] = useState(null);
  const [qaLoading, setQaLoading] = useState(false);
  const [qaMatchCount, setQaMatchCount] = useState(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/flagged-routes")
      .then((res) => res.json())
      .then((data) => {
        const sorted = [...data].sort((a, b) => (b.week_of > a.week_of ? 1 : -1));
        setRoutes(sorted);
      })
      .catch((err) => console.error("Error fetching flagged routes:", err));
  }, []);

  const handleRowClick = (index, route) => {
    if (expandedIndex === index) {
      setExpandedIndex(null);
      return;
    }
    setExpandedIndex(index);
    if (!historyCache[route]) {
      setLoadingHistory(true);
      fetch(`http://localhost:8000/api/route-history/${encodeURIComponent(route)}`)
        .then((res) => res.json())
        .then((data) => {
          setHistoryCache((prev) => ({ ...prev, [route]: data }));
          setLoadingHistory(false);
        })
        .catch((err) => {
          console.error("Error fetching route history:", err);
          setLoadingHistory(false);
        });
    }
  };

  const handleAsk = () => {
    if (!qaQuestion.trim()) return;
    setQaLoading(true);
    setQaAnswer(null);
    setQaMatchCount(null);
    fetch("http://localhost:8000/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: qaQuestion }),
    })
      .then((res) => res.json())
      .then((data) => {
        setQaAnswer(data.answer);
        setQaMatchCount(data.matched_row_count);
        setQaLoading(false);
      })
      .catch((err) => {
        console.error("Error calling /api/ask:", err);
        setQaLoading(false);
      });
  };

  return (
    <div className="container">
      <header className="header">
        <h1>Freight Cost Watch Dashboard</h1>
        <p className="subtitle">Weekly cost-per-tonne-km anomalies, context evidence & route trend analysis</p>
      </header>

      <div className="qa-section">
        <h3 className="qa-heading">Ask about a route</h3>
        <div className="qa-row">
          <input
            className="qa-input"
            type="text"
            value={qaQuestion}
            onChange={(e) => setQaQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAsk()}
            placeholder="e.g. why did Ahmedabad Mumbai get pricier in January 2025"
          />
          <button className="qa-button" onClick={handleAsk} disabled={qaLoading}>
            {qaLoading ? "Thinking..." : "Ask"}
          </button>
        </div>
        {qaLoading && <p className="qa-answer qa-answer-muted">Thinking...</p>}
        {!qaLoading && qaAnswer !== null && (
          <p className={`qa-answer ${qaMatchCount === 0 ? "qa-answer-muted" : "qa-answer-grounded"}`}>
            {qaAnswer}
          </p>
        )}
      </div>

      <div className="table-wrapper">
        <table className="flagged-table">
          <thead>
            <tr>
              <th>Route</th>
              <th>Week</th>
              <th>Cost / Tonne-KM</th>
              <th>vs Own History</th>
              <th>vs Similar Routes</th>
              <th>Verdict</th>
            </tr>
          </thead>
          <tbody>
            {routes.map((row, idx) => {
              const isExpanded = expandedIndex === idx;
              const isYes = row.flagged === "Yes";
              const routeHistory = historyCache[row.route] || [];

              return (
                <React.Fragment key={`${row.route}-${row.week_of}`}>
                  <tr
                    className={`data-row ${isYes ? "row-unexplained" : "row-justified"} ${isExpanded ? "expanded" : ""}`}
                    onClick={() => handleRowClick(idx, row.route)}
                  >
                    <td className="route-cell">{row.route}</td>
                    <td>{row.week_of}</td>
                    <td>₹{typeof row.cost_per_tonne_km === "number" ? row.cost_per_tonne_km.toFixed(2) : row.cost_per_tonne_km}</td>
                    <td>{row.vs_own_history}</td>
                    <td>{row.vs_similar_routes}</td>
                    <td>
                      <span className={`badge ${isYes ? "badge-unexplained" : "badge-justified"}`}>
                        {row.flagged}
                      </span>
                    </td>
                  </tr>

                  {isExpanded && (
                    <tr className="detail-row">
                      <td colSpan={6}>
                        <div className={`detail-panel ${isYes ? "panel-unexplained" : "panel-justified"}`}>
                          <div className="detail-section">
                            <h4>Explanation & Verdict Rationale</h4>
                            <p className="reason-text">{row.reason}</p>
                          </div>

                          <div className="detail-section">
                            <h4>Context Note Evidence</h4>
                            {row.matched_note_text ? (
                              <div className="note-card">
                                <div className="note-meta">
                                  <strong>Note ID:</strong> {row.matched_note_id} | <strong>Date:</strong> {row.matched_note_date}
                                </div>
                                <p className="note-text">{row.matched_note_text}</p>
                              </div>
                            ) : (
                              <p className="no-note">No supporting note found</p>
                            )}
                          </div>

                          <div className="detail-section chart-section">
                            <h4>Route Cost History (Cost / Tonne-KM over time)</h4>
                            {loadingHistory && !historyCache[row.route] ? (
                              <div className="loading-text">Loading route trend...</div>
                            ) : (
                              <div style={{ width: "100%", height: 260 }}>
                                <ResponsiveContainer>
                                  <LineChart data={routeHistory} margin={{ top: 10, right: 30, left: 10, bottom: 20 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                                    <XAxis
                                      dataKey="week_of"
                                      tick={{ fontSize: 11 }}
                                      angle={-45}
                                      textAnchor="end"
                                      height={50}
                                    />
                                    <YAxis
                                      domain={['auto', 'auto']}
                                      tick={{ fontSize: 11 }}
                                      tickFormatter={(val) => `₹${val.toFixed(1)}`}
                                    />
                                    <Tooltip
                                      formatter={(val) => [`₹${Number(val).toFixed(2)}`, "Cost / Tonne-KM"]}
                                      labelFormatter={(lbl) => `Week of ${lbl}`}
                                    />
                                    <Line
                                      type="monotone"
                                      dataKey="cost_per_tonne_km"
                                      stroke={isYes ? "#d9381e" : "#0f766e"}
                                      strokeWidth={2}
                                      dot={false}
                                      activeDot={{ r: 5 }}
                                    />
                                  </LineChart>
                                </ResponsiveContainer>
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default App;
