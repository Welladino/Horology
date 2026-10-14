"""Bounded Sheets and Drive calls with the job's Google credentials."""
import asyncio
from urllib.parse import quote

import httpx
from horology_runtime.settings import TIMEOUTS

SCOPES = ("https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.readonly")
MAX_FILE_BYTES = 2_000_000
TEXT_TYPES = ("text/markdown", "text/plain", "text/x-markdown")
GOOGLE_DOC = "application/vnd.google-apps.document"
INDEXABLE_TYPES = TEXT_TYPES + (GOOGLE_DOC,)


class GoogleClient:
    def __init__(self, credentials=None):
        if credentials is None:
            import google.auth
            credentials, _ = google.auth.default(scopes=SCOPES)
        self.credentials = credentials

    async def _token(self):
        if not self.credentials.valid:
            from google.auth.transport.requests import Request
            await asyncio.to_thread(self.credentials.refresh, Request())
        return self.credentials.token

    async def _request(self, method, url, **kwargs):
        headers = {"Authorization": f"Bearer {await self._token()}"}
        async with httpx.AsyncClient(timeout=TIMEOUTS.gateway_http, follow_redirects=False, trust_env=False) as http:
            response = await http.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    async def sheet_rows(self, spreadsheet_id, tab):
        """All rows of a tab, raw values (booleans stay booleans)."""
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{quote(repr_tab(tab))}"
        data = (await self._request("GET", url, params={"valueRenderOption": "UNFORMATTED_VALUE"})).json()
        return data.get("values", [])

    async def write_cells(self, spreadsheet_id, updates):
        """updates: [(A1 range, [[values]])]; written as typed, not parsed."""
        if not updates:
            return
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values:batchUpdate"
        body = {"valueInputOption": "RAW", "data": [{"range": r, "values": v} for r, v in updates]}
        await self._request("POST", url, json=body)

    async def tab_titles(self, spreadsheet_id):
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
        data = (await self._request("GET", url, params={"fields": "sheets.properties.title"})).json()
        return [sheet["properties"]["title"] for sheet in data.get("sheets", [])]

    async def add_tab(self, spreadsheet_id, title):
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate"
        await self._request("POST", url, json={"requests": [{"addSheet": {"properties": {"title": title}}}]})

    async def replace_tab(self, spreadsheet_id, tab, rows):
        """Clear a tab's values, then write rows (header first) from A1, as typed."""
        base = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values"
        await self._request("POST", f"{base}/{quote(repr_tab(tab))}:clear", json={})
        await self.write_cells(spreadsheet_id, [(f"{repr_tab(tab)}!A1", rows)])

    async def file_metadata(self, file_id):
        url = f"https://www.googleapis.com/drive/v3/files/{quote(file_id)}"
        params = {"fields": "id,mimeType,version,size,trashed", "supportsAllDrives": "true"}
        return (await self._request("GET", url, params=params)).json()

    async def file_text(self, meta):
        """Text of a Markdown/plain upload or a Google Doc; other types are refused."""
        file_id = quote(meta["id"])
        if meta["mimeType"] == GOOGLE_DOC:
            url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
            response = await self._request("GET", url, params={"mimeType": "text/plain"})
        elif meta["mimeType"] in TEXT_TYPES:
            if int(meta.get("size") or 0) > MAX_FILE_BYTES:
                raise ValueError("File is too large to index")
            url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
            response = await self._request("GET", url, params={"alt": "media", "supportsAllDrives": "true"})
        else:
            raise ValueError(f"Unsupported file type {meta['mimeType']}")
        if len(response.content) > MAX_FILE_BYTES:
            raise ValueError("File is too large to index")
        return response.content.decode("utf-8", errors="replace")


def repr_tab(tab):
    """A1 tab reference with quotes, doubling any apostrophe."""
    return "'" + tab.replace("'", "''") + "'"
