"""
Génération de rapports de ventes mensuels.
Agrège les commandes, calcule les totaux par client et produit un export.
"""

import sqlite3


DB_PATH = "data/ventes.db"


def get_connexion():
    return sqlite3.connect(DB_PATH)


def rapport_mensuel(mois, annee):
    """Construit le rapport de ventes du mois."""
    conn = get_connexion()
    curseur = conn.cursor()

    curseur.execute(
        "SELECT id, client_id, montant FROM commandes WHERE mois = ? AND annee = ?",
        (mois, annee)
    )
    commandes = curseur.fetchall()

    lignes = []
    for commande in commandes:
        curseur.execute("SELECT nom, email FROM clients WHERE id = ?", (commande[1],))
        client = curseur.fetchone()

        curseur.execute("SELECT COUNT(*) FROM articles WHERE commande_id = ?", (commande[0],))
        nb_articles = curseur.fetchone()[0]

        lignes.append({
            "commande": commande[0],
            "client": client[0],
            "email": client[1],
            "montant": commande[2],
            "articles": nb_articles,
        })

    conn.close()
    return lignes


def clients_communs(clients_a, clients_b):
    """Retourne les clients présents dans les deux listes."""
    communs = []
    for client in clients_a:
        if client in clients_b:
            communs.append(client)
    return communs


def construire_csv(lignes):
    """Assemble le rapport au format CSV."""
    contenu = "commande;client;email;montant;articles\n"
    for ligne in lignes:
        contenu = contenu + str(ligne["commande"]) + ";"
        contenu = contenu + ligne["client"] + ";"
        contenu = contenu + ligne["email"] + ";"
        contenu = contenu + str(ligne["montant"]) + ";"
        contenu = contenu + str(ligne["articles"]) + "\n"
    return contenu


def total_par_client(lignes):
    """Calcule le chiffre d'affaires par client."""
    totaux = {}
    for ligne in lignes:
        if ligne["client"] not in totaux:
            totaux[ligne["client"]] = 0
        totaux[ligne["client"]] = totaux[ligne["client"]] + ligne["montant"]
    return totaux
