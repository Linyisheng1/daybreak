#!/usr/bin/env python3
"""Fix admin password hash in PostgreSQL for Daybreak.

Uses Daybreak's own PBKDF2 hashing to generate the correct hash,
then stores it in the database using parameterized queries
that avoid shell expansion of $ signs.
"""
import asyncio
import hashlib
import base64
import os
import asyncpg

DOLLAR = chr(36)

def make_password_hash(password: str, iterations: int = 390000) -> str:
    """Generate PBKDF2 SHA256 hash matching Daybreak's format: pbkdf2_sha256$iterations$salt$digest"""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    salt_b64 = base64.b64encode(salt).decode('ascii')
    digest_b64 = base64.b64encode(dk).decode('ascii')
    return f"pbkdf2_sha256{DOLLAR}{iterations}{DOLLAR}{salt_b64}{DOLLAR}{digest_b64}"

async def fix_admin_password():
    conn = await asyncpg.connect(
        host="127.0.0.1",
        port=5432,
        database="daybreak",
        user="root",
        password="123456"
    )
    try:
        # Generate correct hash for the admin password
        password_hash = make_password_hash("DaybreakAdmin123!")

        # Update using parameterized queries (DOLLAR sign placeholders built at runtime)
        update_query = f"UPDATE system_users SET password_hash = {DOLLAR}1 WHERE username = {DOLLAR}2"
        result = await conn.execute(update_query, password_hash, "admin")
        print(f"[OK] Updated admin password hash: {result}")
        print(f"[OK] Hash value: {password_hash[:30]}...")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_admin_password())
