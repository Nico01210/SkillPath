# Banc d'essai SkillPath

Mesure la qualité de l'analyse produite par SkillPath sur un corpus de
fichiers dont on connaît à l'avance les erreurs.

L'objectif n'est pas de vérifier que l'application fonctionne — c'est le
rôle des tests unitaires — mais de **mesurer si la configuration actuelle
dit vrai** : le prompt, le modèle et les réglages du RAG.

---

## Isolation

Cet outil est volontairement séparé de l'application. Il n'importe aucun
module de SkillPath et ne communique avec elle que par HTTP, comme le
ferait n'importe quel client externe. Le supprimer entièrement n'a aucun
effet sur le fonctionnement de SkillPath.

---

## Utilisation

SkillPath doit tourner :

```bash
uvicorn main:app
```

Puis, depuis ce dossier :

```bash
python benchmark.py
```

Options :

```bash
python benchmark.py --url http://localhost:8000    # autre instance
python benchmark.py --fichier panier.js            # un seul fichier
python benchmark.py --json resultats.json          # export machine
```

Le script sort avec le code `0` si la configuration est conforme, `1`
sinon — de quoi le brancher dans une CI le jour où l'application sera
hébergée.

---

## Les deux mesures

**Rappel** — part des erreurs attendues que l'analyse a effectivement
trouvées. Un rappel faible signifie que le modèle passe à côté de
problèmes réels.

**Faux positifs** — erreurs remontées sur les fichiers volontairement
propres. Ces fichiers ne contiennent aucun défaut : toute erreur y est
nécessairement inventée.

Une erreur détectée en plus du corpus sur un fichier bugué **n'est pas**
comptée comme un faux positif. Elle peut être parfaitement légitime,
simplement non anticipée lors de l'écriture des attendus. Elle est
signalée entre parenthèses, sans pénalité. Seuls les fichiers propres
permettent de trancher sans ambiguïté.

### Seuils

```python
SEUIL_RAPPEL      = 0.90   # au moins 90 % des erreurs attendues
MAX_FAUX_POSITIFS = 0      # aucune erreur inventée toléré
```

Les deux mesures se contredisent : durcir le prompt jusqu'à tout trouver
produit des faux positifs, l'assouplir jusqu'à n'en produire aucun fait
chuter le rappel. Le réglage se juge sur les deux à la fois.

---

## Écrire les attendus

Dans `attendus.yml`, chaque erreur attendue est décrite par des
**mots-clés**, pas par son titre exact — le modèle reformule les titres
à chaque scan.

```yaml
- nom: api_reservation.py
  attendus:
    - libelle: Injection SQL par concaténation
      mots_cles: [injection, sql]
    - libelle: CORS permissif
      mots_cles: [cors]
```

Une erreur détectée satisfait un attendu si **tous** ses mots-clés
apparaissent dans le titre ou la description, sans tenir compte de la
casse ni des accents. Une même erreur détectée ne peut satisfaire qu'un
seul attendu.

Choisir des mots-clés discriminants et peu nombreux : deux termes
suffisent généralement. Trop de mots-clés rend l'attendu impossible à
satisfaire, trop peu le rend trop facile.

Un fichier propre se déclare avec une liste vide :

```yaml
- nom: formatage.js
  attendus: []
```

---

## Interpréter un résultat

```
  ✓ gestion_stock.py         5/5 attendues  (+1 hors corpus)
  ~ api_reservation.py       4/5 attendues
      manque : Paramètres non validés
  ✓ formatage.js             aucun faux positif

  Rappel           95%   19/20 erreurs attendues détectées
  Faux positifs      0   sur 2 fichier(s) volontairement propre(s)
```

Une ligne `manque` indique une erreur du corpus que l'analyse n'a pas
trouvée. Deux causes possibles, à distinguer avant de toucher au prompt :

- l'analyse est réellement passée à côté du problème
- les mots-clés de l'attendu sont trop stricts et ne matchent pas la
  formulation du modèle

Vérifier la seconde hypothèse en scannant le fichier depuis l'interface
et en lisant la formulation réelle.

---

## Quand le lancer

À chaque modification du prompt, du modèle, ou des réglages du RAG.
C'est ce qui permet de savoir si un changement améliore ou dégrade la
qualité, plutôt que de s'en remettre à une impression.
