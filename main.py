import os
from datetime import datetime

from memory import Memory

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import openai
except ImportError:
    openai = None


def simple_reply(user_input: str, memories: list) -> str:
    """A fallback local reply system for beginners.

    This does not use an external LLM. It reads the most recent memories
    and gives a simple response based on the user's message.
    """
    cleaned = user_input.strip()

    if not cleaned:
        return "I didn't catch that. Try asking me something else."

    if memories:
        recent = "\n".join(f"- {m.get('text', '')}" for m in memories[:3])
        return (
            f"I remember: {recent}\n\n"
            f"You said: {cleaned}\n"
            f"I can keep that in mind and respond based on it."
        )

    if "hello" in cleaned.lower() or "hi" in cleaned.lower():
        return "Hi! I’m JimAI. I can remember things and talk with you. What would you like to do today?"

    if "your name" in cleaned.lower() or "who are you" in cleaned.lower():
        return "I’m JimAI, your beginner-friendly AI assistant. I like to remember things and chat with you."

    return (
        f"Thanks for saying: \"{cleaned}\". "
        "I’m still learning, but I can remember what you tell me and use it in future conversations."
    )


def llm_reply(user_input: str, memories: list) -> str:
    """Optional reply using OpenAI if the API key is available."""
    if openai is None or not os.getenv("OPENAI_API_KEY"):
        return simple_reply(user_input, memories)

    memory_context = "\n".join(f"- {m.get('text', '')}" for m in memories[:5])

    prompt = f"You are JimAI, a helpful AI assistant. Keep replies short and friendly.\n\nRelevant memories:\n{memory_context or 'No previous memories.'}\n\nUser: {user_input}\nAI:"

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are JimAI, a friendly AI assistant with memory."},
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
    print("JimAI: Hello! I can remember things. Type 'exit' to stop.")

    while True:
        user_input = input("You: ")

        if user_input.strip().lower() in {"exit", "quit", "bye"}:
            print("JimAI: Goodbye! I’ll remember what we discussed.")
            break

        # Save a general memory for important things
        memory.add(f"User said: {user_input} at {datetime.now().isoformat(timespec='seconds')}")

        recent_memories = memory.get_recent(limit=5)
        response = llm_reply(user_input, recent_memories)
        print(f"JimAI: {response}")


if __name__ == "__main__":
    main()
