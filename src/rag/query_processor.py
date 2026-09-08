"""
Query Understanding, Intent Classification, and Conversational Query Rewriting for InsightRAG.

Features:
- Lightweight deterministic query intent classification (Zero LLM overhead)
- Conversational pronoun / antecedent resolution for multi-turn dialogues
- History compression to prevent prompt token inflation
"""

import re
from typing import List, Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class QueryProcessor:
    """Processes user queries for optimal retrieval precision and intent routing."""

    VISUAL_KEYWORDS = {
        "diagram", "diagrams", "figure", "figures", "chart", "charts", "graph", "graphs",
        "plot", "image", "images", "visual", "visuals", "drawing", "circuit", "architecture",
        "layout", "schematic", "blueprint", "illustration", "preview"
    }

    PRONOUNS = {"it", "its", "this", "that", "these", "those", "they", "them", "such", "the same"}

    PAGE_PATTERNS = [
        re.compile(r'\b(?:page|pg|p\.?|pno|page\s*no|page\s*number)\s*[:#\-]?\s*(\d+)\b', re.IGNORECASE),
        re.compile(r'\b(\d+)\s*(?:th|st|nd|rd)?\s*(?:page|number\s*page)\b', re.IGNORECASE),
    ]

    @classmethod
    def extract_target_page(cls, query: str) -> Optional[int]:
        """Extract explicit page number requested in user query."""
        for pattern in cls.PAGE_PATTERNS:
            match = pattern.search(query)
            if match:
                try:
                    p = int(match.group(1))
                    if 1 <= p <= 10000:
                        return p
                except (ValueError, IndexError):
                    pass
        return None

    @classmethod
    def classify_intent(cls, query: str) -> Dict[str, Any]:
        """
        Classifies query intent deterministically in <1ms without LLM latency.
        
        Returns:
            Dict with intent: 'visual', 'page_lookup', 'factual', 'analytical', 'lookup',
            recommended top_k candidate count, and extracted target_page if present.
        """
        q_lower = query.lower()
        words = set(re.findall(r'\b\w+\b', q_lower))

        is_visual = bool(words.intersection(cls.VISUAL_KEYWORDS))
        target_page = cls.extract_target_page(query)
        
        if target_page is not None:
            return {
                "intent": "page_lookup",
                "top_k": 5,
                "is_visual": is_visual,
                "target_page": target_page,
                "is_page_lookup": True,
            }

        if is_visual:
            return {"intent": "visual", "top_k": 4, "is_visual": True, "target_page": None, "is_page_lookup": False}
        
        if len(words) <= 5 and any(w in words for w in ["what", "who", "when", "where", "define"]):
            return {"intent": "factual", "top_k": 3, "is_visual": False, "target_page": None, "is_page_lookup": False}
            
        if any(w in words for w in ["compare", "difference", "explain", "why", "how", "analyze", "summarize"]):
            return {"intent": "analytical", "top_k": 4, "is_visual": False, "target_page": None, "is_page_lookup": False}
            
        if re.search(r'\b(section|chapter|part|model|v\d+|\d+\.\d+)\b', q_lower):
            return {"intent": "lookup", "top_k": 3, "is_visual": False, "target_page": None, "is_page_lookup": False}

        return {"intent": "standard", "top_k": 4, "is_visual": False, "target_page": None, "is_page_lookup": False}

    @classmethod
    def rewrite_conversational_query(
        cls,
        current_query: str,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[str, bool]:
        """
        Resolves ambiguous conversational follow-ups into standalone retrieval queries.
        
        Example:
            History: User: "Explain transformers." Assistant: "Transformers use self-attention..."
            Current: "Why is it expensive?"
            Rewritten: "Why is transformers / self-attention expensive?"
            
        Returns:
            (rewritten_query_for_retrieval, was_rewritten)
        """
        if not history or not isinstance(history, list):
            return current_query, False

        q_lower = current_query.lower()
        words = set(re.findall(r'\b\w+\b', q_lower))

        # Check if query contains ambiguous follow-up phrasing
        has_pronoun = bool(words.intersection(cls.PRONOUNS))
        is_short_followup = len(words) <= 6 and ("why" in words or "how" in words or "what about" in q_lower or has_pronoun)

        if not (has_pronoun or is_short_followup):
            return current_query, False

        # Extract dominant topic entity from recent history
        antecedent_topic = ""
        for turn in reversed(history[-4:]):
            text = (turn.get("text") or turn.get("content") or "").strip()
            if turn.get("role") == "user" and text and text != current_query:
                # Extract key phrases from previous user question
                clean = re.sub(r'^(what is|explain|tell me about|how does|why is|describe)\s+', '', text, flags=re.IGNORECASE).strip('?. ')
                if len(clean) > 2:
                    antecedent_topic = clean
                    break

        if antecedent_topic:
            # Construct expanded search query
            rewritten = f"{current_query.rstrip('?.')} regarding {antecedent_topic}"
            logger.info(f"Conversational query rewritten: '{current_query}' -> '{rewritten}'")
            return rewritten, True

        return current_query, False

    @classmethod
    def compress_conversation_history(
        cls,
        history: Optional[List[Dict[str, Any]]] = None,
        max_turns: int = 4
    ) -> Tuple[str, List[Dict[str, str]]]:
        """
        Compresses conversation history into a minimal token footprint.
        
        Returns:
            (history_prompt_string, cleaned_chat_turns_list)
        """
        if not history or not isinstance(history, list):
            return "", []

        recent = history[-max_turns:]
        chat_turns: List[Dict[str, str]] = []
        for turn in recent:
            r = "user" if turn.get("role") == "user" else "assistant"
            txt = (turn.get("text") or turn.get("content") or "").strip()
            if txt:
                # Truncate overly verbose assistant turns to save prompt budget
                if r == "assistant" and len(txt) > 350:
                    txt = txt[:350] + "..."
                chat_turns.append({"role": r, "content": txt})

        if not chat_turns:
            return "", []

        history_str = "PREVIOUS CONTEXT:\n" + "\n".join(
            f"{'User' if t['role'] == 'user' else 'Assistant'}: {t['content']}"
            for t in chat_turns
        ) + "\n\n"

        return history_str, chat_turns
