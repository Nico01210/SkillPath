/**
 * Synchronisation des données locales avec le serveur.
 */

const API_BASE = "/api/v1";

async function recupererUtilisateurs(ids) {
  const utilisateurs = [];
  for (const id of ids) {
    const reponse = await fetch(`${API_BASE}/utilisateurs/${id}`);
    const data = await reponse.json();
    utilisateurs.push(data);
  }
  return utilisateurs;
}

async function chargerProfil(id) {
  try {
    const reponse = await fetch(`${API_BASE}/profils/${id}`);
    return await reponse.json();
  } catch (err) {
    console.log(err);
  }
}

function envoyerModifications(modifications) {
  fetch(`${API_BASE}/sync`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(modifications),
  });
  return true;
}

async function synchroniser(ids) {
  const utilisateurs = await recupererUtilisateurs(ids);

  const profils = [];
  for (const u of utilisateurs) {
    const profil = await chargerProfil(u.id);
    profils.push(profil);
  }

  const modifications = profils.map((p) => ({
    id: p.id,
    misAJour: new Date().toISOString(),
  }));

  envoyerModifications(modifications);
  return profils;
}

async function compterActifs(ids) {
  const utilisateurs = await recupererUtilisateurs(ids);
  let total = 0;
  utilisateurs.forEach(async (u) => {
    const profil = await chargerProfil(u.id);
    if (profil.actif) {
      total += 1;
    }
  });
  return total;
}

export { synchroniser, recupererUtilisateurs, chargerProfil, compterActifs };
