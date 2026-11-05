# P2 — Perte d'un datacenter (zone)

Exemple : la zone `europe-west9-a` (DC1) est perdue.

| Composant | Ce qui se passe | Action humaine |
|---|---|---|
| LB public, `rp-2`, `app-1b`, `app-2b` | Le LB et Apache retirent les serveurs du DC1 (health checks) | Aucune |
| PostgreSQL | Patroni promeut `db-2` (quorum etcd : `db-2` + `witness`) | Vérifier (`make p2-db-status`) |
| RabbitMQ | Les files quorum continuent sur `mq-2` + `witness` | Aucune |
| NAS | `nas-1` perdu : les QR ne s'écrivent plus | [`p2-nas.md`](p2-nas.md) : `make p2-nas-failover TO=nas-2` |
| Ordonnanceur (`scheduler`, DC1) | Rattrapage arrêté (SPOF assumé : la file émet en temps normal) | Le recréer en DC2 si la perte dure : changer sa zone dans `infra/p2/main.tf`, `make p2-apply p2-configure` |
| Bastion, supervision, sauvegarde | En zone c, non touchés | — |

Capacité : la moitié des serveurs d'app reste. Dimensionnement vertical si besoin (`machine_types`, arrêt-relance VM par VM).

Retour à la normale, zone revenue : les VM du DC1 redémarrent ; Patroni réintègre `db-1` en réplica, RabbitMQ resynchronise ses files ; garder le NAS sur `nas-2` (pas de retour arrière inutile) ; `make p2-configure` puis `make p2-smoke`.

La perte de **la région** sort du périmètre P2 (PRA manuel : recréer la plateforme dans une autre région à partir des instantanés stockés dans l'UE et des sauvegardes Barman).
