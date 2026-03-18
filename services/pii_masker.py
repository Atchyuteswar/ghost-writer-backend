"""Ghost-Writer Backend — PII Masker Service.

Uses Presidio to detect and mask PII in messages.
"""
import logging
from typing import Tuple

from models.schemas import ParsedMessage, PIISettings

logger = logging.getLogger(__name__)

# Lazy-loaded engines (initialized once on first use)
_analyzer_engine = None
_anonymizer_engine = None
_presidio_available = False


def _init_presidio():
    """Initialize Presidio engines once."""
    global _analyzer_engine, _anonymizer_engine, _presidio_available
    if _analyzer_engine is not None:
        return

    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine
        from presidio_anonymizer.entities import OperatorConfig

        _analyzer_engine = AnalyzerEngine()
        _anonymizer_engine = AnonymizerEngine()
        _presidio_available = True
        logger.info("Presidio engines initialized successfully")
    except Exception as e:
        logger.warning(f"Presidio not available: {e}. PII masking will use regex fallback.")
        _presidio_available = False


class PIIMasker:
    """Detects and masks PII in parsed messages."""

    def __init__(self):
        _init_presidio()

    @property
    def is_available(self) -> bool:
        return _presidio_available

    def mask(
        self,
        messages: list[ParsedMessage],
        settings: PIISettings,
    ) -> Tuple[list[ParsedMessage], int, dict[str, int]]:
        """Mask PII in messages based on settings.

        Returns: (masked_messages, total_masked_count, mask_breakdown)
        """
        # Build active entity types
        active_entities: list[str] = []
        if settings.mask_phone_numbers:
            active_entities.append("PHONE_NUMBER")
        if settings.mask_email_addresses:
            active_entities.append("EMAIL_ADDRESS")
        if settings.mask_real_names:
            active_entities.append("PERSON")
        if settings.mask_locations:
            active_entities.extend(["LOCATION", "GPE"])
        if settings.mask_financial_info:
            active_entities.extend(["MONEY", "CREDIT_CARD"])

        if not active_entities:
            return messages, 0, {}

        masked_messages: list[ParsedMessage] = []
        total_masked = 0
        breakdown: dict[str, int] = {}

        # Replacement map
        replacements = {
            "PHONE_NUMBER": "[PHONE]",
            "EMAIL_ADDRESS": "[EMAIL]",
            "PERSON": "[NAME]",
            "LOCATION": "[LOCATION]",
            "GPE": "[LOCATION]",
            "MONEY": "[FINANCIAL]",
            "CREDIT_CARD": "[FINANCIAL]",
        }

        for msg in messages:
            if _presidio_available and _analyzer_engine and _anonymizer_engine:
                try:
                    from presidio_anonymizer.entities import OperatorConfig

                    results = _analyzer_engine.analyze(
                        text=msg.text,
                        entities=active_entities,
                        language="en",
                    )

                    if results:
                        operators = {}
                        for entity_type, replacement in replacements.items():
                            if entity_type in active_entities:
                                operators[entity_type] = OperatorConfig(
                                    "replace", {"new_value": replacement}
                                )

                        anonymized = _anonymizer_engine.anonymize(
                            text=msg.text,
                            analyzer_results=results,
                            operators=operators,
                        )

                        for r in results:
                            entity = r.entity_type
                            breakdown[entity] = breakdown.get(entity, 0) + 1
                            total_masked += 1

                        masked_messages.append(msg.model_copy(update={
                            "text": anonymized.text,
                            "char_count": len(anonymized.text),
                        }))
                        continue
                except Exception as e:
                    logger.warning(f"Presidio masking failed for message: {e}")

            # Fallback: use regex-based masking
            masked_text = self._regex_mask(msg.text, settings, breakdown)
            if masked_text != msg.text:
                total_masked += 1
            masked_messages.append(msg.model_copy(update={
                "text": masked_text,
                "char_count": len(masked_text),
            }))

        return masked_messages, total_masked, breakdown

    def _regex_mask(self, text: str, settings: PIISettings, breakdown: dict[str, int]) -> str:
        """Simple regex fallback for PII masking."""
        import re
        result = text

        if settings.mask_phone_numbers:
            phone_pattern = r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
            matches = re.findall(phone_pattern, result)
            if matches:
                breakdown["PHONE_NUMBER"] = breakdown.get("PHONE_NUMBER", 0) + len(matches)
                result = re.sub(phone_pattern, "[PHONE]", result)

        if settings.mask_email_addresses:
            email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
            matches = re.findall(email_pattern, result)
            if matches:
                breakdown["EMAIL_ADDRESS"] = breakdown.get("EMAIL_ADDRESS", 0) + len(matches)
                result = re.sub(email_pattern, "[EMAIL]", result)

        return result
