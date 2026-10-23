"""Create a high-entropy owner password locally. Never prints credentials."""
import hashlib
import secrets
from pathlib import Path
from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
destination = root / '.key-setup' / 'horary-admin.txt'
env_path = root / '.env.local'
existing = dotenv_values(env_path).get('HORARY_ADMIN_PASSWORD_HASH')
if existing:
    if not destination.exists() or hashlib.sha256(destination.read_text().strip().encode()).hexdigest() != existing:
        raise SystemExit('An admin credential already exists. Refusing to overwrite it.')
else:
    password = secrets.token_urlsafe(32)
    destination.parent.mkdir(exist_ok=True)
    if destination.exists():
        raise SystemExit('Credential file already exists. Refusing to overwrite it.')
    destination.write_text(password,encoding='utf-8')
    with env_path.open('a',encoding='utf-8') as handle:
        handle.write('\nHORARY_ADMIN_PASSWORD_HASH='+hashlib.sha256(password.encode()).hexdigest()+'\n')
print('Admin credential is ready in the ignored local file. No secret printed.')
