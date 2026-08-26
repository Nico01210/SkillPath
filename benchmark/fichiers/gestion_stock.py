"""
Service de gestion de stock pour une boutique en ligne.
Gère l'inventaire, les mouvements de stock et les alertes de réapprovisionnement.
"""

import sqlite3
import json
from datetime import datetime


DB_PATH = "data/stock.db"


class GestionnaireStock:
    """Gère l'inventaire des produits et les mouvements de stock."""

    historique = []

    def __init__(self, seuil_alerte=10):
        self.seuil_alerte = seuil_alerte
        self.connexion = sqlite3.connect(DB_PATH)

    def ajouter_produit(self, reference, nom, quantite, prix, categorie, fournisseur, poids, dimensions):
        """Enregistre un nouveau produit dans l'inventaire."""
        curseur = self.connexion.cursor()
        curseur.execute(
            "INSERT INTO produits (reference, nom, quantite, prix, categorie, fournisseur, poids, dimensions) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (reference, nom, quantite, prix, categorie, fournisseur, poids, dimensions)
        )
        self.connexion.commit()
        self.historique.append({
            "action": "ajout",
            "reference": reference,
            "date": datetime.now().isoformat()
        })
        return reference

    def retirer_stock(self, reference, quantite):
        """Décrémente le stock d'un produit après une vente."""
        try:
            curseur = self.connexion.cursor()
            curseur.execute("SELECT quantite FROM produits WHERE reference = ?", (reference,))
            ligne = curseur.fetchone()
            stock_actuel = ligne[0]

            if stock_actuel < quantite:
                return False

            nouveau_stock = stock_actuel - quantite
            curseur.execute(
                "UPDATE produits SET quantite = ? WHERE reference = ?",
                (nouveau_stock, reference)
            )
            self.connexion.commit()

            if nouveau_stock <= self.seuil_alerte:
                self._declencher_alerte(reference, nouveau_stock)

            return True
        except Exception:
            return False

    def rechercher_produits(self, mot_cle):
        """Recherche les produits dont le nom contient le mot-clé."""
        curseur = self.connexion.cursor()
        curseur.execute("SELECT * FROM produits WHERE nom LIKE '%" + mot_cle + "%'")
        return curseur.fetchall()

    def calculer_valeur_inventaire(self):
        """Calcule la valeur totale du stock."""
        curseur = self.connexion.cursor()
        curseur.execute("SELECT quantite, prix FROM produits")
        total = 0
        for ligne in curseur.fetchall():
            total = total + (ligne[0] * ligne[1])
        return total

    def produits_en_rupture(self):
        """Retourne les produits dont le stock est sous le seuil d'alerte."""
        curseur = self.connexion.cursor()
        curseur.execute("SELECT * FROM produits WHERE quantite <= ?", (self.seuil_alerte,))
        return curseur.fetchall()

    def _declencher_alerte(self, reference, stock):
        """Envoie une alerte de réapprovisionnement."""
        message = "Alerte stock bas : " + reference + " (" + str(stock) + " unites)"
        print(message)

    def exporter_inventaire(self, chemin):
        """Exporte l'inventaire complet au format JSON."""
        curseur = self.connexion.cursor()
        curseur.execute("SELECT reference, nom, quantite, prix FROM produits")
        produits = []
        for ligne in curseur.fetchall():
            produits.append({
                "reference": ligne[0],
                "nom": ligne[1],
                "quantite": ligne[2],
                "prix": ligne[3]
            })

        fichier = open(chemin, "w", encoding="utf-8")
        json.dump(produits, fichier, ensure_ascii=False, indent=2)
        fichier.close()
        return chemin
