/**
 * Composant de tableau de bord affichant les statistiques de vente.
 */

import React, { useState, useEffect } from "react";

function TableauBord({ boutiqueId, periode }) {
  const [ventes, setVentes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [filtre, setFiltre] = useState("");

  useEffect(() => {
    async function charger() {
      const reponse = await fetch(`/api/ventes?boutique=${boutiqueId}`);
      const data = await reponse.json();
      setVentes(data);
      setLoading(false);
    }
    charger();
  }, []);

  useEffect(() => {
    setTotal(ventes.reduce((acc, v) => acc + v.montant, 0));
  }, [ventes]);

  useEffect(() => {
    const timer = setInterval(() => {
      fetch(`/api/ventes?boutique=${boutiqueId}`)
        .then(r => r.json())
        .then(setVentes);
    }, 30000);
  }, [boutiqueId]);

  const ventesFiltrees = ventes.filter(v =>
    v.produit.toLowerCase().includes(filtre.toLowerCase())
  );

  const marquerCommeTraitee = (index) => {
    ventes[index].traitee = true;
    setVentes(ventes);
  };

  if (loading) return <div className="spinner">Chargement...</div>;

  return (
    <div className="tableau-bord">
      <header>
        <h1>Tableau de bord</h1>
        <p>Période : {periode}</p>
      </header>

      <div className="stats">
        <div className="stat-card">
          <span className="stat-number">{total.toFixed(2)} €</span>
          <span className="stat-label">Chiffre d'affaires</span>
        </div>
        <div className="stat-card">
          <span className="stat-number">{ventes.length}</span>
          <span className="stat-label">Ventes</span>
        </div>
      </div>

      <input
        type="text"
        placeholder="Filtrer par produit"
        value={filtre}
        onChange={e => setFiltre(e.target.value)}
      />

      <table>
        <thead>
          <tr>
            <th>Produit</th>
            <th>Montant</th>
            <th>Date</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {ventesFiltrees.map((vente, index) => (
            <tr key={index} className={vente.traitee ? "traitee" : ""}>
              <td>{vente.produit}</td>
              <td>{vente.montant.toFixed(2)} €</td>
              <td>{new Date(vente.date).toLocaleDateString("fr-FR")}</td>
              <td>
                <button onClick={() => marquerCommeTraitee(index)}>
                  Marquer traitée
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {ventesFiltrees.length && (
        <footer>
          <p>{ventesFiltrees.length} résultat(s)</p>
        </footer>
      )}
    </div>
  );
}

export default TableauBord;
