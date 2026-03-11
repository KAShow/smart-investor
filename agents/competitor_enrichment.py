"""Competitor enrichment via DuckDuckGo web search."""

import asyncio
import logging
from web_search import search_web

logger = logging.getLogger(__name__)

# Max concurrent web searches to avoid rate limiting
MAX_CONCURRENT = 3


class CompetitorEnrichment:
    """Enriches competitor data by searching the web for additional details."""

    def enrich_competitor(self, company_name: str, sector: str) -> dict:
        """
        Search for a single competitor and extract additional details.

        Returns dict with:
        - website: company website if found
        - description: brief description from search results
        - strengths: apparent strengths from public info
        - estimated_size: size estimate based on available info
        """
        try:
            query = f'"{company_name}" البحرين {sector}'
            results = search_web(query, max_results=3, region='xa-ar')

            if not results:
                # Try English search
                query_en = f'"{company_name}" Bahrain'
                results = search_web(query_en, max_results=2, region='wt-wt')

            if not results:
                return {"enriched": False}

            # Extract useful info from search results
            website = ""
            description = ""
            lines = results.split("\n")

            for line in lines:
                if "المصدر:" in line or "href" in line.lower():
                    url = line.split("المصدر:")[-1].strip() if "المصدر:" in line else ""
                    if url and company_name.lower().replace(" ", "") in url.lower().replace(" ", ""):
                        website = url
                elif line.strip() and not line.startswith("المصدر:") and len(line.strip()) > 20:
                    if not description:
                        # Clean up: remove markdown bold markers and numbering
                        clean = line.strip().lstrip("0123456789. ")
                        clean = clean.replace("**", "")
                        if len(clean) > 15:
                            description = clean[:200]

            return {
                "enriched": True,
                "website": website,
                "description": description,
                "search_source": "DuckDuckGo",
            }

        except Exception as e:
            logger.warning(f"Failed to enrich competitor '{company_name}': {e}")
            return {"enriched": False}

    def enrich_batch(self, competitors: list, sector: str, max_enrich: int = 8) -> list:
        """
        Enrich a batch of competitors with web search data.
        Only enriches top competitors to respect rate limits.

        Args:
            competitors: list of competitor dicts from Sijilat
            sector: sector name for search context
            max_enrich: max competitors to enrich (default 8)

        Returns:
            Same list with enrichment data merged in
        """
        enriched = []
        count = 0

        for comp in competitors:
            if count < max_enrich:
                name = comp.get("name_en") or comp.get("name_ar", "")
                if name:
                    extra = self.enrich_competitor(name, sector)
                    merged = dict(comp)
                    if extra.get("enriched"):
                        if extra.get("website") and not merged.get("website"):
                            merged["website"] = extra["website"]
                        if extra.get("description"):
                            merged["web_description"] = extra["description"]
                    merged["enriched"] = extra.get("enriched", False)
                    enriched.append(merged)
                    count += 1
                else:
                    enriched.append(dict(comp, enriched=False))
            else:
                enriched.append(dict(comp, enriched=False))

        logger.info(f"Enriched {count}/{len(competitors)} competitors for sector '{sector}'")
        return enriched
