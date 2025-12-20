# 07 - Guest Experience Components Specification

## 1. Overview
This document specifies the UI components used for the public-facing (guest) Landing Page of the **MTF Trading System**. These components are designed to convert visitors into users by showcasing the system's features, performance (via demo signals), and workflow.

**Parent Page:** `frontend/app/page.tsx` (Guest View)
**Directory:** `frontend/components/guest/`

## 2. Component Architecture

### 2.1 GuestHeader
**File:** `GuestHeader.tsx`
*   **Purpose:** Top navigation bar for unauthenticated users.
*   **Behavior:** Fixed to top, backdrop blur effect.
*   **Elements:**
    *   **Logo:** Links to `/`.
    *   **Nav Links:** Anchor links to `#features`, `#signals-preview`, `#how-it-works`.
    *   **CTA:** "Get Started" button linking to `/login`.

### 2.2 HeroSection
**File:** `HeroSection.tsx`
*   **Purpose:** Immediate value proposition and primary Call-to-Action.
*   **Design:**
    *   Animated background (gradient orbs, grid pattern).
    *   **Trust Badge:** Highlighting "AI-Powered" and Risk Management.
    *   **Headline:** "Intelligent XAU/USD Trading..." with gradient text.
    *   **Stats Grid:** Displays key performance metrics (Win Rate, R:R, etc.).
    *   **Actions:**
        *   "Start Trading" (Primary) -> `/login`
        *   "View Live Signals" (Secondary) -> `#signals-preview`

### 2.3 FeaturesGrid
**File:** `FeaturesGrid.tsx`
*   **Purpose:** Highlights the three pillars of the system: MTF Strategy, AI Analyst, and SMC.
*   **Design:**
    *   3-column grid of cards.
    *   **Hover Effects:** Scale up, border glow, internal gradient bloom.
    *   **Content:** Icon (Lucide), Title, Description.

### 2.4 HowItWorks
**File:** `HowItWorks.tsx`
*   **Purpose:** Explains the trading logic flow in 3 simple steps.
*   **Steps:**
    1.  **Analysis:** 4H/Daily trends + News.
    2.  **Setup:** Fib zones + Order blocks.
    3.  **Execute:** 15m triggers + Risk management.
*   **Design:** Process flow with connecting lines (desktop only) and step numbers.

### 2.5 LiveSignalPreview
**File:** `LiveSignalPreview.tsx`
*   **Purpose:** Social proof via "recent" (demo) signals.
*   **Data Source:** `frontend/lib/demo-data.ts`.
*   **Interactivity:**
    *   **Cards:** Display Symbol, Direction (Bullish/Bearish), Setup context, Confidence bar.
    *   **Hover State:** Blur overlay with "Sign up to unlock full details" prompt to drive conversion.

### 2.6 CTASection
**File:** `CTASection.tsx`
*   **Purpose:** Final push for conversion at the bottom of the page.
*   **Design:** High-contrast gradient card with floating background elements.
*   **Trust Indicators:** "No credit card required", "Free trial", etc.

### 2.7 GuestFooter
**File:** `GuestFooter.tsx`
*   **Purpose:** Standard footer navigation.
*   **Links:** Product, Resources, Socials, Legal (Privacy/Terms).

## 3. Design System Integration
All components must adhere to the global design tokens defined in `frontend/app/globals.css` and Tailwind config:
*   **Colors:** `accent-blue`, `accent-green`, `accent-red`, `gray-950` (background).
*   **Typography:** Inter (Body), JetBrains Mono (Code/Numbers).
*   **Animations:** `animate-fade-in`, `animate-slide-up`, `animate-pulse`.

## 4. Dependencies
*   **Icons:** `lucide-react`
*   **Routing:** `next/link`
*   **Data:** `frontend/lib/demo-data.ts` (Mock data for signals)
