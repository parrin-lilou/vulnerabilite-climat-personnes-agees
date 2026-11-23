"""
Calcul des indicateurs climatiques WorldClim par EPCI.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd
from rasterstats import zonal_stats

DOSSIER = Path(__file__).resolve().parent.parent / "data"  # données brutes, non versionnées (voir README)

# --- Fichiers d'entrée -------------------------------------------------------
SHAPEFILE = DOSSIER / "EPCI" / "EPCI.shp"
ACTUEL = {
    "BIO5": DOSSIER / "climat_actuel" / "bio5_1970-2000.tif",
    "BIO6": DOSSIER / "climat_actuel" / "bio6_1970-2000.tif",
}
FUTUR = {  # fichiers "bioc" : 19 bandes, la bande n correspond à BIOn
    "245": DOSSIER / "climat_futur" / "bioc_ssp245_2081-2100.tif",
    "585": DOSSIER / "climat_futur" / "bioc_ssp585_2081-2100.tif",
}
SORTIE = DOSSIER / "climat_epci.csv"


def moyenne_par_epci(epci, raster, bande=1):
    """Moyenne des pixels du raster à l'intérieur de chaque EPCI."""
    stats = zonal_stats(
        epci,
        str(raster),
        band=bande,
        stats=["mean"],
        all_touched=True,  # compte aussi les pixels en bordure (utile pour les petits EPCI)
    )
    return pd.Series([s["mean"] for s in stats], index=epci.index).round(2)


# --- 1. Charger les EPCI et les passer dans le système de coordonnées de WorldClim
epci = gpd.read_file(SHAPEFILE)
print(f"{len(epci)} EPCI chargés")
epci_wgs84 = epci.to_crs("EPSG:4326")  # Lambert-93 -> latitude/longitude

resultat = pd.DataFrame({"CODE_SIREN": epci["CODE_SIREN"].astype(str)})

# --- 2. Climat actuel (1970-2000)
print("Climat actuel...")
resultat["BIO5_ACT"] = moyenne_par_epci(epci_wgs84, ACTUEL["BIO5"])
resultat["BIO6_ACT"] = moyenne_par_epci(epci_wgs84, ACTUEL["BIO6"])

# --- 3. Climat futur (2081-2100), un bloc de colonnes par scénario
for ssp, fichier in FUTUR.items():
    print(f"Scénario SSP{ssp[0]}-{ssp[1]}.{ssp[2]}...")
    resultat[f"BIO5_{ssp}"] = moyenne_par_epci(epci_wgs84, fichier, bande=5)
    resultat[f"BIO6_{ssp}"] = moyenne_par_epci(epci_wgs84, fichier, bande=6)
    resultat[f"HAUS5_{ssp}"] = (resultat[f"BIO5_{ssp}"] - resultat["BIO5_ACT"]).round(2)

# --- 4. Contrôles et export
manquants = resultat.isna().any(axis=1).sum()
print(f"\nEPCI avec au moins une valeur manquante : {manquants}")
print(resultat.drop(columns="CODE_SIREN").describe().round(1))

resultat.to_csv(SORTIE, index=False)
print(f"\nFichier créé : {SORTIE}")
