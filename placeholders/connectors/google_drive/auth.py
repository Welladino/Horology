"""Provider OAuth refresh, separate from the Google identity used to log into MCP."""
import asyncio
import time
import httpx
from horology_runtime.settings import TIMEOUTS
from policy import credential, Denied


class GoogleCredentials:
    def __init__(self):
        self.token = None
        self.expires = 0
        self.lock = asyncio.Lock()

    async def access_token(self):
        async with self.lock:
            if self.token and time.monotonic() < self.expires:
                return self.token
            async with httpx.AsyncClient(timeout=TIMEOUTS.gateway_http, follow_redirects=False, trust_env=False) as client:
                response = await client.post('https://oauth2.googleapis.com/token', data={'client_id':credential('GOOGLE_DRIVE_CLIENT_ID'),'client_secret':credential('GOOGLE_DRIVE_CLIENT_SECRET'),'refresh_token':credential('GOOGLE_DRIVE_REFRESH_TOKEN'),'grant_type':'refresh_token'})
                if response.status_code != 200:
                    raise Denied('Google provider authorization needs operator attention')
                data = response.json()
            if not isinstance(data.get('access_token'), str) or type(data.get('expires_in')) is not int or data['expires_in'] <= 60:
                raise Denied('Invalid Google provider token response')
            self.token = data['access_token']
            self.expires = time.monotonic() + min(data['expires_in'], 3600) - 60
            return self.token


credentials = GoogleCredentials()
