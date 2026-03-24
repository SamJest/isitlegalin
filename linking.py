try:
    from .utils.strings import toSentence
except ImportError:
    from pygen.utils.strings import toSentence


QUERY_TYPE_ORDER = ["legal", "can-i", "consequences", "requirements"]


def pageId(page):
    return f'{page["country"]["slug"]}:{page["query_type"]}:{page["topic"]["slug"]}'


def toLink(page, reason):
    return {
        "href": page["canonical_path"],
        "label": page["query"],
        "title": page["query"],
        "reason": reason,
        "verdict": page["verdict"],
        "queryType": page["query_type_label"],
        "country": page["country"]["name"],
        "countrySlug": page["country"]["slug"],
        "topic": page["topic"]["label"],
        "topicSlug": page["topic"]["slug"],
    }


def queryTypeOrderIndex(value):
    try:
        return QUERY_TYPE_ORDER.index(value)
    except ValueError:
        return -1


def countrySortKey(page):
    return toSentence(page["country"]["name"].lower())


def querySortKey(page):
    return toSentence(page["query"].lower())


def riskSortKey(page):
    return (-page["risk"]["score"], querySortKey(page))


def categoryLabel(slug):
    return (slug or "").replace("-", " ").strip()


def pushUnique(target, candidates, reason, currentPage):
    for candidate in candidates:
        if candidate["canonical_path"] == currentPage["canonical_path"]:
            continue

        if any(item["href"] == candidate["canonical_path"] for item in target):
            continue

        target.append(toLink(candidate, reason))

        if len(target) >= 10:
            return


def appendUniquePages(target, candidates, currentPage, limit=10):
    for candidate in candidates:
        if candidate["canonical_path"] == currentPage["canonical_path"]:
            continue

        if any(item["canonical_path"] == candidate["canonical_path"] for item in target):
            continue

        target.append(candidate)

        if len(target) >= limit:
            return


def filterByCountry(page, candidates):
    return [
        candidate
        for candidate in candidates
        if candidate["country"]["slug"] != page["country"]["slug"]
    ]


def sortPagesByCountry(candidates):
    return sorted(candidates, key=lambda page: (countrySortKey(page), querySortKey(page)))


def sortPagesByRisk(candidates):
    return sorted(candidates, key=riskSortKey)


def attachRelatedLinks(pages):
    bySource = {}
    byTopicLegal = {}
    byCountryLegal = {}
    byCountryAndQueryType = {}
    byCountryCategoryLegal = {}

    for page in pages:
        sourceKey = page["source_id"]
        countryQueryKey = f'{page["country"]["slug"]}:{page["query_type"]}'

        if sourceKey not in bySource:
            bySource[sourceKey] = []

        if countryQueryKey not in byCountryAndQueryType:
            byCountryAndQueryType[countryQueryKey] = []

        bySource[sourceKey].append(page)
        byCountryAndQueryType[countryQueryKey].append(page)

        if page["query_type"] != "legal":
            continue

        topicKey = page["topic"]["slug"]
        countryKey = page["country"]["slug"]

        if topicKey not in byTopicLegal:
            byTopicLegal[topicKey] = []

        if countryKey not in byCountryLegal:
            byCountryLegal[countryKey] = []

        byTopicLegal[topicKey].append(page)
        byCountryLegal[countryKey].append(page)

        for categorySlug in page["topic"].get("category_slugs") or []:
            bucketKey = f"{countryKey}:{categorySlug}"
            if bucketKey not in byCountryCategoryLegal:
                byCountryCategoryLegal[bucketKey] = []
            byCountryCategoryLegal[bucketKey].append(page)

    output = []
    countryHighInterest = {
        countrySlug: sortPagesByRisk(items)
        for countrySlug, items in byCountryLegal.items()
    }

    for page in pages:
        links = []
        sameRulePages = [
            candidate
            for candidate in bySource.get(page["source_id"], [])
            if candidate["canonical_path"] != page["canonical_path"]
        ]
        sameActivityLegalPages = sortPagesByCountry(
            filterByCountry(page, byTopicLegal.get(page["topic"]["slug"], []))
        )
        sameCountryLegalPages = [
            candidate
            for candidate in byCountryLegal.get(page["country"]["slug"], [])
            if candidate["canonical_path"] != page["canonical_path"]
        ]
        relatedActivityPages = []
        sameTopicPages = []
        primaryCategory = ((page["topic"].get("category_slugs") or []) + [""])[0]

        pushUnique(links, sameRulePages, "Same rule, different intent", page)
        pushUnique(
            links,
            sameActivityLegalPages,
            "Same activity in another country",
            page,
        )

        for relatedTopicSlug in page["related_topic_slugs"]:
            relatedCandidates = [
                candidate
                for candidate in sameCountryLegalPages
                if candidate["topic"]["slug"] == relatedTopicSlug
            ]
            appendUniquePages(
                relatedActivityPages,
                sortPagesByRisk(relatedCandidates),
                page,
            )

        if primaryCategory:
            sameCategoryCandidates = [
                candidate
                for candidate in byCountryCategoryLegal.get(
                    f'{page["country"]["slug"]}:{primaryCategory}', []
                )
                if candidate["canonical_path"] != page["canonical_path"]
            ]
            appendUniquePages(
                sameTopicPages,
                sortPagesByRisk(sameCategoryCandidates),
                page,
            )

        if len(relatedActivityPages) < 8:
            appendUniquePages(
                relatedActivityPages,
                sortPagesByRisk(sameCountryLegalPages),
                page,
                limit=8,
            )

        if len(sameTopicPages) < 8:
            appendUniquePages(
                sameTopicPages,
                sortPagesByRisk(sameCountryLegalPages),
                page,
                limit=8,
            )

        pushUnique(
            links,
            relatedActivityPages,
            "Related activity in the same country",
            page,
        )

        if len(links) < 6:
            pushUnique(
                links,
                countryHighInterest.get(page["country"]["slug"], []),
                "High-interest law in the same country",
                page,
            )

        if len(links) < 5:
            fallbackSameCountryPages = [
                candidate
                for candidate in byCountryAndQueryType.get(
                    f'{page["country"]["slug"]}:{page["query_type"]}', []
                )
                if pageId(candidate) != pageId(page)
            ]
            pushUnique(
                links,
                fallbackSameCountryPages,
                "Another rule in the same country",
                page,
            )

        relatedLegalQuestions = []
        pushUnique(
            relatedLegalQuestions,
            sameActivityLegalPages[:3],
            "Same activity in another country",
            page,
        )
        pushUnique(
            relatedLegalQuestions,
            relatedActivityPages[:3],
            "Related activity in the same country",
            page,
        )
        pushUnique(
            relatedLegalQuestions,
            countryHighInterest.get(page["country"]["slug"], [])[:4],
            "High-interest law in the same country",
            page,
        )

        if len(relatedLegalQuestions) < 4:
            pushUnique(
                relatedLegalQuestions,
                sameTopicPages[:4],
                "Same topic in the same country",
                page,
            )

        if len(relatedLegalQuestions) < 4:
            pushUnique(
                relatedLegalQuestions,
                [
                    candidate
                    for candidate in sameCountryLegalPages
                    if pageId(candidate) != pageId(page)
                ],
                "Another rule in the same country",
                page,
            )

        query_type_links = [
            {
                "href": candidate["canonical_path"],
                "label": candidate["query_type_label"],
                "query": candidate["query"],
                "active": candidate["canonical_path"] == page["canonical_path"],
            }
            for candidate in sorted(
                bySource.get(page["source_id"], []),
                key=lambda candidate: queryTypeOrderIndex(candidate["query_type"]),
            )
        ]

        output.append(
            {
                **page,
                "primary_category_slug": primaryCategory,
                "primary_category_label": categoryLabel(primaryCategory),
                "query_type_links": query_type_links,
                "same_activity_country_links": [
                    toLink(candidate, "Same activity in another country")
                    for candidate in sameActivityLegalPages[:10]
                ],
                "same_country_related_links": [
                    toLink(candidate, "Related activity in the same country")
                    for candidate in relatedActivityPages[:10]
                ],
                "same_topic_links": [
                    toLink(
                        candidate,
                        f'{categoryLabel(primaryCategory).title()} law in the same country'
                        if primaryCategory
                        else "Another nearby law in the same country",
                    )
                    for candidate in sameTopicPages[:10]
                ],
                "related_legal_questions": relatedLegalQuestions[:8],
                "related_links": links[:10],
            }
        )

    return output
