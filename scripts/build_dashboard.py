"""Build the two self-contained dashboard entry pages. No private inputs."""
import base64, hashlib
from pathlib import Path
root = Path(__file__).resolve().parents[1]
source = (root / 'scripts/dashboard.template.html').read_text()
script = (root / 'dashboard.js').read_text()
assert '</script' not in script.lower()
hash_value = "'sha256-" + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode() + "'"
html = source.replace('__SCRIPT_HASH__', hash_value).replace('__DASHBOARD_CSS__', (root / 'dashboard.css').read_text()).replace('__DASHBOARD_JS__', script)
for name in ('dashboard.html', 'index.html'):
    (root / name).write_text(html)
print('Built identical self-contained index.html and dashboard.html with a CSP script hash')
