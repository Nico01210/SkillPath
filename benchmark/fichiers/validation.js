/**
 * Règles de validation de formulaire.
 *
 * Toutes les fonctions sont pures : elles ne modifient aucun état
 * externe et retournent toujours une nouvelle valeur.
 */

const LONGUEUR_MIN_MOT_DE_PASSE = 12;
const LONGUEUR_MAX_CHAMP = 255;

/** Motif de code postal français : cinq chiffres. */
const MOTIF_CODE_POSTAL = /^[0-9]{5}$/;

/** Motif de numéro de téléphone français, avec ou sans indicatif. */
const MOTIF_TELEPHONE = /^(?:\+33|0)[1-9](?:[0-9]{8})$/;

/** Libellés de rejet — constantes fixes, sans donnée saisie par l'utilisateur. */
const RAISONS = Object.freeze({
  REQUIS: "Ce champ est obligatoire",
  TROP_LONG: `Ce champ dépasse ${LONGUEUR_MAX_CHAMP} caractères`,
  MOT_DE_PASSE_COURT: `Le mot de passe doit contenir au moins ${LONGUEUR_MIN_MOT_DE_PASSE} caractères`,
  MOT_DE_PASSE_FAIBLE: "Le mot de passe doit mêler majuscules, minuscules et chiffres",
  CODE_POSTAL_INVALIDE: "Le code postal doit contenir cinq chiffres",
  TELEPHONE_INVALIDE: "Le numéro de téléphone n'est pas au format attendu",
  CONFIRMATION_DIFFERENTE: "Les deux saisies ne correspondent pas",
});

/**
 * Construit un résultat de validation.
 * @param {boolean} valide - Si la valeur satisfait la règle.
 * @param {string|null} [raison] - Le libellé de rejet le cas échéant.
 * @returns {{valide: boolean, raison: string|null}} Le résultat.
 */
function resultat(valide, raison = null) {
  return { valide, raison };
}

/**
 * Vérifie qu'un champ obligatoire est renseigné.
 * @param {string} valeur - La valeur saisie.
 * @returns {{valide: boolean, raison: string|null}} Le résultat.
 */
export function validerRequis(valeur) {
  if (typeof valeur !== "string" || valeur.trim().length === 0) {
    return resultat(false, RAISONS.REQUIS);
  }
  return resultat(true);
}

/**
 * Vérifie qu'un champ ne dépasse pas la longueur maximale.
 * @param {string} valeur - La valeur saisie.
 * @returns {{valide: boolean, raison: string|null}} Le résultat.
 */
export function validerLongueur(valeur) {
  if (typeof valeur !== "string") {
    return resultat(false, RAISONS.REQUIS);
  }
  if (valeur.length > LONGUEUR_MAX_CHAMP) {
    return resultat(false, RAISONS.TROP_LONG);
  }
  return resultat(true);
}

/**
 * Vérifie la robustesse d'un mot de passe.
 *
 * La règle porte sur la longueur et la diversité des caractères, sans
 * imposer de caractère spécial : cette contrainte pousse en pratique
 * les utilisateurs vers des mots de passe plus courts.
 *
 * @param {string} valeur - Le mot de passe saisi.
 * @returns {{valide: boolean, raison: string|null}} Le résultat.
 */
export function validerMotDePasse(valeur) {
  if (typeof valeur !== "string" || valeur.length === 0) {
    return resultat(false, RAISONS.REQUIS);
  }

  if (valeur.length < LONGUEUR_MIN_MOT_DE_PASSE) {
    return resultat(false, RAISONS.MOT_DE_PASSE_COURT);
  }

  const aMajuscule = /[A-Z]/.test(valeur);
  const aMinuscule = /[a-z]/.test(valeur);
  const aChiffre = /[0-9]/.test(valeur);

  if (!aMajuscule || !aMinuscule || !aChiffre) {
    return resultat(false, RAISONS.MOT_DE_PASSE_FAIBLE);
  }

  return resultat(true);
}

/**
 * Vérifie qu'une confirmation correspond à la saisie d'origine.
 * @param {string} valeur - La saisie d'origine.
 * @param {string} confirmation - La saisie de confirmation.
 * @returns {{valide: boolean, raison: string|null}} Le résultat.
 */
export function validerConfirmation(valeur, confirmation) {
  if (valeur !== confirmation) {
    return resultat(false, RAISONS.CONFIRMATION_DIFFERENTE);
  }
  return resultat(true);
}

/**
 * Vérifie le format d'un code postal français.
 * @param {string} valeur - Le code postal saisi.
 * @returns {{valide: boolean, raison: string|null}} Le résultat.
 */
export function validerCodePostal(valeur) {
  if (typeof valeur !== "string" || !MOTIF_CODE_POSTAL.test(valeur.trim())) {
    return resultat(false, RAISONS.CODE_POSTAL_INVALIDE);
  }
  return resultat(true);
}

/**
 * Vérifie le format d'un numéro de téléphone français.
 * @param {string} valeur - Le numéro saisi, espaces tolérés.
 * @returns {{valide: boolean, raison: string|null}} Le résultat.
 */
export function validerTelephone(valeur) {
  if (typeof valeur !== "string") {
    return resultat(false, RAISONS.TELEPHONE_INVALIDE);
  }

  const compacte = valeur.replace(/[\s.-]/g, "");

  if (!MOTIF_TELEPHONE.test(compacte)) {
    return resultat(false, RAISONS.TELEPHONE_INVALIDE);
  }
  return resultat(true);
}

/**
 * Applique une série de règles à un formulaire complet.
 *
 * Chaque champ est validé indépendamment des autres : aucun état n'est
 * partagé entre les validations successives.
 *
 * @param {Object<string, string>} champs - Les valeurs saisies, par nom de champ.
 * @param {Object<string, Function>} regles - La règle à appliquer à chaque champ.
 * @returns {{valide: boolean, erreurs: Object<string, string>}} Le bilan.
 */
export function validerFormulaire(champs, regles) {
  const erreurs = {};

  for (const [nom, regle] of Object.entries(regles)) {
    const { valide, raison } = regle(champs[nom]);
    if (!valide) {
      erreurs[nom] = raison;
    }
  }

  return { valide: Object.keys(erreurs).length === 0, erreurs };
}
