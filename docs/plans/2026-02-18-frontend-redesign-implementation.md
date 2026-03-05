# Frontend Redesign ("Warm Ledger") — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the frontend with a warm dark palette, amber accent, editorial typography, compact header with global stage pills, and denser data-first layouts — while preserving all existing functionality and passing all 120 tests.

**Architecture:** CSS-first approach. Phase 1 replaces the entire color/font system via CSS variables without touching components. Subsequent phases restructure components one tab at a time. Tests are updated alongside component changes. Zero backend changes.

**Tech Stack:** React 19, Vite 7, CSS (no preprocessors), Google Fonts (Fraunces, IBM Plex Mono), Fontsource/CDN (Geist)

---

### Task 1: Replace Color Palette and Font Stack

The foundation. Change every color and font across the app by updating CSS variables and font imports. No component changes — all 120 tests must still pass unchanged.

**Files:**
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/App.css`

**Step 1: Update font imports and root variables in index.css**

Replace `frontend/src/index.css` entirely:

```css
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=IBM+Plex+Mono:wght@400;500&display=swap');
@import url('https://cdn.jsdelivr.net/npm/geist@1/dist/fonts/geist-sans/style.min.css');

:root {
  /* Background */
  --bg-deep: #141210;
  --bg-surface: #1c1a17;
  --bg-elevated: #252220;
  --bg-input: #1e1c19;

  /* Borders */
  --border-subtle: #2a2723;
  --border-medium: #3a3630;
  --border-strong: #4a4540;

  /* Text */
  --text-primary: #e8e4de;
  --text-secondary: #9b9590;
  --text-tertiary: #6b6560;

  /* Accent (Amber/Gold) */
  --accent: #d4a054;
  --accent-hover: #e0b06a;
  --accent-muted: rgba(212, 160, 84, 0.15);
  --accent-glow: rgba(212, 160, 84, 0.08);

  /* Semantic */
  --positive: #6bba6e;
  --negative: #d45b56;
  --neutral: #9b9590;
  --forecast-bg: rgba(212, 160, 84, 0.04);
  --actual-bg: rgba(107, 186, 110, 0.04);

  /* Dirty/Changed */
  --dirty: #d4a054;
  --dirty-bg: rgba(212, 160, 84, 0.08);
  --dirty-border: rgba(212, 160, 84, 0.4);

  /* Calculated/Preview */
  --calc-text: #7a7570;
  --calc-preview: #b09060;

  /* Shadows */
  --shadow-elevated: 0 8px 32px rgba(0, 0, 0, 0.4);

  /* Fonts */
  --font-display: 'Fraunces', Georgia, serif;
  --font-body: 'Geist', system-ui, -apple-system, sans-serif;
  --font-mono: 'IBM Plex Mono', 'SF Mono', monospace;

  color-scheme: dark;
  background-color: var(--bg-deep);
  color: var(--text-primary);
  font-family: var(--font-body);
  font-size: 13px;
  line-height: 1.5;
  font-weight: 400;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  margin: 0;
  min-height: 100vh;
  background: var(--bg-deep);
}

a {
  color: var(--accent);
  text-decoration: none;
}
a:hover {
  color: var(--accent-hover);
}
```

**Step 2: Update App.css color references**

This is a systematic find-and-replace across App.css. Every hardcoded color becomes a CSS variable reference. Key replacements:

| Old Value | New Value |
|---|---|
| `#0a0e1a`, `#1a1f2e`, `#0f1419` (backgrounds) | `var(--bg-deep)` |
| `#1a1f2e`, `rgba(26, 31, 46, ...)` (card/surface bg) | `var(--bg-surface)` |
| `#e8eaed` (primary text) | `var(--text-primary)` |
| `#9aa0a6` (secondary text) | `var(--text-secondary)` |
| `#bb86fc`, `#7c4dff` (purple accent) | `var(--accent)` |
| `rgba(187, 134, 252, ...)` (purple variants) | `var(--accent-muted)` or `var(--accent)` with opacity |
| `#66bb6a` (green) | `var(--positive)` |
| `#ef5350` (red) | `var(--negative)` |
| `#2d2d3d`, `#3d3d4d` (borders) | `var(--border-subtle)` or `var(--border-medium)` |
| `#cf6679` (danger) | `var(--negative)` |
| `'DM Serif Display'` | `var(--font-display)` |
| `'IBM Plex Sans'` | `var(--font-body)` |

Also update all financial value elements to use `var(--font-mono)`:
- `.data-cell`, `.calculated-value`, `.data-input` — font-family: `var(--font-mono)`
- `.stat-content .stat-value` (KPI values) — font-family: `var(--font-mono)`
- `.summary-card-value` — font-family: `var(--font-mono)`
- `.pnl-table td` — font-family: `var(--font-mono)`

Remove the gradient background on `.cashflow-container` and replace with flat `var(--bg-deep)`.

Remove `backdrop-filter: blur()` from `.header` — replace with solid `var(--bg-surface)` background and `border-bottom: 1px solid var(--border-subtle)`.

Change `border-radius: 12px`/`16px` on cards to `6px` max.

Add subtle paper grain texture to `.cashflow-container`:

```css
.cashflow-container {
  background: var(--bg-deep);
  position: relative;
}
.cashflow-container::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E");
  background-size: 256px 256px;
  pointer-events: none;
  z-index: 0;
}
```

**Step 3: Run all frontend tests**

Run: `cd frontend && npx vitest run`

Expected: All 120 tests pass. No component structure changed — only CSS values.

**Step 4: Run frontend lint**

Run: `cd frontend && npm run lint`

Expected: Clean.

**Step 5: Visual check**

Run: `cd frontend && npm run dev`

Open http://localhost:5173 and verify:
- Warm dark background (brownish-black, not blue-black)
- Amber/gold accent color on active tab, buttons
- Fraunces serif on headings
- Geist sans on labels and body text
- IBM Plex Mono on all financial values
- No purple remaining anywhere
- Paper grain texture visible on close inspection

**Step 6: Commit**

```bash
git add frontend/src/index.css frontend/src/App.css
git commit -m "Replace color palette and font stack with warm ledger theme"
```

---

### Task 2: Compact Header with Global Stage Selector

Restructure the header into a tight 2-line layout: app title + report context + stage pills on line 1, tabs on line 2. The stage selector becomes global state in App.jsx.

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/Header.jsx`
- Modify: `frontend/src/components/TabBar.jsx`
- Create: `frontend/src/components/StagePills.jsx`
- Modify: `frontend/src/App.css`
- Modify: `frontend/src/App.test.jsx`
- Modify: `frontend/src/components/tabs/DataEntryTab.jsx`
- Modify: `frontend/src/components/tabs/DataEntryTab.test.jsx`

**Step 1: Create StagePills component**

Create `frontend/src/components/StagePills.jsx`:

```jsx
const STAGES = ['s1', 's2', 's3', 's4', 's5'];
const LABELS = { s1: 'S1', s2: 'S2', s3: 'S3', s4: 'S4', s5: 'S5' };

export default function StagePills({ active, onChange, dirtyCounts = {} }) {
  return (
    <div className="stage-pills">
      {STAGES.map(s => (
        <button
          key={s}
          className={`stage-pill${active === s ? ' active' : ''}`}
          onClick={() => onChange(s)}
        >
          {LABELS[s]}
          {(dirtyCounts[s] || 0) > 0 && <span className="stage-dirty-dot" />}
        </button>
      ))}
    </div>
  );
}
```

**Step 2: Update Header.jsx**

Replace `frontend/src/components/Header.jsx`:

```jsx
export default function Header({ children, right }) {
  return (
    <header className="header">
      <div className="header-line-1">
        <div className="header-title">
          <span className="header-logo">PCG</span>
          <span className="header-app-name">Cashflow</span>
        </div>
        {right}
      </div>
      <div className="header-line-2">
        {children}
      </div>
    </header>
  );
}
```

**Step 3: Update TabBar.jsx**

Replace `frontend/src/components/TabBar.jsx`:

```jsx
import { LayoutDashboard, CalendarRange, GitCompare, Receipt, PenLine } from 'lucide-react';

const tabs = [
  { id: 'dashboard', label: 'Overview', icon: LayoutDashboard },
  { id: 'forecast', label: 'Forecast', icon: CalendarRange },
  { id: 'stages', label: 'Stages', icon: GitCompare },
  { id: 'pnl', label: 'P&L', icon: Receipt },
  { id: 'entry', label: 'Data Entry', icon: PenLine },
];

export default function TabBar({ activeTab, onTabChange }) {
  return (
    <nav className="tab-bar">
      {tabs.map(tab => (
        <button
          key={tab.id}
          className={`tab-btn${activeTab === tab.id ? ' active' : ''}`}
          onClick={() => onTabChange(tab.id)}
        >
          <tab.icon size={14} />
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
```

**Step 4: Update App.jsx to add global activeStage state**

Add to `frontend/src/App.jsx`:
- New state: `const [activeStage, setActiveStage] = useState('s1');`
- Import StagePills: `import StagePills from './components/StagePills'`
- Pass `right={<StagePills active={activeStage} onChange={setActiveStage} />}` to Header
- Pass `activeStage` and `setActiveStage` to DataEntryTab (so it uses global state instead of local)
- Rename the heading from "Cash Flow Projection" (since it's now in the compact header)

Updated App.jsx render:

```jsx
return (
  <div className="cashflow-container">
    <Header right={<StagePills active={activeStage} onChange={setActiveStage} />}>
      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
    </Header>
    <main className="main-content">
      {activeTab === 'dashboard' && <DashboardTab onTabChange={setActiveTab} />}
      {activeTab === 'forecast' && (
        <ForecastTab
          ncfData={ncfData} n12mData={n12mData} months={months}
          loading={loading} error={error}
          expandedSections={expandedSections} toggleSection={toggleSection}
        />
      )}
      {activeTab === 'stages' && <StageComparisonTab />}
      {activeTab === 'pnl' && <PnLTab />}
      {activeTab === 'entry' && (
        <DataEntryTab activeStage={activeStage} onStageChange={setActiveStage} />
      )}
    </main>
  </div>
);
```

**Step 5: Update DataEntryTab to use global stage state**

In `frontend/src/components/tabs/DataEntryTab.jsx`:
- Change props to `{ activeStage, onStageChange }`
- Remove local `activeStage` state (`useState('s1')`)
- Replace all `setActiveStage` calls with `onStageChange`
- Remove the stage tabs section from the render (stage pills are now in the header)
- Keep `stageDirtyCounts` computation and pass it up somehow — actually, the dirtyCounts need to reach the header's StagePills. Two options:
  - Option A: Lift dirty state to App.jsx (complex, over-engineered)
  - Option B: Keep dirtyCounts local and render a secondary StagePills inside DataEntryTab that shows dirty dots (simpler, keeps the header pills clean)

**Decision: Option B.** The header StagePills shows stage selection globally. When on the Data Entry tab, the dirty dots are visible on the stage pills there. This avoids lifting complex dirty state to App.

Actually, simpler: pass `dirtyCounts` up to App via a callback, and App passes it to StagePills. But that requires state in App for something that only Data Entry cares about.

**Revised decision:** Keep the stage pills in the header always, but only show dirty dots when on the Data Entry tab. DataEntryTab will communicate dirty counts via a ref or callback.

**Simplest approach:** Add `stageDirtyCounts` state to App.jsx, pass a setter to DataEntryTab, DataEntryTab calls it when dirty changes. App passes it to StagePills.

In App.jsx:
```jsx
const [stageDirtyCounts, setStageDirtyCounts] = useState({});

// In Header:
<StagePills active={activeStage} onChange={setActiveStage} dirtyCounts={activeTab === 'entry' ? stageDirtyCounts : {}} />

// Pass to DataEntryTab:
<DataEntryTab activeStage={activeStage} onStageChange={setActiveStage} onDirtyCountsChange={setStageDirtyCounts} />
```

In DataEntryTab.jsx, add a `useEffect` that calls `onDirtyCountsChange(stageDirtyCounts)` whenever dirty changes:

```jsx
import { useState, useCallback, useEffect } from 'react';

// Inside component:
const stageDirtyCounts = STAGES.reduce((acc, stage) => {
  acc[stage] = [...dirty].filter(k => k.startsWith(stage + ':')).length;
  return acc;
}, {});

useEffect(() => {
  onDirtyCountsChange?.(stageDirtyCounts);
}, [dirty.size]); // eslint-disable-line react-hooks/exhaustive-deps
```

Remove the stage tabs JSX from DataEntryTab's render.

**Step 6: Add CSS for new header layout**

Add to `frontend/src/App.css`:

```css
/* Compact 2-line header */
.header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
}

.header-line-1 {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 24px;
  border-bottom: 1px solid var(--border-subtle);
}

.header-title {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.header-logo {
  font-family: var(--font-display);
  font-size: 18px;
  color: var(--accent);
  font-weight: 600;
}

.header-app-name {
  font-family: var(--font-display);
  font-size: 18px;
  color: var(--text-primary);
  font-weight: 600;
}

.header-line-2 {
  padding: 0 24px;
}

/* Stage Pills */
.stage-pills {
  display: flex;
  gap: 4px;
}

.stage-pill {
  position: relative;
  padding: 4px 12px;
  border: 1px solid var(--border-medium);
  border-radius: 4px;
  background: transparent;
  color: var(--text-secondary);
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.stage-pill:hover {
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.stage-pill.active {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-muted);
}

.stage-dirty-dot {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
}

/* Updated tab bar */
.tab-bar {
  display: flex;
  gap: 0;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.15s ease, border-color 0.15s ease;
}

.tab-btn:hover {
  color: var(--text-primary);
}

.tab-btn.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}
```

Remove the old `.header`, `.header-content`, `.header-title`, `.logo`, `h1` gradient text, and old `.tab-bar`/`.tab-btn` styles.

**Step 7: Update App.test.jsx**

The test `it('renders header title')` checks for `screen.getByText('Cash Flow Projection')`. Update to check for `screen.getByText('PCG')` and `screen.getByText('Cashflow')`.

The test that clicks `.tab-btn` elements should still work since we kept that class name.

Update the test that checks `screen.getByText('Revenue & Proceeds')` — this text comes from ForecastTab section titles and should still be present.

**Step 8: Update DataEntryTab.test.jsx**

The test `it('renders placeholder when no import selected')` checks for `screen.getByText('Data Entry')`. This heading text should still be present in the tab content (not the header). Keep it.

Remove or update any test that queries the stage tab buttons inside DataEntryTab, since those have moved to the header's StagePills.

**Step 9: Run all tests**

Run: `cd frontend && npx vitest run`

Expected: All 120 tests pass (with the updates above).

**Step 10: Run lint**

Run: `cd frontend && npm run lint`

Expected: Clean.

**Step 11: Commit**

```bash
git add frontend/src/components/StagePills.jsx frontend/src/components/Header.jsx frontend/src/components/TabBar.jsx frontend/src/App.jsx frontend/src/App.css frontend/src/App.test.jsx frontend/src/components/tabs/DataEntryTab.jsx frontend/src/components/tabs/DataEntryTab.test.jsx
git commit -m "Add compact header with global stage selector"
```

---

### Task 3: Redesign Overview Tab (was Dashboard)

Replace the 11-card Dashboard with a compact KPI strip + structured summary panels. Remove NavCard component.

**Files:**
- Modify: `frontend/src/components/tabs/DashboardTab.jsx`
- Modify: `frontend/src/components/tabs/DashboardTab.test.jsx`
- Delete: `frontend/src/components/cards/NavCard.jsx`
- Modify: `frontend/src/components/cards/KpiCard.jsx`
- Modify: `frontend/src/components/cards/SummaryCard.jsx`
- Modify: `frontend/src/App.css`

**Step 1: Redesign KpiCard as a compact inline metric**

Replace `frontend/src/components/cards/KpiCard.jsx`:

```jsx
export default function KpiCard({ title, value, subtitle, trend = 'neutral' }) {
  return (
    <div className="kpi-metric">
      <span className="kpi-label">{title}</span>
      <span className={`kpi-value ${trend !== 'neutral' ? `kpi-${trend}` : ''}`}>{value}</span>
      {subtitle && <span className={`kpi-subtitle kpi-${trend}`}>{subtitle}</span>}
    </div>
  );
}
```

Note: `icon` prop removed — the KPI strip doesn't need icons. DashboardTab still passes `icon` but it's ignored harmlessly.

**Step 2: Redesign SummaryCard as a compact table panel**

Replace `frontend/src/components/cards/SummaryCard.jsx`:

```jsx
import { formatCurrency } from '../../utils/formatCurrency';
import { formatDelta } from '../../utils/formatDelta';

export default function SummaryCard({ title, icon: Icon, items = [], deltaBudgetDollar, deltaBudgetPct, deltaPrevDollar, deltaPrevPct, total, pctComplete }) {
  const budgetDelta = formatDelta(deltaBudgetDollar, 'dollar');
  const budgetPctDelta = formatDelta(deltaBudgetPct, 'percent');
  const prevDelta = formatDelta(deltaPrevDollar, 'dollar');
  const prevPctDelta = formatDelta(deltaPrevPct, 'percent');

  return (
    <div className="summary-panel">
      <div className="summary-panel-header">
        {Icon && <Icon size={14} />}
        <span className="summary-panel-title">{title}</span>
        <span className="summary-panel-total">{formatCurrency(total)}</span>
      </div>
      <div className="summary-panel-deltas">
        <div className="delta-row">
          <span className="delta-label">vs Budget</span>
          <span className={budgetDelta.className}>{budgetDelta.text}</span>
          <span className={budgetPctDelta.className}>{budgetPctDelta.text}</span>
        </div>
        <div className="delta-row">
          <span className="delta-label">vs Prev</span>
          <span className={prevDelta.className}>{prevDelta.text}</span>
          <span className={prevPctDelta.className}>{prevPctDelta.text}</span>
        </div>
      </div>
    </div>
  );
}
```

**Step 3: Update DashboardTab.jsx**

Key changes:
- Remove NavCard imports and nav card rendering
- Remove the `navMetrics` useMemo
- Update the layout to use KPI strip + 2x2 summary panel grid
- Remove the `onTabChange` prop (no more nav cards)

The updated render structure:

```jsx
return (
  <div className="overview-tab">
    <div className="kpi-strip">
      {/* KpiCard for each metric — same data derivation as before */}
    </div>
    <div className="summary-grid">
      {/* SummaryCard for Revenue, Development, Overheads, CapEx */}
    </div>
    <div className="import-history">
      {/* ImportPickerCard — collapsed by default */}
    </div>
  </div>
);
```

Remove `onTabChange` from props. The DashboardTab becomes self-contained.

**Step 4: Update App.jsx**

Remove `onTabChange={setActiveTab}` prop from DashboardTab:

```jsx
{activeTab === 'dashboard' && <DashboardTab />}
```

**Step 5: Update DashboardTab.test.jsx**

- Remove tests for nav cards (`it('renders navigation cards')`, `it('calls onTabChange when a nav card is clicked')`, `it('renders P&L net profit metric on nav card')`)
- Remove `onTabChange` from render calls
- Keep all KPI and summary card tests — update text matchers if card content changed

**Step 6: Add CSS for new overview layout**

```css
/* Overview Tab */
.overview-tab {
  padding: 24px;
  max-width: 1200px;
}

.kpi-strip {
  display: flex;
  gap: 32px;
  padding: 16px 0;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: 24px;
}

.kpi-metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kpi-label {
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-secondary);
}

.kpi-value {
  font-family: var(--font-mono);
  font-size: 20px;
  font-weight: 500;
  color: var(--text-primary);
}

.kpi-subtitle {
  font-family: var(--font-body);
  font-size: 11px;
}

.kpi-positive { color: var(--positive); }
.kpi-negative { color: var(--negative); }

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 24px;
}

.summary-panel {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  padding: 16px;
}

.summary-panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  color: var(--text-secondary);
}

.summary-panel-title {
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  flex: 1;
}

.summary-panel-total {
  font-family: var(--font-mono);
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
}

.summary-panel-deltas {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.summary-panel-deltas .delta-row {
  display: flex;
  gap: 12px;
  font-size: 12px;
}

.summary-panel-deltas .delta-label {
  color: var(--text-tertiary);
  min-width: 60px;
}

.import-history {
  border-top: 1px solid var(--border-subtle);
  padding-top: 16px;
}
```

Remove old Dashboard CSS (`.dashboard`, `.dashboard-kpi-row`, `.dashboard-summary-row`, `.dashboard-nav-row`, `.nav-card`, etc.)

**Step 7: Run tests**

Run: `cd frontend && npx vitest run`

Expected: All tests pass (with removed nav card tests).

**Step 8: Run lint**

Run: `cd frontend && npm run lint`

**Step 9: Commit**

```bash
git add -A
git commit -m "Redesign Dashboard as compact Overview tab"
```

---

### Task 4: Rebuild Forecast Tab as Continuous Grid

Replace the collapsible ForecastCard accordion with one continuous scrollable table. Section headers become inline divider rows. NCF moves to the bottom of the same table. Remove ForecastCard, DataSection, NcfSection, NcfDataRow, N12mDataRow components.

**Files:**
- Modify: `frontend/src/components/tabs/ForecastTab.jsx` (major rewrite)
- Modify: `frontend/src/components/tabs/ForecastTab.test.jsx`
- Delete: `frontend/src/components/cards/ForecastCard.jsx`
- Delete: `frontend/src/components/DataSection.jsx`
- Delete: `frontend/src/components/NcfSection.jsx`
- Delete: `frontend/src/components/NcfDataRow.jsx`
- Delete: `frontend/src/components/N12mDataRow.jsx`
- Delete: `frontend/src/components/StatsBar.jsx`
- Modify: `frontend/src/components/NcfSection.test.jsx` (delete or move)
- Modify: `frontend/src/App.jsx` (remove expandedSections state)
- Modify: `frontend/src/App.test.jsx`
- Modify: `frontend/src/App.css`

**Step 1: Rewrite ForecastTab as one continuous grid**

The new ForecastTab renders a single `<table>` with:
- A sticky month header row (with ACT/FCST badges per column)
- Section divider rows (REVENUE, DEVELOPMENT, etc.) as `<tr>` with colspan
- Data rows for each line item using `formatCurrency`
- Calculated rows styled differently (dimmed, with diamond marker)
- NCF cumulative and periodic rows at the bottom
- A KPI strip at the top (inline, not a separate StatsBar component)

```jsx
import { useMemo } from 'react';
import { Loader } from 'lucide-react';
import { formatCurrency } from '../../utils/formatCurrency';

const SECTION_ORDER = ['revenue', 'development', 'overheads', 'capex', 'contingency'];
const SECTION_LABELS = {
  revenue: 'Revenue & Proceeds',
  development: 'Development Costs',
  overheads: 'Development Overheads',
  capex: 'Capital Expenditures',
  contingency: 'Contingency Items',
};

const SERIES_LABELS = { current: 'Current', previous: 'Previous', budget: 'Budget', max: 'Max', min: 'Min' };

function formatMonth(m) {
  if (!m) return '';
  const d = new Date(m + '-01');
  return d.toLocaleDateString('en-AU', { month: 'short', year: '2-digit' }).replace(' ', '-');
}

export default function ForecastTab({ ncfData, n12mData, months, loading, error }) {
  const actualFlags = n12mData?.actual_flags || [];

  const kpis = useMemo(() => {
    if (!n12mData?.sections) return null;
    const getValues = (section, key) =>
      n12mData.sections[section]?.items?.find(i => i.key === key)?.values || [];
    const sum = vals => vals.reduce((a, v) => a + (v || 0), 0);
    const netRev = sum(getValues('revenue', 'net_revenue_proceeds'));
    const devSub = sum(getValues('development', 'subtotal_inventory_capex'));
    const ovhSub = sum(getValues('overheads', 'subtotal_dev_overheads'));
    const grossCF = netRev - devSub - ovhSub;
    const period = months?.length >= 2
      ? `${formatMonth(months[0])} \u2013 ${formatMonth(months[months.length - 1])}`
      : '';
    return { netRev, grossCF, period };
  }, [n12mData, months]);

  if (loading) {
    return (
      <div className="loading-container">
        <Loader className="loading-spinner" size={24} />
        <span>Loading financial data...</span>
      </div>
    );
  }

  if (error) {
    return <div className="error-banner">{error}</div>;
  }

  const displayMonths = (months || []).map(m => formatMonth(m));

  return (
    <div className="forecast-tab">
      {kpis && (
        <div className="kpi-strip">
          <div className="kpi-metric">
            <span className="kpi-label">Net Revenue</span>
            <span className="kpi-value">{formatCurrency(kpis.netRev)}</span>
          </div>
          <div className="kpi-metric">
            <span className="kpi-label">Gross Cash Flow</span>
            <span className="kpi-value">{formatCurrency(kpis.grossCF)}</span>
          </div>
          <div className="kpi-metric">
            <span className="kpi-label">Period</span>
            <span className="kpi-value kpi-period">{kpis.period}</span>
          </div>
        </div>
      )}

      <div className="forecast-grid-wrapper">
        <table className="forecast-table">
          <thead>
            <tr>
              <th className="row-label-header"></th>
              {displayMonths.map((m, i) => (
                <th key={i} className={`month-col ${actualFlags[i] ? 'actual' : 'forecast'}`}>
                  <span className="month-name">{m}</span>
                  <span className={`month-badge ${actualFlags[i] ? 'actual' : 'forecast'}`}>
                    {actualFlags[i] ? 'ACT' : 'FCST'}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {SECTION_ORDER.map(sectionKey => {
              const items = n12mData?.sections?.[sectionKey]?.items || [];
              return [
                <tr key={`section-${sectionKey}`} className="section-divider-row">
                  <td colSpan={displayMonths.length + 1}>{SECTION_LABELS[sectionKey]}</td>
                </tr>,
                ...items.map(item => (
                  <tr key={item.key} className={`data-row${item.is_calculated ? ' calculated' : ''}`}>
                    <td className="row-label">
                      {item.is_calculated && <span className="calc-indicator">\u25C6</span>}
                      {item.label}
                    </td>
                    {(item.values || []).map((val, i) => (
                      <td key={i} className={`data-cell ${actualFlags[i] ? 'actual' : 'forecast'}`}>
                        <span className="calculated-value">{formatCurrency(val)}</span>
                      </td>
                    ))}
                  </tr>
                )),
              ];
            })}

            {/* Metrics section (settlements) */}
            {n12mData?.sections?.metrics?.items?.map(item => (
              <tr key={item.key} className="data-row">
                <td className="row-label">{item.label}</td>
                {(item.values || []).map((val, i) => (
                  <td key={i} className="data-cell">
                    <span className="calculated-value">{formatCurrency(val)}</span>
                  </td>
                ))}
              </tr>
            ))}

            {/* NCF Section */}
            {ncfData && (
              <>
                <tr className="section-divider-row">
                  <td colSpan={displayMonths.length + 1}>Net Cash Flow (NCF)</td>
                </tr>
                <tr className="section-divider-row sub">
                  <td colSpan={displayMonths.length + 1}>Cumulative</td>
                </tr>
                {Object.keys(ncfData.cumulative || {}).map(seriesKey => (
                  <tr key={`cum-${seriesKey}`} className="data-row">
                    <td className="row-label">{SERIES_LABELS[seriesKey] || seriesKey}</td>
                    {(ncfData.cumulative[seriesKey] || []).map((val, i) => (
                      <td key={i} className="data-cell">
                        <span className="calculated-value">{formatCurrency(val)}</span>
                      </td>
                    ))}
                  </tr>
                ))}
                <tr className="section-divider-row sub">
                  <td colSpan={displayMonths.length + 1}>Periodic</td>
                </tr>
                {Object.keys(ncfData.periodic || {}).map(seriesKey => (
                  <tr key={`per-${seriesKey}`} className="data-row">
                    <td className="row-label">{SERIES_LABELS[seriesKey] || seriesKey}</td>
                    {(ncfData.periodic[seriesKey] || []).map((val, i) => (
                      <td key={i} className="data-cell">
                        <span className="calculated-value">{formatCurrency(val)}</span>
                      </td>
                    ))}
                  </tr>
                ))}
              </>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

**Step 2: Update App.jsx**

Remove `expandedSections` state and `toggleSection` function. Remove those props from ForecastTab:

```jsx
{activeTab === 'forecast' && (
  <ForecastTab
    ncfData={ncfData} n12mData={n12mData} months={months}
    loading={loading} error={error}
  />
)}
```

**Step 3: Delete old components**

Delete these files:
- `frontend/src/components/cards/ForecastCard.jsx`
- `frontend/src/components/DataSection.jsx`
- `frontend/src/components/NcfSection.jsx`
- `frontend/src/components/NcfDataRow.jsx`
- `frontend/src/components/N12mDataRow.jsx`
- `frontend/src/components/StatsBar.jsx`

**Step 4: Delete NcfSection.test.jsx**

Delete `frontend/src/components/NcfSection.test.jsx` — the NcfSection component no longer exists. The NCF rendering is now tested via ForecastTab tests.

**Step 5: Update ForecastTab.test.jsx**

Update tests to match the new continuous table structure:
- `it('renders section titles')` — check for 'Revenue & Proceeds', 'Development Costs', etc. as table text
- `it('renders NCF section')` — check for 'Net Cash Flow (NCF)', 'Current', 'Budget'
- `it('renders loading state')` — unchanged
- `it('renders error state')` — unchanged
- `it('renders KPI strip')` — check for 'Net Revenue', 'Gross Cash Flow', 'Period'
- `it('renders month headers')` — check for month text in table headers
- Remove test for expandedSections/toggleSection (no longer applicable)
- Remove test for forecast card summary metrics (cards are gone)

**Step 6: Update App.test.jsx**

- Remove assertions for `expandedSections` and related toggle behavior
- Update text checks: 'Revenue & Proceeds' should still appear
- Update/remove queries for `.data-grid` class (now `.forecast-table`)
- Keep `.month-headers` check or update to new class name — update to query `th.month-col` elements instead
- Keep `.row-label` check (class name preserved)
- Update `.section-content` check (now `tbody` or `.forecast-grid-wrapper`)

**Step 7: Add CSS for continuous forecast grid**

```css
/* Forecast Tab */
.forecast-tab {
  padding: 24px;
}

.forecast-grid-wrapper {
  overflow-x: auto;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
}

.forecast-table {
  width: 100%;
  min-width: 1280px;
  border-collapse: collapse;
  font-family: var(--font-mono);
  font-size: 13px;
}

.forecast-table thead {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--bg-surface);
}

.forecast-table th {
  padding: 8px 12px;
  text-align: right;
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-medium);
}

.forecast-table th.row-label-header {
  width: 200px;
  text-align: left;
}

.month-col {
  text-align: center !important;
}

.month-col.forecast {
  background: var(--forecast-bg);
}

.month-col.actual {
  background: var(--actual-bg);
}

.month-name {
  display: block;
  font-size: 12px;
}

.month-badge {
  display: inline-block;
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.05em;
  padding: 1px 4px;
  border-radius: 2px;
  margin-top: 2px;
}

.month-badge.actual {
  color: var(--positive);
  background: rgba(107, 186, 110, 0.1);
}

.month-badge.forecast {
  color: var(--accent);
  background: var(--accent-muted);
}

.section-divider-row td {
  padding: 10px 12px 4px;
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-secondary);
  border-top: 1px solid var(--border-medium);
  background: var(--bg-elevated);
}

.section-divider-row.sub td {
  font-size: 10px;
  font-weight: 500;
  padding: 6px 12px 2px;
  border-top: none;
  background: transparent;
  color: var(--text-tertiary);
}

.forecast-table .data-row td {
  padding: 4px 12px;
  border-bottom: 1px solid var(--border-subtle);
}

.forecast-table .data-row.calculated td {
  color: var(--calc-text);
}

.forecast-table .row-label {
  text-align: left;
  font-family: var(--font-body);
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
}

.forecast-table .data-cell {
  text-align: right;
  color: var(--text-primary);
}

.forecast-table .data-cell.forecast {
  background: var(--forecast-bg);
}

.forecast-table .data-cell.actual {
  background: var(--actual-bg);
}

.kpi-period {
  font-family: var(--font-body) !important;
  font-size: 15px !important;
}
```

Remove old forecast-card CSS, stats-bar CSS, data-grid CSS (partially — keep what DataEntryGrid still uses).

**Step 8: Run tests**

Run: `cd frontend && npx vitest run`

Expected: All tests pass.

**Step 9: Run lint**

Run: `cd frontend && npm run lint`

**Step 10: Commit**

```bash
git add -A
git commit -m "Rebuild Forecast tab as continuous grid table"
```

---

### Task 5: Align Data Entry Tab Styling

Update DataEntryGrid and DataEntryTab to use the new amber-accent dirty/calculated styling and match the Forecast tab's table appearance. The action bar (unsaved count, Discard, Save) moves into the tab header area.

**Files:**
- Modify: `frontend/src/components/tabs/DataEntryTab.jsx`
- Modify: `frontend/src/components/DataEntryGrid.jsx`
- Modify: `frontend/src/App.css`
- Modify: `frontend/src/components/DataEntryGrid.test.jsx`

**Step 1: Update DataEntryGrid styling**

The grid already works well. Key CSS changes:
- Dirty cells: amber left border + faint amber background (using `var(--dirty)`, `var(--dirty-bg)`, `var(--dirty-border)`)
- Calculated preview: amber text (`var(--calc-preview)`)
- Section dividers: match forecast tab's `section-divider-row` style
- All values in `var(--font-mono)`
- Inputs: `var(--bg-input)` background, `var(--border-strong)` focus border in amber

No structural changes to DataEntryGrid.jsx — the component logic stays the same. Only CSS class styling changes.

**Step 2: Update DataEntryTab action bar**

Move the action bar (unsaved count + Discard + Save) to sit between the tab heading and the grid, styled as a compact strip:

```css
.entry-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  font-size: 12px;
}

.dirty-count {
  font-family: var(--font-mono);
  color: var(--accent);
  font-size: 12px;
}
```

**Step 3: Update CSS for data entry grid**

Update existing data entry CSS classes to use the new variables:

```css
.cell-dirty {
  border-left: 3px solid var(--dirty-border);
  background: var(--dirty-bg);
}

.dirty-row {
  background: var(--dirty-bg);
}

.cell-preview .calculated-value {
  color: var(--calc-preview);
  font-style: italic;
}

.data-input {
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 13px;
}

.data-input:focus {
  border-color: var(--accent);
  outline: none;
  box-shadow: 0 0 0 1px var(--accent-muted);
}
```

**Step 4: Run tests**

Run: `cd frontend && npx vitest run`

Expected: All tests pass. CSS-only changes don't break tests.

**Step 5: Commit**

```bash
git add frontend/src/components/tabs/DataEntryTab.jsx frontend/src/components/DataEntryGrid.jsx frontend/src/App.css
git commit -m "Align Data Entry tab with warm ledger theme"
```

---

### Task 6: Clean Up Stages and P&L Tabs

Update StageComparisonTab and PnLTab to use the new theme variables and table styling. Minimal structural changes.

**Files:**
- Modify: `frontend/src/components/tabs/StageComparisonTab.jsx`
- Modify: `frontend/src/components/tabs/PnLTab.jsx`
- Modify: `frontend/src/App.css`

**Step 1: Update StageComparisonTab**

Key changes:
- Stage overview cards: use `var(--bg-surface)`, `var(--border-subtle)`, amber accent for active
- View toggle buttons: amber accent for active state
- Table: use `var(--font-mono)` for values, `var(--border-subtle)` for rules
- Subtotal rows: amber background tint instead of purple
- Delta colors: `var(--positive)` / `var(--negative)`

These are CSS-only changes. The component JSX stays the same.

**Step 2: Update PnLTab**

Key changes:
- Table: `var(--font-mono)` for all values
- Highlight rows (Gross Profit, Net Profit): amber background tint
- Margin cards: `var(--bg-surface)` background, amber value color
- Delta colors: `var(--positive)` / `var(--negative)`

CSS-only changes. Component JSX stays the same.

**Step 3: Update CSS**

Replace old stage comparison and P&L colors with variable references. Key replacements:

```css
/* Stage overview cards */
.stage-overview-card.active {
  border-color: var(--accent);
  background: var(--accent-muted);
}

/* View toggle */
.toggle-btn.active {
  background: var(--accent);
  color: var(--bg-deep);
}

/* Stage table */
.stage-table th {
  font-family: var(--font-body);
  color: var(--text-secondary);
}

.stage-table td {
  font-family: var(--font-mono);
}

.subtotal-row {
  background: var(--accent-glow);
  font-weight: 500;
}

/* P&L */
.pnl-highlight {
  background: var(--accent-glow);
}

.pnl-table td {
  font-family: var(--font-mono);
}

.margin-value {
  font-family: var(--font-mono);
  color: var(--accent);
}

/* Delta colors */
.delta-positive { color: var(--positive); }
.delta-negative { color: var(--negative); }
.delta-neutral { color: var(--neutral); }
```

**Step 4: Run tests**

Run: `cd frontend && npx vitest run`

Expected: All tests pass. CSS-only changes.

**Step 5: Commit**

```bash
git add frontend/src/components/tabs/StageComparisonTab.jsx frontend/src/components/tabs/PnLTab.jsx frontend/src/App.css
git commit -m "Apply warm ledger theme to Stages and P&L tabs"
```

---

### Task 7: Animation, Scroll Polish, and Responsive

Add crisp transitions, scroll fade indicators, sticky columns, and responsive breakpoints.

**Files:**
- Modify: `frontend/src/App.css`

**Step 1: Tab transition animations**

```css
/* Tab content transition */
.main-content > * {
  animation: fadeIn 200ms ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* KPI strip stagger */
.kpi-strip .kpi-metric:nth-child(1) { animation-delay: 0ms; }
.kpi-strip .kpi-metric:nth-child(2) { animation-delay: 60ms; }
.kpi-strip .kpi-metric:nth-child(3) { animation-delay: 120ms; }
.kpi-strip .kpi-metric:nth-child(4) { animation-delay: 180ms; }

.kpi-strip .kpi-metric {
  animation: fadeIn 200ms ease-out backwards;
}
```

**Step 2: Scroll fade indicator**

```css
.forecast-grid-wrapper {
  position: relative;
}

.forecast-grid-wrapper::after {
  content: '';
  position: sticky;
  right: 0;
  top: 0;
  bottom: 0;
  width: 40px;
  background: linear-gradient(to right, transparent, var(--bg-deep));
  pointer-events: none;
  z-index: 5;
}
```

Note: The `::after` on a scrolling container is tricky. If it doesn't work well, implement via a JS scroll listener that toggles a class. Evaluate during visual check.

**Step 3: Sticky first column**

```css
.forecast-table .row-label,
.forecast-table th.row-label-header {
  position: sticky;
  left: 0;
  z-index: 5;
  background: var(--bg-deep);
}

.forecast-table thead th.row-label-header {
  background: var(--bg-surface);
  z-index: 11;
}
```

**Step 4: Row hover**

```css
.forecast-table .data-row:hover td {
  background: var(--accent-glow);
  transition: background 100ms ease;
}
```

**Step 5: Responsive breakpoints**

```css
@media (max-width: 1400px) {
  .forecast-table {
    min-width: 1000px;
  }
  .summary-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 1024px) {
  .stage-pills {
    display: none; /* Collapse to dropdown on tablet — future enhancement */
  }
  .kpi-strip {
    flex-wrap: wrap;
    gap: 16px;
  }
  .summary-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .header-line-1 {
    padding: 8px 12px;
  }
  .header-line-2 {
    padding: 0 12px;
  }
  .tab-btn {
    padding: 8px 10px;
    font-size: 11px;
  }
  .tab-btn svg {
    display: none;
  }
  .forecast-tab,
  .overview-tab {
    padding: 12px;
  }
  .kpi-strip {
    flex-direction: column;
    gap: 8px;
  }
}
```

**Step 6: Interaction transitions**

```css
/* Cell focus */
.data-input:focus {
  transition: border-color 150ms ease;
}

/* Dirty cell appearance */
.cell-dirty {
  transition: border-left-width 200ms ease, background 200ms ease;
}

/* Button hover */
.btn, .stage-pill, .toggle-btn {
  transition: all 150ms ease;
}
```

**Step 7: Clean up old animations**

Remove old `@keyframes slideUp` and `expandDown` animations from App.css if no longer referenced.

**Step 8: Run tests**

Run: `cd frontend && npx vitest run`

Expected: All tests pass. CSS-only.

**Step 9: Run lint**

Run: `cd frontend && npm run lint`

**Step 10: Commit**

```bash
git add frontend/src/App.css
git commit -m "Add animations, scroll polish, and responsive breakpoints"
```

---

### Task 8: Final Cleanup and CSS Audit

Remove all dead CSS, unused imports, and verify no purple remnants. Run full test suite.

**Files:**
- Modify: `frontend/src/App.css`
- Possibly modify: any component with unused imports

**Step 1: Remove dead CSS**

Search App.css for any class that is no longer referenced by any component:
- Old `.header-content`, `.logo`, `h1` gradient styles
- Old `.nav-card` styles
- Old `.forecast-card` styles
- Old `.stats-bar`, `.stat-card` (if fully replaced by `.kpi-strip`)
- Old DataSection styles
- Any remaining purple color references (`#bb86fc`, `#7c4dff`, `rgba(187, 134, 252, ...)`)

**Step 2: Remove unused component imports from App.jsx**

If StatsBar, NcfSection, etc. were deleted in Task 4, verify their imports are also removed from App.jsx and ForecastTab.jsx.

**Step 3: Run full test suite**

Run: `cd frontend && npx vitest run`

Expected: All tests pass.

**Step 4: Run lint**

Run: `cd frontend && npm run lint`

Expected: Clean (no unused imports, no errors).

**Step 5: Visual audit**

Run: `cd frontend && npm run dev`

Walk through every tab and verify:
- Overview: KPI strip + 4 summary panels + import picker
- Forecast: continuous table with section dividers, ACT/FCST badges, sticky header and first column
- Stages: themed stage cards, table with amber subtotals
- P&L: themed table with amber highlights and margin cards
- Data Entry: amber dirty indicators, calc preview, keyboard nav still works
- Header: compact 2-line, PCG Cashflow title, stage pills with dirty dots
- No purple anywhere
- Paper grain texture visible
- All fonts correct (Fraunces headings, Geist labels, IBM Plex Mono values)

**Step 6: Commit**

```bash
git add -A
git commit -m "Clean up dead CSS and remove purple remnants"
```

---

### Task 9: Run Backend Tests (Sanity Check)

Verify that no backend behavior was affected.

**Step 1: Run backend tests**

Run: `docker compose exec -e PYTHONPATH=/app backend python -m pytest --tb=short`

Expected: All 66 tests pass. Zero backend changes were made.

**Step 2: Build production Docker image**

Run: `docker build -f Dockerfile.prod -t cashflow-prod .`

Expected: Build succeeds. Frontend builds cleanly inside the Docker image.
