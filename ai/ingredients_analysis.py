"""
Minimal Cohere-based analysis for ingredients text. No dependency on ai/clients or organizations.
"""
import os

import cohere

from ai.prompts import INGREDIENTS_ANALYSIS_PROMPT


def analyze_ingredients(ingredients_text: str) -> str:
    """Run LLM analysis on extracted ingredients text. Returns analysis string."""
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        return "Analysis unavailable: COHERE_API_KEY not set."
    ingredients_text = (ingredients_text or "").strip() or "No ingredients text provided."
    prompt = INGREDIENTS_ANALYSIS_PROMPT.format(ingredients_text=ingredients_text)
    client = cohere.Client(api_key)
    response = client.chat(
        message="Analyze the ingredients above and follow the instructions.",
        preamble=prompt,
        model=os.getenv("COHERE_LLM_MODEL", "command-r-plus"),
    )
    return (response.text or "").strip()
