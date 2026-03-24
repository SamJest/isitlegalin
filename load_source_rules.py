import csv
import os
import re
from datetime import datetime, timezone

try:
    from .config.site import RULES_DIR
    from .utils.fs import readJson, walkFiles
    from .utils.strings import (
        addIndefiniteArticle,
        compactText,
        dedupe,
        normalizeActionPhrase,
        normalizeDate,
        titleCase,
        slugify,
        toGerundPhrase,
        toSentence,
    )
except ImportError:
    from pygen.config.site import RULES_DIR
    from pygen.utils.fs import readJson, walkFiles
    from pygen.utils.strings import (
        addIndefiniteArticle,
        compactText,
        dedupe,
        normalizeActionPhrase,
        normalizeDate,
        titleCase,
        slugify,
        toGerundPhrase,
        toSentence,
    )


VALID_VERDICTS = {"Yes", "No", "Depends"}
PLACEHOLDER_PATTERN = re.compile(r"^(none|n/a|not specified)\.?$", re.IGNORECASE)
BATCHES_DIR = os.path.join(os.path.dirname(__file__), "data", "batches")
COUNTRIES_CSV = os.path.join(os.path.dirname(__file__), "data", "countries.csv")


def asList(value):
    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        return list(value)

    return [value]


def hasField(payload, key):
    return isinstance(payload, dict) and key in payload


def cleanNarrativeText(value):
    text = compactText(value)

    if not text or PLACEHOLDER_PATTERN.search(text):
        return ""

    return re.sub(r"\s+(none|n/a|not specified)\.$", "", text, flags=re.IGNORECASE).strip()


def normalizeNarrativeList(values=None, sentencify=False):
    output = []

    for value in asList(values):
        cleaned = cleanNarrativeText(value)
        if cleaned:
            output.append(toSentence(cleaned) if sentencify else cleaned)

    return dedupe(output)


def normalizePenaltyBlock(penalties=None, fieldPresent=False, sourceFile=""):
    if penalties is None:
        penalties = {}

    if not isinstance(penalties, dict):
        raise Exception(f'Invalid penalties block in {sourceFile}: expected an object')

    fine = cleanNarrativeText(penalties.get("fine"))
    jail = cleanNarrativeText(penalties.get("jail"))
    notes = cleanNarrativeText(penalties.get("notes"))

    if fieldPresent and not any([fine, jail, notes]):
        raise Exception(f'Empty structured field "penalties" in {sourceFile}')

    return {
        "fine": toSentence(fine) or "Not specified",
        "jail": toSentence(jail) or "Not specified",
        "notes": toSentence(notes) if notes else "",
    }


def validateOptionalNarrativeField(rule, key, sourceFile):
    if hasField(rule, key) and not cleanNarrativeText(rule.get(key)):
        raise Exception(f'Empty structured field "{key}" in {sourceFile}')


def validateOptionalNarrativeList(rule, key, sourceFile):
    if not hasField(rule, key):
        return

    values = asList(rule.get(key))

    if not values or not normalizeNarrativeList(values):
        raise Exception(f'Empty structured field "{key}" in {sourceFile}')


def ruleStructuredScore(rule):
    return sum(
        [
            1 if rule.get("summary") else 0,
            1 if rule.get("summary_short") else 0,
            len(rule.get("conditions") or []),
            len(rule.get("exceptions") or []),
            1 if rule.get("enforcement") else 0,
            len(rule.get("verify_next") or []),
            1 if rule["penalties"]["fine"] != "Not specified" else 0,
            1 if rule["penalties"]["jail"] != "Not specified" else 0,
            1 if rule["penalties"]["notes"] else 0,
            len(rule.get("sources") or []),
        ]
    )


def printValidationWarning(title, lines):
    if not lines:
        return

    print(f"{title}\n- " + "\n- ".join(lines))


def loadCountryIndex():
    countries = {}

    with open(COUNTRIES_CSV, "r", encoding="utf8", newline="") as file:
        for row in csv.DictReader(file):
            slug = compactText(row.get("slug"))

            if not slug:
                continue

            countries[slug] = {
                "slug": slug,
                "name": compactText(row.get("country")),
                "region": compactText(row.get("region")),
            }

    return countries


def parseDelimitedList(value):
    if isinstance(value, (list, tuple, set)):
        return dedupe(value)

    text = compactText(value)

    if not text:
        return []

    return dedupe(re.split(r"\s*[,;|]\s*", text))


def mapBatchVerdict(value, sourceFile):
    verdict = compactText(value).lower()
    mapping = {
        "yes": "Yes",
        "legal": "Yes",
        "no": "No",
        "illegal": "No",
        "depends": "Depends",
        "restricted": "Depends",
    }

    if verdict not in mapping:
        raise Exception(f'Invalid legal_status "{value}" in {sourceFile}')

    return mapping[verdict]


def buildBatchRule(row, sourceFile, countryMeta, topicCategorySlug):
    activity = compactText(row.get("activity"))
    topicSlug = slugify(activity)
    actionLabel = normalizeActionPhrase(activity)
    summary = compactText(row.get("notes"))
    conditions = parseDelimitedList(row.get("conditions"))
    exceptions = parseDelimitedList(row.get("exceptions"))
    verifyNext = parseDelimitedList(row.get("verify_next"))
    sources = parseDelimitedList(row.get("sources"))
    enforcement = compactText(row.get("enforcement"))
    penalties = {
        "fine": compactText(row.get("fine")),
        "jail": compactText(row.get("jail")),
        "notes": compactText(row.get("penalty_notes")),
    }

    if not activity or not topicSlug:
        raise Exception(f"Invalid activity value in {sourceFile}")

    rule = {
        "id": f'{countryMeta["slug"]}-{topicSlug}',
        "query": f"is {activity} legal in {countryMeta['name']}",
        "location": countryMeta["name"],
        "verdict": mapBatchVerdict(row.get("legal_status"), sourceFile),
        "last_updated": datetime.now(timezone.utc).date().isoformat(),
        "source_file": sourceFile,
        "country": countryMeta,
        "topic": {
            "slug": topicSlug,
            "label": titleCase(activity),
            "query_label": f"{activity} legal",
            "action_label": actionLabel or activity.lower(),
            "requirement_label": f"{activity} rules",
            "category_slugs": [topicCategorySlug],
        },
        "related_topic_slugs": [
            slugify(item)
            for item in parseDelimitedList(row.get("related_topic_slugs"))
            if slugify(item)
        ],
    }

    if summary:
        rule["summary"] = summary
        rule["summary_short"] = summary

    if conditions:
        rule["conditions"] = conditions

    if exceptions:
        rule["exceptions"] = exceptions

    if verifyNext:
        rule["verify_next"] = verifyNext

    if sources:
        rule["sources"] = sources

    if enforcement:
        rule["enforcement"] = enforcement

    if any(penalties.values()):
        rule["penalties"] = penalties

    return rule


def loadBatchRules(countryIndex):
    if not os.path.isdir(BATCHES_DIR):
        return []

    rules = []

    for filePath in sorted(walkFiles(BATCHES_DIR)):
        if not filePath.endswith(".csv"):
            continue

        relativePath = os.path.relpath(filePath, BATCHES_DIR)
        topicCategorySlug = slugify(os.path.basename(os.path.dirname(filePath)))
        countrySlug = slugify(os.path.splitext(os.path.basename(filePath))[0])
        countryMeta = countryIndex.get(countrySlug)

        if not countryMeta:
            raise Exception(f"Unknown country slug derived from batch file {relativePath}")

        with open(filePath, "r", encoding="utf-8-sig", newline="") as file:
            for rowNumber, row in enumerate(csv.DictReader(file), start=2):
                sourceFile = f"{relativePath}#row{rowNumber}"
                rules.append(buildBatchRule(row, sourceFile, countryMeta, topicCategorySlug))

    return rules


def normalizeTopic(topic=None):
    if topic is None:
        topic = {}

    queryLabel = compactText(topic.get("query_label") or topic.get("label"))
    label = compactText(topic.get("label") or queryLabel)
    slug = compactText(topic.get("slug")) or slugify(queryLabel)
    rawActionPhrase = compactText(topic.get("action_label"))
    actionPhrase = normalizeActionPhrase(rawActionPhrase, label)
    nounPhrase = addIndefiniteArticle(label.lower())
    legalObject = compactText(topic.get("legal_object") or nounPhrase or label.lower())
    gerundPhrase = compactText(topic.get("gerund_phrase"))

    if not gerundPhrase:
        rawFirstWord = compactText(rawActionPhrase).split(" ", 1)[0].lower()
        gerundPhrase = (
            compactText(rawActionPhrase)
            if rawFirstWord.endswith("ing")
            else toGerundPhrase(actionPhrase)
        )

    naturalQuestion = compactText(topic.get("natural_question")) or f"Is it legal to {actionPhrase}?"

    return {
        "slug": slug,
        "label": label,
        "query_label": queryLabel.lower(),
        "action_label": actionPhrase or f"do {queryLabel.lower()}",
        "requirement_label": compactText(topic.get("requirement_label"))
        or f"permission for {queryLabel.lower()}",
        "legal_object": legalObject,
        "gerund_phrase": gerundPhrase or queryLabel.lower(),
        "natural_question": naturalQuestion,
        "category_slugs": dedupe(asList(topic.get("category_slugs"))),
    }


def normalizeCountry(country=None):
    if country is None:
        country = {}

    return {
        "slug": compactText(country.get("slug")),
        "name": compactText(country.get("name")),
        "region": compactText(country.get("region")),
    }


def normalizeRule(rule, sourceFile):
    country = normalizeCountry(rule.get("country"))
    topic = normalizeTopic(rule.get("topic"))
    rawVerdict = compactText(rule.get("verdict"))
    rawLegalStatus = compactText(rule.get("legal_status"))
    verdict = rawVerdict or rawLegalStatus
    lastUpdated = normalizeDate(rule.get("last_updated"))

    if not country["slug"] or not country["name"] or not country["region"]:
        raise Exception(f"Invalid country block in {sourceFile}")

    if not topic["slug"] or not topic["label"] or not topic["query_label"]:
        raise Exception(f"Invalid topic block in {sourceFile}")

    if rawVerdict and rawLegalStatus and rawVerdict != rawLegalStatus:
        raise Exception(
            f'Conflicting verdict/legal_status values in {sourceFile}: "{rawVerdict}" vs "{rawLegalStatus}"'
        )

    if verdict not in VALID_VERDICTS:
        label = "legal_status" if hasField(rule, "legal_status") and not rawVerdict else "verdict"
        raise Exception(f'Invalid {label} "{rule.get(label)}" in {sourceFile}')

    if not lastUpdated:
        raise Exception(f"Invalid last_updated value in {sourceFile}")

    # Optional structured legality fields are supported when present, but they
    # must contain meaningful data so bad rows fail early and clearly.
    for key in ("summary", "summary_short", "enforcement"):
        validateOptionalNarrativeField(rule, key, sourceFile)

    for key in ("conditions", "exceptions", "verify_next"):
        validateOptionalNarrativeList(rule, key, sourceFile)

    return {
        "id": compactText(rule.get("id")) or f'{country["slug"]}-{topic["slug"]}',
        "source_file": sourceFile,
        "query": compactText(rule.get("query")) or topic["query_label"],
        "location": compactText(rule.get("location")) or country["name"],
        "verdict": verdict,
        "summary": toSentence(cleanNarrativeText(rule.get("summary"))),
        "summary_short": toSentence(cleanNarrativeText(rule.get("summary_short"))),
        "conditions": normalizeNarrativeList(rule.get("conditions"), sentencify=True),
        "exceptions": normalizeNarrativeList(rule.get("exceptions"), sentencify=True),
        "penalties": normalizePenaltyBlock(
            rule.get("penalties"),
            fieldPresent=hasField(rule, "penalties"),
            sourceFile=sourceFile,
        ),
        "enforcement": toSentence(cleanNarrativeText(rule.get("enforcement"))),
        "verify_next": normalizeNarrativeList(rule.get("verify_next"), sentencify=True),
        "last_updated": lastUpdated,
        "sources": dedupe(asList(rule.get("sources"))),
        "country": country,
        "topic": topic,
        "related_topic_slugs": dedupe(asList(rule.get("related_topic_slugs"))),
    }


def validateRuleSet(rules):
    grouped = {}
    dedupedRules = []
    topicSlugsByCountry = {}

    for rule in rules:
        key = f'{rule["country"]["slug"]}:{rule["topic"]["slug"]}'
        grouped.setdefault(key, []).append(rule)

    duplicateWarnings = []

    for key, candidates in sorted(grouped.items()):
        chosen = sorted(
            candidates,
            key=lambda rule: (
                ruleStructuredScore(rule),
                rule["last_updated"],
                rule["source_file"],
            ),
        )[-1]
        dedupedRules.append(chosen)

        if len(candidates) > 1:
            dropped = [
                candidate["source_file"]
                for candidate in candidates
                if candidate["source_file"] != chosen["source_file"]
            ]
            duplicateWarnings.append(
                f'{key} -> kept {chosen["source_file"]}; dropped {", ".join(sorted(dropped))}'
            )

    printValidationWarning(
        "[dataset validation] Duplicate country/topic rows detected. Keeping the richest row per key.",
        duplicateWarnings,
    )

    for rule in dedupedRules:
        topicSlugsByCountry.setdefault(rule["country"]["slug"], set()).add(
            rule["topic"]["slug"]
        )

    cleanedRelatedTopicWarnings = []

    for rule in dedupedRules:
        availableTopics = topicSlugsByCountry.get(rule["country"]["slug"]) or set()
        cleanedRelatedTopicSlugs = []

        for relatedTopicSlug in rule["related_topic_slugs"]:
            if relatedTopicSlug in availableTopics:
                cleanedRelatedTopicSlugs.append(relatedTopicSlug)
            else:
                cleanedRelatedTopicWarnings.append(
                    f'{rule["source_file"]}: removed related_topic_slugs value "{relatedTopicSlug}" because it does not exist in {rule["country"]["slug"]}'
                )

        rule["related_topic_slugs"] = cleanedRelatedTopicSlugs

    printValidationWarning(
        "[dataset validation] Removed invalid related topic references.",
        sorted(set(cleanedRelatedTopicWarnings)),
    )

    return sorted(
        dedupedRules,
        key=lambda rule: f'{rule["country"]["slug"]}/{rule["topic"]["slug"]}',
    )


def loadSourceRules():
    files = [filePath for filePath in walkFiles(RULES_DIR) if filePath.endswith(".json")]
    countryIndex = loadCountryIndex()

    if not files:
        raise Exception(
            f'No rule files found in {RULES_DIR}. Run "npm run import:legacy" inside V2 first.'
        )

    rules = []

    for filePath in files:
        payload = readJson(filePath)
        entries = payload if isinstance(payload, list) else [payload]

        for entry in entries:
            rules.append(normalizeRule(entry, os.path.relpath(filePath, RULES_DIR)))

    for rule in loadBatchRules(countryIndex):
        rules.append(normalizeRule(rule, rule["source_file"]))

    return validateRuleSet(rules)
