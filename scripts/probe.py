"""Sonde de résilience : achète en continu et mesure ce que voit un client pendant une panne.

    python3 scripts/probe.py <BASE_URL> <ADMIN_TOKEN> --seconds 120 --rate 5

Crée un événement, envoie `rate` commandes par seconde (chacune avec sa clé d'idempotence, rejouée une fois
en cas d'échec comme le ferait un client), puis affiche : taux de succès, plus longue interruption,
billets émis à la fin. Sans dépendance : bibliothèque standard Python.
"""

import argparse
import json
import time
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime, timedelta


def call(method, url, body=None, headers=None, timeout=5):
    if not url.startswith(("http://", "https://")):
        raise ValueError(url)
    req = urllib.request.Request(  # noqa: S310 (schéma vérifié ci-dessus)
        url,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (URL fournie par l'opérateur)
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:  # connexion refusée, timeout : compté comme échec
        return 0, None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("base")
    p.add_argument("admin_token")
    p.add_argument("--seconds", type=int, default=120)
    p.add_argument("--rate", type=float, default=5)
    a = p.parse_args()
    now = datetime.now(UTC)
    st, ev = call(
        "POST",
        f"{a.base}/events",
        {
            "name": f"Sonde {now:%H:%M:%S}",
            "venue": "EPITA",
            "capacity": 100000,
            "price_cents": 100,
            "starts_at": (now + timedelta(days=30)).isoformat(),
            "sales_open_at": (now - timedelta(minutes=1)).isoformat(),
        },
        {"Authorization": f"Bearer {a.admin_token}"},
    )
    if st != 201:
        raise SystemExit(f"création d'événement impossible ({st})")
    ok = ko = streak = 0
    tickets, last_ok, worst_gap = [], time.monotonic(), 0.0
    end = time.monotonic() + a.seconds
    while time.monotonic() < end:
        t0 = time.monotonic()
        key = uuid.uuid4().hex
        for _ in range(2):  # un essai + un rejeu idempotent
            body = {"buyer_email": "probe@example.com", "quantity": 1}
            st, order = call("POST", f"{a.base}/events/{ev['id']}/orders", body, {"Idempotency-Key": key})
            if st in (200, 201):
                break
        if st in (200, 201):
            if streak:
                print(f"{datetime.now():%H:%M:%S} rétabli après {streak} échecs", flush=True)
                streak = 0
            ok += 1
            tickets.append(order["tickets"][0]["id"])
            worst_gap = max(worst_gap, time.monotonic() - last_ok)
            last_ok = time.monotonic()
        else:
            ko += 1
            if not streak:
                print(f"{datetime.now():%H:%M:%S} échecs (HTTP {st})…", flush=True)
            streak += 1
        time.sleep(max(0.0, 1 / a.rate - (time.monotonic() - t0)))
    worst_gap = max(worst_gap, time.monotonic() - last_ok)
    time.sleep(10)
    issued = sum(1 for t in tickets[-50:] if call("GET", f"{a.base}/tickets/{t}")[1].get("status") == "issued")
    _, evn = call("GET", f"{a.base}/events/{ev['id']}")
    print(
        json.dumps(
            {
                "commandes_reussies": ok,
                "commandes_en_echec": ko,
                "succes_pct": round(100 * ok / max(1, ok + ko), 2),
                "plus_longue_interruption_s": round(worst_gap, 1),
                "stock_coherent": evn["capacity"] - evn["remaining"] == ok,
                "billets_emis_sur_50_derniers": issued,
            },
            ensure_ascii=False,
            indent=1,
        )
    )


if __name__ == "__main__":
    main()
