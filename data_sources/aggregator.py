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
}

# Agent-to-source mapping: which sources are primary/secondary for each agent
AGENT_SOURCE_MAP = {
    "market": {
        "primary": ["trading_economics", "edb", "sijilat"],
        "secondary": ["world_bank"],
    },
    "financial": {
        "primary": ["cbb", "tamkeen", "world_bank"],
        "secondary": ["bahrain_bourse"],
    },
    "competitive": {
        "primary": ["sijilat"],
        "secondary": ["bahrain_bourse"],
    },
    "legal": {
        "primary": ["tamkeen"],
        "secondary": ["sijilat"],
    },
    "technical": {
        "primary": ["world_bank"],
        "secondary": ["tamkeen", "edb"],
    },
    "brokerage_models": {
        "primary": ["sijilat", "edb"],
        "secondary": [],
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
        if growth:
            parts.append("📈 مؤشرات النمو:\n" + "\n".join(f"  - {g}" for g in growth))

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
