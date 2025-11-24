# Trading Journal UI/UX Design: "The Psychological MRI"

## 1. Design Philosophy
**"Map Your Pattern, Don't Just Log It."**

The goal is to move away from spreadsheet-style data entry (which is boring and often skipped) to a **Guided Wizard** experience. This "Psychological MRI" approach breaks the complex task of mental analysis into small, digestible steps, ensuring high-quality data capture for the AI.

## 2. User Flow (The Wizard)

The journal entry process is divided into **4 Distinct Stages**.

### Stage 1: Technical Context & Risk Parameters (The "Setup")
*   **Goal:** Capture trade data with a focus on Risk & Money Management (Forex First).
*   **UI Elements:**
    *   **Market Data (Forex Priority):**
        *   **Pair:** Dropdown (Default: XAU/USD, EUR/USD, GBP/JPY).
        *   **Direction:** Toggle (LONG / SHORT).
        *   **Session:** Dropdown (Asian, London, NY).
    *   **Risk & Money Management:**
        *   **Entry/SL/TP:** Price inputs.
        *   **Risk Amount:** Input ($ or %). *Auto-calcs Lot Size based on SL.*
        *   **R-Multiple Target:** Auto-calc (Reward/Risk).
    *   **Execution Result:**
        *   **Exit Price:** Input.
        *   **Realized PnL:** Input ($).
        *   **Realized R:** Auto-calc.
    *   **Context Score:** Slider (1-10) "How well did you understand the market context?"

### Stage 2: The Game Level (The "Verdict")
*   **Goal:** Categorize the performance quality.
*   **UI Elements:**
    *   **Three Big Cards (Select One):**
        *   🟢 **A-Game (Learning Mistake):** "I did my best, but didn't know enough."
        *   🟡 **B-Game (Marginal Mistake):** "I got sloppy or slightly emotional."
        *   🔴 **C-Game (Obvious Mistake):** "I lost control / Tilted."

### Stage 3: Mental Pattern Mapping (The "MRI")
*   **Goal:** Visualize the emotional sequence.
*   **UI Elements:**
    *   **Timeline Builder:** A vertical timeline where users add "Events":
        *   [+] Add Trigger (e.g., "Missed a trade")
        *   [+] Add Thought (e.g., "I need to make it back")
        *   [+] Add Emotion (e.g., "Frustration")
        *   [+] Add Behavior (e.g., "Entered early")
    *   **Severity Sliders:**
        *   "Rate your Greed": 1 (None) - 10 (Uncontrolled)
        *   "Rate your Fear": 1 (Calm) - 10 (Panic)
        *   *Visual Feedback:* Sliders change color from Green to Red as they increase.

### Stage 4: Root Cause & Correction (The "Fix")
*   **Goal:** Structured self-coaching.
*   **UI Elements:**
    *   **5 Guided Text Areas (The Mental Hand History):**
        1.  **Problem:** "Describe the specific issue."
        2.  **Why:** "Why did this happen?"
        3.  **Flaw:** "What is the underlying belief?"
        4.  **Correction:** "What is the fix?"
        5.  **Logic:** "Why does this fix work?"
    *   *AI Assistant:* A "Ask Gemini" button next to each field to suggest answers based on previous entries.

## 3. Dashboard Integration
*   **"My Patterns" View:** A heatmap or list showing the most frequent triggers and flaws identified by the AI.
*   **"Performance vs. Emotion" Chart:** A scatter plot correlating "Severity Level" with "PnL" to find the user's tipping point.

## 4. Technical Requirements
*   **Frontend:** Next.js + Tailwind CSS (Glassmorphism).
*   **State:** React Context for the Wizard data.
*   **Storage:** PostgreSQL (JSONB for the flexible timeline data).
