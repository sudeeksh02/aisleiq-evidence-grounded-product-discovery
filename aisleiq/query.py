from __future__ import annotations

import re

from aisleiq.models import Intent

ALIASES = {
    "battery": ("battery", "battery life", "backup"),
    "camera": ("camera", "photography", "photos"),
    "display": ("display", "screen", "amoled", "resolution"),
    "performance": ("performance", "fast", "processor", "gaming", "ram"),
    "thermals": ("thermal", "thermals", "heating", "overheating", "cooling"),
    "build_quality": ("build quality", "durability", "sturdy", "long lasting"),
    "value": ("value for money", "affordable", "budget", "worth"),
    "sound": ("sound", "audio", "speaker"),
}
CATEGORIES = {
    "laptop": ("laptop", "notebook", "gaming pc"),
    "mobile": ("phone", "mobile", "smartphone", "iphone"),
    "headphones": ("headphone", "earphone", "earbud", "headset"),
    "television": ("television", "tv"),
    "washing_machine": ("washing machine", "washer"),
    "camera": ("camera", "dslr", "mirrorless"),
}


def parse_intent(query: str, category: str | None = None) -> Intent:
    text = query.lower()
    money = re.search(
        r"(?:under|below|less than|max(?:imum)?(?: budget)?|upto|up to|within)\s*"
        r"(?:₹|rs\.?\s*)?([\d,]+(?:\.\d+)?)\s*(k|thousand|l|lakh)?",
        text,
    )
    minimum = re.search(
        r"(?:above|over|more than|at least|minimum)\s*(?:₹|rs\.?\s*)?"
        r"([\d,]+(?:\.\d+)?)\s*(k|thousand|l|lakh)?",
        text,
    )

    def amount(match: re.Match[str] | None) -> float | None:
        if not match:
            return None
        value = float(match.group(1).replace(",", ""))
        unit = (match.group(2) or "").lower()
        return value * (
            1000 if unit in {"k", "thousand"} else 100000 if unit in {"l", "lakh"} else 1
        )

    detected_category = category.lower() if category else None
    if not detected_category:
        detected_category = next(
            (name for name, terms in CATEGORIES.items() if any(t in text for t in terms)), None
        )
    use_case = "gaming" if "gaming" in text else None
    positives: list[str] = []
    negatives: list[str] = []
    for aspect, terms in ALIASES.items():
        term = next((term for term in terms if term in text), None)
        if not term:
            continue
        index = text.find(term)
        window = text[max(0, index - 24) : index]
        trailing = text[index + len(term) : index + len(term) + 20]
        negated = re.search(r"\b(no|not|without|avoid)\b", window) or re.match(
            r"\s*(is|are)?\s*(not|without)\b", trailing
        )
        (negatives if negated else positives).append(aspect)
    hard = [
        a
        for a in positives
        if re.search(
            rf"\b(need|must|required|prioriti[sz]e)\b.*{re.escape(a.replace('_', ' '))}", text
        )
    ]
    preferred = [a for a in positives if a not in hard]
    return Intent(
        raw_query=query,
        category=detected_category,
        use_case=use_case,
        max_price=amount(money),
        min_price=amount(minimum),
        required_attributes=hard,
        preferred_attributes=preferred,
        negated_attributes=negatives,
    )
