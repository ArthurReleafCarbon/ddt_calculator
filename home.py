import streamlit as st
import base64

st.set_page_config(
    page_title="Calculette Distances",
    page_icon="🚗",
    layout="wide"
)

# Fonction cachée pour charger et encoder le logo
@st.cache_data
def load_logo_base64():
    with open("img/logo2.png", "rb") as f:
        return base64.b64encode(f.read()).decode()

# Fonction cachée pour charger l'image hero
@st.cache_resource
def load_hero_image():
    from PIL import Image
    return Image.open("img/heropic.jpg")

# Encodage du logo en base64 pour l'injecter en CSS (fiable en déploiement)
logo_b64 = load_logo_base64()

st.markdown(f"""
<style>
/* 1) Cas standard : navigation multipage visible (stSidebarNav) */
[data-testid="stSidebarNav"]::before {{
    content: "";
    display: block;
    margin: 0rem auto 1rem auto;
    width: 80%;
    height: 100px;
    background-image: url("data:image/png;base64,{logo_b64}");
    background-repeat: no-repeat;
    background-position: center;
    background-size: contain;
}}
</style>
""", unsafe_allow_html=True)
st.markdown("""
# Bienvenue !



""")

c1,c2 = st.columns([2,1])

with c1:
    st.markdown("""
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
    """)
    st.write("")
    st.write("")
    st.markdown(
    "<p style='text-align:left; font-weight:bold; font-size:18px;'>"
    "👈 Sélectionnez un mode dans la barre latérale pour commencer !"
    "</p>",
    unsafe_allow_html=True
    )
with c2:
    st.image(load_hero_image(), use_container_width=True)

st.write("")
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
