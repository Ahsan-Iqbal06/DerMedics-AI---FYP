"""Text generation for condition descriptions and medicine suggestions.

`OpenAICompatibleProvider` talks to any OpenAI-compatible chat endpoint (Qwen via DashScope by default).
When no LLM_API_KEY is configured, or a call fails, `KnowledgeBaseProvider` serves curated content.
"""

import json
import logging
from functools import lru_cache

from app.core.config import get_settings
from app.schemas import ConditionInfo, MedicineSuggestion
from app.services.knowledge_base import display_name, load_conditions

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a careful dermatology information assistant inside a patient education app. "
    "You never diagnose and never prescribe. Write in plain, calm language for the public. "
    "Always respond with valid JSON only, matching the requested schema exactly."
)


class KnowledgeBaseProvider:
    source = "knowledge_base"

    def describe(self, label: str, body_area: str, symptoms: str) -> ConditionInfo:
        info = load_conditions().get(label)
        if info is None:
            return ConditionInfo(
                name=display_name(label),
                overview="No curated information is available for this condition yet.",
                when_to_see_doctor="Consult a dermatologist for an assessment.",
            )
        return ConditionInfo(
            name=info["display_name"],
            overview=info["overview"],
            symptoms=info["symptoms"],
            precautions=info["precautions"],
            when_to_see_doctor=info["when_to_see_doctor"],
        )

    def medicines(self, label: str, description: ConditionInfo, region: str) -> list[MedicineSuggestion]:
        info = load_conditions().get(label, {})
        return [MedicineSuggestion(**m) for m in info.get("medicines", [])]


class OpenAICompatibleProvider:
    source = "llm"

    def __init__(self, base_url: str, api_key: str, model: str, fallback_models: list[str] | None = None):
        from openai import OpenAI

        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=30, max_retries=0)
        self.models = [model, *(fallback_models or [])]
        self.extra_body = _no_thinking(base_url) if get_settings().llm_disable_reasoning else None
        self.fallback = KnowledgeBaseProvider()

    def _ask_json(self, prompt: str) -> dict:
        # Try each configured model in order; e.g. a paid model out of credits or a rate-limited free one.
        last_error: Exception | None = None
        for model in self.models:
            try:
                resp = self.client.chat.completions.create(
                    model=model,
                    temperature=0.2,
                    response_format={"type": "json_object"},
                    extra_body=self.extra_body,
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
                )
                text = (resp.choices[0].message.content or "").strip()
                # Some models wrap JSON in a ```json fence despite response_format.
                text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                return json.loads(text or "{}")
            except Exception as e:
                log.warning("LLM model %s failed: %s", model, e)
                last_error = e
        raise last_error or RuntimeError("No LLM models configured")

    def describe(self, label: str, body_area: str, symptoms: str) -> ConditionInfo:
        name = display_name(label)
        prompt = (
            f"An image classifier suggested the skin condition: {name}.\n"
            f"Body area: {body_area or 'not specified'}. User-reported notes: {symptoms or 'none'}.\n"
            "Return JSON with keys: name (string), overview (2-3 sentences: what it is and common triggers), "
            "symptoms (list of 3-5 short strings), precautions (list of 3-5 short self-care strings), "
            "when_to_see_doctor (1 sentence including red-flag signs)."
        )
        try:
            data = self._ask_json(prompt)
            data.setdefault("name", name)
            return ConditionInfo(**data)
        except Exception:
            log.exception("LLM description failed; using knowledge base")
            return self.fallback.describe(label, body_area, symptoms)

    def medicines(self, label: str, description: ConditionInfo, region: str) -> list[MedicineSuggestion]:
        prompt = (
            f"Condition: {description.name}.\nDescription: {description.overview}\n"
            f"Region: {region}. Suggest commonly used, guideline-supported treatment options that are generally "
            "available in this region. Prefer generic names. Include over-the-counter options first.\n"
            'Return JSON: {"medicines": [{"name": str, "type": "Topical"|"Oral"|"Procedure", '
            '"usage_note": str (general, no exact dosing schedule), "prescription_required": bool, '
            '"caution": str}]} with 2-4 items.'
        )
        try:
            data = self._ask_json(prompt)
            items = [MedicineSuggestion(**m) for m in data.get("medicines", [])][:4]
            return items or self.fallback.medicines(label, description, region)
        except Exception:
            log.exception("LLM medicine suggestion failed; using knowledge base")
            return self.fallback.medicines(label, description, region)


def _no_thinking(base_url: str) -> dict | None:
    """Turn off "thinking" for reasoning models (e.g. Qwen 3): same answers here, ~8x faster and far fewer tokens."""
    if "openrouter.ai" in base_url:
        return {"reasoning": {"enabled": False}}
    if "aliyuncs.com" in base_url:  # Alibaba Model Studio / DashScope
        return {"enable_thinking": False}
    return None


@lru_cache
def get_text_provider():
    s = get_settings()
    if s.llm_api_key:
        fallbacks = [m.strip() for m in s.llm_fallback_models.split(",") if m.strip()]
        return OpenAICompatibleProvider(s.llm_base_url, s.llm_api_key, s.llm_model, fallbacks)
    return KnowledgeBaseProvider()
