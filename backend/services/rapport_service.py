import html
import os
from backend.services import sqlite_service
from backend.models.schemas import RapportResponse, StatsRapport, Erreur, CoursLie
from backend.config import settings
from datetime import date, timedelta

 
 
def get_rapport(jour: date) -> RapportResponse:
    """
    Agrège toutes les analyses SQLite d'une date donnée et retourne le rapport
    structuré. Sert au rapport du jour, d'hier, ou de n'importe quelle journée
    passée (historique) — GET /rapport?date=AAAA-MM-JJ.
    """
    analyses = sqlite_service.get_analyses_par_date(jour)

    toutes_erreurs = []
    fichiers_vus = set()

    for analyse in analyses:
        fichiers_vus.add(analyse["fichier"])
        for e in analyse["erreurs"]:
            # Reconstruit les objets Pydantic depuis les dicts JSON
            cours = [CoursLie(**c) for c in e.get("cours", [])]
            toutes_erreurs.append(Erreur(
                niveau=e["niveau"],
                titre=e["titre"],
                fichier=e["fichier"],
                ligne=e["ligne"],
                description=e["description"],
                extrait=e["extrait"],
                cours=cours
            ))

    critiques = sum(1 for e in toutes_erreurs if e.niveau == "critique")
    avertissements = sum(1 for e in toutes_erreurs if e.niveau == "avertissement")
    # Déduplique les cours recommandés pour compter les cours uniques
    cours_uniques = {c.chunk_id for e in toutes_erreurs for c in e.cours}

    return RapportResponse(
        date=jour,
        stats=StatsRapport(
            critiques=critiques,
            avertissements=avertissements,
            fichiers_analyses=len(fichiers_vus),
            cours_a_relire=len(cours_uniques)
        ),
        erreurs=toutes_erreurs
    )


def get_rapport_du_jour() -> RapportResponse:
    """Rapport d'aujourd'hui."""
    return get_rapport(date.today())


def get_rapport_hier() -> RapportResponse:
    """Rapport du jour précédent."""
    return get_rapport(date.today() - timedelta(days=1))


def generer_html(rapport: RapportResponse) -> str:
    """
    Génère le HTML complet du rapport journalier.
    Retourne une chaîne HTML prête à être sauvegardée ou envoyée.
    """
    # Génère les cartes d'erreurs
    cartes_html = ""
    for e in rapport.erreurs:
        niveau_class = "critique" if e.niveau == "critique" else "warning"
        niveau_label = "Critique" if e.niveau == "critique" else "Avertissement"
 
        cours_tags = "".join([
            f'<span class="cours-tag">{html.escape(c.titre)}</span>'
            for c in e.cours
        ]) or "<span class='no-cours'>Aucun cours lié</span>"

        cartes_html += f"""
        <div class="card {niveau_class}">
          <div class="card-header">
            <span class="badge {niveau_class}">{niveau_label}</span>
            <span class="card-title">{html.escape(e.titre)}</span>
            <span class="card-meta">{html.escape(e.fichier)} · ligne {e.ligne}</span>
          </div>
          <p class="description">{html.escape(e.description)}</p>
          <pre class="extrait">{html.escape(e.extrait)}</pre>
          <div class="cours-section">
            <span class="cours-label">📚 Cours à relire</span>
            <div class="cours-tags">{cours_tags}</div>
          </div>
        </div>"""

    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SkillPath — Rapport du {rapport.date}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f8f9fa; color: #1a1a1a; padding: 2rem; }}
    .container {{ max-width: 860px; margin: 0 auto; }}
    header {{ display: flex; justify-content: space-between; align-items: flex-start;
              border-bottom: 1px solid #e5e7eb; padding-bottom: 1.5rem; margin-bottom: 1.5rem; }}
    h1 {{ font-size: 1.25rem; font-weight: 600; }}
    .subtitle {{ font-size: .875rem; color: #6b7280; margin-top: 4px; }}
    .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 1.5rem; }}
    .stat {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 10px;
             padding: .875rem; text-align: center; }}
    .stat-n {{ font-size: 1.5rem; font-weight: 600; }}
    .stat-l {{ font-size: .75rem; color: #6b7280; margin-top: 2px; }}
    .rouge {{ color: #dc2626; }} .orange {{ color: #d97706; }}
    .bleu {{ color: #2563eb; }} .vert {{ color: #16a34a; }}
    .card {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 10px;
             padding: 1rem 1.25rem; margin-bottom: 12px; }}
    .card.critique {{ border-left: 3px solid #dc2626; }}
    .card.warning {{ border-left: 3px solid #d97706; }}
    .card-header {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }}
    .badge {{ font-size: .7rem; font-weight: 600; padding: 2px 8px; border-radius: 20px; }}
    .badge.critique {{ background: #fee2e2; color: #dc2626; }}
    .badge.warning {{ background: #fef3c7; color: #d97706; }}
    .card-title {{ font-size: .875rem; font-weight: 600; }}
    .card-meta {{ font-size: .75rem; color: #9ca3af; margin-left: auto; }}
    .description {{ font-size: .875rem; color: #374151; margin-bottom: 10px; }}
    pre.extrait {{ background: #f3f4f6; border-radius: 6px; padding: 10px 12px;
                   font-size: .8rem; overflow-x: auto; margin-bottom: 10px; }}
    .cours-section {{ border-top: 1px solid #f3f4f6; padding-top: 10px; }}
    .cours-label {{ font-size: .75rem; color: #6b7280; display: block; margin-bottom: 6px; }}
    .cours-tag {{ display: inline-block; font-size: .75rem; padding: 3px 10px;
                  border-radius: 20px; background: #eff6ff; color: #2563eb; margin: 2px 3px 2px 0; }}
    .no-cours {{ font-size: .75rem; color: #9ca3af; font-style: italic; }}
    footer {{ text-align: center; font-size: .75rem; color: #9ca3af; margin-top: 2rem; }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>SkillPath — Rapport du {rapport.date}</h1>
        <p class="subtitle">{rapport.stats.fichiers_analyses} fichier(s) analysé(s) · {len(rapport.erreurs)} erreur(s) détectée(s)</p>
      </div>
    </header>
 
    <div class="stats">
      <div class="stat"><div class="stat-n rouge">{rapport.stats.critiques}</div><div class="stat-l">Erreurs critiques</div></div>
      <div class="stat"><div class="stat-n orange">{rapport.stats.avertissements}</div><div class="stat-l">Avertissements</div></div>
      <div class="stat"><div class="stat-n bleu">{rapport.stats.fichiers_analyses}</div><div class="stat-l">Fichiers analysés</div></div>
      <div class="stat"><div class="stat-n vert">{rapport.stats.cours_a_relire}</div><div class="stat-l">Cours à relire</div></div>
    </div>
 
    {cartes_html}
 
    <footer>Généré par SkillPath · {rapport.date}</footer>
  </div>
</body>
</html>"""
 
    return html_content


def sauvegarder_html(html_content: str, jour: date | None = None) -> str:
    """
    Sauvegarde le HTML dans data/reports/ et retourne le chemin du fichier.
    Le nom de fichier porte la date du rapport (par défaut aujourd'hui).
    """
    jour = jour or date.today()
    os.makedirs(settings.reports_path, exist_ok=True)
    chemin = os.path.join(settings.reports_path, f"rapport_{jour.isoformat()}.html")
 
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(html_content)
 
    return chemin