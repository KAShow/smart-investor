"""data.gov.bh - Bahrain Open Data Portal (expanded datasets beyond GDP)."""

import logging
import requests
from .base import DataSourceBase
from .sector_mapping import get_sector_mapping

logger = logging.getLogger(__name__)

API_BASE = "https://www.data.gov.bh/api/explore/v2.1/catalog/datasets"

# Additional datasets not already covered by bahrain_data.py's DATASET_CONFIG
EXTRA_DATASETS = {
    "population": {
        "api_id": "population-by-governorate-nationality-and-sex-census-2020",
        "params": {"limit": 50},
        "name_ar": "السكان حسب المحافظة",
    },
    "exports": {
        "api_id": "total-export-1-2024",
        "params": {"order_by": "export_value_bd desc", "limit": 30},
        "name_ar": "الصادرات",
    },
    "tourism_spending": {
        "api_id": "01-average-expenditure-per-visitor-per-trip",
        "params": {"order_by": "year desc", "limit": 20},
        "name_ar": "إنفاق السياح",
    },
    "licenses_gcc": {
        "api_id": "04-number-of-licenses-granted-to-gcc-citizens-to-economic-activities",
        "params": {"order_by": "year desc", "limit": 30},
        "name_ar": "تراخيص تجارية لمواطني الخليج",
    },
    "real_estate_gcc": {
        "api_id": "11-number-of-gcc-nationals-owning-real-estate",
        "params": {"order_by": "year desc", "limit": 20},
        "name_ar": "تملك عقارات مواطني الخليج",
    },
    "insurance_workforce": {
        "api_id": "03-bahrain-insurance-market-manpower",
        "params": {"order_by": "year desc", "limit": 20},
        "name_ar": "القوى العاملة في التأمين",
    },
    "air_cargo": {
        "api_id": "02-caa-monthly-air-cargo-movement",
        "params": {"order_by": "year desc, month desc", "limit": 20},
        "name_ar": "حركة الشحن الجوي",
    },
    "wages": {
        "api_id": "workers-covered-by-social-insurance-system-private-sector-by-monthly-wage-groups",
        "params": {"order_by": "year desc", "limit": 30},
        "name_ar": "فئات الأجور الشهرية",
    },
    "unemployment": {
        "api_id": "03-unemployment-yearly",
        "params": {"order_by": "year desc", "limit": 10},
        "name_ar": "البطالة السنوية",
    },
    "gdp_quarterly": {
        "api_id": "2-quarterly-growth-cp-change",
        "params": {"order_by": "year desc, quarter desc", "limit": 30},
        "name_ar": "النمو الفصلي للناتج المحلي",
    },
}

# Which datasets are relevant per sector keyword
_SECTOR_DATASET_MAP = [
    ("عقار", ["real_estate_gcc", "population", "licenses_gcc"]),
    ("تشييد", ["real_estate_gcc", "population", "licenses_gcc"]),
    ("بناء", ["real_estate_gcc", "population"]),
    ("مالي", ["insurance_workforce", "licenses_gcc"]),
    ("تأمين", ["insurance_workforce", "licenses_gcc"]),
    ("سياح", ["tourism_spending", "population"]),
    ("فنادق", ["tourism_spending", "population"]),
    ("إقامة", ["tourism_spending", "population"]),
    ("طعام", ["tourism_spending", "population"]),
    ("نقل", ["air_cargo", "exports"]),
    ("تخزين", ["air_cargo", "exports"]),
    ("صناع", ["exports", "licenses_gcc"]),
    ("تحويل", ["exports", "licenses_gcc"]),
    ("تجار", ["exports", "licenses_gcc", "population"]),
]

# Always include these for any sector
_ALWAYS_INCLUDE = ["population", "wages", "unemployment", "gdp_quarterly"]


def _fetch_records(api_id, params):
    """Fetch records from data.gov.bh API."""
    url = f"{API_BASE}/{api_id}/records"
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", data.get("records", []))
    except Exception as e:
        logger.warning(f"data.gov.bh fetch failed for {api_id}: {e}")
        return []


def _get_fields(record):
    if "record" in record:
        return record["record"].get("fields", {})
    return record


class DataGovSource(DataSourceBase):

    @property
    def source_name(self) -> str:
        return "datagov"

    @property
    def reliability_score(self) -> float:
        return 0.9

    @property
    def cache_ttl_seconds(self) -> int:
        return 30 * 24 * 3600  # 30 days

    async def fetch(self, sector: str) -> dict:
        # Determine which datasets to fetch based on sector
        name_ar = ""
        try:
            from bahrain_data import get_sectors
            sectors = get_sectors()
            info = sectors.get(sector, {})
            name_ar = info.get("name_ar", "")
        except Exception:
            pass

        relevant_ds = list(_ALWAYS_INCLUDE)
        for keyword, datasets in _SECTOR_DATASET_MAP:
            if keyword in name_ar:
                for ds in datasets:
                    if ds not in relevant_ds:
                        relevant_ds.append(ds)
                break  # first match

        results = {}
        total_points = 0
        for ds_key in relevant_ds:
            config = EXTRA_DATASETS.get(ds_key)
            if not config:
                continue
            records = _fetch_records(config["api_id"], config["params"])
            if records:
                # Extract summary from records
                summary = self._summarize(ds_key, records)
                results[ds_key] = {
                    "name_ar": config["name_ar"],
                    "record_count": len(records),
                    "summary": summary,
                }
                total_points += 1

        return {
            "source": self.source_name,
            "reliability": self.reliability_score,
            "datasets": results,
            "data_points": total_points,
            "note": "بيانات من بوابة البحرين للبيانات المفتوحة (data.gov.bh)",
        }

    def _summarize(self, ds_key, records):
        """Extract key summary from dataset records."""
        fields_list = [_get_fields(r) for r in records[:10]]
        if not fields_list:
            return {}

        if ds_key == "population":
            total = 0
            by_gov = {}
            for f in fields_list:
                gov = f.get("governorate", f.get("lmhfz", ""))
                pop = f.get("total", f.get("ljml", 0))
                if gov and pop:
                    try:
                        pop = int(pop)
                        total += pop
                        by_gov[gov] = by_gov.get(gov, 0) + pop
                    except (ValueError, TypeError):
                        pass
            return {"total": total, "by_governorate": by_gov}

        if ds_key == "unemployment":
            latest = fields_list[0] if fields_list else {}
            return {
                "year": latest.get("year", ""),
                "rate": latest.get("unemployment_rate", latest.get("rate", "")),
            }

        if ds_key == "wages":
            return {"record_count": len(fields_list), "sample": fields_list[:3]}

        if ds_key == "tourism_spending":
            latest = fields_list[0] if fields_list else {}
            return {
                "year": latest.get("year", ""),
                "avg_spending": latest.get("average_expenditure", latest.get("value", "")),
            }

        if ds_key == "exports":
            top = []
            for f in fields_list[:5]:
                commodity = f.get("commodity", f.get("lslaa", ""))
                value = f.get("export_value_bd", f.get("value", ""))
                if commodity:
                    top.append({"commodity": commodity, "value_bd": value})
            return {"top_exports": top}

        if ds_key == "gdp_quarterly":
            latest = fields_list[0] if fields_list else {}
            return {
                "year": latest.get("year", ""),
                "quarter": latest.get("quarter", ""),
                "growth_rate": latest.get("growth_rate", ""),
            }

        if ds_key in ("real_estate_gcc", "licenses_gcc", "insurance_workforce"):
            latest = fields_list[0] if fields_list else {}
            return {"year": latest.get("year", ""), "data": latest}

        if ds_key == "air_cargo":
            latest = fields_list[0] if fields_list else {}
            return {
                "year": latest.get("year", ""),
                "month": latest.get("month", ""),
                "tonnage": latest.get("total", latest.get("value", "")),
            }

        return {"record_count": len(fields_list)}
