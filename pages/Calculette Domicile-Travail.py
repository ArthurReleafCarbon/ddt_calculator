import streamlit as st
import pandas as pd
from calculators import (
    calculate_distance,
    calculate_distance_dual_validation,
    create_summary_report,
    create_transport_mode_summary
)
from validation import ExcelValidator
import io
import logging
from config import get_api_key
import base64

st.set_page_config(
    page_title="Calculateur Distance Domicile-Travail",
    page_icon="🚗",
    layout="wide"
)
# Encodage du logo en base64 pour l'injecter en CSS (fiable en déploiement)
with open("img/logo2.png", "rb") as f:
    logo_b64 = base64.b64encode(f.read()).decode()

st.markdown(f"""
<style>
/* 1) Cas standard : navigation multipage visible (stSidebarNav) */
[data-testid="stSidebarNav"]::before {{
    content: "";
    display: block;
    margin: 1rem auto 1rem auto;
    width: 80%;
    height: 100px;
    background-image: url("data:image/png;base64,{logo_b64}");
    background-repeat: no-repeat;
    background-position: center;
    background-size: contain;
}}
</style>
""", unsafe_allow_html=True)
st.title("📍 Calcul de Distances domicile-travail")
st.markdown("---")

# Créer deux colonnes pour Instructions et Système de validation
col_instructions, col_validation = st.columns([1, 1])

with col_instructions:
    st.markdown("""
    ### Instructions
    1. Uploadez votre fichier Excel contenant les données de déplacements
    2. L'application calculera automatiquement les distances
    3. Téléchargez le fichier enrichi avec les résultats détaillés et le récapitulatif par mode de transport
    """)

with col_validation:
    st.markdown("""
    ### 🎯 Système de validation croisée
    Le système calcule automatiquement avec **2 services** (Nominatim + OpenRouteService) et sélectionne la valeur la plus fiable :
    - **Différence < 10%** → Moyenne des deux valeurs
    - **Différence > 10%** → Valeur la plus petite
    - **Distance > 300 km** → Rejetée automatiquement (aberrante)
    """)

# Configuration de l'API
st.sidebar.header("⚙️ Configuration")

# Sélection de l'année du bilan
st.sidebar.markdown("### 📅 Paramètres du bilan")

# Dictionnaire des jours fériés en semaine par année
JOURS_FERIES = {
    2023: 9,
    2024: 10,
    2025: 10,
    2026: 9,
}

annee_bilan = st.sidebar.selectbox(
    "Année du bilan:",
    options=sorted(JOURS_FERIES.keys(), reverse=True),
    index=1,  # 2024 par défaut
    help="Sélectionner l'année du bilan pour calculer les distances annuelles"
)

jours_feries = JOURS_FERIES.get(annee_bilan, 10)
st.sidebar.info(f"ℹ️ Jours fériés en semaine pour {annee_bilan}: **{jours_feries} jours**")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📍 Localisation")

# Dictionnaire des départements français
DEPARTEMENTS = {
    "01": "Ain", "02": "Aisne", "03": "Allier", "04": "Alpes-de-Haute-Provence", "05": "Hautes-Alpes",
    "06": "Alpes-Maritimes", "07": "Ardèche", "08": "Ardennes", "09": "Ariège", "10": "Aube",
    "11": "Aude", "12": "Aveyron", "13": "Bouches-du-Rhône", "14": "Calvados", "15": "Cantal",
    "16": "Charente", "17": "Charente-Maritime", "18": "Cher", "19": "Corrèze", "21": "Côte-d'Or",
    "22": "Côtes-d'Armor", "23": "Creuse", "24": "Dordogne", "25": "Doubs", "26": "Drôme",
    "27": "Eure", "28": "Eure-et-Loir", "29": "Finistère", "2A": "Corse-du-Sud", "2B": "Haute-Corse",
    "30": "Gard", "31": "Haute-Garonne", "32": "Gers", "33": "Gironde", "34": "Hérault",
    "35": "Ille-et-Vilaine", "36": "Indre", "37": "Indre-et-Loire", "38": "Isère", "39": "Jura",
    "40": "Landes", "41": "Loir-et-Cher", "42": "Loire", "43": "Haute-Loire", "44": "Loire-Atlantique",
    "45": "Loiret", "46": "Lot", "47": "Lot-et-Garonne", "48": "Lozère", "49": "Maine-et-Loire",
    "50": "Manche", "51": "Marne", "52": "Haute-Marne", "53": "Mayenne", "54": "Meurthe-et-Moselle",
    "55": "Meuse", "56": "Morbihan", "57": "Moselle", "58": "Nièvre", "59": "Nord",
    "60": "Oise", "61": "Orne", "62": "Pas-de-Calais", "63": "Puy-de-Dôme", "64": "Pyrénées-Atlantiques",
    "65": "Hautes-Pyrénées", "66": "Pyrénées-Orientales", "67": "Bas-Rhin", "68": "Haut-Rhin", "69": "Rhône",
    "70": "Haute-Saône", "71": "Saône-et-Loire", "72": "Sarthe", "73": "Savoie", "74": "Haute-Savoie",
    "75": "Paris", "76": "Seine-Maritime", "77": "Seine-et-Marne", "78": "Yvelines", "79": "Deux-Sèvres",
    "80": "Somme", "81": "Tarn", "82": "Tarn-et-Garonne", "83": "Var", "84": "Vaucluse",
    "85": "Vendée", "86": "Vienne", "87": "Haute-Vienne", "88": "Vosges", "89": "Yonne",
    "90": "Territoire de Belfort", "91": "Essonne", "92": "Hauts-de-Seine", "93": "Seine-Saint-Denis",
    "94": "Val-de-Marne", "95": "Val-d'Oise", "971": "Guadeloupe", "972": "Martinique",
    "973": "Guyane", "974": "La Réunion", "976": "Mayotte"
}

# Créer la liste des options pour le selectbox
departement_options = ["Non spécifié"] + [f"{code} - {nom}" for code, nom in sorted(DEPARTEMENTS.items())]

departement_selection = st.sidebar.selectbox(
    "Département:",
    departement_options,
    index=departement_options.index("59 - Nord") if "59 - Nord" in departement_options else 0,
    help="Spécifier le département améliore la précision de géolocalisation"
)

# Extraire le nom du département
if departement_selection == "Non spécifié":
    region_choice = None
else:
    # Extraire le nom après le " - "
    region_choice = departement_selection.split(" - ", 1)[1] if " - " in departement_selection else None

st.sidebar.markdown("---")
st.sidebar.markdown("### 🌐 Service de géolocalisation")

# Charger automatiquement la clé API ORS depuis st.secrets ou .env
api_key_ors = get_api_key()

if api_key_ors:
    st.sidebar.success("✅ Clé API OpenRouteService chargée")
    st.sidebar.info(
        "💡 **Calcul automatique**: Les distances seront calculées avec Nominatim ET "
        "OpenRouteService pour garantir la précision. Le système sélectionnera automatiquement "
        "la valeur la plus réaliste."
    )
else:
    st.sidebar.warning(
        "⚠️ Clé API OpenRouteService non trouvée. "
        "Le calcul sera effectué uniquement avec Nominatim (plus lent)."
    )
    st.sidebar.info(
        "💡 **Conseil**: Ajoutez votre clé ORS dans les secrets "
        "pour activer la validation croisée des distances."
    )

# Upload du fichier
uploaded_file = st.file_uploader(
    "📁 Glissez-déposez votre fichier Excel ici",
    type=["xlsx", "xls"],
    help="Le fichier doit contenir les colonnes de commune de résidence et lieu de travail"
)

if uploaded_file is not None:
    try:
        # Validation du fichier Excel
        st.info("🔍 Validation du fichier en cours...")
        validator = ExcelValidator()
        validation_result = validator.validate_file(uploaded_file)

        # Affichage du rapport de validation
        st.markdown("### 📋 Rapport de Validation")

        # Statistiques générales
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Lignes totales", validation_result.total_rows)
        with col2:
            st.metric("✅ Lignes valides", validation_result.valid_rows)
        with col3:
            st.metric("❌ Lignes invalides", validation_result.total_rows - validation_result.valid_rows)

        # Affichage des erreurs critiques
        if validation_result.errors:
            st.error("🚫 Erreurs critiques détectées")
            for error in validation_result.errors:
                st.error(error)

        # Affichage des avertissements
        if validation_result.warnings:
            with st.expander(f"⚠️ Avertissements ({len(validation_result.warnings)})"):
                for warning in validation_result.warnings:
                    st.warning(warning)

        # Si la validation échoue, arrêter le traitement
        if not validation_result.is_valid:
            st.error("❌ Le fichier ne peut pas être traité. Veuillez corriger les erreurs ci-dessus.")
            st.stop()

        # Message de succès de validation
        st.success(f"✅ Validation réussie ! {validation_result.valid_rows} lignes peuvent être traitées sur {validation_result.total_rows}")

        # Lecture du fichier Excel avec la feuille spécifique
        # skiprows=5 pour ignorer les 5 premières lignes (1-5)
        # La ligne 6 devient les en-têtes de colonnes
        # Les données commencent à la ligne 7
        uploaded_file.seek(0)  # Réinitialiser le pointeur du fichier
        df = pd.read_excel(uploaded_file, sheet_name="Questionnaire dom-travail", skiprows=5)

        # Affichage aperçu
        with st.expander("👀 Aperçu des données"):
            st.dataframe(df.head(10))

        # Identifier les colonnes par leur position (index commence à 0)
        # F = colonne 5, H = colonne 7, I = colonne 8, J = colonne 9, L = colonne 11

        # Renommer les colonnes pour faciliter le traitement
        df_columns = df.columns.tolist()

        # Vérifier que le fichier a assez de colonnes
        if len(df_columns) < 12:
            st.error(f"❌ Le fichier n'a pas assez de colonnes. Nombre de colonnes: {len(df_columns)}")
        else:
            # Utiliser directement les colonnes existantes par leur position
            residence_col = df_columns[5]  # Colonne F
            jours_site_col = df_columns[6]  # Colonne G - Nombre de jours sur site par semaine
            transport_col = df_columns[7]  # Colonne H
            vehicle_col = df_columns[8]    # Colonne I
            energy_col = df_columns[9]     # Colonne J
            travail_col = df_columns[11]   # Colonne L

            has_transport_data = True

            st.info(f"📋 Colonnes identifiées:\n- Habitation: Colonne F\n- Jours/semaine: Colonne G\n- Transport: Colonne H\n- Véhicule: Colonne I\n- Énergie: Colonne J\n- Travail: Colonne L")

            if region_choice:
                st.success(f"🌍 Région sélectionnée: **{region_choice}**")
            else:
                st.warning("⚠️ Aucune région spécifiée - la géolocalisation peut être moins précise")

            # Bouton de calcul
            if st.button("🚀 Calculer les distances", type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()

                distances = []
                errors = []
                warnings = []

                # Initialiser les compteurs de statistiques
                dual_validation_count = 0
                nominatim_only_count = 0
                ors_only_count = 0
                average_count = 0
                manual_check_count = 0

                # Configurer le logger pour afficher dans le terminal
                logger = logging.getLogger('dual_distance_calculator')

                for idx, row in df.iterrows():
                    status_text.text(f"Calcul en cours... {idx + 1}/{len(df)}")
                    progress_bar.progress((idx + 1) / len(df))

                    commune_residence = str(row[residence_col]).strip()
                    commune_travail = str(row[travail_col]).strip()

                    # Calcul avec validation croisée si clé ORS disponible
                    if api_key_ors:
                        result = calculate_distance_dual_validation(
                            commune_residence,
                            commune_travail,
                            api_key_ors=api_key_ors,
                            region1=region_choice,
                            region2=region_choice
                        )

                        distance = result.final_distance

                        # Compter les sources
                        if result.source == "average":
                            average_count += 1
                        elif result.source == "nominatim":
                            nominatim_only_count += 1
                        elif result.source == "ors":
                            ors_only_count += 1
                        elif result.source == "both":
                            dual_validation_count += 1

                        if result.status == "error":
                            manual_check_count += 1
                            errors.append(f"Ligne {idx + 1}: {commune_residence} → {commune_travail} - {result.message}")
                        elif result.status == "warning":
                            warnings.append(f"Ligne {idx + 1}: {commune_residence} → {commune_travail} - {result.message}")

                    else:
                        # Fallback sur Nominatim uniquement
                        distance = calculate_distance(
                            commune_residence,
                            commune_travail,
                            api_choice="Nominatim (Gratuit)",
                            api_key=None,
                            region1=region_choice,
                            region2=region_choice
                        )
                        nominatim_only_count += 1

                    if distance is None:
                        if api_key_ors:
                            errors.append(f"Ligne {idx + 1}: {commune_residence} → {commune_travail} - Distance non calculable")
                        else:
                            errors.append(f"Ligne {idx + 1}: {commune_residence} → {commune_travail}")
                        distances.append(None)
                    else:
                        distances.append(round(distance, 2))

                # Ajout de la colonne distance
                df["Distance (km)"] = distances

                # Afficher les statistiques de validation dans les logs
                if api_key_ors:
                    logger.info(f"\n{'='*80}")
                    logger.info(f"📊 RAPPORT DE VALIDATION CROISÉE")
                    logger.info(f"{'='*80}")
                    logger.info(f"✅ Validation par moyenne (diff < 10%): {average_count}")
                    logger.info(f"✅ Même commune confirmée par les deux: {dual_validation_count}")
                    logger.info(f"⚠️  Nominatim uniquement: {nominatim_only_count}")
                    logger.info(f"⚠️  ORS uniquement: {ors_only_count}")
                    logger.info(f"❌ À vérifier manuellement: {manual_check_count}")
                    logger.info(f"{'='*80}\n")

                # Calcul du nombre de jours travaillés par an et de la distance annuelle
                jours_annuels = []
                distances_annuelles = []

                for idx, row in df.iterrows():
                    jours_par_semaine = row[jours_site_col]
                    distance_km = row["Distance (km)"]

                    # Vérifier que les valeurs sont valides
                    if pd.notna(jours_par_semaine) and pd.notna(distance_km):
                        try:
                            jours_par_semaine = float(jours_par_semaine)
                            # Calcul: (jours/semaine × 52) - jours fériés
                            nb_jours_annuel = (jours_par_semaine * 52) - jours_feries
                            jours_annuels.append(round(nb_jours_annuel, 0))

                            # Calcul distance annuelle: distance × nb_jours × 2 (aller-retour)
                            distance_annuelle = distance_km * nb_jours_annuel * 2
                            distances_annuelles.append(round(distance_annuelle, 2))
                        except (ValueError, TypeError):
                            jours_annuels.append(None)
                            distances_annuelles.append(None)
                    else:
                        jours_annuels.append(None)
                        distances_annuelles.append(None)

                df["Jours travaillés/an"] = jours_annuels
                df["Distance annuelle (km)"] = distances_annuelles

                status_text.text("✅ Calcul terminé !")
                progress_bar.progress(1.0)

                # Affichage des erreurs
                if errors:
                    with st.expander(f"⚠️ {len(errors)} erreur(s) de calcul"):
                        for error in errors:
                            st.warning(error)

                # Affichage du résultat
                st.success(f"🎉 Distances calculées avec succès !")

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Lignes traitées", len(df))
                with col2:
                    st.metric("Distances calculées", len(df) - len(errors))

                # Aperçu du résultat
                with st.expander("📊 Résultat détaillé"):
                    st.dataframe(df)

                # Génération du récapitulatif
                st.markdown(f"### 📊 Récapitulatif par mode de transport - Année {annee_bilan}")

                # Créer un DataFrame pour le récapitulatif avec les colonnes nécessaires
                df_summary = df[[residence_col, travail_col, transport_col, vehicle_col, energy_col, jours_site_col, "Distance (km)", "Distance annuelle (km)"]].copy()
                df_summary.columns = ["Lieu d'habitation", "Lieu de travail", "Mode de transport", "Type de véhicule", "Type d'énergie", "Jours/semaine", "Distance (km)", "Distance annuelle (km)"]

                summary_detailed = create_summary_report(df_summary)
                st.dataframe(summary_detailed, use_container_width=True)

                # Export du fichier avec 2 feuilles
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Questionnaire dom-travail')
                    summary_detailed.to_excel(writer, index=False, sheet_name='Récapitulatif')

                excel_data = output.getvalue()

                st.download_button(
                    label="📥 Télécharger le fichier Excel complet",
                    data=excel_data,
                    file_name="DDT_avec_distances.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
    
    except Exception as e:
        st.error(f"❌ Erreur lors du traitement du fichier: {str(e)}")
        st.exception(e)

else:
    st.info("👆 Commencez par uploader un fichier Excel")

    # Afficher un exemple de fichier
    st.markdown("### 📝 Format attendu du fichier Excel")

    st.markdown("""
    **Structure requise :**
    - Feuille nommée : `Questionnaire dom-travail`
    - Ligne 6 : En-têtes de colonnes
    - Ligne 7+ : Données
    """)

    example_df = pd.DataFrame({
        "Colonne F\nCommune de résidence": [
            "Paris",
            "Lyon",
            "Marseille",
            "Lille"
        ],
        "Colonne G\nJours/semaine sur site": [
            5,
            4,
            3,
            5
        ],
        "Colonne H\nMoyen de transport": [
            "Voiture",
            "Voiture",
            "Transport en commun",
            "Vélo ou marche"
        ],
        "Colonne I\nCatégorie voiture": [
            "Petite",
            "Moyenne",
            "",
            ""
        ],
        "Colonne J\nÉnergie voiture": [
            "Essence",
            "Diesel",
            "",
            ""
        ],
        "Colonne L\nLieu de travail": [
            "La Défense, Paris",
            "Villeurbanne",
            "Aix-en-Provence",
            "Roubaix"
        ]
    })

    st.dataframe(example_df, use_container_width=True)

    st.markdown("""
    **Notes importantes :**
    - Les colonnes I et J (catégorie et énergie voiture) sont **obligatoires uniquement** si le transport est "Voiture"
    - Les communes peuvent être précisées avec leur département ou région
    - Le nombre de jours/semaine doit être entre 1 et 5
    """)

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Développé pour le calcul des émissions domicile-travail | "
    "Compatible avec toutes les communes de France"
    "</div>",
    unsafe_allow_html=True
)