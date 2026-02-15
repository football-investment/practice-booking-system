"""
seed_credit_invoices.py
=======================
Seeds verified InvoiceRequest records for all @lfa-seed.hu users so that
every credit balance is transparently backed by admin-verified invoices.

Uses ONLY the three real credit purchase packages from the system:
  Bronze : 100 credits  /  €10.00
  Silver : 500 credits  /  €45.00
  Gold   : 1000 credits /  €80.00

Each user is assigned one of 12 deterministic invoice combos (rn % 12),
producing 12 realistic credit tiers:

  Combo  Packages           Total credits  # users
  ──────────────────────────────────────────────────
    0    1× Bronze          100 cr         86
    1    2× Bronze          200 cr         86
    2    3× Bronze          300 cr         86
    3    1× Silver          500 cr         86
    4    1× Silver+Bronze   600 cr         85
    5    2× Silver          1000 cr        85
    6    1× Gold            1000 cr        85
    7    1× Gold+Silver     1500 cr        85
    8    2× Gold            2000 cr        85
    9    2× Gold+Silver     2500 cr        85
   10    3× Gold            3000 cr        85
   11    4× Gold            4000 cr        85
  ──────────────────────────────────────────────────
  Total                                   1024 users
                                          ~2217 invoices

Payment reference format (unique per invoice):
  SEED-{user_id:06d}-{seq:02d}   e.g. SEED-071770-01  (16 chars, SWIFT-safe)

Race-condition prevention:
  Verification is done in SEQ ROUNDS (all seq=01 first, then seq=02, …).
  Within each round every user appears at most once
  → no concurrent credit_balance conflict.
"""

from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import psycopg2
import psycopg2.extras
import requests

# ── Config ────────────────────────────────────────────────────────────────────
DATABASE_URL   = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
API_BASE       = "http://localhost:8000"
ADMIN_EMAIL    = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"
SEED_DOMAIN    = "%@lfa-seed.hu"
REF_PREFIX     = "SEED-"   # used for idempotent cleanup
MAX_WORKERS    = 20        # concurrent verify calls per round

# ── Credit packages (production definitions) ──────────────────────────────────
BRONZE = {"credits": 100,  "eur": 10.0,  "name": "Bronze"}
SILVER = {"credits": 500,  "eur": 45.0,  "name": "Silver"}
GOLD   = {"credits": 1000, "eur": 80.0,  "name": "Gold"}

# 12 invoice combos — assigned by  rn % 12  (deterministic, repeating cycle)
# Each entry is a list of packages bought by that user.
INVOICE_COMBOS = [
    [BRONZE],                        # combo  0 →  100 cr
    [BRONZE, BRONZE],                # combo  1 →  200 cr
    [BRONZE, BRONZE, BRONZE],        # combo  2 →  300 cr
    [SILVER],                        # combo  3 →  500 cr
    [SILVER, BRONZE],                # combo  4 →  600 cr
    [SILVER, SILVER],                # combo  5 → 1000 cr  (2× Silver)
    [GOLD],                          # combo  6 → 1000 cr  (1× Gold)
    [GOLD, SILVER],                  # combo  7 → 1500 cr
    [GOLD, GOLD],                    # combo  8 → 2000 cr
    [GOLD, GOLD, SILVER],            # combo  9 → 2500 cr
    [GOLD, GOLD, GOLD],              # combo 10 → 3000 cr
    [GOLD, GOLD, GOLD, GOLD],        # combo 11 → 4000 cr
]

# Sanity-check: at most 4 packages per user → max 4 seq rounds
assert all(len(c) <= 4 for c in INVOICE_COMBOS)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_admin_token() -> str:
    r = requests.post(
        f"{API_BASE}/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=15,
    )
    r.raise_for_status()
    token = r.json().get("access_token")
    if not token:
        raise RuntimeError(f"Login failed: {r.text}")
    return token


def verify_invoice(session: requests.Session, token: str, invoice_id: int) -> dict:
    """POST /api/v1/invoices/{id}/verify — application stack credits the user."""
    r = session.post(
        f"{API_BASE}/api/v1/invoices/{invoice_id}/verify",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    return {
        "invoice_id": invoice_id,
        "status_code": r.status_code,
        "ok": r.status_code == 200,
    }


def verify_batch(session, token, inv_ids, label, totals):
    """Verify a batch of invoices concurrently (no same-user conflicts in one batch)."""
    ok = failed = 0
    start = datetime.now()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(verify_invoice, session, token, i): i for i in inv_ids}
        for future in as_completed(futures):
            res = future.result()
            if res["ok"]:
                ok += 1
            else:
                failed += 1
                totals["failed"].append(res["invoice_id"])
    elapsed = (datetime.now() - start).total_seconds()
    print(f"    {label}: {len(inv_ids):>4} invoices  ✓{ok}  ✗{failed}  [{elapsed:.1f}s]")
    totals["ok"] += ok


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  seed_credit_invoices.py — package-based transparent credit seed")
    print("=" * 65)

    # ── Step 0: Admin token ───────────────────────────────────────
    print("\n[0] Authenticating as admin...")
    token = get_admin_token()
    print("    ✓ Token acquired")

    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # ── Step 1: Reset credits ─────────────────────────────────
        print("\n[1] Resetting credit_balance / credit_purchased to 0...")
        cur.execute("""
            UPDATE users
            SET credit_balance   = 0,
                credit_purchased = 0
            WHERE email LIKE %s
        """, (SEED_DOMAIN,))
        print(f"    ✓ Reset {cur.rowcount} users")
        conn.commit()

        # ── Step 2: Purge previous SEED-* invoices (idempotency) ──
        print("\n[2] Purging previous SEED-* invoice records...")
        cur.execute("""
            DELETE FROM invoice_requests
            WHERE payment_reference LIKE %s
        """, (REF_PREFIX + "%",))
        deleted = cur.rowcount
        print(f"    ✓ Deleted {deleted} old seed invoices")
        conn.commit()

        if deleted > 0:
            cur.execute("""
                UPDATE users SET credit_balance = 0, credit_purchased = 0
                WHERE email LIKE %s
            """, (SEED_DOMAIN,))
            conn.commit()
            print("    ✓ Re-reset credits after partial cleanup")

        # ── Step 3: Fetch seed users (ordered → deterministic rn) ─
        print("\n[3] Fetching seed users...")
        cur.execute("""
            SELECT id, email
            FROM users
            WHERE email LIKE %s
            ORDER BY email
        """, (SEED_DOMAIN,))
        seed_users = cur.fetchall()
        n_users = len(seed_users)
        print(f"    ✓ Found {n_users} seed users")

        if not seed_users:
            print("    ⚠ No seed users found — nothing to do.")
            return

        # ── Step 4: Build invoice rows ────────────────────────────
        print("\n[4] Building invoice plan (packages only)...")
        # all_invoices: list of (user_id, payment_reference, credit_amount, amount_eur, seq)
        all_invoices = []
        for rn, row in enumerate(seed_users):
            uid   = row["id"]
            combo = INVOICE_COMBOS[rn % len(INVOICE_COMBOS)]
            for seq, pkg in enumerate(combo, start=1):
                ref = f"SEED-{uid:06d}-{seq:02d}"   # e.g. SEED-071770-01
                all_invoices.append((uid, ref, pkg["credits"], pkg["eur"], seq))

        # Verify uniqueness of payment_reference
        refs = [row[1] for row in all_invoices]
        assert len(refs) == len(set(refs)), "Duplicate payment references detected!"

        n_combos   = len(INVOICE_COMBOS)
        max_seq    = max(len(c) for c in INVOICE_COMBOS)
        print(f"    ✓ {len(all_invoices)} invoices planned for {n_users} users")
        print(f"      Combos: {n_combos}  |  max seq per user: {max_seq}")

        # ── Step 5: INSERT InvoiceRequest records ─────────────────
        print("\n[5] Inserting InvoiceRequest records (status=pending)...")
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO invoice_requests
                (user_id, payment_reference, credit_amount, amount_eur,
                 specialization, status, created_at)
            VALUES %s
            """,
            [
                (uid, ref, credits, eur, "LFA_FOOTBALL_PLAYER", "pending",
                 datetime.now(timezone.utc))
                for uid, ref, credits, eur, _seq in all_invoices
            ],
            template=None,
            page_size=500,
        )
        conn.commit()

        # Fetch back all inserted IDs with their references
        cur.execute("""
            SELECT id, payment_reference, credit_amount
            FROM invoice_requests
            WHERE payment_reference LIKE %s
              AND status = 'pending'
            ORDER BY payment_reference
        """, (REF_PREFIX + "%",))
        inserted_rows = cur.fetchall()
        print(f"    ✓ Inserted {len(inserted_rows)} invoice records")

        # Build: ref → invoice_id
        ref_to_id = {row["payment_reference"]: row["id"] for row in inserted_rows}

        # Build seq-rounds: round[i] = list of invoice_ids where seq == i+1
        rounds = [[] for _ in range(max_seq)]
        for uid, ref, credits, eur, seq in all_invoices:
            inv_id = ref_to_id.get(ref)
            if inv_id:
                rounds[seq - 1].append(inv_id)

        # ── Step 6: Verify in SEQ ROUNDS (no same-user concurrency) ──
        print(f"\n[6] Verifying invoices in {max_seq} sequential rounds "
              f"({MAX_WORKERS} workers/round)...")
        totals = {"ok": 0, "failed": []}
        http_session = requests.Session()

        for i, round_ids in enumerate(rounds, start=1):
            if round_ids:
                verify_batch(http_session, token, round_ids,
                             f"  Round {i} (seq={i})", totals)

        total_invoices = sum(len(r) for r in rounds)
        print(f"\n    ✓ Total verified: {totals['ok']} / {total_invoices}")
        if totals["failed"]:
            print(f"    ✗ Failed:         {len(totals['failed'])}"
                  f"  →  IDs: {totals['failed'][:10]}")

    finally:
        cur.close()
        conn.close()

    # ── Step 7: DB Audit ──────────────────────────────────────────
    print("\n[7] DB Audit...")
    conn2 = psycopg2.connect(DATABASE_URL)
    cur2  = conn2.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # User credit stats
    cur2.execute("""
        SELECT
            COUNT(*)                              AS total_users,
            COUNT(DISTINCT credit_balance)        AS distinct_tiers,
            MIN(credit_balance)                   AS min_credit,
            MAX(credit_balance)                   AS max_credit,
            ROUND(AVG(credit_balance)::numeric,0) AS avg_credit,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY credit_balance)::int
                                                  AS median_credit,
            COUNT(*) FILTER (WHERE credit_balance = 0) AS zero_count
        FROM users
        WHERE email LIKE %s
    """, (SEED_DOMAIN,))
    stats = cur2.fetchone()

    print(f"\n    ── User credit balances ──────────────────────────────")
    print(f"    Users:          {stats['total_users']}")
    print(f"    Distinct tiers: {stats['distinct_tiers']}")
    print(f"    Min:            {stats['min_credit']} cr")
    print(f"    Max:            {stats['max_credit']} cr")
    print(f"    Avg:            {stats['avg_credit']} cr")
    print(f"    Median:         {stats['median_credit']} cr")
    print(f"    Zero-balance:   {stats['zero_count']}")

    # Tier distribution
    cur2.execute("""
        SELECT credit_balance, COUNT(*) AS cnt
        FROM users
        WHERE email LIKE %s
        GROUP BY credit_balance
        ORDER BY credit_balance
    """, (SEED_DOMAIN,))
    tiers = cur2.fetchall()
    print(f"\n    ── Credit tier breakdown ─────────────────────────────")
    for t in tiers:
        bar = "█" * (t["cnt"] // 5)
        print(f"    {t['credit_balance']:>5} cr → {t['cnt']:>4} users  {bar}")

    # Invoice audit
    cur2.execute("""
        SELECT
            COUNT(*)                                      AS total_invoices,
            COUNT(*) FILTER (WHERE status = 'verified')  AS verified,
            COUNT(*) FILTER (WHERE status = 'pending')   AS pending,
            COUNT(DISTINCT credit_amount)                 AS distinct_amounts,
            COUNT(DISTINCT payment_reference)             AS unique_refs,
            string_agg(DISTINCT credit_amount::text, ', '
                       ORDER BY credit_amount::text)      AS amounts_used
        FROM invoice_requests
        WHERE payment_reference LIKE %s
    """, (REF_PREFIX + "%",))
    inv = cur2.fetchone()

    print(f"\n    ── InvoiceRequests ───────────────────────────────────")
    print(f"    Total invoices: {inv['total_invoices']}")
    print(f"    Verified:       {inv['verified']}")
    print(f"    Pending:        {inv['pending']}")
    print(f"    Unique refs:    {inv['unique_refs']}")
    print(f"    Distinct amts:  {inv['distinct_amounts']}  ({inv['amounts_used']} cr)")

    cur2.close()
    conn2.close()

    # ── Final result ──────────────────────────────────────────────
    passed = (
        totals["ok"] == total_invoices
        and int(stats["zero_count"]) == 0
        and int(inv["pending"]) == 0
        and inv["distinct_amounts"] == 3          # only Bronze/Silver/Gold amounts
    )
    print("\n" + "=" * 65)
    if passed:
        print("  RESULT: ALL PASSED ✓")
        print("  → Every credit is backed by a package-based verified invoice")
        print(f"  → Only Bronze/Silver/Gold amounts used (100 / 500 / 1000 cr)")
    else:
        print(f"  RESULT: PARTIAL — verify={totals['ok']}/{total_invoices}, "
              f"zero={stats['zero_count']}, pending={inv['pending']}")
    print("=" * 65)


if __name__ == "__main__":
    main()
