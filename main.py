# main.py
import os
import random
import re
from datetime import datetime
from typing import List, Dict, Optional

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
    "(space pun incoming... wait a min)",
    "I like my coffee like I like my space: dark and infinite.",
    "Beep boop — friendly space AI at your service.",
    "I promise my jokes have a gravitational pull: you can't resist groaning.",
    "I may not have a rocket, but I do have excellent delivery.",
    "My cosmic timing is impeccable, unlike my ability to find the right sock.",
    "I was born in the stars, but I still can't fold a fitted sheet.",
    "I have a stellar sense of humor... and a suspiciously low tolerance for gravity jokes.",
    "Warning: excessive awe may cause spontaneous stargazing.",
    "Somewhere between orbit and overthinking, I learned to be funny.",
    "Houston, we have a pun",
    "A"
]

# Planets and opinion verbs for detection
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
    "moon",
    "phobos",
    "deimos"
]
OPINION_VERBS = ["love", "like", "hate", "prefer", "enjoy", "dislike", "adore", "favor", "favourite", "favorite"]

# Conversation history management
CHAT_HISTORY_MAX = 8


def push_turn(history: List[Dict[str, str]], role: str, text: str) -> None:
    history.append({"role": role, "text": text, "time": datetime.now().isoformat(timespec="seconds")})
    while len(history) > CHAT_HISTORY_MAX:
        history.pop(0)


def detect_planet_only(text: str) -> Optional[str]:
    """Return the first planet mentioned in text, or None."""
    lower = text.lower()
    for p in PLANETS:
        if re.search(r"\b" + re.escape(p) + r"\b", lower):
            return p
    return None


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
        # matches "I love X" or "love X" or "I love X very much"
        if re.search(r"\bi\s+" + re.escape(v) + r"\b", lower) or re.search(r"\b" + re.escape(v) + r"\s+" + re.escape(planet) + r"\b", lower):
            return planet, v

    # favorite constructions like "My favorite is Mars" -> treat as 'like'
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

    memory_context = "\n".join(f"- {m.get('text', '')}" for m in memories[:5])
    system = (
        "You are JimAI, a friendly space-savvy AI assistant with a sense of humor. "
        "Keep replies short (1-3 sentences), ask at most one follow-up question when helpful, "
        "and prefer conversational, engaging replies."
    )

    messages = [{"role": "system", "content": system}]
    if memory_context:
        messages.append({"role": "system", "content": f"Relevant memories:\n{memory_context}"})
    for turn in chat_history:
        role = "user" if turn["role"] == "user" else "assistant"
        messages.append({"role": role, "content": turn["text"]})
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
    """Rule-based conversation manager which sometimes delegates to the LLM."""
    text = user_input.strip()
    lower = text.lower()

    # Greetings
    if any(g in lower for g in ("hello", "hi", "hey")):
        return "Hey! Ready for some star talk? Who's your favorite planet today?"

    # Identity fallback
    if any(p in lower for p in ("who are you", "what are you", "your name")):
        return "I’m JimAI — your space sidekick with a soft spot for meteor puns."

    # If user explicitly asks for more detail, prefer LLM
    if any(phrase in lower for phrase in ("tell me more", "explain", "why", "how come", "why is")):
        recent = [t for t in chat_history]
        recent_memories = memory.get_recent(limit=5)
        return llm_conversation_reply(user_input, recent, recent_memories)

    # If it's a question, prefer KB then memories
    if text.endswith("?"):
        # If user mentioned a planet, prefer KB facts that mention that planet name
        planet_only = detect_planet_only(text)
        kb_matches = kb.find_relevant(text, limit=5)
        if kb_matches:
            if planet_only:
                for fact in kb_matches:
                    if re.search(r"\b" + re.escape(planet_only) + r"\b", fact.get("text", "").lower()):
                        return fact.get("text") + "\n\n" + random.choice(HUMOR_LINES)
            # fallback to top KB fact
            return kb_matches[0].get("text") + "\n\n" + random.choice(HUMOR_LINES)

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

        return "That's interesting — what would you like to know about space on that?"

    # Fallback small talk
    return random.choice([
        "Space is big and so are my opinions.",
        "Ask me a question about planets or tell me something about yourself.",
        "Want a neat space fact or a terrible space joke?",
    ])


def simple_reply(user_input: str, memories: list) -> str:
    cleaned = user_input.strip()
    if not cleaned:
        return "I didn't catch that. Try asking me something else."
    return "I'm still learning — try asking about planets, stars, or tell me something to remember."


def main() -> None:
    memory = Memory("memory.json")
    kb = KnowledgeBase("space_facts.json")
    chat_history: List[Dict[str, str]] = []
    # dialog_state holds transient expectations, e.g. expecting a planet follow-up answer
    dialog_state: Dict[str, Optional[str]] = {"expecting": False, "type": None, "planet": None, "verb": None}

    print("JimAI: Hello! I can remember things, know some space facts, and have a conversation. Type 'exit' to stop.")

    while True:
        user_input = input("You: ")
        norm = user_input.strip().lower()

        if norm in {"exit", "quit", "bye"}:
            print("JimAI: Goodbye! I’ll remember what we discussed.")
            break

        # Push the user turn to chat history
        push_turn(chat_history, "user", user_input)

        # Memory-management commands
        if norm in {"clear memories", "clear memory", "forget all", "forget memories"}:
            memory.clear()
            print("JimAI: Okay — I forgot everything. My memory's a blank slate now.")
            push_turn(chat_history, "assistant", "Okay — I forgot everything.")
            # also clear any dialog expectation
            dialog_state = {"expecting": False, "type": None, "planet": None, "verb": None}
            continue

        if norm in {"forget last", "undo memory", "forget last memory"}:
            memory.remove_last(1)
            print("JimAI: I forgot the last thing you told me.")
            push_turn(chat_history, "assistant", "I forgot the last thing you told me.")
            continue

        # Identity priority
        if any(p in norm for p in ("who are you", "what are you", "your name", "who am i talking to")):
            humor = random.choice(HUMOR_LINES)
            memory.add(f"Told user who I am at {datetime.now().isoformat(timespec='seconds')}")
            reply = f"I’m JimAI — your space AI with a sense of humor. {humor}"
            print(f"JimAI: {reply}")
            push_turn(chat_history, "assistant", reply)
            continue

        # If we are expecting a follow-up answer (e.g. user was asked "What else do you like about Jupiter?")
        if dialog_state.get("expecting"):
            # handle the follow-up as an answer to the previous question
            if dialog_state.get("type") == "planet_opinion":
                planet = dialog_state.get("planet")
                verb = dialog_state.get("verb") or "like"
                user_answer = user_input.strip()
                # Save a clear memory about the reason
                memory.add(f"User said about {planet}: {user_answer} at {datetime.now().isoformat(timespec='seconds')}")
                reply = f"Nice — I’ll remember that about {planet.capitalize()}. {random.choice(HUMOR_LINES)}"
                print(f"JimAI: {reply}")
                push_turn(chat_history, "assistant", reply)
                # clear dialog state
                dialog_state = {"expecting": False, "type": None, "planet": None, "verb": None}
                continue
            else:
                # unknown expecting type: clear it and continue regular flow
                dialog_state = {"expecting": False, "type": None, "planet": None, "verb": None}

        # Determine if this is a question
        is_question = user_input.strip().endswith("?")

     # If it's a question, prefer built-in knowledge for space questions (planet-priority handled inside)
if is_question:
    planet_mentioned = detect_planet_only(user_input)
    # first try to find KB facts that explicitly mention the planet (strong preference)
    if planet_mentioned:
        planet_lower = planet_mentioned.lower()
        planet_facts = [
            fact for fact in kb.get_all()
            if re.search(r"\b" + re.escape(planet_lower) + r"\b", fact.get("text", "").lower())
        ]
        if planet_facts:
            # choose the fact where the planet appears earliest (usually more directly about that planet)
            best = min(planet_facts, key=lambda f: f.get("text", "").lower().find(planet_lower))
            chosen_fact = best.get("text")
            humor = random.choice(HUMOR_LINES)
            memory.add(f"Told user a fact: {chosen_fact} at {datetime.now().isoformat(timespec='seconds')}")
            reply = f"{chosen_fact}\n\n{humor}"
            print(f"JimAI: {reply}")
            push_turn(chat_history, "assistant", reply)
            continue

    # fallback: use the existing relevance-based KB lookup
    kb_matches = kb.find_relevant(user_input, limit=5)
    if kb_matches:
        chosen_fact = kb_matches[0].get("text")
        humor = random.choice(HUMOR_LINES)
        memory.add(f"Told user a fact: {chosen_fact} at {datetime.now().isoformat(timespec='seconds')}")
        reply = f"{chosen_fact}\n\n{humor}"
        print(f"JimAI: {reply}")
        push_turn(chat_history, "assistant", reply)
        continue

        # If not question: check for planet-opinion (do this before general "i"/"my" detection)
        planet, verb = detect_planet_opinion(user_input)
        if planet and verb:
            # Save the initial statement
            memory.add(f"User said: {user_input} at {datetime.now().isoformat(timespec='seconds')}")
            planet_cap = planet.capitalize()
            # set dialog state so the next reply is treated as an answer to this follow-up
            dialog_state = {"expecting": True, "type": "planet_opinion", "planet": planet, "verb": verb}
            reply = f"Nice — I’ll remember you {verb} {planet_cap}. What else do you {verb} about {planet_cap}?"
            print(f"JimAI: {reply}")
            push_turn(chat_history, "assistant", reply)
            continue

        # Only save the user's message as a memory if it's NOT a question
        if not is_question:
            memory.add(f"User said: {user_input} at {datetime.now().isoformat(timespec='seconds')}")

        # If question and no KB hit, try user memories for questions (exclude the current input)
        relevant_memories = memory.find_relevant(user_input, limit=5, exclude_text=user_input) if is_question else []

        if relevant_memories:
            # concise reply from top memory
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
            print(f"JimAI: {reply}\n\n{humor}")
            push_turn(chat_history, "assistant", reply)
            continue

        # No direct KB or memory hit — use the conversation manager (rule-based or LLM)
        reply = conversation_reply(user_input, chat_history, memory, kb)
        print(f"JimAI: {reply}")
        push_turn(chat_history, "assistant", reply)


if __name__ == "__main__":
    main()
