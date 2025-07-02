# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from pysus.online_data.SIH import SIH

def calcular_internacoes_cronicas_por_10mil():
    print("Iniciando o cálculo do indicador: Internações por Doenças Crônicas por 10 mil habitantes...\n")

    # --- PARÂMETROS GERAIS ---
    UF_SIGLA = 'TO'
    GRUPO_SIH = 'RD'  # AIH Reduzida
    ANO = 2022
    DOENCAS_CID10 = [
        "I10", "I11", "I12", "I13", "I15",  # Hipertensão
        "E10", "E11", "E12", "E13", "E14",  # Diabetes
        "J45", "J46"                        # Asma
    ]
    ARQUIVO_POPULACAO = "populacao_brasil_censo_2022_com_estado.csv"

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

    # --- PASSO 1: BAIXAR DADOS SIH ---
    print(f"Passo 1/5: Baixando dados do SIH (AIH Reduzida) para o ano {ANO}...")
    try:
        sih = SIH()
        sih.load()

        files = sih.get_files(group=GRUPO_SIH, uf=UF_SIGLA, year=ANO)

        if not files:
            print(f"⚠️ Nenhum arquivo SIH encontrado para {UF_SIGLA} no ano {ANO}.")
            return

        arquivos_ano = sorted(files, key=lambda f: f.name)
        print(f"✔️ {len(arquivos_ano)} arquivos encontrados para {ANO}.")

        # Baixar todos os arquivos e concatenar os DataFrames
        parquet_list = sih.download(arquivos_ano)
        df_list = [p.to_dataframe() for p in parquet_list]
        df_sih = pd.concat(df_list, ignore_index=True)

        print(f"✔️ Dados carregados: {df_sih.shape[0]} registros de internações.\n")
    except Exception as e:
        print(f"Erro ao baixar dados do SIH: {e}")
        return

    # --- PASSO 2: FILTRAR INTERNAÇÕES POR DOENÇAS CRÔNICAS ---
    print("Passo 2/5: Filtrando internações por doenças crônicas (CID-10)...")
    if "DIAG_PRINC" not in df_sih.columns:
        print("⚠️ Coluna 'DIAG_PRINC' não encontrada.")
        return

    df_cronicas = df_sih[df_sih["DIAG_PRINC"].astype(str).str[:3].isin([cid[:3] for cid in DOENCAS_CID10])].copy()
    print(f"✔️ Total de internações por doenças crônicas: {df_cronicas.shape[0]}\n")

    # --- PASSO 3: AGRUPAR POR MUNICÍPIO ---
    print("Passo 3/5: Agrupando por município de residência...")
    df_cronicas["MUNIC_RES"] = df_cronicas["MUNIC_RES"].astype(str).str.zfill(6)
    internacoes_por_mun = df_cronicas.groupby("MUNIC_RES").size().to_frame("n_internacoes")

    # --- PASSO 4: UNIR COM POPULAÇÃO E CALCULAR INDICADOR ---
    print("Passo 4/5: Unindo com dados populacionais e calculando indicador...\n")
    df_base = df_base.join(internacoes_por_mun, how="left")
    df_base["n_internacoes"] = df_base["n_internacoes"].fillna(0).astype(int)

    df_base["DOENCAS_CRONICAS"] = df_base.apply(
        lambda row: (row["n_internacoes"] / row["populacao"]) * 10000 if row["populacao"] > 0 else 0,
        axis=1
    )

    print("✅ Indicador calculado com sucesso.")
    print("\nTop 10 municípios por internações por 10 mil habitantes:")
    print(df_base[["n_internacoes", "populacao", "DOENCAS_CRONICAS"]]
          .sort_values(by="DOENCAS_CRONICAS", ascending=False)
          .head(10)
          .round(2))

    # --- PASSO 5: VISUALIZAÇÃO (MAPA) ---
    print("\nPasso 5/5: Carregando shapefile e gerando o mapa...")
    try:
        shapefile_path = "shapefiles/BR_Municipios_2022.shp"
        gdf_mun = gpd.read_file(shapefile_path)
    except Exception as e:
        print(f"⚠️ Erro ao carregar shapefile: {e}")
        return

    gdf_mun = gdf_mun[gdf_mun["SIGLA_UF"] == UF_SIGLA].copy()
    gdf_mun["CD_MUN"] = gdf_mun["CD_MUN"].astype(str).str[:6]
    gdf_mun.set_index("CD_MUN", inplace=True)

    gdf_mun = gdf_mun.join(df_base[["DOENCAS_CRONICAS"]], how="left")
    gdf_mun["DOENCAS_CRONICAS"] = gdf_mun["DOENCAS_CRONICAS"].fillna(0)

    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    gdf_mun.plot(
        column="DOENCAS_CRONICAS",
        cmap="OrRd",
        linewidth=0.5,
        edgecolor="black",
        legend=True,
        legend_kwds={'label': "Internações por Doenças Crônicas por 10 mil Habitantes", 'shrink': 0.6},
        ax=ax
    )
    ax.set_title(f"Mapa de Internações por Doenças Crônicas por 10 mil Habitantes - {UF_SIGLA} ({ANO})", fontsize=16)
    ax.axis("off")
    plt.tight_layout()

    output_filename = f"mapa_internacoes_cronicas_{UF_SIGLA.lower()}_{ANO}.png"
    plt.savefig(output_filename, dpi=300)
    print(f"\n🗺️ Mapa salvo como '{output_filename}'")
    plt.show()
    return df_base

if __name__ == "__main__":
    df = calcular_internacoes_cronicas_por_10mil()
    print(df.head())
