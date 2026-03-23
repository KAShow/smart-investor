"""IMF DataMapper API - Economic forecasts for Bahrain. No API key required."""

import logging
import aiohttp

from .base import DataSourceBase

logger = logging.getLogger(__name__)

# IMF indicator codes and descriptions
IMF_INDICATORS = {
    "NGDP_RPCH": "نمو GDP الحقيقي المتوقع (%)",
    "PCPIPCH": "معدل التضخم المتوقع (%)",
    "GGXWDG_NGDP": "الدين الحكومي (% من GDP)",
    "BCA_NGDPD": "ميزان الحساب الجاري (% من GDP)",
    "LUR": "معدل البطالة المتوقع (%)",
    "NGDPDPC": "GDP للفرد (دولار أمريكي)",
}

BASE_URL = "https://www.imf.org/external/datamapper/api/v1"


class IMFSource(DataSourceBase):

    @property
    def source_name(self) -> str:
        return "imf"

    @property
    def reliability_score(self) -> float:
        return 0.90

    @property
    def cache_ttl_seconds(self) -> int:
        return 30 * 24 * 3600  # 30 days (IMF updates quarterly)

    async def fetch(self, sector: str) -> dict:
        results = {}
        periods = "2022,2023,2024,2025,2026,2027,2028,2029"

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                for indicator, name_ar in IMF_INDICATORS.items():
                    url = f"{BASE_URL}/{indicator}?periods={periods}"
                    try:
                        async with session.get(url) as resp:
                            if resp.status == 200:
                                data = await resp.json(content_type=None)
                                bhr = data.get("values", {}).get(indicator, {}).get("BHR", {})
                                if bhr:
                                    results[indicator] = {
                                        "name": name_ar,
                                        "data": {str(k): round(v, 2) if isinstance(v, float) else v
                                                 for k, v in sorted(bhr.items())},
                                    }
                            else:
                                logger.warning(f"IMF API returned {resp.status} for {indicator}")
                    except Exception as e:
                        logger.warning(f"IMF fetch failed for {indicator}: {e}")
                        continue

        except Exception as e:
            logger.error(f"IMF session error: {e}")

        # Derive forecast summary
        forecast = {}
        gdp_growth = results.get("NGDP_RPCH", {}).get("data", {})
        if gdp_growth:
            recent = {k: v for k, v in gdp_growth.items() if int(k) >= 2025}
            if recent:
                forecast["gdp_growth_forecast"] = recent
                avg = round(sum(recent.values()) / len(recent), 1)
                forecast["avg_gdp_growth_2025_2029"] = avg

        debt = results.get("GGXWDG_NGDP", {}).get("data", {})
        if debt:
            latest = max(debt.items(), key=lambda x: x[0])
            forecast["latest_debt_gdp"] = {"year": latest[0], "value": latest[1]}

        return {
            "source": self.source_name,
            "reliability": self.reliability_score,
            "indicators": results,
            "forecast_summary": forecast,
            "data_points": sum(len(v["data"]) for v in results.values()),
        }
