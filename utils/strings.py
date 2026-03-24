import math
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


_LOCKED_PLURALS = {
    "brass knuckles",
    "night vision goggles",
    "lock picking tools",
}

_ACTION_PHRASE_OVERRIDES = {
    "carry pepper spray": "carry pepper spray",
    "drive on footpath": "drive on the footpath",
    "drive on pavement": "drive on the pavement",
    "drive on sidewalk": "drive on the sidewalk",
    "drive over speed limit": "drive over the speed limit",
    "drive under influence": "drive under the influence",
    "drive uninsured": "drive without insurance",
    "drive with expired licence": "drive with an expired licence",
    "drive without inspection": "drive without a valid inspection",
    "drive without licence": "drive without a licence",
    "drive without license": "drive without a license",
    "drive without mot": "drive without an MOT",
    "drive without pollution certificate": "drive without a pollution certificate",
    "not wear seatbelt": "drive without wearing a seatbelt",
    "use phone while driving": "use a phone while driving",
}

_GERUND_OVERRIDES = {
    "be": "being",
    "carry": "carrying",
    "drive": "driving",
    "have": "having",
    "make": "making",
    "not": "not being",
    "own": "owning",
    "possess": "possessing",
    "use": "using",
}

_DEGERUND_OVERRIDES = {
    "bringing": "bring",
    "carrying": "carry",
    "declaring": "declare",
    "downloading": "download",
    "filming": "film",
    "gambling": "gamble",
    "installing": "install",
    "monitoring": "monitor",
    "recording": "record",
    "streaming": "stream",
    "tracking": "track",
    "torrenting": "torrent",
    "using": "use",
}


def _js_string(value):
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
    return str(value)


def escapeHtml(value):
    return (
        _js_string(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def slugify(value):
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", _js_string(value).lower()))


def compactText(value):
    return re.sub(r"\s+", " ", _js_string(value)).strip()


def toSentence(value):
    text = compactText(value)

    if not text:
        return ""

    if re.search(r"[.!?]$", text):
        return text

    return f"{text}."


def capitalizeFirst(value):
    text = compactText(value)

    if not text:
        return ""

    return f"{text[:1].upper()}{text[1:]}"


def isPluralPhrase(value):
    phrase = compactText(value).lower()

    if not phrase:
        return False

    if phrase in _LOCKED_PLURALS:
        return True

    lastWord = phrase.split(" ")[-1] if phrase else ""

    if not lastWord:
        return False

    return re.search(r"(goggles|tools|knuckles)$", lastWord) is not None


def beVerbForPhrase(value):
    return "are" if isPluralPhrase(value) else "is"


def beQuestionVerbForPhrase(value):
    return "Are" if isPluralPhrase(value) else "Is"


def titleCase(value):
    words = [word for word in compactText(value).split(" ") if word]
    output = []

    for word in words:
        if len(word) <= 2 and word.isupper():
            output.append(word)
        else:
            output.append(f"{word[:1].upper()}{word[1:].lower()}")

    return " ".join(output)


def formatLocation(value):
    text = compactText(value)
    needsArticle = {
        "United Kingdom",
        "United States",
        "Netherlands",
        "Philippines",
        "Czech Republic",
        "Dominican Republic",
        "United Arab Emirates",
    }

    if not text:
        return ""

    return f"the {text}" if text in needsArticle else text


def startsWithArticle(value):
    text = compactText(value).lower()
    return bool(re.match(r"^(a|an|the)\b", text))


def addIndefiniteArticle(value):
    text = compactText(value)

    if not text or startsWithArticle(text) or isPluralPhrase(text):
        return text

    lowered = text.lower()

    if re.match(r"^(mot|puc)\b", lowered):
        article = "an" if lowered.startswith("m") else "a"
    else:
        article = "an" if re.match(r"^[aeiou]", lowered) else "a"

    return f"{article} {text}"


def normalizeActionPhrase(value, fallback=""):
    text = compactText(value).lower()

    if not text:
        return compactText(fallback).lower()

    if text in _ACTION_PHRASE_OVERRIDES:
        return _ACTION_PHRASE_OVERRIDES[text]

    parts = text.split(" ", 1)
    firstWord = parts[0]
    remainder = parts[1] if len(parts) > 1 else ""

    if firstWord.endswith("ing"):
        baseWord = _DEGERUND_OVERRIDES.get(firstWord)

        if baseWord:
            return compactText(" ".join([baseWord, remainder]))

    return text


def toGerundPhrase(value):
    phrase = compactText(value).lower()

    if not phrase:
        return ""

    parts = phrase.split(" ", 1)
    firstWord = parts[0]
    remainder = parts[1] if len(parts) > 1 else ""

    gerund = _GERUND_OVERRIDES.get(firstWord)

    if gerund is None:
        if firstWord.endswith("ie"):
            gerund = f"{firstWord[:-2]}ying"
        elif firstWord.endswith("e") and firstWord not in {"be", "see"}:
            gerund = f"{firstWord[:-1]}ing"
        else:
            gerund = f"{firstWord}ing"

    return compactText(" ".join([gerund, remainder]))


def dedupe(values):
    if values is None:
        return []

    if not isinstance(values, (list, tuple, set)):
        values = [values]

    seen = set()
    output = []

    for value in values or []:
        normalized = compactText(value)

        if not normalized:
            continue

        key = normalized.lower()

        if key in seen:
            continue

        seen.add(key)
        output.append(normalized)

    return output


def limitText(value, maxLength=160):
    text = compactText(value)

    if len(text) <= maxLength:
        return text

    return f"{text[: maxLength - 3].strip()}..."


def stripHtml(value):
    text = _js_string(value)
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalizeDate(value):
    text = compactText(value)
    local_timezone = datetime.now().astimezone().tzinfo

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text

    if re.fullmatch(r"\d{4}", text):
        return f"{text}-01-01"

    if not text:
        return ""

    iso_candidate = text.replace("Z", "+00:00")

    try:
        parsed = datetime.fromisoformat(iso_candidate)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError, IndexError, OverflowError):
            parsed = None

    if parsed is None:
        for pattern in (
            "%B %d, %Y",
            "%b %d, %Y",
            "%B %d %Y",
            "%b %d %Y",
            "%Y/%m/%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
        ):
            try:
                parsed = datetime.strptime(text, pattern)
                break
            except ValueError:
                continue

    if parsed is None:
        return ""

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=local_timezone)
    else:
        parsed = parsed.astimezone(timezone.utc)

    return parsed.astimezone(timezone.utc).date().isoformat()


def singularizePhrase(value):
    phrase = compactText(value).lower()

    if not phrase or phrase in _LOCKED_PLURALS:
        return phrase

    words = phrase.split(" ")
    lastWord = words[-1] if words else ""

    if not lastWord:
        return phrase

    singular = lastWord

    if singular.endswith("ies"):
        singular = f"{singular[:-3]}y"
    elif singular.endswith("s") and not singular.endswith("ss"):
        singular = singular[:-1]

    words[-1] = singular
    return " ".join(words)
