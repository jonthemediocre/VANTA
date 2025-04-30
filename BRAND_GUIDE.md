# VANTA - Brand Guide v1.0

## 1. Introduction

### 1.1 Mission & Vision
*(Briefly restate the core goal from `theplan.md` - e.g., To deploy VANTA, a recursive symbolic operating system designed for continuity, aesthetic mutation, and coherent mythic evolution.)*

### 1.2 Purpose of this Guide
This document outlines the visual and communication standards for the VANTA project to ensure consistency, coherence, and a strong brand identity across all interfaces and artifacts.

---

## 2. Logo

### 2.1 Primary Logo
*(Reference `logo.png`)*
![VANTA Logo](./logo.png)

### 2.2 Usage Guidelines
- **Clear Space:** Maintain minimum clear space around the logo (e.g., equivalent to the height of the 'V').
- **Minimum Size:** Define minimum size for legibility (e.g., 24px height).
- **Placement:** Preferred placement (e.g., top-left).

### 2.3 Misuse
- Do not stretch, distort, or alter the logo's colors.
- Do not place on overly busy backgrounds without proper contrast treatment.
- *(Add other specific misuse examples)*

---

## 3. Color Palette

### 3.1 Primary Colors
*(Define 1-2 primary colors representing the core brand)*
- **VANTA Black:** `#0A0A0A` (Example)
- **Symbolic Gold:** `#E0B050` (Example)

### 3.2 Secondary Colors
*(Define 2-3 secondary colors for accents, calls-to-action, or specific states)*
- **Ritual Red:** `#A02C2C` (Example)
- **Kernel Blue:** `#4A7D9F` (Example)

### 3.3 Neutral Colors
*(Define a range of grays/off-whites for backgrounds, text, borders)*
- **Neutral 1 (Dark BG):** `#1A1A1A` (Example)
- **Neutral 2 (Light BG):** `#F5F5F5` (Example)
- **Neutral 3 (Text):** `#DCDCDC` (Example)
- **Neutral 4 (Borders):** `#3C3C3C` (Example)

### 3.4 Color Usage
- **Theme:** Primarily dark theme, aligning with the reference `interface.png`.
- **Backgrounds:** Use `VANTA Black` or `Neutral 1 (Dark BG)` for main backgrounds and container elements.
- **Text:** Use `Neutral 3 (Text)` for standard body text on dark backgrounds.
- **Primary Actions & Highlights:** Use `Symbolic Gold` for primary buttons, active states, focus indicators, key icons, and important highlights to draw attention.
- **Secondary Actions:** Use `Neutral 3 (Text)` or `Neutral 4 (Borders)` for secondary buttons (e.g., outlines) or less prominent interactive elements.
- **Accent Colors:** Use `Ritual Red` or `Kernel Blue` sparingly for specific states (e.g., errors, notifications) if needed, ensuring sufficient contrast.

---

## 4. Typography

### 4.1 Primary Font Family
*(Define the main font for headings and prominent text - specify web-safe fallbacks)*
- **Font:** `Inter`, sans-serif (Example)
- **Weights:** Bold (700), Regular (400)

### 4.2 Secondary Font Family (Optional)
*(Define a font for body text or special cases, if different)*
- **Font:** `Source Code Pro`, monospace (Example - for code snippets or specific UI elements)
- **Weights:** Regular (400)

### 4.3 Font Hierarchy & Sizing
*(Define standard sizes and weights for different text elements)*
- **H1 (Page Title):** 32px, Bold
- **H2 (Section Title):** 24px, Bold
- **H3 (Subsection Title):** 18px, Bold
- **Body Text:** 16px, Regular
- **Code/Monospace:** 14px, Regular
- **Captions/Labels:** 12px, Regular

### 4.4 Line Spacing & Paragraphs
- **Line Height:** 1.5 (Example)
- **Paragraph Spacing:** 1em (Example)

---

## 5. Iconography

### 5.1 Style
*(Define the desired icon style - e.g., Line icons, Solid icons, Minimalist, Geometric)*
- **Style:** Minimalist, geometric line icons (Example)

### 5.2 Source
*(Specify preferred icon library or source - e.g., Feather Icons, Material Symbols, Custom)*
- **Source:** Feather Icons (Example)

### 5.3 Usage
- **Size:** Standard sizes (e.g., 16px, 24px).
- **Color:** Use `Symbolic Gold` for key interactive icons. Use `Neutral 3 (Text)` for standard informational icons on dark backgrounds. Ensure contrast.
- **Consistency:** Maintain consistent style across the interface.

---

## 6. Imagery & Visual Style

### 6.1 Illustrations & Graphics
*(Define the style for any custom illustrations - e.g., Abstract, Geometric, Symbolic, Dark/Mysterious)*
- **Style:** Abstract, symbolic vector graphics with limited color palette. (Example)

### 6.2 Photography (If applicable)
*(Guidelines for photo usage - e.g., Authentic, moody, abstract)*

### 6.3 UI Mockups & Visuals
*(Reference `interface.png` if it sets a precedent)*
- **Style:** Clean, minimalist, dark-themed UI with clear hierarchy. (Example based on common modern styles)
- **Consistency:** Follow grid layouts, spacing rules, and component styles defined below.
- **Square Default:** For social media or non-UI contexts, default to square aspect ratios unless specified otherwise (as per `GLOBAL.md`).

---

## 7. Tone of Voice

### 7.1 Core Attributes
*(List 3-5 keywords describing the desired communication style)*
- Symbolic
- Authoritative
- Evolving
- Precise
- (Slightly) Mysterious

### 7.2 Guidelines
- Use clear and concise language.
- Avoid jargon where possible, unless defining specific VANTA terms.
- Maintain a consistent tone across all UI text, documentation, and communications.

---

## 8. UI Component Guidelines (Foundation)

### 8.1 Layout & Spacing
- **Grid System:** 8px grid (Example).
- **Spacing Scale:** 4px increments (4, 8, 12, 16, 24, 32px...) (Example).
- **Reference Layout:** Follow the two-column (Sidebar + Main Content) structure shown in `interface.png`.

### 8.2 Buttons
- **Primary Button:** Solid fill with `Symbolic Gold` background, `VANTA Black` text. Hover/Active states should provide clear visual feedback (e.g., slightly darken/lighten gold).
- **Secondary Button:** Outline style with `Neutral 4 (Borders)` border, `Neutral 3 (Text)` text. Hover/Active state could use a subtle `Neutral 1` background fill.
- **Icon Buttons:** Use icons (colored per Section 5.3) with appropriate padding and clear focus states (e.g., `Symbolic Gold` ring).

### 8.3 Forms & Inputs
- **Input Fields:** Dark background (e.g., `Neutral 1` slightly lighter than main BG), `Neutral 4` border, `Neutral 3` text. Focus state should use `Symbolic Gold` outline or border.
- **Labels:** `Neutral 3 (Text)`, placed above the input field.
- **Validation States:** Use `Ritual Red` for error borders/text.

### 8.4 Cards & Containers
- **Background:** `Neutral 1 (Dark BG)` or slightly lighter/darker variant.
- **Border Radius:** Consistent radius (e.g., 4px or 8px).
- **Padding:** Use spacing scale (e.g., 16px).

### 8.5 Navigation
- **Sidebar:** `VANTA Black` or darkest neutral background.
- **Active Item:** Highlight active navigation items (Sidebar, Tabs) using `Symbolic Gold` (e.g., background highlight, text color, or border indicator).
- **Inactive Item:** `Neutral 3 (Text)`.

---

## 9. Accessibility (WCAG 2.1 AA Minimum)

### 9.1 Color Contrast
- Ensure text and interactive elements meet minimum contrast ratios (4.5:1 for normal text, 3:1 for large text/graphics). Use contrast checker tools.

### 9.2 Keyboard Navigation
- All interactive elements must be navigable and operable using a keyboard.
- Focus indicators must be clear and visible.

### 9.3 Semantic HTML
- Use appropriate HTML5 elements for structure and meaning (e.g., `<nav>`, `<main>`, `<button>`).

### 9.4 Alt Text
- Provide descriptive alt text for all meaningful images. Decorative images should have empty alt attributes (`alt=""`).

---

## 10. Evolution
This guide is a living document and will evolve alongside the VANTA project. Updates should be proposed, reviewed (potentially via CoE), and versioned. 