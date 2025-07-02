# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from pysus.online_data.CNES import CNES  # Importa a classe CNES

def calcular_medicos_por_mil_habitantes():
    print("Iniciando o processo de cálculo do indicador: Médicos por 1.000 Habitantes...")

    # --- PARÂMETROS GERAIS ---
    UF_SIGLA = 'TO'
    ANO = 2022
    MES = 12  # Mês de referência: dezembro
    GRUPO_CNES = 'PF'  # Profissionais
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

    # --- PASSO 1: DADOS CNES-PF ---
    print(f"Passo 1/5: Obtendo dados do CNES para o grupo {GRUPO_CNES} (Profissionais)...")
    try:
        cnes_db = CNES()
        files = cnes_db.get_files(group=GRUPO_CNES, uf=UF_SIGLA, year=ANO, month=MES)

        if not files:
            print(f"⚠️ Nenhum arquivo encontrado para {UF_SIGLA} em {MES}/{ANO}.")
            return

        print(f"Arquivo encontrado: {files[0].name}. Baixando e convertendo para DataFrame...")
        parquet_set = cnes_db.download(files)
        df_cnes = parquet_set.to_dataframe()

        print(f"Dados CNES-PF carregados: {df_cnes.shape[0]} registros de profissionais.")
        print("Colunas disponíveis:", df_cnes.columns.tolist())
    except Exception as e:
        print(f"Ocorreu um erro ao baixar os dados do CNES: {e}")
        return

    # --- PASSO 2: FILTRAGEM DE MÉDICOS ---
    print("Passo 2/5: Filtrando e contabilizando médicos únicos por município...")

    if 'CBO' not in df_cnes.columns:
        print("⚠️ Coluna 'CBO' não encontrada no DataFrame.")
        return

    df_medicos = df_cnes[df_cnes['CBO'].astype(str).str.startswith('225')].copy()
    print(f"Total de registros de médicos (vínculos): {df_medicos.shape[0]}")

    medicos_por_municipio = df_medicos.groupby('CODUFMUN').agg(
        n_medicos=('CPFUNICO', 'nunique')
    )
    print(f"Total de médicos únicos no estado: {medicos_por_municipio['n_medicos'].sum()}\n")

    # --- PASSO 3: JUNÇÃO COM POPULAÇÃO ---
    print("Passo 3/5: Padronizando códigos municipais e unindo dados...")
    medicos_por_municipio.index = medicos_por_municipio.index.astype(str)
    df_base = df_base.join(medicos_por_municipio, how='left')
    df_base['n_medicos'] = df_base['n_medicos'].fillna(0).astype(int)

    # --- PASSO 4: CÁLCULO DO INDICADOR ---
    print("Passo 4/5: Calculando a Taxa de Médicos por 1.000 Habitantes...")
    df_base['TAXA_MEDICOS'] = df_base.apply(
        lambda row: (row['n_medicos'] / row['populacao']) * 1000 if row['populacao'] > 0 else 0,
        axis=1
    )

    print("✅ Indicador calculado com sucesso.")
    print("\nTop 10 municípios por Taxa de Médicos por 1.000 Habitantes:")
    print(df_base[['n_medicos', 'populacao', 'TAXA_MEDICOS']].sort_values(by='TAXA_MEDICOS', ascending=False).head(10).round(2))

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

    gdf_mun = gdf_mun.join(df_base[["TAXA_MEDICOS"]], how="left")
    gdf_mun["TAXA_MEDICOS"] = gdf_mun["TAXA_MEDICOS"].fillna(0)

    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    gdf_mun.plot(
        column="TAXA_MEDICOS",
        cmap="plasma",
        linewidth=0.5,
        edgecolor="black",
        legend=True,
        legend_kwds={'label': "Médicos por 1.000 Habitantes", 'shrink': 0.6},
        ax=ax
    )
    ax.set_title(f"Mapa de Médicos por 1.000 Habitantes - {UF_SIGLA} ({MES}/{ANO})", fontsize=16)
    ax.axis("off")
    plt.tight_layout()

    output_filename = f"mapa_taxa_medicos_{UF_SIGLA.lower()}_{ANO}.png"
    plt.savefig(output_filename, dpi=300)
    print(f"\nMapa salvo como '{output_filename}'")
    plt.show()
    return df_base

if __name__ == "__main__":
    df = calcular_medicos_por_mil_habitantes()
    print(df.head())
