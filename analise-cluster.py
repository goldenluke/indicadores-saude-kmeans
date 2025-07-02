# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# --- PASSO 1: CARREGAR E PREPARAR OS DADOS ---
print("--- PASSO 1: Carregando e preparando os dados ---")
df = pd.read_csv('indicadores_integrados_tocantins_2022.csv', sep=';')
indicadores = [
    'TMI', 'COBERTURA_PRENATAL', 'TAXA_MEDICOS',
    'PROP_CESAREOS', 'PROP_MAL_DEFINIDAS', 'DOENCAS_CRONICAS'
]
df_indicadores = df[indicadores]
UF_SIGLA = 'TO'

# --- PASSO 1.5: GERAR O GRÁFICO DE CORRELAÇÃO ---
print("\n--- PASSO 1.5: Gerando o Mapa de Calor das Correlações ---")
try:
    correlation_matrix = df_indicadores.corr()
    plt.figure(figsize=(12, 10))
    sns.heatmap(
        correlation_matrix,
        annot=True,
        cmap='coolwarm',
        fmt=".2f",
        linewidths=.5
    )
    plt.title(f'Mapa de Calor da Correlação entre Indicadores - {UF_SIGLA}', fontsize=16)
    plt.savefig("grafico_correlacao.png", dpi=300, bbox_inches='tight')
    print("✔️ Gráfico de correlação salvo como 'grafico_correlacao.png'")
    plt.show()
except Exception as e:
    print(f"⚠️ Erro ao gerar o gráfico de correlação: {e}")

# --- PASSO 2: PADRONIZAR DADOS ---
print("\n--- PASSO 2: Padronizando os dados para o modelo K-Means ---")
scaler = StandardScaler()
dados_escalados = scaler.fit_transform(df_indicadores)
df_escalado = pd.DataFrame(dados_escalados, columns=indicadores)

# --- PASSO 2.5: ELBOW METHOD ---
print("\n--- PASSO 2.5: Gerando o Gráfico do Elbow Method ---")
try:
    distortions = []
    k_range = range(1, 11)
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(dados_escalados)
        distortions.append(kmeans.inertia_)

    plt.figure(figsize=(10, 6))
    plt.plot(k_range, distortions, marker='o', linestyle='--')
    plt.title('Método do Cotovelo (Elbow Method)', fontsize=16)
    plt.xlabel('Número de Clusters (K)')
    plt.ylabel('Inércia (Distância Total Intra-cluster)')
    plt.xticks(k_range)
    plt.grid(True, linestyle='--')
    plt.savefig("kmeans_elbow_method.png", dpi=300, bbox_inches='tight')
    print("✔️ Gráfico do Elbow Method salvo como 'kmeans_elbow_method.png'")
    plt.show()
except Exception as e:
    print(f"⚠️ Erro ao gerar o Elbow Method: {e}")

# --- PASSO 3: APLICAR K-MEANS ---
print("\n--- PASSO 3: Aplicando K-Means para K=3 e K=4 ---")
kmeans_k3 = KMeans(n_clusters=3, random_state=42, n_init=10)
df_escalado['cluster_k3'] = kmeans_k3.fit_predict(dados_escalados)

kmeans_k4 = KMeans(n_clusters=4, random_state=42, n_init=10)
df_escalado['cluster_k4'] = kmeans_k4.fit_predict(dados_escalados)

# --- PASSO 4: SNAKE PLOTS ---
print("\n--- PASSO 4: Gerando 'Snake Plots' para comparar os perfis ---")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7), sharey=True)

perfil_k3 = df_escalado.groupby('cluster_k3').mean()
for i in perfil_k3.index:
    ax1.plot(perfil_k3.columns, perfil_k3.loc[i], marker='o', label=f'Cluster {i}')
ax1.set_title('Perfil dos Clusters com K=3', fontsize=16)
ax1.set_ylabel('Valor Padronizado (Z-score)')
ax1.tick_params(axis='x', rotation=45)
ax1.legend()
ax1.grid(True, linestyle='--')

perfil_k4 = df_escalado.groupby('cluster_k4').mean()
for i in perfil_k4.index:
    ax2.plot(perfil_k4.columns, perfil_k4.loc[i], marker='o', label=f'Cluster {i}')
ax2.set_title('Perfil dos Clusters com K=4', fontsize=16)
ax2.tick_params(axis='x', rotation=45)
ax2.legend()
ax2.grid(True, linestyle='--')

plt.suptitle('Comparação dos Perfis de Cluster (Snake Plot)', fontsize=20)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.savefig("kmeans_snake_plot_k3_vs_k4.png", dpi=300)
plt.show()

# --- PASSO 5: MAPAS ---
print("\n--- PASSO 5: Tentando gerar os mapas de clusters ---")
try:
    shapefile_path = "shapefiles/BR_Municipios_2022.shp"
    gdf_mun = gpd.read_file(shapefile_path)
    gdf_mun = gdf_mun[gdf_mun["SIGLA_UF"] == UF_SIGLA].copy()
    gdf_mun["CD_MUN"] = gdf_mun["CD_MUN"].astype(str).str[:6]

    df['cluster_k3'] = df_escalado['cluster_k3']
    df['cluster_k4'] = df_escalado['cluster_k4']

    df_mapa = df[['cod_mun_ibge_6', 'cluster_k3', 'cluster_k4']].copy()
    df_mapa['cod_mun_ibge_6'] = df_mapa['cod_mun_ibge_6'].astype(str)
    gdf_final = gdf_mun.merge(df_mapa, left_on='CD_MUN', right_on='cod_mun_ibge_6')

    fig_map, (ax_map1, ax_map2) = plt.subplots(1, 2, figsize=(20, 10))

    gdf_final.plot(column="cluster_k3", cmap="Accent", categorical=True, linewidth=0.5, edgecolor="black", legend=True, ax=ax_map1)
    ax_map1.set_title('Mapa de Clusters com K=3', fontsize=16)
    ax_map1.axis("off")

    gdf_final.plot(column="cluster_k4", cmap="viridis", categorical=True, linewidth=0.5, edgecolor="black", legend=True, ax=ax_map2)
    ax_map2.set_title('Mapa de Clusters com K=4', fontsize=16)
    ax_map2.axis("off")

    plt.suptitle('Comparação dos Mapas de Cluster', fontsize=20)
    plt.savefig("kmeans_maps_k3_vs_k4.png", dpi=300)
    plt.show()
except FileNotFoundError:
    print("⚠️ Shapefile não encontrado. Os mapas não serão gerados.")
