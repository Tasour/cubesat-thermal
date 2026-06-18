# 🛰️ Garder un satellite en vie dans le vide de l'espace
## Explication du projet pour tout le monde

---

> *"Pourquoi un ingénieur qui travaillait sur des centrales nucléaires se met à programmer des simulations de satellites ?"*  
> C'est exactement la bonne question. Voici la réponse.

---

## Commençons par le début : c'est quoi un CubeSat ?

Imagine une brique de Lego géante : **10 cm × 10 cm × 30 cm**. C'est à peu près la taille de deux grandes canettes de soda empilées. Ce petit objet, qui pèse environ 4 kilos — le poids d'un sac de pommes de terre — est un vrai satellite opérationnel. On l'appelle un **CubeSat 3U** (le "3U" signifie 3 unités, soit 30 cm de longueur).

Ces mini-satellites ont révolutionné l'accès à l'espace depuis les années 2000. Avant, construire et lancer un satellite coûtait des centaines de millions d'euros et prenait dix ans. Un CubeSat peut être construit pour quelques centaines de milliers d'euros par une équipe universitaire ou une startup, et lancé en quelques années. Ils servent à photographier la Terre, mesurer des phénomènes climatiques, tester de nouvelles technologies, ou même transmettre des communications.

**Le satellite de ce projet orbite à 550 km d'altitude.** Pour se faire une idée : la Station Spatiale Internationale est à environ 400 km. Si tu regardais le sol depuis cette altitude, Paris tiendrait dans ton champ de vision comme un timbre-poste.

---

## Le problème central : la température dans l'espace est un enfer (et un congélateur simultanément)

Voici le vrai défi qu'on résout dans ce projet.

### Ce que la plupart des gens imaginent

La plupart des gens pensent que l'espace est "froid". Ce n'est pas tout à fait faux — mais c'est bien plus compliqué que ça.

### Ce qui se passe vraiment

Un satellite en orbite basse fait le tour de la Terre en **96 minutes**. Pendant ce tour, il passe environ **60 minutes en plein soleil**, puis **36 minutes dans l'ombre complète de la Terre** (ce qu'on appelle une éclipse). Et il recommence, indéfiniment, 15 fois par jour.

Imagine que tu passes alternativement :
- 60 minutes sous un chalumeau qui brûle à plein régime (le Soleil sans atmosphère pour filtrer)
- 36 minutes dans un congélateur industriel

Et tu recommences. Sans arrêt. Des milliers de fois pendant la durée de vie du satellite.

**En chiffres concrets**, les faces du CubeSat peuvent passer de **−50°C pendant l'éclipse** à **+70°C au soleil**. Une variation de 120°C en moins de deux heures. Sur les structures. Sur l'électronique. Sur les batteries. Sur les optiques.

---

## Pourquoi c'est un problème technique grave

### L'électronique a des limites

Ton téléphone portable fonctionne entre environ 0°C et +35°C. Si tu le mets au congélateur, la batterie lâche. Si tu le laisses au soleil sur le tableau de bord en été, il s'éteint en surchauffe. 

Les composants électroniques d'un satellite, c'est pareil — mais dans des conditions bien plus extrêmes. Le processeur de bord, les batteries, les capteurs optiques : chaque composant a une **plage de température dans laquelle il fonctionne correctement**. En dehors de cette plage, il se casse, fonctionne mal, ou donne des données erronées.

### L'expansion thermique

La physique nous dit que tous les matériaux se dilatent quand ils chauffent et se contractent quand ils refroidissent. Une vis en aluminium qui chauffe de 100°C s'allonge d'un tout petit millimètre... mais si cette vis tient un miroir ou un connecteur électrique, ce millimètre peut suffire à tout dérégler. Sur des centaines de cycles thermiques par mois, ces micro-déformations finissent par fatiguer les matériaux et briser les connexions.

### L'absence d'air : le problème fondamental

Sur Terre, si tu as trop chaud, tu transpires — l'eau s'évapore et emporte la chaleur. Si une pièce mécanique chauffe, l'air autour se réchauffe et se déplace (c'est la convection). **Dans l'espace, il n'y a pas d'air.** Zéro. Néant. Le vide absolu.

Cela signifie qu'il n'existe qu'**une seule façon de se débarrasser de la chaleur** : émettre du rayonnement (comme un radiateur qui émet des rayons infrarouges, invisibles mais porteurs d'énergie). Et il n'existe que **deux façons de recevoir de la chaleur** : absorber du rayonnement (du Soleil, de la Terre) ou que les composants électroniques en produisent eux-mêmes.

C'est une contrainte physique absolue. On ne peut pas "ventiler" un satellite.

---

## Comment résout-on ce problème ? La gestion thermique

L'ingénieur thermique spatial a un seul objectif : **maintenir tous les composants dans leur plage de température pendant toute la durée de vie du satellite**, en n'utilisant que des radiateurs passifs, des isolants, et des peintures spéciales.

Pas de climatisation. Pas de ventilateur. Juste de la physique bien appliquée.

### L'outil principal : les coatings (revêtements de surface)

La surface d'un satellite n'est pas choisie pour son apparence — elle est choisie pour ses propriétés physiques. Deux nombres décrivent chaque surface :

- **α (alpha) — absorptivité** : quelle fraction de la lumière solaire la surface absorbe (0 = miroir parfait, 1 = éponge noire parfaite)
- **ε (epsilon) — émissivité** : à quelle efficacité la surface rayonne sa propre chaleur vers l'espace (0 = garde toute sa chaleur, 1 = radiateur parfait)

La magie, c'est que ces deux propriétés peuvent être découplées. On peut choisir une surface qui **absorbe peu de soleil** (α faible = blanc ou doré) mais qui **rayonne bien** (ε élevé) → la surface reste fraîche. Ou l'inverse pour une face qu'on veut garder chaude.

| Surface | α (absorbe le soleil) | ε (rayonne la chaleur) | Résultat |
|---|---|---|---|
| Peinture blanche | 23% | 88% | Froide → bon radiateur |
| Aluminium nu et brillant | 37% | 5% | Chaud → mauvais radiateur ! |
| Panneau solaire | 92% | 85% | Chaud mais rayonne bien |
| MLI (couverture dorée) | 5% | 2% | Isolant → garde la chaleur |

*C'est pour ça que les satellites ont cette apparence dorée ou blanche caractéristique.*

---

## Ce que fait concrètement ce projet : la simulation numérique

Construire un vrai satellite pour tester ses températures coûte des millions d'euros et prend des années. La solution : **simuler le comportement thermique par ordinateur** avant de construire quoi que ce soit.

### L'idée centrale : découper en morceaux (le modèle nodal)

On ne peut pas calculer la température de chaque atome du satellite — c'est mathématiquement impossible. Alors on fait comme les ingénieurs ont toujours fait : on simplifie intelligemment.

**On découpe le satellite en zones** (qu'on appelle "nœuds" ou "nœuds thermiques"), et on suppose que chaque zone a une température uniforme. Pour notre CubeSat, on choisit **9 zones** :

```
🔲 Face droite (+X)     🔲 Face gauche (-X)
🔲 Face avant (+Y)      🔲 Face arrière (-Y)  
🔲 Face haut (+Z)       🔲 Face bas (-Z)       ← Les 6 faces extérieures
🔩 Structure interne                             ← Le châssis en aluminium
💻 Électronique (OBC + EPS)                     ← L'ordinateur de bord + gestion énergie
📷 Payload (caméra)                             ← La charge utile, le composant le plus précieux
```

Pour chaque zone, on écrit une équation très simple dans son principe :

> **Chaleur qui rentre** − **Chaleur qui sort** = **Variation de température**

C'est exactement le bilan d'un compte en banque : entrées − sorties = évolution du solde.

### Les "rentrées" de chaleur

Pour les faces extérieures, trois sources :

**1. Le Soleil direct 🌞**  
Quand une face "regarde" le Soleil, elle reçoit son rayonnement. La puissance reçue dépend de l'angle : une face perpendiculaire au Soleil reçoit le maximum, une face parallèle ne reçoit rien — exactement comme tu reçois plus de chaleur du Soleil à midi (rayons directs) qu'au coucher du soleil (rayons rasants).

**2. L'albédo de la Terre 🌍**  
La Terre réfléchit environ 30% de la lumière solaire qu'elle reçoit (c'est ce qu'on appelle l'albédo, du latin *albus*, blanc). Cette lumière réfléchie arrive sur les faces du satellite qui "regardent" vers le bas. C'est moins intense que le Soleil direct, mais ça compte.

**3. Le rayonnement infrarouge de la Terre 🌡️**  
La Terre est à environ −18°C en moyenne (température d'équilibre sans effet de serre). Comme tout corps ayant une température, elle émet un rayonnement invisible (infrarouge). Ce flux est **permanent** — il arrive aussi bien le jour que la nuit, éclipse ou pas.

**4. La chaleur des composants électroniques 🔋**  
L'électronique consomme de l'énergie électrique. Cette énergie finit toujours en chaleur — c'est une loi fondamentale de la physique. L'ordinateur de bord dissipe ~0.5 W, la caméra ~2 W quand elle est active, etc.

### La "sortie" de chaleur

**Il n'en existe qu'une seule : le rayonnement vers l'espace.**  
Toute surface chaude émet un rayonnement proportionnel à sa température (à la puissance 4 — donc ça augmente très vite avec la température). L'espace est à 3 Kelvin (−270°C), donc il absorbe pratiquement tout ce qu'on lui envoie.

### Le moteur de la simulation : résoudre 9 équations en même temps

Ces 9 zones sont couplées entre elles : quand la structure se réchauffe, elle conduit de la chaleur vers l'électronique. Quand l'électronique chauffe, elle transmet à la caméra. Ces transferts de chaleur par contact (on dit "conduction") créent un réseau d'interactions.

À chaque instant, on a donc **9 équations simultanées** qui décrivent l'évolution des 9 températures. Elles sont couplées, elles changent dans le temps, et elles dépendent elles-mêmes des températures (parce que le rayonnement dépend de T⁴).

C'est ce qu'on appelle un **système d'équations différentielles ordinaires** — impossible à résoudre à la main, mais très bien géré par un ordinateur avec l'algorithme adéquat. On utilise ici une méthode classique (Runge-Kutta 4/5, celle qu'utilisent les ingénieurs et physiciens depuis des décennies) implémentée dans la bibliothèque scientifique Python SciPy.

**En pratique :** on dit à l'ordinateur "voilà l'état du satellite à l'instant 0 (tout à 280 K)", et il calcule pas à pas, 5000 fois, comment évolue chaque température au fil de 5 orbites complètes (≈8 heures réelles simulées en quelques secondes).

---

## L'angle β : le paramètre qui change tout

C'est le concept le plus important du projet, et probablement le moins intuitif.

Imagine l'orbite du satellite comme un cerceau. Le Soleil est loin, mais il éclaire le cerceau selon un certain angle. Cet angle entre le plan du cerceau et la direction du Soleil, c'est **l'angle β** (bêta).

```
β = 0°  → Le Soleil est "dans le plan" de l'orbite
           Le satellite passe dans l'ombre de la Terre à chaque tour
           → Éclipses longues, grand écart thermique → cas LE PLUS FROID

β = 90° → Le Soleil est "au-dessus" du plan orbital
           Le satellite est TOUJOURS au soleil, jamais d'ombre
           → Aucune éclipse, chaleur constante → cas LE PLUS CHAUD
```

Selon la saison et l'orientation de l'orbite, β varie de −90° à +90°. Un bon ingénieur thermique doit s'assurer que le satellite survit aux **deux cas extrêmes** — et à tout ce qui se passe entre les deux.

C'est pour ça que l'analyse de sensibilité à β est l'un des livrables principaux du projet.

---

## Ce que produit le projet concrètement

### Un dashboard interactif

L'interface permet à n'importe quel ingénieur de changer les paramètres (angle β, puissance interne, type de peinture...) et de voir instantanément comment réagissent les températures de chaque composant. C'est comme un simulateur de vol, mais pour la thermique.

### Des graphiques de température

On voit en temps réel comment la température de chaque face monte et descend à chaque orbite, formant des vagues régulières coupées par les éclipses. La caméra, par exemple, doit toujours rester entre −20°C et +60°C — et on voit graphiquement si cette contrainte est respectée.

### Les "marges thermiques"

C'est le livrable le plus important pour un ingénieur. Pour chaque composant, on calcule :
- À quelle température minimale il descend réellement → combien de degrés le séparent de sa limite basse
- À quelle température maximale il monte réellement → combien de degrés le séparent de sa limite haute

Si la marge est négative, le composant mourra en orbite. Si la marge est faible (quelques degrés), on est dans la zone de risque. Si elle est large (>15°C), le design est robuste.

### L'analyse de sensibilité

On répond à des questions de type : *"Si je remplace la peinture blanche par de l'aluminium nu sur la face +Y, est-ce que la caméra survivra ?"* ou *"Si la dissipation électronique double parce qu'on ajoute un composant, quelles sont les conséquences ?"*

Ces analyses permettent de **prendre des décisions de design éclairées** avant de construire le moindre bout de métal.

---

## Le lien avec mon travail précédent sur l'EPR2

C'est là où ce projet devient intéressant d'un point de vue de carrière.

Pendant mon travail sur le projet EPR2 (le nouveau réacteur nucléaire français), je réalisais des **bilans thermiques** : calculer comment la chaleur se distribue dans un bâtiment complexe — ventilation, chauffage, isolation des tuyaux, zones à température contrôlée. J'automatisais ces calculs avec Python à partir de données extraites d'une maquette numérique 3D.

La méthode est **exactement la même** :

| Ce que je faisais sur l'EPR2 | Ce que je fais sur le CubeSat |
|---|---|
| Découper le bâtiment en zones thermiques | Découper le satellite en 9 nœuds |
| Calculer les flux de chaleur (ventilation, convection) | Calculer les flux (solaire, albédo, IR) |
| Résoudre les bilans d'énergie par zone | Résoudre les 9 équations couplées |
| Vérifier que T reste dans les limites de sécurité | Vérifier les marges thermiques des composants |
| Faire des analyses de sensibilité | Analyser β, coatings, puissance interne |
| Automatiser avec Python | Automatiser avec Python |

La différence principale : en bâtiment, c'est l'air (convection) qui transporte la chaleur. Dans l'espace, c'est le rayonnement. Le mécanisme change, mais la **démarche d'ingénieur** est identique.

Ce projet démontre que la compétence est **transférable** — et c'est précisément ce qu'un recruteur dans le secteur spatial cherche chez un candidat venant d'un autre domaine industriel.

---

## Pour résumer en une phrase

> Ce projet simule, en Python, comment la température d'un mini-satellite évolue en orbite, en tenant compte du Soleil, de l'ombre de la Terre, et de la chaleur des composants électroniques — pour vérifier qu'aucun composant ne surchauffe ni ne gèle, avant même d'avoir fabriqué le moindre écrou.

---

*Si tu veux aller plus loin dans les détails techniques, le cahier des charges complet est disponible dans le même dépôt.*
