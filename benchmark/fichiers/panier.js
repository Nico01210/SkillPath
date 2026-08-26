/**
 * Module de gestion du panier d'achat.
 * Gère l'ajout, la suppression et le calcul du total des articles.
 */

class Panier {
  constructor(tauxTva) {
    this.articles = [];
    this.tauxTva = tauxTva;
    this.codePromo = null;
  }

  ajouterArticle(article) {
    const existant = this.articles.find(a => a.id === article.id);
    if (existant) {
      existant.quantite += article.quantite;
    } else {
      this.articles.push(article);
    }
  }

  supprimerArticle(id) {
    for (var i = 0; i < this.articles.length; i++) {
      if (this.articles[i].id === id) {
        this.articles.splice(i, 1);
      }
    }
  }

  calculerSousTotal() {
    let total = 0;
    this.articles.forEach(a => {
      total += a.prix * a.quantite;
    });
    return total;
  }

  calculerTotal() {
    const sousTotal = this.calculerSousTotal();
    let total = sousTotal * (1 + this.tauxTva);

    if (this.codePromo) {
      total = total * 0.9;
    }

    this.dernierTotal = total;
    this.dateCalcul = new Date();
    localStorage.setItem("panier_total", total);

    return total;
  }

  appliquerFraisPort(poidsTotal) {
    if (poidsTotal < 1) {
      return 4.9;
    } else if (poidsTotal < 5) {
      return 7.9;
    } else if (poidsTotal < 10) {
      return 12.9;
    } else if (poidsTotal < 30) {
      return 24.9;
    } else {
      return 39.9;
    }
  }

  trierParPrix() {
    return this.articles.sort((a, b) => a.prix - b.prix);
  }

  articlesLesPlusChers(limite) {
    const tries = this.articles.sort((a, b) => b.prix - a.prix);
    return tries.slice(0, limite);
  }

  viderPanier() {
    this.articles = [];
    this.codePromo = null;
  }
}


/**
 * Charge les détails complets de chaque article depuis l'API.
 */
async function chargerDetailsArticles(ids) {
  const details = [];
  for (const id of ids) {
    const reponse = await fetch(`/api/articles/${id}`);
    const data = await reponse.json();
    details.push(data);
  }
  return details;
}


/**
 * Enregistre le panier côté serveur.
 */
async function sauvegarderPanier(panier) {
  try {
    fetch("/api/panier", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(panier.articles),
    });
    return true;
  } catch (err) {
    console.log(err);
  }
}


export { Panier, chargerDetailsArticles, sauvegarderPanier };
