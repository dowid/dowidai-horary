import os
import secrets
import psycopg
from psycopg.rows import dict_row

DAILY_LIMIT = 10

def connect():
    url = os.environ.get('HORARY_DATABASE_URL') or os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
    if not url:
        raise RuntimeError('Database is not configured')
    return psycopg.connect(url, row_factory=dict_row, connect_timeout=10)

def migrate():
    with connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, owner TEXT NOT NULL, created TIMESTAMPTZ NOT NULL DEFAULT now(), question TEXT NOT NULL, topic TEXT NOT NULL, city TEXT NOT NULL, data JSONB NOT NULL, share TEXT UNIQUE, feedback SMALLINT)')
        db.execute('CREATE INDEX IF NOT EXISTS reports_owner ON reports(owner, created DESC)')
        db.execute('CREATE TABLE IF NOT EXISTS quota (month TEXT PRIMARY KEY, reservations INTEGER NOT NULL DEFAULT 0)')
        db.execute('CREATE TABLE IF NOT EXISTS throttle (key TEXT PRIMARY KEY, touched TIMESTAMPTZ NOT NULL DEFAULT now())')

def reserve(owner, ip_hash, question_hash, purpose='reading', receipt=False, continuation=None):
    """One transaction: rate limits and conservative spend reservation, no refunds on errors."""
    if purpose == 'voice':
        owner, ip_hash = 'voice:'+owner, 'voice:'+ip_hash
    elif purpose != 'reading':
        raise ValueError('Unknown reservation purpose')
    with connect() as db:
        # Serialise quota and throttle decisions across all instances.
        db.execute('SELECT pg_advisory_xact_lock(8246517)')
        db.execute("DELETE FROM throttle WHERE touched < now() - interval '2 days'")
        # Slot zero preserves attempts made before the daily limit was raised.
        slots = [f'o:{owner}'] + [f'o:{owner}:{i}' for i in range(1, DAILY_LIMIT)]
        active = {row['key'] for row in db.execute(
            "SELECT key FROM throttle WHERE key=ANY(%s) AND touched > now() - interval '24 hours'",
            (slots,)).fetchall()}
        slot = next((key for key in slots if key not in active), None)
        if slot is None:
            return 'daily'
        continuation_key = f'c:{owner}:{continuation}' if receipt and continuation else None
        continuing = continuation_key and db.execute(
            "SELECT 1 FROM throttle WHERE key=%s AND touched > now() - interval '10 minutes'", (continuation_key,)).fetchone()
        if not continuing and db.execute("SELECT 1 FROM throttle WHERE key=%s AND touched > now() - interval '1 minute'", (f'i:{ip_hash}',)).fetchone():
            return 'rate'
        # Separate abuse ceiling, including clarified requests whose reading slot is released.
        if receipt:
            request_slots = [f'a:{owner}:{i}' for i in range(40)]
            used = {row['key'] for row in db.execute(
                "SELECT key FROM throttle WHERE key=ANY(%s) AND touched > now() - interval '24 hours'",
                (request_slots,)).fetchall()}
            request_slot = next((key for key in request_slots if key not in used), None)
            if request_slot is None:
                return 'requests'
        month = db.execute("SELECT to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM') AS month").fetchone()['month']
        db.execute('INSERT INTO quota(month) VALUES (%s) ON CONFLICT DO NOTHING', (month,))
        count=db.execute('SELECT reservations FROM quota WHERE month=%s', (month,)).fetchone()['reservations']
        if count >= 380:
            return 'budget'
        db.execute('UPDATE quota SET reservations=reservations+1 WHERE month=%s', (month,))
        if continuing:
            db.execute('DELETE FROM throttle WHERE key=%s', (continuation_key,))
        for key in (slot, f'i:{ip_hash}'):
            db.execute('INSERT INTO throttle(key) VALUES (%s) ON CONFLICT(key) DO UPDATE SET touched=now()', (key,))
        if receipt:
            db.execute('INSERT INTO throttle(key) VALUES (%s) ON CONFLICT(key) DO UPDATE SET touched=now()', (request_slot,))
            touched = db.execute('SELECT touched FROM throttle WHERE key=%s', (slot,)).fetchone()['touched']
            return {'slot':slot, 'ip_key':f'i:{ip_hash}', 'touched':touched, 'owner':owner}
    return None


def release_clarification(receipt):
    """Release only this request's daily slot and cooldown, never its spent AI budget."""
    with connect() as db:
        db.execute('SELECT pg_advisory_xact_lock(8246517)')
        removed = db.execute('DELETE FROM throttle WHERE key=%s AND touched=%s RETURNING key',
                             (receipt['slot'], receipt['touched'])).fetchone()
        if not removed:
            return None
        db.execute('DELETE FROM throttle WHERE key=%s AND touched=%s',
                   (receipt['ip_key'], receipt['touched']))
        token = secrets.token_urlsafe(24)
        db.execute('INSERT INTO throttle(key) VALUES (%s)', (f"c:{receipt['owner']}:{token}",))
        return token
