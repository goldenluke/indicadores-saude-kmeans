# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from scipy.spatial.distance import euclidean
import os
import numpy as np
from pathlib import Path

def classificar_perfis_por_similaridade(perfil_df, arquétipos):
    """
    Classifica cada cluster encontrado medindo sua distância euclidiana
    para um conjunto de arquétipos pré-definidos.
    """
    mapeamento = {}
    for i, row in perfil_df.iterrows():
        distancias = {
            nome: euclidean(row.values, perfil)
            for nome, perfil in arquétipos.items()
        }
        perfil_mais_proximo = min(distancias, key=distancias.get)
        mapeamento[i] = perfil_mais_proximo
    return mapeamento

def gerar_mapa_perfis_de_saude(
    shapefile_path: str,
    df_analise: pd.DataFrame,
    uf_sigla: str,
    ano: int,
    cores_perfis: dict,
    output_path: str
):
    """
    Gera um mapa temático de perfis de saúde por município.

    Parâmetros:
    - shapefile_path: caminho para o shapefile dos municípios.
    - df_analise: DataFrame com colunas 'cod_mun_ibge_6', 'perfil' e 'cor'.
    - uf_sigla: sigla da UF (ex: 'TO').
    - ano: ano de referência (ex: 2022).
    - cores_perfis: dicionário {nome_perfil: cor_hexadecimal}.
    - output_path: caminho do arquivo de saída (PNG).
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    gdf_mun = gpd.read_file(shapefile_path)
    gdf_uf = gdf_mun[gdf_mun["SIGLA_UF"] == uf_sigla].copy()
    gdf_uf["CD_MUN"] = gdf_uf["CD_MUN"].astype(str).str[:6]

    df_mapa = df_analise[['cod_mun_ibge_6', 'cor', 'perfil']].copy()
    df_mapa['cod_mun_ibge_6'] = df_mapa['cod_mun_ibge_6'].astype(str)

    gdf_final = gdf_uf.merge(df_mapa, left_on='CD_MUN', right_on='cod_mun_ibge_6')

    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    gdf_final.plot(color=gdf_final['cor'], linewidth=0.5, edgecolor="black", ax=ax)

    perfis_presentes = sorted([p for p in gdf_final['perfil'].unique() if p in cores_perfis])
    patches = [mpatches.Patch(color=cores_perfis[label], label=label) for label in perfis_presentes]
    ax.legend(handles=patches, title="Perfis de Saúde", loc='upper right', fontsize=12)

    ax.set_title(f'Mapa de Perfis de Saúde - {uf_sigla} {ano}', fontsize=16)
    ax.axis("off")
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"✔️ Mapa de Perfis para {uf_sigla}/{ano} salvo.")


def analisar_clusters_com_arquétipos(df_painel):
    """
    Executa a análise de cluster e classifica os clusters por similaridade a arquétipos definidos.
    """
    output_dir = "resultados_analise_cluster"
    os.makedirs(output_dir, exist_ok=True)

    cores_perfis = {
        "Vulnerabilidade Crítica": "#d73027", "Sobrecarga Crônica": "#fc8d59",
        "Desafio na Cobertura da APS": "#4575b4", "Eficiência na APS": "#1a9850"
    }

    indicadores = ['TMI', 'COBERTURA_PRENATAL', 'TAXA_MEDICOS', 'PROP_CESAREOS', 'PROP_MAL_DEFINIDAS', 'DOENCAS_CRONICAS']

    # --- PASSO 1: DEFINIR OS ARQUÉTIPOS DE REFERÊNCIA ---
    arquétipos = {
        "Vulnerabilidade Crítica": np.array([2.0, -0.5, 0.0, 0.5, 1.0, 0.5]),
        "Sobrecarga Crônica":    np.array([-0.5, 0.0, 0.0, 0.0, 0.0, 2.0]),
        "Eficiência na APS":       np.array([-0.5, 1.0, 0.5, -0.5, -0.5, -0.5]),
        "Desafio na Cobertura da APS":  np.array([0.0, -1.0, -0.5, 0.0, 0.0, 0.0])
    }
    print("Arquétipos de saúde definidos.")

    # --- PASSO 2: LOOP DE ANÁLISE E CLASSIFICAÇÃO ---
    combinacoes = df_painel[['UF', 'ANO']].drop_duplicates()
    for index, row in combinacoes.iterrows():
        uf_sigla, ano = row['UF'], row['ANO']

        print(f"\n====================================================")
        print(f"📊 PROCESSANDO E CLASSIFICANDO: {uf_sigla} - {ano}")
        print(f"====================================================")

        df_analise = df_painel[(df_painel['UF'] == uf_sigla) & (df_painel['ANO'] == ano)].copy()
        if df_analise.empty: continue

        scaler = StandardScaler()
        dados_escalados = scaler.fit_transform(df_analise[indicadores])

        K_OTIMO = 4
        kmeans = KMeans(n_clusters=K_OTIMO, random_state=42, n_init=10).fit(dados_escalados)

        perfil_clusters_encontrados = pd.DataFrame(kmeans.cluster_centers_, columns=indicadores)
        mapeamento_nomes = classificar_perfis_por_similaridade(perfil_clusters_encontrados, arquétipos)

        df_analise['cluster_num'] = kmeans.labels_
        df_analise['perfil'] = df_analise['cluster_num'].map(mapeamento_nomes)
        df_analise['cor'] = df_analise['perfil'].map(cores_perfis)
        print(f" -> Mapeamento para {uf_sigla}/{ano}: {mapeamento_nomes}")

        # --- Visualização: Mapa de Perfis ---
        try:
            BASE_DIR = Path(__file__).resolve().parent.parent  # sobe 2 níveis (ajuste se precisar)
            shapefile_path = BASE_DIR / "shapefiles" / "BR_Municipios_2022.shp"
            output_file = Path(output_dir) / f"mapa_perfis_{uf_sigla.lower()}_{ano}.png"

            gerar_mapa_perfis_de_saude(
                shapefile_path=str(shapefile_path),
                df_analise=df_analise,
                uf_sigla=uf_sigla,
                ano=ano,
                cores_perfis=cores_perfis,
                output_path=str(output_file)
            )
        except Exception as e:
            print(f"⚠️ Erro ao gerar o mapa para {uf_sigla}/{ano}: {e}")



if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent.parent  # sobe 2 níveis (ajuste se precisar)
    arquivo_painel = BASE_DIR / "indicadores_integrados.csv"

    try:
        df_painel_completo = pd.read_csv(str(arquivo_painel), sep=';')
        analisar_clusters_com_arquétipos(df_painel_completo)
        print("\n✅ Análise de cluster concluída para todas as combinações de UF/Ano.")
    except FileNotFoundError:
        print(f"❌ ERRO: Arquivo de painel '{arquivo_painel}' não encontrado.")
