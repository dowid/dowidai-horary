"""Local setup, never prints secret values. Run from project root."""
from pathlib import Path
import secrets
import subprocess
import os
from dotenv import load_dotenv, dotenv_values, set_key

root=Path(__file__).resolve().parents[1]
os.chdir(root)
load_dotenv(root/'.env.vercel.local')
load_dotenv(root/'.env.local',override=True)
if not os.environ.get('SESSION_SECRET'):
    secret=secrets.token_hex(32)
    set_key(root/'.env.local','SESSION_SECRET',secret)
    os.environ['SESSION_SECRET']=secret
if not os.environ.get('OPENAI_API_KEY'):
    raise SystemExit('OPENAI_API_KEY missing; no credentials printed.')
import storage
storage.migrate()
print('Database schema ready.')
cli=Path(os.environ['APPDATA'])/'npm'/'node_modules'/'vercel'/'dist'/'index.js'
for name in ('OPENAI_API_KEY','SESSION_SECRET'):
    result=subprocess.run(['node',str(cli),'env','add',name,'production,preview','--sensitive','--yes','--scope','dowidaiprojects','--project','dowidai-horary'],input=os.environ[name],text=True,capture_output=True)
    # CLI output is intentionally not echoed because values enter stdin.
    print(name+': '+('uploaded securely' if result.returncode==0 else 'upload failed'))
    if result.returncode:raise SystemExit(1)
