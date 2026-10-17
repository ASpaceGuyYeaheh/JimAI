import os
import random
from datetime import datetime

from memory import Memory
from knowledge import KnowledgeBase

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import openai
except ImportError:
    openai = None

HUMOR_LINES = [
    "(space pun incoming... wait for it)",
    "I like my coffee like I like my space: dark and infinite.",
    "Beep boop — friendly space AI at your service.",
    "I promise my jokes have a gravitational pull: you can't resist groaning.",
]


def simple_reply(user_input: str, memories: list) -> str:
    """A fallback local reply system for beginners.

    If the user asks a question, and we have a relevant memory or fact,
    we show it. Otherwise, we fall back to friendly canned replies.
    """
    cleaned = user_input.strip()

    if not cleaned:
        return "I didn't catch that. Try asking me something else."

    if cleaned.endswith("?") and memories:
        lines = "\n".join(f"- {m.get('text', '')}" for m in memories[:5])
        humor = random.choice(HUMOR_LINES)
        return (
            f"I found these memories related to your question:\n{lines}\n\n"
            f"Short answer: (from my memory)\n{lines.splitlines()[0]}\n\n{humor}"
        )

    if memories:
        recent = "\n".join(f"- {m.get('text', '')}" for m in memories[:3])
        return (
            f"I remember: {recent}\n\n"
            f"You said: {cleaned}\n"
            f"I can keep that in mind and respond based on it. {random.choice(HUMOR_LINES)}"
        )

    if "hello" in cleaned.lower() or "hi" in cleaned.lower():
        return "Hi! I’m JimAI, your space-savvy assistant with a sense of humor. Ask me about planets, stars, or ask me anything else."

    if "your name" in cleaned.lower() or "who are you" in cleaned.lower():
        return "I’m JimAI, a space AI who remembers things and likes to crack (mild) space jokes."

    return (
        f"Thanks for saying: \"{cleaned}\". "
        "I’m still learning, but I can remember what you tell me and use it in future conversations."
    )


def llm_reply(user_input: str, memories: list) -> str:
    """Optional reply using OpenAI if the API key is available."""
    if openai is None or not os.getenv("OPENAI_API_KEY"):
        return simple_reply(user_input, memories)

    memory_context = "\n".join(f"- {m.get('text', '')}" for m in memories[:5])

    prompt = f"You are JimAI, a helpful space-savvy AI assistant. Keep replies short and friendly and add a little humor when appropriate.\n\nRelevant memories:\n{memory_context or 'No previous memories.'}\n\nUser: {user_input}\nAI:"

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are JimAI, a friendly space AI with memory."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        return f"I tried to use the AI model, but it failed. Falling back to local mode. Error: {exc}\n\n{simple_reply(user_input, memories)}"


def main() -> None:
    memory = Memory("memory.json")
    kb = KnowledgeBase("space_facts.json")

    print("JimAI: Hello! I can remember things and I know some space facts. Type 'exit' to stop.")

    while True:
        user_input = input("You: ")

        if user_input.strip().lower() in {"exit", "quit", "bye"}:
            print("JimAI: Goodbye! I’ll remember what we discussed.")
            break

        # Save a general memory for important things
        memory.add(f"User said: {user_input} at {datetime.now().isoformat(timespec='seconds')}")

        is_question = user_input.strip().endswith("?")

        # Prefer built-in knowledge for space questions
        kb_matches = kb.find_relevant(user_input, limit=3) if is_question else []
        if kb_matches:
            # Use the top fact and add a humorous line
            fact = kb_matches[0].get("text")
            humor = random.choice(HUMOR_LINES)
            # Also store that we told the user this fact
            memory.add(f"Told user a fact: {fact} at {datetime.now().isoformat(timespec='seconds')}")
            print(f"JimAI: {fact} \n\n{humor}")
            continue

        # If no KB match, try user memories for questions
        relevant_memories = memory.find_relevant(user_input, limit=5) if is_question else []

        # Use relevant memories first (if any), otherwise use the most recent ones
        if relevant_memories:
            context_memories = relevant_memories
        else:
            context_memories = memory.get_recent(limit=5)

        response = llm_reply(user_input, context_memories)
        print(f"JimAI: {response}")


if __name__ == "__main__":
    main()
