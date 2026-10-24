import copy
import importlib.util
import json
import shutil
import sys
import types
from pathlib import Path

root = Path(__file__).resolve().parents[1]
node_root = root / 'ComfyUI-Easy-Install/ComfyUI/custom_nodes/ComfyUI-MiniMaxH3Mod'
library = root / 'ComfyUI-Easy-Install/ComfyUI/models/refmods'
pkg = types.ModuleType('identity_bundle_tools')
pkg.__path__ = [str(node_root)]
sys.modules[pkg.__name__] = pkg
for part in ('core', 'bundle'):
    spec = importlib.util.spec_from_file_location(pkg.__name__ + '.' + part, node_root / (part + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
core = sys.modules[pkg.__name__ + '.core']
bundle = sys.modules[pkg.__name__ + '.bundle']
manifest = json.loads((root / 'maintenance/trimmed-identity-encode-sources.json').read_text())
report = {}
for person in ('Rafa', 'Lune'):
    name = person + '_IdentityEncode_v1'
    path = library / name
    backup = root / 'maintenance' / (name + '-original-stack.safetensors')
    if not backup.exists():
        shutil.copy2(str(path) + '.safetensors', backup)
    original = bundle.load_bundle(str(backup.with_suffix('')))
    assert len(original) == 1
    mod = original[0][0]
    sources = [i['image'] for i in manifest['images'] if i['included'] and ('_' + person + '_') in i['image']]
    assert len(sources) == mod.latent_t
    entries = []
    for i, source in enumerate(sources):
        metadata = copy.deepcopy(mod.metadata())
        metadata.update(name=Path(source).stem.removeprefix('refmod_' + person + '_'),
                        kind='image', latent_t=1, source='image',
                        source_shape=f'1x{mod.latent_h}x{mod.latent_w}',
                        tags=['identity_encode', 'independent still', source], concept_type='identity')
        member = core.H3RefMod.from_metadata(metadata, mod.latent[:, :, i:i+1].clone(), str(path))
        entries.append((member, 1.0))
    bundle.save_bundle(str(path), name, entries)
    saved = bundle.load_bundle(str(path))
    assert len(saved) == len(sources)
    assert all(m.kind == 'image' and m.latent_t == 1 for m, _ in saved)
    assert all(new.latent.equal(old.latent) for (new, _), (old, _) in zip(saved, entries))
    report[person] = {'file': str(path) + '.safetensors', 'image_members': len(saved),
                      'video_members': 0, 'source_images': sources, 'latents_unchanged': True}
(root / 'maintenance/identity-still-members-verified.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
