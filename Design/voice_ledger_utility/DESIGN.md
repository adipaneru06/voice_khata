---
name: Voice Ledger Utility
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#3a3939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#c4c7c8'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#8e9192'
  outline-variant: '#444748'
  surface-tint: '#c6c6c7'
  primary: '#ffffff'
  on-primary: '#2f3131'
  primary-container: '#e2e2e2'
  on-primary-container: '#636565'
  inverse-primary: '#5d5f5f'
  secondary: '#c7c6c6'
  on-secondary: '#303031'
  secondary-container: '#464747'
  on-secondary-container: '#b5b5b5'
  tertiary: '#ffffff'
  on-tertiary: '#303030'
  tertiary-container: '#e4e2e1'
  on-tertiary-container: '#656464'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e2e2e2'
  primary-fixed-dim: '#c6c6c7'
  on-primary-fixed: '#1a1c1c'
  on-primary-fixed-variant: '#454747'
  secondary-fixed: '#e3e2e2'
  secondary-fixed-dim: '#c7c6c6'
  on-secondary-fixed: '#1b1c1c'
  on-secondary-fixed-variant: '#464747'
  tertiary-fixed: '#e4e2e1'
  tertiary-fixed-dim: '#c8c6c5'
  on-tertiary-fixed: '#1b1c1c'
  on-tertiary-fixed-variant: '#474746'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '500'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '500'
    lineHeight: 24px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: '0'
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: '0'
  body-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0.01em
  label-lg:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: '0'
  label-md:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 10px
    fontWeight: '500'
    lineHeight: 12px
    letterSpacing: 0.04em
  currency-lg:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '500'
    lineHeight: 24px
    letterSpacing: -0.02em
  currency-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: '0'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 0.5rem
  gutter-desktop: 1rem
  margin: 0.75rem
  margin-desktop: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

This design system is engineered for Indian shopkeepers operating in dense, fast-moving retail environments who require absolute clarity, speed, and uncompromising accuracy. The interface treats ledger accounting with the precision and sobriety of high-end developer tooling and institutional banking software. 

The aesthetic is functional minimalism:
- Zero decorative gradients, drop shadows, or glassmorphic blur effects.
- High-contrast, strictly neutral monochromatic base punctuated solely by low-saturation, semantic status accents.
- Dense, left-aligned structural hierarchy optimized for rapid thumb operation and glanceable auditing under bright ambient store lighting.
- Quiet, mechanical reliability that treats voice inputs not as a conversational gimmick, but as an instant, hands-free keyboard accelerator.

## Colors

The palette is rooted entirely in deep neutrals to minimize visual fatigue, maintain legibility in dark or poorly lit environments, and enforce zero visual noise.

### Core Canvas & Surfaces
- **Canvas Base (`#0A0A0A`):** The primary view background.
- **Card / Surface Container (`#141414`):** Base ledger rows, input surfaces, and module containers.
- **Raised Elements / Popovers (`#1C1C1C`):** Dropdowns, active voice input panels, and elevated sheets.
- **Structural Outlines (`#2A2A2A`):** 1px structural dividing lines and input borders.

### Typography Hierarchy
- **Primary Text (`#EDEDED`):** Customer names, active currency values, titles, and voice transcripts.
- **Secondary Text (`#8A8A8A`):** Metadata, timestamps, phone numbers, and field labels.
- **Disabled / Structural Text (`#555555`):** Placeholders, historical dividers, and inactive icons.

### Semantic Status Indicators (Desaturated)
- **Debit / Owed (`#C97B7B`):** Negative ledger state ("You will give" / balance owed by customer).
- **Credit / Received (`#7BA68A`):** Settled ledger state ("You received" / payments cleared).
- **Recording Active (`#D9534F`):** Voice listening mode pulse and real-time buffer capture.

## Typography

The typography is built entirely on `Inter`, restricted strictly to weights `400` (Regular) and `500` (Medium).

- **Tabular Figures:** Always apply `font-variant-numeric: tabular-nums` (or OpenType feature `"tnum" 1`) across all currency values, dates, serial codes, and quantities to align vertical decimals across row-level transactions.
- **Left Alignment:** All data elements, transactional headers, customer records, and ledger rows align strictly left. Only currency figures align right inside data tables for fast column scanning.
- **Compact Vertical Ryhthm:** Tight line heights ensure dense scanning on small Android touchscreens without row overlaps.

## Layout & Spacing

A strict **4px vertical and horizontal grid rhythm** governs layout geometry.

### Grid & Form Factors
- **Mobile First (Default):** Fluid 4-column layout with 12px outer screen margins (`margin: 0.75rem`) and 8px gutters (`gutter: 0.5rem`). Information is stacked in compact, continuous ledger rows.
- **Tablet / Desktop:** 12-column layout max-width bounded at 960px to preserve data density; margins scale to 24px (`margin-desktop: 1.5rem`).

### Density & Metrics
- Component paddings exclusively use `space-xs` (4px), `space-sm` (8px), `space-md` (12px), and `space-lg` (16px).
- Row height for mobile ledger items is fixed at 44px or 52px to maximize items visible per screen while preserving touch target compliance.

## Elevation & Depth

Visual hierarchy uses **tonal layering and low-contrast borders**, omitting shadows entirely:

1. **Base Tier (`#0A0A0A`):** Canvas ground. Zero border.
2. **Container Tier (`#141414`):** Cards, primary lists, and ledger panels. Framed with a 1px solid border (`#2A2A2A`).
3. **Floating & Active Tier (`#1C1C1C`):** Persistent bottom sheets, voice intake states, popovers, and sticky totalizers. Framed with a 1px solid border (`#2A2A2A`).

No shadow spreads, blurs, or ambient lighting effects are permitted. Separation between components is strictly conveyed through surface tint change and the 1px line boundary.

## Shapes

The design system enforces a uniform **8px corner radius (`0.5rem`)** across all containers, inputs, buttons, and action sheets.

- **Cards, Modals, and Sheets:** 8px radius.
- **Buttons, Inputs, and Search Fields:** 8px radius.
- **Data Chips & Tags:** 8px radius.
- **Voice Pulse Orb:** Hard circular exception (50% / fully pill-rounded) restricted entirely to the active recording icon/button.

## Components

### Buttons
- **Primary:** Background `#EDEDED`, text `#0A0A0A`, font-weight 500. Height 36px (compact) or 44px (touch-primary). 8px radius. No border.
- **Secondary / Utility:** Background `#141414`, text `#EDEDED`, 1px solid `#2A2A2A`. Hover/Active: Background `#1C1C1C`.
- **Voice Action Button:** Height 48px. Resting: `#141414` with `#2A2A2A` border and `#EDEDED` mic icon. Active recording: `#1C1C1C` with `#D9534F` 1px border and `#D9534F` text/icon state. Zero box-shadows.

### Inputs & Search Bars
- Background `#141414`, 1px solid `#2A2A2A`, text `#EDEDED`, placeholder `#555555`. 8px radius.
- Active/Focused: Border changes to 1px solid `#8A8A8A`. No glow or outline spread.
- Height: 40px with 12px horizontal padding. Left-aligned text.

### Ledger Transaction Row
- Background `#141414`, separated by 1px solid `#2A2A2A` horizontal dividers or discrete cards.
- Left side: Contact name in `#EDEDED` (`headline-sm`), relative timestamp and note in `#8A8A8A` (`body-sm`).
- Right side: Transaction amount in tabular figures (`currency-md`). Color is strictly `#C97B7B` (owed/give) or `#7BA68A` (received/got).

### Voice Parsing Bar
- Fixed bottom utility bar. Background `#1C1C1C`, border-top 1px solid `#2A2A2A`.
- Active transcription line displays real-time parsed tokens in `#EDEDED` with tentative amount tags highlighted in `#7BA68A` or `#C97B7B`.

### Filter Chips
- Height 28px. 8px radius. Background `#141414`, border 1px solid `#2A2A2A`, text `#8A8A8A`.
- Selected: Background `#1C1C1C`, border 1px solid `#EDEDED`, text `#EDEDED`.

### Checkboxes & Radios
- Size 16x16px. Background `#141414`, border 1px solid `#2A2A2A`, radius 4px (checkbox) or 50% (radio).
- Checked: Background `#EDEDED`, inner mark `#0A0A0A`.

### Summary Metric Card
- Background `#141414`, border 1px solid `#2A2A2A`, padding 12px.
- Left-aligned label in `#8A8A8A` (`label-md`), big counter in `#EDEDED` (`currency-lg`) with colored status indicator dot (4px circle in `#C97B7B` or `#7BA68A`).