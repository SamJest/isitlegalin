import locale


INTENT_ORDER = ["legal", "can-i", "consequences", "requirements"]


def localeCompareKey(value):
    return locale.strxfrm(str(value))


def intentOrderIndex(value):
    try:
        return INTENT_ORDER.index(value)
    except ValueError:
        return -1


def sortByRiskThenName(pages):
    return sorted(
        pages,
        key=lambda page: (-page["risk"]["score"], localeCompareKey(page["query"])),
    )


def sortByCountryThenQuery(pages):
    return sorted(
        pages,
        key=lambda page: (
            localeCompareKey(page["country"]["name"]),
            localeCompareKey(page["query"]),
        ),
    )


def summarizeVerdicts(pages):
    result = {"Yes": 0, "No": 0, "Depends": 0}

    for page in pages:
        result[page["verdict"]] = (result.get(page["verdict"]) or 0) + 1

    return result


def sortByCountryName(items):
    return sorted(items, key=lambda item: localeCompareKey(item["country"]["name"]))


def buildSiteModel(pages):
    primaryPages = [page for page in pages if page["query_type"] == "legal"]
    countriesMap = {}
    topicsMap = {}
    queryTypesMap = {}
    regionsMap = {}

    for page in primaryPages:
        if page["country"]["slug"] not in countriesMap:
            countriesMap[page["country"]["slug"]] = {
                "slug": page["country"]["slug"],
                "name": page["country"]["name"],
                "region": page["country"]["region"],
                "pages": [],
            }

        if page["topic"]["slug"] not in topicsMap:
            topicsMap[page["topic"]["slug"]] = {
                "slug": page["topic"]["slug"],
                "label": page["topic"]["label"],
                "queryLabel": page["topic"]["query_label"],
                "actionPhrase": page["topic"]["action_label"],
                "gerundPhrase": page["topic"]["gerund_phrase"],
                "categorySlugs": page["topic"]["category_slugs"],
                "pages": [],
            }

        if page["country"]["region"] not in regionsMap:
            regionsMap[page["country"]["region"]] = {
                "name": page["country"]["region"],
                "pages": [],
                "countries": set(),
            }

        countriesMap[page["country"]["slug"]]["pages"].append(page)
        topicsMap[page["topic"]["slug"]]["pages"].append(page)
        regionsMap[page["country"]["region"]]["pages"].append(page)
        regionsMap[page["country"]["region"]]["countries"].add(page["country"]["slug"])

    for page in pages:
        if page["query_type"] not in queryTypesMap:
            queryTypesMap[page["query_type"]] = {
                "slug": page["query_type"],
                "label": page["query_type_label"],
                "pages": [],
            }

        queryTypesMap[page["query_type"]]["pages"].append(page)

    countries = sorted(
        [
            {
                **country,
                "stats": summarizeVerdicts(country["pages"]),
                "topPages": sortByRiskThenName(country["pages"])[:6],
                "permissivePages": [
                    page for page in country["pages"] if page["verdict"] == "Yes"
                ][:4],
            }
            for country in countriesMap.values()
        ],
        key=lambda country: country["name"],
    )

    topics = sorted(
        [
            {
                **topic,
                "stats": summarizeVerdicts(topic["pages"]),
                "highRiskPages": sortByRiskThenName(topic["pages"])[:6],
            }
            for topic in topicsMap.values()
        ],
        key=lambda topic: topic["label"],
    )

    queryTypes = sorted(
        [
            {
                **queryType,
                "stats": summarizeVerdicts(queryType["pages"]),
                "featuredPages": sortByRiskThenName(queryType["pages"])[:8],
            }
            for queryType in queryTypesMap.values()
        ],
        key=lambda queryType: intentOrderIndex(queryType["slug"]),
    )

    regions = sorted(
        [
            {
                "name": region["name"],
                "countries": [
                    country
                    for country in (
                        next(
                            (
                                country
                                for country in countries
                                if country["slug"] == countrySlug
                            ),
                            None,
                        )
                        for countrySlug in region["countries"]
                    )
                    if country
                ],
                "stats": summarizeVerdicts(region["pages"]),
            }
            for region in regionsMap.values()
        ],
        key=lambda region: localeCompareKey(region["name"]),
    )

    countryIndex = {country["slug"]: country for country in countries}
    topicIndex = {topic["slug"]: topic for topic in topics}
    topicComparisons = []
    discoveryPages = []

    for topic in topics:
        legalPages = sortByCountryName(
            [page for page in topic["pages"] if page["query_type"] == "legal"]
        )
        comparisonPath = f'/comparison/{topic["slug"]}-laws-worldwide.html'
        byVerdict = {
            "Yes": [page for page in legalPages if page["verdict"] == "Yes"],
            "No": [page for page in legalPages if page["verdict"] == "No"],
            "Depends": [page for page in legalPages if page["verdict"] == "Depends"],
        }

        topicComparisons.append(
            {
                "slug": topic["slug"],
                "label": topic["label"],
                "gerundPhrase": topic["gerundPhrase"],
                "actionPhrase": topic["actionPhrase"],
                "canonical_path": comparisonPath,
                "pages": legalPages,
                "stats": summarizeVerdicts(legalPages),
            }
        )

        for verdict, keyword in [("Yes", "legal"), ("No", "illegal")]:
            discoveryPages.append(
                {
                    "slug": f'{topic["slug"]}-{keyword}',
                    "topicSlug": topic["slug"],
                    "topicLabel": topic["label"],
                    "verdict": verdict,
                    "keyword": keyword,
                    "canonical_path": f'/discovery/countries-where-{topic["slug"]}-is-{keyword}.html',
                    "pages": byVerdict[verdict],
                    "comparison_path": comparisonPath,
                }
            )

    pageContexts = {}
    comparisonIndex = {
        item["slug"]: item for item in topicComparisons
    }

    for page in pages:
        country = countryIndex.get(page["country"]["slug"])
        topic = topicIndex.get(page["topic"]["slug"])
        otherCountriesForTopic = [
            candidate
            for candidate in (topic.get("pages") if topic else []) or []
            if candidate["country"]["slug"] != page["country"]["slug"]
        ][:6]
        sameTopicIntentPages = sortByCountryThenQuery(
            [
                candidate
                for candidate in pages
                if candidate["topic"]["slug"] == page["topic"]["slug"]
                and candidate["query_type"] == page["query_type"]
            ]
        )
        countryHighlights = [
            candidate
            for candidate in (country.get("topPages") if country else []) or []
            if candidate["canonical_path"] != page["canonical_path"]
        ]
        regionPeers = (
            [
                candidate
                for candidate in next(
                    (
                        region
                        for region in regions
                        if region["name"] == page["country"]["region"]
                    ),
                    {"countries": []},
                )["countries"]
                if candidate["slug"] != page["country"]["slug"]
            ][:4]
            or []
        )

        pageContexts[page["canonical_path"]] = {
            "country": country,
            "topic": topic,
            "otherCountriesForTopic": otherCountriesForTopic,
            "sameTopicIntentPages": sameTopicIntentPages,
            "countryHighlights": countryHighlights,
            "regionPeers": regionPeers,
            "topicComparison": comparisonIndex.get(page["topic"]["slug"]),
        }

    featuredPrimaryPages = sortByRiskThenName(primaryPages)

    return {
        "pages": pages,
        "primaryPages": primaryPages,
        "countries": countries,
        "topics": topics,
        "topicComparisons": topicComparisons,
        "discoveryPages": discoveryPages,
        "queryTypes": queryTypes,
        "regions": regions,
        "featured": {
            "highRisk": featuredPrimaryPages[:8],
            "quickestYes": sorted(
                [page for page in primaryPages if page["verdict"] == "Yes"],
                key=lambda page: page["risk"]["score"],
            )[:8],
            "guardedCalls": sorted(
                [page for page in primaryPages if page["verdict"] == "Depends"],
                key=lambda page: -page["risk"]["score"],
            )[:8],
        },
        "pageContexts": pageContexts,
    }
