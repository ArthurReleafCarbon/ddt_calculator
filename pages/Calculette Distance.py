import streamlit as st
import pandas as pd
from calculators import get_cache, BatchProcessor, calculate_batch_distance
import io
import time
from config import get_api_key
import base64
import hashlib

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
        # Générer un session_id unique basé sur le nom du fichier
        session_id = hashlib.md5(uploaded_file.name.encode()).hexdigest()

        # Réinitialiser les résultats si un nouveau fichier est uploadé
        if 'uploaded_file_name' not in st.session_state or st.session_state['uploaded_file_name'] != uploaded_file.name:
            st.session_state['uploaded_file_name'] = uploaded_file.name
            st.session_state['session_id'] = session_id
            # NE PAS vider le cache persistant - il est réutilisable entre sessions
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

        # Vérifier s'il existe des résultats partiels d'une session précédente
        batch_processor = BatchProcessor(batch_size=50)
        has_pending, num_batches = batch_processor.has_pending_session(session_id)

        if has_pending:
            st.warning(f"⚠️ Résultats partiels détectés ({num_batches} batch(s) sauvegardé(s))")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📥 Récupérer les résultats partiels", type="secondary"):
                    partial_df = batch_processor.get_partial_results(session_id, df, address1_col, address2_col)
                    if partial_df is not None:
                        st.success("✅ Résultats partiels récupérés")
                        # Exporter les résultats partiels
                        df_export = partial_df[[address1_col, address2_col, distance_col]].copy()
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df_export.to_excel(writer, index=False, sheet_name='Distances calculées')
                        excel_data = output.getvalue()
                        st.download_button(
                            label="📥 Télécharger les résultats partiels",
                            data=excel_data,
                            file_name=f"distances_partielles_{uploaded_file.name}",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary"
                        )
            with col2:
                if st.button("🔄 Reprendre le calcul", type="primary"):
                    st.session_state['resume_calculation'] = True
                    st.rerun()

        # Bouton de calcul
        if st.button("🚀 Calculer les distances", type="primary") or st.session_state.get('resume_calculation', False):
            # Stocker les noms de colonnes dans session_state
            st.session_state['address1_col'] = address1_col
            st.session_state['address2_col'] = address2_col
            st.session_state['distance_col'] = distance_col

            # Réinitialiser le flag de reprise
            if 'resume_calculation' in st.session_state:
                del st.session_state['resume_calculation']

            # Utiliser st.status pour un meilleur affichage de progression
            with st.status("Calcul des distances en cours...", expanded=True) as status:
                progress_bar = st.progress(0)
                status_text = st.empty()

                # Callback pour mettre à jour la progression
                def update_progress(current: int, total: int, message: str):
                    try:
                        progress = current / total if total > 0 else 0
                        progress_bar.progress(min(progress, 1.0))
                        status_text.markdown(f"**{message}** : {current}/{total} lignes")
                    except Exception as e:
                        # En cas d'erreur Streamlit, juste logger
                        print(f"Erreur mise à jour progress: {e}")

                # Calcul par batch avec sauvegarde temporaire
                start_time = time.time()
                status_text.text("📋 Préparation des données...")

                try:
                    result_df, stats = batch_processor.process_batches(
                        df=df,
                        process_function=calculate_batch_distance,
                        address1_col=address1_col,
                        address2_col=address2_col,
                        session_id=session_id,
                        progress_callback=update_progress,
                        max_workers=5,
                        api_key_ors=api_key_ors,
                        quiet=True
                    )

                    elapsed_time = time.time() - start_time

                    # Statistiques du cache
                    cache = get_cache()
                    cache_stats = cache.get_stats()

                    status_text.text("✅ Calcul terminé !")
                    progress_bar.progress(1.0)

                    # Marquer le status comme complété
                    status.update(label="✅ Calcul terminé !", state="complete")

                    # Afficher les stats du cache
                    if cache_stats['cache_size'] > 0:
                        st.info(f"💾 Cache: {cache_stats['cache_size']} adresses enregistrées | "
                               f"Taux de hit: {cache_stats['hit_rate']:.1f}% "
                               f"({cache_stats['hits']} hits, {cache_stats['misses']} misses)")

                    st.success(f"✅ Traitement terminé en {elapsed_time:.1f} secondes")

                    # Stocker les résultats dans session_state
                    st.session_state['results_df'] = result_df
                    st.session_state['success_count'] = stats['success_count']
                    st.session_state['warning_count'] = stats['warning_count']
                    st.session_state['error_count'] = stats['error_count']

                except Exception as e:
                    status.update(label="❌ Erreur lors du calcul", state="error")
                    st.error(f"❌ Erreur lors du calcul: {str(e)}")
                    st.exception(e)
                    # Proposer de récupérer les résultats partiels
                    st.warning("💡 Des résultats partiels ont peut-être été sauvegardés. Rechargez la page pour les récupérer.")

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
