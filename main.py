import os
import random
import re
from datetime import datetime
from typing import List, Dict

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

# Planets and opinion verbs for detecting planet mentions with opinions
PLANETS = [
    "mercury",
    "venus",
    "earth",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
]
OPINION_VERBS = ["love", "like", "hate", "prefer", "enjoy", "dislike", "adore", "favor", "favourite", "favorite"]

# Conversation history management
CHAT_HISTORY_MAX = 8


def push_turn(history: List[Dict[str, str]], role: str, text: str) -> None:
    history.append({"role": role, "text": text, "time": datetime.now().isoformat(timespec="seconds")})
    while len(history) > CHAT_HISTORY_MAX:
        history.pop(0)


def detect_planet_opinion(text: str):
    """Detect whether the user expressed an opinion about a planet.

    Returns (planet, verb) or (None, None).
    """
    lower = text.lower()
    planet = None
    for p in PLANETS:
        if re.search(r"\b" + re.escape(p) + r"\b", lower):
            planet = p
            break
    if not planet:
        return None, None

    for v in OPINION_VERBS:
        if re.search(r"\bi\s+" + re.escape(v) + r"\b", lower) or re.search(r"\b" + re.escape(v) + r"\s+" + re.escape(planet) + r"\b", lower):
            return planet, v

    # check favorite constructions
    if "favorite" in lower or "favourite" in lower:
        return planet, "like"

    return planet, None


def llm_conversation_reply(user_input: str, chat_history: List[Dict[str, str]], memories: List[Dict[str, str]]) -> str:
    """Call OpenAI chat completion using the recent chat history and relevant memories.

    Falls back to simple_reply if OpenAI is not configured or call fails.
    """
    if openai is None or not os.getenv("OPENAI_API_KEY"):
        # simple fallback
        return simple_reply(user_input, memories)

    # Build messages: system persona, short context from memories, then chat history
    memory_context = "\n".join(f"- {m.get('text', '')}" for m in memories[:5])
    system = (
        "You are JimAI, a friendly space-savvy AI assistant with a sense of humor. "
        "Keep replies short (1-3 sentences), ask at most one follow-up question when helpful, "
        "and prefer conversational, engaging replies."
    )

    messages = [{"role": "system", "content": system}]

    if memory_context:
        messages.append({"role": "system", "content": f"Relevant memories:\n{memory_context}"})

    # Add recent chat history (convert roles)
    for turn in chat_history:
        role = "user" if turn["role"] == "user" else "assistant"
        messages.append({"role": role, "content": turn["text"]})

    # Finally add the current user input
    messages.append({"role": "user", "content": user_input})

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return simple_reply(user_input, memories)


def conversation_reply(user_input: str, chat_history: List[Dict[str, str]], memory: Memory, kb: KnowledgeBase) -> str:
    """A rule-based conversation manager that sometimes delegates to the LLM for nicer replies.

    Strategy:
    - Short rules for greetings, preferences, identity, and follow-ups.
    - Use KB or memories for factual questions first.
    - If user asks for "explain" or "tell me more", or if we want a natural reply, call the LLM.
    """
    text = user_input.strip()
    lower = text.lower()

    # Greetings
    if any(g in lower for g in ("hello", "hi", "hey")):
        return "Hey! Ready for some star talk? Who's your favorite planet today?"

    # Identity handled elsewhere in main loop, but keep fallback
    if any(p in lower for p in ("who are you", "what are you", "your name")):
        return "I’m JimAI — your space sidekick with a soft spot for meteor puns."

    # Detect planet + opinion first
    planet, verb = detect_planet_opinion(text)
    if planet and verb:
        # Save memory (main loop also saves non-questions, but be safe)
        memory.add(f"User said: {text} at {datetime.now().isoformat(timespec='seconds')}")
        planet_cap = planet.capitalize()
        # Normalize verb for reply (you <verb> <planet>)
        reply = f"Nice — I’ll remember you {verb} {planet_cap}. What else do you {verb} about {planet_cap}?"
        return reply

    # User expresses a preference or general statement -> save and follow up
    if lower.startswith("i ") or lower.startswith("my "):
        memory.add(f"User said: {text} at {datetime.now().isoformat(timespec='seconds')}")
        return "Nice! What do you like most about that?"

    # If user explicitly asks for more detail, prefer LLM
    if any(phrase in lower for phrase in ("tell me more", "explain", "why", "how come", "why is")):
        # Gather recent context and call LLM
        recent = [t for t in chat_history]
        recent_memories = memory.get_recent(limit=5)
        return llm_conversation_reply(user_input, recent, recent_memories)

    # If it's a question, prefer KB then memories
    if text.endswith("?"):
        kb_matches = kb.find_relevant(text, limit=2)
        if kb_matches:
            fact = kb_matches[0].get("text")
            return fact + "\n\n" + random.choice(HUMOR_LINES)

        mem_matches = memory.find_relevant(text, limit=2, exclude_text=text)
        if mem_matches:
            cleaned = memory._clean_memory_text(mem_matches[0].get("text", ""))
            cl_lower = cleaned.lower()
            if cl_lower.startswith("i "):
                reply = "You " + cleaned[2:]
            elif cl_lower.startswith("my "):
                reply = "Your " + cleaned[3:]
            else:
                reply = cleaned
            return reply + "\n\n" + random.choice(HUMOR_LINES)

        # No direct KB or memory hit — ask a friendly clarifying question
        return "That's interesting — what would you like to know about space on that?"

    # Fallback casual replies
    return random.choice([
        "Space is big and so are my opinions.",
        "Ask me a question about planets or tell me something about yourself.",
        "Want a neat space fact or a terrible space joke?",
    ])


def simple_reply(user_input: str, memories: list) -> str:
    """Kept as a minimal fallback for offline/LLM-failed mode."""
    cleaned = user_input.strip()
    if not cleaned:
        return "I didn't catch that. Try asking me something else."
    return "I'm still learning — try asking about planets, stars, or tell me something to remember."


def main() -> None:
    memory = Memory("memory.json")
    kb = KnowledgeBase("space_facts.json")
    chat_history: List[Dict[str, str]] = []

    print("JimAI: Hello! I can remember things, know some space facts, and have a conversation. Type 'exit' to stop.")

    while True:
        user_input = input("You: ")
        norm = user_input.strip().lower()

        if norm in {"exit", "quit", "bye"}:
            print("JimAI: Goodbye! I’ll remember what we discussed.")
            break

        # Push the user turn to chat history
        push_turn(chat_history, "user", user_input)

        # Memory-management and identity remain simple here
        if norm in {"clear memories", "clear memory", "forget all", "forget memories"}:
            memory.clear()
            print("JimAI: Okay — I forgot everything. My memory's a blank slate now.")
            push_turn(chat_history, "assistant", "Okay — I forgot everything.")
            continue

        if norm in {"forget last", "undo memory", "forget last memory"}:
            memory.remove_last(1)
            print("JimAI: I forgot the last thing you told me.")
            push_turn(chat_history, "assistant", "I forgot the last thing you told me.")
            continue

        if any(p in norm for p in ("who are you", "what are you", "your name", "who am i talking to")):
            humor = random.choice(HUMOR_LINES)
            memory.add(f"Told user who I am at {datetime.now().isoformat(timespec='seconds')}")
            reply = f"I’m JimAI — your space AI with a sense of humor. {humor}"
            print(f"JimAI: {reply}")
            push_turn(chat_history, "assistant", reply)
            continue

        # Determine if this is a question
        is_question = user_input.strip().endswith("?")

        # Prefer built-in knowledge for space questions
        if is_question:
            kb_matches = kb.find_relevant(user_input, limit=3)
            if kb_matches:
                fact = kb_matches[0].get("text")
                humor = random.choice(HUMOR_LINES)
                memory.add(f"Told user a fact: {fact} at {datetime.now().isoformat(timespec='seconds')}")
                reply = f"{fact}\n\n{humor}"
                print(f"JimAI: {reply}")
                push_turn(chat_history, "assistant", reply)
                continue

        # Only save the user's message as a memory if it's NOT a question
        if not is_question:
            memory.add(f"User said: {user_input} at {datetime.now().isoformat(timespec='seconds')}")

        # If no KB match, try user memories for questions (exclude the current input to avoid matches)
        relevant_memories = memory.find_relevant(user_input, limit=5, exclude_text=user_input) if is_question else []

        if relevant_memories:
            # create concise reply from the top memory
            top = relevant_memories[0]
            cleaned = memory._clean_memory_text(top.get("text", ""))
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
            push_turn(chat_history, "assistant", reply)
            continue

        # No direct KB or memory hit — use the conversation manager (rule-based or LLM)
        # conversation_reply will decide to call the LLM when appropriate
        reply = conversation_reply(user_input, chat_history, memory, kb)
        print(f"JimAI: {reply}")
        push_turn(chat_history, "assistant", reply)


if __name__ == "__main__":
    main()
