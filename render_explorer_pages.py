import json

try:
    from .config.site import SITE_CONFIG
    from .utils.strings import escapeHtml
except ImportError:
    from pygen.config.site import SITE_CONFIG
    from pygen.utils.strings import escapeHtml


QUERY_TYPE_DESCRIPTIONS = {
    "legal": "Direct yes, no, or depends answers for people who need a fast legal read.",
    "can-i": "Action-first pages for people deciding whether they can do something right now.",
    "consequences": "Pages that bring likely penalties and enforcement risks to the front.",
    "requirements": "Pages that focus on permits, paperwork, and compliance steps before acting.",
}


def _json_stringify(value, indent=None):
    if indent is None:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace(
            "<", "\\u003c"
        )

    return json.dumps(value, ensure_ascii=False, indent=indent).replace("<", "\\u003c")


def asJsonLd(value):
    return _json_stringify(value, indent=2)


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
  <!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-SDKGW2Z55L"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-SDKGW2Z55L');
</script>
  {headExtras}
  {schemaScripts}
</head>
<body class="{escapeHtml(bodyClass)}">
{content}
<script src="/assets/site.js"></script>
</body>
</html>"""


def renderPageCards(pages, reasonLabel=""):
    output = []

    for page in pages:
        output.append(
            f"""
        <a class="content-card-link" href="{escapeHtml(page["canonical_path"])}">
          <div class="content-card-link__meta">
            <span>{escapeHtml(page["country"]["name"])}</span>
            <span>{escapeHtml(page["query_type_label"])}</span>
            <span>{escapeHtml(page["verdict"])}</span>
            {'<span>' + escapeHtml(reasonLabel) + '</span>' if reasonLabel else ''}
          </div>
          <h3>{escapeHtml(page["query"])}</h3>
          <p>{escapeHtml(page["summary"])}</p>
        </a>
      """.rstrip()
        )

    return "\n".join(output)


def renderRankedPageCards(pages):
    output = []

    for index, page in enumerate(pages):
        output.append(
            f"""
        <a class="content-card-link" href="{escapeHtml(page["canonical_path"])}">
          <div class="content-card-link__meta">
            <span>#{index + 1}</span>
            <span>{escapeHtml(page["country"]["name"])}</span>
            <span>{escapeHtml(page["query_type_label"])}</span>
            <span>{escapeHtml(page["verdict"])}</span>
          </div>
          <h3>{escapeHtml(page["query"])}</h3>
          <p>{escapeHtml(page["summary"])}</p>
        </a>
      """.rstrip()
        )

    return "\n".join(output)


def renderDirectoryCards(items, hrefBuilder, subtitleBuilder):
    output = []

    for item in items:
        output.append(
            f"""
        <a class="directory-card" href="{escapeHtml(hrefBuilder(item))}">
          <h3>{escapeHtml(item.get("name") or item.get("label"))}</h3>
          <p>{escapeHtml(subtitleBuilder(item))}</p>
        </a>
      """.rstrip()
        )

    return "\n".join(output)


def renderHeroSearch(title, description, compact=False):
    return f"""
    <section class="landing-hero{' landing-hero--compact' if compact else ''}">
      <div class="landing-hero__copy">
        <p class="eyebrow">Legal intelligence database</p>
        <h1>{escapeHtml(title)}</h1>
        <p>{escapeHtml(description)}</p>
        <div class="landing-hero__actions">
          <a class="action-button action-button--primary" href="/browse/">Open explorer</a>
          <a class="action-button action-button--ghost" href="/countries/">Browse countries</a>
        </div>
      </div>

      <div class="search-console" data-explorer-root data-mode="{'compact' if compact else 'full'}">
        <div class="search-console__header">
          <h2>Search the rulebase</h2>
          <p>Search by action, then narrow by country, topic, intent, and verdict to reach the right page faster.</p>
        </div>
        <div class="search-console__controls">
          <input type="search" placeholder="Try: pepper spray UK, drones France, radar detector Germany" data-search-input>
          <select data-country-filter>
            <option value="">All countries</option>
          </select>
          <select data-topic-filter>
            <option value="">All topics</option>
          </select>
          <select data-intent-filter>
            <option value="">All intents</option>
          </select>
          <select data-verdict-filter>
            <option value="">All verdicts</option>
          </select>
        </div>
        <div class="search-console__status" data-search-status>Loading index...</div>
        <div class="search-console__results" data-search-results></div>
      </div>
    </section>
  """


def renderShell(title, description, canonicalPath, bodyClass, mainContent, schema=None):
    if schema is None:
        schema = []

    return renderDocument(
        title=title,
        metaDescription=description,
        canonicalUrl=f'{SITE_CONFIG["baseUrl"]}{canonicalPath}',
        bodyClass=bodyClass,
        schema=schema,
        content=f"""
      <div class="site-shell">
        <header class="masthead">
          <div class="masthead__brand">
            <a class="brand-mark" href="/">Is It Legal In</a>
            <p class="brand-subtitle">Legal intelligence across countries</p>
          </div>
          <nav class="masthead__nav" aria-label="Primary">
            <a href="/browse/">Browse</a>
            <a href="/countries/">Countries</a>
            <a href="/topics/">Topics</a>
            <a href="/legal/">Intents</a>
          </nav>
          <form class="masthead__search" action="/browse/" method="get">
            <input type="search" name="q" placeholder="Search rules, countries, or actions">
            <button type="submit">Search</button>
          </form>
        </header>

        <main class="landing-frame">
          {mainContent}
        </main>
      </div>
    """,
    )


def buildLandingSchema(title, description, canonicalUrl):
    return [
        asJsonLd(
            {
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": title,
                "description": description,
                "url": canonicalUrl,
            }
        )
    ]


def renderHomePage(model):
    title = "Is It Legal In | Legal intelligence, consequences, and compliance rules"
    description = "Explore a legal intelligence database built for trusted answers, practical comparisons, and clearer compliance guidance across countries."

    return renderShell(
        title=title,
        description=description,
        canonicalPath="/",
        bodyClass="landing-page landing-page--home",
        schema=buildLandingSchema(title, description, f'{SITE_CONFIG["baseUrl"]}/'),
        mainContent=f"""
      {renderHeroSearch("A clearer legal database for cross-country decisions", "Search by action, country, or consequence, then move from a fast answer to the conditions, risks, and next steps that matter.")}

      <section class="landing-section">
        <div class="section-heading">
          <p class="panel-kicker">Database pulse</p>
          <h2>Built to feel credible under pressure</h2>
        </div>
        <div class="stats-grid">
          <article class="stat-card"><h3>{len(model["primaryPages"])}</h3><p>core legal pages</p></article>
          <article class="stat-card"><h3>{len(model["pages"])}</h3><p>total generated pages</p></article>
          <article class="stat-card"><h3>{len(model["countries"])}</h3><p>countries tracked</p></article>
          <article class="stat-card"><h3>{len(model["topics"])}</h3><p>topics mapped</p></article>
        </div>
      </section>

      <section class="landing-section">
        <div class="section-heading">
          <p class="panel-kicker">Browse by intent</p>
          <h2>Start from the question in your head</h2>
        </div>
        <div class="directory-grid">
          {renderDirectoryCards(model["queryTypes"], lambda item: f'/{item["slug"]}/', lambda item: QUERY_TYPE_DESCRIPTIONS[item["slug"]])}
        </div>
      </section>

      <section class="landing-section">
        <div class="section-heading">
          <p class="panel-kicker">High consequence</p>
          <h2>Rules people should not guess about</h2>
        </div>
        <div class="card-grid">
          {renderPageCards(model["featured"]["highRisk"])}
        </div>
      </section>

      <section class="landing-section landing-section--split">
        <div class="landing-column">
          <div class="section-heading">
            <p class="panel-kicker">Fast green lights</p>
            <h2>Lower-friction starting points</h2>
          </div>
          <div class="card-grid card-grid--compact">
            {renderPageCards(model["featured"]["quickestYes"])}
          </div>
        </div>
        <div class="landing-column">
          <div class="section-heading">
            <p class="panel-kicker">Edge cases</p>
            <h2>Rules that hinge on conditions</h2>
          </div>
          <div class="card-grid card-grid--compact">
            {renderPageCards(model["featured"]["guardedCalls"])}
          </div>
        </div>
      </section>

      <section class="landing-section landing-section--split">
        <div class="landing-column">
          <div class="section-heading">
            <p class="panel-kicker">Come back to this</p>
            <h2>Recent explorations</h2>
          </div>
          <div class="recent-list recent-list--landing" data-recent-pages></div>
        </div>
        <div class="landing-column">
          <div class="section-heading">
            <p class="panel-kicker">Saved for later</p>
            <h2>Pages you marked to revisit</h2>
          </div>
          <div class="recent-list recent-list--landing" data-saved-pages></div>
        </div>
      </section>

      <section class="landing-section landing-section--split">
        <div class="landing-column">
          <div class="section-heading">
            <p class="panel-kicker">Countries</p>
            <h2>Jump into a jurisdiction</h2>
          </div>
          <div class="directory-grid">
            {renderDirectoryCards(model["countries"], lambda item: f'/{item["slug"]}/', lambda item: f'{item["stats"]["Yes"]} yes | {item["stats"]["Depends"]} depends | {item["stats"]["No"]} no')}
          </div>
        </div>
        <div class="landing-column">
          <div class="section-heading">
            <p class="panel-kicker">Topics</p>
            <h2>Follow the action you care about</h2>
          </div>
          <div class="directory-grid">
            {renderDirectoryCards(model["topics"], lambda item: f'/topics/{item["slug"]}/', lambda item: f'{len(item["pages"])} countries tracked')}
          </div>
        </div>
      </section>
    """,
    )


def renderBrowsePage(model):
    title = "Browse the Is It Legal In database"
    description = "Filter the database by action, country, intent, verdict, and risk level to find the right legal page quickly."

    return renderShell(
        title=title,
        description=description,
        canonicalPath="/browse/",
        bodyClass="landing-page landing-page--browse",
        schema=buildLandingSchema(title, description, f'{SITE_CONFIG["baseUrl"]}/browse/'),
        mainContent=f"""
      {renderHeroSearch("Explore the full database without losing context", "Use live search, structured filters, recent pages, and saved pages to review rules with less guesswork and better continuity.", compact=True)}

      <section class="landing-section">
        <div class="section-heading">
          <p class="panel-kicker">Search notes</p>
          <h2>What the explorer is optimized for</h2>
        </div>
        <div class="directory-grid">
          <article class="directory-card directory-card--static"><h3>Connected legal views</h3><p>Legal, can-I, consequences, and requirements pages stay linked around the same rule.</p></article>
          <article class="directory-card directory-card--static"><h3>Private continuity</h3><p>Recent and saved pages stay on device so research sessions are easy to resume.</p></article>
          <article class="directory-card directory-card--static"><h3>Structured comparisons</h3><p>Results remain filterable by country, topic, verdict, and intent for cleaner review.</p></article>
        </div>
      </section>
    """,
    )


def renderCountriesDirectory(model):
    title = "Countries in the Is It Legal In database"
    description = "Browse legal rules by country and open jurisdiction-specific hubs with verdict mixes, high-friction pages, and related actions."

    return renderShell(
        title=title,
        description=description,
        canonicalPath="/countries/",
        bodyClass="landing-page landing-page--directory",
        schema=buildLandingSchema(title, description, f'{SITE_CONFIG["baseUrl"]}/countries/'),
        mainContent=f"""
      <section class="landing-section">
        <div class="section-heading">
          <p class="panel-kicker">Country directory</p>
          <h1>Every tracked jurisdiction in one place</h1>
          <p class="section-copy">Each country hub brings together the verdict mix, the riskiest rules, and the quickest routes into the four query intents.</p>
        </div>
        <div class="directory-grid">
          {renderDirectoryCards(model["countries"], lambda item: f'/{item["slug"]}/', lambda item: f'{item["stats"]["Yes"]} yes | {item["stats"]["Depends"]} depends | {item["stats"]["No"]} no')}
        </div>
      </section>
    """,
    )


def renderTopicsDirectory(model):
    title = "Topics in the Is It Legal In database"
    description = "Browse the database by topic to compare how the same action is treated across countries and where the toughest rules sit."

    return renderShell(
        title=title,
        description=description,
        canonicalPath="/topics/",
        bodyClass="landing-page landing-page--directory",
        schema=buildLandingSchema(title, description, f'{SITE_CONFIG["baseUrl"]}/topics/'),
        mainContent=f"""
      <section class="landing-section">
        <div class="section-heading">
          <p class="panel-kicker">Topic directory</p>
          <h1>Every tracked action, item, or rule cluster</h1>
          <p class="section-copy">Topic hubs show the global verdict mix, country-by-country links, and the most important rule pages for that subject.</p>
        </div>
        <div class="directory-grid">
          {renderDirectoryCards(model["topics"], lambda item: f'/topics/{item["slug"]}/', lambda item: f'{len(item["pages"])} countries tracked')}
        </div>
      </section>
    """,
    )


def renderIntentDirectory(model):
    title = "Browse the database by query intent"
    description = "Start from the question you actually have in mind: is it legal, can I, what happens if, or what do I need."

    return renderShell(
        title=title,
        description=description,
        canonicalPath="/legal/",
        bodyClass="landing-page landing-page--directory",
        schema=buildLandingSchema(title, description, f'{SITE_CONFIG["baseUrl"]}/legal/'),
        mainContent=f"""
      <section class="landing-section">
        <div class="section-heading">
          <p class="panel-kicker">Intent directory</p>
          <h1>Choose the angle that matches your decision</h1>
          <p class="section-copy">Each intent hub uses the same underlying rules but frames them differently for users in different moments.</p>
        </div>
        <div class="directory-grid">
          {renderDirectoryCards(model["queryTypes"], lambda item: f'/{item["slug"]}/', lambda item: QUERY_TYPE_DESCRIPTIONS[item["slug"]])}
        </div>
      </section>
    """,
    )


def renderCountryHub(country, model):
    title = f'{country["name"]} legal rules and compliance guide'
    description = f'Explore the {country["name"]} hub to see tracked rules, verdict mixes, and the most important legal pages in one place.'

    return renderShell(
        title=title,
        description=description,
        canonicalPath=f'/{country["slug"]}/',
        bodyClass="landing-page landing-page--hub",
        schema=buildLandingSchema(title, description, f'{SITE_CONFIG["baseUrl"]}/{country["slug"]}/'),
        mainContent=f"""
      <section class="landing-section">
        <div class="section-heading">
          <p class="panel-kicker">{escapeHtml(country["region"])}</p>
          <h1>{escapeHtml(country["name"])}</h1>
          <p class="section-copy">This hub gives you the fastest route into the highest-value rule pages for {escapeHtml(country["name"])}.</p>
        </div>
        <div class="stats-grid">
          <article class="stat-card"><h3>{len(country["pages"])}</h3><p>tracked rules</p></article>
          <article class="stat-card"><h3>{country["stats"]["Yes"]}</h3><p>yes answers</p></article>
          <article class="stat-card"><h3>{country["stats"]["Depends"]}</h3><p>depends answers</p></article>
          <article class="stat-card"><h3>{country["stats"]["No"]}</h3><p>no answers</p></article>
        </div>
      </section>

      <section class="landing-section">
        <div class="section-heading">
          <p class="panel-kicker">Priority rules</p>
          <h2>Where users should start</h2>
        </div>
        <div class="card-grid">
          {renderPageCards(country["topPages"])}
        </div>
      </section>

      <section class="landing-section">
        <div class="section-heading">
          <p class="panel-kicker">More permissive routes</p>
          <h2>Rules that appear easier to navigate</h2>
        </div>
        <div class="card-grid card-grid--compact">
          {renderPageCards(country["permissivePages"])}
        </div>
      </section>
    """,
    )


def renderTopicHub(topic):
    title = f'{topic["label"]} rules by country'
    description = f'Compare how {topic["gerundPhrase"]} is treated across countries, with verdict mixes, high-friction pages, and the best comparison paths.'

    return renderShell(
        title=title,
        description=description,
        canonicalPath=f'/topics/{topic["slug"]}/',
        bodyClass="landing-page landing-page--hub",
        schema=buildLandingSchema(title, description, f'{SITE_CONFIG["baseUrl"]}/topics/{topic["slug"]}/'),
        mainContent=f"""
      <section class="landing-section">
        <div class="section-heading">
          <p class="panel-kicker">Topic hub</p>
          <h1>{escapeHtml(topic["label"])}</h1>
          <p class="section-copy">Track how the same topic changes across countries and where the most important differences appear.</p>
        </div>
        <div class="stats-grid">
          <article class="stat-card"><h3>{len(topic["pages"])}</h3><p>countries tracked</p></article>
          <article class="stat-card"><h3>{topic["stats"]["Yes"]}</h3><p>yes answers</p></article>
          <article class="stat-card"><h3>{topic["stats"]["Depends"]}</h3><p>depends answers</p></article>
          <article class="stat-card"><h3>{topic["stats"]["No"]}</h3><p>no answers</p></article>
        </div>
      </section>

      <section class="landing-section">
        <div class="section-heading">
          <p class="panel-kicker">High-friction pages</p>
          <h2>Where users will need the most guidance</h2>
        </div>
        <div class="card-grid">
          {renderPageCards(topic["highRiskPages"])}
        </div>
      </section>
    """,
    )


def renderIntentHub(queryType):
    title = f'{queryType["label"]} pages in the Is It Legal In database'
    description = QUERY_TYPE_DESCRIPTIONS[queryType["slug"]]

    return renderShell(
        title=title,
        description=description,
        canonicalPath=f'/{queryType["slug"]}/',
        bodyClass="landing-page landing-page--hub",
        schema=buildLandingSchema(title, description, f'{SITE_CONFIG["baseUrl"]}/{queryType["slug"]}/'),
        mainContent=f"""
      <section class="landing-section">
        <div class="section-heading">
          <p class="panel-kicker">Intent hub</p>
          <h1>{escapeHtml(queryType["label"])}</h1>
          <p class="section-copy">{escapeHtml(description)}</p>
        </div>
        <div class="stats-grid">
          <article class="stat-card"><h3>{len(queryType["pages"])}</h3><p>pages in this intent</p></article>
          <article class="stat-card"><h3>{queryType["stats"]["Yes"]}</h3><p>yes answers</p></article>
          <article class="stat-card"><h3>{queryType["stats"]["Depends"]}</h3><p>depends answers</p></article>
          <article class="stat-card"><h3>{queryType["stats"]["No"]}</h3><p>no answers</p></article>
        </div>
      </section>

      <section class="landing-section">
        <div class="section-heading">
          <p class="panel-kicker">Featured pages</p>
          <h2>Best starting points in this intent</h2>
        </div>
        <div class="card-grid">
          {renderPageCards(queryType["featuredPages"])}
        </div>
      </section>
    """,
    )


def renderComparisonPage(item):
    title = f'{item["label"]} Laws Worldwide | {SITE_CONFIG["siteName"]}'
    description = f'Compare {item["gerundPhrase"]} across countries with a simple verdict table and direct links into each legality page.'
    rows = "\n".join(
        [
            f"""
            <tr>
              <td>{escapeHtml(page["country"]["name"])}</td>
              <td>{escapeHtml(page["verdict"])}</td>
              <td><a href="{escapeHtml(page["canonical_path"])}">{escapeHtml(page["query"])}</a></td>
            </tr>
          """.rstrip()
            for page in item["pages"]
        ]
    )

    return renderShell(
        title=title,
        description=description,
        canonicalPath=item["canonical_path"],
        bodyClass="landing-page landing-page--comparison",
        schema=buildLandingSchema(title, description, f'{SITE_CONFIG["baseUrl"]}{item["canonical_path"]}'),
        mainContent=f"""
      <section class="landing-section">
        <div class="section-heading">
          <p class="panel-kicker">Comparison</p>
          <h1>{escapeHtml(item["label"])} laws worldwide</h1>
          <p class="section-copy">Use this page to compare the baseline legal status country by country. Open any row for the fuller legality page.</p>
        </div>
        <div class="panel">
          <div class="meta-note">
            <p><strong>Countries tracked:</strong> {len(item["pages"])}</p>
            <p><strong>Verdict mix:</strong> {item["stats"]["Yes"]} yes | {item["stats"]["Depends"]} depends | {item["stats"]["No"]} no</p>
          </div>
          <div class="table-wrap">
            <table class="comparison-table">
              <thead>
                <tr>
                  <th>Country</th>
                  <th>Legal Status</th>
                  <th>Legality Page</th>
                </tr>
              </thead>
              <tbody>
                {rows}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    """,
    )


def renderDiscoveryPage(item):
    if item.get("kind") == "ranking":
        title = f'{item["heading"]} | {SITE_CONFIG["siteName"]}'
        description = item["description"]
        cards = renderRankedPageCards(item["pages"])

        comparisonHtml = (
            f'<p><strong>Explore all countries:</strong> <a href="{escapeHtml(item["comparison_path"])}">{escapeHtml(item["comparison_label"])}</a></p>'
            if item.get("comparison_path") and item.get("comparison_label")
            else ""
        )

        return renderShell(
            title=title,
            description=description,
            canonicalPath=item["canonical_path"],
            bodyClass="landing-page landing-page--discovery",
            schema=buildLandingSchema(title, description, f'{SITE_CONFIG["baseUrl"]}{item["canonical_path"]}'),
            mainContent=f"""
      <section class="landing-section">
        <div class="section-heading">
          <p class="panel-kicker">Discovery</p>
          <h1>{escapeHtml(item["heading"])}</h1>
          <p class="section-copy">{escapeHtml(item["intro"])}</p>
        </div>
        <div class="panel">
          <div class="meta-note">
            <p><strong>Countries ranked:</strong> {len(item["pages"])}</p>
            {comparisonHtml}
          </div>
          <div class="card-grid">
            {cards or '<p class="empty-state">No countries are currently available for this ranking.</p>'}
          </div>
        </div>
      </section>
    """,
        )

    title = f'Countries Where {item["topicLabel"]} Is {item["keyword"].capitalize()} | {SITE_CONFIG["siteName"]}'
    description = f'Browse countries where {item["topicLabel"].lower()} is marked {item["keyword"]} and jump straight into the underlying legality pages.'
    cards = renderPageCards(item["pages"], reasonLabel=item["keyword"])

    return renderShell(
        title=title,
        description=description,
        canonicalPath=item["canonical_path"],
        bodyClass="landing-page landing-page--discovery",
        schema=buildLandingSchema(title, description, f'{SITE_CONFIG["baseUrl"]}{item["canonical_path"]}'),
        mainContent=f"""
      <section class="landing-section">
        <div class="section-heading">
          <p class="panel-kicker">Discovery</p>
          <h1>Countries where {escapeHtml(item["topicLabel"].lower())} is {escapeHtml(item["keyword"])}</h1>
          <p class="section-copy">This is a simple discovery view built from the current legality pages. Use it to spot likely matches, then open the underlying country page for the exact rule.</p>
        </div>
        <div class="panel">
          <div class="meta-note">
            <p><strong>Countries in this list:</strong> {len(item["pages"])}</p>
            <p><strong>Compare all countries:</strong> <a href="{escapeHtml(item["comparison_path"])}">{escapeHtml(item["topicLabel"])} laws worldwide</a></p>
          </div>
          <div class="card-grid">
            {cards or '<p class="empty-state">No countries currently match this status in the tracked legality pages.</p>'}
          </div>
        </div>
      </section>
    """,
    )


def render404Page():
    title = "Page not found | Is It Legal In"
    description = "The page you wanted moved or no longer exists. Use the explorer to find the closest rule page."

    return renderShell(
        title=title,
        description=description,
        canonicalPath="/404.html",
        bodyClass="landing-page landing-page--404",
        schema=buildLandingSchema(title, description, f'{SITE_CONFIG["baseUrl"]}/404.html'),
        mainContent="""
      <section class="landing-section landing-section--centered">
        <div class="section-heading">
          <p class="panel-kicker">404</p>
          <h1>That route is gone, but the database is still here</h1>
          <p class="section-copy">Use the explorer or jump back to the homepage to keep moving.</p>
        </div>
        <div class="landing-hero__actions">
          <a class="action-button action-button--primary" href="/browse/">Open explorer</a>
          <a class="action-button action-button--ghost" href="/">Go home</a>
        </div>
      </section>
    """,
    )
