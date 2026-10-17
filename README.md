# JimAI

JimAI is a beginner-friendly AI project where the assistant has a simple memory system and a chat loop.

## What it does

- Stores memories in a JSON file
- Remembers recent facts and previous conversations
- Uses those memories when replying
- Supports a simple offline mode
- Can optionally use OpenAI if you provide an API key

## Project structure

- `memory.py` — memory storage logic
- `main.py` — interactive chat loop
- `requirements.txt` — Python dependencies
- `.gitignore` — common Python ignores

## Setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

   On Windows PowerShell:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the app:

   ```bash
   python main.py
   ```

## Optional: OpenAI support

Create a `.env` file or set an environment variable:

```bash
export OPENAI_API_KEY="your_key_here"
```

Then start the app. If the key is missing, JimAI will automatically fall back to a basic local reply mode.

## Beginner note

This is deliberately simple and easy to extend. A later version could use:

- vector embeddings for smarter memory search
- a real LLM backend
- a web interface
- long-term memory persistence in a database

