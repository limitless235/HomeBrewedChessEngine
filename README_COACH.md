# Local AI Chess Coach Architecture

This document explains the architecture and customization of the local LLM-powered chess coach.

## Architecture Highlights
- **100% Local Inference**: The entire analysis runs on your machine via LM Studio. No API keys, zero cost, and total privacy.
- **Asynchronous Data Flow**: The frontend sends the move to both the chess engine (`/move`) and the AI coach (`/analyze_move`) simultaneously. The Engine responds in milliseconds, while the local LLM takes its time to stream the analysis without blocking your game.
- **Dynamic Content Formatting**: The LLM’s response is requested with highly specific structural tags (`VERDICT:`, `WHAT THIS MOVE DOES:`, etc.), which the frontend parser identifies and styles distinctly.
- **Automated Openings**: Moves are aggressively matched against a 60+ line opening dictionary mapped within `server.py` to deduce specific deviations (e.g. Sicilian Najdorf) instantly, avoiding hallucinations from the LLM.

## How to Swap Models
The LLM coaching uses LM Studio's generalized OpenAI-compatible interface. 
1. Open LM Studio.
2. Download any GGUF instruction-tuned model (e.g., Llama-3, Mistral, Phi-3).
3. Load it into the "Local Server" tab and run it.
4. Your chess app will automatically connect to whatever model is currently loaded in the memory slot!

*Note: The `LM_STUDIO_MODEL` variable in `server.py` is ignored by LM Studio in Local Server mode; the Active server context takes precedence.*

## How to Tune the Coaching Prompt
If you want the coach to be harsher, friendlier, or focus specifically on endgames, you can tweak the System Prompt.

1. Open `server.py`.
2. Locate the `COACH_SYSTEM_PROMPT` string variable near the LLM handler section.
3. Modify the instructions!
   * *Want it to sound like a Grandmaster?* Add: "Speak with the strict, authoritative, and blunt tone of an Eastern European Grandmaster."
   * *Want it to focus on kids?* Add: "Use very simple language suitable for an 8-year-old beginner."
   * *Want to change the structure?* Alter the explicit headings list (e.g., replace `PRINCIPLE TO REMEMBER:` with `HISTORICAL GAME REFERENCE:`). Ensure `index.html`'s frontend parser is updated to catch your new tags.
