# ADR 0018 — P2 : réglages de bascule (Patroni, pool, sonde Apache, erreurs JSON)

- Statut : proposé
- Date de proposition : 2026-11-16
- Auteur(s) : Hugo, avec l'assistant IA, d'après les décisions de Brian Perret (tech lead) du 2026-11-15
- Questions concernées : Q-001, Q-010 (seuils de résilience, à confirmer)
- Validation : décisions du tech lead rapportées par Hugo le 2026-11-16 ; statut à confirmer par l'équipe
- Remplace / remplacée par : précise [0015](0015-p2-clusters-etat-de-l-art.md) (réglages, pas l'architecture)

## Contexte

Au labo P2 (2026-11-13), la perte du primaire PostgreSQL coupait le service 50 s : 36 s pour Patroni (`ttl 30`, `loop_wait 10`), environ 5 s pour l'IP virtuelle, puis la reconnexion des pools. Le délai entre deux tentatives de `psycopg_pool` double sans limite : un serveur d'app est revenu 24 s après la base. Apache sondait `/readyz`, qui dépend de la base : il retirait tous les serveurs ensemble et le client recevait une page HTML d'Apache au lieu du 503 JSON de l'app.

## Décision

| Point | Avant | Après |
| --- | --- | --- |
| Patroni (`bootstrap.dcs`) | `ttl 30`, `loop_wait 10`, `retry_timeout 10` | `ttl 20`, `loop_wait 5`, `retry_timeout 5` (règle `loop_wait + 2 × retry_timeout ≤ ttl`) |
| Pool de l'app | délai doublé sans plafond | plafond de 5 s, sans abandon (`reconnect_timeout` infini) |
| Sonde Apache | `/readyz`, `hcpasses=2` | `/healthz`, `hcpasses=1` (`hcfails=2`, 5 s inchangés) |
| Erreurs d'Apache | pages HTML | 502/503/504 en `problem+json` (`code: unavailable`), `Retry-After: 5` si absent |

## Conséquences

- La bascule du primaire passe de 43 à 50 s à **30 s** (labo, 2026-11-16 ; détail dans [`infra/p2/README.md`](../../infra/p2/README.md)). Le runbook [`p2-db.md`](../runbooks/p2-db.md) donne ce délai.
- Pendant la bascule, le pool attend jusqu'à 5 s une connexion (`timeout=5`) avant de répondre 503 : un client qui abandonne avant 5 s voit un délai dépassé plutôt que l'erreur JSON. Réduire cette attente reste à décider.
- Base absente, les serveurs d'app restent en rotation et répondent eux-mêmes 503 avec `Retry-After: 2` : le client a toujours une erreur exploitable. Un serveur arrêté sort toujours en ~10 s.
- Un `ttl` plus court rend Patroni plus sensible aux coupures réseau courtes vers etcd : ne pas descendre en dessous sans mesure.
- Les valeurs Patroni ne s'appliquent qu'à la création du cluster ; sur un cluster existant : `patronictl edit-config`.
- Le plafond du pool remplace une classe interne de `psycopg_pool` 3.3 ; `app/tests/test_pool_backoff.py` échoue si une montée de version le défait.
- Contrat d'exécution mis à jour ([`app-runtime.md`](../../contracts/runtime/app-runtime.md)).
