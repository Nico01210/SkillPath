"""
Nettoyage et normalisation de données importées depuis un fichier tiers.
"""

import json


def nettoyer_lignes(lignes, ignorees=[]):
    """Retire les lignes vides et celles marquées comme ignorées."""
    resultat = []
    for i in range(len(lignes)):
        ligne = lignes[i]
        if ligne.strip() == "":
            ignorees.append(i)
            continue
        if ligne.startswith("#"):
            ignorees.append(i)
            continue
        resultat.append(ligne.strip())
    return resultat


def parser_enregistrement(ligne, separateur=";"):
    champs = ligne.split(separateur)
    enregistrement = {}
    enregistrement["nom"] = champs[0]
    enregistrement["email"] = champs[1]
    enregistrement["age"] = champs[2]
    enregistrement["ville"] = champs[3]
    return enregistrement


def normaliser(enregistrement):
    """Met les champs texte en minuscules et convertit l'âge."""
    enregistrement["nom"] = enregistrement["nom"].lower()
    enregistrement["email"] = enregistrement["email"].lower()
    enregistrement["ville"] = enregistrement["ville"].lower()
    enregistrement["age"] = int(enregistrement["age"])
    return enregistrement


def filtrer_majeurs(enregistrements):
    majeurs = []
    for e in enregistrements:
        if e["age"] >= 18:
            majeurs.append(e)
    return majeurs


def grouper_par_ville(enregistrements):
    groupes = {}
    for e in enregistrements:
        ville = e["ville"]
        if ville not in groupes:
            groupes[ville] = []
        groupes[ville].append(e)
    return groupes


def exporter(enregistrements, chemin):
    contenu = json.dumps(enregistrements, ensure_ascii=False, indent=2)
    fichier = open(chemin, "w")
    fichier.write(contenu)
    fichier.close()
