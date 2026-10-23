"""Rotate the new app database role and publish an app-owned connection secret.
No secret values or exception details are printed.
"""
from pathlib import Path
import os,secrets,subprocess
from urllib.parse import urlsplit,urlunsplit,quote,unquote
from dotenv import load_dotenv,set_key
import psycopg
from psycopg import sql
root=Path(__file__).resolve().parents[1]
os.chdir(root)
load_dotenv('.env.vercel.local');load_dotenv('.env.local',override=True)
try:
    original=os.environ.get('HORARY_DATABASE_URL') or os.environ['DATABASE_URL']
    parts=urlsplit(original)
    password=secrets.token_urlsafe(36)
    with psycopg.connect(original,connect_timeout=10) as db:
        role=db.execute('SELECT current_user').fetchone()[0]
        db.execute(sql.SQL('ALTER ROLE {} PASSWORD {}').format(sql.Identifier(role),sql.Literal(password)))
    netloc=quote(unquote(parts.username),safe='')+':'+quote(password,safe='')+'@'+parts.hostname+((':'+str(parts.port)) if parts.port else '')
    replacement=urlunsplit((parts.scheme,netloc,parts.path,parts.query,parts.fragment))
    set_key(root/'.env.local','HORARY_DATABASE_URL',replacement)
    cli=Path(os.environ['APPDATA'])/'npm/node_modules/vercel/dist/index.js'
    result=subprocess.run(['node',str(cli),'env','add','HORARY_DATABASE_URL','production,preview','--sensitive','--yes','--scope','dowidaiprojects','--project','dowidai-horary'],input=replacement,text=True,capture_output=True)
    if result.returncode:raise RuntimeError('Upload failed')
    with psycopg.connect(replacement,connect_timeout=10) as db:db.execute('SELECT 1')
    print('New database credential verified and uploaded. Previous password invalidated.')
except Exception:
    print('Database credential rotation needs attention; details suppressed.')
    raise SystemExit(1)
