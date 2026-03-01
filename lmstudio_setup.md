# Local AI Chess Coach — LM Studio Setup

The AntiGravity Chess Coach runs 100% locally on your machine using LM Studio. This means zero API costs, total privacy, and offline capabilities.

Follow these 5 steps to get the Local AI Coach running alongside your Chess Engine.

## Step 1: Download and Install
1. Go to [https://lmstudio.ai](https://lmstudio.ai) and download the installer for your OS (Mac/Windows/Linux).
2. Install and open the LM Studio application.

## Step 2: Download a Model
Inside LM Studio, we need to download a "Weights" file (the actual AI "brain").

1. Click the **Search** tab (magnifying glass icon on the left sidebar).
2. Search for and download one of these recommended models:
   
   **PRIMARY (Best Chess Knowledge, needs 8GB+ RAM):**
   - `mistralai/Mistral-7B-Instruct-v0.3-GGUF` (Select the `Q4_K_M` quantization)
   
   **ALTERNATIVE (Faster, needs 4GB+ RAM):**
   - `microsoft/Phi-3-mini-4k-instruct-GGUF` (Select the `Q4_K_M` quantization)
   
   **ALTERNATIVE (Best Strategy Reasoning, needs 16GB+ RAM):**
   - `meta-llama/Meta-Llama-3-8B-Instruct-GGUF` (Select the `Q4_K_M` quantization)

3. Click the **Download** button next to your chosen model variant.

## Step 3: Start the Local Server
1. Click the **Local Server** tab (looks like `<->` icon on the left sidebar).
2. Use the top dropdown menu to **Select the model** you just downloaded.
3. Click the green **Start Server** button.
   * *The server will start running at `http://localhost:1234` by default.*
   * *LM Studio now exposes an OpenAI-compatible API at `http://localhost:1234/v1`.*

## Step 4: Verify Server is Running
Open your terminal and run this command:
```bash
curl http://localhost:1234/v1/models
```
*(It should return a JSON list displaying your loaded model name).*

## Step 5: Test a Completion
You can verify the AI is responding correctly by running this test command in your terminal:
```bash
curl http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local-model",
    "messages": [{"role":"user","content":"What is the Sicilian Defense?"}],
    "temperature": 0.3,
    "max_tokens": 200
  }'
```
*(Note: LM Studio ignores the "local-model" string and simply uses whatever model is actively loaded in the UI).*

---

### You're Done!
Leave the LM Studio server running in the background. Now, whenever you open `localhost:8000` to play chess, the backend will automatically connect to your local AI model and generate grandmaster-level coaching feedback after every move!
