import geopandas as gpd
import matplotlib.pyplot as plt
import os

def gerar_mapa_indicador(
    df, uf: str, ano: int, coluna_valor: str,
    legenda: str, cmap: str, nome_arquivo: str,
    output_dir: str = "mapas",
    title: str = None,
    ativo=False):
    if not ativo:
        print("Geração de mapa desativada.")
        return
    """
    Gera e salva um mapa temático para o indicador desejado.

    Parâmetros:
    - df: DataFrame com os valores do indicador indexado por código de município (6 dígitos).
    - uf (str): Sigla da UF (ex: 'TO').
    - ano (int): Ano de referência.
    - coluna_valor (str): Nome da coluna com os valores a serem mapeados.
    - legenda (str): Legenda da barra de cores.
    - cmap (str): Colormap para o indicador (ex: 'Greens', 'Blues').
    - nome_arquivo (str): Nome base do arquivo a ser salvo.
    - output_dir (str): Diretório de saída.
    - title (str): Título do mapa (opcional). Se não fornecido, será gerado automaticamente.
    """
    try:
        # 1: carregar shapefile
        shp = "shapefiles/BR_Municipios_2022.shp"
        gdf = gpd.read_file(shp)
        gdf = gdf[gdf["SIGLA_UF"] == uf].copy()
        gdf["CD_MUN"] = gdf["CD_MUN"].astype(str).str[:6]

        # 2: juntar com dados
        gdf = (
            gdf.set_index("CD_MUN")
               .join(df[[coluna_valor]], how="left")
               .fillna({coluna_valor: 0})
        )

        # 3: criar mapa
        fig, ax = plt.subplots(figsize=(12, 10))
        gdf.plot(
            column=coluna_valor,
            cmap=cmap,
            linewidth=0.5,
            edgecolor="black",
            legend=True,
            legend_kwds={'label': legenda},
            ax=ax
        )

        # 4: título e layout
        if not title:
            title = f"{uf} – {legenda} ({ano})"
        ax.set_title(title, fontsize=14)
        ax.axis("off")
        plt.tight_layout()

        # 5: salvar arquivo
        os.makedirs(output_dir, exist_ok=True)
        fn = f"{output_dir}/mapa_{nome_arquivo}_{uf.lower()}_{ano}.png"
        plt.savefig(fn, dpi=300)
        plt.close(fig)
        print(f"🗺️ Mapa salvo: {fn}")

    except Exception as e:
        print(f"❌ Erro ao gerar mapa {uf}/{ano}: {e}")
