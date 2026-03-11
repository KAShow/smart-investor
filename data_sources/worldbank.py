"""World Bank Open Data API - No API key required."""

import logging
import aiohttp
from .base import DataSourceBase
from .sector_mapping import SECTOR_MAP

logger = logging.getLogger(__name__)

# World Bank indicator descriptions
INDICATOR_NAMES = {
    "NY.GDP.MKTP.KD.ZG": "معدل نمو GDP الحقيقي (%)",
    "FP.CPI.TOTL.ZG": "معدل التضخم (%)",
    "SP.POP.TOTL": "عدد السكان",
    "NE.TRD.GNFS.ZS": "التجارة (% من GDP)",
    "BX.KLT.DINV.CD.WD": "الاستثمار الأجنبي المباشر (USD)",
    "IT.NET.USER.ZS": "مستخدمو الإنترنت (% من السكان)",
    "IT.CEL.SETS.P2": "اشتراكات الهاتف المحمول (لكل 100 شخص)",
    "GB.XPD.RSDV.GD.ZS": "الإنفاق على البحث والتطوير (% من GDP)",
    "FM.LBL.BMNY.GD.ZS": "النقد بالمعنى الواسع (% من GDP)",
    "NV.IND.MANF.ZS": "القيمة المضافة للصناعة التحويلية (% من GDP)",
    "SH.XPD.CHEX.GD.ZS": "الإنفاق الصحي (% من GDP)",
    "SH.MED.PHYS.ZS": "الأطباء (لكل 1000 شخص)",
    "SE.XPD.TOTL.GD.ZS": "الإنفاق على التعليم (% من GDP)",
    "SL.UEM.TOTL.ZS": "معدل البطالة (%)",
    "IS.SHP.GOOD.TU": "حركة الشحن البحري (طن)",
}

BASE_URL = "https://api.worldbank.org/v2/country/BHR/indicator"


class WorldBankSource(DataSourceBase):

    @property
    def source_name(self) -> str:
        return "world_bank"

    @property
    def reliability_score(self) -> float:
        return 0.95

    @property
    def cache_ttl_seconds(self) -> int:
        return 30 * 24 * 3600  # 30 days

    async def fetch(self, sector: str) -> dict:
        mapping = SECTOR_MAP.get(sector, {})
        indicators = mapping.get("worldbank_indicators", ["NY.GDP.MKTP.KD.ZG", "FP.CPI.TOTL.ZG"])

        results = {}
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                for indicator in indicators:
                    url = f"{BASE_URL}/{indicator}?format=json&date=2019:2024&per_page=10"
                    try:
                        async with session.get(url) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if data and len(data) > 1 and data[1]:
                                    points = []
                                    for item in data[1]:
                                        if item.get("value") is not None:
                                            points.append({
                                                "year": item["date"],
                                                "value": round(item["value"], 2)
                                            })
                                    if points:
                                        results[indicator] = {
                                            "name": INDICATOR_NAMES.get(indicator, indicator),
                                            "data": points[:5],
                                            "unit": self._get_unit(indicator),
                                        }
                            else:
                                logger.warning(f"World Bank API returned {resp.status} for {indicator}")
                    except Exception as e:
                        logger.warning(f"World Bank fetch failed for {indicator}: {e}")
                        continue

        except Exception as e:
            logger.error(f"World Bank session error: {e}")

        return {
            "source": self.source_name,
            "reliability": self.reliability_score,
            "indicators": results,
            "data_points": sum(len(v["data"]) for v in results.values()),
        }

    def _get_unit(self, indicator: str) -> str:
        if indicator.endswith(".ZG") or indicator.endswith(".ZS"):
            return "%"
        if "CD.WD" in indicator:
            return "USD"
        if "TOTL" in indicator and "POP" in indicator:
            return "نسمة"
        return ""
