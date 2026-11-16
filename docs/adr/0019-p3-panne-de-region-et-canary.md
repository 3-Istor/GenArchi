# ADR 0019 — P3 : panne de région par drapeau Firestore, canary avec trafic dédié

- Statut : proposé
- Date de proposition : 2026-11-16
- Auteur(s) : Hugo, avec l'assistant IA, d'après les décisions de Brian Perret (tech lead) du 2026-11-15
- Questions concernées : Q-001 (scénarios et seuils de reprise), Q-010 (protocole de mesure), à confirmer
- Validation : décisions du tech lead rapportées par Hugo le 2026-11-16 ; statut à confirmer par l'équipe
- Remplace / remplacée par : précise [0004](0004-p3-drp-permanent-rollback-auto.md) (mécanismes, pas le principe)

## Contexte

Sur GCP (2026-11-15), le test de panne de région ne produisait aucune panne : le job changeait `CHAOS_FORCE_UNREADY`, ce qui crée une révision, et Cloud Run ne bascule le trafic que vers une révision prête ; l'ancienne a donc continué à tout servir. La canary promouvait une région sans trafic (`europe-west4` : 0 requête, promue) et `/version` affichait la version injectée par OpenTofu, pas celle de l'image servie.

## Décision

| Point | Avant | Après |
| --- | --- | --- |
| Panne de région (T4) | variable d'environnement, nouvelle révision | document Firestore `chaos/<région>` (`unready_until`), relu par `/readyz` au plus toutes les 5 s ; écrit par `genarchi chaos-region`, expire seul |
| Droits du job de panne | `run.developer`, `actAs` sur l'API, lecture des images | `roles/datastore.user` seulement |
| Routage de test | aucun | en-tête `X-GenArchi-Region` → backend de cette seule région ; sans en-tête, inchangé |
| Canary | attente passive, promotion même sans trafic | `probe.py` à 5 achats/s par région via le LB ; retour arrière sous 30 requêtes (`MIN_REQUESTS`) ou au-delà de 2 % de 5xx |
| `/version` | `APP_VERSION` injectée par OpenTofu | version inscrite dans l'image par Cloud Build |

## Conséquences

- La bascule de région repose sur la fonction *service health* de Cloud Run (readiness) : si le LB ne bascule pas alors que toutes les instances d'une région sont non prêtes, le test le montrera et la question reviendra à l'équipe.
- N'importe quel client peut fixer une région avec l'en-tête : sans privilège ni donnée en jeu, mais il contourne la bascule pour ses propres requêtes. Réservé aux tests.
- La canary crée des commandes de test (un événement « Sonde » par région et par mise en production).
- Le job de panne reçoit des jetons factices : la configuration les exige, le job ne sert aucune requête et n'accède pas aux secrets.
