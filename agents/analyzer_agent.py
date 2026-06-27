import asyncio
import random
import re
from agents.base_agent import BaseAgent
from core.step import Step

class AnalyzerAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="AnalyzerAgent", stream_delay=0.010)

    async def _execute(self, step, context):
        if step.payload.get("force_fail"):
            raise ValueError("Simulated analysis failure: input too ambiguous")
        
        prev_result = context.get(f"step_{step.index - 1}_result", "")
        raw_text = step.payload.get("text", prev_result) or "No source data available."
        
        await asyncio.sleep(random.uniform(0.4, 0.9))
        
        themes = self._extract_themes(raw_text)
        sentiment = self._estimate_sentiment(raw_text)
        summary = self._build_summary(raw_text, themes)
        
        return (
            f"[Analysis Report]\n"
            f"   • Summary   : {summary}\n"
            f"   • Key themes: {', '.join(themes)}\n"
            f"   • Sentiment : {sentiment}"
        )

    @staticmethod
    def _extract_themes(text):
        items = re.findall(r"\(\d+\)\s+([A-Za-z\s\-]+?)[\.,]", text)
        themes = [" ".join(t.strip().split()[0:4]) for t in items[:4]]
        return themes if themes else ["Innovation", "Growth", "Challenges"]

    @staticmethod
    def _estimate_sentiment(text):
        positive = ["growth", "progress", "improve", "increase", "advanced"]
        negative = ["challenge", "risk", "decline", "failure", "crisis"]
        pos = sum(text.lower().count(w) for w in positive)
        neg = sum(text.lower().count(w) for w in negative)
        if pos > neg:
            return "Positive 📈"
        elif neg > pos:
            return "Negative 📉"
        return "Neutral ↔️"

    @staticmethod
    def _build_summary(text, themes):
        first = text.split(".")[0].strip()[:80]
        theme_str = " and ".join(themes[:2]) if themes else "the topic"
        return f"Covers {theme_str}. {first}."