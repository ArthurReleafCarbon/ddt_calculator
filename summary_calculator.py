import pandas as pd

def create_summary_report(df):
    """
    Crée un rapport récapitulatif avec groupby par mode de transport, type de véhicule et énergie

    Args:
        df: DataFrame contenant les colonnes:
            - Mode de transport
            - Type de véhicule (pour voiture)
            - Type d'énergie (pour voiture)
            - Distance (km)

    Returns:
        DataFrame avec le récapitulatif
    """

    # Créer une colonne combinée pour le groupby
    df_copy = df.copy()

    # Pour les voitures, créer une catégorie détaillée
    def create_category(row):
        if pd.isna(row["Mode de transport"]):
            return "Non renseigné"

        mode = str(row["Mode de transport"]).strip()

        if mode.lower() == "voiture":
            vehicle = str(row.get("Type de véhicule", "")).strip() if not pd.isna(row.get("Type de véhicule")) else ""
            energy = str(row.get("Type d'énergie", "")).strip() if not pd.isna(row.get("Type d'énergie")) else ""

            if vehicle and energy:
                return f"Voiture - {vehicle.capitalize()} - {energy.capitalize()}"
            elif vehicle:
                return f"Voiture - {vehicle.capitalize()}"
            else:
                return "Voiture"
        else:
            return mode.capitalize()

    df_copy["Catégorie"] = df_copy.apply(create_category, axis=1)

    # Vérifier si la colonne Distance annuelle existe
    has_distance_annuelle = "Distance annuelle (km)" in df_copy.columns

    # Définir les agrégations
    agg_dict = {
        "Distance (km)": "sum"
    }

    if has_distance_annuelle:
        agg_dict["Distance annuelle (km)"] = "sum"

    # Grouper par catégorie
    summary = df_copy.groupby("Catégorie").agg(agg_dict).reset_index()

    # Renommer les colonnes
    if has_distance_annuelle:
        summary.columns = [
            "Catégorie",
            "Distance totale (km)",
            "Distance annuelle totale (km)"
        ]
    else:
        summary.columns = [
            "Catégorie",
            "Distance totale (km)"
        ]

    # Arrondir les valeurs
    summary["Distance totale (km)"] = summary["Distance totale (km)"].round(2)

    if has_distance_annuelle:
        summary["Distance annuelle totale (km)"] = summary["Distance annuelle totale (km)"].round(2)
        # Trier par distance annuelle décroissante
        summary = summary.sort_values("Distance annuelle totale (km)", ascending=False)
    else:
        # Trier par distance totale décroissante
        summary = summary.sort_values("Distance totale (km)", ascending=False)

    # Ajouter une ligne de total
    total_dict = {
        "Catégorie": ["TOTAL"],
        "Distance totale (km)": [summary["Distance totale (km)"].sum().round(2)]
    }

    if has_distance_annuelle:
        total_dict["Distance annuelle totale (km)"] = [summary["Distance annuelle totale (km)"].sum().round(2)]

    total_row = pd.DataFrame(total_dict)

    summary = pd.concat([summary, total_row], ignore_index=True)

    return summary


def create_transport_mode_summary(df):
    """
    Crée un récapitulatif simple par mode de transport principal
    """
    summary = df.groupby("Mode de transport").agg({
        "Distance (km)": "sum"
    }).reset_index()

    summary.columns = [
        "Mode de transport",
        "Distance totale (km)"
    ]

    summary["Distance totale (km)"] = summary["Distance totale (km)"].round(2)

    return summary.sort_values("Distance totale (km)", ascending=False)
