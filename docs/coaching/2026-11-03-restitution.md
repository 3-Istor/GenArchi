# Gen-Archi — Compte rendu du coaching avec les enseignants

**Date du coaching :** 3 novembre 2026 (date de la transcription transmise)  
**Projet :** Gen-Archi — comparaison de plateformes de génération P2 et P3  
**Échéance annoncée :** 12 janvier (2027 probable, année à confirmer)  
**Source :** transcription orale fournie par l'équipe, reformulée pour être lisible  

> **Note de fidélité :** la transcription comporte des passages imprécis. Les éléments considérés comme validés sont distingués des choix proposés et des points restant à confirmer. Les terminologies techniques ambiguës, notamment autour de l'élection du leader et du quorum, doivent être revérifiées auprès de l'équipe.

## 1. Objectif et périmètre du projet

Le projet vise à **comparer deux générations de plateformes (P2 et P3)** à partir d'un **même cas d'usage applicatif**, en étudiant leur architecture, leur exploitation et leur réaction aux défaillances.

- **Application commune retenue pour l'étude :** billetterie d'événements (par exemple, réservation ou création de billets).
- **Principe validé pendant l'échange :** conserver la même application et les mêmes fonctionnalités métier sur les deux plateformes pour rendre la comparaison pertinente.
- **Angle principal :** ne pas seulement présenter les technologies ; **démontrer les différences de comportement en cas de panne**, les modalités de reprise et les compromis d'architecture.

## 2. Plateforme P2 — approche davantage administrée manuellement

### Proposition de l'équipe

- Hébergement et exploitation plus proches d'une logique d'infrastructure administrée par l'équipe.
- **Basculement et interventions principalement manuels** en cas d'incident, par opposition à la P3 davantage automatisée.
- Accès d'administration via un **bastion**.
- Présence envisagée de mécanismes de redondance, de choix d'un leader et de quorum au sein de certains composants.
- Une question a été soulevée sur la **fonction exacte du mécanisme d'élection/quorum** et ses éventuels liens avec la messagerie **RabbitMQ** ; la transcription ne permet pas de reconstituer avec certitude la réponse technique.

### Ce qu'il faudra démontrer

1. Identifier la panne d'un composant représentatif.
2. Expliquer les conséquences pour l'utilisateur et les transactions de billetterie.
3. Montrer **qui intervient**, selon quelle procédure, et **comment le service est rétabli**.
4. Décrire les limites de cette approche : délais de reprise, risques d'erreur humaine, dépendance à l'exploitation et niveau de redondance réel.

**Attention :** « P2 = bascule manuelle » est le **parti pris proposé pour la démonstration**, pas une propriété universelle de toute plateforme P2.

## 3. Plateforme P3 — approche cloud managée et automatisée

### Proposition de l'équipe

- **Fournisseur envisagé : Google Cloud Platform (GCP)**, notamment en raison des crédits disponibles ; le recours à GCP plutôt qu'à AWS n'a pas été présenté comme bloquant.
- Architecture envisagée **active-active sur deux régions** : les deux régions participent au service en fonctionnement normal.
- **Conteneurs sans état (stateless)** pour la couche applicative.
- Recours accru à des **services managés**, avec automatisation et redondance prises en charge en partie par le fournisseur.
- Séparation des responsabilités applicatives par des **événements** : par exemple, la création d'un billet déclenche la publication d'un événement qui peut être consommé par d'autres composants.
- La résilience des **données** mérite une attention particulière : une architecture applicative multirégion ne prouve pas à elle seule que la base de données reste disponible lors d'une panne.

### Points de vigilance

- Ne pas présumer qu'un service est **multirégion par défaut** : préciser, pour chaque service GCP retenu, sa portée géographique, son mode de réplication et son comportement en cas de panne.
- Distinguer **redondance**, **haute disponibilité**, **bascule automatique**, **résilience** et **absence de perte de données** : ces garanties ne sont pas synonymes.
- Clarifier le mécanisme de traitement des événements (ordre, doublons, retry, idempotence, perte éventuelle).
- Ne pas limiter les tests à la chute complète d'une région : les pannes de **base de données** ou de composant individuel peuvent être plus instructives.

## 4. Questions posées aux enseignants et réponses retenues

| Sujet | Enseignements de l'échange |
|---|---|
| Même application en P2 et P3 ? | **Oui** : une application métier commune permet une comparaison cohérente des deux approches. |
| Architecture proposée globalement cohérente ? | Aucun rejet de principe n'apparaît dans la transcription. Les détails techniques doivent encore être précisés. |
| Quels scénarios de panne faut-il montrer ? | **Pas de scénario unique imposé**. Choisir des incidents pertinents pour le cas d'usage et démontrer leur traitement. Une panne de base de données est une piste explicitement discutée. |
| Faut-il forcément simuler la perte d'une région entière ? | **Non**. La discussion privilégie également des pannes ciblées et la vérification des dépendances de données. |
| RTO / RPO attendus ? | Des indicateurs de reprise et de perte de données sont pertinents pour étayer la comparaison, mais **aucune cible chiffrée universelle n'a été imposée**. Les objectifs sont à justifier par le métier. |
| Supervision obligatoire ? | **Non**, pas d'obligation explicite de mettre en place une supervision complète. Elle reste utile pour constater et expliquer les pannes. |
| Durée imposée des pannes ou de leur démonstration ? | **Pas de durée minimale ou maximale spécifique évoquée** ; l'ensemble doit tenir dans le temps imparti à la soutenance. |
| Critères d'évaluation / différence avec un précédent exercice ? | Aller au-delà d'un simple déploiement : montrer les compromis entre générations de plateformes et **prouver** ce qui se passe lorsqu'un élément tombe en panne. |

## 5. RTO et RPO : relier les objectifs au métier

Les enseignants invitent l'équipe à **définir elle-même des exigences réalistes selon le contexte de la billetterie**, plutôt qu'à appliquer des chiffres arbitraires.

- **RTO (Recovery Time Objective)** : durée maximale acceptable d'interruption du service après un incident.
- **RPO (Recovery Point Objective)** : quantité maximale de données susceptibles d'être perdues, exprimée en durée.
- **Exemple discuté :** la perte de réservations **la veille d'un concert** peut avoir des conséquences bien plus graves qu'une indisponibilité ou une perte de données survenant plusieurs mois avant l'événement.

### Proposition de méthode pour la soutenance

1. Définir deux ou trois événements métier critiques : achat de billet, paiement confirmé, génération/consultation du billet.
2. Définir des objectifs de disponibilité et de perte de données **distincts** selon la criticité, sans les présenter comme imposés par les professeurs.
3. Mesurer ou observer le comportement réel des deux plateformes pour le même incident.
4. Présenter l'écart entre **objectif**, **comportement observé** et **compromis accepté**.

## 6. Différence conceptuelle entre P2 et P3

La discussion a remis le projet dans une trajectoire historique : transition d'une logique de **data center / infrastructure mise à disposition** vers une consommation accrue de **services cloud managés** (repère historique autour des années 2010, à prendre comme illustration et non comme définition normative).

| Dimension | P2 — scénario proposé | P3 — scénario proposé |
|---|---|---|
| Responsabilités | Davantage d'exploitation à la charge de l'équipe | Plus de responsabilités déléguées aux services managés |
| Reprise sur incident | Procédures et bascules plus manuelles | Détection, redondance et reprise plus automatisées selon les services |
| Déploiement applicatif | Infrastructure davantage pilotée directement | Conteneurs stateless et services cloud |
| Distribution géographique | À expliciter dans le design | Deux régions actives proposées |
| Messagerie et données | Administration et mécanismes de quorum à détailler | Services managés et garanties de données à vérifier |
| Démonstration recherchée | Montrer la procédure de reprise | Montrer la continuité ou le rétablissement automatique **effectivement obtenu** |

**Message central :** la différence doit se voir dans les **responsabilités opérationnelles et les résultats observés**, pas uniquement dans les noms de produits.

## 7. Discussion exploratoire : une éventuelle plateforme P4

Une question a été posée sur l'existence d'une **quatrième génération (P4)**.

- Aucune définition stabilisée ou unanimement reconnue n'a été confirmée pendant l'échange.
- Piste évoquée : plateformes **fortement ou intégralement automatisées**, éventuellement pilotées par IA, où l'utilisateur exprime une intention plutôt que de gérer explicitement déploiement et infrastructure.
- Un changement de l'**interface de consommation des applications** a également été évoqué : interaction conversationnelle et délégation à des agents.
- **MCP**, à lui seul, ne suffit pas à caractériser une rupture générationnelle : il facilite des interactions entre systèmes/outils sans constituer automatiquement une nouvelle plateforme.

**Statut :** sujet de réflexion hors cœur de la démonstration P2/P3 ; ne pas le présenter comme une nomenclature technique établie.

## 8. Plan d'action recommandé à l'équipe

### Priorité 1 — figer le scénario métier

- [ ] Définir le parcours de billetterie commun aux deux plateformes (création d'événement, achat, confirmation, consultation de billet).
- [ ] Identifier les composants et les données critiques.
- [ ] Conserver des tests et une charge comparables entre P2 et P3.

### Priorité 2 — finaliser et justifier les architectures

- [ ] Produire un schéma P2 précisant bastion, composants, dépendances, mécanismes de bascule et rôles des nœuds/quorums.
- [ ] Lever l'ambiguïté sur l'élection du leader et le quorum de RabbitMQ.
- [ ] Produire un schéma P3 précisant les services GCP effectivement choisis, leurs régions, leurs garanties et les éventuels points de défaillance uniques.
- [ ] Vérifier la stratégie de stockage des données et l'architecture événementielle.

### Priorité 3 — préparer une matrice de tests de panne

Proposition de scénarios **à sélectionner selon la faisabilité**, non imposée par les enseignants :

| Scénario | Ce qu'il faut observer | Comparaison attendue |
|---|---|---|
| Arrêt d'une instance applicative | Disponibilité de l'achat/consultation de billet | Intervention manuelle vs reprise/redistribution automatique |
| Indisponibilité de la base de données | Échec, attente ou reprise des transactions | Conséquences sur l'intégrité des billets et le RPO |
| Défaillance de la messagerie | Retard ou perte éventuelle des événements | Comportement de reprise, retraitement et idempotence |
| Perte d'un nœud participant à un quorum | Maintien ou perte de disponibilité du composant | Rôle du quorum et limites de la redondance |
| Indisponibilité régionale partielle | Routage et continuité applicative | Garanties *réelles* des services GCP utilisés |

Pour **chaque scénario**, conserver la même trame : **état initial → injection de panne → effet utilisateur → détection → reprise → données perdues ou préservées → conclusion P2/P3**.

### Priorité 4 — préparer les preuves et la soutenance

- [ ] Définir des hypothèses métier explicites pour le RTO et le RPO.
- [ ] Capturer des traces ou observations exploitables : chronologie, requêtes réussies/échouées, état des billets, opérations manuelles.
- [ ] Prévoir une démo courte, reproductible et compréhensible dans le créneau de soutenance.
- [ ] Présenter un tableau final des compromis : disponibilité, reprise, intégrité des données, simplicité opérationnelle, limites et coûts **si l'équipe souhaite les intégrer**.

## 9. Points à confirmer

1. **Date exacte de la soutenance :** « 12 janvier » est mentionné ; année à confirmer dans les consignes officielles.
2. **Élection du leader / quorum :** rôle précis des nœuds et éventuel couplage avec RabbitMQ, passage oral insuffisamment net.
3. **Liste définitive des services GCP :** non identifiable dans la transcription ; ne pas présumer de leurs capacités multirégion.
4. **Grille de notation officielle :** les enseignants ont donné une orientation, mais aucun barème détaillé n'est établi par la transcription.
5. **Cibles RTO/RPO et éventuelles contraintes budgétaires :** à fixer ou vérifier selon les consignes, sans inventer de seuils.

## 10. Synthèse exécutive

Le coaching confirme une direction claire : **utiliser une seule application de billetterie pour comparer P2 et P3 au travers de scénarios de panne concrets**. La P2 est conçue comme une plateforme demandant davantage d'administration et de basculement manuel ; la P3, envisagée sur GCP avec des services managés et deux régions actives, doit illustrer une reprise plus automatisée. Les professeurs **n'imposent ni panne unique, ni seuil chiffré de RTO/RPO, ni supervision complète**. Ils attendent surtout une comparaison argumentée, réaliste du point de vue métier et **étayée par des démonstrations observables**. La prochaine étape est de figer les schémas, sélectionner quelques pannes pertinentes et construire les preuves de reprise et d'intégrité des données.
