# JimAI

JimAI is a beginner-friendly space AI project: a chat assistant that remembers things and knows a few space facts.

## What it does

- Stores memories in a JSON file
- Has a tiny local knowledge base of space facts (space_facts.json)
- When you ask questions (ending with `?`), Jim will first look in the space facts and then in past memories
- Replies use simple rules by default and can optionally call OpenAI if you provide an API key

## Project structure

- `memory.py` — memory storage logic
- `knowledge.py` — a tiny local knowledge base (space facts)
- `space_facts.json` — some starter space facts Jim can answer from
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

## Example

- You: Hi Jim
- JimAI: Hi! I’m JimAI, your space-savvy assistant with a sense of humor.
- You: I love Jupiter
- (Jim stores that as a memory)
- You: What do I love?
- JimAI: I found these memories related to your question: - User said: I love Jupiter ... \n\n Short answer: (from my memory) - User said: I love Jupiter ...

## Optional: OpenAI support

Create a `.env` file or set an environment variable:

```bash
export OPENAI_API_KEY="your_key_here"
```

Then start the app. If the key is missing, JimAI will automatically fall back to a basic local reply mode.
