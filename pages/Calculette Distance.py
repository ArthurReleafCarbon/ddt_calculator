import streamlit as st
import pandas as pd
from batch_distance_calculator import calculate_batch_distance
import io
import os
import logging
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

st.set_page_config(
    page_title="Calcul de Distances par Lots",
    page_icon="📍",
    layout="wide"
)

st.title("📍 Calcul de Distances par Lots")
st.markdown("---")

st.markdown("""
### Instructions
1. Préparez un fichier Excel avec **3 colonnes** :
   - **Colonne 1** : Adresse de départ (rue + numéro + ville)
   - **Colonne 2** : Adresse d'arrivée (rue + numéro + ville)
   - **Colonne 3** : Distance (vide, sera remplie automatiquement)
2. Uploadez votre fichier
3. L'application calculera automatiquement les distances entre chaque paire d'adresses
4. Téléchargez le fichier enrichi avec les distances calculées

**Note** : Le système utilise la validation croisée Nominatim + OpenRouteService pour garantir la précision des résultats.
""")

# Sidebar configuration
st.sidebar.header("⚙️ Configuration")

st.sidebar.markdown("### 🌐 Service de géolocalisation")

# Charger la clé API ORS depuis .env
api_key_ors = os.getenv("API_ORS")

if api_key_ors:
    st.sidebar.success("✅ Clé API OpenRouteService chargée")
    st.sidebar.info(
        "💡 **Validation croisée active** : Les distances sont calculées avec Nominatim ET "
        "OpenRouteService. Le système sélectionne automatiquement la valeur la plus réaliste."
    )
else:
    st.sidebar.warning(
        "⚠️ Clé API OpenRouteService non trouvée dans .env. "
        "Le calcul sera effectué uniquement avec Nominatim."
    )
    st.sidebar.info(
        "💡 **Conseil** : Ajoutez votre clé ORS dans le fichier .env "
        "pour activer la validation croisée."
    )

st.sidebar.markdown("---")
st.sidebar.markdown("### 📋 Format attendu")
st.sidebar.markdown("""
**Exemple de structure Excel :**

| Adresse 1 | Adresse 2 | Distance (km) |
|-----------|-----------|---------------|
| 12 Rue de la Paix, Paris | 5 Avenue des Champs-Élysées, Paris | |
| Lille | Marseille | |
| 10 Rue Victor Hugo, Lyon | 25 Boulevard Haussmann, Paris | |

**La colonne Distance peut avoir n'importe quel nom, elle sera remplie automatiquement.**
""")

# Upload du fichier
uploaded_file = st.file_uploader(
    "📁 Glissez-déposez votre fichier Excel ici",
    type=["xlsx", "xls"],
    help="Le fichier doit contenir au minimum 2 colonnes avec les adresses"
)

if uploaded_file is not None:
    try:
        # Lecture du fichier Excel
        df = pd.read_excel(uploaded_file)

        # Vérification du nombre de colonnes
        if len(df.columns) < 2:
            st.error("❌ Le fichier doit contenir au moins 2 colonnes (Adresse 1, Adresse 2)")
            st.stop()

        # Si pas de 3ème colonne, en créer une
        if len(df.columns) < 3:
            df["Distance (km)"] = None
            st.info("ℹ️ Colonne 'Distance (km)' ajoutée automatiquement")

        # Renommer les colonnes pour faciliter le traitement
        col_names = df.columns.tolist()
        address1_col = col_names[0]
        address2_col = col_names[1]
        distance_col = col_names[2] if len(col_names) > 2 else "Distance (km)"

        # Affichage aperçu des données
        st.markdown("### 👀 Aperçu des données")
        st.dataframe(df.head(10), use_container_width=True)

        st.info(f"📊 **{len(df)}** lignes détectées")
        st.info(f"📋 Colonnes identifiées :\n- Adresse 1 : `{address1_col}`\n- Adresse 2 : `{address2_col}`\n- Distance : `{distance_col}`")

        # Bouton de calcul
        if st.button("🚀 Calculer les distances", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()

            distances = []
            sources = []
            statuses = []
            messages = []
            nominatim_distances = []
            ors_distances = []

            # Statistiques
            success_count = 0
            error_count = 0
            warning_count = 0
            average_count = 0
            nominatim_only_count = 0
            ors_only_count = 0

            # Configurer le logger
            logger = logging.getLogger('batch_distance_calculator')

            for idx, row in df.iterrows():
                status_text.text(f"Calcul en cours... {idx + 1}/{len(df)}")
                progress_bar.progress((idx + 1) / len(df))

                address1 = str(row[address1_col]).strip()
                address2 = str(row[address2_col]).strip()

                # Vérifier que les adresses ne sont pas vides
                if not address1 or address1 == "nan" or not address2 or address2 == "nan":
                    distances.append(None)
                    sources.append("none")
                    statuses.append("error")
                    messages.append("Adresse manquante")
                    nominatim_distances.append(None)
                    ors_distances.append(None)
                    error_count += 1
                    continue

                # Calcul avec validation croisée
                result = calculate_batch_distance(
                    address1,
                    address2,
                    api_key_ors=api_key_ors
                )

                distances.append(result.final_distance)
                sources.append(result.source)
                statuses.append(result.status)
                messages.append(result.message)
                nominatim_distances.append(result.nominatim_distance)
                ors_distances.append(result.ors_distance)

                # Compter les statistiques
                if result.status == "ok":
                    success_count += 1
                    if result.source == "average":
                        average_count += 1
                    elif result.source == "nominatim":
                        nominatim_only_count += 1
                    elif result.source == "ors":
                        ors_only_count += 1
                elif result.status == "warning":
                    warning_count += 1
                else:
                    error_count += 1

            # Mise à jour du DataFrame
            df[distance_col] = distances
            df["Source"] = sources
            df["Statut"] = statuses
            df["Message"] = messages
            df["Distance Nominatim (km)"] = nominatim_distances
            df["Distance ORS (km)"] = ors_distances

            status_text.text("✅ Calcul terminé !")
            progress_bar.progress(1.0)

            # Affichage des statistiques
            st.markdown("### 📊 Statistiques de Calcul")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("✅ Succès", success_count, delta=None)
            with col2:
                st.metric("⚠️ Avertissements", warning_count, delta=None)
            with col3:
                st.metric("❌ Erreurs", error_count, delta=None)
            with col4:
                st.metric("📊 Total", len(df), delta=None)

            if api_key_ors:
                st.markdown("#### 🔍 Détail des sources de validation")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📐 Moyenne (< 10% diff)", average_count)
                with col2:
                    st.metric("📡 Nominatim seul", nominatim_only_count)
                with col3:
                    st.metric("📡 ORS seul", ors_only_count)

            # Affichage des erreurs
            if error_count > 0:
                with st.expander(f"⚠️ {error_count} erreur(s) de calcul"):
                    error_df = df[df["Statut"] == "error"][[address1_col, address2_col, "Message"]]
                    st.dataframe(error_df, use_container_width=True)

            # Affichage des avertissements
            if warning_count > 0:
                with st.expander(f"⚠️ {warning_count} avertissement(s)"):
                    warning_df = df[df["Statut"] == "warning"][[address1_col, address2_col, distance_col, "Message"]]
                    st.dataframe(warning_df, use_container_width=True)

            # Affichage du résultat complet
            st.markdown("### 📋 Résultat détaillé")
            st.dataframe(df, use_container_width=True)

            # Export du fichier
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Distances calculées')

            excel_data = output.getvalue()

            st.download_button(
                label="📥 Télécharger le fichier Excel avec les distances",
                data=excel_data,
                file_name="distances_calculees.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

            # Statistiques de distance
            valid_distances = [d for d in distances if d is not None]
            if valid_distances:
                st.markdown("### 📏 Statistiques de Distance")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Distance minimale", f"{min(valid_distances):.2f} km")
                with col2:
                    st.metric("Distance moyenne", f"{sum(valid_distances) / len(valid_distances):.2f} km")
                with col3:
                    st.metric("Distance maximale", f"{max(valid_distances):.2f} km")

    except Exception as e:
        st.error(f"❌ Erreur lors du traitement du fichier : {str(e)}")
        st.exception(e)

else:
    st.info("👆 Commencez par uploader un fichier Excel avec 2 colonnes d'adresses")

    # Afficher un exemple de fichier
    st.markdown("### 📝 Exemple de fichier")
    example_df = pd.DataFrame({
        "Adresse 1": [
            "12 Rue de la Paix, Paris",
            "Place Bellecour, Lyon",
            "Lille",
            "10 Rue Victor Hugo, Lyon"
        ],
        "Adresse 2": [
            "5 Avenue des Champs-Élysées, Paris",
            "25 Boulevard Haussmann, Paris",
            "Marseille",
            "Bordeaux"
        ],
        "Distance (km)": [None, None, None, None]
    })
    st.dataframe(example_df, use_container_width=True)

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Calcul de distances par lots avec validation croisée | "
    "Aucun plafond de distance"
    "</div>",
    unsafe_allow_html=True
)
