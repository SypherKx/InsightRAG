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
        "layout", "schematic", "blueprint", "illustration", "preview", "photo", "photos",
        "pic", "pics", "picture", "pictures", "snapshot", "crop", "screenshot", "snippet"
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
            has_view_verb = bool(re.search(r'\b(show|give|display|preview|crop|see|view|extract)\b', q_lower))
            return {"intent": "lookup", "top_k": 4, "is_visual": is_visual or has_view_verb, "target_page": None, "is_page_lookup": False}

        return {"intent": "standard", "top_k": 4, "is_visual": False, "target_page": None, "is_page_lookup": False}

    @classmethod
    def rewrite_query_with_llm(
        cls,
        current_query: str,
        history: Optional[List[Dict[str, Any]]] = None,
        ollama_url: str = "http://127.0.0.1:11434",
        model: str = "llama3.2:3b",
        timeout_seconds: float = 3.5,
    ) -> Tuple[str, bool]:
        """
        Rewrites the current query into a standalone question using the last 2 turns of chat history
        via the local Ollama LLM (temperature=0.0).
        
        If there is no history, returns (current_query, False).
        If Ollama is unavailable, times out, or produces invalid output, falls back to rule-based rewriting.
        
        Returns:
            Tuple of (rewritten_query_for_retrieval, was_rewritten)
        """
        if not history or not isinstance(history, list) or len(history) == 0:
            return current_query, False

        # Extract up to the last 2 turns of conversation history
        recent_turns = []
        for turn in history[-2:]:
            role = "User" if turn.get("role") == "user" else "Assistant"
            text = (turn.get("text") or turn.get("content") or "").strip()
            if text:
                if len(text) > 250:
                    text = text[:250] + "..."
                recent_turns.append(f"{role}: {text}")

        if not recent_turns:
            return current_query, False

        history_context = "\n".join(recent_turns)
        
        prompt = (
            "Given the following chat history and a follow-up question, rewrite the follow-up question "
            "into a clear, self-contained, standalone question for search and retrieval. "
            "Do NOT answer the question. Do NOT include explanations. Return ONLY the rewritten question.\n\n"
            f"Chat History:\n{history_context}\n\n"
            f"Follow-up Question: {current_query}\n"
            "Standalone Question:"
        )

        try:
            import httpx
            with httpx.Client(timeout=timeout_seconds) as client:
                res = client.post(
                    f"{ollama_url.rstrip('/')}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "keep_alive": "10m",
                        "options": {
                            "temperature": 0.0,
                            "num_predict": 60,
                            "top_k": 20,
                            "top_p": 0.9,
                        }
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    rewritten = data.get("response", "").strip()
                    # Strip leading/trailing quotes or 'Standalone Question:' echo
                    rewritten = re.sub(r'^(standalone question\s*:\s*|["\'])', '', rewritten, flags=re.IGNORECASE)
                    rewritten = rewritten.strip('"\'. \n')
                    if rewritten and len(rewritten) > 3 and rewritten.lower() != current_query.lower():
                        logger.info(f"Ollama conversational query rewrite: '{current_query}' -> '{rewritten}'")
                        return rewritten, True
        except Exception as e:
            logger.debug(f"Ollama query rewrite call failed or timed out ({e}); attempting heuristic fallback")

        # Fallback to rule-based rewrite if LLM was unavailable or produced identical text
        return cls.rewrite_conversational_query(current_query, history)

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
