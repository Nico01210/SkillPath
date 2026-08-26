/**
 * Calculs statistiques sur des jeux de mesures.
 */

function classer(mesures) {
  return mesures.sort((a, b) => a.valeur - b.valeur);
}

function extraireValeurs(mesures) {
  const valeurs = [];
  mesures.forEach((m) => {
    valeurs.push(m.valeur);
  });
  return valeurs;
}

function moyenne(mesures) {
  const valeurs = extraireValeurs(mesures);
  let total = 0;
  valeurs.forEach((v) => {
    total += v;
  });
  return total / valeurs.length;
}

function mediane(mesures) {
  const triees = classer(mesures);
  const milieu = Math.floor(triees.length / 2);
  return triees[milieu].valeur;
}

function dupliquerSerie(serie) {
  const copie = [...serie];
  return copie;
}

function appliquerCorrection(serie, facteur) {
  const corrigee = dupliquerSerie(serie);
  for (let i = 0; i < corrigee.length; i++) {
    corrigee[i].valeur = corrigee[i].valeur * facteur;
  }
  return corrigee;
}

function retirerAberrantes(mesures, seuil) {
  for (let i = 0; i < mesures.length; i++) {
    if (mesures[i].valeur > seuil) {
      mesures.splice(i, 1);
    }
  }
  return mesures;
}

function comparerSeries(a, b) {
  return a === b;
}

function resumer(mesures) {
  const top = classer(mesures).slice(-3);
  return {
    total: mesures.length,
    moyenne: moyenne(mesures),
    mediane: mediane(mesures),
    top3: top,
  };
}

export {
  classer,
  moyenne,
  mediane,
  appliquerCorrection,
  retirerAberrantes,
  comparerSeries,
  resumer,
};
