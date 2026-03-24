try:
    from ..utils.strings import (
        compactText,
        formatLocation,
        limitText,
        toSentence,
    )
except ImportError:
    from pygen.utils.strings import (
        compactText,
        formatLocation,
        limitText,
        toSentence,
    )


def buildPenaltyParts(penalties):
    parts = []

    if compactText(penalties["fine"]) and compactText(penalties["fine"]) != "Not specified":
        parts.append(compactText(penalties["fine"]))

    if compactText(penalties["jail"]) and compactText(penalties["jail"]) != "Not specified":
        parts.append(compactText(penalties["jail"]))

    if compactText(penalties["notes"]) and compactText(penalties["notes"]) != "See source material for penalty detail.":
        parts.append(compactText(penalties["notes"]))

    return parts


def buildMetaDescription(page, closing):
    statusLine = {
        "Yes": "Generally legal",
        "No": "Generally illegal",
        "Depends": "Legality depends on the circumstances",
    }.get(page["verdict"], "Legal status explained")
    intro = {
        "legal": f'{statusLine} in {page["country"]["name"]}.',
        "can-i": f'{statusLine} if you are deciding whether you can act in {page["country"]["name"]}.',
        "consequences": f'{statusLine} in {page["country"]["name"]}, with consequences if you get it wrong.',
        "requirements": f'{statusLine} in {page["country"]["name"]}, subject to local rules or paperwork.',
    }.get(page["query_type"], f'{statusLine} in {page["country"]["name"]}.')
    return limitText(
        f'{intro} This guide explains {page["topic"]["label"].lower()} in {page["country"]["name"]}, including {closing}.',
        160,
    )


QUERY_TYPES = {
    "legal": {
        "slug": "legal",
        "label": "Legal",
        "intentLabel": "is-it-legal",
        "buildQuery": lambda rule: f'Is it legal to {rule["topic"]["action_label"]} in {formatLocation(rule["location"])}?',
        "buildSummary": lambda _rule, derived: toSentence(
            f'{derived["summaryLead"]} Review the conditions, exceptions, penalties, and enforcement notes below before relying on the headline answer.'
        ),
        "buildMetaDescription": lambda page: buildMetaDescription(
            page, "the key conditions, exceptions, and enforcement points"
        ),
    },
    "can-i": {
        "slug": "can-i",
        "label": "Can I",
        "intentLabel": "can-i",
        "buildQuery": lambda rule: f'Can I {rule["topic"]["action_label"]} in {formatLocation(rule["location"])}?',
        "buildSummary": lambda _rule, derived: toSentence(
            f'{derived["summaryLead"]} Use the conditions and exceptions below to check whether your exact situation still fits the rule.'
        ),
        "buildMetaDescription": lambda page: buildMetaDescription(
            page, "the practical conditions, exceptions, and next checks"
        ),
    },
    "consequences": {
        "slug": "consequences",
        "label": "Consequences",
        "intentLabel": "what-happens-if",
        "buildQuery": lambda rule: f'What happens if I {rule["topic"]["action_label"]} in {formatLocation(rule["location"])}?',
        "buildSummary": lambda _rule, derived: toSentence(
            f'{derived["summaryLead"]} Use the penalties and enforcement notes below to judge the practical downside of getting this wrong.'
        ),
        "buildMetaDescription": lambda page: buildMetaDescription(
            page, "the likely penalties, enforcement approach, and key exceptions"
        ),
    },
    "requirements": {
        "slug": "requirements",
        "label": "Requirements",
        "intentLabel": "do-i-need",
        "buildQuery": lambda rule: f'What rules or paperwork do I need to {rule["topic"]["action_label"]} in {formatLocation(rule["location"])}?',
        "buildSummary": lambda _rule, derived: toSentence(
            f'{derived["summaryLead"]} Use the conditions below to confirm which compliance steps, paperwork, or proof matter before you act.'
        ),
        "buildMetaDescription": lambda page: buildMetaDescription(
            page, "the permissions, paperwork, and compliance checks that matter"
        ),
    },
}

queryTypes = list(QUERY_TYPES.values())
