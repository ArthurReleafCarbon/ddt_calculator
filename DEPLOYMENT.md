# 🚀 Guide de Déploiement sur Streamlit Cloud

## Prérequis
- Compte GitHub avec le code pushé
- Compte Streamlit Cloud (gratuit) sur [share.streamlit.io](https://share.streamlit.io)
- Clé API OpenRouteService (gratuite) de [openrouteservice.org](https://openrouteservice.org)

## Étapes de déploiement

### 1. Préparer votre repository GitHub
```bash
# Assurez-vous que tous les fichiers sont commités
git add .
git commit -m "Ready for Streamlit Cloud deployment"
git push origin main
```

### 2. Déployer sur Streamlit Cloud

1. Allez sur [share.streamlit.io](https://share.streamlit.io)
2. Cliquez sur "New app"
3. Connectez votre repository GitHub
4. Configurez l'application :
   - **Repository** : `votre-username/auto_dist_ddt`
   - **Branch** : `main` (ou `master`)
   - **Main file path** : `home.py`
5. Cliquez sur "Advanced settings"

### 3. Configurer les Secrets

Dans la section **Secrets**, ajoutez votre clé API au format TOML :

```toml
[secrets]
API_ORS = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjE0OTFkMzM5Nzg5NDQ3ODU4OTBhNzM2ZDQ1MjI5OGI5IiwiaCI6Im11cm11cjY0In0="
```

**⚠️ Important** :
- Respectez exactement cette structure (avec `[secrets]` en première ligne)
- N'utilisez **PAS** de guillemets simples, uniquement des guillemets doubles
- Remplacez la valeur par votre propre clé API si nécessaire

### 4. Déployer

Cliquez sur "Deploy!" et attendez que l'application se lance (2-3 minutes).

## Vérification après déploiement

Une fois l'application déployée, vérifiez que :

1. ✅ La page d'accueil s'affiche correctement
2. ✅ Les deux pages sont accessibles dans la barre latérale :
   - 📍 Calculette Distance
   - 🚗 Calculette Domicile-Travail
3. ✅ Le message "✅ Clé API OpenRouteService chargée" apparaît dans la sidebar
4. ✅ Vous pouvez uploader un fichier Excel

## Mise à jour de l'application

Pour mettre à jour l'application après des modifications :

```bash
git add .
git commit -m "Update: description des changements"
git push origin main
```

Streamlit Cloud redéploiera automatiquement l'application en 1-2 minutes.

## Mise à jour des Secrets

Si vous devez changer votre clé API :

1. Allez sur votre app sur Streamlit Cloud
2. Cliquez sur "Settings" (⚙️) en haut à droite
3. Allez dans l'onglet "Secrets"
4. Modifiez la clé API
5. Sauvegardez (l'app redémarrera automatiquement)

## Troubleshooting

### L'app ne démarre pas
- Vérifiez que `home.py` est bien le fichier principal spécifié
- Consultez les logs dans Streamlit Cloud (bouton "Manage app" > "Logs")

### "Module not found"
- Vérifiez que toutes les dépendances sont dans `requirements.txt`
- Vérifiez qu'il n'y a pas de versions incompatibles

### La clé API ne fonctionne pas
- Vérifiez le format dans les Secrets (doit être du TOML valide)
- Vérifiez que la clé API est valide sur openrouteservice.org
- Essayez de redémarrer l'app : Settings > Reboot app

### Erreurs de calcul de distance
- L'app fonctionne aussi sans clé API (uniquement Nominatim)
- Vérifiez que les adresses sont complètes et valides

## Support

- Documentation Streamlit Cloud : [docs.streamlit.io](https://docs.streamlit.io/streamlit-community-cloud)
- OpenRouteService API : [openrouteservice.org/dev](https://openrouteservice.org/dev/)
