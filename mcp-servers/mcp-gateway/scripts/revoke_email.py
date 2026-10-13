"""Revoke every gateway access and refresh token issued to one Google email.

Usage: GATEWAY_DATABASE_URL=... python scripts/revoke_email.py person@example.com
Remove the person from Google Auth Platform Audience test users first, so they cannot sign in again.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.connection import Database
from database.repositories.oauth import OAuthRepository


async def main(email):
    async with Database(os.environ.get('GATEWAY_DATABASE_URL')) as database:
        removed = await OAuthRepository(database).revoke_email(email)
    print(f'Removed {removed} token records for {email.lower()}')


if __name__ == '__main__':
    if len(sys.argv) != 2 or '@' not in sys.argv[1]:
        sys.exit('Usage: python scripts/revoke_email.py person@example.com')
    asyncio.run(main(sys.argv[1]))
