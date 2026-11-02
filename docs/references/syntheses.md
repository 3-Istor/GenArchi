# Synthèses des supports

Ces notes retiennent le contexte utile au projet. Pour les limites de lecture et les noms d’origine, consulter l’[index des sources](README.md).

## Kickoff

Source : [kickoff](originaux/kickoff.pptx), proposition de travail datée du 1er novembre 2026.

- **Mission et preuves** — diapositives 2–3 : même application, deux déploiements Terraform, fonctionnement et résilience à montrer ; critères, dates officielles et budget encore ouverts.
- **Pistes P2/P3** — diapositives 4–6 : P2 illustrée par un load balancer, des VM redondées et une DB primaire/réplique dont la bascule reste à définir ; P3 illustrée par des instances remplaçables, des données externes et l’auto-reprise. Ce sont des exemples à discuter.
- **MVP** — diapositive 7 : priorité aux deux déploiements, à un scénario de panne vérifié par plateforme et à une comparaison étayée. Les approfondissements viennent ensuite.
- **Organisation et dates** — diapositives 8–9 : proposition de six personnes, conception commune puis chantiers P2/P3 parallèles ; cible interne de démonstration au 15 décembre 2026.
- **Coaching** — diapositives 10–11 : préparer les questions sur la résilience, la différenciation P2/P3, Terraform, les environnements et l’évaluation ; choisir les technologies après clarification.

À retenir pour le dépôt : séparer les propositions du kickoff des consignes du TD et conserver les incertitudes dans le [cadrage](../cadrage.md).

## Cours 1

Source : [Cours 1 & TD 1](originaux/cours-1-td-1.pptx).

- **TD** — diapositive 5 : construire une application web résiliente en P2 et P3 ; livrer deux Terraforms ; environ trois suivis et une soutenance.
- **Différence de générations** — diapositive 8 : passage d’une approche centrée sur l’infrastructure et sa redondance à une approche centrée sur l’application et sa résilience ; image « pets to cattle ».
- **Architecture et exploitation** — diapositive 10 : comparaison des modes de calcul, stockage, réseau, déploiement et reprise. Les exemples vont de la virtualisation à des usages de services cloud.
- **Organisation** — diapositives 11–12 : générations hétérogènes dans un SI ; rapprochement entre architecture, pratiques d’exploitation et automatisation.
- **Prudence d’interprétation** — diapositive 17 : les modèles donnent des tendances et doivent être confrontés au besoin.

À retenir : la diapositive 5 fonde le livrable pédagogique ; les tableaux comparatifs aident à argumenter les architectures sans déterminer seuls les technologies.

## Cours 2

Source : [P2 — Infrastructure](originaux/cours-2-p2-infra.pptx).

- **Piliers** — diapositive 5 : calculer, communiquer, persister ; examiner serveur, réseau et stockage ensemble.
- **Calcul et virtualisation** — diapositives 7–14 : ressources, isolation, mutualisation, consolidation et critères de choix selon le besoin. La haute disponibilité est abordée via le clustering.
- **Réseau et entrée du service** — diapositives 17–26 : adressage, protocoles, segmentation, redondance réseau et services IP ; la diapositive 25 présente l’équilibrage de charge et le failover.
- **Données** — diapositives 29–37 : distinguer stockage, sauvegarde et archivage ; choix block/file/object, réplication et contraintes de distance. La diapositive 37 pose la question du besoin RTO/RPO et du synchrone/asynchrone.

À retenir : justifier les points de défaillance et les choix de redondance de P2. Aucun objectif RTO/RPO chiffré n’est fixé ici pour le TD.

## Cours 3

Source : [P2 — Middleware](originaux/cours-3-p2-middleware.pptx).

- **Rôle** — diapositives 5–6 : logiciels intermédiaires et familles orientées données ou traitements ; la frontière avec l’infrastructure dépend du contexte.
- **Persistance** — diapositives 7–9 : familles de bases, compromis de cohérence/disponibilité et fonctions de sécurité, disponibilité, sauvegarde et traçabilité.
- **Échanges** — diapositives 11–16 : ETL, messages, transfert et partage de fichiers, avec des usages et besoins différents.
- **Exécution web** — diapositives 17–18 : serveurs web et applicatifs, équilibrage de charge et disponibilité.
- **Autres intégrations** — diapositives 20–23 : transactions, EAI/ESB, planification et orchestration de traitements.

À retenir : sélectionner les middlewares nécessaires à l’application choisie. Le catalogue pédagogique n’impose pas d’installer chaque famille.

## Cours 4

Source : [P3 — Architecture & Production](originaux/cours-4-p3-architecture-production.pptx).

- **Orientations P3** — diapositive 5 : comparaison P2/P3 sur architecture, hébergement, delivery, scalabilité et exploitation ; ces tendances ne sont pas une prescription de microservices pour le TD.
- **Code et configuration** — diapositives 10–14 : code versionné, dépendances déclarées, configuration séparée, ressources externes et distinction build/release/run.
- **Processus** — diapositives 15–20 : état persistant externalisé, processus jetables, arrêt gracieux, parité des environnements et logs en flux.
- **Observation et réparation** — diapositives 21–31 : supervision par couche ; la diapositive 31 décrit une approche P3 où les alertes alimentent une remédiation automatisée, avec exemple de reconstruction d’instance.
- **Protection et mesures** — diapositives 32–40 : sauvegardes, restauration, mécanismes de protection des données et historique des métriques.
- **Exploitation** — diapositives 43–52 : traitements, capacité, environnements, tests de reprise, rôles et gestion des changements/incidents ; la diapositive 51 mentionne la procédure de rollback.

À retenir : préparer des preuves de comportement en panne, d’observation et de remise en état. La présence d’un conteneur ne suffit pas à démontrer l’auto-reprise.
