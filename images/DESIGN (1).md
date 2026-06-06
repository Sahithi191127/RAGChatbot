---
name: Executive FinTech Dark System
colors:
  surface: '#0d141d'
  surface-dim: '#0d141d'
  surface-bright: '#333a44'
  surface-container-lowest: '#080f17'
  surface-container-low: '#151c25'
  surface-container: '#192029'
  surface-container-high: '#232a34'
  surface-container-highest: '#2e353f'
  on-surface: '#dce3f0'
  on-surface-variant: '#bbcac1'
  inverse-surface: '#dce3f0'
  inverse-on-surface: '#2a313b'
  outline: '#86948c'
  outline-variant: '#3c4a43'
  surface-tint: '#50ddad'
  primary: '#50ddad'
  on-primary: '#003828'
  primary-container: '#00b386'
  on-primary-container: '#003d2c'
  inverse-primary: '#006c4f'
  secondary: '#ffb95f'
  on-secondary: '#472a00'
  secondary-container: '#ee9800'
  on-secondary-container: '#5b3800'
  tertiary: '#ffb4ab'
  on-tertiary: '#630f0d'
  tertiary-container: '#f27a6e'
  on-tertiary-container: '#691411'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#71fac8'
  primary-fixed-dim: '#50ddad'
  on-primary-fixed: '#002116'
  on-primary-fixed-variant: '#00513b'
  secondary-fixed: '#ffddb8'
  secondary-fixed-dim: '#ffb95f'
  on-secondary-fixed: '#2a1700'
  on-secondary-fixed-variant: '#653e00'
  tertiary-fixed: '#ffdad6'
  tertiary-fixed-dim: '#ffb4ab'
  on-tertiary-fixed: '#410002'
  on-tertiary-fixed-variant: '#822620'
  background: '#0d141d'
  on-background: '#dce3f0'
  surface-variant: '#2e353f'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  title-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.01em
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 48px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style

The brand personality is authoritative yet approachable, designed to function as a sophisticated AI-driven financial advisor. It prioritizes clarity, data density, and professional compliance over flashy trends. The target audience includes high-net-worth investors and fund managers who require precision and a calm, focused environment for decision-making.

The design style is **Modern Glassmorphism**. This is achieved through layered, semi-transparent surfaces that create a sense of depth without overwhelming the user. We avoid "neon" or "crypto" aesthetics by using high-quality blurs, muted gradients, and a strict adherence to a professional, dark-mode-first architecture inspired by top-tier SaaS dashboards like Vercel and Stripe.

## Colors

The palette is anchored in deep, sophisticated tones to ensure visual comfort during long sessions.

- **Primary Emerald (#00B386):** Used for growth indicators, primary CTAs, and successful states. It communicates stability and financial health.
- **Secondary Amber (#F59E0B):** Reserved for cautionary data, pending states, or regulatory warnings. It is never used as an "error" (red), but as a sophisticated signal for "attention required."
- **Greyscale:** The background hierarchy moves from Deep Charcoal (#0B0F14) for the canvas to Dark Navy (#111827) for navigation, and Card BG (#1F2937) for floating elements.
- **Text:** Primary text (#F9FAFB) provides high contrast, while Secondary text (#9CA3AF) manages information hierarchy for metadata and labels.

## Typography

This design system uses **Inter** for its neutral, highly legible, and systematic qualities. It bridges the gap between a modern startup aesthetic and a reliable institutional tool.

- **Headlines:** Use tighter letter spacing (-0.01em to -0.02em) to maintain a premium, "Swiss" feel.
- **Data Points:** For numeric values in tables or fund performance charts, ensure tabular lining is enabled to keep columns aligned.
- **Monospace:** Use **JetBrains Mono** sparingly for transaction IDs, legal identifiers, or technical metadata to reinforce the "AI/Systems" narrative.

## Layout & Spacing

The layout utilizes a **12-column fluid grid** for desktop and a **4-column grid** for mobile. 

- **Density:** High data density is encouraged but balanced with generous outer margins (48px) to provide "breathing room" for premium feel.
- **Rhythm:** An 8px linear scale is used for all internal component spacing (padding, gaps).
- **Alignment:** Content should be strictly left-aligned to mimic professional financial reporting, with numeric data right-aligned in tables for readability.

## Elevation & Depth

Depth is established through **Glassmorphism and Tonal Layering** rather than traditional heavy shadows.

1.  **The Canvas (Level 0):** #0B0F14. The furthest back layer.
2.  **Navigation/Sidebar (Level 1):** #111827 with no blur, providing a solid foundation.
3.  **Floating Cards (Level 2):** #1F2937 with an 80% opacity. Apply a `backdrop-filter: blur(16px)` to these elements.
4.  **Borders:** Use a subtle, light-reflective border (`rgba(255, 255, 255, 0.08)`) to define edges against dark backgrounds.
5.  **Overlays:** Modals and dropdowns should use a higher blur (24px) and a slightly thicker border (`rgba(255, 255, 255, 0.12)`) to indicate the highest level of the Z-index.

## Shapes

The design system uses a **Rounded** shape language to soften the "technical" nature of the data.

- **Standard Cards/Containers:** 16px (rounded-lg) to 20px (rounded-xl) for larger dashboard sections.
- **Buttons/Inputs:** 8px (rounded-md) to maintain a sense of precision.
- **Chips/Badges:** Fully pill-shaped (999px) to distinguish them from interactive buttons.

## Components

- **Buttons:**
    - **Primary:** Solid Emerald Green (#00B386) with white or near-white text. Use a subtle inner glow (top-down) for a tactile feel.
    - **Secondary/Ghost:** Transparent background with the 0.08 white border.
- **Input Fields:** Backgrounds should be slightly darker than the card they sit on. Use a 1px border that glows slightly (Emerald) only on focus.
- **Cards:** Floating appearance with `backdrop-filter: blur(16px)`. Title areas should have a subtle 1px bottom divider.
- **Data Chips:** Small, pill-shaped markers for "Compliant," "High Growth," or "Low Risk." Use low-opacity fills of the status color (e.g., 10% Emerald fill with 100% Emerald text).
- **Charts:** Use thin lines (1.5px to 2px) for trend lines. Area charts should use a vertical gradient from Emerald (20% opacity) to transparent.
- **AI Assistant Interface:** Use a specific "Blur-glass" container with a slightly higher border-opacity to differentiate AI-generated insights from static fund data.