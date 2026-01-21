# Mae Pla Pakka Kiew (MPPK) Strategy

## Description
A Price Action strategy focusing on specific reversal patterns (Pinbars, Engulfing, Stars) occurring at key structure levels (Support/Resistance) or Psychological Levels ("Krob").

## Logic
1.  **Patterns**:
    *   **PAT1**: Pinbar (Wick >= 2x Body).
    *   **PAT2**: Engulfing / Harami.
    *   **PAT3**: Morning / Evening Star.
2.  **Context**:
    *   **Krob**: Price touches integer levels ending in 0 or 5.
    *   **Structure**: Buy at Support, Sell at Resistance.
    *   **Filtering**: Ignore signals "Headbutting" the wrong level (e.g., Buying directly into Resistance).

## Parameters
*   `tp_points`: Target profit in points (Default: 1000).
*   `stop_loss_buffer`: Buffer for SL calculation.

## AI Metadata
*   `pattern`: The pattern detected (PAT1/2/3).
*   `context`: Support or Resistance.
*   `krob_check`: Whether a Krob level was touched.
