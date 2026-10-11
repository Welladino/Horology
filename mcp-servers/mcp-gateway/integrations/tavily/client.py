"""Restricted tavily integration."""
from policy import Denied, credential
from shared.http import request
from shared.text import clean_text


async def tavily(query, advanced=False):
    if not query.strip() or len(query) > 400:
        raise Denied('Search query must contain 1–400 characters')
    data = await request('POST', 'https://api.tavily.com/search', token=credential('TAVILY_API_KEY'), body={'query': query, 'search_depth': 'advanced' if advanced else 'basic', 'auto_parameters': False, 'max_results': 5, 'include_answer': False, 'include_raw_content': False, 'include_images': False, 'include_usage': True})
    return [{'title': clean_text(r.get('title'), 500), 'url': r.get('url'), 'content': clean_text(r.get('content'), 5000)} for r in data.get('results', [])[:5]]
