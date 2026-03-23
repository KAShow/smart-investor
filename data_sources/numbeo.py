"""Numbeo - Cost of living data for Bahrain (embedded, no API key needed)."""

import logging
from .base import DataSourceBase

logger = logging.getLogger(__name__)

# Real Bahrain cost of living data (Manama/Bahrain) sourced from Numbeo.com
BAHRAIN_COSTS = {
    "currency": "BHD",
    "last_updated": "2025-Q4",
    "office_rent": {
        "city_center_sqm_monthly": 8.0,   # BHD per sqm/month in city center
        "outside_center_sqm_monthly": 5.5,
        "small_office_50sqm_center": 400,  # BHD/month
        "medium_office_100sqm_center": 800,
        "coworking_desk_monthly": 120,
    },
    "residential_rent": {
        "apartment_1br_center": 350,   # BHD/month
        "apartment_1br_outside": 250,
        "apartment_3br_center": 650,
        "apartment_3br_outside": 450,
    },
    "salaries": {
        "avg_monthly_salary_net": 650,     # BHD
        "min_wage_bahraini": 300,          # BHD (private sector for Bahraini)
        "software_developer": 900,
        "marketing_manager": 800,
        "accountant": 600,
        "sales_representative": 500,
        "office_admin": 350,
        "driver": 200,
        "cleaner": 150,
    },
    "utilities": {
        "electricity_water_monthly_85sqm": 35,  # BHD
        "internet_60mbps_monthly": 25,
        "mobile_plan_monthly": 15,
    },
    "business_costs": {
        "commercial_registration_fee": 50,  # BHD (Sijilat basic)
        "cr_renewal_annual": 50,
        "municipality_license": 100,        # BHD approx
        "work_permit_expat": 200,           # BHD/year
        "company_formation_wll": 1000,      # BHD approx
    },
    "food_prices": {
        "meal_inexpensive_restaurant": 2.5,  # BHD
        "meal_mid_range_2person": 12,
        "cappuccino": 1.8,
        "water_1_5l": 0.3,
        "rice_1kg": 0.8,
        "chicken_1kg": 2.5,
    },
    "transport": {
        "gasoline_liter": 0.140,  # BHD (subsidized)
        "taxi_1km": 0.300,
        "monthly_public_transport": 25,
    },
    "cost_of_living_index": {
        "bahrain_index": 47.3,   # Numbeo index (NYC = 100)
        "rent_index": 24.8,
        "groceries_index": 36.2,
        "restaurant_index": 38.5,
        "purchasing_power_index": 72.1,
    },
}


def _count_numeric_values(d):
    """Recursively count all numeric (int/float) values in a nested dict."""
    count = 0
    for v in d.values():
        if isinstance(v, dict):
            count += _count_numeric_values(v)
        elif isinstance(v, (int, float)):
            count += 1
    return count


class NumbeoSource(DataSourceBase):

    @property
    def source_name(self) -> str:
        return "numbeo"

    @property
    def reliability_score(self) -> float:
        return 0.75

    @property
    def cache_ttl_seconds(self) -> int:
        return 90 * 24 * 3600  # 90 days (cost data changes slowly)

    async def fetch(self, sector: str) -> dict:
        sector_lower = sector.lower()

        # Sector-specific highlights
        sector_highlights = {}
        if "financial" in sector_lower or "finance" in sector_lower:
            sector_highlights = {
                "focus": "business_costs + office_rent + salaries",
                "business_costs": BAHRAIN_COSTS["business_costs"],
                "office_rent": BAHRAIN_COSTS["office_rent"],
                "salaries": BAHRAIN_COSTS["salaries"],
            }

        data_points = _count_numeric_values(BAHRAIN_COSTS)

        return {
            "source": self.source_name,
            "reliability": self.reliability_score,
            "cost_data": BAHRAIN_COSTS,
            "sector_highlights": sector_highlights,
            "data_points": data_points,
            "note": "بيانات تكاليف المعيشة من Numbeo.com — المنامة/البحرين (2025-Q4)",
        }
