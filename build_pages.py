import json
import re

try:
    from .config.query_types import queryTypes
    from .config.site import SITE_CONFIG
    from .utils.strings import (
        compactText,
        dedupe,
        formatLocation,
        toSentence,
    )
except ImportError:
    from pygen.config.query_types import queryTypes
    from pygen.config.site import SITE_CONFIG
    from pygen.utils.strings import (
        compactText,
        dedupe,
        formatLocation,
        toSentence,
    )


def buildPenaltyAnswer(penalties):
    parts = []

    if compactText(penalties["fine"]) and compactText(penalties["fine"]) != "Not specified":
        parts.append(compactText(penalties["fine"]))

    if compactText(penalties["jail"]) and compactText(penalties["jail"]) != "Not specified":
        parts.append(compactText(penalties["jail"]))

    if compactText(penalties["notes"]):
        parts.append(compactText(penalties["notes"]))

    return " ".join(dedupe(parts))


def pickVariant(rule, options, salt=0):
    key = f'{rule["country"]["slug"]}:{rule["topic"]["slug"]}:{salt}'
    index = sum(ord(char) for char in key) % len(options)
    return options[index]


def buildSummaryLead(rule):
    sourceSummary = compactText(rule.get("summary_short")) or compactText(
        rule.get("summary")
    )

    if sourceSummary:
        return toSentence(sourceSummary)

    subject = rule["topic"]["gerund_phrase"]
    location = formatLocation(rule["location"])

    if rule["verdict"] == "Yes":
        return f"{subject.capitalize()} is generally legal in {location}."

    if rule["verdict"] == "No":
        return f"{subject.capitalize()} is generally illegal in {location}."

    return f"The legality of {subject} in {location} depends on the circumstances."


def buildVerdictExplainer(rule):
    if rule["verdict"] == "Yes":
        return "The baseline answer looks permissive, but misuse, transport, import, and public-use rules can still narrow what is allowed."

    if rule["verdict"] == "No":
        return "The safest reading is prohibition unless you can point to a narrow and documented exemption that fits your exact situation."

    return "The answer flips on context, permits, labels, or how authorities classify the conduct, so the headline verdict is only the start of the analysis."


def buildConfidence(rule):
    score = 34

    score += min(len(rule["sources"]), 4) * 7
    score += min(len(rule["conditions"]), 3) * 4
    score += min(len(rule["exceptions"]), 2) * 3

    if rule["penalties"]["jail"] != "Not specified":
        score += 8

    if rule["penalties"]["fine"] != "Not specified":
        score += 5

    if rule["verdict"] == "Depends":
        score -= 10

    score = max(20, min(score, 82))

    if score >= 64:
        return {
            "score": score,
            "label": "Moderate confidence",
            "slug": "moderate",
            "note": "This page has a useful source trail and multiple structured signals, but it should still be checked against primary law before high-stakes reliance.",
        }

    if score >= 48:
        return {
            "score": score,
            "label": "Working answer",
            "slug": "working",
            "note": "This page is strong enough for triage and comparison, but you should verify the listed sources before acting on it.",
        }

    return {
        "score": score,
        "label": "Use extra caution",
        "slug": "caution",
        "note": "This page is still useful for orientation, but the answer needs careful verification before any purchase, travel, or self-defence decision.",
    }


def buildRiskProfile(rule):
    score = 22

    if rule["verdict"] == "No":
        score += 48
    elif rule["verdict"] == "Depends":
        score += 26

    if rule["penalties"]["jail"] != "Not specified":
        score += 18

    if rule["penalties"]["fine"] != "Not specified":
        score += 10

    if re.search(r"confiscation|criminal|prohibited|firearm|charges", rule["penalties"]["notes"], re.IGNORECASE):
        score += 8

    score = max(8, min(score, 96))

    if score >= 78:
        return {
            "score": score,
            "label": "High risk",
            "tone": "Treat this as a rule where mistakes can carry real consequences.",
            "slug": "high",
        }

    if score >= 48:
        return {
            "score": score,
            "label": "Guarded",
            "tone": "The answer turns on conditions, documentation, or context.",
            "slug": "guarded",
        }

    return {
        "score": score,
        "label": "Low risk",
        "tone": "The rule looks more permissive, but the details still matter.",
        "slug": "low",
    }


def buildFreshnessNote(rule):
    return toSentence(
        f'Last refreshed on {rule["last_updated"]} from the current structured source set. Verify the source trail before relying on the answer for travel, purchase, self-defence, or enforcement-sensitive decisions'
    )


def buildMemoryHook(rule):
    if rule["verdict"] == "Yes":
        return 'If you remember one thing, "legal" does not mean unrestricted. Stay inside the listed conditions and treat misuse or transport edge cases seriously.'

    if rule["verdict"] == "No":
        return f'If you remember one thing, treat {rule["topic"]["gerund_phrase"]} as prohibited in {formatLocation(rule["location"])} unless a narrow and documented exception clearly applies.'

    return "If you remember one thing, the outcome can flip on one missing detail such as the permit status, labelling, purpose, or context of use."


def buildSummaryPoints(verdictExplainer, confidence, risk, freshnessNote):
    return dedupe(
        [
            verdictExplainer,
            confidence["note"],
            risk["tone"],
            freshnessNote,
        ]
    )[:4]


def buildComplianceChecklist(rule):
    checks = []

    if rule["verify_next"]:
        return dedupe(rule["verify_next"])[:5]

    for item in dedupe(rule["conditions"][:2]):
        checks.append(item)

    if len(rule["exceptions"]) > 0:
        checks.append("Check whether any listed exception really applies to your exact facts before you act.")

    if compactText(rule["enforcement"]):
        checks.append(
            "Verify how the rule is enforced locally, especially if practice varies by state, province, or region."
        )

    if (
        compactText(rule["penalties"]["fine"]) != "Not specified"
        or compactText(rule["penalties"]["jail"]) != "Not specified"
        or compactText(rule["penalties"]["notes"])
        != "See source material for penalty detail."
    ):
        checks.append(
            "Confirm the current penalty range and record consequences with a primary source if the stakes are high."
        )

    checks.append(
        "Review the cited source trail before relying on the answer for travel, purchase, work, or public use."
    )

    return dedupe(checks)[:5]


def buildDecisionSteps(rule, confidence):
    steps = []

    if rule["verdict"] == "No":
        steps.append("Start from prohibition, not from edge-case exceptions.")
    elif rule["verdict"] == "Depends":
        steps.append("Define the exact scenario first, because a small detail can change the result.")
    else:
        steps.append("Start from the permissive baseline, then test the limits before acting.")

    if len(rule["conditions"]) > 0 and rule["conditions"][0]:
        steps.append(compactText(rule["conditions"][0]))

    if len(rule["exceptions"]) > 0 and rule["exceptions"][0]:
        steps.append(compactText(rule["exceptions"][0]))

    steps.append(buildPenaltyAnswer(rule["penalties"]))
    steps.append(confidence["note"])

    return dedupe(steps)[:5]


def buildPracticalTakeaways(rule, freshnessNote):
    if rule["verify_next"]:
        return dedupe(rule["verify_next"])[:4]

    items = []

    if len(rule["conditions"]) > 1:
        items.append(compactText(rule["conditions"][1]))
    elif len(rule["conditions"]) > 0:
        items.append(compactText(rule["conditions"][0]))

    if len(rule["exceptions"]) > 0:
        items.append(
            f'Check whether this exception applies to your exact situation: {compactText(rule["exceptions"][0])}'
        )

    if compactText(rule["enforcement"]):
        items.append("Look at local enforcement practice, not just the statutory wording.")

    if compactText(buildPenaltyAnswer(rule["penalties"])):
        items.append("Double-check the penalties before assuming a mistake would be minor.")

    items.append(freshnessNote)

    return dedupe(items)[:4]


def buildDirectAnswer(rule):
    subject = rule["topic"]["gerund_phrase"]
    location = formatLocation(rule["location"])

    if rule["verdict"] == "Yes":
        return f"Yes. {subject.capitalize()} is generally legal in {location}, although specific conditions or restrictions may still apply."

    if rule["verdict"] == "No":
        return f"No. {subject.capitalize()} is generally illegal in {location}, unless a narrow exception or legal justification clearly applies."

    return f"Depends. In {location}, {subject} may be legal depending on the circumstances, purpose, or local restrictions."


def buildPageTitle(page):
    year = page["last_updated"][:4]
    location = formatLocation(page["location"])
    topicLabel = page["topic"]["label"]
    titleOptions = {
        "legal": [
            f'{page["query"]} | {SITE_CONFIG["siteName"]}',
            f'{topicLabel} legality in {location} explained ({year}) | {SITE_CONFIG["siteName"]}',
        ],
        "can-i": [
            f'{page["query"]} | {SITE_CONFIG["siteName"]}',
            f'Can I {page["topic"]["action_label"]} in {location}? {year} guide | {SITE_CONFIG["siteName"]}',
        ],
        "consequences": [
            f'{page["query"]} ({year} penalties) | {SITE_CONFIG["siteName"]}',
            f'{topicLabel} penalties in {location} explained ({year}) | {SITE_CONFIG["siteName"]}',
        ],
        "requirements": [
            f'{page["query"]} ({year} rules) | {SITE_CONFIG["siteName"]}',
            f'{topicLabel} rules and paperwork in {location} ({year}) | {SITE_CONFIG["siteName"]}',
        ],
    }

    return pickVariant(page, titleOptions.get(page["query_type"]) or [page["query"]], 11)


def buildFaq(page):
    location = formatLocation(page["location"])
    sections = page.get("sections") or {}

    return [
        {
            "question": page["query"],
            "answer": page["direct_answer"],
        },
        {
            "question": f'What conditions matter for {page["topic"]["gerund_phrase"]} in {location}?',
            "answer": " ".join((sections.get("conditions") or page["conditions"])[:3]),
        },
        {
            "question": f'Are there exceptions for {page["topic"]["gerund_phrase"]} in {location}?',
            "answer": " ".join(sections.get("exceptions") or page["exceptions"])
            or "No explicit exceptions were captured in the current structured dataset.",
        },
        {
            "question": f'What are the penalties for {page["topic"]["gerund_phrase"]} in {location}?',
            "answer": (sections.get("penalties") or {}).get("summary")
            or buildPenaltyAnswer(page["penalties"])
            or "No explicit penalty summary was captured in the current structured dataset.",
        },
        {
            "question": f'How is {page["topic"]["gerund_phrase"]} enforced in {location}?',
            "answer": sections.get("enforcement")
            or page["enforcement"]
            or "No explicit enforcement note was captured in the current structured dataset.",
        },
        {
            "question": f'What should I verify next about {page["topic"]["gerund_phrase"]} in {location}?',
            "answer": " ".join(sections.get("verify_next") or page["practical_takeaways"])
            or "Use the source trail before relying on this rule.",
        },
    ]


def expandRulesToPages(rules):
    output = []

    for rule in rules:
        summaryLead = buildSummaryLead(rule)
        verdictExplainer = buildVerdictExplainer(rule)
        confidence = buildConfidence(rule)
        risk = buildRiskProfile(rule)
        freshnessNote = buildFreshnessNote(rule)
        memoryHook = buildMemoryHook(rule)
        penaltyLead = buildPenaltyAnswer(rule["penalties"])
        summaryPoints = buildSummaryPoints(
            verdictExplainer,
            confidence,
            risk,
            freshnessNote,
        )
        complianceChecklist = buildComplianceChecklist(rule)
        practicalTakeaways = buildPracticalTakeaways(rule, freshnessNote)
        decisionSteps = buildDecisionSteps(rule, confidence)
        structuredVerifyNext = dedupe(rule["verify_next"])[:4]

        for queryType in queryTypes:
            query = queryType["buildQuery"](rule)
            summary = queryType["buildSummary"](
                rule,
                {
                    "summaryLead": summaryLead,
                    "verdictExplainer": verdictExplainer,
                    "confidence": confidence,
                    "risk": risk,
                    "freshnessNote": freshnessNote,
                    "memoryHook": memoryHook,
                    "penaltyLead": penaltyLead,
                },
            )
            canonicalPath = f'/{rule["country"]["slug"]}/{queryType["slug"]}/{rule["topic"]["slug"]}/'

            page = {
                **rule,
                "source_id": rule["id"],
                "query": query,
                "query_type": queryType["slug"],
                "query_type_label": queryType["label"],
                "intent_label": queryType["intentLabel"],
                "h1": query,
                "summary": toSentence(summary),
                "summary_lead": summaryLead,
                "verdict_explainer": verdictExplainer,
                "canonical_path": canonicalPath,
                "canonical_url": f'{SITE_CONFIG["baseUrl"]}{canonicalPath}',
                "verdict_slug": rule["verdict"].lower(),
                "confidence": confidence,
                "risk": risk,
                "freshness_note": freshnessNote,
                "memory_hook": memoryHook,
                "direct_answer": buildDirectAnswer(rule),
                "summary_points": summaryPoints,
                "compliance_checklist": complianceChecklist,
                "decision_steps": decisionSteps,
                "practical_takeaways": practicalTakeaways,
                "penalty_answer": penaltyLead,
                # Legality sections map from normalized rule data first, with
                # fallback only when the optional structured fields are absent.
                "sections": {
                    "summary_points": summaryPoints,
                    "conditions": rule["conditions"],
                    "exceptions": rule["exceptions"],
                    "penalties": {
                        "summary": penaltyLead,
                        "fine": compactText(rule["penalties"]["fine"]),
                        "jail": compactText(rule["penalties"]["jail"]),
                        "notes": compactText(rule["penalties"]["notes"]),
                    },
                    "enforcement": compactText(rule["enforcement"]),
                    "verify_next": structuredVerifyNext or practicalTakeaways,
                },
            }

            page["title"] = buildPageTitle(page)
            page["meta_description"] = compactText(queryType["buildMetaDescription"](page))
            page["faq"] = [
                json.loads(item)
                for item in dedupe(
                    [
                        json.dumps(item, ensure_ascii=False, separators=(",", ":"))
                        for item in buildFaq(page)
                    ]
                )
            ]

            output.append(page)

    return output
