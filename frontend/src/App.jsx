import { useState } from 'react'

const TABS = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'forecast', label: 'Forecast' },
  { id: 'phase-comparison', label: 'Phase Comparison' },
  { id: 'pnl', label: 'P&L' },
  { id: 'data-entry', label: 'Data Entry' },
]

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1 className="app-title">Cashflow</h1>
      </header>

      <nav className="app-nav" role="navigation" aria-label="Main tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`app-nav-tab${activeTab === tab.id ? ' app-nav-tab--active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
            aria-current={activeTab === tab.id ? 'page' : undefined}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <main className="app-main">
        {activeTab === 'dashboard' && (
          <section className="dashboard-section">
            <h2 className="dashboard-heading">Dashboard</h2>
            <p className="dashboard-stat">No data loaded yet.</p>
          </section>
        )}

        {activeTab === 'forecast' && (
          <section className="forecast-section">
            <h2 className="forecast-heading">Forecast</h2>
            <p className="forecast-label">No forecast data available.</p>
          </section>
        )}

        {activeTab === 'phase-comparison' && (
          <section className="phase-comparison-section">
            <h2 className="phase-comparison-heading">Phase Comparison</h2>
            <p className="phase-comparison-label">No phase data available.</p>
          </section>
        )}

        {activeTab === 'pnl' && (
          <section className="pnl-section">
            <h2 className="pnl-heading">P&L</h2>
            <p className="pnl-label">No P&L data available.</p>
          </section>
        )}

        {activeTab === 'data-entry' && (
          <section className="data-entry-section">
            <h2 className="data-entry-heading">Data Entry</h2>
            <p className="data-entry-label">No entries yet.</p>
          </section>
        )}
      </main>
    </div>
  )
}

export default App
