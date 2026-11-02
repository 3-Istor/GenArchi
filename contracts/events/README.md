# Contrats d'événements

Contrat `0.1.0`. Format d'enveloppe : **CloudEvents 1.0, mode structuré JSON** (`application/cloudevents+json`).

En **P3**, ces événements circulent sur Pub/Sub (c'est le cœur de l'architecture *event-driven*).
En **P2**, il n'y a **pas de bus** : c'est voulu (*data-driven*). L'état `pending` des billets en base joue le rôle de file d'attente, lue par le batch `issue-pending`. Les schémas `data` restent la référence pour le contenu métier, ce qui permet d'écrire **une seule fonction d'émission** appelée par les deux déclencheurs.

## Catalogue

| `type` | Producteur | Consommateur(s) | Topic Pub/Sub (P3) | Schéma `data` |
|---|---|---|---|---|
| `fr.genarchi.ticket.purchased.v1` | `api`, après commit de la commande | `worker` (émission des QR), abonnement BigQuery (stats, bonus) | `ticket-purchased` | [`ticket-purchased.v1.schema.json`](ticket-purchased.v1.schema.json) |
| `fr.genarchi.ticket.issued.v1` | `worker`, après écriture du QR | Aucun obligatoire (notification, stats) | `ticket-issued` | [`ticket-issued.v1.schema.json`](ticket-issued.v1.schema.json) |

## Attributs d'enveloppe obligatoires

| Attribut | Valeur |
|---|---|
| `specversion` | `1.0` |
| `id` | UUID unique par événement émis (sert à la déduplication) |
| `source` | `//genarchi/{platform}/{process}` ex. `//genarchi/p3/api` |
| `type` | voir catalogue |
| `time` | RFC 3339 UTC |
| `datacontenttype` | `application/json` |
| `subject` | `orders/{order_id}` ou `tickets/{ticket_id}` |
| `traceparent` | (extension) W3C Trace Context, pour relier la trace HTTP et le traitement asynchrone |

Les attributs Pub/Sub du message reprennent `ce-type` et `ce-id` pour permettre le filtrage par abonnement.

## Garanties de livraison

- **At-least-once** : un consommateur peut recevoir le même événement plusieurs fois, y compris depuis deux régions. Il doit être **idempotent** (invariant I5 du modèle).
- **Pas d'ordre garanti** entre événements.
- **Perte à la publication** (l'API a commité la commande mais la publication a échoué) : rattrapée par le *sweeper* P3, qui republie les billets `pending` depuis plus de 2 minutes (voir `contracts/platforms/platform3.md`).
- Dead-letter après **5** tentatives vers le topic `ticket-purchased-dlq`, avec alerte.

## Évolution

- Ajouter un champ optionnel = compatible, même `type`.
- Supprimer ou renommer un champ = nouveau `type` en `.v2`, publié en parallèle de `.v1` le temps de migrer les consommateurs.

## Exemple

```json
{
  "specversion": "1.0",
  "id": "8f6b2a0e-3c1d-4d5e-9a7b-1f2e3d4c5b6a",
  "source": "//genarchi/p3/api",
  "type": "fr.genarchi.ticket.purchased.v1",
  "time": "2026-12-04T17:00:01.234Z",
  "datacontenttype": "application/json",
  "subject": "orders/ord_5c2f",
  "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
  "data": {
    "order_id": "ord_5c2f",
    "event_id": "evt_gala2026",
    "ticket_ids": ["tkt_a1", "tkt_a2"],
    "quantity": 2,
    "amount_cents": 5000,
    "buyer_email": "alice@example.com",
    "purchased_at": "2026-12-04T17:00:01.200Z"
  }
}
```
