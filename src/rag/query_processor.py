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
        
        # Check multi-part query patterns
        is_multi_part = bool(
            re.search(r'\b(and also|as well as|along with|plus|aur|tatha)\b', q_lower) or
            ("?" in query and query.count("?") > 1) or
            re.search(r'\b(what|how|why|where|when|explain)\b.*\b(and|aur)\b.*\b(what|how|why|where|when|explain)\b', q_lower)
        )
        is_comparative = bool(re.search(r'\b(compare|comparison|versus|vs\.?|difference between|differences between)\b', q_lower))

        if target_page is not None:
            return {
                "intent": "page_lookup",
                "top_k": 5,
                "is_visual": is_visual,
                "target_page": target_page,
                "is_page_lookup": True,
                "is_multi_part": is_multi_part,
            }

        if is_visual:
            return {"intent": "visual", "top_k": 4, "is_visual": True, "target_page": None, "is_page_lookup": False, "is_multi_part": is_multi_part}

        if is_comparative:
            return {"intent": "comparative", "top_k": 6, "is_visual": False, "target_page": None, "is_page_lookup": False, "is_multi_part": True}

        if is_multi_part:
            return {"intent": "multi_part", "top_k": 6, "is_visual": False, "target_page": None, "is_page_lookup": False, "is_multi_part": True}
        
        if len(words) <= 5 and any(w in words for w in ["what", "who", "when", "where", "define"]):
            return {"intent": "factual", "top_k": 4, "is_visual": False, "target_page": None, "is_page_lookup": False, "is_multi_part": False}
            
        if any(w in words for w in ["compare", "difference", "explain", "why", "how", "analyze", "summarize"]):
            return {"intent": "analytical", "top_k": 5, "is_visual": False, "target_page": None, "is_page_lookup": False, "is_multi_part": False}
            
        if re.search(r'\b(section|chapter|part|model|v\d+|\d+\.\d+)\b', q_lower):
            has_view_verb = bool(re.search(r'\b(show|give|display|preview|crop|see|view|extract)\b', q_lower))
            return {"intent": "lookup", "top_k": 4, "is_visual": is_visual or has_view_verb, "target_page": None, "is_page_lookup": False, "is_multi_part": False}

        return {"intent": "standard", "top_k": 5, "is_visual": False, "target_page": None, "is_page_lookup": False, "is_multi_part": False}

    HINGLISH_TRANSLATION_MAP = {
        "bhai": "",
        "yaar": "",
        "isme": "in this",
        "isme se": "from this",
        "ye": "this",
        "yeh": "this",
        "kaise": "how",
        "kaam karta hai": "works mechanics architecture",
        "kaam karti hai": "works mechanics architecture",
        "karta hai": "does",
        "karti hai": "does",
        "kya hai": "what is definition details",
        "kya": "what",
        "konsa": "which",
        "kounsa": "which",
        "batao": "explain describe details",
        "samjhao": "explain overview details",
        "karo": "",
        "kariye": "",
        "aur": "and",
        "tatha": "and",
        "ke bare me": "about regarding",
        "bare me": "about regarding",
        "ke baare mein": "about regarding",
        "baare mein": "about regarding",
        "fayde": "benefits advantages",
        "nuksan": "disadvantages limitations",
        "antar": "difference comparison",
        "farq": "difference comparison",
    }

    @classmethod
    def normalize_hinglish_query(cls, query: str) -> str:
        """
        Translates/normalizes Hinglish & colloquial phrases to English technical keywords
        to maximize dense FAISS vector and BM25 recall against English documents.
        """
        q = query.strip()
        q_lower = q.lower()
        has_hinglish = any(
            re.search(r'\b' + re.escape(k) + r'\b', q_lower)
            for k in ["bhai", "yaar", "isme", "kaise", "kya", "konsa", "batao", "samjhao", "ke bare", "karta hai", "fayde", "antar"]
        )
        if not has_hinglish:
            return q

        normalized = q_lower
        for hk, en in cls.HINGLISH_TRANSLATION_MAP.items():
            normalized = re.sub(r'\b' + re.escape(hk) + r'\b', en, normalized)

        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized if len(normalized) >= 4 else q

    @classmethod
    def decompose_query(
        cls,
        query: str,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        Decomposes complex, compound, comparative, or conversational queries into 2-4 focused sub-queries.
        Enables multi-query RAG so each part of the user's question retrieves matching context.
        """
        sub_queries: List[str] = []
        raw_clean = query.strip()
        if not raw_clean:
            return [query]

        # 1. Primary normalized query
        normalized = cls.normalize_hinglish_query(raw_clean)
        sub_queries.append(normalized)

        # 2. Check comparative queries (e.g. "compare X and Y", "difference between X and Y", "X vs Y")
        comp_match = re.search(
            r'(?:compare|comparison between|difference between|differences between)\s+([a-zA-Z0-9_\-\s]+?)\s+(?:and|with|versus|vs\.?)\s+([a-zA-Z0-9_\-\s]+)',
            normalized,
            re.IGNORECASE
        )
        if comp_match:
            ent1 = comp_match.group(1).strip()
            ent2 = comp_match.group(2).strip()
            if ent1 and ent2:
                sub_queries.append(f"{ent1} specifications features overview")
                sub_queries.append(f"{ent2} specifications features overview")
                sub_queries.append(f"comparison difference between {ent1} and {ent2}")
                return list(dict.fromkeys(sub_queries))[:4]

        # 3. Delimiter & clause splitting (questions with multiple '?', ';', or conjunctions)
        # Split on question marks or semicolons
        parts = [p.strip() for p in re.split(r'[\?;]', raw_clean) if len(p.strip()) > 5]
        if len(parts) > 1:
            for p in parts[:3]:
                norm_p = cls.normalize_hinglish_query(p)
                if norm_p not in sub_queries:
                    sub_queries.append(norm_p)
            return list(dict.fromkeys(sub_queries))[:4]

        # 4. Multi-clause conjunction splitting ("and also", "as well as", "and how", "and what", "along with", "and", ",")
        conjunction_split = re.split(
            r'\b(?:and also|as well as|along with|plus|and what|and how|and why|and where|and explain|\band\b)\b|,',
            normalized,
            flags=re.IGNORECASE
        )
        if len(conjunction_split) > 1:
            for clause in conjunction_split:
                c_clean = clause.strip().strip(',. ')
                c_clean = re.sub(r'^(what is|tell me about|how does|why is|explain)\s+', '', c_clean, flags=re.IGNORECASE).strip()
                if len(c_clean) > 3 and c_clean not in sub_queries and not any(c_clean == w for w in ["this", "that", "it", "how"]):
                    sub_queries.append(c_clean)

        # Deduplicate while preserving order and limit to max 4 sub-queries
        clean_sub_queries = []
        for sq in sub_queries:
            sq_stripped = sq.strip()
            if sq_stripped and sq_stripped not in clean_sub_queries:
                clean_sub_queries.append(sq_stripped)

        return clean_sub_queries[:4]

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
            use_model = "llama3.2:3b" if ("vl" in str(model).lower() or "vision" in str(model).lower()) else model
            with httpx.Client(timeout=timeout_seconds) as client:
                res = client.post(
                    f"{ollama_url.rstrip('/')}/api/generate",
                    json={
                        "model": use_model,
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

        # Check if query contains ambiguous follow-up phrasing or referential visual follow-up
        has_pronoun = bool(words.intersection(cls.PRONOUNS))
        is_visual_followup = bool(re.search(
            r'\b(the\s+(?:photo|image|picture|diagram|figure|chart|graph|plot|table|schematic)|'
            r'(?:show|send|provide|give|display)\s+(?:me\s+)?(?:the\s+)?(?:photo|image|picture|diagram|figure|chart|graph|plot|it|them))\b',
            q_lower
        ))
        is_short_followup = len(words) <= 7 and ("why" in words or "how" in words or "what about" in q_lower or has_pronoun or is_visual_followup)

        if not (has_pronoun or is_short_followup or is_visual_followup):
            return current_query, False

        # Extract dominant topic entity and antecedent page from recent history
        antecedent_topic = ""
        antecedent_page = None
        for turn in reversed(history[-4:]):
            text = (turn.get("text") or turn.get("content") or "").strip()
            if not text or text == current_query:
                continue
            if antecedent_page is None:
                p = cls.extract_target_page(text)
                if p is not None:
                    antecedent_page = p
            if not antecedent_topic and turn.get("role") == "user":
                clean = re.sub(r'^(what is|explain|tell me about|how does|why is|describe|send me|provide me|show me)\s+', '', text, flags=re.IGNORECASE).strip('?. ')
                clean = re.sub(r'\b(?:on\s+)?(?:page|pg|p\.?|pno|page\s*no|page\s*number)\s*[:#\-]?\s*\d+\b', '', clean, flags=re.IGNORECASE).strip('?. ')
                if len(clean) > 2 and clean.lower() not in q_lower:
                    antecedent_topic = clean

        page_suffix = f" on page {antecedent_page}" if (antecedent_page and cls.extract_target_page(current_query) is None) else ""
        topic_suffix = f" regarding {antecedent_topic}" if antecedent_topic and antecedent_topic.lower() not in q_lower else ""

        if page_suffix or topic_suffix:
            rewritten = f"{current_query.rstrip('?.')}{page_suffix}{topic_suffix}".strip()
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
