"""GCC-Stat - GCC benchmark and comparative economic data (embedded data)."""

import logging
from .base import DataSourceBase

logger = logging.getLogger(__name__)

GCC_BENCHMARKS = {
    "year": 2023,
    "countries": {
        "البحرين": {"gdp_billion_usd": 43.6, "population_million": 1.5, "gdp_per_capita_usd": 29057, "inflation_pct": 0.1, "unemployment_pct": 5.0, "internet_pct": 99.7, "ease_of_business_rank": 43},
        "السعودية": {"gdp_billion_usd": 1061.9, "population_million": 32.2, "gdp_per_capita_usd": 32982, "inflation_pct": 2.3, "unemployment_pct": 4.9, "internet_pct": 99.0, "ease_of_business_rank": 62},
        "الإمارات": {"gdp_billion_usd": 507.5, "population_million": 9.4, "gdp_per_capita_usd": 53983, "inflation_pct": 1.6, "unemployment_pct": 2.8, "internet_pct": 99.5, "ease_of_business_rank": 16},
        "قطر": {"gdp_billion_usd": 219.6, "population_million": 2.7, "gdp_per_capita_usd": 81307, "inflation_pct": 2.8, "unemployment_pct": 0.1, "internet_pct": 99.7, "ease_of_business_rank": 77},
        "الكويت": {"gdp_billion_usd": 161.8, "population_million": 4.3, "gdp_per_capita_usd": 37639, "inflation_pct": 3.6, "unemployment_pct": 2.2, "internet_pct": 98.6, "ease_of_business_rank": 83},
        "عُمان": {"gdp_billion_usd": 104.9, "population_million": 4.6, "gdp_per_capita_usd": 22805, "inflation_pct": 0.9, "unemployment_pct": 2.3, "internet_pct": 95.2, "ease_of_business_rank": 68},
    },
    "bahrain_advantages": [
        "أصغر اقتصاد خليجي لكن أعلى كثافة سكانية — سوق مركّز",
        "أقل معدل تضخم في الخليج (0.1%) — استقرار أسعار",
        "ثاني أعلى نسبة استخدام إنترنت (99.7%) — سوق رقمي ناضج",
        "ثالث أفضل ترتيب في سهولة ممارسة الأعمال خليجياً (بعد الإمارات وقطر)",
        "موقع جغرافي استراتيجي — جسر الملك فهد يربطها بالسعودية",
    ],
    "bahrain_challenges": [
        "أعلى معدل بطالة خليجي (5%)",
        "أصغر سوق محلي (1.5 مليون نسمة)",
        "أعلى دين حكومي (123% من GDP)",
    ],
}

# Sector-specific GCC comparison metrics
SECTOR_GCC_METRICS = {
    "technology": ["gdp_per_capita_usd", "internet_pct", "ease_of_business_rank"],
    "retail": ["gdp_per_capita_usd", "population_million", "inflation_pct"],
    "finance": ["gdp_billion_usd", "gdp_per_capita_usd", "ease_of_business_rank"],
    "manufacturing": ["gdp_billion_usd", "ease_of_business_rank", "inflation_pct"],
    "construction": ["gdp_billion_usd", "population_million", "unemployment_pct"],
    "food_hospitality": ["population_million", "gdp_per_capita_usd", "inflation_pct"],
    "health": ["gdp_per_capita_usd", "population_million", "internet_pct"],
    "transport": ["population_million", "gdp_billion_usd", "ease_of_business_rank"],
}


class GCCStatSource(DataSourceBase):

    @property
    def source_name(self) -> str:
        return "gccstat"

    @property
    def reliability_score(self) -> float:
        return 0.75

    @property
    def cache_ttl_seconds(self) -> int:
        return 90 * 24 * 3600  # 90 days

    async def fetch(self, sector: str) -> dict:
        relevant_metrics = SECTOR_GCC_METRICS.get(sector, list(
            GCC_BENCHMARKS["countries"]["البحرين"].keys()
        ))

        # Build sector-relevant comparison across GCC countries
        comparison = {}
        for country, stats in GCC_BENCHMARKS["countries"].items():
            comparison[country] = {
                k: v for k, v in stats.items() if k in relevant_metrics
            }

        # Compute Bahrain's rank for each relevant metric
        bahrain_rankings = {}
        for metric in relevant_metrics:
            values = [
                (country, stats.get(metric))
                for country, stats in GCC_BENCHMARKS["countries"].items()
                if stats.get(metric) is not None
            ]
            # Lower is better for: unemployment, inflation, ease_of_business_rank
            lower_better = metric in ("unemployment_pct", "inflation_pct", "ease_of_business_rank")
            sorted_vals = sorted(values, key=lambda x: x[1], reverse=not lower_better)
            for rank, (country, _) in enumerate(sorted_vals, 1):
                if country == "البحرين":
                    bahrain_rankings[metric] = {"rank": rank, "out_of": len(sorted_vals)}
                    break

        data_points = sum(len(v) for v in comparison.values()) + len(
            GCC_BENCHMARKS["bahrain_advantages"]
        ) + len(GCC_BENCHMARKS["bahrain_challenges"])

        return {
            "source": self.source_name,
            "reliability": self.reliability_score,
            "year": GCC_BENCHMARKS["year"],
            "gcc_comparison": comparison,
            "bahrain_rankings": bahrain_rankings,
            "bahrain_advantages": GCC_BENCHMARKS["bahrain_advantages"],
            "bahrain_challenges": GCC_BENCHMARKS["bahrain_challenges"],
            "data_points": data_points,
        }
