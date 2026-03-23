"""DataAggregator - Fetches from all sources in parallel and builds agent-specific context."""

import asyncio
import json
import logging
import time
from datetime import datetime

from .worldbank import WorldBankSource
from .cbb import CBBSource
from .sijilat import SijilatSource
from .trading_economics import TradingEconomicsSource
from .bahrain_bourse import BahrainBourseSource
from .tamkeen import TamkeenSource
from .edb import EDBSource
from .datagov import DataGovSource
from .google_trends import GoogleTrendsSource
from .jobs import JobMarketSource
from .imf import IMFSource
from .comtrade import ComtradeSource
from .numbeo import NumbeoSource
from .wto import WTOSource
from .gccstat import GCCStatSource
from .itu import ITUSource

logger = logging.getLogger(__name__)

# Human-readable metadata for each data source
SOURCE_META = {
    "world_bank": {
        "name_ar": "البنك الدولي",
        "name_en": "World Bank",
        "icon": "\U0001f30d",
        "type": "api",
        "url": "https://api.worldbank.org",
        "description_ar": "مؤشرات اقتصادية أساسية + متخصصة حسب القطاع: نمو GDP، التضخم، البطالة، التجارة، السكان",
    },
    "cbb": {
        "name_ar": "مصرف البحرين المركزي",
        "name_en": "Central Bank of Bahrain",
        "icon": "\U0001f3db\ufe0f",
        "type": "api_with_fallback",
        "url": "https://www.cbb.gov.bh",
        "description_ar": "أسعار صرف الدينار البحريني وأسعار الفائدة الرئيسية",
    },
    "sijilat": {
        "name_ar": "سجلات - السجل التجاري",
        "name_en": "Sijilat",
        "icon": "\U0001f4cb",
        "type": "api_optional",
        "url": "https://sijilat.bh",
        "description_ar": "بيانات السجلات التجارية وعدد الشركات المسجلة حسب النشاط",
    },
    "trading_economics": {
        "name_ar": "Trading Economics",
        "name_en": "Trading Economics",
        "icon": "\U0001f4c8",
        "type": "api_optional",
        "url": "https://tradingeconomics.com",
        "description_ar": "مؤشرات اقتصادية كلية: GDP بالتفصيل، تضخم، بطالة، ميزان تجاري",
    },
    "bahrain_bourse": {
        "name_ar": "بورصة البحرين",
        "name_en": "Bahrain Bourse",
        "icon": "\U0001f4ca",
        "type": "embedded",
        "url": "https://bahrainbourse.com",
        "description_ar": "الشركات المدرجة والقيمة السوقية وبيانات القطاعات",
    },
    "tamkeen": {
        "name_ar": "تمكين (صندوق العمل)",
        "name_en": "Tamkeen",
        "icon": "\U0001f91d",
        "type": "embedded",
        "url": "https://tamkeen.bh",
        "description_ar": "برامج دعم المؤسسات: دعم رواتب، تدريب، تحول رقمي، سجلي",
    },
    "edb": {
        "name_ar": "مجلس التنمية الاقتصادية",
        "name_en": "EDB",
        "icon": "\U0001f3e2",
        "type": "embedded",
        "url": "https://bahrainedb.com",
        "description_ar": "نظرة عامة اقتصادية، قطاعات التركيز، حوافز الاستثمار",
    },
    "datagov": {
        "name_ar": "بوابة البيانات المفتوحة",
        "name_en": "Bahrain Open Data",
        "icon": "\U0001f4ca",
        "type": "api",
        "url": "https://data.gov.bh",
        "description_ar": "بيانات حكومية: سكان، صادرات، سياحة، تراخيص، بطالة، أجور، شحن جوي",
    },
    "google_trends": {
        "name_ar": "اتجاهات البحث",
        "name_en": "Google Trends",
        "icon": "\U0001f50d",
        "type": "api_optional",
        "url": "https://trends.google.com",
        "description_ar": "اتجاهات البحث في البحرين: مؤشر الطلب الرقمي وكلمات البحث الصاعدة",
    },
    "job_market": {
        "name_ar": "سوق الوظائف",
        "name_en": "Job Market",
        "icon": "\U0001f4bc",
        "type": "api_optional",
        "url": "https://linkedin.com",
        "description_ar": "مؤشرات التوظيف: إعلانات وظائف، شركات توظف، مسميات وظيفية",
    },
    "imf": {
        "name_ar": "صندوق النقد الدولي",
        "name_en": "IMF",
        "icon": "\U0001f3e6",
        "type": "api",
        "url": "https://www.imf.org/external/datamapper",
        "description_ar": "توقعات اقتصادية: نمو GDP المتوقع، التضخم، الدين الحكومي، ميزان الحساب الجاري",
    },
    "comtrade": {
        "name_ar": "التجارة الدولية (UN)",
        "name_en": "UN Comtrade",
        "icon": "\U0001f6a2",
        "type": "embedded",
        "url": "https://comtrade.un.org",
        "description_ar": "صادرات وواردات البحرين المفصلة حسب المنتج والشريك التجاري",
    },
    "numbeo": {
        "name_ar": "تكاليف المعيشة والتشغيل",
        "name_en": "Numbeo",
        "icon": "\U0001f4b0",
        "type": "embedded",
        "url": "https://www.numbeo.com",
        "description_ar": "تكاليف حقيقية: إيجارات مكاتب، رواتب، مرافق، تكاليف تأسيس",
    },
    "wto": {
        "name_ar": "منظمة التجارة العالمية",
        "name_en": "WTO",
        "icon": "\U0001f310",
        "type": "embedded",
        "url": "https://www.wto.org",
        "description_ar": "اتفاقيات تجارة حرة، تعريفات جمركية، تسهيلات تجارية",
    },
    "gccstat": {
        "name_ar": "مقارنة خليجية",
        "name_en": "GCC-Stat",
        "icon": "\U0001f30d",
        "type": "embedded",
        "url": "https://gccstat.org",
        "description_ar": "مقارنة البحرين بدول الخليج: GDP، سكان، بطالة، سهولة أعمال",
    },
    "itu": {
        "name_ar": "البنية التحتية الرقمية",
        "name_en": "ITU DataHub",
        "icon": "\U0001f4f6",
        "type": "embedded",
        "url": "https://datahub.itu.int",
        "description_ar": "مؤشرات رقمية: إنترنت، 5G، نطاق عريض، تجارة إلكترونية، بنية تحتية",
    },
}

# Agent-to-source mapping: which sources are primary/secondary for each agent
AGENT_SOURCE_MAP = {
    "market": {
        "primary": ["trading_economics", "edb", "sijilat", "google_trends", "imf", "comtrade"],
        "secondary": ["world_bank", "datagov", "job_market", "gccstat"],
    },
    "financial": {
        "primary": ["cbb", "tamkeen", "world_bank", "numbeo", "imf"],
        "secondary": ["bahrain_bourse", "datagov"],
    },
    "competitive": {
        "primary": ["sijilat", "job_market", "comtrade"],
        "secondary": ["bahrain_bourse", "google_trends", "gccstat"],
    },
    "legal": {
        "primary": ["tamkeen", "wto"],
        "secondary": ["sijilat", "datagov"],
    },
    "technical": {
        "primary": ["world_bank", "google_trends", "itu"],
        "secondary": ["tamkeen", "edb"],
    },
    "brokerage_models": {
        "primary": ["sijilat", "edb", "job_market", "comtrade"],
        "secondary": ["google_trends", "datagov", "gccstat"],
    },
    "gap_analysis": {
        "primary": ["trading_economics", "sijilat", "google_trends", "job_market", "datagov", "comtrade", "imf"],
        "secondary": ["world_bank", "cbb", "tamkeen", "edb", "bahrain_bourse", "gccstat", "numbeo", "wto", "itu"],
    },
}


class DataAggregator:
    """Coordinates data fetching from all sources and builds context for agents."""

    def __init__(self):
        self.sources = {
            "world_bank": WorldBankSource(),
            "cbb": CBBSource(),
            "sijilat": SijilatSource(),
            "trading_economics": TradingEconomicsSource(),
            "bahrain_bourse": BahrainBourseSource(),
            "tamkeen": TamkeenSource(),
            "edb": EDBSource(),
            "datagov": DataGovSource(),
            "google_trends": GoogleTrendsSource(),
            "job_market": JobMarketSource(),
            "imf": IMFSource(),
            "comtrade": ComtradeSource(),
            "numbeo": NumbeoSource(),
            "wto": WTOSource(),
            "gccstat": GCCStatSource(),
            "itu": ITUSource(),
        }
        # Simple in-memory cache
        self._cache = {}

    def build_data_attribution(self, aggregated_data: dict) -> dict:
        """Build a summary of which data sources contributed to each agent."""
        agent_names_ar = {
            "market": "تحليل السوق",
            "financial": "التحليل المالي",
            "competitive": "تحليل المنافسة",
            "legal": "التحليل القانوني",
            "technical": "التحليل التقني",
            "brokerage_models": "نماذج الوساطة",
        }
        agents = {}
        total_points = 0
        active_sources = set()

        for agent_type, mapping in AGENT_SOURCE_MAP.items():
            sources_used = []
            for role in ("primary", "secondary"):
                for src_name in mapping[role]:
                    data = aggregated_data.get(src_name, {})
                    has_error = bool(data.get("error"))
                    dp = data.get("data_points", 0) if not has_error else 0
                    meta = SOURCE_META.get(src_name, {})
                    if not has_error and dp > 0:
                        active_sources.add(src_name)
                    sources_used.append({
                        "key": src_name,
                        "name_ar": meta.get("name_ar", src_name),
                        "icon": meta.get("icon", ""),
                        "role": role,
                        "data_points": dp,
                        "status": "error" if has_error else ("active" if dp > 0 else "empty"),
                    })
            agent_points = sum(s["data_points"] for s in sources_used)
            total_points += agent_points
            agents[agent_type] = {
                "name_ar": agent_names_ar.get(agent_type, agent_type),
                "sources": sources_used,
                "total_points": agent_points,
            }

        return {
            "agents": agents,
            "total_data_points": sum(d.get("data_points", 0) for d in aggregated_data.values() if not d.get("error")),
            "active_sources": len(active_sources),
            "total_sources": len(self.sources),
        }

    def get_sources_meta(self) -> dict:
        """Return metadata about all data sources (for the dashboard UI)."""
        # Invert AGENT_SOURCE_MAP: source -> list of agents that use it
        source_agents = {}
        for agent, mapping in AGENT_SOURCE_MAP.items():
            for src in mapping["primary"] + mapping["secondary"]:
                source_agents.setdefault(src, []).append(agent)

        sources = []
        for key, source in self.sources.items():
            meta = SOURCE_META.get(key, {})
            sources.append({
                "key": key,
                "name_ar": meta.get("name_ar", key),
                "name_en": meta.get("name_en", key),
                "icon": meta.get("icon", ""),
                "type": meta.get("type", "unknown"),
                "url": meta.get("url", ""),
                "description_ar": meta.get("description_ar", ""),
                "reliability": source.reliability_score,
                "cache_ttl": source.cache_ttl_seconds,
                "agents": source_agents.get(key, []),
            })

        return {
            "sources": sources,
            "agent_source_map": AGENT_SOURCE_MAP,
        }

    async def fetch_all(self, sector: str) -> dict:
        """Fetch data from all sources in parallel. Returns dict keyed by source_name."""
        start = time.time()
        logger.info(f"📊 DataAggregator: بدء جلب البيانات لقطاع '{sector}'")

        # Check in-memory cache
        cache_key = f"all:{sector}"
        cached = self._cache.get(cache_key)
        if cached and (time.time() - cached["ts"]) < 3600:  # 1-hour in-memory TTL
            logger.info(f"📊 DataAggregator: استخدام الكاش (عمره {int(time.time() - cached['ts'])} ثانية)")
            return cached["data"]

        tasks = {}
        for name, source in self.sources.items():
            tasks[name] = source.fetch(sector)

        # Gather with return_exceptions=True for graceful degradation
        results_list = await asyncio.gather(
            *tasks.values(),
            return_exceptions=True
        )

        results = {}
        source_names = list(tasks.keys())
        for i, result in enumerate(results_list):
            name = source_names[i]
            if isinstance(result, Exception):
                logger.warning(f"⚠️ مصدر '{name}' فشل: {type(result).__name__}: {result}")
                results[name] = {"source": name, "error": str(result), "data_points": 0}
            else:
                results[name] = result
                dp = result.get("data_points", 0)
                logger.info(f"✅ مصدر '{name}': {dp} نقطة بيانات")

        elapsed = time.time() - start
        total_points = sum(r.get("data_points", 0) for r in results.values())
        logger.info(f"📊 DataAggregator: انتهى في {elapsed:.1f}s | {total_points} نقطة بيانات من {len(results)} مصدر")

        # Cache the results
        self._cache[cache_key] = {"data": results, "ts": time.time()}

        return results

    def _build_cross_source_summary(self, sector: str, data: dict) -> str:
        """Build an interconnected summary from all sources for market need detection."""
        parts = []

        # ── Market Size ──
        te = data.get("trading_economics", {})
        sj = data.get("sijilat", {})
        bo = data.get("bahrain_bourse", {})
        market = []
        if te and not te.get("error"):
            gdp_info = te.get("sector_gdp", {})
            if gdp_info and gdp_info.get("contribution") != "غير متوفر":
                market.append(f"مساهمة القطاع في GDP: {gdp_info['contribution']}")
            macro = te.get("macro", {})
            gdp_val = macro.get("gdp", {})
            if gdp_val:
                market.append(f"إجمالي GDP البحرين: {gdp_val.get('value', 'N/A')} ({gdp_val.get('year', '')})")
        if sj and not sj.get("error"):
            total = sj.get("total_registered", 0)
            active = sj.get("active_companies", 0)
            annual = sj.get("annual_new_registrations", 0)
            if total:
                market.append(f"شركات مسجلة في القطاع: ~{total:,} (نشطة: ~{active:,})")
            if annual:
                market.append(f"تسجيلات جديدة سنوياً: ~{annual}")
        if bo and not bo.get("error"):
            sd = bo.get("sector_data")
            if sd:
                market.append(f"شركات مدرجة في البورصة: {sd.get('listed_companies', 'N/A')} (قيمة سوقية: {sd.get('market_cap_approx', 'N/A')})")
        if market:
            parts.append("📊 حجم السوق والعرض:\n" + "\n".join(f"  - {m}" for m in market))

        # ── Business Environment ──
        cb = data.get("cbb", {})
        tk = data.get("tamkeen", {})
        ed = data.get("edb", {})
        env = []
        if cb and not cb.get("error"):
            cbb_data = cb.get("data", {})
            ir = cbb_data.get("interest_rate", {})
            if ir:
                env.append(f"فائدة الإقراض: {ir.get('overnight_lending', 'N/A')} | فائدة الإيداع: {ir.get('overnight_deposit', 'N/A')}")
        if tk and not tk.get("error"):
            progs = tk.get("programs", {})
            if progs:
                prog_names = [p.get("name_ar", k) for k, p in progs.items()]
                env.append(f"برامج دعم تمكين المتاحة: {', '.join(prog_names)}")
            sijilli = tk.get("sijilli", {})
            if sijilli:
                env.append(f"سجلي: {sijilli.get('total_activities', 71)} نشاط متاح برسوم {sijilli.get('annual_fee', '50 د.ب')}/سنة")
        if ed and not ed.get("error"):
            incentives = ed.get("investment_incentives", {})
            if incentives:
                env.append(f"حوافز: {incentives.get('tax_free', '')} | ضريبة قيمة مضافة: {incentives.get('vat', '')} | تأسيس: {incentives.get('company_setup', '')}")
        if env:
            parts.append("🏢 بيئة الأعمال:\n" + "\n".join(f"  - {e}" for e in env))

        # ── Growth Indicators ──
        wb = data.get("world_bank", {})
        growth = []
        if wb and not wb.get("error"):
            indicators = wb.get("indicators", {})
            gdp_growth = indicators.get("NY.GDP.MKTP.KD.ZG", {})
            pts = gdp_growth.get("data", [])
            if pts:
                latest = pts[0]
                growth.append(f"نمو GDP الحقيقي: {latest['value']}% ({latest['year']})")
                if len(pts) >= 3:
                    vals = [p["value"] for p in pts[:3] if p["value"] is not None]
                    if vals:
                        avg = sum(vals) / len(vals)
                        growth.append(f"متوسط نمو (3 سنوات): {avg:.1f}%")
            inflation = indicators.get("FP.CPI.TOTL.ZG", {})
            inf_pts = inflation.get("data", [])
            if inf_pts:
                growth.append(f"التضخم: {inf_pts[0]['value']}% ({inf_pts[0]['year']})")
        if te and not te.get("error"):
            macro = te.get("macro", {})
            unemp = macro.get("unemployment", {})
            if unemp:
                growth.append(f"البطالة: {unemp.get('value', 'N/A')} ({unemp.get('year', '')})")
        # IMF forecasts
        imf = data.get("imf", {})
        if imf and not imf.get("error"):
            forecast = imf.get("forecast_summary", {})
            avg_gdp = forecast.get("avg_gdp_growth_2025_2029")
            if avg_gdp:
                growth.append(f"متوسط نمو GDP المتوقع (2025-2029): {avg_gdp}% (المصدر: IMF)")
            debt = forecast.get("latest_debt_gdp")
            if debt:
                growth.append(f"الدين الحكومي: {debt['value']}% من GDP ({debt['year']}) (المصدر: IMF)")

        if growth:
            parts.append("📈 مؤشرات النمو:\n" + "\n".join(f"  - {g}" for g in growth))

        # ── Trade Context ──
        ct = data.get("comtrade", {})
        if ct and not ct.get("error"):
            trade = []
            overview = ct.get("trade_overview", {})
            imp = overview.get("total_imports_2023", {})
            if imp:
                trade.append(f"إجمالي واردات البحرين: ${imp.get('value_usd', 0)/1e9:.1f} مليار")
            sector_imports = ct.get("sector_relevant_imports", [])
            if sector_imports:
                for s in sector_imports[:2]:
                    trade.append(f"واردات {s['sector']}: ${s['value_usd']/1e6:.0f} مليون ({s['share_pct']}% من الواردات)")
            if trade:
                parts.append("🚢 سياق التجارة الدولية:\n" + "\n".join(f"  - {t}" for t in trade))

        # ── Market Opportunities ──
        opps = []
        if ed and not ed.get("error"):
            for name, details in ed.get("sector_details", {}).items():
                highlights = details.get("highlights", [])
                for h in highlights[:2]:
                    opps.append(h)
        if sj and not sj.get("error"):
            annual = sj.get("annual_new_registrations", 0)
            total = sj.get("total_registered", 0)
            if annual and total and total > 0:
                growth_rate = (annual / total) * 100
                if growth_rate > 5:
                    opps.append(f"نمو سريع في التسجيلات ({growth_rate:.0f}% سنوياً) يشير لطلب متزايد")
                elif growth_rate < 2:
                    opps.append(f"تباطؤ في التسجيلات الجديدة ({growth_rate:.0f}%) قد يشير لتشبع أو فرصة لتمايز")

        # Google Trends signals
        gt = data.get("google_trends", {})
        if gt and not gt.get("error") and gt.get("trends"):
            rising_terms = [t for t, info in gt["trends"].items() if info.get("trend") == "rising"]
            if rising_terms:
                opps.append(f"اهتمام رقمي متزايد: {', '.join(rising_terms[:3])}")

        # Job market signals
        jm = data.get("job_market", {})
        if jm and not jm.get("error") and jm.get("demand_signal") == "high":
            opps.append(f"طلب توظيف مرتفع ({jm.get('total_results', 0)} إعلان) يشير لنمو القطاع")

        if opps:
            parts.append("🎯 مؤشرات فرص السوق:\n" + "\n".join(f"  - {o}" for o in opps))

        if not parts:
            return ""
        return "══ ملخص مترابط من جميع المصادر ══\n" + "\n\n".join(parts) + "\n══ نهاية الملخص ══"

    def build_agent_context(self, sector: str, agent_type: str, aggregated_data: dict) -> str:
        """Build a context string tailored for a specific agent type."""
        source_map = AGENT_SOURCE_MAP.get(agent_type, {"primary": [], "secondary": []})
        primary_sources = source_map["primary"]
        secondary_sources = source_map["secondary"]

        sections = []

        # Add cross-source summary first
        cross_summary = self._build_cross_source_summary(sector, aggregated_data)
        if cross_summary:
            sections.append("\n" + cross_summary)

        sections.append("\n══ بيانات إضافية من مصادر متعددة ══")

        # Primary sources
        for src_name in primary_sources:
            data = aggregated_data.get(src_name)
            if data and not data.get("error"):
                section = self._format_source_data(src_name, data, agent_type)
                if section:
                    sections.append(section)

        # Secondary sources
        for src_name in secondary_sources:
            data = aggregated_data.get(src_name)
            if data and not data.get("error"):
                section = self._format_source_data(src_name, data, agent_type)
                if section:
                    sections.append(section)

        if len(sections) <= 1:
            return ""

        sections.append("══ نهاية البيانات الإضافية ══\n")
        return "\n".join(sections)

    def _format_source_data(self, source_name: str, data: dict, agent_type: str) -> str:
        """Format source data into a readable context string for agents."""
        formatters = {
            "world_bank": self._format_worldbank,
            "cbb": self._format_cbb,
            "sijilat": self._format_sijilat,
            "trading_economics": self._format_trading_economics,
            "bahrain_bourse": self._format_bourse,
            "tamkeen": self._format_tamkeen,
            "edb": self._format_edb,
            "datagov": self._format_datagov,
            "google_trends": self._format_google_trends,
            "job_market": self._format_job_market,
            "imf": self._format_imf,
            "comtrade": self._format_comtrade,
            "numbeo": self._format_numbeo,
            "wto": self._format_wto,
            "gccstat": self._format_gccstat,
            "itu": self._format_itu,
        }

        formatter = formatters.get(source_name)
        if formatter:
            return formatter(data, agent_type)
        return ""

    def _format_worldbank(self, data: dict, agent_type: str) -> str:
        indicators = data.get("indicators", {})
        if not indicators:
            return ""

        lines = [f"── البنك الدولي (موثوقية: {data.get('reliability', 0.95)}) ──"]
        for ind_id, ind_data in indicators.items():
            name = ind_data.get("name", ind_id)
            points = ind_data.get("data", [])
            unit = ind_data.get("unit", "")
            if points:
                latest = points[0]
                lines.append(f"• {name}: {latest['value']}{unit} ({latest['year']})")
                if len(points) > 1:
                    prev = points[1]
                    lines.append(f"  العام السابق: {prev['value']}{unit} ({prev['year']})")
        return "\n".join(lines)

    def _format_cbb(self, data: dict, agent_type: str) -> str:
        cbb_data = data.get("data", {})
        if not cbb_data:
            return ""

        lines = [f"── مصرف البحرين المركزي (موثوقية: {data.get('reliability', 0.9)}) ──"]

        ex = cbb_data.get("exchange_rates", {})
        if ex:
            lines.append(f"• سعر الصرف: 1 BHD = {1/float(ex.get('BHD_to_USD', 0.377)):.4f} USD")
            if ex.get("note"):
                lines.append(f"  {ex['note']}")

        ir = cbb_data.get("interest_rate", {})
        if ir:
            lines.append(f"• فائدة الإيداع لليلة واحدة: {ir.get('overnight_deposit', 'N/A')}")
            lines.append(f"• فائدة الإقراض لليلة واحدة: {ir.get('overnight_lending', 'N/A')}")

        return "\n".join(lines)

    def _format_sijilat(self, data: dict, agent_type: str) -> str:
        lines = [f"── سجلات تجارية - Sijilat (موثوقية: {data.get('reliability', 0.7)}) ──"]

        total = data.get("total_registered", 0)
        active = data.get("active_companies", 0)
        annual_new = data.get("annual_new_registrations", 0)

        if total:
            lines.append(f"• إجمالي الشركات المسجلة: ~{total:,}")
        if active:
            lines.append(f"• الشركات النشطة: ~{active:,}")
        if annual_new:
            lines.append(f"• تسجيلات جديدة سنوياً: ~{annual_new}")

        activities = data.get("activities", {})
        if activities:
            lines.append("• الأنشطة المرتبطة:")
            for act, info in list(activities.items())[:5]:
                count = info.get("registered_count", "غير محدد")
                lines.append(f"  - {act}: {count}")

        is_live = data.get("is_live", False)
        if not is_live:
            lines.append(f"  ⚠ {data.get('note', 'بيانات تقديرية')}")

        return "\n".join(lines)

    def _format_trading_economics(self, data: dict, agent_type: str) -> str:
        lines = [f"── مؤشرات اقتصادية كلية (موثوقية: {data.get('reliability', 0.85)}) ──"]

        macro = data.get("macro", {})
        if macro:
            key_indicators = ["gdp", "gdp_growth", "inflation", "unemployment", "population"]
            labels = {
                "gdp": "الناتج المحلي",
                "gdp_growth": "نمو GDP",
                "inflation": "التضخم",
                "unemployment": "البطالة",
                "population": "السكان",
            }
            for key in key_indicators:
                if key in macro:
                    label = labels.get(key, key)
                    val = macro[key]
                    lines.append(f"• {label}: {val['value']} ({val['year']})")

        sector_gdp = data.get("sector_gdp", {})
        if sector_gdp and sector_gdp.get("contribution") != "غير متوفر":
            lines.append(f"• مساهمة القطاع في GDP: {sector_gdp['contribution']}")
            if sector_gdp.get("note"):
                lines.append(f"  ({sector_gdp['note']})")

        return "\n".join(lines)

    def _format_bourse(self, data: dict, agent_type: str) -> str:
        sector_data = data.get("sector_data")
        overview = data.get("overview", {})

        lines = [f"── بورصة البحرين (موثوقية: {data.get('reliability', 0.85)}) ──"]
        lines.append(f"• إجمالي الشركات المدرجة: {overview.get('total_listed', 'N/A')}")
        lines.append(f"• القيمة السوقية الإجمالية: {overview.get('market_cap_total', 'N/A')}")
        lines.append(f"• الملكية الأجنبية: {'مسموحة' if overview.get('foreign_ownership_allowed') else 'مقيدة'}")

        if sector_data:
            lines.append(f"• قطاع {sector_data.get('name_ar', '')}:")
            lines.append(f"  - شركات مدرجة: {sector_data.get('listed_companies', 0)}")
            lines.append(f"  - القيمة السوقية: {sector_data.get('market_cap_approx', 'N/A')}")
            if sector_data.get("major_companies"):
                lines.append(f"  - أبرز الشركات: {', '.join(sector_data['major_companies'][:3])}")

        return "\n".join(lines)

    def _format_tamkeen(self, data: dict, agent_type: str) -> str:
        lines = [f"── تمكين (صندوق العمل) (موثوقية: {data.get('reliability', 0.8)}) ──"]

        programs = data.get("programs", {})
        if programs:
            lines.append("• برامج الدعم المتاحة:")
            for key, prog in programs.items():
                lines.append(f"  - {prog['name_ar']}: {prog.get('description', '')}")
                if prog.get("max_support"):
                    lines.append(f"    الحد الأقصى: {prog['max_support']}")
                if prog.get("coverage"):
                    lines.append(f"    التغطية: {prog['coverage']}")

        sijilli = data.get("sijilli", {})
        if sijilli:
            lines.append(f"• {sijilli.get('name_ar', 'سجلي')}:")
            lines.append(f"  - {sijilli.get('description', '')}")
            lines.append(f"  - الرسوم السنوية: {sijilli.get('annual_fee', '50 د.ب')}")
            lines.append(f"  - عدد الأنشطة المتاحة: {sijilli.get('total_activities', 71)}")

        return "\n".join(lines)

    def _format_edb(self, data: dict, agent_type: str) -> str:
        lines = [f"── مجلس التنمية الاقتصادية (موثوقية: {data.get('reliability', 0.8)}) ──"]

        overview = data.get("overview", {})
        if overview:
            lines.append(f"• GDP: {overview.get('gdp_2023', 'N/A')} (نمو {overview.get('gdp_growth_2023', 'N/A')})")
            lines.append(f"• السكان: {overview.get('population', 'N/A')}")
            lines.append(f"• الإنترنت: {overview.get('internet_penetration', 'N/A')}")

        sector_details = data.get("sector_details", {})
        for name, details in sector_details.items():
            lines.append(f"• {details.get('name_ar', name)}:")
            if details.get("contribution_gdp"):
                lines.append(f"  - مساهمة في GDP: {details['contribution_gdp']}")
            if details.get("companies"):
                lines.append(f"  - عدد الشركات: {details['companies']}")
            if details.get("highlights"):
                for h in details["highlights"][:2]:
                    lines.append(f"  - {h}")

        incentives = data.get("investment_incentives", {})
        if incentives and agent_type in ("financial", "legal"):
            lines.append("• حوافز الاستثمار:")
            lines.append(f"  - {incentives.get('tax_free', '')}")
            lines.append(f"  - ضريبة القيمة المضافة: {incentives.get('vat', '')}")
            lines.append(f"  - تأسيس شركة: {incentives.get('company_setup', '')}")

        return "\n".join(lines)

    def _format_datagov(self, data: dict, agent_type: str) -> str:
        datasets = data.get("datasets", {})
        if not datasets:
            return ""

        lines = [f"── بوابة البيانات المفتوحة (موثوقية: {data.get('reliability', 0.9)}) ──"]

        for key, ds in datasets.items():
            name = ds.get("name_ar", key)
            summary = ds.get("summary", {})
            count = ds.get("record_count", 0)
            lines.append(f"• {name} ({count} سجل):")

            if key == "population" and summary.get("total"):
                lines.append(f"  - إجمالي السكان: {summary['total']:,}")
                for gov, pop in list(summary.get("by_governorate", {}).items())[:4]:
                    lines.append(f"    {gov}: {pop:,}")
            elif key == "unemployment" and summary.get("rate"):
                lines.append(f"  - معدل البطالة: {summary['rate']}% ({summary.get('year', '')})")
            elif key == "exports" and summary.get("top_exports"):
                for exp in summary["top_exports"][:3]:
                    lines.append(f"  - {exp['commodity']}: {exp['value_bd']} د.ب")
            elif key == "tourism_spending" and summary.get("avg_spending"):
                lines.append(f"  - متوسط إنفاق الزائر: {summary['avg_spending']} ({summary.get('year', '')})")
            elif key == "gdp_quarterly" and summary.get("growth_rate"):
                lines.append(f"  - نمو فصلي: {summary['growth_rate']}% (Q{summary.get('quarter', '')} {summary.get('year', '')})")
            elif key == "air_cargo" and summary.get("tonnage"):
                lines.append(f"  - حجم الشحن: {summary['tonnage']} ({summary.get('year', '')}/{summary.get('month', '')})")

        return "\n".join(lines)

    def _format_google_trends(self, data: dict, agent_type: str) -> str:
        trends = data.get("trends", {})
        if not trends and not data.get("is_live"):
            return ""

        lines = [f"── اتجاهات البحث Google Trends (موثوقية: {data.get('reliability', 0.65)}) ──"]

        if trends:
            for term, info in trends.items():
                trend_ar = {"rising": "↗ صاعد", "declining": "↘ هابط", "stable": "→ مستقر"}.get(info["trend"], info["trend"])
                lines.append(f"• \"{term}\": {trend_ar} (اهتمام حالي: {info['recent_interest']}/100)")

        related = data.get("related_queries", {})
        if related:
            lines.append("• عمليات بحث صاعدة:")
            for term, queries in list(related.items())[:2]:
                for q in queries[:3]:
                    lines.append(f"  - {q}")
        elif not trends:
            lines.append(f"• كلمات البحث المقترحة: {', '.join(data.get('search_terms', [])[:3])}")
            lines.append("  ⚠ لم يتم جلب بيانات حية (pytrends غير متوفر)")

        return "\n".join(lines)

    def _format_job_market(self, data: dict, agent_type: str) -> str:
        total = data.get("total_results", 0)
        if total == 0 and not data.get("is_live"):
            return ""

        lines = [f"── سوق الوظائف (موثوقية: {data.get('reliability', 0.6)}) ──"]

        demand = data.get("demand_signal", "unknown")
        demand_ar = {"high": "طلب مرتفع", "medium": "طلب متوسط", "low": "طلب منخفض"}.get(demand, "غير معروف")
        lines.append(f"• مستوى الطلب: {demand_ar} ({total} إعلان وظيفي)")

        titles = data.get("sample_job_titles", [])
        if titles:
            lines.append(f"• مسميات وظيفية رائجة: {', '.join(titles[:5])}")

        companies = data.get("hiring_companies", [])
        if companies:
            lines.append(f"• شركات توظف: {', '.join(companies[:5])}")

        return "\n".join(lines)

    # ── New data source formatters ──

    def _format_imf(self, data: dict, agent_type: str) -> str:
        indicators = data.get("indicators", {})
        if not indicators:
            return ""

        lines = [f"── صندوق النقد الدولي - توقعات (موثوقية: {data.get('reliability', 0.9)}) ──"]
        for ind_id, ind_data in indicators.items():
            name = ind_data.get("name", ind_id)
            points = ind_data.get("data", {})
            if points:
                # Show forecast years (2025+)
                forecast = {k: v for k, v in points.items() if int(k) >= 2025}
                historical = {k: v for k, v in points.items() if int(k) < 2025}
                if historical:
                    latest_year = max(historical.keys())
                    lines.append(f"• {name}: {historical[latest_year]} ({latest_year})")
                if forecast:
                    vals = ", ".join(f"{y}: {v}" for y, v in list(forecast.items())[:3])
                    lines.append(f"  توقعات: {vals}")

        summary = data.get("forecast_summary", {})
        avg = summary.get("avg_gdp_growth_2025_2029")
        if avg:
            lines.append(f"• متوسط نمو GDP المتوقع (2025-2029): {avg}%")

        debt = summary.get("latest_debt_gdp")
        if debt:
            lines.append(f"• الدين الحكومي: {debt['value']}% من GDP ({debt['year']})")

        return "\n".join(lines)

    def _format_comtrade(self, data: dict, agent_type: str) -> str:
        lines = [f"── التجارة الدولية UN Comtrade (موثوقية: {data.get('reliability', 0.8)}) ──"]

        overview = data.get("trade_overview", {})
        if overview:
            imp = overview.get("total_imports_2023", {})
            exp = overview.get("total_exports_2023", {})
            if imp:
                lines.append(f"• إجمالي الواردات: ${imp.get('value_usd', 0)/1e9:.1f} مليار ({imp.get('year', '')})")
            if exp:
                lines.append(f"• إجمالي الصادرات: ${exp.get('value_usd', 0)/1e9:.1f} مليار ({exp.get('year', '')})")

        partners = overview.get("top_import_partners", [])
        if partners:
            top3 = ", ".join(f"{p['country']} ({p['share_pct']}%)" for p in partners[:3])
            lines.append(f"• أهم شركاء الاستيراد: {top3}")

        # Sector-specific trade
        sector_imports = data.get("sector_relevant_imports", [])
        if sector_imports:
            lines.append("• واردات ذات صلة بالقطاع:")
            for s in sector_imports[:3]:
                lines.append(f"  - {s['sector']}: ${s['value_usd']/1e6:.0f} مليون ({s['share_pct']}%)")

        sector_exports = data.get("sector_relevant_exports", [])
        if sector_exports:
            lines.append("• صادرات ذات صلة بالقطاع:")
            for s in sector_exports[:3]:
                lines.append(f"  - {s['sector']}: ${s['value_usd']/1e6:.0f} مليون ({s['share_pct']}%)")

        return "\n".join(lines)

    def _format_numbeo(self, data: dict, agent_type: str) -> str:
        costs = data.get("cost_data", data.get("costs", {}))
        if not costs:
            return ""

        lines = [f"── تكاليف المعيشة والتشغيل - Numbeo (موثوقية: {data.get('reliability', 0.75)}) ──"]

        office = costs.get("office_rent", {})
        if office:
            lines.append(f"• إيجار مكتب 50م² وسط المدينة: {office.get('small_office_50sqm_center', 'N/A')} د.ب/شهر")
            lines.append(f"• مكتب مشترك (coworking): {office.get('coworking_desk_monthly', 'N/A')} د.ب/شهر")

        salaries = costs.get("salaries", {})
        if salaries:
            lines.append(f"• متوسط الراتب الشهري: {salaries.get('avg_monthly_salary_net', 'N/A')} د.ب")
            lines.append(f"• الحد الأدنى للأجور (بحريني): {salaries.get('min_wage_bahraini', 'N/A')} د.ب")
            if agent_type == "financial":
                for role in ["software_developer", "marketing_manager", "accountant", "sales_representative", "office_admin"]:
                    if role in salaries:
                        label = role.replace("_", " ").title()
                        lines.append(f"  - {label}: {salaries[role]} د.ب/شهر")

        utilities = costs.get("utilities", {})
        if utilities:
            lines.append(f"• كهرباء ومياه (85م²): {utilities.get('electricity_water_monthly_85sqm', 'N/A')} د.ب/شهر")
            lines.append(f"• إنترنت 60Mbps: {utilities.get('internet_60mbps_monthly', 'N/A')} د.ب/شهر")

        biz = costs.get("business_costs", {})
        if biz and agent_type in ("financial", "legal"):
            lines.append(f"• رسوم السجل التجاري: {biz.get('commercial_registration_fee', 'N/A')} د.ب")
            lines.append(f"• تأسيس شركة WLL: ~{biz.get('company_formation_wll', 'N/A')} د.ب")
            lines.append(f"• تصريح عمل (وافد): {biz.get('work_permit_expat', 'N/A')} د.ب/سنة")

        idx = costs.get("cost_of_living_index", {})
        if idx:
            lines.append(f"• مؤشر تكاليف المعيشة: {idx.get('bahrain_index', 'N/A')} (نيويورك = 100)")
            lines.append(f"• القوة الشرائية: {idx.get('purchasing_power_index', 'N/A')}")

        return "\n".join(lines)

    def _format_wto(self, data: dict, agent_type: str) -> str:
        lines = [f"── منظمة التجارة العالمية (موثوقية: {data.get('reliability', 0.8)}) ──"]

        agreements = data.get("trade_agreements", [])
        if agreements:
            lines.append("• اتفاقيات التجارة الحرة:")
            for a in agreements[:4]:
                lines.append(f"  - {a.get('name', '')}: {a.get('impact', '')}")

        tariff = data.get("tariff_overview", {})
        if tariff:
            lines.append(f"• متوسط التعريفة الجمركية: {tariff.get('avg_applied_tariff_pct', 'N/A')}%")
            lines.append(f"• بنود معفاة من الرسوم: {tariff.get('duty_free_lines_pct', 'N/A')}%")
            lines.append(f"• ضريبة القيمة المضافة: {tariff.get('vat_rate_pct', 'N/A')}%")

        facilitation = data.get("trade_facilitation", {})
        if facilitation:
            lines.append(f"• زمن الاستيراد: {facilitation.get('time_to_import_days', 'N/A')} أيام")
            lines.append(f"• زمن التصدير: {facilitation.get('time_to_export_days', 'N/A')} أيام")

        bit = data.get("bilateral_investment_treaties")
        dta = data.get("double_taxation_agreements")
        if bit:
            lines.append(f"• اتفاقيات حماية الاستثمار: {bit} اتفاقية")
        if dta:
            lines.append(f"• اتفاقيات تجنب الازدواج الضريبي: {dta} اتفاقية")

        return "\n".join(lines)

    def _format_gccstat(self, data: dict, agent_type: str) -> str:
        countries = data.get("gcc_comparison", data.get("countries", {}))
        if not countries:
            return ""

        lines = [f"── مقارنة خليجية GCC-Stat (موثوقية: {data.get('reliability', 0.75)}) ──"]

        bhr = countries.get("البحرين", {})
        if bhr:
            lines.append(f"• البحرين: GDP ${bhr.get('gdp_billion_usd', 'N/A')}B | سكان {bhr.get('population_million', 'N/A')}M | بطالة {bhr.get('unemployment_pct', 'N/A')}%")

        # Comparison with key competitors
        for name in ["الإمارات", "السعودية"]:
            c = countries.get(name, {})
            if c:
                lines.append(f"• {name}: GDP ${c.get('gdp_billion_usd', 'N/A')}B | سكان {c.get('population_million', 'N/A')}M | بطالة {c.get('unemployment_pct', 'N/A')}%")

        advantages = data.get("bahrain_advantages", [])
        if advantages:
            lines.append("• مزايا البحرين الخليجية:")
            for a in advantages[:3]:
                lines.append(f"  - {a}")

        challenges = data.get("bahrain_challenges", [])
        if challenges:
            lines.append("• تحديات:")
            for c in challenges[:2]:
                lines.append(f"  - {c}")

        return "\n".join(lines)

    def _format_itu(self, data: dict, agent_type: str) -> str:
        lines = [f"── البنية التحتية الرقمية ITU (موثوقية: {data.get('reliability', 0.8)}) ──"]

        broadband = data.get("broadband", {})
        if broadband:
            lines.append(f"• سرعة التحميل: {broadband.get('avg_download_speed_mbps', 'N/A')} Mbps")
            lines.append(f"• تغطية الألياف الضوئية: {broadband.get('fiber_coverage_pct', 'N/A')}%")

        mobile = data.get("mobile", {})
        if mobile:
            lines.append(f"• تغطية 5G: {mobile.get('5g_coverage_pct', 'N/A')}%")
            lines.append(f"• انتشار الهواتف الذكية: {mobile.get('smartphone_penetration_pct', 'N/A')}%")

        internet = data.get("internet", {})
        if internet:
            lines.append(f"• مستخدمو الإنترنت: {internet.get('internet_users_pct', 'N/A')}%")
            lines.append(f"• التجارة الإلكترونية: {internet.get('ecommerce_users_pct', 'N/A')}%")
            lines.append(f"• الدفع الرقمي: {internet.get('digital_payments_pct', 'N/A')}%")

        digital = data.get("digital_economy", {})
        if digital:
            lines.append(f"• شركات تقنية مسجلة: {digital.get('tech_companies_registered', 'N/A')}")
            lines.append(f"• شركات فينتك: {digital.get('fintech_companies', 'N/A')}")
            lines.append(f"• خدمات حكومية إلكترونية: {digital.get('government_services_online_pct', 'N/A')}%")

        infra = data.get("infrastructure", {})
        if infra:
            lines.append(f"• مراكز بيانات: {infra.get('data_centers', 'N/A')}")
            lines.append(f"• ترتيب الأمن السيبراني عالمياً: {infra.get('cybersecurity_index_global_rank', 'N/A')}")

        return "\n".join(lines)
