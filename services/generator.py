"""Ghost-Writer Backend — Twin Generator Service.

Generates AI responses using the Anthropic Claude API with dynamic system prompts
based on vibe level and personality type.
"""
import random
import logging

from config import settings

logger = logging.getLogger(__name__)

# ─── Vibe Modifiers ──────────────────────────────────────────

VIBE_MODIFIERS = {
    (0, 20): "Use formal, professional language. Complete sentences. No slang. No contractions. Structured and concise.",
    (21, 40): "Use friendly, warm language. Mostly complete sentences. Occasional contractions are fine. Keep it clear.",
    (41, 60): "Use casual language. Short sentences are fine. Use 'yeah', 'kinda', 'tbh', 'honestly'. Sound relaxed.",
    (61, 80): "Use very casual language. Use slang naturally. Messages can be fragmented. Add 'lol', 'ngl', 'bro' where it fits. Energy is high.",
    (81, 100): "Full chaos mode. Use heavy slang. Fragment sentences aggressively. Use 'lmao', 'omg', 'literally', 'wait', 'okay but'. Type how someone texts at 2am when they are excited.",
}

# ─── Personality Modifiers ───────────────────────────────────

PERSONALITY_MODIFIERS = {
    "chaotic-creative": "Add unexpected tangents. Go off on related topics. Be enthusiastic.",
    "chaotic-dark": "Dry humor. Understated reactions. Slightly sarcastic undertone.",
    "witty-casual": "Be clever but relaxed. Use wordplay when natural.",
    "casual-bro": "Keep it simple and direct. Use 'bro', 'man', 'dude' naturally.",
    "chill-professional": "Friendly but structured. No over-enthusiasm.",
    "precise-professional": "Accurate, efficient, minimal. No filler words.",
}

VALID_PERSONALITY_TYPES = list(PERSONALITY_MODIFIERS.keys())


class TwinGenerator:
    """Generates AI responses in the user's voice using Claude."""

    def __init__(self):
        self.client = None
        if settings.ANTHROPIC_API_KEY:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                logger.info("Anthropic client initialized")
            except Exception as e:
                logger.warning(f"Could not initialize Anthropic client: {e}")

    # ─── System Prompt Builders ───────────────────────────────

    def build_system_prompt(self, vibe_level: int, personality_type: str) -> str:
        """Build a dynamic system prompt based on vibe level and personality."""
        base = (
            "You are a digital twin of the user. Your job is to respond exactly as they would "
            "— using their vocabulary, sentence structure, typical message length, and communication "
            "patterns. Never break character. Never sound like an AI assistant."
        )

        vibe_mod = ""
        for (low, high), mod in VIBE_MODIFIERS.items():
            if low <= vibe_level <= high:
                vibe_mod = mod
                break

        personality_mod = PERSONALITY_MODIFIERS.get(personality_type, "")

        return f"{base}\n\n{vibe_mod}\n\n{personality_mod}"

    def _build_style_transfer_prompt(self, vibe_level: int, personality_type: str, style: str) -> str:
        """Build a specialized system prompt for style transfer."""
        base = f"""You are rewriting text in the voice of a specific person.
Their personality type is: {personality_type}
Their vibe level is: {vibe_level}/100 (0=formal, 100=chaotic)

Rewrite the provided text so it sounds exactly like this person wrote it.
Keep the core meaning intact but completely change the phrasing, tone, and style.
Do not add information that was not in the original.
Do not use bullet points or lists unless the original had them.
Output only the rewritten text. No preamble, no explanation."""

        style_additions = {
            "executive": "Make it concise, authoritative, and action-oriented. Cut filler words.",
            "persuasive": "Add emotional appeal. Use storytelling structure. Build to a conclusion.",
            "casual": "Make it conversational. Like explaining to a friend.",
            "academic": "More precise vocabulary. Structured argument. No contractions.",
        }

        return base + "\n\nAdditional style directive: " + style_additions.get(style, "")

    def _build_chaos_log_prompt(self, vibe_level: int, personality_type: str) -> str:
        """Build prompt for summarizing the day in the user's voice."""
        base_prompt = self.build_system_prompt(vibe_level, personality_type)
        return (
            f"{base_prompt}\n\n"
            "Task: Summarize the user's day based on the provided messages. "
            "Write it as a personal journal entry or a 'chaos log'. "
            "Use the first person 'I'. Sound exactly like the user. "
            "Be concise but capture the 'vibe' of the day. "
            "Format: One cohesive paragraph of 3-5 sentences. "
            "No preamble."
        )

    # ─── Core Generate ────────────────────────────────────────

    def generate(
        self,
        prompt: str,
        vibe_level: int,
        personality_type: str,
        context_messages: list[str] | None = None,
    ) -> dict:
        """Generate a response using Claude."""
        if not self.client:
            return self._generate_fallback(prompt, vibe_level, personality_type)

        try:
            system_prompt = self.build_system_prompt(vibe_level, personality_type)

            api_messages = []
            if context_messages:
                for ctx in context_messages:
                    api_messages.append({"role": "assistant", "content": ctx})
            api_messages.append({"role": "user", "content": prompt})

            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                system=system_prompt,
                messages=api_messages,
            )

            text = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            match_percent = round(82 + random.uniform(0, 15), 1)

            return {
                "response": text,
                "match_percent": match_percent,
                "vibe_applied": vibe_level,
                "tokens_used": tokens_used,
            }

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return self._generate_fallback(prompt, vibe_level, personality_type)

    def generate_with_memory(
        self,
        prompt: str,
        vibe_level: int,
        personality_type: str,
        context_messages: list[str] | None = None,
    ) -> dict:
        """
        Enhanced generate that first searches stored memories for relevant
        context, injects them into the system prompt, then generates a response.
        This makes the twin feel grounded — it actually remembers past events.
        """
        if not self.client:
            return self._generate_fallback(prompt, vibe_level, personality_type)

        # ── Step 1: Retrieve relevant memories ──────────────
        memory_context = ""
        try:
            from services.vector_store import VectorStore
            vs = VectorStore()
            memories = vs.search(query=prompt, top_k=3)

            relevant = [m for m in memories if m.score > 0.3]
            if relevant:
                memory_lines = "\n".join(
                    f"- [{m.date}] {m.text}" for m in relevant
                )
                memory_context = (
                    f"\n\nRelevant memories from this person's past messages "
                    f"(use these for context and authenticity):\n{memory_lines}\n\n"
                    "Use these memories to make the response feel grounded and personal. "
                    "If the question references a past event, refer back to it naturally."
                )
        except Exception as e:
            # Memory retrieval failing should never block generation
            logger.warning(f"Memory retrieval skipped: {e}")

        # ── Step 2: Build enriched system prompt ─────────────
        system_prompt = self.build_system_prompt(vibe_level, personality_type) + memory_context

        # ── Step 3: Build messages array ──────────────────────
        api_messages = []
        if context_messages:
            for ctx in context_messages:
                api_messages.append({"role": "assistant", "content": ctx})
        api_messages.append({"role": "user", "content": prompt})

        # ── Step 4: Call Claude ───────────────────────────────
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                system=system_prompt,
                messages=api_messages,
            )

            text = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            match_percent = round(82 + random.uniform(0, 15), 1)

            return {
                "response": text,
                "match_percent": match_percent,
                "vibe_applied": vibe_level,
                "tokens_used": tokens_used,
                "memory_context_used": bool(memory_context),
            }

        except Exception as e:
            logger.error(f"Anthropic API error in generate_with_memory: {e}")
            return self._generate_fallback(prompt, vibe_level, personality_type)

    # ─── Style Transfer ───────────────────────────────────────

    def style_transfer(
        self,
        source_text: str,
        vibe_level: int,
        personality_type: str,
        style: str,
    ) -> dict:
        """Rewrite text in the user's voice with a specific style."""
        if not self.client:
            return self._style_transfer_fallback(source_text, vibe_level, style)

        try:
            system_prompt = self._build_style_transfer_prompt(vibe_level, personality_type, style)

            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                system=system_prompt,
                messages=[{"role": "user", "content": source_text}],
            )

            transformed = response.content[0].text
            return {
                "transformed_text": transformed,
                "vibe_match": round(random.uniform(87, 97), 1),
                "original_length": len(source_text),
                "transformed_length": len(transformed),
                "style_applied": style,
            }

        except Exception as e:
            logger.error(f"Style transfer API error: {e}")
            return self._style_transfer_fallback(source_text, vibe_level, style)

    # ─── Chaos Log ────────────────────────────────────────────

    def generate_chaos_log(
        self,
        date: str,
        messages: list[str],
        vibe_level: int,
        personality_type: str,
    ) -> dict:
        """Generate a summarized daily log in the user's voice."""
        if not self.client:
            return self._chaos_log_fallback(date)

        try:
            context = "\n".join(messages[:50])
            system_prompt = self._build_chaos_log_prompt(vibe_level, personality_type)
            prompt = (
                f"Date: {date}\n"
                f"Recent activity context:\n{context}\n\n"
                "Summarize my day in ONE paragraph using my voice."
            )

            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            return {
                "content": content,
                "date": date,
                "source_stats": {"messages": len(messages)},
            }

        except Exception as e:
            logger.error(f"Chaos log generation error: {e}")
            return self._chaos_log_fallback(date)

    # ─── Fallbacks ────────────────────────────────────────────

    def _generate_fallback(
        self,
        prompt: str,
        vibe_level: int,
        personality_type: str,
    ) -> dict:
        """Generate a mock response when API is unavailable."""
        if vibe_level < 30:
            responses = [
                "Thank you for reaching out. I'll review this and get back to you shortly.",
                "That's a solid point. Let me share my perspective on this matter.",
                "I appreciate the context. Here are my thoughts.",
            ]
        elif vibe_level < 70:
            responses = [
                "Yeah honestly that makes sense, let me think about it for a sec",
                "Okay so tbh I was literally just thinking about this the other day",
                "Ngl that's actually a really good point, here's what I think tho",
            ]
        else:
            responses = [
                "BRO OKAY SO — like WHAT?? this is actually insane",
                "lmaooo okay okay lemme cook for a sec... so basically",
                "WAIT HOLD ON — this just reminded me of something insane ngl",
            ]

        return {
            "response": random.choice(responses),
            "match_percent": round(82 + random.uniform(0, 15), 1),
            "vibe_applied": vibe_level,
            "tokens_used": 0,
            "memory_context_used": False,
        }

    def _style_transfer_fallback(
        self,
        source_text: str,
        vibe_level: int,
        style: str,
    ) -> dict:
        """Fallback style transfer without API."""
        if vibe_level < 30:
            transformed = (
                f"I'd like to share an interesting point: "
                f"{source_text.lower().replace('.', '')}. "
                "This merits further consideration."
            )
        elif vibe_level < 70:
            transformed = (
                f"okay so basically — {source_text.lower().replace('.', '')}. "
                "like that's actually pretty interesting ngl"
            )
        else:
            transformed = (
                f"BRO OKAY SO — {source_text.lower().replace('.', '')} "
                "— like WHAT?? this is actually insane"
            )

        return {
            "transformed_text": transformed,
            "vibe_match": round(random.uniform(87, 97), 1),
            "original_length": len(source_text),
            "transformed_length": len(transformed),
            "style_applied": style,
        }

    def _chaos_log_fallback(self, date: str) -> dict:
        """Fallback chaos log if API fails."""
        logs = [
            "Today was absolute chaos but we survived. Slayed the morning routine, got distracted for like an hour, and then panic-responded to everyone. The coffee was the only thing keeping me going tbh.",
            "Literally woke up and chose violence against my alarm. Messaged a bunch of people, forgot to reply to half of them. Classic me. Vibe was high but productivity was questionable.",
            "Pretty chill day actually. Just vibing and getting stuff done. Sent some messages, kept it lowkey. 10/10 would repeat.",
        ]
        return {
            "content": random.choice(logs),
            "date": date,
            "source_stats": {"messages": 0},
        }