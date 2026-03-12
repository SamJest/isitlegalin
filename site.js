// IsItLegalIn Global JS

// -----------------------------
// Law Search Redirect
// -----------------------------

const search = document.getElementById("lawSearch");

if (search) {

  search.addEventListener("keypress", function(e) {

    if (e.key === "Enter") {

      const value = search.value.toLowerCase().trim();

      const parts = value.split(" ");

      if (parts.length >= 2) {

        const activity = parts.slice(0, parts.length - 1).join("-");
        const country = parts[parts.length - 1];

        window.location.href = `/is-${activity}-legal-in-${country}`;

      }

    }

  });

}


// -----------------------------
// Prefetch Links (Perceived Speed)
// -----------------------------

document.querySelectorAll("a").forEach(link => {

  link.addEventListener("mouseover", () => {

    const url = link.href;

    if (!url) return;

    const prefetch = document.createElement("link");

    prefetch.rel = "prefetch";
    prefetch.href = url;

    document.head.appendChild(prefetch);

  });

});