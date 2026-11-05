# ADR 0017 — P2 : substitutions d'outils par rapport aux exemples du cours

- Statut : proposé
- Date de proposition : 2026-11-04
- Auteur(s) : Brian Perret (tech lead), avec l'assistant IA
- Questions concernées : sans objet
- Validation : à confirmer (date, validateurs et lien vers CR/restitution)
- Remplace / remplacée par : sans objet

## Contexte

Les supports citent des outils typiques d'un SI de génération 2 (ELK, Rundeck, nginx…). L'équipe dispose de quelques semaines et de VM modestes.

## Décision proposée

| Fonction | Exemple courant | Choix | Raison |
| --- | --- | --- | --- |
| Reverse proxy + WAF | nginx | Apache + ModSecurity 2 + OWASP CRS 3.3 | `mod_proxy_hcheck` fait des health checks **actifs** des serveurs d'app (nginx libre ne fait que du passif) ; ModSecurity 2 + CRS empaquetés et branchés d'office dans Debian |
| Journaux centralisés | ELK | rsyslog (TCP, file disque) vers `monitoring`, un fichier par serveur et programme | Elasticsearch demande plus de mémoire que toute la P2 ; même fonction (centraliser, conserver) |
| Ordonnanceur | Rundeck / cron central | Timers systemd sur `scheduler` | Une seule tâche planifiée ; journalisée par journald |
| Supervision | Zabbix + mail | Zabbix 7.0 + webhook Discord (proposition du chantier P2, ADR 0012) | Le port 25 est bloqué sur Compute Engine |
| Système | Debian 12 | Debian 13 (PostgreSQL 17, Patroni 4, RabbitMQ 4.0, Python 3.13 : tous dans la distribution) | Une seule source de paquets, pas de dépôt tiers |

## Conséquences

À dire en soutenance : ces choix gardent la nature P2 (logiciel installé et exploité dans des VM), avec un outillage plus léger.

## Références

[`infra/p2/ansible/`](../../infra/p2/ansible/), [ADR 0012](0012-p2-supervision-zabbix.md).
