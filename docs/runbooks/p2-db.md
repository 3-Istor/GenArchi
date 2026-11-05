# P2 — Base de données (PostgreSQL 17 + Patroni)

Rappel : deux serveurs PostgreSQL (`db-1` en DC1, `db-2` en DC2), réplication **synchrone** (RPO = 0), arbitrage par un quorum etcd à trois membres (`db-1`, `db-2`, `witness` en zone c). L'app se connecte à `db.p2.genarchi.internal`, IP virtuelle portée par un load balancer interne dont la sonde (`GET :8008/primary`) ne répond 200 que sur le primaire.

## État du cluster

```bash
make p2-db-status
```

Attendu : un `Leader` et un `Sync Standby`, `Lag in MB` à 0.

## Le primaire tombe (panne non planifiée)

**Symptômes** : alerte Zabbix « db-x unreachable », erreurs 503 pendant ~30 s.

Patroni bascule seul : le réplica synchrone devient primaire après l'expiration du verrou (30 s), la sonde du LB suit en ~6 s. L'humain **vérifie** et **réintègre** :

1. `make p2-db-status` : le nouveau primaire est `Leader`.
2. `make p2-smoke` : vert.
3. Réparer l'ancien primaire (redémarrer la VM, ou la recréer avec `make p2-apply`).
4. Au redémarrage, Patroni le réintègre comme réplica (`pg_rewind`). S'il refuse : `make p2-ssh HOST=db-1` puis `sudo -u postgres patronictl -c /etc/patroni/config.yml reinit genarchi db-1`.

> Bascule strictement manuelle : `sudo -u postgres patronictl -c /etc/patroni/config.yml pause` désactive la bascule automatique (mode maintenance). Une panne du primaire demande alors `patronictl failover`.

## Bascule planifiée (patch, test T4)

```bash
make p2-db-switchover CANDIDATE=db-2
```

Interruption : quelques secondes ; les connexions sont rétablies par le pool de l'app.

## Restaurer (erreur humaine, corruption)

Barman (`backup`, zone c) reçoit les WAL en continu (slot `barman`) et fait une sauvegarde complète chaque nuit. RPO ≈ quelques secondes.

1. `make p2-backup-status` : liste des sauvegardes.
2. Choisir l'instant cible, **avant** l'erreur.
3. Mettre le cluster en pause : `patronictl pause`, arrêter `patroni` sur les deux serveurs.
4. Sur `backup` : `barman recover --remote-ssh-command "ssh postgres@db-1" --target-time "AAAA-MM-JJ HH:MM:SS" genarchi latest /var/lib/postgresql/17/genarchi` (accès SSH de `barman` vers `postgres@db-1` à ouvrir pour l'occasion).
5. Démarrer Patroni sur `db-1` (il devient primaire), puis `patronictl reinit genarchi db-2`, puis `patronictl resume`.
6. `make p2-smoke`. Consigner l'incident.

Tester la restauration au moins une fois avant la soutenance (preuve T6) : une sauvegarde jamais restaurée n'est pas une sauvegarde.
