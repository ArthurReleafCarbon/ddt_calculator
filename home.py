import streamlit as st

st.set_page_config(
    page_title="Calculateur de Distances",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Calculateur de Distances")
st.markdown("---")

st.markdown("""
# Bienvenue !

Cette application propose deux modes de calcul de distances :

### 📍 Calcul de Distances par Lots
- Importez un fichier Excel avec 2 colonnes d'adresses
- Calculez automatiquement les distances entre chaque paire
- Validation croisée Nominatim + OpenRouteService

### 🚗 Calculateur Domicile-Travail
- Spécialement conçu pour le poste domicile-travail, sur base de la trame Releaf Carbon
- Calcul des distances annuelles
- Récapitulatif par mode de transport
- Validation des données Excel

---

👈 **Sélectionnez un mode dans la barre latérale pour commencer !**
""")

st.markdown("---")

st.markdown("### 🔧 Configuration requise")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Services de géolocalisation :**
    - 🌍 Nominatim (OpenStreetMap) - Gratuit
    - 📍 OpenRouteService - Clé API requise

    **Recommandation :** Configurez une clé API OpenRouteService dans votre fichier `.env`
    pour bénéficier de la validation croisée et d'une meilleure précision.
    """)

with col2:
    st.markdown("""
    **Format des fichiers :**
    - 📊 Excel (.xlsx, .xls)
    - Encodage UTF-8
    - Colonnes clairement identifiées

    **Note :** Les exemples de format sont disponibles dans chaque section.
    """)

st.markdown("---")

st.info("""
💡 **Astuce** : Pour des résultats optimaux, utilisez des adresses complètes
incluant le numéro, la rue et la ville.
""")

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Développé pour le calcul de distances et bilans carbone | "
    "Compatible avec toutes les communes de France"
    "</div>",
    unsafe_allow_html=True
)
