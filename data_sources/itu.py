"""ITU - Bahrain ICT and digital economy indicators (embedded data)."""

import logging
from .base import DataSourceBase

logger = logging.getLogger(__name__)

BAHRAIN_ICT = {
    "year": 2024,
    "broadband": {
        "fixed_broadband_subscriptions_per_100": 28.4,
        "mobile_broadband_subscriptions_per_100": 135.2,
        "avg_download_speed_mbps": 135.8,
        "avg_upload_speed_mbps": 48.2,
        "fiber_coverage_pct": 95,
    },
    "mobile": {
        "mobile_subscriptions_per_100": 128.5,
        "smartphone_penetration_pct": 92,
        "5g_coverage_pct": 85,
        "4g_coverage_pct": 99,
    },
    "internet": {
        "internet_users_pct": 99.7,
        "social_media_users_pct": 88.2,
        "ecommerce_users_pct": 65,
        "digital_payments_pct": 78,
    },
    "infrastructure": {
        "data_centers": 8,
        "international_bandwidth_gbps": 1200,
        "cloud_readiness_index": 7.8,
        "cybersecurity_index_global_rank": 46,
    },
    "digital_economy": {
        "ict_sector_gdp_pct": 3.5,
        "tech_companies_registered": 800,
        "fintech_companies": 50,
        "government_services_online_pct": 90,
        "eid_adoption_pct": 95,
    },
}

# Sector-specific ICT relevance mapping
SECTOR_ICT_RELEVANCE = {
    "technology": ["broadband", "mobile", "internet", "infrastructure", "digital_economy"],
    "finance": ["internet", "infrastructure", "digital_economy"],
    "retail": ["internet", "mobile", "digital_economy"],
    "food_hospitality": ["internet", "mobile"],
    "health": ["broadband", "internet", "infrastructure"],
    "manufacturing": ["broadband", "infrastructure"],
    "construction": ["broadband", "mobile"],
    "transport": ["mobile", "internet", "infrastructure"],
}


class ITUSource(DataSourceBase):

    @property
    def source_name(self) -> str:
        return "itu"

    @property
    def reliability_score(self) -> float:
        return 0.80

    @property
    def cache_ttl_seconds(self) -> int:
        return 90 * 24 * 3600  # 90 days

    async def fetch(self, sector: str) -> dict:
        relevant_categories = SECTOR_ICT_RELEVANCE.get(sector, list(BAHRAIN_ICT.keys()))
        # Exclude 'year' from categories
        relevant_categories = [c for c in relevant_categories if c != "year"]

        # Build filtered ICT data relevant to the sector
        filtered = {}
        data_points = 0
        for category in relevant_categories:
            cat_data = BAHRAIN_ICT.get(category)
            if cat_data and isinstance(cat_data, dict):
                filtered[category] = cat_data
                data_points += len(cat_data)

        # Compute a digital readiness summary
        digital_readiness = {
            "internet_penetration": BAHRAIN_ICT["internet"]["internet_users_pct"],
            "smartphone_penetration": BAHRAIN_ICT["mobile"]["smartphone_penetration_pct"],
            "ecommerce_adoption": BAHRAIN_ICT["internet"]["ecommerce_users_pct"],
            "digital_payments_adoption": BAHRAIN_ICT["internet"]["digital_payments_pct"],
            "5g_availability": BAHRAIN_ICT["mobile"]["5g_coverage_pct"],
            "fiber_coverage": BAHRAIN_ICT["broadband"]["fiber_coverage_pct"],
        }
        avg_score = round(sum(digital_readiness.values()) / len(digital_readiness), 1)
        digital_readiness["overall_score"] = avg_score

        return {
            "source": self.source_name,
            "reliability": self.reliability_score,
            "year": BAHRAIN_ICT["year"],
            "ict_indicators": filtered,
            "digital_readiness_summary": digital_readiness,
            "data_points": data_points,
        }
