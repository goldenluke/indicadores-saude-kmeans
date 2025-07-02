# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from pysus.online_data.SINAN import SINAN

def calcular_taxa_notificacao_dengue():
    print("Iniciando o processo de cálculo do indicador: Taxa de Notificação de Dengue...")

    # --- PARÂMETROS ---
    UF_SIGLA = 'TO'
    ANO = 2022
    DOENCA_COD = 'DENG'
    UF_CODIGO = {'TO': '17'}

    # --- PASSO 0: MUNICÍPIOS E POPULAÇÃO ---
    print("\nPasso 0/5: Carregando base local com população e municípios...")
    try:
        arquivo_populacao = "populacao_tocantins_2022.csv"
        df_base = pd.read_csv(arquivo_populacao, sep=';', dtype={'cod_mun_ibge_6': str, 'cod_mun_ibge_7': str})
        df_base.set_index('cod_mun_ibge_6', inplace=True)
        print(f"Base local carregada com {df_base.shape[0]} municípios.\n")
    except Exception as e:
        print(f"Erro carregando a base populacional: {e}")
        return

    # --- PASSO 1: DADOS SINAN ---
    print(f"Passo 1/5: Obtendo dados do SINAN para {DOENCA_COD} ({ANO})...")
    try:
        sinan = SINAN().load()
        arquivos = sinan.get_files(dis_code=DOENCA_COD, year=ANO)
        if not arquivos:
            print(f"Nenhum arquivo encontrado para {DOENCA_COD} em {ANO}.")
            return
        arquivo = arquivos[0]
        print(f"Baixando {arquivo.name}...")
        downloaded_parquets = sinan.download(arquivo)

        # --- LEITURA DO DATAFRAME ---
        print("Convertendo para DataFrame...")
        if isinstance(downloaded_parquets, list):
            df_list = [p.to_dataframe() for p in downloaded_parquets]
            df_sinan = pd.concat(df_list, ignore_index=True)
        elif hasattr(downloaded_parquets, "_parquets"):
            df_list = [p.to_dataframe() for p in downloaded_parquets._parquets]
            df_sinan = pd.concat(df_list, ignore_index=True)
        else:
            df_sinan = downloaded_parquets.to_dataframe()

        print(f"Total de registros brutos: {df_sinan.shape[0]}")
        print("Filtrando apenas municípios do Tocantins (códigos iniciando por 17)...")
        df_sinan = df_sinan[df_sinan['ID_MUNICIP'].astype(str).str.startswith(UF_CODIGO[UF_SIGLA])]
        print(f"Registros filtrados: {df_sinan.shape[0]}")
    except Exception as e:
        print(f"Erro durante o carregamento do SINAN: {e}")
        return

    # --- PASSO 2: CONTAGEM DE CASOS ---
    print("\nPasso 2/5: Contabilizando casos de Dengue por município...")
    casos_dengue = df_sinan.groupby("ID_MUNICIP").size().rename("casos_dengue")
    print(f"Total de casos no estado: {casos_dengue.sum()}\n")

    # --- PASSO 3: UNINDO COM POPULAÇÃO ---
    print("Passo 3/5: Padronizando códigos e unindo bases...")
    casos_dengue.index = casos_dengue.index.astype(str).str[:6]
    df_base = df_base.join(casos_dengue, how='left')
    df_base['casos_dengue'] = df_base['casos_dengue'].fillna(0).astype(int)

    # --- PASSO 4: TAXA POR 100 MIL HABITANTES ---
    print("\nPasso 4/5: Calculando Taxa de Notificação por 100.000 habitantes...")
    df_base['TAXA_DENGUE'] = df_base.apply(
        lambda row: (row['casos_dengue'] / row['populacao_2022']) * 100000 if row['populacao_2022'] > 0 else 0,
        axis=1
    )
    print("✅ Cálculo concluído.")
    print(df_base[['casos_dengue', 'populacao_2022', 'TAXA_DENGUE']].sort_values(by='TAXA_DENGUE', ascending=False).head(10).round(2))

    # --- PASSO 5: MAPA ---
    print("\nPasso 5/5: Gerando mapa de calor da taxa de notificação...")
    try:
        shapefile_path = "shapefiles/BR_Municipios_2022.shp"
        gdf_mun = gpd.read_file(shapefile_path)
    except Exception as e:
        print(f"Erro ao carregar shapefile: {e}")
        return

    gdf_mun = gdf_mun[gdf_mun["SIGLA_UF"] == UF_SIGLA].copy()
    gdf_mun["CD_MUN"] = gdf_mun["CD_MUN"].astype(str).str[:6]
    gdf_mun.set_index("CD_MUN", inplace=True)
    gdf_mun = gdf_mun.join(df_base[["TAXA_DENGUE"]], how="left")
    gdf_mun["TAXA_DENGUE"] = gdf_mun["TAXA_DENGUE"].fillna(0)

    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    gdf_mun.plot(
        column="TAXA_DENGUE", cmap="Reds", linewidth=0.5, edgecolor="black", legend=True,
        legend_kwds={'label': "Taxa de Notificação de Dengue (por 100.000 hab.)", 'shrink': 0.6},
        ax=ax, scheme='quantiles', k=5
    )
    ax.set_title(f"Mapa da Taxa de Notificação de Dengue - {UF_SIGLA} ({ANO})", fontsize=16)
    ax.axis("off")
    plt.tight_layout()

    output_filename = f"mapa_taxa_dengue_{UF_SIGLA.lower()}_{ANO}.png"
    plt.savefig(output_filename, dpi=300)
    print(f"\n🗺️ Mapa salvo como '{output_filename}'")
    plt.show()

if __name__ == "__main__":
    calcular_taxa_notificacao_dengue()
