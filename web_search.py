"""
خدمة البحث على الإنترنت — DuckDuckGo
Web search service for follow-up questions
"""
import logging

logger = logging.getLogger(__name__)


def search_web(query, max_results=5, region='xa-ar'):
    """
    البحث في الإنترنت عبر DuckDuckGo وإرجاع نتائج منسّقة.

    Args:
        query: استعلام البحث (عربي أو إنجليزي)
        max_results: الحد الأقصى لعدد النتائج
        region: رمز المنطقة — 'xa-ar' للعربية، 'wt-wt' للعالمي

    Returns:
        نص منسّق بالنتائج أو None عند الفشل
    """
    try:
        import sys
        logger.info(f"Python executable: {sys.executable}")
        logger.info(f"Python path: {sys.path[:3]}")
        from ddgs import DDGS
        logger.info("ddgs imported successfully")

        results = list(DDGS().text(
            query,
            region=region,
            safesearch='moderate',
            max_results=max_results
        ))

        if not results:
            # محاولة ثانية: بحث عالمي
            results = list(DDGS().text(
                query,
                region='wt-wt',
                safesearch='moderate',
                max_results=max_results
            ))

        if not results:
            logger.info(f"لا نتائج بحث لـ: {query[:80]}")
            return None

        formatted = []
        for i, r in enumerate(results, 1):
            title = r.get('title', '')
            body = r.get('body', '')
            href = r.get('href', '')
            formatted.append(f"{i}. **{title}**\n   {body}\n   المصدر: {href}")

        output = "\n\n".join(formatted)
        logger.info(f"بحث الويب: {len(results)} نتيجة لـ: {query[:80]}")
        return output

    except ImportError as e:
        import sys
        logger.warning(f"ImportError: {e} | Python: {sys.executable} | site-packages exists: {any('site-packages' in p for p in sys.path)}")
        return None
    except Exception as e:
        logger.error(f"فشل بحث الويب: {type(e).__name__}: {e}")
        return None
