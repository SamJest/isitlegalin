import os
import sys


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
PACKAGE_PARENT = os.path.dirname(PROJECT_ROOT)
for path in (PROJECT_ROOT, PACKAGE_PARENT):
    if path and path not in sys.path:
        sys.path.insert(0, path)

try:
    from pygen.build_pages import expandRulesToPages
    from pygen.build_site_model import buildSiteModel, localeCompareKey
    from pygen.config.site import OUTPUT_DIR
    from pygen.linking import attachRelatedLinks
    from pygen.load_source_rules import loadSourceRules
    from pygen.render_explorer_pages import renderDiscoveryPage
    from pygen.utils.fs import ensureDir
except ImportError:
    from build_pages import expandRulesToPages
    from build_site_model import buildSiteModel, localeCompareKey
    from config.site import OUTPUT_DIR
    from linking import attachRelatedLinks
    from load_source_rules import loadSourceRules
    from render_explorer_pages import renderDiscoveryPage
    from utils.fs import ensureDir


DISCOVERY_DIR = os.path.join(OUTPUT_DIR, "discovery")
VERDICT_KEYWORDS = [("Yes", "legal"), ("No", "illegal")]


def slug_label(slug):
    return (slug or "").replace("-", " ").strip()


def sort_by_country(pages):
    return sorted(pages, key=lambda page: localeCompareKey(page["country"]["name"]))


def strictness_rank(page):
    verdict_rank = {"No": 0, "Depends": 1, "Yes": 2}
    return (
        verdict_rank.get(page["verdict"], 3),
        -page["risk"]["score"],
        localeCompareKey(page["country"]["name"]),
    )


def leniency_rank(page):
    verdict_rank = {"Yes": 0, "Depends": 1, "No": 2}
    return (
        verdict_rank.get(page["verdict"], 3),
        page["risk"]["score"],
        localeCompareKey(page["country"]["name"]),
    )


def build_discovery_pages(model):
    discovery_pages = []

    for topic in model["topics"]:
        legal_pages = sort_by_country(
            [page for page in topic["pages"] if page["query_type"] == "legal"]
        )
        comparison_path = f'/comparison/{topic["slug"]}-laws-worldwide.html'
        by_verdict = {
            "Yes": [page for page in legal_pages if page["verdict"] == "Yes"],
            "No": [page for page in legal_pages if page["verdict"] == "No"],
        }

        for verdict, keyword in VERDICT_KEYWORDS:
            discovery_pages.append(
                {
                    "kind": "verdict",
                    "slug": f'{topic["slug"]}-{keyword}',
                    "topicSlug": topic["slug"],
                    "topicLabel": topic["label"],
                    "verdict": verdict,
                    "keyword": keyword,
                    "canonical_path": f'/discovery/countries-where-{topic["slug"]}-is-{keyword}.html',
                    "pages": by_verdict[verdict],
                    "comparison_path": comparison_path,
                }
            )

    category_pages = {}

    for topic in model["topics"]:
        for category_slug in topic.get("categorySlugs") or []:
            category_pages.setdefault(category_slug, [])
            category_pages[category_slug].extend(
                [page for page in topic["pages"] if page["query_type"] == "legal"]
            )

    for category_slug, pages in sorted(category_pages.items()):
        deduped = list(
            {
                page["canonical_path"]: page
                for page in sort_by_country(pages)
            }.values()
        )
        if len(deduped) < 2:
            continue

        label = slug_label(category_slug)
        discovery_pages.append(
            {
                "kind": "ranking",
                "slug": f"strictest-{category_slug}",
                "heading": f"Strictest countries for {label}",
                "description": f'Browse the stricter end of the current {label} legality pages and open each country page for the exact rule.',
                "intro": f'This ranking uses the current legality dataset and orders countries from the most restrictive baseline toward the middle. Open any card for the country-level rule page.',
                "canonical_path": f"/discovery/strictest-countries-for-{category_slug}.html",
                "pages": sorted(deduped, key=strictness_rank)[:12],
            }
        )
        discovery_pages.append(
            {
                "kind": "ranking",
                "slug": f"lenient-{category_slug}",
                "heading": f"Most lenient countries for {label}",
                "description": f'Browse the more permissive end of the current {label} legality pages and open each country page for the exact rule.',
                "intro": f'This ranking uses the current legality dataset and orders countries from the most permissive baseline toward the middle. Open any card for the country-level rule page.',
                "canonical_path": f"/discovery/most-lenient-countries-for-{category_slug}.html",
                "pages": sorted(deduped, key=leniency_rank)[:12],
            }
        )

    return discovery_pages


def write_discovery_pages(discovery_pages):
    ensureDir(DISCOVERY_DIR)

    for item in discovery_pages:
        output_file = os.path.join(OUTPUT_DIR, item["canonical_path"].lstrip("/"))
        ensureDir(os.path.dirname(output_file))
        with open(output_file, "w", encoding="utf8", newline="") as file:
            file.write(renderDiscoveryPage(item))


def generate_discovery_pages(model=None):
    if model is None:
        rules = loadSourceRules()
        pages = attachRelatedLinks(expandRulesToPages(rules))
        model = buildSiteModel(pages)

    discovery_pages = build_discovery_pages(model)
    write_discovery_pages(discovery_pages)
    return discovery_pages


def main():
    discovery_pages = generate_discovery_pages()
    print(f"Generated {len(discovery_pages)} discovery pages in {DISCOVERY_DIR}")


if __name__ == "__main__":
    main()
