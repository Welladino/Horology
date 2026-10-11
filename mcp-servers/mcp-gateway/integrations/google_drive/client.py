"""Restricted google_drive integration."""
from urllib.parse import quote
from policy import Denied, credential
from shared.http import request
from shared.text import clean_text


def drive_check(policy, config, file_id):
    if file_id not in policy['drive']['files'] or file_id not in config.get('drive_files', []):
        raise Denied('Drive file is outside assignment scope')

async def drive_list(policy, config):
    # Explicit IDs deliberately avoid a global Drive search permission.
    output = []
    for file_id in config.get('drive_files', [])[:20]:
        drive_check(policy, config, file_id)
        data = await request('GET', f'https://www.googleapis.com/drive/v3/files/{quote(file_id, safe="")}', token=credential('GOOGLE_READ_ACCESS_TOKEN'), params={'fields': 'id,name,mimeType,modifiedTime'})
        output.append(data)
    return output

async def drive_read(policy, config, file_id, sheet_range):
    drive_check(policy, config, file_id)
    if sheet_range:
        ranges = config.get('sheet_ranges', {}).get(file_id, [])
        if sheet_range not in ranges or sheet_range not in policy['drive'].get('sheet_ranges', {}).get(file_id, []):
            raise Denied('Only operator-approved exact sheet ranges can be read')
        data = await request('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{quote(file_id, safe="")}/values/{quote(sheet_range, safe="")}', token=credential('GOOGLE_READ_ACCESS_TOKEN'))
        return {'range': data.get('range'), 'values': data.get('values', [])}
    data = await request('GET', f'https://docs.googleapis.com/v1/documents/{quote(file_id, safe="")}', token=credential('GOOGLE_READ_ACCESS_TOKEN'))
    def text_elements(value):
        if isinstance(value, dict):
            if 'textRun' in value:
                yield value['textRun'].get('content', '')
            for key, child in value.items():
                if key != 'textRun':
                    yield from text_elements(child)
        elif isinstance(value, list):
            for child in value:
                yield from text_elements(child)
    return {'id': file_id, 'title': data.get('title'), 'text': clean_text(''.join(text_elements(data)), 40_000)}
