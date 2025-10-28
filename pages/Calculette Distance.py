import streamlit as st
import pandas as pd
from calculators import get_cache
import io
import time
from config import get_api_key
import base64

st.set_page_config(
    page_title="Calcul de Distances par Lots",
    page_icon="📍",
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
    margin: 1rem auto 0rem auto;
    width: 80%;
    height: 100px;
    background-image: url("data:image/png;base64,{logo_b64}");
    background-repeat: no-repeat;
    background-position: center;
    background-size: contain;
}}
</style>
""", unsafe_allow_html=True)

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

# Charger la clé API ORS depuis st.secrets ou .env
api_key_ors = get_api_key()

if api_key_ors:
    st.sidebar.success("✅ Clé API OpenRouteService chargée")
    st.sidebar.info(
        "💡 **Validation croisée active** : Les distances sont calculées avec Nominatim ET "
        "OpenRouteService. Le système sélectionne automatiquement la valeur la plus réaliste."
    )
else:
    st.sidebar.warning(
        "⚠️ Clé API OpenRouteService non trouvée. "
        "Le calcul sera effectué uniquement avec Nominatim."
    )
    st.sidebar.info(
        "💡 **Conseil** : Ajoutez votre clé ORS dans les secrets "
        "pour activer la validation croisée."
    )


# Upload du fichier
uploaded_file = st.file_uploader(
    "📁 Glissez-déposez votre fichier Excel ici",
    type=["xlsx", "xls"],
    help="Le fichier doit contenir au minimum 2 colonnes avec les adresses"
)

if uploaded_file is not None:
    try:
        # Réinitialiser les résultats si un nouveau fichier est uploadé
        if 'uploaded_file_name' not in st.session_state or st.session_state['uploaded_file_name'] != uploaded_file.name:
            st.session_state['uploaded_file_name'] = uploaded_file.name
            # Vider le cache seulement lors d'un nouveau fichier
            cache = get_cache()
            cache.clear()
            if 'results_df' in st.session_state:
                del st.session_state['results_df']
                del st.session_state['success_count']
                del st.session_state['warning_count']
                del st.session_state['error_count']
                del st.session_state['address1_col']
                del st.session_state['address2_col']
                del st.session_state['distance_col']

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

        # Forcer les colonnes d'adresses à être de type string pour éviter les erreurs Arrow
        df[address1_col] = df[address1_col].astype(str)
        df[address2_col] = df[address2_col].astype(str)

        # Affichage aperçu des données
        st.markdown("### 👀 Aperçu des données")
        st.dataframe(df.head(10), use_container_width=True)

        st.info(f"📊 **{len(df)}** lignes détectées")
        st.info(f"📋 Colonnes identifiées :\n- Adresse 1 : `{address1_col}`\n- Adresse 2 : `{address2_col}`\n- Distance : `{distance_col}`")

        # Bouton de calcul
        if st.button("🚀 Calculer les distances", type="primary"):
            # Stocker les noms de colonnes dans session_state
            st.session_state['address1_col'] = address1_col
            st.session_state['address2_col'] = address2_col
            st.session_state['distance_col'] = distance_col

            progress_bar = st.progress(0)
            status_text = st.empty()

            # Préparer les paires d'adresses
            status_text.text("📋 Préparation des données...")
            addresses_pairs = []
            valid_indices = []

            for idx, row in df.iterrows():
                address1 = str(row[address1_col]).strip()
                address2 = str(row[address2_col]).strip()

                # Vérifier que les adresses ne sont pas vides
                if not address1 or address1 == "nan" or not address2 or address2 == "nan":
                    continue

                addresses_pairs.append((address1, address2))
                valid_indices.append(idx)

            total_valid = len(addresses_pairs)
            total_invalid = len(df) - total_valid

            if total_invalid > 0:
                st.warning(f"⚠️ {total_invalid} ligne(s) ignorée(s) (adresses manquantes)")

            # Calcul parallèle des distances avec suivi de progression
            start_time = time.time()

            # Utiliser ThreadPoolExecutor pour suivre la progression
            from concurrent.futures import ThreadPoolExecutor, as_completed
            from calculators import calculate_batch_distance

            results = [None] * total_valid
            completed = 0

            with ThreadPoolExecutor(max_workers=5) as executor:
                # Soumettre tous les calculs
                future_to_index = {
                    executor.submit(
                        calculate_batch_distance,
                        addr1, addr2,
                        api_key_ors=api_key_ors,
                        quiet=True
                    ): idx
                    for idx, (addr1, addr2) in enumerate(addresses_pairs)
                }

                # Collecter les résultats avec mise à jour de la progress bar
                for future in as_completed(future_to_index):
                    idx = future_to_index[future]
                    try:
                        results[idx] = future.result()
                    except Exception as e:
                        # Créer un résultat d'erreur
                        addr1, addr2 = addresses_pairs[idx]
                        from calculators import BatchDistanceResult
                        results[idx] = BatchDistanceResult(
                            final_distance=None,
                            nominatim_distance=None,
                            ors_distance=None,
                            source="none",
                            status="error",
                            message=f"Erreur: {str(e)}",
                            address1=addr1,
                            address2=addr2
                        )

                    completed += 1
                    progress = completed / total_valid
                    progress_bar.progress(progress)
                    status_text.text(f"Calcul en cours... {completed}/{total_valid}")

            elapsed_time = time.time() - start_time

            # Statistiques du cache
            cache = get_cache()
            cache_stats = cache.get_stats()

            # Initialiser les listes avec des valeurs par défaut pour toutes les lignes
            distances = [None] * len(df)
            sources = ["none"] * len(df)
            statuses = ["error"] * len(df)
            messages = ["Adresse manquante"] * len(df)
            nominatim_distances = [None] * len(df)
            ors_distances = [None] * len(df)

            # Remplir avec les résultats valides
            for idx, result in zip(valid_indices, results):
                distances[idx] = result.final_distance
                sources[idx] = result.source
                statuses[idx] = result.status
                messages[idx] = result.message
                nominatim_distances[idx] = result.nominatim_distance
                ors_distances[idx] = result.ors_distance

            # Compter les statistiques
            success_count = sum(1 for s in statuses if s == "ok")
            warning_count = sum(1 for s in statuses if s == "warning")
            error_count = sum(1 for s in statuses if s == "error")

            average_count = sum(1 for src in sources if src == "average")
            nominatim_only_count = sum(1 for src in sources if src == "nominatim")
            ors_only_count = sum(1 for src in sources if src == "ors")

            # Mise à jour du DataFrame
            df[distance_col] = distances
            df["Source"] = sources
            df["Statut"] = statuses
            df["Message"] = messages
            df["Distance Nominatim (km)"] = nominatim_distances
            df["Distance ORS (km)"] = ors_distances

            status_text.text("✅ Calcul terminé !")
            progress_bar.progress(1.0)

            # Stocker les résultats dans session_state
            st.session_state['results_df'] = df
            st.session_state['success_count'] = success_count
            st.session_state['warning_count'] = warning_count
            st.session_state['error_count'] = error_count

        # Affichage des résultats (en dehors du if button pour qu'ils persistent)
        if 'results_df' in st.session_state:
            df = st.session_state['results_df']
            success_count = st.session_state['success_count']
            warning_count = st.session_state['warning_count']
            error_count = st.session_state['error_count']
            address1_col = st.session_state['address1_col']
            address2_col = st.session_state['address2_col']
            distance_col = st.session_state['distance_col']

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

            # Export du fichier - seulement les 3 colonnes principales
            df_export = df[[address1_col, address2_col, distance_col]].copy()

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False, sheet_name='Distances calculées')

            excel_data = output.getvalue()

            st.download_button(
                label="📥 Télécharger le fichier Excel avec les distances",
                data=excel_data,
                file_name="distances_calculees.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

    except Exception as e:
        st.error(f"❌ Erreur lors du traitement du fichier : {str(e)}")
        st.exception(e)

else:
    st.info("👆 Commencez par uploader un fichier Excel avec 2 colonnes d'adresses")

    # Afficher un exemple de fichier
    st.markdown("### 📝 Exemple de fichier attendu")
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
    "Calcul de distances avec validation croisée "
    "</div>",
    unsafe_allow_html=True
)
