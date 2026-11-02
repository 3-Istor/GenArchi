# Challenge des architectures P2 et P3

> **Objet** : avant de dessiner quoi que ce soit dans Noodle, vérifier composant par composant que la P2 est bien de la **P2** (et pas de la « P2.5 » Cloud-Ready) et que la P3 est bien de la **P3**. Valider aussi le choix serverless plutôt que Kubernetes managé.
> **À faire** : les deux tech leads relisent chaque ligne marquée ⚠️ et tranchent dans l’ADR indiquée (registre : `docs/adr/README.md`). Les ❌ sont des lignes rouges.

## 1. La grille de référence

Le cours (Cours 1, slide 10) découpe en **trois colonnes**, pas deux :

| | Col. 1 — Virtual 2 Virtual (**P2**) | Col. 2 — Cloud-Ready (**« P2.5 »**) | Col. 3 — Born 2 be Cloud (**P3**) |
|---|---|---|---|
| Compute | VM as a Service | Instance + autoscaling 1:1 sur statistiques | Pool d'instances, autoscaling sur la charge réelle, piloté par l'app |
| Stockage | Bloc | Objet | Objet |
| Réseau | VLAN, subnet /24, firewall dans la VM ou ACL | Subnet /21 + security groups | SDN, réseau centré application |
| Sauvegarde | Plan de backup existant | Mécanismes intégrés (snapshots) | Gérée par l'application (journalisation) |
| Monitoring | Alerte puis traitement manuel | Alerte + prétraitement automatique | Alerte + destruction/reconstruction automatique |
| Patching | Plan de patch existant | Rebuild mensuel | Continuous delivery |
| Résilience / DRP | Mono-AZ, DRP manuel | Dual-AZ mono-région, DRP automatisé | Multi-AZ multi-région, **test de DRP permanent** |
| Déploiement | Manuel | Automatisé (compute), user-data, « Puppet-like » | Tout automatisé, template applicatif |
| Exploitation | Infogérance | DevOps | NoOps |
| Middleware | Installé dans la VM | DBaaS | DBaaS |

**Le critère qui sépare les colonnes n'est pas « est-ce dans le cloud ? » mais « qui agit quand quelque chose change : un humain, un script, ou le système lui-même ? »**

## 2. La P2 est-elle bien de la P2 ?

| Dimension | Notre choix | Colonne réelle | Verdict | Si on veut être puriste |
|---|---|---|---|---|
| Compute | VM nommées, groupe d'instances **non managé** | 1 | ✅ | — |
| Scalabilité | Resize vertical manuel | 1 | ✅ | — |
| Stockage | Disques persistants (bloc) + NFS sur VM | 1 | ✅ | — |
| Middleware | PostgreSQL et nginx installés dans les VM | 1 | ✅ | — |
| Réseau | Sous-réseaux /24 par tier, firewall **par plage d'IP** | 1 | ✅ | — |
| Échanges | Fichiers (NFS, export CSV), batch | 1 | ✅ | — |
| Monitoring | Zabbix, alerte mail, humain | 1 | ✅ | — |
| Patching | `apt upgrade` manuel par runbook | 1 | ✅ | ❌ ne pas activer VM Manager / OS patch management |
| Exploitation | RFC + runbooks (ITIL) | 1 | ✅ | — |
| **Résilience** | **2 zones**, réplique PostgreSQL, **bascule manuelle** | entre 1 et 2 | ⚠️ ADR 0002 | Mono-zone. Mais une entreprise P2 a presque toujours deux salles ou un DC de secours (Cours 2 : « 2 DC ou 1 Dual-DC », réplication de baie). Ce qui fait la colonne 2, c'est le **DRP automatisé** : tant que la bascule est manuelle, on reste en P2 |
| **Sauvegarde** | `pg_dump` + **snapshots planifiés de disques** | 1 + un peu de 2 | ⚠️ ADR 0009 | Garder seulement `pg_dump` vers NFS. Défense du snapshot : c'est une fonction de **baie de stockage** P2 (Cours 2, slide 34), pas une invention cloud |
| **Déploiement** | Terraform + Ansible pour **construire** | 2 pour le build | ⚠️ ADR 0010 | Impossible d'être puriste : 2 Terraform sont le livrable imposé. Règle proposée : **build automatisé, run manuel**. Ansible ne sert qu'à l'installation initiale ; mise en prod, patch et bascule sont des runbooks exécutés à la main (commandes SSH), pas des playbooks |
| **Équipements réseau** | LB régional managé, Cloud NAT, Cloud DNS privé, tunnel IAP vers le bastion | 1 (équivalents d'appliances) | ⚠️ ADR 0006 | LB = l'appliance F5 du DC, NAT = la passerelle internet, DNS = service IP du cours. IAP est l'élément le plus « moderne » : alternative = bastion avec IP publique filtrée sur l'IP de l'école |

### Lignes rouges P2 (elles feraient basculer en P2.5)

- ❌ Managed Instance Group, autoscaler, **autohealing**
- ❌ Cloud SQL ou tout DBaaS
- ❌ **Patroni, repmgr ou pg_auto_failover** : une bascule de base automatique, c'est le « DRP automatisé » de la colonne 2. La bascule reste un runbook
- ❌ Alerte qui déclenche une action automatique (redémarrage auto par Zabbix, Cloud Functions…)
- ❌ Docker sur les VM
- ❌ Bucket Cloud Storage pour les données de l'app
- ❌ Pipeline CI qui déploie l'app sur les VM

Les lignes rouges « ressources » sont vérifiées en CI par `scripts/check_boundary.py`. Les lignes rouges « processus » sont dans la checklist de revue de PR.

**Conclusion P2** : c'est bien de la P2, avec **4 écarts assumés** (dual-zone, snapshots, build en IaC, équipements réseau managés). Les présenter tels quels en soutenance : montrer qu'on sait où passe la frontière vaut mieux que prétendre une pureté impossible sur GCP.

## 3. La P3 est-elle bien de la P3 ?

| Dimension | Notre choix | Colonne | Verdict | Point de vigilance |
|---|---|---|---|---|
| Compute | Cloud Run, autoscaling sur la concurrence réelle | 3 | ✅ | — |
| Stockage | Cloud Storage, versioning | 3 | ✅ | — |
| Middleware | Firestore (DBaaS NoSQL multi-région) | 3 | ✅ | — |
| Réseau | Pas de VPC applicatif, contrôle par identité (IAM), ingress | 3 | ✅ | — |
| Sauvegarde | PITR Firestore, versioning GCS | 3 | ✅ | — |
| Patching | Rebuild à chaque build + hebdomadaire | 3 | ✅ | Le rebuild hebdo doit exister vraiment (workflow planifié) |
| Déploiement | Terraform + CI, canary | 3 | ✅ | Zéro clic console, zéro `gcloud` manuel |
| Exploitation | SLO, error budget, rollback automatique | 3 | ✅ | — |
| Architecture | Event-driven (Pub/Sub), 2 services | 3 | ✅ | — |
| **Monitoring** | Cloud Run remplace les instances ; canary avec rollback auto | 3 si démontré | ⚠️ | Il faut **au moins une alerte qui déclenche une action automatique**, montrée en démo (le rollback canary). Sinon c'est la colonne 2 |
| **Résilience / DRP** | 2 régions actives, bascule auto | 2 **sans** le chaos, 3 **avec** | ⚠️ | Le **test de DRP permanent** (chaos nocturne `p3-chaos`) est ce qui fait la colonne 3. Il est donc **obligatoire**, pas un bonus |
| **Sweeper** | Job planifié toutes les 5 min | — | ⚠️ ADR 0011 | Ressemble à un batch. Défense : c'est un filet de réconciliation, pas le traitement métier. Alternative à évaluer : trigger Eventarc sur création de document Firestore (supprime la double écriture base + publication) |

### Lignes rouges P3 (elles feraient retomber en Cloud-Ready)

- ❌ Une seule région, ou une base zonale (Cloud SQL sans multi-région)
- ❌ Pas de test de bascule permanent
- ❌ Déploiement ou correction à la main
- ❌ État dans les instances (sessions, fichiers locaux)
- ❌ Traitement métier par batch planifié
- ❌ VM, même « juste pour un petit truc »

**Conclusion P3** : c'est bien de la P3 **à condition** de livrer le chaos nocturne et le rollback automatique, qui étaient présentés comme des bonus dans le cadrage et deviennent obligatoires.

## 4. Serverless plutôt que Kubernetes managé

### Le choix

**Cloud Run services** (serverless de containers), pas Kubernetes managé (GKE Autopilot), et pas Cloud Run *functions* (le vrai équivalent de Lambda).

| Critère | Cloud Run services ✅ | Cloud Run functions (≈ Lambda) | GKE Autopilot |
|---|---|---|---|
| Colonne P3 du cours | Oui (« container ») | Oui (« lambda ») | Oui (« container », slide orchestration) |
| Unité déployée | Une image container standard | Une fonction par point d'entrée | Des pods, services, ingress, HPA… |
| Multi-région + bascule auto | Natif (service health + LB global) | Possible, plus de plomberie | 2 clusters + Multi Cluster Gateway |
| Ce qu'il faut exploiter | Presque rien | Presque rien, mais beaucoup de petits morceaux | Le cluster, les manifests, les quotas, les montées de version |
| Coût à notre trafic | Proche de 0 hors min instances | Proche de 0 | Frais de gestion par cluster + pods ; 2 clusters pour le multi-région |
| Tourne en local tel quel | Oui (`docker run`) | Partiellement (framework) | Oui, mais il faut un cluster local |
| Portabilité | Image standard ; API compatible Knative | Faible (modèle de fonction propriétaire) | Forte |
| Temps de mise en place pour l'équipe | Faible | Faible | Élevé |

**Pourquoi pas des « vraies lambdas » (functions)** : on garde un seul code et une seule image pour `api` et `worker`. Découper en une fonction par route mènerait à des nano-services (voir § 5, point 9) et casserait l'idée « une même app sur P2 et P3 ».

**Pourquoi pas Kubernetes** : pour **une** application, Kubernetes est une plateforme à construire avant de pouvoir s'en servir. Le multi-région demande deux clusters et une passerelle multi-cluster. Le temps passé irait dans le cluster plutôt que dans la démonstration P2 → P3. Kubernetes devient le bon choix avec beaucoup de services, une charge soutenue, des besoins de sidecars, de stateful ou de GPU, ou une exigence de portabilité multi-cloud.

**À dire en soutenance** : la slide « orchestration de containers » du cours (self-healing, scaling horizontal, rollouts, découverte de services, secrets) est couverte par Cloud Run, mais c'est Google qui opère l'orchestrateur. C'est du NoOps poussé plus loin que Kubernetes.

## 5. « Le serverless est souvent une fausse bonne idée » : pourquoi les architectes le disent

Le serverless promet « pas de serveur, pas d'ops, on paie à l'usage ». Chaque promesse a un revers. Le cas d'école : en 2023, l'équipe de monitoring vidéo de **Prime Video** a remplacé une architecture Step Functions + Lambda par un seul processus sur ECS. Le service bloquait à environ 5 % de la charge visée ; la refonte a réduit le coût d'infrastructure de plus de 90 %.

| # | Argument | Ce qui se passe | Nous concerne ? | Notre parade |
|---|---|---|---|---|
| 1 | **Démarrages à froid** | Une instance neuve met du temps à démarrer : la latence p99 s'envole aux pics | Oui, au moment de l'ouverture des ventes | `min_instances = 1` par région, CPU boost, image légère |
| 2 | **Cher à charge forte et constante** | Payer à la seconde ou à la requête coûte plus cher que des machines réservées, dès que la charge est stable et élevée | Non : trafic faible avec des pics | Le comparer chiffres à l'appui (tableau de scores) |
| 3 | **Le goulot glisse vers la base** | 500 instances × N connexions saturent une base SQL classique | Non avec Firestore ; **oui si on prenait Cloud SQL** | Firestore ; sinon pool de connexions + `max_instances` |
| 4 | **Limites d'exécution** | Durée maximale par requête, mémoire et CPU plafonnés, pas de disque, connexions longues mal supportées | Non : requêtes courtes | — |
| 5 | **La complexité ne disparaît pas, elle se déplace** | « No ops » devient IAM, retries, idempotence, files d'erreur, quotas. Déboguer un système distribué est plus dur qu'un monolithe | **Oui, c'est notre vrai coût** | Contrats I5 (idempotence), DLQ, traces OpenTelemetry, tests de contrat |
| 6 | **Enfermement chez le fournisseur** | Déclencheurs, formats d'événements et IAM propriétaires | Partiellement | Image container standard, CloudEvents, adaptateurs |
| 7 | **Facture imprévisible** | Un pic, un bug en boucle ou une attaque font exploser le coût (« denial of wallet ») | Oui | `max_instances`, rate limit Cloud Armor, alertes budget |
| 8 | **Moins de contrôle** | Pas la main sur l'OS, le réseau fin ou certaines contraintes de conformité | Non | — |
| 9 | **Nano-services** | Une fonction par route donne un « monolithe distribué » : bavard, lent, cher (le problème de Prime Video) | Non : 2 services seulement | Découper par responsabilité, pas par endpoint |

### Quand le serverless ne marche pas (ou mal)

- Charge **forte et stable** 24/7 (le coût par requête perd face au réservé)
- Traitements **longs** ou gros calculs batch
- Applications **avec état** ou connexions longues : jeux en ligne, chat temps réel massif, streaming
- **Latence très basse garantie** (trading, temps réel dur)
- **Legacy** qui suppose un OS, un disque local ou un serveur précis
- Beaucoup de connexions vers une **base SQL** classique sans pooler
- Contraintes de **conformité** qui exigent la maîtrise de l'infrastructure

### Quand c'est le bon choix

- Trafic **en pics** ou imprévisible, faible le reste du temps
- Traitements **déclenchés par des événements**
- **Petite équipe** sans temps pour opérer une plateforme
- Besoin de **multi-région** sans équipe d'exploitation

La billetterie coche ces quatre cases. Le serverless devient une fausse bonne idée quand on le choisit **par défaut** pour une charge de la première liste.

## 6. Décision demandée aux tech leads

| # | Question | Proposition | ADR |
|---|---|---|---|
| 1 | Dual-zone en P2 accepté comme P2 ? | Oui, avec bascule strictement manuelle | 0002 |
| 2 | Snapshots de disques en P2 ? | Oui, justifiés par la « baie de stockage » | 0009 |
| 3 | Règle « build automatisé, run manuel » en P2 ? | Oui | 0010 |
| 4 | LB, NAT, DNS managés et IAP en P2 ? | Oui, documentés comme équivalents d'appliances | 0006 |
| 5 | Chaos nocturne et rollback auto obligatoires en P3 ? | Oui | 0004 |
| 6 | Cloud Run services plutôt que GKE ou functions ? | Oui | 0003 |
| 7 | Sweeper ou trigger Eventarc Firestore ? | Sweeper en v1, Eventarc à évaluer | 0011 |

Une fois ces 7 points tranchés : passer les ADR au statut **accepté** (validateurs + lien vers le CR, voir le registre), passer les contrats en `1.0.0`, puis lancer les schémas Noodle à partir de `platform2.md` et `platform3.md`.

## Sources

- Supports du cours « Génération Architecture » (Cours 1 slide 10, Cours 2 slides 25 et 34, Cours 4 slides 5 à 9 et 48)
- [Cloud Run — Automate cross-region failover with service health](https://docs.cloud.google.com/run/docs/configuring/configure-service-health)
- [Cloud Run — Serve traffic from multiple regions](https://docs.cloud.google.com/run/docs/multiple-regions)
- [Network World — 6 lessons from the Amazon Prime Video serverless vs. monolith flap](https://www.networkworld.com/article/3697737/6-lessons-from-the-amazon-prime-video-serverless-vs-monolith-flap.html)
