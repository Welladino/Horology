"""Create/copy approved templates and edit only this assignment's own draft."""
from urllib.parse import quote
from policy import Denied
from shared.http import request
from ..auth import credentials


def scope_check(policy, config, folder_id, pipeline_id, template_id=''):
    for key, value in (('output_folders',folder_id), ('pipeline_ids',pipeline_id)):
        allowed = policy.get('drive', {}).get(key, []) if key == 'output_folders' else None
        if value not in config.get('drive_'+key, []) or (allowed is not None and value not in allowed):
            raise Denied('Draft destination or Pipeline ID is outside assignment scope')
    if template_id and (template_id not in policy['drive'].get('templates', []) or template_id not in config.get('drive_templates', [])):
        raise Denied('Template is outside assignment scope')


async def metadata(file_id):
    return await request('GET', 'https://www.googleapis.com/drive/v3/files/'+quote(file_id,safe=''), token=await credentials.access_token(), params={'fields':'id,mimeType,parents,trashed,appProperties','supportsAllDrives':'true'})


async def create(policy, config, assignment, folder_id, pipeline_id, title, template_id):
    scope_check(policy,config,folder_id,pipeline_id,template_id)
    destination = await metadata(folder_id)
    if destination.get('trashed') or destination.get('mimeType') != 'application/vnd.google-apps.folder':
        raise Denied('Approved output folder is unavailable')
    body = {'name':title,'parents':[folder_id],'appProperties':{'horology_assignment':assignment,'horology_pipeline':pipeline_id,'horology_state':'draft'}}
    if template_id:
        original = await metadata(template_id)
        if original.get('trashed') or original.get('mimeType') != 'application/vnd.google-apps.document':
            raise Denied('Only approved native Doc templates may be copied')
        endpoint = 'https://www.googleapis.com/drive/v3/files/'+quote(template_id,safe='')+'/copy'
    else:
        endpoint = 'https://www.googleapis.com/drive/v3/files'
        body['mimeType'] = 'application/vnd.google-apps.document'
    result = await request('POST', endpoint, token=await credentials.access_token(), params={'fields':'id,name,webViewLink','supportsAllDrives':'true'}, body=body)
    if not result.get('id'):
        raise Denied('Draft creation outcome is uncertain')
    return {'id':result['id'],'title':result.get('name'), 'url':'https://docs.google.com/document/d/'+result['id']+'/edit','folder':folder_id,'pipeline_id':pipeline_id}


async def own_draft(policy, config, assignment, file_id, store):
    receipt = store.draft(assignment,file_id)
    scope_check(policy,config,receipt['folder'],receipt['pipeline_id'])
    meta = await metadata(file_id)
    tags = meta.get('appProperties', {})
    if meta.get('trashed') or meta.get('mimeType') != 'application/vnd.google-apps.document' or meta.get('parents') != [receipt['folder']] or tags.get('horology_assignment') != assignment or tags.get('horology_state') != 'draft':
        raise Denied('Only an unchanged assignment-owned draft may be edited')
    return receipt


async def edit(file_id, revision_id, replacements, append_text):
    requests = [{'replaceAllText':{'containsText':{'text':r['find'],'matchCase':True},'replaceText':r['replace']}} for r in replacements]
    if append_text:
        requests.append({'insertText':{'endOfSegmentLocation':{},'text':append_text}})
    data = await request('POST','https://docs.googleapis.com/v1/documents/'+quote(file_id,safe='')+':batchUpdate',token=await credentials.access_token(),body={'writeControl':{'requiredRevisionId':revision_id},'requests':requests})
    return {'id':file_id,'revision_id':data.get('writeControl', {}).get('requiredRevisionId'), 'updated':True}
