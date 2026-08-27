/**
 * Utilitaires de formatage pour l'affichage de données métier.
 *
 * Toutes les fonctions sont pures : elles ne modifient aucun état
 * externe et retournent toujours une nouvelle valeur.
 */

const LOCALE_PAR_DEFAUT = "fr-FR";
const DEVISE_PAR_DEFAUT = "EUR";

/** Seuils utilisés pour le formatage des durées relatives, en secondes. */
const SEUILS_DUREE = Object.freeze([
  { limite: 60, unite: "second", diviseur: 1 },
  { limite: 3600, unite: "minute", diviseur: 60 },
  { limite: 86400, unite: "hour", diviseur: 3600 },
  { limite: 2592000, unite: "day", diviseur: 86400 },
]);

/** Seuil appliqué au-delà d'un mois écoulé. */
const SEUIL_DUREE_MOIS = Object.freeze({ unite: "month", diviseur: 2592000 });

/** Unités de taille de fichier, par puissance de 1024 croissante. */
const UNITES_TAILLE = Object.freeze(["o", "Ko", "Mo", "Go", "To"]);

const OCTETS_PAR_UNITE = 1024;

/**
 * Formate un montant en devise locale.
 * @param {number} montant - Le montant à formater.
 * @param {string} [devise] - Le code ISO de la devise.
 * @param {string} [locale] - La locale d'affichage.
 * @returns {string} Le montant formaté, ou une chaîne vide si l'entrée est invalide.
 */
export function formaterMontant(
  montant,
  devise = DEVISE_PAR_DEFAUT,
  locale = LOCALE_PAR_DEFAUT
) {
  if (!Number.isFinite(montant)) {
    return "";
  }

  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: devise,
  }).format(montant);
}

/**
 * Convertit une entrée en objet Date valide.
 * @param {Date|string|number} valeur - La valeur à convertir.
 * @returns {Date|null} La date convertie, ou null si la conversion échoue.
 */
function versDate(valeur) {
  const date = valeur instanceof Date ? valeur : new Date(valeur);
  return Number.isFinite(date.getTime()) ? date : null;
}

/**
 * Formate une date au format long localisé.
 * @param {Date|string} date - La date à formater.
 * @param {string} [locale] - La locale d'affichage.
 * @returns {string} La date formatée, ou une chaîne vide si l'entrée est invalide.
 */
export function formaterDate(date, locale = LOCALE_PAR_DEFAUT) {
  const objetDate = versDate(date);

  if (objetDate === null) {
    return "";
  }

  return new Intl.DateTimeFormat(locale, {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(objetDate);
}

/**
 * Formate une durée écoulée sous forme relative ("il y a 3 minutes").
 * @param {Date|string} date - La date de référence.
 * @param {string} [locale] - La locale d'affichage.
 * @returns {string} La durée relative formatée, ou une chaîne vide si l'entrée est invalide.
 */
export function formaterDureeRelative(date, locale = LOCALE_PAR_DEFAUT) {
  const objetDate = versDate(date);

  if (objetDate === null) {
    return "";
  }

  const secondesEcoulees = Math.trunc((objetDate.getTime() - Date.now()) / 1000);
  const secondesAbsolues = Math.abs(secondesEcoulees);

  let seuil = SEUIL_DUREE_MOIS;
  for (const candidat of SEUILS_DUREE) {
    if (secondesAbsolues < candidat.limite) {
      seuil = candidat;
      break;
    }
  }

  const valeur = Math.trunc(secondesEcoulees / seuil.diviseur);

  return new Intl.RelativeTimeFormat(locale, { numeric: "auto" }).format(
    valeur,
    seuil.unite
  );
}

/**
 * Tronque un texte à une longueur maximale en préservant les mots entiers.
 * @param {string} texte - Le texte à tronquer.
 * @param {number} longueurMax - La longueur maximale souhaitée.
 * @param {string} [suffixe] - Le suffixe ajouté en cas de troncature.
 * @returns {string} Le texte tronqué, ou une chaîne vide si l'entrée est invalide.
 */
export function tronquer(texte, longueurMax, suffixe = "…") {
  if (typeof texte !== "string") {
    return "";
  }

  if (texte.length <= longueurMax) {
    return texte;
  }

  const coupe = texte.slice(0, longueurMax);
  const dernierEspace = coupe.lastIndexOf(" ");
  const base = dernierEspace > 0 ? coupe.slice(0, dernierEspace) : coupe;

  return base + suffixe;
}

/**
 * Formate une taille de fichier en unité lisible.
 * @param {number} octets - La taille en octets.
 * @param {string} [locale] - La locale d'affichage.
 * @returns {string} La taille formatée, ou une chaîne vide si l'entrée est invalide.
 */
export function formaterTaille(octets, locale = LOCALE_PAR_DEFAUT) {
  if (!Number.isFinite(octets) || octets < 0) {
    return "";
  }

  let valeur = octets;
  let indexUnite = 0;

  while (valeur >= OCTETS_PAR_UNITE && indexUnite < UNITES_TAILLE.length - 1) {
    valeur /= OCTETS_PAR_UNITE;
    indexUnite += 1;
  }

  const decimales = indexUnite === 0 ? 0 : 1;
  const nombreFormate = new Intl.NumberFormat(locale, {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  }).format(valeur);

  return nombreFormate + " " + UNITES_TAILLE[indexUnite];
}

/**
 * Convertit une chaîne en slug utilisable dans une URL.
 * @param {string} texte - Le texte à convertir.
 * @returns {string} Le slug généré, ou une chaîne vide si l'entrée est invalide.
 */
export function creerSlug(texte) {
  if (typeof texte !== "string") {
    return "";
  }

  const sansAccents = texte.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  const minuscules = sansAccents.toLowerCase().trim();
  const avecTirets = minuscules.replace(/[^a-z0-9]+/g, "-");

  return avecTirets.replace(/^-+|-+$/g, "");
}

/**
 * Met en majuscule la première lettre d'une chaîne.
 * @param {string} texte - Le texte à capitaliser.
 * @returns {string} Le texte capitalisé, ou une chaîne vide si l'entrée est invalide.
 */
export function capitaliser(texte) {
  if (typeof texte !== "string" || texte.length === 0) {
    return "";
  }

  return texte.charAt(0).toUpperCase() + texte.slice(1);
}
