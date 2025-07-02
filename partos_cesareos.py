# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from pysus.online_data.SINASC import download as download_sinasc

def calcular_proporcao_partos_cesareos():
    """
    Script completo para baixar dados de nascidos vivos, calcular e visualizar
    a Proporção de Partos Cesáreos para o Tocantins em 2022.
    """
    print("Iniciando o processo de cálculo do indicador: Proporção de Partos Cesáreos...")

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

    # --- PASSO 1: OBTENÇÃO DOS DADOS DE NASCIDOS VIVOS (SINASC) ---
    print("Passo 1/5: Obtendo dados SINASC (nascidos vivos)...")
    sinasc_files = download_sinasc(states=UF_SIGLA, years=ANO, groups=["DN"])

    # Tratamento robusto da saída do PySUS (pode ser lista ou objeto único)
    if isinstance(sinasc_files, list) and len(sinasc_files) > 0:
        print(f"SINASC retornou {len(sinasc_files)} arquivos. Concatenando em um DataFrame...")
        df_list = [f.to_dataframe() for f in sinasc_files]
        df_sinasc = pd.concat(df_list, ignore_index=True)
    elif hasattr(sinasc_files, "to_dataframe"):
        print("SINASC retornou um único arquivo. Convertendo para DataFrame...")
        df_sinasc = sinasc_files.to_dataframe()
    else:
        print(f"⚠️ Nenhum dado do SINASC retornado para {UF_SIGLA}/{ANO}.")
        return

    print(f"Dados SINASC carregados: {df_sinasc.shape[0]} linhas totais de nascidos vivos.")

    # --- PASSO 2: CONTABILIZANDO NASCIMENTOS TOTAIS E CESÁREOS ---
    print("Passo 2/5: Contabilizando nascimentos totais e partos cesáreos...")

    # DENOMINADOR: Total de nascidos vivos por município de residência
    total_nascimentos = df_sinasc.groupby("CODMUNRES").size().rename("total_nascimentos")
    print(f"Total de nascidos vivos no estado: {total_nascimentos.sum()}")

    # NUMERADOR: Nascidos vivos de parto cesáreo (TIPOPARTO = 2)
    # É mais seguro comparar com string '2', pois a coluna pode ser carregada como objeto.
    df_cesareos = df_sinasc[df_sinasc['PARTO'] == '2'].copy()
    partos_cesareos = df_cesareos.groupby("CODMUNRES").size().rename("partos_cesareos")
    print(f"Total de partos cesáreos: {partos_cesareos.sum()}\n")

    # --- PASSO 3: PADRONIZAR CHAVES E JUNTAR BASES ---
    print("Passo 3/5: Padronizando códigos municipais e unindo dados...")

    # Padronizar índices para 6 dígitos string
    total_nascimentos.index = total_nascimentos.index.astype(str).str[:6]
    partos_cesareos.index = partos_cesareos.index.astype(str).str[:6]

    # Juntar na base local
    df_base = df_base.join(total_nascimentos, how='left')
    df_base = df_base.join(partos_cesareos, how='left')

    # Tratar NaNs, garantindo que municípios sem registros sejam 0
    df_base['total_nascimentos'] = df_base['total_nascimentos'].fillna(0).astype(int)
    df_base['partos_cesareos'] = df_base['partos_cesareos'].fillna(0).astype(int)

    # --- PASSO 4: CÁLCULO DO INDICADOR ---
    print("Passo 4/5: Calculando a Proporção de Partos Cesáreos...")

    df_base['PROP_CESAREOS'] = df_base.apply(
        lambda row: (row['partos_cesareos'] / row['total_nascimentos']) * 100 if row['total_nascimentos'] > 0 else 0,
        axis=1
    )

    print("✅ Indicador calculado com sucesso.\n")
    print("Top 10 municípios por Proporção de Partos Cesáreos (%):")
    print(df_base[['total_nascimentos', 'partos_cesareos', 'PROP_CESAREOS']].sort_values(by='PROP_CESAREOS', ascending=False).head(10).round(2))

    # --- PASSO 5: VISUALIZAÇÃO - MAPA DE CALOR ---
    print("\nPasso 5/5: Carregando shapefile e gerando o mapa...")
    try:
        shapefile_path = "shapefiles/BR_Municipios_2022.shp"
        gdf_mun = gpd.read_file(shapefile_path)
    except Exception as e:
        print(f"⚠️ Não foi possível carregar o shapefile de '{shapefile_path}'. Verifique o caminho. Erro: {e}")
        return

    # Filtra apenas os municípios do Tocantins e prepara para o join
    gdf_mun = gdf_mun[gdf_mun["SIGLA_UF"] == UF_SIGLA].copy()
    gdf_mun["CD_MUN"] = gdf_mun["CD_MUN"].astype(str).str[:6]
    gdf_mun.set_index("CD_MUN", inplace=True)

    # Faz o join com os dados do indicador
    gdf_mun = gdf_mun.join(df_base[["PROP_CESAREOS"]], how="left")
    gdf_mun["PROP_CESAREOS"] = gdf_mun["PROP_CESAREOS"].fillna(0) # Garante que não haja NaN no mapa

    # Plotagem do mapa
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    gdf_mun.plot(
        column="PROP_CESAREOS",
        cmap="Blues",  # Esquema de cor azul é comum para este tipo de indicador
        linewidth=0.5,
        edgecolor="black",
        legend=True,
        legend_kwds={'label': "Proporção de Partos Cesáreos (%)", 'shrink': 0.6},
        ax=ax
    )
    ax.set_title(f"Mapa de Proporção de Partos Cesáreos (%)- {UF_SIGLA} ({ANO})", fontsize=16)
    ax.axis("off")
    plt.tight_layout()

    output_filename = f"mapa_prop_cesareos_{UF_SIGLA.lower()}_{ANO}.png"
    plt.savefig(output_filename, dpi=300)
    print(f"\nMapa salvo como '{output_filename}'")
    plt.show()
    return df_base

if __name__ == "__main__":
    df = calcular_proporcao_partos_cesareos()
    print(df.head())
