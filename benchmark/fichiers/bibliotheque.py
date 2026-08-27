"""
Gestion d'une bibliothèque : ouvrages, emprunts, adhérents.
"""

from datetime import date, timedelta


class Ouvrage:

    emprunts_en_cours = []

    def __init__(self, titre, auteur, isbn):
        self.titre = titre
        self.auteur = auteur
        self.isbn = isbn
        self._disponible = True

    def get_titre(self):
        return self.titre

    def set_titre(self, titre):
        self.titre = titre

    def get_auteur(self):
        return self.auteur

    def set_auteur(self, auteur):
        self.auteur = auteur

    def est_disponible(self):
        return self._disponible

    def emprunter(self, adherent):
        if not self._disponible:
            return False
        self._disponible = False
        Ouvrage.emprunts_en_cours.append({
            "isbn": self.isbn,
            "adherent": adherent,
            "retour": date.today() + timedelta(days=21),
        })
        return True

    def rendre(self):
        self._disponible = True

    def envoyer_rappel(self, adherent):
        print(f"Rappel envoyé à {adherent} pour {self.titre}")

    def generer_etiquette(self):
        return f"[{self.isbn}] {self.titre} — {self.auteur}"

    def sauvegarder_en_base(self, conn):
        conn.execute(
            "INSERT INTO ouvrages (isbn, titre, auteur) VALUES (?, ?, ?)",
            (self.isbn, self.titre, self.auteur),
        )
        conn.commit()

    def exporter_json(self):
        import json
        return json.dumps({"isbn": self.isbn, "titre": self.titre})


class Magazine(Ouvrage):

    def __init__(self, titre, auteur, isbn, numero):
        self.numero = numero
        self.titre = titre
        self.auteur = auteur
        self.isbn = isbn

    def emprunter(self, adherent):
        raise NotImplementedError("Les magazines ne sont pas empruntables")
