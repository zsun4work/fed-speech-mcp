"""Importance scoring for Fed speeches."""

from ..models import (
    DocType,
    Features,
    Importance,
    ImportanceTier,
    Speaker,
    SpeakerRole,
)


class ImportanceScorer:
    """Rule-based importance scoring for market relevance.

    Scoring rules (from V1 spec):

    Base tier by role:
    - Chair or Vice Chair: high
    - Governor: medium

    Adjustments:
    - Testimony: +1 tier
    - Has Q&A: +1 tier
    - Mentions rates AND (inflation OR labor market): +1 tier
    - Word count < 300: -1 tier

    Output:
    - importance.tier: high | medium | low
    - importance.score: normalized numeric score (0–1)
    - importance.reasons: list of explanatory strings
    """

    # Tier numeric values for calculations
    TIER_VALUES = {
        ImportanceTier.LOW: 0,
        ImportanceTier.MEDIUM: 1,
        ImportanceTier.HIGH: 2,
    }

    # Reverse mapping from value to tier
    VALUE_TO_TIER = {
        0: ImportanceTier.LOW,
        1: ImportanceTier.MEDIUM,
        2: ImportanceTier.HIGH,
    }

    def score(
        self,
        speaker: Speaker,
        doc_type: DocType,
        features: Features,
    ) -> Importance:
        """Calculate importance score for a speech.

        Args:
            speaker: Speaker information.
            doc_type: Document type.
            features: Extracted features.

        Returns:
            Importance object with tier, score, and reasons.
        """
        reasons = []
        adjustments = 0

        # Base tier by role
        if speaker.role in (SpeakerRole.CHAIR, SpeakerRole.VICE_CHAIR):
            base_tier = ImportanceTier.HIGH
            reasons.append(f"Speaker is {speaker.role.value} ({speaker.name})")
        else:
            base_tier = ImportanceTier.MEDIUM
            reasons.append(f"Speaker is {speaker.role.value} ({speaker.name})")

        base_value = self.TIER_VALUES[base_tier]

        # Testimony adjustment (+1)
        if doc_type == DocType.TESTIMONY:
            adjustments += 1
            reasons.append("Congressional testimony (high market attention)")

        # Q&A adjustment (+1)
        if features.has_qa:
            adjustments += 1
            reasons.append("Contains Q&A section (unscripted remarks)")

        # Topic-based adjustment (+1)
        topics = features.topics
        if topics.rates and (topics.inflation or topics.labor_market):
            adjustments += 1
            topic_context = []
            if topics.inflation:
                topic_context.append("inflation")
            if topics.labor_market:
                topic_context.append("labor market")
            reasons.append(
                f"Discusses rates in context of {' and '.join(topic_context)}"
            )

        # Low word count adjustment (-1)
        if features.word_count < 300:
            adjustments -= 1
            reasons.append(f"Short document ({features.word_count} words)")

        # Calculate final tier value (clamped to 0-2)
        final_value = max(0, min(2, base_value + adjustments))
        final_tier = self.VALUE_TO_TIER[final_value]

        # Calculate normalized score (0-1)
        # We use a slightly more nuanced calculation that considers
        # the number of positive factors
        positive_factors = sum(
            [
                speaker.role in (SpeakerRole.CHAIR, SpeakerRole.VICE_CHAIR),
                doc_type == DocType.TESTIMONY,
                features.has_qa,
                topics.rates and (topics.inflation or topics.labor_market),
            ]
        )
        negative_factors = sum([features.word_count < 300])

        # Score formula: base 0.33 per tier + 0.05 per positive factor
        score = (final_value * 0.33) + (positive_factors * 0.05) - (negative_factors * 0.05)
        score = round(max(0.0, min(1.0, score)), 2)

        return Importance(
            tier=final_tier,
            score=score,
            reasons=reasons,
        )

    def explain_score(self, importance: Importance) -> str:
        """Generate human-readable explanation of importance score.

        Args:
            importance: The importance object to explain.

        Returns:
            Formatted explanation string.
        """
        lines = [
            f"Importance: {importance.tier.value.upper()} (score: {importance.score:.2f})",
            "",
            "Factors:",
        ]

        for reason in importance.reasons:
            lines.append(f"  • {reason}")

        return "\n".join(lines)

