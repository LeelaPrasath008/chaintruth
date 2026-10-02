# ChainTruth Design System

## Overview
Light enterprise analytics theme targeting Snowflake Native Apps / Power BI / Gartner quality.
Single source of truth across all 12 pages. No per-page CSS.

## Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `bg` | `#F4F6F9` | App background |
| `surface` | `#FFFFFF` | Cards, panels |
| `border` | `#DDE3EA` | Card borders, dividers |
| `text` | `#1B2733` | Primary text |
| `text_muted` | `#5B6B7B` | Labels, captions |
| `primary` | `#0B6BCB` | Interactive elements |
| `primary_hover` | `#095AAE` | Button hover |
| `accent` | `#29B5E8` | Logo accent, sidebar active bar |
| `sidebar_bg` | `#0F2A43` | Navy sidebar |
| `sidebar_text` | `#E6EDF5` | Sidebar text |
| `sidebar_muted` | `#A9B8C9` | Sidebar section labels |
| `sidebar_active_bg` | `#1B4468` | Active nav item |
| `success` | `#17794C` / tint `#E6F4EC` | Healthy status |
| `warning` | `#8A5A00` / tint `#FFF4DB` | Warning status |
| `danger` | `#B3202F` / tint `#FBE8EA` | Critical status |
| `series` | `#2F6FB5, #2A9D8F, #C77700, #7A5FB3, #D1495B, #6B7C93` | Chart series |
| `grid` | `#E6EBF1` | Chart gridlines |

## Typography
- Font stack: `"Segoe UI", -apple-system, "Helvetica Neue", Arial, sans-serif`
- Page title: 24px / 32px, weight 600
- Section header: 16px / 24px, weight 600
- Body: 14px / 20px
- Table text: 13px / 18px
- KPI label: 12px / 16px, weight 600, sentence case
- KPI value: 28px / 32px, weight 600, `font-variant-numeric: tabular-nums`

## Spacing
4 / 8 / 12 / 16 / 24 / 32 px scale.

## Components

### page_header(title, subtitle, freshness)
White strip, ~72px. Title left, freshness caption right. No gradient.

### kpi_card(label, value, status, caption, icon_name)
CSS grid layout: `repeat(auto-fit, minmax(180px, 1fr))`, gap 12px.
Card ~100px tall, left-aligned. Status chip with SVG icon + text.

### section(title)
16px weight-600 with 1px bottom border.

### insight(title, body, level)
White card with 3px left border colored by level (danger/warning/success).

### alert_card(title, body, kind)
Tinted background card with left border. Kinds: danger, warning, info.

### status_chip(text, kind)
Inline pill: SVG icon + text on tinted background. Never color alone.

### icon(name)
18px inline SVG, `stroke=currentColor`. Available: chart, dollar, alert, factory,
box, clock, shield, search, graph, book, sparkle, link, check, x, minus.

## Charts
Plotly with `apply_light(fig, height)`. White background, `#E6EBF1` gridlines,
muted axis text. No chart-internal titles — use `section()` headers instead.
Series colors from `SERIES` list. Max 6 series.

## Navigation
`st.navigation` with grouped sections:
- **Overview**: Dashboard (default), Executive Story, Executive Summary
- **Investigate**: Conflict Center, Supplier Risk, AI Insights, Ask ChainTruth
- **Govern**: Ontology Explorer, Data Lineage, Business Glossary
- **Monitor**: Alert Center, Supply Chain Network, What-If Analysis

Navy sidebar with brand block at top, `:material/` icons on each page.

## Accessibility
- All text >= 4.5:1 contrast ratio (WCAG AA)
- All graphics/UI >= 3.0:1 contrast ratio
- Visible `:focus-visible` outlines
- Body text >= 14px
- Status communicated by icon + text, never color alone
- `prefers-reduced-motion` respected

## File Structure
```
app/
  .streamlit/config.toml     # Theme + toolbar config
  streamlit_app.py            # st.navigation entry point only
  utils/
    __init__.py
    db.py                     # Snowflake connection (unchanged)
    theme.py                  # Tokens + single CSS block
    components.py             # Shared UI components
    charts.py                 # Plotly light theme helper
  pages/
    00_Executive_Story.py
    01_Executive_Summary.py
    02_Dashboard.py
    03_Definition_Conflict_Center.py
    04_Supplier_Risk_Analysis.py
    05_AI_Insights.py
    06_Ontology_Explorer.py
    07_Data_Lineage.py
    08_Business_Glossary.py
    09_Ask_ChainTruth.py
    10_Alert_Center.py
    11_Supply_Chain_Network.py
    12_What_If_Analysis.py
tests/
  test_contrast.py            # WCAG contrast verification
docs/
  DESIGN_SYSTEM.md            # This file
```
