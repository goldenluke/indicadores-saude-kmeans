# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from pysus.online_data.SIM import download as download_sim
from pysus.online_data.SINASC import download as download_sinasc
import geopandas as gpd
import matplotlib.pyplot as plt

# A função agora não aceita parâmetros.
def calcular_tmi():
    """
    Calcula a Taxa de Mortalidade Infantil para TO/2022, com parâmetros definidos internamente.
    """
    # --- PARÂMETROS GERAIS DEFINIDOS INTERNAMENTE ---
    UF_SIGLA = 'TO'
    ANO = 2022
    ARQUIVO_POPULACAO = "populacao_brasil_censo_2022_com_estado.csv"

    print(f"Iniciando o processo de cálculo da TMI para {UF_SIGLA}/{ANO}...")

    # --- PASSO 0: CARREGAR BASE MUNICIPAL ---
    print("\nPasso 0/5: Carregando base local com população e municípios...")
    try:
        df_base_completa = pd.read_csv(ARQUIVO_POPULACAO, sep=';', dtype={'cod_mun_ibge_6': str, 'cod_mun_ibge_7': str})
        # Filtra a base para a UF de interesse
        df_base = df_base_completa[df_base_completa['UF'] == UF_SIGLA].copy()
        df_base.set_index('cod_mun_ibge_6', inplace=True)
        print(f"Base local carregada e filtrada para {UF_SIGLA}: {df_base.shape[0]} municípios.\n")
    except FileNotFoundError:
        print(f"⚠️ Arquivo '{ARQUIVO_POPULACAO}' não encontrado.")
        return None
    except KeyError:
        print(f"⚠️ A coluna 'estado' não foi encontrada no arquivo de população. Verifique o arquivo.")
        return None

    # --- PASSO 1: OBTER DADOS SIM (ÓBITOS INFANTIS) ---
    print("Passo 1/5: Obtendo dados SIM (óbitos infantis)...")
    sim_files = download_sim(states=UF_SIGLA, years=ANO, groups=["CID10"])
    df_sim = sim_files.to_dataframe()
    print(f"Dados SIM carregados: {df_sim.shape[0]} linhas")

    df_sim["IDADE"] = pd.to_numeric(df_sim["IDADE"], errors="coerce")
    df_infantil = df_sim[df_sim["IDADE"] < 401]
    obitos_infantis = df_infantil.groupby("CODMUNRES").size().rename("obitos_infantis")
    print(f"Óbitos infantis filtrados: {obitos_infantis.sum()} casos.\n")

    # --- PASSO 2: OBTER DADOS SINASC (NASCIDOS VIVOS) ---
    print("Passo 2/5: Obtendo dados SINASC (nascidos vivos)...")
    files_sinasc = download_sinasc(states=UF_SIGLA, years=ANO, groups=["DN"])

    if isinstance(files_sinasc, list) and len(files_sinasc) > 0:
        df_list = [f.to_dataframe() for f in files_sinasc]
        df_sinasc = pd.concat(df_list, ignore_index=True)
    elif hasattr(files_sinasc, "to_dataframe"):
        df_sinasc = files_sinasc.to_dataframe()
    else:
        df_sinasc = pd.DataFrame(columns=["CODMUNRES"])

    nascidos_vivos = df_sinasc.groupby("CODMUNRES").size().rename("nascidos_vivos")
    print(f"Total de nascidos vivos agrupados: {nascidos_vivos.sum()}\n")

    # --- PASSO 3: PADRONIZAR CHAVES E JUNTAR BASES ---
    print("Passo 3/5: Padronizando códigos municipais e unindo dados...")
    obitos_infantis.index = obitos_infantis.index.astype(str).str[:6]
    nascidos_vivos.index = nascidos_vivos.index.astype(str).str[:6]

    df_base = df_base.join(obitos_infantis, how='left')
    df_base = df_base.join(nascidos_vivos, how='left')
    df_base.fillna(0, inplace=True)
    df_base['obitos_infantis'] = df_base['obitos_infantis'].astype(int)
    df_base['nascidos_vivos'] = df_base['nascidos_vivos'].astype(int)

    # --- PASSO 4: CALCULAR TMI ---
    print("Passo 4/5: Calculando Taxa de Mortalidade Infantil (TMI)...")
    df_base['TMI'] = df_base.apply(
        lambda row: (row['obitos_infantis'] / row['nascidos_vivos']) * 1000 if row['nascidos_vivos'] > 0 else 0,
        axis=1
    )
    print("✅ Taxa de Mortalidade Infantil calculada.\n")

    # --- PASSO 5: VISUALIZAÇÃO ---
    print("Passo 5/5: Gerando mapa da TMI...")
    try:
        shapefile_path = "shapefiles/BR_Municipios_2022.shp"
        gdf_mun = gpd.read_file(shapefile_path)

        gdf_mun = gdf_mun[gdf_mun["SIGLA_UF"] == UF_SIGLA].copy()
        gdf_mun["CD_MUN"] = gdf_mun["CD_MUN"].astype(str).str[:6]
        gdf_mun.set_index("CD_MUN", inplace=True)

        gdf_mun = gdf_mun.join(df_base[["TMI"]], how="left")
        gdf_mun["TMI"] = gdf_mun["TMI"].fillna(0)

        fig, ax = plt.subplots(1, 1, figsize=(12, 10))
        gdf_mun.plot(
            column="TMI", cmap="Reds", linewidth=0.5, edgecolor="black", legend=True,
            legend_kwds={'label': "Taxa de Mortalidade Infantil (por mil)", 'shrink': 0.6},
            ax=ax
        )
        ax.set_title(f"Mapa da Taxa de Mortalidade Infantil (por mil) - {UF_SIGLA} ({ANO})", fontsize=16)
        ax.axis("off")
        plt.tight_layout()

        output_filename = f"mapa_tmi_{UF_SIGLA.lower()}_{ANO}.png"
        plt.savefig(output_filename, dpi=300)
        print(f"\nMapa salvo como '{output_filename}'")
        plt.show()

    except Exception as e:
        print(f"⚠️ Erro ao gerar o mapa: {e}")

    return df_base

# Bloco para execução independente do script
if __name__ == "__main__":
    df_resultado_tmi = calcular_tmi()
    if df_resultado_tmi is not None:
        print("\n--- Amostra do DataFrame Final (TMI) ---")
        print(df_resultado_tmi[['municipio', 'populacao', 'TMI']].head())
