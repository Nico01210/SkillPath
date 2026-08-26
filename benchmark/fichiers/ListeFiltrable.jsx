/**
 * Liste filtrable et triable, avec sélection multiple.
 *
 * L'état est réduit au strict nécessaire : tout ce qui peut être calculé
 * au rendu l'est, plutôt que d'être stocké et synchronisé.
 */

import React, { useState, useMemo, useCallback } from "react";

/** Ordres de tri proposés, exposés pour permettre le test unitaire. */
export const ORDRES = Object.freeze({
  ALPHABETIQUE: "alphabetique",
  RECENT: "recent",
});

/**
 * Trie une copie de la liste selon l'ordre demandé.
 * @param {Array<{id: string, nom: string, date: string}>} elements - Les éléments à trier.
 * @param {string} ordre - L'ordre de tri souhaité.
 * @returns {Array} Une nouvelle liste triée, l'entrée reste intacte.
 */
function trier(elements, ordre) {
  const copie = [...elements];

  if (ordre === ORDRES.RECENT) {
    return copie.sort((a, b) => new Date(b.date) - new Date(a.date));
  }
  return copie.sort((a, b) => a.nom.localeCompare(b.nom, "fr"));
}

/**
 * Ne conserve que les éléments dont le nom contient le filtre.
 * @param {Array<{nom: string}>} elements - Les éléments à filtrer.
 * @param {string} filtre - Le texte recherché.
 * @returns {Array} Une nouvelle liste filtrée.
 */
function filtrer(elements, filtre) {
  const recherche = filtre.trim().toLowerCase();
  if (recherche.length === 0) {
    return elements;
  }
  return elements.filter((e) => e.nom.toLowerCase().includes(recherche));
}

function ListeFiltrable({ elements, onSelectionChange }) {
  const [filtre, setFiltre] = useState("");
  const [ordre, setOrdre] = useState(ORDRES.ALPHABETIQUE);
  const [selection, setSelection] = useState(() => new Set());

  // Valeurs dérivées : calculées au rendu, jamais stockées dans l'état.
  const visibles = useMemo(
    () => trier(filtrer(elements, filtre), ordre),
    [elements, filtre, ordre]
  );

  const toutSelectionne = visibles.length > 0 && visibles.every((e) => selection.has(e.id));

  const basculerSelection = useCallback(
    (id) => {
      setSelection((precedente) => {
        const suivante = new Set(precedente);
        if (suivante.has(id)) {
          suivante.delete(id);
        } else {
          suivante.add(id);
        }
        onSelectionChange?.([...suivante]);
        return suivante;
      });
    },
    [onSelectionChange]
  );

  const basculerTout = useCallback(() => {
    setSelection((precedente) => {
      const suivante = toutSelectionne ? new Set() : new Set(visibles.map((e) => e.id));
      onSelectionChange?.([...suivante]);
      return suivante;
    });
  }, [toutSelectionne, visibles, onSelectionChange]);

  if (elements.length === 0) {
    return (
      <div className="liste-vide">
        <p className="liste-vide-titre">Aucun élément</p>
        <p className="liste-vide-texte">Ajoutez un premier élément pour commencer.</p>
      </div>
    );
  }

  return (
    <div className="liste-filtrable">
      <div className="liste-controles">
        <input
          type="search"
          value={filtre}
          onChange={(e) => setFiltre(e.target.value)}
          placeholder="Filtrer par nom"
          aria-label="Filtrer la liste par nom"
        />

        <select
          value={ordre}
          onChange={(e) => setOrdre(e.target.value)}
          aria-label="Ordre de tri"
        >
          <option value={ORDRES.ALPHABETIQUE}>Ordre alphabétique</option>
          <option value={ORDRES.RECENT}>Plus récent d'abord</option>
        </select>

        <button type="button" onClick={basculerTout}>
          {toutSelectionne ? "Tout désélectionner" : "Tout sélectionner"}
        </button>
      </div>

      {visibles.length === 0 ? (
        <p className="liste-aucun-resultat">Aucun élément ne correspond à « {filtre} ».</p>
      ) : (
        <ul className="liste-elements">
          {visibles.map((element) => (
            <li key={element.id} className="liste-element">
              <label>
                <input
                  type="checkbox"
                  checked={selection.has(element.id)}
                  onChange={() => basculerSelection(element.id)}
                />
                <span className="element-nom">{element.nom}</span>
                <time dateTime={element.date}>
                  {new Date(element.date).toLocaleDateString("fr-FR")}
                </time>
              </label>
            </li>
          ))}
        </ul>
      )}

      <footer className="liste-pied">
        <span>
          {visibles.length} élément{visibles.length > 1 ? "s" : ""} affiché
          {visibles.length > 1 ? "s" : ""} sur {elements.length}
        </span>
        {selection.size > 0 && <span>{selection.size} sélectionné(s)</span>}
      </footer>
    </div>
  );
}

export default ListeFiltrable;
