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
    "I may not have a rocket, but I do have excellent delivery.",
    "My cosmic timing is impeccable, unlike my ability to find the right sock.",
    "I was born in the stars, but I still can't fold a fitted sheet.",
    "I have a stellar sense of humor... and a suspiciously low tolerance for gravity jokes.",
    "Warning: excessive awe may cause spontaneous stargazing.",
    "Somewhere between orbit and overthinking, I learned to be funny."
]

# Commands the user can type to manage memories
CLEAR_COMMANDS = {"clear memories", "clear memory", "forget all", "forget memories"}
FORGET_LAST_COMMANDS = {"forget last", "undo memory", "forget last memory"}


def simple_reply(user_input: str, memories: list) -> str:
    """A fallback local reply system for beginners.

    This returns concise answers only (no memory lists) so the assistant feels cleaner.
    """
    cleaned = user_input.strip()

    if not cleaned:
        return "I didn't catch that. Try asking me something else."

    # If the user asked a question and we have a memory, give a concise reply
    if cleaned.endswith("?") and memories:
        first = memories[0]
        mem_text = first.get("text", "")
        # If the memory is a user-statement like 'I love Jupiter', convert to 'You love Jupiter'
        mem_text_lower = mem_text.lower()
        if mem_text_lower.startswith("i "):
            reply = "You " + mem_text[2:]
        elif mem_text_lower.startswith("my "):
            reply = "Your " + mem_text[3:]
        else:
            reply = mem_text
        return reply + "\n\n" + random.choice(HUMOR_LINES)

    # Non-question with memories: short acknowledgement
    if memories:
        return "Got it — I remembered that. " + random.choice(HUMOR_LINES)

    if "hello" in cleaned.lower() or "hi" in cleaned.lower():
        return "Hi! I’m JimAI, your space-savvy assistant with a sense of humor. Ask me about planets, stars, or tell me something to remember."

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
        norm = user_input.strip().lower()

        if norm in {"exit", "quit", "bye"}:
            print("JimAI: Goodbye! I’ll remember what we discussed.")
            break

        # Memory management commands
        if norm in CLEAR_COMMANDS:
            memory.clear()
            print("JimAI: Okay — I forgot everything. My memory's a blank slate now.")
            continue

        if norm in FORGET_LAST_COMMANDS:
            memory.remove_last(1)
            print("JimAI: I forgot the last thing you told me.")
            continue

        # Identity-priority: answer who/what you are before checking KB or memories
        if any(p in norm for p in ("who are you", "what are you", "your name", "who am i talking to")):
            humor = random.choice(HUMOR_LINES)
            memory.add(f"Told user who I am at {datetime.now().isoformat(timespec='seconds')}")
            print(f"JimAI: I’m JimAI — your space AI with a sense of humor. {humor}")
            continue

        # Determine if this is a question first
        is_question = user_input.strip().endswith("?")

        # Prefer built-in knowledge for space questions
        kb_matches = kb.find_relevant(user_input, limit=3) if is_question else []
        if kb_matches:
            fact = kb_matches[0].get("text")
            humor = random.choice(HUMOR_LINES)
            memory.add(f"Told user a fact: {fact} at {datetime.now().isoformat(timespec='seconds')}")
            print(f"JimAI: {fact} \n\n{humor}")
            continue

        # Only save the user's message as a memory if it's NOT a question
        if not is_question:
            memory.add(f"User said: {user_input} at {datetime.now().isoformat(timespec='seconds')}")

        # If no KB match, try user memories for questions (exclude the current input to avoid matches)
        relevant_memories = memory.find_relevant(user_input, limit=5, exclude_text=user_input) if is_question else []

        # Use relevant memories first (if any), otherwise use the most recent ones
        if relevant_memories:
            # create concise reply from the top memory
            top = relevant_memories[0]
            cleaned = memory._clean_memory_text(top.get("text", ""))
            # convert simple first-person statements to second-person for replies
            cleaned_lower = cleaned.lower()
            if cleaned_lower.startswith("i "):
                reply = "You " + cleaned[2:]
            elif cleaned_lower.startswith("my "):
                reply = "Your " + cleaned[3:]
            else:
                reply = cleaned
            humor = random.choice(HUMOR_LINES)
            memory.add(f"Told user from memory: {cleaned} at {datetime.now().isoformat(timespec='seconds')}")
            print(f"JimAI: {reply} \n\n{humor}")
            continue

        # No direct KB or memory hit — use recent context for a reply
        context_memories = memory.get_recent(limit=5)
        # Use cleaned context (no wrappers) when calling the LLM / simple reply
        cleaned_context = [
            {"text": memory._clean_memory_text(m.get("text", "")), "created_at": m.get("created_at")} for m in context_memories
        ]

        response = llm_reply(user_input, cleaned_context)
        print(f"JimAI: {response}")


if __name__ == "__main__":
    main()
