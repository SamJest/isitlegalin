import json
from datetime import datetime
from pathlib import Path

try:
    from .config.site import SITE_CONFIG, TEMPLATES_DIR
    from .utils.strings import compactText, escapeHtml, formatLocation
    from .utils.template import renderTemplate
except ImportError:
    from pygen.config.site import SITE_CONFIG, TEMPLATES_DIR
    from pygen.utils.strings import compactText, escapeHtml, formatLocation
    from pygen.utils.template import renderTemplate


PAGE_TEMPLATE_FILE = str(Path(TEMPLATES_DIR) / "page.html")

pageTemplate = None


def _json_stringify(value, indent=None):
    if indent is None:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace(
            "<", "\\u003c"
        )

    return json.dumps(value, ensure_ascii=False, indent=indent).replace("<", "\\u003c")


def renderDocument(
    title,
    metaDescription,
    canonicalUrl,
    bodyClass="",
    schema=None,
    content="",
    headExtras="",
):
    if schema is None:
        schema = []

    schemaScripts = "\n".join(
        [
            f'<script type="application/ld+json">{item}</script>'
            for item in schema
            if item
        ]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escapeHtml(title)}</title>
  <meta name="description" content="{escapeHtml(metaDescription)}">
  <meta name="robots" content="index,follow">
  <meta name="theme-color" content="#070b16">
  <link rel="canonical" href="{escapeHtml(canonicalUrl)}">
  <meta property="og:title" content="{escapeHtml(title)}">
  <meta property="og:description" content="{escapeHtml(metaDescription)}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{escapeHtml(canonicalUrl)}">
  <meta property="og:site_name" content="{escapeHtml(SITE_CONFIG["siteName"])}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escapeHtml(title)}">
  <meta name="twitter:description" content="{escapeHtml(metaDescription)}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Fraunces:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/assets/styles.css">
  {headExtras}
  <!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-SDKGW2Z55L"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-SDKGW2Z55L');
</script>
  {schemaScripts}
</head>
<body class="{escapeHtml(bodyClass)}">
{content}
<script src="/assets/site.js"></script>
</body>
</html>"""


def loadPageTemplate():
    global pageTemplate

    if pageTemplate is None:
        with open(PAGE_TEMPLATE_FILE, "r", encoding="utf8") as file:
            pageTemplate = file.read()

    return pageTemplate


def asJsonLd(value):
    return _json_stringify(value, indent=2)


def asInlineJson(value):
    return _json_stringify(value)


def assertNoUnresolvedPlaceholders(html, page):
    if "{{" in html or "}}" in html:
        raise Exception(f'Unresolved template placeholder in {page["canonical_path"]}')


def formatDateLabel(value):
    try:
        parsed = datetime.strptime(f"{value}T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
        return f"{parsed.day} {parsed.strftime('%B')} {parsed.year}"
    except Exception:
        return value


def buildVerdictView(page):
    if page["verdict"] == "Yes":
        return {
            "cardLabel": "Legal",
            "kicker": "Permissive baseline",
            "shortLabel": "Legal",
            "explainer": "The rule looks permissive at a baseline level, but storage, transport, import, or misuse rules can still narrow what is safe.",
        }

    if page["verdict"] == "No":
        return {
            "cardLabel": "Illegal",
            "kicker": "Prohibited baseline",
            "shortLabel": "Illegal",
            "explainer": "The safest read is prohibition unless a narrow and documented exception clearly fits your exact situation.",
        }

    return {
        "cardLabel": "Depends on context",
        "kicker": "Context-sensitive answer",
        "shortLabel": "Depends",
        "explainer": "The answer turns on purpose, labelling, permits, public use, or how local authorities classify the conduct.",
    }


def buildClarityView(page):
    if page["verdict"] == "Depends":
        return {
            "label": "Mixed or context-dependent",
            "note": "This is not a clean yes-or-no rule. The conditions and exceptions are part of the answer, not just footnotes.",
        }

    if page["confidence"]["score"] >= 64:
        return {
            "label": "Relatively clear baseline",
            "note": "The structured signals point in one direction, but primary sources still matter before any high-stakes decision.",
        }

    return {
        "label": "Clear enough for triage",
        "note": "This page gives a usable starting point, but you should verify the cited source trail before relying on it.",
    }


def renderListItems(items):
    safeItems = [item for item in (items or []) if item]

    if not safeItems:
        return ""

    return "\n".join([f"<li>{escapeHtml(item)}</li>" for item in safeItems])


def renderFaq(items):
    output = []

    for item in items or []:
        if not item or not item.get("question") or not item.get("answer"):
            continue

        output.append(
            f"""
        <details>
          <summary>{escapeHtml(item["question"])}</summary>
          <p>{escapeHtml(item["answer"])}</p>
        </details>
      """.rstrip()
        )

    return "\n".join(output)


def renderStatRows(rows):
    output = []

    for row in rows:
        if not row or not row.get("value"):
            continue

        output.append(
            f"""
        <article class="stat-row">
          <p>{escapeHtml(row["label"])}</p>
          <h3>{escapeHtml(row["value"])}</h3>
          <span>{escapeHtml(row["detail"])}</span>
        </article>
      """.rstrip()
        )

    return "\n".join(output)


def renderMiniLinks(items):
    output = []

    for item in items:
        if not item or not item.get("href") or not item.get("title"):
            continue

        output.append(
            f"""
        <a class="mini-card" href="{escapeHtml(item["href"])}">
          <strong>{escapeHtml(item["title"])}</strong>
          <span>{escapeHtml(item.get("subtitle") or "")}</span>
        </a>
      """.rstrip()
        )

    return "\n".join(output)


def renderMiniLinkGrid(items, emptyText):
    rendered = renderMiniLinks(items)
    return rendered or f'<p class="empty-state">{escapeHtml(emptyText)}</p>'


def renderSources(sources):
    output = []

    for index, source in enumerate(sources or []):
        if not source:
            continue

        output.append(
            f"""
        <li>
          <strong>Source {index + 1}</strong><br>
          {escapeHtml(source)}
        </li>
      """.rstrip()
        )

    return "\n".join(output)


def renderPenaltyCards(page):
    penalties = (page.get("sections") or {}).get("penalties") or page["penalties"]
    cards = []

    if compactText(penalties.get("fine")) and compactText(penalties["fine"]) != "Not specified":
        cards.append({"label": "Fine exposure", "value": penalties["fine"]})

    if compactText(penalties.get("jail")) and compactText(penalties["jail"]) != "Not specified":
        cards.append({"label": "Jail exposure", "value": penalties["jail"]})

    if compactText(penalties.get("notes")):
        cards.append({"label": "Penalty notes", "value": penalties["notes"]})

    if not cards:
        return ""

    output = []

    for card in cards:
        output.append(
            f"""
        <article class="penalty-card">
          <p class="penalty-card__label">{escapeHtml(card["label"])}</p>
          <p class="penalty-card__value">{escapeHtml(card["value"])}</p>
        </article>
      """.rstrip()
        )

    return "\n".join(output)


def renderIntentSwitcher(page):
    output = []

    for link in page.get("query_type_links") or []:
        output.append(
            f"""
        <a class="intent-pill{' intent-pill--active' if link['active'] else ''}" href="{escapeHtml(link["href"])}" aria-current="{'page' if link['active'] else 'false'}">
          <span>{escapeHtml(link["label"])}</span>
          <small>{escapeHtml(link["query"])}</small>
        </a>
      """.rstrip()
        )

    return "\n".join(output)


def renderContextLinks(page):
    links = [
        {"href": f'/{page["country"]["slug"]}/', "label": page["country"]["name"]},
        {"href": f'/{page["query_type"]}/', "label": page["query_type_label"]},
        {"href": f'/topics/{page["topic"]["slug"]}/', "label": page["topic"]["label"]},
    ]

    comparison = ((page.get("context") or {}).get("topicComparison") or {}).get(
        "canonical_path"
    )

    if comparison:
        links.append(
            {
                "href": comparison,
                "label": f'{page["topic"]["label"]} worldwide',
            }
        )

    return " | ".join(
        [
            f'<a href="{escapeHtml(item["href"])}">{escapeHtml(item["label"])}</a>'
            for item in links
        ]
    )


def dedupeText(items):
    seen = set()
    output = []

    for item in items:
        value = compactText(item)

        if not value:
            continue

        key = value.lower()

        if key in seen:
            continue

        seen.add(key)
        output.append(value)

    return output


def buildQuickAnswer(page):
    if page["verdict"] == "Yes":
        return "The baseline answer is permissive, but the listed conditions and practical limits still matter."

    if page["verdict"] == "No":
        return "Start from prohibition and only move off that position if a clear exception fits your facts."

    return "Small factual differences can change the result, so treat the conditions and exceptions as part of the answer."


def buildTrustBlock(page):
    sourceLabel = "source" if len(page["sources"]) == 1 else "sources"
    return f"""
      <section class="trust-panel" aria-label="How to use this page">
        <div class="trust-panel__header">
          <p class="panel-kicker">Trust</p>
          <h2>Use this page as guidance, not legal advice</h2>
        </div>
        <div class="trust-panel__grid">
          <div class="trust-chip">
            <strong>Publisher</strong>
            <span>Is It Legal In</span>
          </div>
          <div class="trust-chip">
            <strong>By</strong>
            <span>Sam Jones</span>
          </div>
          <div class="trust-chip">
            <strong>Last updated</strong>
            <span>{escapeHtml(formatDateLabel(page["last_updated"]))}</span>
          </div>
          <div class="trust-chip">
            <strong>Structured review</strong>
            <span>{len(page["sources"])} {sourceLabel} in view</span>
          </div>
        </div>
        <p class="trust-panel__body">This page is informational guidance built from the current structured source set. Verify the source trail and local official guidance before relying on it for travel, purchase, public carry, self-defence, or enforcement-sensitive decisions.</p>
      </section>
    """.rstrip()


def buildSignalCards(page, context, clarity, dataShare):
    countryStats = ((context or {}).get("country") or {}).get("stats")
    topicStats = ((context or {}).get("topic") or {}).get("stats")

    cards = [
        {
            "label": "Clarity",
            "value": clarity["label"],
            "text": f'{len(page["sources"])} sources in view.',
        },
        {
            "label": "Confidence",
            "value": page["confidence"]["label"],
            "text": f'{page["confidence"]["score"]}/100 confidence score.',
        },
        {
            "label": "Risk profile",
            "value": page["risk"]["label"],
            "text": f'{page["risk"]["score"]}/100 risk score.',
        },
        {
            "label": "Data coverage",
            "value": f'{round(dataShare * 100)}% data-driven',
            "text": f'{len(page["conditions"])} conditions, {len(page["exceptions"])} exceptions.',
        },
    ]

    if countryStats:
        cards[1] = {
            "label": "This country",
            "value": f'{len(context["country"]["pages"])} tracked topics',
            "text": f'{countryStats["Yes"]} yes | {countryStats["Depends"]} depends | {countryStats["No"]} no.',
        }

    if topicStats:
        cards[2] = {
            "label": "This topic",
            "value": f'{len(context["topic"]["pages"])} countries',
            "text": f'{topicStats["Yes"]} yes | {topicStats["Depends"]} depends | {topicStats["No"]} no.',
        }

    output = []

    for card in cards:
        output.append(
            f"""
        <article class="micro-card">
          <p>{escapeHtml(card["label"])}</p>
          <h3>{escapeHtml(card["value"])}</h3>
          <span>{escapeHtml(card["text"])}</span>
        </article>
      """.rstrip()
        )

    return "\n".join(output)


def buildCountrySnapshot(page, context):
    country = (context or {}).get("country")

    if not country:
        return renderStatRows(
            [
                {
                    "label": "Coverage",
                    "value": "Country context unavailable",
                    "detail": "The page still includes the core rule, but no hub-level snapshot was attached.",
                }
            ]
        )

    statRows = [
        {
            "label": "Verdict mix",
            "value": f'{country["stats"]["Yes"]} yes / {country["stats"]["Depends"]} depends / {country["stats"]["No"]} no',
            "detail": f'{len(country["pages"])} primary legal pages tracked for this country.',
        },
        {
            "label": "Region",
            "value": page["country"]["region"],
            "detail": "Use nearby hubs for comparison.",
        },
    ]

    quickLinks = []

    for candidate in country.get("topPages") or []:
        if candidate["canonical_path"] == page["canonical_path"]:
            continue

        quickLinks.append(
            {
                "href": candidate["canonical_path"],
                "title": candidate["topic"]["label"],
                "subtitle": f'{candidate["verdict"]} answer in {country["name"]}',
            }
        )

        if len(quickLinks) >= 3:
            break

    for peer in (context.get("regionPeers") if context else []) or []:
        quickLinks.append(
            {
                "href": f'/{peer["slug"]}/',
                "title": peer["name"],
                "subtitle": f'Compare another {page["country"]["region"]} jurisdiction',
            }
        )

        if len(quickLinks) >= 5:
            break

    extra = ("\n" + renderMiniLinks(quickLinks)) if quickLinks else ""
    return f"{renderStatRows(statRows)}{extra}"


def buildTopicSnapshot(page, context):
    topic = (context or {}).get("topic")

    if not topic:
        return renderStatRows(
            [
                {
                    "label": "Coverage",
                    "value": "Topic context unavailable",
                    "detail": "The page still includes the rule-level detail, but no topic-level comparison snapshot was attached.",
                }
            ]
        )

    statRows = [
        {
            "label": "Countries tracked",
            "value": f'{len(topic["pages"])}',
            "detail": f'Primary legal pages for {page["topic"]["label"].lower()}.',
        },
        {
            "label": "Global verdict mix",
            "value": f'{topic["stats"]["Yes"]} yes / {topic["stats"]["Depends"]} depends / {topic["stats"]["No"]} no',
            "detail": f'Check whether {page["location"]} is an outlier.',
        },
    ]

    comparisonLinks = []

    for candidate in (context.get("sameTopicIntentPages") if context else []) or []:
        if candidate["canonical_path"] == page["canonical_path"]:
            continue

        comparisonLinks.append(
            {
                "href": candidate["canonical_path"],
                "title": candidate["country"]["name"],
                "subtitle": f'{candidate["query_type_label"]} view | {candidate["verdict"]}',
            }
        )

        if len(comparisonLinks) >= 5:
            break

    extra = ("\n" + renderMiniLinks(comparisonLinks)) if comparisonLinks else ""
    return f"{renderStatRows(statRows)}{extra}"


def buildBreadcrumbs(page):
    return [
        {"label": "Home", "href": "/"},
        {"label": "Countries", "href": "/countries/"},
        {"label": page["country"]["name"], "href": f'/{page["country"]["slug"]}/'},
        {"label": page["query_type_label"], "href": f'/{page["query_type"]}/'},
        {"label": page["topic"]["label"]},
    ]


def buildCountryLinks(page, context):
    items = [
        {
            "href": link["href"],
            "title": link["label"],
            "subtitle": link["reason"],
        }
        for link in (page.get("related_legal_questions") or [])[:8]
    ]
    return renderMiniLinkGrid(
        items,
        "No related legal questions were attached to this page yet.",
    )


def renderBreadcrumbsHtml(items):
    output = []

    for index, item in enumerate(items):
        crumb = (
            f'<a href="{escapeHtml(item["href"])}">{escapeHtml(item["label"])}</a>'
            if item.get("href")
            else f'<span>{escapeHtml(item["label"])}</span>'
        )

        if index == 0:
            output.append(crumb)
        else:
            output.append(f'<span aria-hidden="true">/</span>{crumb}')

    return "".join(output)


def buildSummaryPoints(page):
    sections = page.get("sections") or {}
    return dedupeText(sections.get("summary_points") or page.get("summary_points") or [])[:4]


def buildPracticalTakeaways(page):
    sections = page.get("sections") or {}
    return dedupeText(
        sections.get("verify_next") or page.get("practical_takeaways") or []
    )[:4]


def renderOptionalListSection(kicker, title, items, listClass="", intro=""):
    renderedItems = renderListItems(items)

    if not renderedItems:
        return ""

    introHtml = (
        f'\n            <p class="section-intro">{escapeHtml(intro)}</p>' if intro else ""
    )
    classSuffix = f" {listClass}" if listClass else ""

    return f"""
        <section class="panel">
          <div class="panel-heading">
            <p class="panel-kicker">{escapeHtml(kicker)}</p>
            <h2>{escapeHtml(title)}</h2>{introHtml}
          </div>
          <ul class="stack-list{escapeHtml(classSuffix)}">
            {renderedItems}
          </ul>
        </section>
      """.rstrip()


def renderOptionalRichSection(kicker, title, value):
    text = compactText(value)

    if not text:
        return ""

    return f"""
        <section class="panel">
          <div class="panel-heading">
            <p class="panel-kicker">{escapeHtml(kicker)}</p>
            <h2>{escapeHtml(title)}</h2>
          </div>
          <p class="rich-copy">{escapeHtml(text)}</p>
        </section>
      """.rstrip()


def renderPenaltySection(page):
    penalties = (page.get("sections") or {}).get("penalties") or page["penalties"]
    summary = compactText((penalties or {}).get("summary") or page.get("penalty_answer"))
    cards = renderPenaltyCards(page)

    if not summary and not cards:
        return ""

    summaryHtml = (
        f'\n          <p class="section-intro">{escapeHtml(summary)}</p>' if summary else ""
    )
    cardsHtml = f'\n          <div class="penalty-grid">\n            {cards}\n          </div>' if cards else ""

    return f"""
        <section class="panel">
          <div class="panel-heading">
            <p class="panel-kicker">Penalties</p>
            <h2>Possible penalties</h2>
          </div>{summaryHtml}{cardsHtml}
        </section>
      """.rstrip()


def buildLinkGroups(page, context):
    sameActivityOtherCountries = [
        {
            "href": link["href"],
            "title": link["country"],
            "subtitle": f'{link["verdict"]} legal answer',
        }
        for link in page.get("same_activity_country_links") or []
    ]

    relatedSameCountry = [
        {
            "href": link["href"],
            "title": link["label"],
            "subtitle": link["reason"],
        }
        for link in (page.get("same_country_related_links") or [])[:10]
    ]
    sameTopicLinks = [
        {
            "href": link["href"],
            "title": link["label"],
            "subtitle": link["reason"],
        }
        for link in (page.get("same_topic_links") or [])[:8]
    ]
    topicSectionTitle = (
        f'More {page["primary_category_label"]} laws in {page["country"]["name"]}'
        if page.get("primary_category_label")
        else f'More related laws in {page["country"]["name"]}'
    )

    groups = [
        (
            "Same activity in other countries",
            "Compare the same activity across countries before assuming the answer carries over unchanged.",
            sameActivityOtherCountries[:10],
            "No other country pages were attached to this activity yet.",
        ),
        (
            f'Related activities in {page["country"]["name"]}',
            "Open nearby legal questions in the same country to keep the local picture connected and useful.",
            relatedSameCountry[:10],
            f'No related in-country links were attached for {page["country"]["name"]}.',
        ),
        (
            topicSectionTitle,
            "These links stay within the same broader topic so the next click remains relevant.",
            sameTopicLinks[:8],
            f'No same-topic links were attached for {page["country"]["name"]}.',
        ),
    ]

    output = []

    for title, intro, items, emptyText in groups:
        output.append(
            f"""
        <section class="link-group">
          <div class="panel-heading">
            <p class="panel-kicker">Links</p>
            <h3>{escapeHtml(title)}</h3>
            <p class="link-group__intro">{escapeHtml(intro)}</p>
          </div>
          <div class="link-group__list">
            {renderMiniLinkGrid(items, emptyText)}
          </div>
        </section>
      """.rstrip()
        )

    return f'<div class="link-groups">{"".join(output)}</div>'


def buildSchemas(page, breadcrumbs):
    faqItems = []

    for item in page.get("faq") or []:
        if not item or not item.get("question") or not item.get("answer"):
            continue

        faqItems.append(
            {
                "@type": "Question",
                "name": item["question"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": item["answer"],
                },
            }
        )

    schemas = [
        asJsonLd(
            {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": page["query"],
                "description": page["summary"],
                "datePublished": page["last_updated"],
                "dateModified": page["last_updated"],
                "author": {
                    "@type": "Person",
                    "name": "Sam Jones",
                },
                "publisher": {
                    "@type": "Organization",
                    "name": SITE_CONFIG["siteName"],
                },
                "mainEntityOfPage": page["canonical_url"],
            }
        ),
        asJsonLd(
            {
                "@context": "https://schema.org",
                "@type": "WebPage",
                "name": page["query"],
                "description": page["summary"],
                "url": page["canonical_url"],
            }
        ),
        asJsonLd(
            {
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": index + 1,
                        "name": item["label"],
                        **(
                            {"item": f'{SITE_CONFIG["baseUrl"]}{item["href"]}'}
                            if item.get("href")
                            else {}
                        ),
                    }
                    for index, item in enumerate(breadcrumbs)
                ],
            }
        ),
    ]

    if faqItems:
        schemas.append(
            asJsonLd(
                {
                    "@context": "https://schema.org",
                    "@type": "FAQPage",
                    "mainEntity": faqItems,
                }
            )
        )

    return schemas


def renderPage(page, context=None, dataShare=0.4):
    if context is None:
        context = {}

    page = {**page, "context": context}
    sections = page.get("sections") or {}

    template = loadPageTemplate()
    breadcrumbs = buildBreadcrumbs(page)
    verdictView = buildVerdictView(page)
    clarity = buildClarityView(page)
    friendlyDate = formatDateLabel(page["last_updated"])
    renderedPage = renderTemplate(
        template,
        {
            "breadcrumbs_html": renderBreadcrumbsHtml(breadcrumbs),
            "location": escapeHtml(page["country"]["name"]),
            "region": escapeHtml(page["country"]["region"]),
            "query_type_label": escapeHtml(page["query_type_label"]),
            "h1": escapeHtml(page["h1"]),
            "summary": escapeHtml(page["summary"]),
            "direct_answer": escapeHtml(page["direct_answer"]),
            "copy_text": escapeHtml(f'{page["query"]} {page["summary"]}'),
            "context_links_html": renderContextLinks(page),
            "quick_answer": escapeHtml(buildQuickAnswer(page)),
            "query_type_switcher_html": renderIntentSwitcher(page),
            "verdict_slug": escapeHtml(page["verdict_slug"]),
            "verdict": escapeHtml(verdictView["cardLabel"]),
            "risk_label": escapeHtml(page["risk"]["label"]),
            "risk_score": escapeHtml(str(page["risk"]["score"])),
            "signal_cards_html": buildSignalCards(page, context, clarity, dataShare),
            "summary_points_html": renderListItems(buildSummaryPoints(page)),
            "conditions_section_html": renderOptionalListSection(
                "Conditions",
                "Conditions that shape the answer",
                sections.get("conditions") or page["conditions"],
                "stack-list--conditions",
                "Read these baseline conditions before you move on to exceptions or penalties.",
            ),
            "verify_section_html": renderOptionalListSection(
                "Verify",
                "What to verify next",
                buildPracticalTakeaways(page),
                "stack-list--guidance",
                "These are the next checks most likely to change whether the page is safe to rely on.",
            ),
            "exceptions_section_html": renderOptionalListSection(
                "Exceptions",
                "What can change the answer",
                sections.get("exceptions") or page["exceptions"],
            ),
            "penalties_section_html": renderPenaltySection(page),
            "enforcement_section_html": renderOptionalRichSection(
                "Enforcement",
                "How it is enforced",
                sections.get("enforcement") or page["enforcement"],
            ),
            "faq_html": renderFaq(page["faq"]),
            "link_groups_html": buildLinkGroups(page, context),
            "country_links_html": buildCountryLinks(page, context),
            "country_snapshot_html": buildCountrySnapshot(page, context),
            "topic_label": escapeHtml(page["topic"]["label"]),
            "topic_snapshot_html": buildTopicSnapshot(page, context),
            "sources_html": renderSources(page["sources"]),
            "canonical_path": escapeHtml(page["canonical_path"]),
            "last_updated": escapeHtml(friendlyDate),
            "source_count": escapeHtml(str(len(page["sources"]))),
            "page_payload_json": asInlineJson(
                {
                    "href": page["canonical_path"],
                    "query": page["query"],
                    "country": page["country"]["name"],
                    "topic": page["topic"]["label"],
                    "queryType": page["query_type_label"],
                    "verdict": verdictView["shortLabel"],
                    "directAnswer": page["direct_answer"],
                    "summary": page["summary"],
                    "riskLabel": page["risk"]["label"],
                    "enforcement": sections.get("enforcement") or page["enforcement"],
                }
            ),
        },
    )
    renderedPage = renderedPage.replace(
        '<div class="content-layout">',
        f'{buildTrustBlock(page)}\n\n    <div class="content-layout">',
        1,
    )
    renderedPage = renderedPage.replace(
        f"""<section class="panel">
          <div class="panel-heading">
            <p class="panel-kicker">Country</p>
            <h2>Explore more rules in {escapeHtml(page["country"]["name"])}</h2>
            <p class="section-intro">Keep exploring nearby rules so one answer does not sit in isolation.</p>
          </div>
          <div class="related-grid">
            {buildCountryLinks(page, context)}
          </div>
        </section>""",
        f"""<section class="panel">
          <div class="panel-heading">
            <p class="panel-kicker">Related</p>
            <h2>Related legal questions</h2>
            <p class="section-intro">A short mix of nearby country links, same-topic paths, and high-interest questions to keep discovery useful without getting spammy.</p>
          </div>
          <div class="related-grid">
            {buildCountryLinks(page, context)}
          </div>
        </section>""",
        1,
    )
    assertNoUnresolvedPlaceholders(renderedPage, page)

    return renderDocument(
        title=page["title"],
        metaDescription=page["meta_description"],
        canonicalUrl=page["canonical_url"],
        bodyClass=f'rule-page verdict-{page["verdict_slug"]}',
        schema=buildSchemas(page, breadcrumbs),
        content=renderedPage,
    )
