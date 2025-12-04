This comprehensive design specification for the Trading Journal Module is developed following a **Specification-Driven Development (SDD)** approach, drawing heavily from the principles outlined in "The Mental Game of Trading" to ensure the data is structured and optimized for analysis by Google Gemini AI.

The primary goal of this module is to enable traders in Forex (XAU/USD) and Cryptocurrency markets to create a **"Map Your Pattern"** dataset, linking specific mental triggers to performance flaws, allowing the AI to identify the **"Root of Your Problem"** and assist in implementing corrections.

---

## **Trading Journal Module Specification (SDD)**

### **I. Core Trade Data (Technical Context)**

This section captures the essential quantitative and technical data for the trade, providing context for the AI analysis.

| Data Field | Description | Data Type / Required Input | Source Reference |
| :--- | :--- | :--- | :--- |
| **Trade Identifier** | Unique ID, Date, Time (Entry/Exit) | UUID, DateTime | |
| **Market/Pair** | e.g., XAU/USD, BTC/USD | String | (User Query) |
| **Trade Direction** | Long / Short | Enum | |
| **Planned Execution** | Entry Price, Stop Loss (SL), Take Profit (TP), Position Size | Numeric | |
| **Actual Execution** | Actual Entry/Exit Price, PnL ($ / R-factor) | Numeric | |
| **Trade Duration** | e.g., Intraday, Swing Trade (Trades can last from 1 day to 2 weeks) | Enum/Duration | |
| **Technical Context Score** | Self-rated understanding of the market context, correlation, or location at entry (1-10) | Numeric (1-10) | |

### **II. Mistake Categorization (Game Level Analysis)**

Traders must categorize the trade outcome or the error that occurred, which is crucial for the AI to understand the severity and cause of the problem.

| Game Level | Definition (Mandatory Selection) | Cause | Source Reference |
| :--- | :--- | :--- | :--- |
| **A-Game** | **Learning Mistakes** | Caused by unavoidable weakness in tactical decision-making (e.g., knowledge you haven't yet gained). | |
| **B-Game** | **Marginal Mistakes** | Caused by a blend of weakness in tactical decision-making and mental or emotional flaws. | |
| **C-Game** | **Obvious Mistakes** | Caused by mental or emotional flaws where emotions were too intense or energy was too low. These errors are so obvious there is nothing to learn tactically. | |

### **III. Mental Pattern Mapping (AI Feature Core)**

This section captures the structured mental hand history data, enabling the AI to "Map Your Pattern" by tracking the buildup of emotion. This is the critical dataset for the Gemini AI to analyze.

#### **A. Incident Sequence Data**

The trader must write down what occurred before, during, and after the trading mistake.

| Data Field | Description | Example Clues to Capture | Source Reference |
| :--- | :--- | :--- | :--- |
| **Triggers** | What happened immediately before the error? | Series of losing trades, closing a big winner, or seeing others make money in a missed trade. | |
| **Thoughts** | Specific internal monologue or self-talk. | "Don't miss another one!", Self-doubt, "I’m not letting the market stop me", Thinking about the utility of money. | |
| **Emotions** | What was felt (e.g., frustration, euphoria, revenge). | Antsiness, nervous sensation in the stomach, Heat in the head (for tilt), Wanting revenge. | |
| **Behaviors/Actions**| Observable actions taken (e.g., changing charts, checking PnL). | Hyper-focused on one position, constantly looking at PnL, Gripping the mouse tighter, Checking PnL every 10 minutes. | |
| **Decision Changes** | How the decision-making process changed. | Focused on getting revenge, Disregarding probabilistic thoughts, Giving up the trading plan. | |
| **Perception Changes** | How the view of the market shifted. | Reading too much into price action, Perception is more about money, Clouded judgment. | |

#### **B. Severity Level Mapping (1-10 Scales)**

For the primary mental flaws, the trader must assign a severity level (1-10) to the mental state during the trade or mistake. AI can use these levels to track the correlation between emotional intensity and execution quality (Yerkes-Dodson law threshold).

| Mental Flaw Category | Severity Scale | Scale Context / Goal State | Technical Impact Example (from the sources) | Source Reference |
| :--- | :--- | :--- | :--- | :--- |
| **Greed** | 1 (Manageable) to 10 (Uncontrolled) | Fueled by urgency to prove oneself or unreasonable expectations. | Level 10: Giving up all control, manually managing the trade by looking at every single minute. | |
| **Fear** | 1 (Worry/Doubt) to 10 (Monster/Disruptive) | Often relates to fear of losing or missing out (FOMO). | Level 7: Urge to move stop to breakeven. Level 8: Wanting to secure profits quickly to prove ability. | |
| **Tilt (Anger/Frustration)** | 1 (Small) to 10 (Explosion/Margin Call) | Related to injustice, hating to lose, or mistake tilt. | Level 6: Increasing position size, blindly entering trades with a lot of risk. Level 10: Gambling and just clicking buttons. | |
| **Confidence** | 1 (Give up) to 5 (Ideal) to 10 (Invincible) | 5 is the stable ideal (Confident and calm). Cycles between overconfidence (6-10) and lack of confidence (1-4). | Level 8: Take bigger position sizes, adhering less to stops. Level 2: Looking for perfect trades, overly worried about reversal. | |
| **Discipline** | 1 (Worst) to 10 (Optimal) | Issues include impatience, boredom, or being overly results-oriented. | Level 8: Trouble letting go of losing positions. Level 2: Overtrading, moving stops randomly. | |

### **IV. Mental Hand History (Root Cause Analysis & Correction)**

This section ensures the AI receives not just the data, but the trader's attempt at structured diagnosis and correction, helping the AI provide targeted coaching.

The module must structure the post-trade analysis into five distinct fields:

1.  **What’s the problem:** A clear description of the specific issue (e.g., "I have a need for a trade to be green right from the beginning").
2.  **Why does the problem exist:** The immediate behavioral reason (e.g., "Every loss feels like a step backward, delaying my goals").
3.  **What is flawed:** Identification of the underlying cognitive flaw (e.g., Unreasonable expectation, Black-and-white thinking, or the inability to control the outcome of every trade).
4.  **What’s the correction (Real-time Strategy):** The specific action plan for the future (e.g., Stay focused on quality execution, or building a productive routine).
5.  **What logic confirms that correction:** The long-term logical grounding for the correction (e.g., "Quality execution in the short term is how I get what I want in the long run", or "Losses and drawdowns are part of the game").

### **V. AI Analysis Integration (Google Gemini)**

The structured data output from this module provides Gemini AI with inputs necessary for high-level mental performance analysis:

1.  **Pattern Recognition:** By mapping the Trigger -> Thought -> Emotion -> Behavior sequence, the AI can automatically identify and visualize the specific patterns unique to the user, similar to how Max identified 10 levels of greed, with the first signal being looking at PnL.
2.  **Threshold Identification:** The 1-10 severity scales allow the AI to pinpoint the exact emotional intensity (the "threshold" defined by the Yerkes-Dodson law) at which the trader loses access to their technical knowledge and skills.
3.  **Correction Logic Reinforcement:** The AI can use the trader's stated logic for correction to reinforce process-oriented thinking (e.g., Joe’s shift to a process-focused strategy using 100 boxes to track execution quality rather than PnL). This moves the focus away from being overly results-oriented.

---
**Analogy for Data Structure:**

The structured journal module acts like a **psychological MRI machine**. Instead of simply diagnosing a problem (a failed trade), it captures the entire sequence: the initial nerve impulse (the *Trigger*), the internal tissue response (the *1-10 Emotional Severity*), and the subsequent structural damage (*The Mistake*). This depth of data enables the Gemini AI not just to see the symptoms, but to precisely locate the underlying flaw (the *Root Cause*) for effective long-term treatment.