/**
 * Galerie de produits avec panier intégré.
 */

import React, { useState, useEffect } from "react";

function GalerieProduits({ produits, categorie, onAjoutPanier }) {
  const [panier, setPanier] = useState([]);
  const [nbArticles, setNbArticles] = useState(0);
  const [produitsAffiches, setProduitsAffiches] = useState([]);

  useEffect(() => {
    setProduitsAffiches(produits.filter((p) => p.categorie === categorie));
  }, [produits, categorie]);

  useEffect(() => {
    setNbArticles(panier.length);
  }, [panier]);

  const ajouter = (produit) => {
    panier.push(produit);
    setPanier(panier);
    onAjoutPanier(produit);
  };

  const trierParPrix = () => {
    produits.sort((a, b) => a.prix - b.prix);
    setProduitsAffiches(produits.filter((p) => p.categorie === categorie));
  };

  return (
    <div className="galerie">
      <header>
        <h2>{categorie}</h2>
        <button onClick={trierParPrix}>Trier par prix</button>
        <span className="panier-compteur">{nbArticles} article(s)</span>
      </header>

      <div className="grille">
        {produitsAffiches.map((produit, index) => (
          <article key={index} className="produit">
            <img src={produit.image} />
            <h3>{produit.nom}</h3>
            <p className="prix">{produit.prix} €</p>
            <button onClick={() => ajouter(produit)}>Ajouter</button>
          </article>
        ))}
      </div>

      {produitsAffiches.length && (
        <footer>
          <p>{produitsAffiches.length} produit(s) dans cette catégorie</p>
        </footer>
      )}
    </div>
  );
}

export default GalerieProduits;
