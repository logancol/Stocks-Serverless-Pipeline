import { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [winners, setWinners] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL;
    if (!apiUrl) {
      setError("Missing VITE_API_URL (set it in a .env file)");
      setLoading(false);
      return;
    }

    (async () => {
      try {
        const res = await fetch(apiUrl);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setWinners(Array.isArray(data?.winners) ? data.winners : []);
      } catch (e) {
        setError(e?.message || "Request failed");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div style={{ maxWidth: 700, margin: "0 auto", padding: 24 }}>
      <h1>Biggest Movers</h1>

      {loading && <div>Loading…</div>}
      {error && <div style={{ color: "red" }}>Error: {error}</div>}

      {!loading && !error && winners.length === 0 && (
        <div>No data yet (run the compute Lambda once).</div>
      )}

      {!loading && !error && winners.length > 0 && (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {winners.map((w) => {
            const pct = Number.parseFloat(w.percent_change);
            const pctColor = Number.isFinite(pct)
              ? pct >= 0
                ? "green"
                : "red"
              : "inherit";

            return (
              <li
                key={`${w.date}-${w.ticker_symbol}`}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: "10px 0",
                  borderBottom: "1px solid #ddd",
                }}
              >
                <span>
                  <strong>{w.ticker_symbol}</strong> <span>({w.date})</span>
                </span>
                <span style={{ color: pctColor }}>
                  {Number.isFinite(pct) ? `${pct.toFixed(2)}%` : String(w.percent_change)}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export default App;