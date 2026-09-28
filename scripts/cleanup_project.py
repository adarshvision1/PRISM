"""One-time audited cleanup. Every removed file is verified in a recoverable ZIP."""
from pathlib import Path
import hashlib, zipfile, json
ROOT=Path(__file__).resolve().parents[1]
FILES='''backend/live.py
backend/protocol.py
backend/model/classical.py
backend/ingest/r3d_parser.py
backend/model/salsanext_legacy.py
backend/model/finetune.py
backend/metrics.py
scripts/record3d_bridge.py
scripts/live_smoke.py
scripts/archive_superseded.py
scripts/benchmark_pipeline.py
scripts/benchmark_fast_profile.py
scripts/compute_pilot.py
scripts/export_onnx.py
scripts/near_field_audit.py
scripts/prepare_demo.py
scripts/benchmark.py
scripts/ros2_publish.py
tests/test_live.py
frontend/assets/app.js
frontend/assets/style.css
frontend/assets/recordings.js
frontend/assets/pipeline.js
frontend/assets/near_audit.js
docs/live_setup.md
docs/protocol.md
requirements-live.txt
data/upload_fixtures/sequence.r3d
PRISM-offline-demo.zip
data/offline_manifest.json'''.splitlines()
def main():
    archive=ROOT/'snapshots/removed-legacy-20260926.zip'
    if archive.exists():
        print('Cleanup archive already exists; preserved without overwriting. See data/cleanup_manifest.json.')
        return
    existing=[ROOT/name for name in FILES if (ROOT/name).is_file()]
    # Also identify cached phone results by recorded domain, never by folder name.
    for path in (ROOT/'data/jobs').glob('*/frame-00000.json'):
        domain=json.loads(path.read_text()).get('domain','').lower()
        if 'record3d' in domain:
            existing.extend(p for p in path.parent.rglob('*') if p.is_file())
    for path in existing:
        if not path.resolve().is_relative_to(ROOT):raise ValueError('Outside workspace')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in existing:z.write(path,path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for path in existing:
            assert hashlib.sha256(z.read(path.relative_to(ROOT).as_posix())).digest()==hashlib.sha256(path.read_bytes()).digest()
    for path in existing:path.unlink()
    (ROOT/'data/cleanup_manifest.json').write_text(json.dumps({'archive':str(archive.relative_to(ROOT)),'removed':[str(p.relative_to(ROOT)) for p in existing],'archive_verified':True},indent=2))
    print('Archived and removed',len(existing),'files')
if __name__=='__main__':main()
