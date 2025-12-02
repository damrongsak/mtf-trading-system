# MTF Trading System - Design System Documentation

## 🎨 Color Palette

### Background Colors (Dark Theme)
- **Primary Background**: `#0B0F19` (Very dark blue-gray)
- **Secondary Background**: `#111827` (Gray-900)
- **Tertiary Background**: `#1a202c` (Gray-850)
- **Card Background**: `#2d3748` (Gray-750)

### Foreground/Text Colors
- **Primary Text**: `#e2e8f0` (Light gray-blue)
- **Secondary Text**: `#9ca3af` (Gray-400)
- **Muted Text**: `#6b7280` (Gray-500)
- **Subtle Text**: `#4b5563` (Gray-600)

### Accent Colors
- **Blue (Primary Action)**: `#3b82f6` - Used for active states, primary CTAs
- **Green (Success/Bullish)**: `#10b981` - Trading signals, positive PnL
- **Red (Danger/Bearish)**: `#ef4444` - Alerts, negative signals

### Border Colors
- **Default Border**: `#1f2937` (Gray-800)
- **Accent Blue Border**: `#3b82f6` with 20-30% opacity
- **Accent Green Border**: `#10b981` with 20-30% opacity
- **Accent Red Border**: `#ef4444` with 20-30% opacity

---

## 🖋️ Typography

### Font Families
1. **Sans-Serif (Primary)**: [**Inter**](https://fonts.google.com/specimen/Inter)
   - Used for: UI text, headings, body content
   - Weights: 400 (Regular), 500 (Medium), 700 (Bold)

2. **Monospace (Secondary)**: [**JetBrains Mono**](https://fonts.google.com/specimen/JetBrains+Mono)
   - Used for: Numbers, timestamps, version labels, technical data
   - Weights: 400 (Regular), 700 (Bold)

### Font Sizes & Hierarchy
- **H1 (Page Title)**: `text-3xl` (30px) - Bold, tracking-tight
- **H2 (Section Header)**: `text-2xl` (24px) - Bold
- **H3 (Card Title)**: `text-xl` (20px) - Bold
- **Body Text**: `text-sm` (14px) - Regular
- **Small Text**: `text-xs` (12px) - Regular/Medium
- **Mono Data**: `text-sm` or `text-xs` with `font-mono`

---

## ✨ Design Principles

### 1. Glassmorphism & Depth
- **Backdrop Blur**: `backdrop-blur-sm` or `backdrop-blur-md`
- **Semi-transparent Backgrounds**: Use `/50` or `/80` opacity modifiers
- **Example**: `bg-gray-950/80 backdrop-blur-md`

### 2. Glow Effects
- **Bullish Glow**: `shadow-[0_0_20px_-5px_rgba(16,185,129,0.2)]`
- **Bearish Glow**: `shadow-[0_0_20px_-5px_rgba(239,68,68,0.2)]`
- **Blue Glow**: `shadow-[0_0_20px_-5px_rgba(59,130,246,0.2)]`

### 3. Gradients
- **Brand Gradient**: `bg-gradient-to-r from-accent-blue to-accent-green`
- **Applied to**: Logo text using `bg-clip-text text-transparent`

### 4. Hover States
- **Scale Transform**: `hover:scale-[1.02]`
- **Background Change**: `hover:bg-gray-800/50`
- **Smooth Transitions**: `transition-all duration-200` or `duration-300`

### 5. Borders & Dividers
- **Card Borders**: `border border-gray-800`
- **Accent Borders**: `border-accent-blue/20` (with opacity)
- **Dividers**: `border-t border-gray-800`

---

## 🧩 Component Patterns

### Cards (Glassmorphic Style)
```css
bg-gray-850/50 backdrop-blur-sm 
border border-gray-800 
rounded-xl p-5
transition-all duration-300 hover:scale-[1.02]
```

### Badges/Pills
```css
px-3 py-1 rounded-full 
text-xs font-bold tracking-wider
bg-accent-green/10 text-accent-green 
border border-accent-green/20
```

### Status Indicators
- **Online Indicator**: `w-2 h-2 rounded-full bg-accent-green animate-pulse`
- **Loading Spinner**: `animate-spin rounded-full h-12 w-12 border-b-2 border-accent-blue`

### Sidebar Navigation
- **Active State**: `bg-accent-blue/10 text-accent-blue border border-accent-blue/20`
- **Inactive State**: `text-gray-400 hover:bg-gray-800/50 hover:text-gray-200`

---

## 📐 Layout Structure

### Main Layout
- **Sidebar**: Fixed left, 256px width (`w-64`), full height
- **Header**: Sticky top, 64px height (`h-16`)
- **Main Content**: Flex-1, scrollable, 24px padding (`p-6`)

### Spacing Scale
- **Tight**: `gap-2` (8px)
- **Normal**: `gap-4` (16px)
- **Relaxed**: `gap-6` (24px)
- **Loose**: `gap-10` (40px)

### Container Max Width
- **Content Container**: `max-w-7xl mx-auto` (1280px centered)

---

## 🎭 Theme Summary

**Overall Aesthetic**: **Dark, Premium, Glassmorphic Trading Dashboard**

**Key Characteristics**:
- ✅ **Dark Mode First** - Deep blue-black backgrounds
- ✅ **Glassmorphism** - Frosted glass effects with backdrop blur
- ✅ **Subtle Glows** - Color-coded shadows for signal types
- ✅ **Monospace Data** - Financial data in JetBrains Mono
- ✅ **Smooth Animations** - Micro-interactions on hover/active states
- ✅ **Color-Coded Signals** - Green (bullish), Red (bearish), Blue (neutral/actions)
- ✅ **Gradient Branding** - Blue-to-green gradient for logo/brand elements

---

## 🎯 Usage Guidelines

1. **Always use the custom color tokens** defined in `globals.css` (`--color-accent-blue`, etc.)
2. **Prefer glassmorphism** over solid backgrounds for cards and overlays
3. **Use monospace fonts** for all numerical/technical data (prices, timestamps, metrics)
4. **Apply subtle glow effects** to important interactive elements
5. **Maintain consistent border radius** - `rounded-lg` (8px) or `rounded-xl` (12px)
6. **Use opacity modifiers** (`/10`, `/20`, `/50`) for layered depth

---

## 📚 Reference Implementation

### Key Files
- **Global Styles**: [`frontend/app/globals.css`](file:///home/dan/workspace/mtf-trading-system/frontend/app/globals.css)
- **Layout**: [`frontend/app/layout.tsx`](file:///home/dan/workspace/mtf-trading-system/frontend/app/layout.tsx)
- **Sidebar Component**: [`frontend/components/Sidebar.tsx`](file:///home/dan/workspace/mtf-trading-system/frontend/components/Sidebar.tsx)
- **Header Component**: [`frontend/components/Header.tsx`](file:///home/dan/workspace/mtf-trading-system/frontend/components/Header.tsx)
- **Signal Card Example**: [`frontend/components/SignalCard.tsx`](file:///home/dan/workspace/mtf-trading-system/frontend/components/SignalCard.tsx)

---

This design system is inspired by modern fintech/trading platforms with a focus on **readability in low-light environments**, **clear data hierarchy**, and **premium aesthetics**. The color scheme is optimized for extended screen time and quick visual scanning of trading signals.
