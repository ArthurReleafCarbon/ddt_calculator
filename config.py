"""
Module de configuration pour gérer les secrets
Compatible avec développement local (.env) et Streamlit Cloud (st.secrets)
"""
import os
import streamlit as st

def get_api_key():
    """
    Récupère la clé API OpenRouteService depuis st.secrets ou .env

    Returns:
        str: La clé API ou None si non trouvée
    """
    # Priorité 1: Streamlit Secrets (pour Streamlit Cloud)
    try:
        if hasattr(st, 'secrets') and 'secrets' in st.secrets:
            return st.secrets['secrets']['API_ORS']
    except (KeyError, FileNotFoundError):
        pass

    # Priorité 2: Variables d'environnement (pour développement local avec .env)
    try:
        from dotenv import load_dotenv
        load_dotenv()
        return os.getenv("API_ORS")
    except ImportError:
        # Si python-dotenv n'est pas installé, essayer quand même os.getenv
        return os.getenv("API_ORS")
