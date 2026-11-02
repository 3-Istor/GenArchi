# Modèle de domaine : billetterie

Contrat `0.1.0`. Indépendant du stockage : PostgreSQL (P2) et Firestore (P3) doivent tous deux respecter ce modèle et ses invariants.

## Entités

### Event (événement à billetterie)

| Champ | Type | Règle |
|---|---|---|
| `id` | string | Opaque, généré par le serveur (UUID v4 recommandé) |
| `name` | string | 1 à 120 caractères |
| `venue` | string | 1 à 120 caractères |
| `starts_at` | datetime RFC 3339 (UTC) | Dans le futur à la création |
| `sales_open_at` | datetime RFC 3339 (UTC) | `< starts_at` |
| `capacity` | int | 1 à 100 000 |
| `remaining` | int | `0 ≤ remaining ≤ capacity` |
| `price_cents` | int | ≥ 0, en centimes d'euro |
| `currency` | string | Toujours `EUR` |
| `status` | enum | `scheduled`, `on_sale`, `sold_out`, `closed` (voir cycle de vie) |
| `created_at` | datetime | Serveur |

Cycle de vie de `status` (calculé, jamais écrit directement par un client) :

```
scheduled ──(now ≥ sales_open_at)──▶ on_sale ──(remaining = 0)──▶ sold_out
     │                                  │                             │
     └──────────────(now ≥ starts_at)───┴─────────────────────────────┴──▶ closed
```

### Order (commande)

| Champ | Type | Règle |
|---|---|---|
| `id` | string | Opaque |
| `event_id` | string | Référence un Event existant |
| `buyer_email` | string (email) | Obligatoire |
| `quantity` | int | 1 à 4 |
| `amount_cents` | int | `quantity × price_cents` au moment de l'achat |
| `status` | enum | `confirmed` (une commande refusée n'est pas créée : l'API renvoie une erreur) |
| `idempotency_key` | string | Fourni par le client via l'en-tête `Idempotency-Key` |
| `ticket_ids` | string[] | Exactement `quantity` éléments |
| `created_at` | datetime | Serveur |

### Ticket (billet)

| Champ | Type | Règle |
|---|---|---|
| `id` | string | Opaque, non devinable (≥ 122 bits d'aléa) |
| `order_id`, `event_id` | string | Références |
| `status` | enum | `pending` → `issued` → `scanned` |
| `qr_object` | string \| null | Clé du fichier QR dans le stockage blob, `null` tant que `pending` |
| `issued_at` | datetime \| null | Renseigné au passage à `issued` |
| `scanned_at` | datetime \| null | Renseigné au premier scan |

```
pending ──(génération du QR par le worker)──▶ issued ──(premier scan)──▶ scanned
```

## Invariants (testés par `contracts/tests/acceptance.md`)

| ID | Invariant |
|---|---|
| **I1 — Pas de survente** | À tout instant, pour un événement : `remaining = capacity − Σ quantity des commandes confirmées`, et `remaining ≥ 0`. Le décrément du stock et la création de la commande + billets se font dans **une seule transaction atomique**. |
| **I2 — Achat idempotent** | Deux `POST /events/{id}/orders` avec le même `Idempotency-Key` (même événement) renvoient la même commande ; le stock n'est décrémenté qu'une fois. Une même clé réutilisée avec un corps différent → `409 idempotency_conflict`. Les clés sont conservées au moins 24 h. |
| **I3 — Scan idempotent** | Le premier `POST /tickets/{id}/scan` d'un billet `issued` le passe en `scanned` (200). Tout scan suivant renvoie `409 already_scanned` avec le `scanned_at` d'origine. Un billet `pending` n'est pas scannable (`409 ticket_not_issued`). |
| **I4 — Émission garantie** | Tout billet `pending` finit `issued`. Délai maximal défini **par plateforme** (P2 : batch ≤ 15 min ; P3 : p95 ≤ 10 s). |
| **I5 — Émission idempotente** | Émettre deux fois le même billet produit le même objet QR (clé déterministe `tickets/{event_id}/{ticket_id}.png`) et ne change pas `issued_at` s'il était déjà renseigné. Indispensable car la livraison d'événements est *at-least-once*. |
| **I6 — Pas d'état local** | Aucune donnée métier n'est conservée dans le processus ou sur son disque local. Tuer une instance ne perd rien. |

## Contenu du QR code

Le QR encode l'URL `${PUBLIC_BASE_URL}/t/{ticket_id}`. Pas de donnée personnelle dans le QR.

## Correspondance stockage (indicative, détaillée dans les docs d'architecture)

| Concept | P2 — PostgreSQL | P3 — Firestore |
|---|---|---|
| Event | table `events` | collection `events` |
| Order | table `orders` (+ index unique `(event_id, idempotency_key)`) | collection `orders`, doc id = `sha256(event_id + idempotency_key)` |
| Ticket | table `tickets` | collection `tickets` |
| Atomicité I1 | `UPDATE events SET remaining = remaining - $q WHERE id = $id AND remaining >= $q` dans une transaction | Transaction Firestore lisant `events/{id}` puis écrivant event + order + tickets |
