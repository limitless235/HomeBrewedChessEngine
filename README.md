# HomeBrewed Chess Engine (and Coach) 

A complete, end-to-end framework integrating a hyper-optimized **C++ Chess Engine**, a scalable **Python FastAPI Backend**, an elegant dependency-free **Vanilla JS/CSS Interace**, and a locally hosted **AI Chess Coach** leveraging Large Language Models (LLMs) to provide real-time game analysis.

---

##  Features

###  C++ Calculating Core
Built natively from scratch to maximize bit-level performance and mathematical efficiency:
* **Bitboards & Zobrist Hashing**: Using 64-bit integer mappings and XOR hashing for instant piece positioning and board identity tracking.
* **Magic Bitboards**: Perfect hashing algorithm used to instantaneously generate sliding piece (Rook, Bishop, Queen) attacks, completely avoiding loop overheads.
* **Alpha-Beta Pruning & Negamax**: High-depth search algorithms utilizing Transposition Tables to securely lock in calculations and avoid redundant evaluation trees.
* **Custom Evaluation Function**: Handcrafted heuristics blending Piece-Square Tables (PSTs), King Safety, and Tapered Evaluation (adjusting piece values dynamically between opening, mid, and endgame scenarios).

###  Local AI Chess Coach
A completely strict, localized AI coach that reads the pure truth of the engine and converts it to actionable natural language without hallucination:
* **Restricted LM Generation**: The LLM runs via LM Studio, completely air-gapped from the internet. It is restricted by a highly optimized System Prompt to ONLY relay facts provided by the Python Backend, preventing it from inventing phantom pieces or non-existent checks.
* **Tactical Parsing**: The backend breaks down the engine's Best Move and CP (Centipawn) data to inform the coach exactly when you left a piece **hanging**, exposed your **king**, stepped into a **fork**, or threw away the game. 
* **Pattern Analysis**: The web GUI tracks your sequential behavioral patterns during the match and forwards it. If you blunder three times in a row, the coach will advise you to slow down!

###  3,500+ Deep Opening Book
* Hooked directly into the Lichess Openings Database.
* Dynamically parses raw PGN sequences natively to identify transposition strings using FEN (`python-chess`) mapping hashes.
* Offers one-click redirect integration out to the **Lichess Opening Explorer** or **Deep Analysis View** with pre-loaded position setups. 

### Native Vanilla JS/CSS Frontend
* Gorgeous, bloat-free dark mode dashboard built entirely in Vanilla JS and CSS Grid.
* Uses **Chessground.js** (the same blazingly fast package that Lichess uses) for the actual rendering and drag-n-drop board mechanics.
* Seamless live Copy & Paste PGN Generation. 
* Historic Move Viewing: Click on any previous move in the algebraic log to travel backward relative to that exact FEN board state! 

---

##  Usage Setup

### 1. Requirements
* `make` and a modern C++ compiler (`g++` / `clang`)
* Python 3.10+
* [LM Studio](https://lmstudio.ai/)

### 2. Prepare the Openings Database
To pull the necessary Master Opening tables, execute the download script:
```bash
./openings/download.sh
```

### 3. Build the C++ Engine
Navigate into the directory and hit:
```bash
make clean
make
```

### 4. Setup Python Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Launch LM Studio
* Boot up LM Studio.
* Download any preferred Instruct LLM (e.g. `Mistral-7B-Instruct`, `Llama-3-8B-Instruct`).
* Start the Local Server on port `1234` (default).

### 6. Run the Application
Finally, fire up the FastAPI backend! It orchestrates the engine, the HTML interface, and the AI coach synchronously:
```bash
uvicorn server:app --reload --port 8000
```
Open your browser to `http://localhost:8000` to start playing!

---

## Architecture

1. **`index.html`** → Connects to User. Holds Chessground UI, Move PGN Tracker, & Pattern History caching. Calls endpoints like `/move` and `/analyze_move`.
2. **`server.py`** → Central Intelligence Pipeline. Hosts FastAPI. Subprocesses and queries `./engine` binary. Communicates with Local LM Studio backend via HTTPX. Pre-calculates facts using `python-chess`. 
3. **`engine` (C++)** → Pure mathematical calculation engine running securely behind standard I/O pipes. Speaks strictly UCI coordinates. 

---

### License
MIT License
