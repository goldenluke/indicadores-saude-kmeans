# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from pysus.online_data.SIM import download as download_sim

def calcular_indicador_causas_mal_definidas():
    """
    Script completo para baixar dados de mortalidade, calcular e visualizar
    a Proporção e a Taxa de Óbitos por Causas Mal Definidas para o Tocantins em 2022.
    """
    print("Iniciando o processo de cálculo do indicador: Óbitos por Causas Mal Definidas...")

    UF_SIGLA = 'TO'
    ANO = 2022
    ARQUIVO_POPULACAO = "populacao_brasil_censo_2022_com_estado.csv"

    print(f"Iniciando o processo de cálculo para {UF_SIGLA}/{ANO}...")

    # --- PASSO 0: CARREGAR BASE MUNICIPAL ---
    print("\nPasso 0/5: Carregando base local com população e municípios...")
    try:
        df_base_completa = pd.read_csv(ARQUIVO_POPULACAO, sep=';', dtype={'cod_mun_ibge_6': str, 'cod_mun_ibge_7': str})
        df_base = df_base_completa[df_base_completa['UF'] == UF_SIGLA].copy()
        df_base.set_index('cod_mun_ibge_6', inplace=True)
        print(f"Base local carregada e filtrada para {UF_SIGLA}: {df_base.shape[0]} municípios.\n")
    except FileNotFoundError:
        print(f"⚠️ Arquivo '{ARQUIVO_POPULACAO}' não encontrado.")
        return None
    except KeyError:
        print(f"⚠️ A coluna 'estado' não foi encontrada no arquivo de população. Verifique o arquivo.")
        return None

    # --- PASSO 1: OBTENÇÃO DOS DADOS DE MORTALIDADE (SIM) ---
    print("Passo 1/5: Obtendo dados SIM (óbitos totais)...")
    sim_files = download_sim(states=UF_SIGLA, years=ANO, groups=["CID10"])
    df_sim = sim_files.to_dataframe()
    print(f"Dados SIM carregados: {df_sim.shape[0]} linhas totais de óbitos.")

    # --- PASSO 2: CONTABILIZANDO ÓBITOS TOTAIS E POR CAUSAS MAL DEFINIDAS ---
    print("Passo 2/5: Contabilizando óbitos totais e por causas mal definidas...")

    total_obitos = df_sim.groupby("CODMUNRES").size().rename("total_obitos")
    print(f"Total de óbitos no estado: {total_obitos.sum()}")

    df_mal_definidas = df_sim[df_sim['CAUSABAS'].str.startswith('R', na=False)].copy()
    obitos_mal_definidos = df_mal_definidas.groupby("CODMUNRES").size().rename("obitos_mal_definidos")
    print(f"Total de óbitos por causas mal definidas: {obitos_mal_definidos.sum()}\n")

    # --- PASSO 3: PADRONIZAR CHAVES E JUNTAR BASES ---
    print("Passo 3/5: Padronizando códigos municipais e unindo dados...")

    total_obitos.index = total_obitos.index.astype(str).str[:6]
    obitos_mal_definidos.index = obitos_mal_definidos.index.astype(str).str[:6]

    df_base = df_base.join(total_obitos, how='left')
    df_base = df_base.join(obitos_mal_definidos, how='left')

    df_base['total_obitos'] = df_base['total_obitos'].fillna(0).astype(int)
    df_base['obitos_mal_definidos'] = df_base['obitos_mal_definidos'].fillna(0).astype(int)

    # --- PASSO 4: CÁLCULO DOS INDICADORES ---
    print("Passo 4/5: Calculando a Proporção e a Taxa de Óbitos por Causas Mal Definidas...")

    df_base['PROP_MAL_DEFINIDAS'] = df_base.apply(
        lambda row: (row['obitos_mal_definidos'] / row['total_obitos']) * 100 if row['total_obitos'] > 0 else 0,
        axis=1
    )

    df_base['TX_MAL_DEFINIDAS_P10K'] = df_base.apply(
        lambda row: (row['obitos_mal_definidos'] / row['populacao']) * 10000 if row['populacao'] > 0 else 0,
        axis=1
    )

    print("✅ Indicadores calculados com sucesso.\n")
    print("Top 10 municípios por Taxa de Óbitos Mal Definidos por 10 mil habitantes:")
    print(df_base[['populacao', 'obitos_mal_definidos', 'TX_MAL_DEFINIDAS_P10K']].sort_values(by='TX_MAL_DEFINIDAS_P10K', ascending=False).head(10).round(2))

    # --- PASSO 5: VISUALIZAÇÃO - MAPA DE CALOR ---
    print("\nPasso 5/5: Carregando shapefile e gerando o mapa...")
    try:
        shapefile_path = "shapefiles/BR_Municipios_2022.shp"
        gdf_mun = gpd.read_file(shapefile_path)
    except Exception as e:
        print(f"⚠️ Não foi possível carregar o shapefile de '{shapefile_path}'. Verifique o caminho. Erro: {e}")
        return

    gdf_mun = gdf_mun[gdf_mun["SIGLA_UF"] == UF_SIGLA].copy()
    gdf_mun["CD_MUN"] = gdf_mun["CD_MUN"].astype(str).str[:6]
    gdf_mun.set_index("CD_MUN", inplace=True)

    gdf_mun = gdf_mun.join(df_base[["TX_MAL_DEFINIDAS_P10K"]], how="left")
    gdf_mun["TX_MAL_DEFINIDAS_P10K"] = gdf_mun["TX_MAL_DEFINIDAS_P10K"].fillna(0)

    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    gdf_mun.plot(
        column="TX_MAL_DEFINIDAS_P10K",
        cmap="YlOrRd",
        linewidth=0.5,
        edgecolor="black",
        legend=True,
        legend_kwds={'label': "Óbitos por Causas Mal Definidas por 10 mil habitantes", 'shrink': 0.6},
        ax=ax
    )
    ax.set_title(f"Mapa de Óbitos por Causas Mal Definidas (por 10 mil hab.) - {UF_SIGLA} ({ANO})", fontsize=16)
    ax.axis("off")
    plt.tight_layout()

    output_filename = f"mapa_taxa_mal_definidas_{UF_SIGLA.lower()}_{ANO}.png"
    plt.savefig(output_filename, dpi=300)
    print(f"\nMapa salvo como '{output_filename}'")
    plt.show()
    return df_base

if __name__ == "__main__":
    df = calcular_indicador_causas_mal_definidas()
    print(df.head())
