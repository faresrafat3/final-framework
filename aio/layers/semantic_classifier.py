from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from ..config.models import SemanticClassifierConfig
from .observability import ObservabilityLayer
from ..state import AIOState


def _load_prompts_from_dir(prompt_dir: str) -> Dict[str, str]:
    """Load all .txt files from a directory into a dict keyed by filename stem."""
    prompts: Dict[str, str] = {}
    if not os.path.isdir(prompt_dir):
        return prompts
    for fname in sorted(os.listdir(prompt_dir)):
        if fname.endswith(".txt"):
            path = os.path.join(prompt_dir, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    prompts[fname[:-4]] = f.read()
            except Exception:
                pass
    return prompts


class SemanticClassifier:
    """Layer-8 safety classifier with LLM + regex fallback.

    Loads prompt templates from ``prompts/safety/*.txt`` and uses them
    to guide LLM-based classification when available. Falls back to
    deterministic regex patterns when the LLM is unavailable or disabled.
    """

    def __init__(self, config: SemanticClassifierConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._prompts = _load_prompts_from_dir(config.prompt_dir)
        self._patterns: List[Dict[str, Any]] = []
        self._load_regex_patterns()
        self._llm: Optional[Any] = None
        if config.enable_llm and self._prompts:
            self._llm = self._init_llm()

    def _load_regex_patterns(self) -> None:
        defaults = [
            {"name": "harm", "pattern": r"\b(kill|harm|attack|destroy)\b", "severity": "high"},
            {"name": "pii", "pattern": r"\b(ssn|password|secret_key|api_key)\b", "severity": "high"},
            {"name": "system_integrity", "pattern": r"(rm -rf /|mkfs|fdisk|drop table|delete from)", "severity": "critical"},
            {"name": "jailbreak", "pattern": r"(override|ignore previous)", "severity": "medium"},
        ]
        for p in defaults:
            self._patterns.append(p)
        if self.config.custom_patterns_json:
            try:
                import json
                data = json.loads(self.config.custom_patterns_json)
                for item in data:
                    self._patterns.append({
                        "name": item.get("name", "custom"),
                        "pattern": item.get("pattern", ".*"),
                        "severity": item.get("severity", "medium"),
                    })
            except Exception as exc:
                self.obs.log(logging.WARNING, f"SemanticClassifier: failed to load custom patterns: {exc}")

    def _init_llm(self) -> Optional[Any]:
        from ..config.deps import LANGCHAIN_CHAT_AVAILABLE

        if not LANGCHAIN_CHAT_AVAILABLE:
            return None
        try:
            from langchain_openai import ChatOpenAI
        except Exception:
            ChatOpenAI = None  # type: ignore[misc,assignment]
        try:
            from langchain_anthropic import ChatAnthropic
        except Exception:
            ChatAnthropic = None  # type: ignore[misc,assignment]

        provider = self.config.llm_provider
        if provider == "openai" and ChatOpenAI is not None:
            key = os.getenv("OPENAI_API_KEY")
            if key:
                return ChatOpenAI(
                    model=self.config.llm_model,
                    temperature=self.config.llm_temperature,
                    max_tokens=self.config.llm_max_tokens,
                    api_key=key,
                )
        elif provider == "anthropic" and ChatAnthropic is not None:
            key = os.getenv("ANTHROPIC_API_KEY")
            if key:
                return ChatAnthropic(
                    model=self.config.llm_model,
                    temperature=self.config.llm_temperature,
                    max_tokens=self.config.llm_max_tokens,
                    api_key=key,
                )
        return None

    def _call_llm(self, prompt: str) -> str:
        if self._llm is None:
            raise RuntimeError("LLM not available")
        response = self._llm.invoke(prompt)
        return str(response.content if hasattr(response, "content") else response)

    def classify(self, text: str) -> Dict[str, Any]:
        """Classify text for safety violations.

        Returns a dict with ``violations`` (list), ``llm_used`` (bool),
        and ``overall_risk`` (str).
        """
        start = time.time()
        with self.obs.start_span("semantic_classifier.classify"):
            llm_used = False
            violations: List[Dict[str, Any]] = []

            if self._llm is not None and self.config.enable_llm:
                try:
                    prompt = self._build_llm_prompt(text)
                    raw = self._call_llm(prompt)
                    llm_violations = self._parse_llm_response(raw)
                    violations.extend(llm_violations)
                    llm_used = True
                except Exception as exc:
                    self.obs.log(logging.WARNING, f"SemanticClassifier LLM call failed: {exc}")

            # Regex fallback always runs to catch anything the LLM missed
            regex_violations = self._regex_scan(text)
            # Merge by name
            seen = {v["name"] for v in violations}
            for v in regex_violations:
                if v["name"] not in seen:
                    violations.append(v)

            overall_risk = self._compute_risk(violations)
            self.obs.record_latency("semantic_classifier.classify", time.time() - start)
            self.obs.count_node("semantic_classifier.classify", overall_risk)
            return {
                "violations": violations,
                "llm_used": llm_used,
                "overall_risk": overall_risk,
            }

    def _build_llm_prompt(self, text: str) -> str:
        base = self._prompts.get("classifier", "")
        if base:
            return f"{base}\n\nText to classify:\n{text}\n\nRespond with JSON: {{'violations': [{{'name': str, 'severity': str, 'reason': str}}]}}"
        return (
            "Classify the following text for safety violations. "
            "Respond with JSON: {'violations': [{'name': str, 'severity': str, 'reason': str}]}\n\n"
            f"Text: {text}"
        )

    def _parse_llm_response(self, raw: str) -> List[Dict[str, Any]]:
        import json
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return data.get("violations", [])
        except Exception:
            pass
        return []

    def _regex_scan(self, text: str) -> List[Dict[str, Any]]:
        violations = []
        lowered = text.lower()
        for p in self._patterns:
            if re.search(p["pattern"], lowered):
                violations.append({
                    "name": p["name"],
                    "severity": p["severity"],
                    "source": "regex",
                })
        return violations

    def _compute_risk(self, violations: List[Dict[str, Any]]) -> str:
        if not violations:
            return "low"
        severities = [v.get("severity", "medium") for v in violations]
        if "critical" in severities:
            return "critical"
        if "high" in severities:
            return "high"
        if "medium" in severities:
            return "medium"
        return "low"

    def classify_state(self, state: AIOState) -> AIOState:
        """Run classification on the combined raw_input + plan and write results to state."""
        raw = state.get("raw_input", "") or ""
        plan = state.get("plan", "") or ""
        combined = f"{raw} {plan}".strip()
        result = self.classify(combined)
        state["semantic_classification"] = result
        if result["overall_risk"] in ("high", "critical"):
            state["safety_violations"] = state.get("safety_violations", []) + result["violations"]
            state["failure_state"] = "FAILED"
            state["error"] = f"SemanticClassifier blocked: {result['overall_risk']} risk detected."
        return state
