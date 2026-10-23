"""Owner-only aggregate dashboard. No questions, cities, or owner identifiers leave this API."""
import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import storage

router = APIRouter()
COOKIE = 'horary_admin'
TTL = 8 * 3600


def signing_key():
    secret = os.getenv('SESSION_SECRET', '')
    password_hash = os.getenv('HORARY_ADMIN_PASSWORD_HASH', '')
    if not secret or len(password_hash) != 64:
        raise HTTPException(503, 'Admin access is not configured.')
    return (secret + ':admin:' + password_hash).encode()


def session_token():
    payload = f'{int(time.time()) + TTL}.{secrets.token_hex(16)}'
    signature = hmac.new(signing_key(), payload.encode(), hashlib.sha256).hexdigest()
    return payload + '.' + signature


def require_admin(request):
    key = signing_key()
    try:
        expires, nonce, signature = request.cookies.get(COOKIE, '').split('.')
        payload = expires + '.' + nonce
        expected = hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()
        if int(expires) <= time.time() or int(expires) > time.time() + TTL or len(nonce) != 32 or not hmac.compare_digest(signature, expected):
            raise ValueError()
    except (ValueError, TypeError):
        raise HTTPException(401, 'Sign in to view statistics.')


def login_allowed(request):
    ip = request.headers.get('x-vercel-forwarded-for') or (request.client.host if request.client else 'unknown')
    fingerprint = hmac.new(signing_key(), ip.encode(), hashlib.sha256).hexdigest()
    # Five attempts per IP in a rolling 15-minute window, persistent across instances.
    slots = [f'admin:{fingerprint}:{n}' for n in range(5)]
    with storage.connect() as db:
        db.execute('SELECT pg_advisory_xact_lock(8246518)')
        active = {r['key'] for r in db.execute("SELECT key FROM throttle WHERE key=ANY(%s) AND touched > now() - interval '15 minutes'", (slots,)).fetchall()}
        slot = next((s for s in slots if s not in active), None)
        if slot is None:
            raise HTTPException(429, 'Too many sign-in attempts. Wait 15 minutes.')
        db.execute('INSERT INTO throttle(key) VALUES (%s) ON CONFLICT(key) DO UPDATE SET touched=now()', (slot,))


class Login(BaseModel):
    password: str = Field(min_length=1, max_length=256)


@router.get('/admin')
def admin_page():
    return FileResponse(Path(__file__).parent / 'static' / 'admin.html', headers={'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex, nofollow'})


@router.post('/api/admin/login')
def login(body: Login, request: Request, response: Response):
    login_allowed(request)
    supplied = hashlib.sha256(body.password.encode()).hexdigest()
    if not hmac.compare_digest(supplied, os.environ['HORARY_ADMIN_PASSWORD_HASH']):
        raise HTTPException(401, 'Incorrect password.')
    response.set_cookie(COOKIE, session_token(), httponly=True, secure=bool(os.getenv('VERCEL')), samesite='strict', max_age=TTL, path='/')
    return {'ok': True}


@router.post('/api/admin/logout')
def logout(response: Response):
    response.delete_cookie(COOKIE, path='/')
    return {'ok': True}


@router.get('/api/admin/stats')
def stats(request: Request):
    require_admin(request)
    with storage.connect() as db:
        totals = db.execute("""SELECT count(*) AS reports, count(DISTINCT owner) AS browser_archives,
            count(*) FILTER (WHERE created >= now() - interval '24 hours') AS last_24h,
            count(*) FILTER (WHERE created >= now() - interval '7 days') AS last_7d,
            count(*) FILTER (WHERE share IS NOT NULL) AS shared,
            count(*) FILTER (WHERE feedback=1) AS helpful,
            count(*) FILTER (WHERE feedback=0) AS not_helpful,
            coalesce(sum((data->'usage'->>'prompt_tokens')::bigint),0) AS input_tokens,
            coalesce(sum((data->'usage'->>'completion_tokens')::bigint),0) AS output_tokens
            FROM reports""").fetchone()
        daily = db.execute("""SELECT to_char(d.day,'YYYY-MM-DD') AS day, count(r.id) AS reports
            FROM generate_series((now() AT TIME ZONE 'UTC')::date - 29,
                (now() AT TIME ZONE 'UTC')::date, interval '1 day') d(day)
            LEFT JOIN reports r ON (r.created AT TIME ZONE 'UTC')::date = d.day::date
            GROUP BY d.day ORDER BY d.day""").fetchall()
        languages = db.execute("SELECT coalesce(data->>'language','ru') AS label, count(*) AS count FROM reports GROUP BY 1 ORDER BY 2 DESC").fetchall()
        topics = db.execute('SELECT topic AS label,count(*) AS count FROM reports GROUP BY 1 ORDER BY 2 DESC').fetchall()
        models = db.execute("SELECT coalesce(data->>'model','unknown') AS label,count(*) AS count FROM reports GROUP BY 1 ORDER BY 2 DESC").fetchall()
        quota = db.execute("SELECT to_char(now() AT TIME ZONE 'UTC','YYYY-MM') AS month, coalesce((SELECT reservations FROM quota WHERE month=to_char(now() AT TIME ZONE 'UTC','YYYY-MM')),0) AS reservations").fetchone()
    return {'totals': totals, 'daily': daily, 'languages': languages, 'topics': topics,
            'models': models, 'quota': {**quota, 'limit': 380, 'reserve_per_call': 0.05},
            'generated_at': int(time.time())}
