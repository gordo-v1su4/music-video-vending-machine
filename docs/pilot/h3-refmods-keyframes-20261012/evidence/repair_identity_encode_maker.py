import json
import shutil
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = Path('D:/user/default/workflows/Approved_Close_Coverage_RefMod_Maker_Transfer.json')
backup = root / 'maintenance/before-identity-encode-maker.json'
if not backup.exists():
    shutil.copy2(path, backup)
w = json.loads(path.read_text(encoding='utf-8'))
schema = json.load(urllib.request.urlopen('http://127.0.0.1:8188/object_info/MiniMaxH3RefModMasterExtract'))['MiniMaxH3RefModMasterExtract']
nodes = {n['id']: n for n in w['nodes']}
for ident, person in ((30, 'Rafa'), (60, 'Lune')):
    n = nodes[ident]
    n.pop('title', None)
    n['properties'] = {'Node name for S&R': n['type']}
    n['size'] = [650, 1250]
    settings = {'name': person + '_IdentityEncode_v1', 'mode': 'Full Reference',
                'concept_type': 'identity', 'background_retention': 0.0,
                'ref_resolution': 1024, 'pool_h': 64, 'pool_w': 64,
                'latent_frames': 1, 'identity': 0, 'merge': False,
                'motion_only': False, 'multiplier': 1, 'max_tokens': 0,
                'description': '', 'save': True, 'audio_max_seconds': 30.0,
                'audio_max_tokens': 5120, 'audio_budget_policy': 'error',
                'audio_concept_type': 'voice', 'max_total_tokens': 0,
                'extraction_preset': 'identity_encode', 'subfolder': '',
                'budget_policy': 'error', 'save_layout': 'bundle'}
    # V3 combo fields are COMBO strings, not legacy option lists. Preserve every widget slot.
    widgets = []
    for section in ('required', 'optional'):
        for name, spec in schema['input'].get(section, {}).items():
            kind = spec[0]
            if isinstance(kind, list) or kind in ('COMBO', 'BOOLEAN', 'INT', 'FLOAT', 'STRING'):
                options = spec[1] if len(spec) > 1 else {}
                widgets.append(settings.get(name, options.get('default', '')))
    n['widgets_values'] = widgets
    n['mode'] = 0
for n in w['nodes']:
    if n['id'] not in (30, 60):
        n['mode'] = 0
for g, person in zip(w['groups'], ('Rafa', 'Lune')):
    g['title'] = f'{person}: eight approved sources -> identity_encode -> one saved file'
w['extra']['ds'] = {'scale': 0.47, 'offset': [-1400, -20]}
path.write_text(json.dumps(w, indent=2), encoding='utf-8')
transfer = root / 'maintenance/Approved_Close_Coverage_RefMod_Maker_Transfer.json'
transfer.write_text(json.dumps(w, indent=2), encoding='utf-8')
print(json.dumps({'file': str(path), 'widgets': {p: nodes[i]['widgets_values'] for i, p in ((30, 'Rafa'), (60, 'Lune'))}}, indent=2))
