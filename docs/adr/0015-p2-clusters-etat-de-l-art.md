# ADR 0015 — P2 : clusters middleware « état de l'art » dans les VM

- Statut : proposé
- Date de proposition : 2026-11-04
- Auteur(s) : Brian Perret (tech lead), avec l'assistant IA
- Questions concernées : Q-001, Q-002, Q-009 du [cadrage](../cadrage.md)
- Validation : à confirmer (date, validateurs et lien vers CR/restitution)
- Remplace / remplacée par : remplacerait les propositions [0002](0002-p2-deux-zones-bascule-manuelle.md) et [0009](0009-p2-sauvegarde-pgdump-snapshots.md) si acceptée ; prend le pas sur la version simplifiée du chantier P2 (PR #2), à la demande de Brian Perret le 2026-11-04

## Contexte

La version v0.1 de la P2 gardait plusieurs SPOF « assumés » (une base primaire à bascule manuelle, un NFS dans une seule zone, un batch d'émission toutes les 15 min). La revue du 3 novembre a demandé ce que serait **une bonne P2** : la meilleure architecture possible en n'utilisant que des composants de génération 2, c'est-à-dire des logiciels installés dans des VM, pas des services managés.

## Options étudiées

| Besoin | v0.1 | Proposition | Pourquoi c'est encore de la P2 |
| --- | --- | --- | --- |
| Base | Primaire + réplica asynchrone, promotion manuelle | PostgreSQL 17 + **Patroni**, réplication **synchrone**, quorum **etcd** à 3 membres (DC1, DC2, témoin) | Cluster actif/passif classique d'entreprise (cours 3, PAD) ; c'est l'infrastructure qui bascule, pas l'app |
| IP de la base | DNS `db-primary` changé à la main | IP virtuelle portée par un LB interne passthrough, sonde `/primary` de Patroni | Équivalent GCP d'une VIP keepalived (le VPC ignore l'ARP gratuit) |
| Fichiers | NFS sur un disque zonal | NAS **actif/passif** sur **disque régional** (réplication synchrone), bascule par runbook (`--force-attach` = fencing) | NAS bloc + NFS, bascule humaine |
| Asynchrone | Batch 15 min | **RabbitMQ** 3 nœuds, files **quorum** ; rattrapage toutes les 5 min par timer systemd | Middleware de messagerie dans des VM |
| Sauvegarde | `pg_dump` quotidien | **Barman** : WAL en continu (slot permanent) + sauvegarde complète nocturne, PITR ; instantanés de disques copiés dans l'UE | Outil de sauvegarde d'entreprise |
| Sécurité d'entrée | nginx | Apache + **ModSecurity** (règles OWASP CRS) | WAF logiciel dans la VM |

## Décision proposée

Adopter la colonne « proposition ». La bascule automatique de Patroni est assumée comme de la redondance d'infrastructure ; elle se désactive (`patronictl pause`) si l'équipe veut une P2 strictement manuelle. Le NAS reste à bascule manuelle.

## Conséquences

- 17 VM au lieu de 10 : coût plus élevé (gabarits réduits par défaut, `machine_types` réglable).
- Engagements P2 révisés (contrat P2 0.2.0) : RPO = 0 sur la base et les fichiers ; RTO base < 1 min (automatique), NAS ≤ 15 min (manuel) ; émission des QR en secondes.
- Restent des SPOF assumés : l'ordonnanceur (filet de sécurité), Barman et Zabbix (zone témoin), la région.

## Validation et suivi

Mesuré au labo (conteneurs, 2026-11-04) : primaire tué → 43 s de 503, aucune perte ; nœud RabbitMQ ou serveur d'app tué → aucune erreur client. À refaire sur GCP (tests T4, T5) avec les [modèles de preuve](../../tests/resilience/README.md).

## Références

[Spec P2](../architecture/platform2.md), [runbooks](../runbooks/README.md), [`infra/p2/`](../../infra/p2/README.md), cours 2 diapositives 25 à 37 (actif/passif, réplication), cours 3 diapositive 19 (PAD).
