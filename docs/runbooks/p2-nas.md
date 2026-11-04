# P2 — Bascule du NAS (QR des billets)

Rappel : les QR sont écrits sur un disque **régional** (répliqué de façon synchrone entre DC1 et DC2), monté par un seul serveur à la fois (`nas-1` ou `nas-2`) et partagé en NFS. Les serveurs d'app montent `nas.p2.genarchi.internal`, IP virtuelle d'un load balancer interne dont la sonde (TCP 2049) ne voit que le NAS qui sert.

## Symptômes

- Les billets restent `pending` (l'émission bloque sur l'écriture du QR : montage NFS *hard*) ;
- alerte Zabbix sur `nas-1` ; `GET /tickets/{id}/qr` lent ou en erreur.

## Diagnostic

```bash
make p2-ssh HOST=nas-1        # répond ? `systemctl status nfs-server`, `mount | grep tickets`
gcloud compute backend-services get-health p2-nas --region europe-west9
```

Ne basculer que si `nas-1` est réellement perdu (VM ou zone). Un simple redémarrage de NFS se règle sur place.

## Bascule

```bash
make p2-nas-failover TO=nas-2
```

Le script isole l'ancien NAS s'il répond, **attache de force** le disque à `nas-2` (l'ancien perd l'accès : c'est le fencing, pas de double montage possible), monte le disque, démarre NFS et attend que l'IP virtuelle suive.

Puis, pour que l'outillage reste aligné :

1. dans `infra/p2/env.mk` : `P2_NAS_ACTIVE ?= nas-2` ;
2. `make p2-apply` (OpenTofu reprend le nouvel attachement) puis `make p2-configure`.

## Vérification

- Les billets `pending` sont émis : les consommateurs RabbitMQ réessaient, le rattrapage (`scheduler`, toutes les 5 min) termine le reste ;
- `make p2-smoke` vert.

RTO visé : 15 min (décision + exécution). RPO : 0 (réplication synchrone du disque). En dernier recours, les instantanés horaires (`p2-snapshots-hourly`, copiés dans l'UE) permettent de recréer le disque.
