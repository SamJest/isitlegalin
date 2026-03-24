import json
import os
import shutil
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse
from xml.sax.saxutils import escape

if __package__ in (None, ""):
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

    from pygen.build_pages import expandRulesToPages
    from pygen.build_site_model import buildSiteModel
    from pygen.config.site import ASSETS_DIR, OUTPUT_DIR, SITE_CONFIG
    from pygen.linking import attachRelatedLinks
    from pygen.load_source_rules import loadSourceRules
    from pygen.render_explorer_pages import (
        render404Page,
        renderBrowsePage,
        renderCountriesDirectory,
        renderCountryHub,
        renderComparisonPage,
        renderDiscoveryPage,
        renderHomePage,
        renderIntentDirectory,
        renderIntentHub,
        renderTopicHub,
        renderTopicsDirectory,
    )
    from pygen.render_page import renderPage
    from pygen.scripts.generate_discovery_pages import build_discovery_pages
    from pygen.utils.fs import emptyDir, ensureDir, walkFiles
    from pygen.utils.strings import stripHtml
else:
    from .build_pages import expandRulesToPages
    from .build_site_model import buildSiteModel
    from .config.site import ASSETS_DIR, OUTPUT_DIR, SITE_CONFIG
    from .linking import attachRelatedLinks
    from .load_source_rules import loadSourceRules
    from .render_explorer_pages import (
        render404Page,
        renderBrowsePage,
        renderCountriesDirectory,
        renderCountryHub,
        renderComparisonPage,
        renderDiscoveryPage,
        renderHomePage,
        renderIntentDirectory,
        renderIntentHub,
        renderTopicHub,
        renderTopicsDirectory,
    )
    from .render_page import renderPage
    from .scripts.generate_discovery_pages import build_discovery_pages
    from .utils.fs import emptyDir, ensureDir, walkFiles
    from .utils.strings import stripHtml


ISO_DATE_PATTERN = "????-??-??"
SITEMAP_CHUNK_SIZE = 5000


def writeCNAME():
    domain = SITE_CONFIG.get("domain") or "isitlegalin.com"
    with open(os.path.join(OUTPUT_DIR, "CNAME"), "w", encoding="utf8") as f:
        f.write(domain.strip())

def copyAssets():
    ensureDir(os.path.join(OUTPUT_DIR, "assets"))
    assetFiles = walkFiles(ASSETS_DIR)

    for sourceFile in assetFiles:
        relativePath = os.path.relpath(sourceFile, ASSETS_DIR)
        targetFile = os.path.join(OUTPUT_DIR, "assets", relativePath)
        ensureDir(os.path.dirname(targetFile))
        shutil.copyfile(sourceFile, targetFile)


def buildSitemap(urls):
    return """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{items}
</urlset>
""".format(
        items="\n".join(
            [
                f"  <url><loc>{escape(url)}</loc></url>"
                for url in urls
            ]
        )
    )


def buildSitemapIndex(urls, baseUrl):
    return """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{items}
</sitemapindex>
""".format(
        items="\n".join(
            [
                f"  <sitemap><loc>{escape(baseUrl)}/sitemaps/sitemap-{index}.xml</loc></sitemap>"
                for index in range(1, len(urls) + 1)
            ]
        )
    )


def chunkList(items, chunkSize):
    return [items[i : i + chunkSize] for i in range(0, len(items), chunkSize)]


def isValidUrl(url):
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def detectBaseUrl(urls):
    for url in urls:
        parsed = urlparse(url)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    fallback = SITE_CONFIG.get("baseUrl", "").rstrip("/")
    if fallback and isValidUrl(fallback):
        return fallback
    raise ValueError("Unable to detect sitemap base URL.")


def writeSitemaps(urls):
    uniqueUrls = []
    seen = set()

    for url in urls:
        if not isValidUrl(url) or url in seen:
            continue
        seen.add(url)
        uniqueUrls.append(url)

    sitemapBaseUrl = detectBaseUrl(uniqueUrls)
    sitemapDir = os.path.join(OUTPUT_DIR, "sitemaps")
    ensureDir(sitemapDir)
    sitemapChunks = chunkList(uniqueUrls, SITEMAP_CHUNK_SIZE)

    for index, chunk in enumerate(sitemapChunks, start=1):
        if len(chunk) > SITEMAP_CHUNK_SIZE:
            raise ValueError(f"Sitemap chunk {index} exceeds {SITEMAP_CHUNK_SIZE} URLs.")
        with open(
            os.path.join(sitemapDir, f"sitemap-{index}.xml"),
            "w",
            encoding="utf8",
            newline="",
        ) as file:
            file.write(buildSitemap(chunk))

    with open(
        os.path.join(OUTPUT_DIR, "sitemap.xml"), "w", encoding="utf8", newline=""
    ) as file:
        file.write(buildSitemapIndex(sitemapChunks, sitemapBaseUrl))

    return {"sitemapCount": len(sitemapChunks), "urlCount": len(uniqueUrls)}


def buildManifest(rules, pages, model, averageDataShare):
    byVerdict = {"Yes": 0, "No": 0, "Depends": 0}

    for page in pages:
        byVerdict[page["verdict"]] = (byVerdict.get(page["verdict"]) or 0) + 1

    return {
        "generatedAt": datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
        "ruleCount": len(rules),
        "pageCount": len(pages),
        "averageDataShare": f"{round(averageDataShare * 100)}%",
        "countries": len(model["countries"]),
        "topics": len(model["topics"]),
        "intents": len(model["queryTypes"]),
        "byVerdict": byVerdict,
        "featuredHighRisk": [
            {"href": page["canonical_path"], "label": page["query"]}
            for page in model["featured"]["highRisk"][:6]
        ],
    }


def buildSearchIndex(model):
    return {
        "countries": [
            {
                "slug": country["slug"],
                "name": country["name"],
                "region": country["region"],
            }
            for country in model["countries"]
        ],
        "topics": [
            {
                "slug": topic["slug"],
                "label": topic["label"],
            }
            for topic in model["topics"]
        ],
        "intents": [
            {
                "slug": queryType["slug"],
                "label": queryType["label"],
            }
            for queryType in model["queryTypes"]
        ],
        "verdicts": ["Yes", "No", "Depends"],
        "pages": [
            {
                "href": page["canonical_path"],
                "query": page["query"],
                "summary": page["summary"],
                "verdict": page["verdict"],
                "verdictSlug": page["verdict_slug"],
                "intent": page["query_type"],
                "intentLabel": page["query_type_label"],
                "country": page["country"]["name"],
                "countrySlug": page["country"]["slug"],
                "region": page["country"]["region"],
                "topic": page["topic"]["label"],
                "topicSlug": page["topic"]["slug"],
                "riskLabel": page["risk"]["label"],
                "riskScore": page["risk"]["score"],
                "sourceCount": len(page["sources"]),
            }
            for page in model["pages"]
        ],
    }


def writeStaticPage(relativeOutputPath, html):
    outputFile = os.path.join(OUTPUT_DIR, relativeOutputPath)
    ensureDir(os.path.dirname(outputFile))
    with open(outputFile, "w", encoding="utf8", newline="") as file:
        file.write(html)


def measureDynamicShare(page, html):
    dynamicText = " ".join(
        [
            page["query"],
            page["summary"],
            page["memory_hook"],
            page["freshness_note"],
            *page["summary_points"],
            *page["compliance_checklist"],
            *page["decision_steps"],
            *page["practical_takeaways"],
            *page["conditions"],
            *page["exceptions"],
            page["penalties"]["fine"],
            page["penalties"]["jail"],
            page["penalties"]["notes"],
            page["enforcement"],
            *page["sources"],
            *[
                value
                for item in page["faq"]
                for value in [item["question"], item["answer"]]
            ],
            *[
                value
                for item in page["related_links"]
                for value in [item["label"], item["reason"]]
            ],
        ]
    )

    renderedText = stripHtml(html)
    return len(dynamicText) / max(len(renderedText), 1)


def validatePage(page, html, totalPages):
    issues = []
    dataShare = measureDynamicShare(page, html)

    try:
        datetime.strptime(page["last_updated"], "%Y-%m-%d")
    except ValueError:
        issues.append("last_updated must be an ISO date")

    if len(page["related_links"]) < min(5, max(totalPages - 1, 0)):
        issues.append("page does not have enough related links")

    if dataShare < 0.4:
        issues.append(
            f'data-driven content share is below threshold ({round(dataShare * 100)}%)'
        )

    if issues:
        raise Exception(f'{page["canonical_path"]}\n- ' + "\n- ".join(issues))

    return {"dataShare": dataShare}


def validateInternalTargets(pages, topicComparisons, discoveryPages):
    page_paths = {page["canonical_path"] for page in pages}
    comparison_paths = {item["canonical_path"] for item in topicComparisons}

    for page in pages:
        for collection_name in (
            "query_type_links",
            "same_activity_country_links",
            "same_country_related_links",
            "same_topic_links",
            "related_legal_questions",
            "related_links",
        ):
            for link in page.get(collection_name) or []:
                href = link.get("href")
                if href and href not in page_paths:
                    raise Exception(
                        f'Broken internal link on {page["canonical_path"]}: {href} ({collection_name})'
                    )

    for item in discoveryPages:
        for page in item.get("pages") or []:
            if page["canonical_path"] not in page_paths:
                raise Exception(
                    f'Broken discovery page target on {item["canonical_path"]}: {page["canonical_path"]}'
                )

        if item.get("comparison_path") and item["comparison_path"] not in comparison_paths:
            raise Exception(
                f'Broken discovery comparison target on {item["canonical_path"]}: {item["comparison_path"]}'
            )


def buildSite():
    emptyDir(OUTPUT_DIR)
    writeCNAME()
    copyAssets()

    rules = loadSourceRules()
    pages = attachRelatedLinks(expandRulesToPages(rules))
    model = buildSiteModel(pages)
    discoveryPages = build_discovery_pages(model)
    validateInternalTargets(pages, model["topicComparisons"], discoveryPages)

    dataShareTotal = 0

    for page in pages:
        context = model["pageContexts"].get(page["canonical_path"])
        provisionalHtml = renderPage(page, context, 0.4)
        dataShare = validatePage(page, provisionalHtml, len(pages))["dataShare"]
        finalHtml = renderPage(page, context, dataShare)
        outputFile = os.path.join(
            OUTPUT_DIR,
            page["country"]["slug"],
            page["query_type"],
            page["topic"]["slug"],
            "index.html",
        )

        ensureDir(os.path.dirname(outputFile))
        with open(outputFile, "w", encoding="utf8", newline="") as file:
            file.write(finalHtml)
        dataShareTotal += dataShare

    averageDataShare = dataShareTotal / max(len(pages), 1)

    writeStaticPage("index.html", renderHomePage(model))
    writeStaticPage(os.path.join("browse", "index.html"), renderBrowsePage(model))
    writeStaticPage(
        os.path.join("countries", "index.html"), renderCountriesDirectory(model)
    )
    writeStaticPage(os.path.join("topics", "index.html"), renderTopicsDirectory(model))
    writeStaticPage(os.path.join("legal", "index.html"), renderIntentDirectory(model))
    writeStaticPage("404.html", render404Page())

    for country in model["countries"]:
        writeStaticPage(
            os.path.join(country["slug"], "index.html"), renderCountryHub(country, model)
        )

    for topic in model["topics"]:
        writeStaticPage(
            os.path.join("topics", topic["slug"], "index.html"), renderTopicHub(topic)
        )

    for queryType in model["queryTypes"]:
        writeStaticPage(
            os.path.join(queryType["slug"], "index.html"), renderIntentHub(queryType)
        )

    for item in model["topicComparisons"]:
        writeStaticPage(item["canonical_path"].lstrip("/"), renderComparisonPage(item))

    for item in discoveryPages:
        writeStaticPage(item["canonical_path"].lstrip("/"), renderDiscoveryPage(item))

    searchIndex = buildSearchIndex(model)
    manifest = buildManifest(rules, pages, model, averageDataShare)
    extraUrls = [
        f'{SITE_CONFIG["baseUrl"]}/browse/',
        f'{SITE_CONFIG["baseUrl"]}/countries/',
        f'{SITE_CONFIG["baseUrl"]}/topics/',
        *[
            f'{SITE_CONFIG["baseUrl"]}/{country["slug"]}/'
            for country in model["countries"]
        ],
        *[
            f'{SITE_CONFIG["baseUrl"]}/topics/{topic["slug"]}/'
            for topic in model["topics"]
        ],
        *[
            f'{SITE_CONFIG["baseUrl"]}/{queryType["slug"]}/'
            for queryType in model["queryTypes"]
        ],
        *[
            f'{SITE_CONFIG["baseUrl"]}{item["canonical_path"]}'
            for item in model["topicComparisons"]
        ],
        *[
            f'{SITE_CONFIG["baseUrl"]}{item["canonical_path"]}'
            for item in discoveryPages
        ],
    ]
    allUrls = list(
        dict.fromkeys(
            [
                f'{SITE_CONFIG["baseUrl"]}/',
                *[
                    f'{SITE_CONFIG["baseUrl"]}{page["canonical_path"]}'
                    for page in pages
                ],
                *extraUrls,
            ]
        )
    )
    sitemapSummary = writeSitemaps(allUrls)

    with open(
        os.path.join(OUTPUT_DIR, "build-manifest.json"),
        "w",
        encoding="utf8",
        newline="",
    ) as file:
        file.write(json.dumps(manifest, indent=2, ensure_ascii=False))

    with open(
        os.path.join(OUTPUT_DIR, "page-index.json"),
        "w",
        encoding="utf8",
        newline="",
    ) as file:
        file.write(json.dumps(searchIndex, indent=2, ensure_ascii=False))

    print(f"Built {len(pages)} rule pages from {len(rules)} source rules.")
    print(f"Average data-driven share: {round(averageDataShare * 100)}%")
    print(
        f'Generated {len(model["countries"])} country hubs, {len(model["topics"])} topic hubs, and {len(model["queryTypes"])} intent hubs.'
    )
    print(
        f'Generated {len(model["topicComparisons"])} comparison pages and {len(discoveryPages)} discovery pages.'
    )
    print(
        f'Sitemaps: {sitemapSummary["sitemapCount"]}, total URLs: {sitemapSummary["urlCount"]}'
    )
    print(f"Output written to {OUTPUT_DIR}")


if __name__ == "__main__":
    buildSite()
