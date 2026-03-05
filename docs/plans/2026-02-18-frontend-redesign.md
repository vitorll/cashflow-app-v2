# Frontend Redesign — Design Concept

**Date**: 2026-02-18
**Status**: Draft
**Type**: UX/Visual Design

---

## 1. Design Philosophy

### Who Uses This

Finance professionals managing $50M+ property development portfolios. They spend hours in Excel, they scan numbers fast, and they care about precision. This tool replaces their spreadsheets — it must feel **more trustworthy and more efficient** than Excel, not just prettier.

### Core Principle: The Precision Instrument

Every decision in this redesign serves one question: **does this help a finance professional move faster and trust the numbers more?**

Three pillars:

1. **Density over decoration** — Financial users want information, not whitespace. Cards with 3 numbers each waste screen real estate. Structured tables with good typography convey 10x more data in the same space.
2. **Numbers are the hero** — Typography, alignment, and color should make financial figures instantly scannable. Monospace for all values. Proper right-alignment. Red/green only where it means something.
3. **Data entry is the product** — The grid isn't a secondary feature tucked behind tabs. It's the reason this app exists. Everything else supports it.

### Aesthetic Direction: "Warm Ledger"

A modern take on precision financial instruments with warmth. Not the cold blue-black of every generic dark dashboard. Think: aged paper under lamplight, brass instruments, architectural blueprints — the materials of property development and finance intersecting.

- **Warm dark** palette (charcoal with amber undertones, not blue-black)
- **Gold/amber** accent (money, precision, trust — not the overused purple-on-dark)
- **Serif display** type for headings (authority, editorial quality)
- **Monospace** for all financial figures (alignment, clarity, professionalism)
- **Subtle texture** — faint paper grain on surfaces, not flat matte

---

## 2. Color System

```
Background
  --bg-deep:       #141210       (deepest layer — page background)
  --bg-surface:    #1c1a17       (cards, panels)
  --bg-elevated:   #252220       (hover states, active panels, modals)
  --bg-input:      #1e1c19       (input fields)

Borders & Dividers
  --border-subtle: #2a2723       (section dividers, card edges)
  --border-medium: #3a3630       (table rules, active borders)
  --border-strong: #4a4540       (focused input borders)

Text
  --text-primary:  #e8e4de       (primary content — warm white)
  --text-secondary:#9b9590       (labels, captions, secondary info)
  --text-tertiary: #6b6560       (disabled, placeholders)

Accent (Amber/Gold)
  --accent:        #d4a054       (primary interactive — buttons, links, active tab)
  --accent-hover:  #e0b06a       (hover state)
  --accent-muted:  rgba(212, 160, 84, 0.15)  (subtle highlights, selected row bg)
  --accent-glow:   rgba(212, 160, 84, 0.08)  (ambient glow behind key elements)

Semantic
  --positive:      #6bba6e       (profit, positive delta)
  --negative:      #d45b56       (loss, negative delta)
  --neutral:       #9b9590       (zero change, informational)
  --forecast:      rgba(212, 160, 84, 0.4)   (forecast months — amber tint)
  --actual:        rgba(107, 186, 110, 0.15)  (actual months — green tint)

Dirty/Changed State
  --dirty:         #d4a054       (unsaved change indicator — same as accent)
  --dirty-bg:      rgba(212, 160, 84, 0.08)  (dirty row background)
  --dirty-border:  rgba(212, 160, 84, 0.4)   (dirty cell left border)

Calculated/Preview
  --calc-text:     #7a7570       (calculated cell values — dimmed)
  --calc-preview:  #b09060       (preview of recalculated value — amber-ish)
```

---

## 3. Typography System

```
Display / Page Headings
  Font:    "Fraunces", serif
  Weight:  600
  Sizes:   28px (page title), 20px (section heading)
  Color:   --text-primary
  Usage:   App title, tab headings, section headers
  Note:    Fraunces is a variable optical-size serif — warm, authoritative,
           distinctly NOT generic. It has a slight softness that avoids
           feeling stuffy.

Labels / UI Chrome
  Font:    "Geist", sans-serif
  Weight:  400 (body), 500 (labels), 600 (buttons)
  Sizes:   13px (body), 11px (labels/captions), 12px (buttons)
  Tracking: 0.02em (body), 0.06em (uppercase labels)
  Color:   --text-secondary for labels, --text-primary for body
  Usage:   Tab labels, button text, form labels, table headers, tooltips

Financial Figures
  Font:    "IBM Plex Mono", monospace
  Weight:  400 (values), 500 (totals/subtotals)
  Sizes:   13px (table cells), 15px (KPI values), 20px (hero metrics)
  Color:   --text-primary (standard), --positive/--negative (deltas)
  Usage:   ALL numbers. Every financial value. No exceptions.
  Note:    Right-aligned in tables. Tabular figures. Parentheses for negatives.
```

**Font Loading:**
```
Google Fonts:
  Fraunces:     wght@600  (display only — single weight keeps payload small)
  IBM Plex Mono: wght@400;500
  Geist:         wght@400;500;600   (from CDN or self-hosted)
```

---

## 4. Layout Architecture

### Current Problems

1. **Tab navigation is flat** — 5 tabs treated equally, but Data Entry is the primary use case
2. **Card soup on Dashboard** — 4 KPI cards + 4 summary cards + 3 nav cards = 11 cards competing for attention
3. **No persistent context** — switching tabs loses all context about what you were looking at
4. **Header is wasted space** — just an app title and tabs, taking up 100px+ of vertical space

### Proposed Layout

```
┌──────────────────────────────────────────────────────────┐
│  ▌ PCG Cashflow              [S1] [S2] [S3] [S4] [S5]   │
│  ▌ Report: Sep 2025 (Current)    ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌   │
│  ├──────┬──────────┬────────┬─────┬────────────────────── │
│  │ ⊞    │ 12-Month │ Stages │ P&L │                      │
│  │      │ Forecast │        │     │                      │
│  ├──────┴──────────┴────────┴─────┴────────────────────── │
│  │                                                        │
│  │  [ Main content area — full width ]                    │
│  │                                                        │
│  │                                                        │
│  │                                                        │
│  │                                                        │
│  │                                                        │
│  │                                                        │
│  │                                                        │
│  │                                                        │
│  │                                                        │
│  └────────────────────────────────────────────────────────┘
```

**Key changes:**

1. **Compact header (2 lines)** — App name + report context on line 1. Stage selector (S1-S5) on the right — always visible, not buried in Data Entry tab. Line 2 is the tab bar.

2. **Dashboard becomes ⊞ (Overview)** — A compact grid icon, first tab. It's a landing page, not the primary workspace. Renamed to "Overview" to signal it's a summary, not the main event.

3. **Stage selector is global** — The S1/S2/S3/S4/S5 pills in the header apply across ALL tabs. Viewing Forecast? See S1's forecast. Viewing P&L? See S1's P&L. This eliminates the disconnect between data entry (which is per-stage) and reporting (which currently only shows WOP).

4. **Data Entry is implicit** — Every view IS the data entry view when you click into a cell. The grid is always live. The current "Data Entry" tab becomes the default state of the Forecast tab — a unified grid that's both viewable and editable. Read-only tabs (Stages, P&L) remain read-only.

   **Important caveat:** This is a UX evolution, not a rewrite. For v1 of the redesign, we keep Data Entry as a separate tab but move the stage selector to the header and visually promote it.

### Detailed View Layouts

#### Overview Tab (was "Dashboard")

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  NET REVENUE      GROSS CF        NET CF        PERIOD  │
│  $42.3M           $18.7M          $12.1M       Sep 25   │
│  ▲ +2.1% vs Prev  ▲ +1.8%        ▼ -0.4%      Current  │
│                                                         │
│ ─────────────────────────────────────────────────────── │
│                                                         │
│  Revenue                          Development           │
│  ┌─────────────────────────┐     ┌───────────────────┐  │
│  │ Gross Revenue  $52.3M   │     │ Home Build  $28.1M│  │
│  │ Selling Costs  ($10.0M) │     │ Contingency  $1.2M│  │
│  │ Net Revenue    $42.3M   │     │ Subtotal    $29.3M│  │
│  │ ─── vs Budget ─── ──── │     │ ─── vs Budget ─── │  │
│  │ Δ  +$1.2M     +2.9%    │     │ Δ  -$0.8M   -2.7% │  │
│  │ ─── vs Prev ─── ───── │     │ ─── vs Prev ─── ── │  │
│  │ Δ  +$0.9M     +2.1%    │     │ Δ  -$0.3M   -1.0% │  │
│  └─────────────────────────┘     └───────────────────┘  │
│                                                         │
│  Overheads                        CapEx                 │
│  ┌─────────────────────────┐     ┌───────────────────┐  │
│  │ Marketing       $3.2M   │     │ Estate Works $8.1M│  │
│  │ LPC Overheads   $2.1M   │     │ Civils       $5.4M│  │
│  │ Subtotal        $5.3M   │     │ ...more rows...   │  │
│  │ ─── vs Budget ─── ──── │     │ Subtotal    $22.3M│  │
│  │ Δ  +$0.1M     +1.9%    │     │ ─── vs Budget ─── │  │
│  └─────────────────────────┘     └───────────────────┘  │
│                                                         │
│  ▸ Import History (3 versions)                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Changes from current:**
- KPI row is tighter — one horizontal strip, not 4 separate cards
- Summary sections are compact tables inside bordered panels, not cards with progress bars
- Delta comparisons are inline, not hidden behind hover states
- "Nav Cards" to other tabs are removed — the tab bar is right there
- Import version picker is collapsed into a collapsible "Import History" section at the bottom

#### 12-Month Forecast Tab

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  FORECAST — Stage 1                 ◉ Actual  ○ Fcst   │
│                                                         │
│ ──────────┬───────┬───────┬───────┬───────┬─────── ... │
│           │ Sep25 │ Oct25 │ Nov25 │ Dec25 │ Jan26       │
│           │  ACT  │  ACT  │  ACT  │ FCST  │ FCST        │
│ ──────────┼───────┼───────┼───────┼───────┼─────── ... │
│           │       │       │       │ ░░░░░ │ ░░░░░       │
│ REVENUE   │       │       │       │ ░░░░░ │ ░░░░░       │
│ ──────────┼───────┼───────┼───────┼───────┼───────      │
│ Gross Rev │ 4,321 │ 3,890 │ 4,102 │ 3,800 │ 4,200      │
│ Selling   │  (432)│  (389)│  (410)│  (380)│  (420)     │
│ Net Rev ◆ │ 3,889 │ 3,501 │ 3,692 │ 3,420 │ 3,780      │
│           │       │       │       │       │             │
│ DEVELOPMT │       │       │       │       │             │
│ ──────────┼───────┼───────┼───────┼───────┼───────      │
│ Home Build│ 2,100 │ 1,980 │ 2,340 │ 2,100 │ 2,200      │
│ Contingncy│   120 │   110 │   130 │   120 │   125      │
│ Subtotal ◆│ 2,220 │ 2,090 │ 2,470 │ 2,220 │ 2,325      │
│           │       │       │       │       │             │
│ ...       │       │       │       │       │             │
│           │       │       │       │       │             │
│ NET CF    │       │       │       │       │             │
│ ──────────┼───────┼───────┼───────┼───────┼───────      │
│ Cumulative│15,230 │16,891 │18,002 │19,100 │20,340      │
│ ──────────┴───────┴───────┴───────┴───────┴───────      │
│                                                         │
│  ◆ = Calculated                                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Key design decisions:**
- Forecast months get a subtle **amber-tinted background stripe** (`░░░░`) to distinguish from actuals (which have a faint green tint)
- **Month header row** shows ACT/FCST status badges, not just dashed borders
- Section headers (REVENUE, DEVELOPMT, etc.) are **inline row dividers** with uppercase Geist labels, not collapsible cards
- Calculated rows marked with **◆** diamond, dimmed text
- NCF section is **at the bottom of the same grid**, not a separate collapsible section — one continuous scrollable table
- All values in **IBM Plex Mono**, right-aligned, parentheses for negatives

#### Data Entry Tab

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  DATA ENTRY — Stage 1            3 unsaved │⟲ Discard│💾│
│                                                         │
│ ──────────┬───────┬───────┬───────┬───────┬─────── ... │
│           │ Sep25 │ Oct25 │ Nov25 │ Dec25 │ Jan26       │
│ ──────────┼───────┼───────┼───────┼───────┼─────── ... │
│           │       │       │       │       │             │
│ REVENUE   │       │       │       │       │             │
│ ──────────┼───────┼───────┼───────┼───────┼───────      │
│ Gross Rev │ 4,321 │ 3,890 │[4,500]│ 3,800 │ 4,200      │
│ Selling   │  (432)│  (389)│  (410)│  (380)│  (420)     │
│ Net Rev ◆ │ 3,889 │ 3,501 │ 4,090▴│ 3,420 │ 3,780      │
│           │       │       │       │       │             │
│ ...                                                     │
│                                                         │
│  [4,500] = dirty cell (amber border + bg tint)          │
│  4,090▴  = live-recalculated preview (amber text)       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Data Entry specifics:**
- **Dirty cells**: amber left border + faint amber background tint
- **Calculated preview**: amber-colored monospace text with ▴ indicator
- **Action bar**: integrated into the tab heading line — "3 unsaved" counter + Discard + Save buttons, always visible
- Stage dirty dots appear on the **S1-S5 pills in the header**
- Focused cell gets a **strong amber border** (2px solid)

#### Stage Comparison Tab

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  STAGE COMPARISON                                       │
│                                                         │
│ ──────────┬──────────┬──────────┬──────────┬────── ... │
│           │    S1    │    S2    │    S3    │    S4       │
│           │ Bgt  Cur │ Bgt  Cur │ Bgt  Cur │ Bgt  Cur   │
│ ──────────┼──────────┼──────────┼──────────┼──────      │
│ Gross Rev │ 52.3 54.1│ 38.2 39.0│ 41.1 40.8│ ...       │
│ Selling   │ (5.2)(5.4)│(3.8)(3.9)│(4.1)(4.1)│          │
│ Net Rev   │ 47.1 48.7│ 34.4 35.1│ 37.0 36.7│          │
│ ...       │          │          │          │            │
│ ──────────┼──────────┼──────────┼──────────┼──────      │
│ Net CF    │ 12.1 12.8│  8.9  9.2│  9.4  9.1│          │
│ ──────────┼──────────┼──────────┼──────────┼──────      │
│  Δ Budget │   +0.7   │   +0.3   │   -0.3   │          │
│  Δ %      │  +5.8%   │  +3.4%   │  -3.2%   │          │
│ ──────────┴──────────┴──────────┴──────────┴──────      │
│                                                         │
│  Click stage header to expand → shows all line items    │
│  for that stage with Budget, Current, Δ$, Δ%           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### P&L Tab

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  PROFIT & LOSS                                          │
│                                                         │
│ ─────────────────┬──────────┬──────────┬──────────      │
│                  │  Budget  │ Current  │    Δ           │
│ ─────────────────┼──────────┼──────────┼──────────      │
│ Gross Revenue    │  $52.3M  │  $54.1M  │  +$1.8M       │
│ Selling Costs    │  ($5.2M) │  ($5.4M) │  ($0.2M)      │
│ Net Revenue      │  $47.1M  │  $48.7M  │  +$1.6M       │
│ ─────────────────┼──────────┼──────────┼──────────      │
│ Development      │  $29.3M  │  $28.5M  │  +$0.8M       │
│ Overheads        │   $5.3M  │   $5.4M  │  ($0.1M)      │
│ ─────────────────┼──────────┼──────────┼──────────      │
│ GROSS PROFIT     │  $12.5M  │  $14.8M  │  +$2.3M  ▲    │
│ Gross Margin     │   26.5%  │   30.4%  │  +3.9pp        │
│ ─────────────────┼──────────┼──────────┼──────────      │
│ CapEx            │  $22.3M  │  $21.8M  │  +$0.5M       │
│ ─────────────────┼──────────┼──────────┼──────────      │
│ NET PROFIT       │  ($9.8M) │  ($7.0M) │  +$2.8M  ▲    │
│ Net Margin       │  -20.8%  │  -14.4%  │  +6.4pp        │
│ ─────────────────┴──────────┴──────────┴──────────      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 5. Component Redesign Map

### What Changes

| Current Component | Redesign | Notes |
|---|---|---|
| `Header.jsx` | **HeaderBar** | 2-line compact header: title + report context + stage pills on line 1, tabs on line 2 |
| `StatsBar.jsx` | **KpiStrip** | Single horizontal row of 3-4 metrics, not separate cards |
| `DataSection.jsx` | **Remove** | Replace with inline section divider rows within the grid table |
| `NcfSection.jsx` | **Remove** | NCF becomes rows at the bottom of the Forecast grid |
| `NcfDataRow.jsx` | **Remove** | Unified row component handles all row types |
| `N12mDataRow.jsx` | **Remove** | Unified row component |
| `ForecastCard.jsx` | **Remove** | Sections are inline in one continuous table, not cards |
| `DashboardTab.jsx` | **OverviewTab** | Compact summary panels, no nav cards |
| `ForecastTab.jsx` | **ForecastTab** | One continuous grid table, sections as divider rows |
| `DataEntryTab.jsx` | **DataEntryTab** | Action bar in header area, stage context from global state |
| `DataEntryGrid.jsx` | **DataGrid** | Shared grid component used by both Forecast and Data Entry |
| `StageComparisonTab.jsx` | **StagesTab** | Cleaner table, clickable stage headers to expand |
| `PnLTab.jsx` | **PnlTab** | Minimal changes — already table-based |
| — | **StagePills** (new) | Global S1-S5 selector in header |
| — | **ImportPicker** (new) | Collapsible import version selector |

### What Stays the Same

- `useApi.js` — API layer unchanged
- `formatCurrency.js` — formatting unchanged
- `formatDelta.js` — formatting unchanged
- `calcEvaluator.js` — calc preview unchanged
- All backend APIs — zero backend changes

---

## 6. Interaction & Motion

### Principles

- **No bounce, no spring, no playful easing.** This is financial software. Transitions should be crisp and fast.
- **Opacity + translate only.** Avoid scale, rotate, or filter animations on data.
- **200ms default duration.** 300ms max for larger layout shifts.

### Specific Animations

| Interaction | Animation |
|---|---|
| Tab switch | Content fades in (opacity 0→1, translateY 8px→0, 200ms ease-out) |
| Section expand/collapse | Height auto with 250ms ease-out, content fades in |
| Cell focus | Border color transition 150ms |
| Dirty cell appearance | Left border slides in from 0 to 3px width, 200ms |
| Save success | Brief green flash on action bar (200ms), count resets |
| KPI strip load | Staggered fade-in, 100ms delay between each metric |
| Row hover | Background tint appears, 100ms |

### Scroll Behavior

- Data grids: horizontal scroll with **fade gradient** on right edge when content overflows
- Sticky first column (row labels) on horizontal scroll
- Sticky header row on vertical scroll within the grid

---

## 7. Texture & Atmosphere

### Paper Grain

Apply a subtle noise texture overlay on `--bg-surface` panels:

```css
.surface {
  background-image: url("data:image/svg+xml,..."); /* tiny noise pattern */
  background-size: 200px 200px;
  /* OR use a CSS filter approach: */
  position: relative;
}
.surface::before {
  content: '';
  position: absolute;
  inset: 0;
  background: url('/noise.svg');
  opacity: 0.03;
  pointer-events: none;
}
```

Very subtle — just enough to break the flat matte look and give surfaces a sense of material.

### Borders

- Panels use **1px solid --border-subtle** — no border-radius bigger than 6px. Financial tools look serious with sharp or slightly rounded corners, not pill shapes.
- Table rules: **1px solid --border-subtle** for rows, **1px solid --border-medium** for section dividers
- Active/focused elements: **2px solid --accent** border

### Shadows

Minimal. One shadow level for elevated elements (modals, dropdowns):

```css
--shadow-elevated: 0 8px 32px rgba(0, 0, 0, 0.4);
```

No card shadows. Panels are defined by borders and background color, not elevation.

---

## 8. Responsive Strategy

| Breakpoint | Behavior |
|---|---|
| > 1400px | Full layout, all columns visible |
| 1024-1400px | Compact column widths, abbreviate month headers (Sep→S) |
| 768-1024px | Stage pills collapse to dropdown, grid scrolls horizontally |
| < 768px | Not a primary target. Stack KPI strip vertically, grid full-width scroll |

The app is primarily used on desktop/laptop. Tablet is a secondary concern. Mobile is not a target but should remain usable.

---

## 9. Implementation Approach

### Phase A: Foundation (CSS + Layout)

1. Replace color palette (CSS variables)
2. Swap fonts (Fraunces, Geist, IBM Plex Mono)
3. Restructure header (2-line compact, global stage pills)
4. Add noise texture / atmosphere

### Phase B: Overview Tab

5. Redesign Dashboard → Overview with compact KPI strip and summary panels

### Phase C: Forecast Tab

6. Rebuild as one continuous grid table (remove cards/collapsible sections)
7. Inline section dividers
8. Actual/forecast month visual distinction (column background tints)

### Phase D: Data Entry Tab

9. Move action bar to header area
10. Align grid styling with Forecast tab (shared DataGrid component)
11. Update dirty/calculated cell styling to new amber palette

### Phase E: Stages + P&L

12. Clean up Stage Comparison table styling
13. Clean up P&L table styling

### Phase F: Polish

14. Animations and transitions
15. Scroll fade indicators
16. Sticky columns/headers
17. Responsive breakpoints

---

## 10. What This Redesign Does NOT Do

- No routing (still tab-based state — URL routing is a separate concern)
- No new features (no undo/redo, no multi-cell select, no auto-save)
- No backend changes (all API contracts stay the same)
- No new data fetching patterns (keep useApi hook as-is)
- No state management overhaul (keep useState/useMemo approach)

This is a **visual and layout** redesign only. The bones stay the same, the skin changes.

---

## 11. Success Criteria

1. A finance professional looks at this and feels it's **more trustworthy** than the current version
2. Number scanning is **faster** — monospace alignment, right-justified values, clear hierarchy
3. Data entry is **visually promoted** as the primary workflow
4. Screen real estate is used **more efficiently** — more data visible without scrolling
5. The aesthetic is **distinctive** — not another generic dark dashboard
6. All existing functionality works identically — zero regressions
