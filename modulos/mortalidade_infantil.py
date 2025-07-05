# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from pysus.online_data.SIM import download as download_sim
from pysus.online_data.SINASC import download as download_sinasc
import geopandas as gpd
import matplotlib.pyplot as plt
from utils.mapas import gerar_mapa_indicador

def calcular_tmi_multiplos_uf_anos(ufs=['TO'], anos=[2022], arquivo_populacao="populacao_brasil_censo_2022_com_estado.csv"):
    """
    Calcula a Taxa de Mortalidade Infantil (TMI) para múltiplos estados e anos,
    gerando também mapas por UF/ano.

    Parâmetros:
    - ufs (list): Lista de siglas de UFs (ex: ['TO', 'MG'])
    - anos (list): Lista de anos (ex: [2021, 2022])
    - arquivo_populacao (str): Caminho para o CSV com população municipal

    Retorna:
    - DataFrame com colunas: ['UF','ANO','cod_mun_ibge_6','municipio','populacao','obitos_infantis','nascidos_vivos','TMI']
    """
    resultados = []
    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando {uf} / {ano} ===")

            # carrega população e filtra UF
            try:
                if isinstance(arquivo_populacao, str):
                    df_pop = pd.read_csv(arquivo_populacao, sep=';', dtype={'cod_mun_ibge_6': str})
                    # Remova o filtro por ano se seu CSV não tem essa coluna
                    df_pop_ano = df_pop[df_pop['UF'] == uf].copy()
                elif isinstance(arquivo_populacao, dict):
                    df_pop_ano = pd.read_csv(arquivo_populacao[ano], sep=';', dtype={'cod_mun_ibge_6': str})
                    df_pop_ano = df_pop_ano[df_pop_ano['UF'] == uf].copy()
                elif isinstance(arquivo_populacao, pd.DataFrame):
                    # Se sua DataFrame tem ANO, filtra, senão filtra só por UF
                    if 'ANO' in arquivo_populacao.columns:
                        df_pop_ano = arquivo_populacao[(arquivo_populacao['UF'] == uf) & (arquivo_populacao['ANO'] == ano)].copy()
                    else:
                        df_pop_ano = arquivo_populacao[arquivo_populacao['UF'] == uf].copy()
                else:
                    raise ValueError("Parâmetro 'arquivo_populacao' inválido")

                df_base = df_pop_ano.set_index('cod_mun_ibge_6')
            except Exception as e:
                print(f"Erro ao carregar população para {uf}/{ano}: {e}")
                continue

            # --- SIM: óbitos infantis ---
            try:
                sim_files = download_sim(states=uf, years=ano, groups=["CID10"])
                df_sim = sim_files.to_dataframe()
                df_sim["IDADE"] = pd.to_numeric(df_sim["IDADE"], errors="coerce")
                df_inf = df_sim[df_sim["IDADE"] < 401]
                obitos = df_inf.groupby("CODMUNRES").size().rename("obitos_infantis")
                obitos.index = obitos.index.astype(str).str[:6]
            except Exception as e:
                print(f"⚠️ Erro SIM {uf}/{ano}: {e}")
                obitos = pd.Series(dtype=int)

            # --- SINASC: nascidos vivos ---
            try:
                sinasc_files = download_sinasc(states=uf, years=ano, groups=["DN"])
                if isinstance(sinasc_files, list):
                    df_sin = pd.concat([f.to_dataframe() for f in sinasc_files], ignore_index=True)
                elif hasattr(sinasc_files, "to_dataframe"):
                    df_sin = sinasc_files.to_dataframe()
                else:
                    df_sin = pd.DataFrame(columns=["CODMUNRES"])
                nascidos = df_sin.groupby("CODMUNRES").size().rename("nascidos_vivos")
                nascidos.index = nascidos.index.astype(str).str[:6]
            except Exception as e:
                print(f"⚠️ Erro SINASC {uf}/{ano}: {e}")
                nascidos = pd.Series(dtype=int)

            # junta e calcula TMI
            df_base = df_base.join(obitos, how="left") \
                             .join(nascidos, how="left") \
                             .fillna(0)
            df_base['obitos_infantis'] = df_base['obitos_infantis'].astype(int)
            df_base['nascidos_vivos']   = df_base['nascidos_vivos'].astype(int)
            df_base['TMI'] = df_base.apply(
                lambda r: (r['obitos_infantis']/r['nascidos_vivos']*1000) if r['nascidos_vivos']>0 else 0,
                axis=1
            )

            df_base['UF']  = uf
            df_base['ANO'] = ano
            resultados.append(df_base.reset_index())

            # gera mapa
            gerar_mapa_indicador(
                df=df_base,
                uf=uf,
                ano=ano,
                coluna_valor="TMI",
                legenda="TMI (por mil nascidos vivos)",
                cmap="Reds",
                nome_arquivo="tmi"
            )

    if resultados:
        df_final = pd.concat(resultados, ignore_index=True)
        print("\n✅ TMI calculada para todos os estados/anos.")
        return df_final
    else:
        print("⚠️ Nenhum dado processado.")
        return pd.DataFrame()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Calcula a Taxa de Mortalidade Infantil (TMI) por UF e ano.")
    parser.add_argument("--ufs", nargs="+", default=["TO", "GO"], help="Lista de UFs, ex: TO GO MG")
    parser.add_argument("--anos", nargs="+", type=int, default=[2021, 2022], help="Lista de anos")
    parser.add_argument("--pop", type=str, default="populacao_brasil_censo_2022_com_estado.csv", help="Arquivo CSV com população municipal")
    parser.add_argument("--saida", type=str, default="tmi_multiplos_estados_anos.csv", help="Arquivo CSV de saída")

    args = parser.parse_args()

    df_tmi = calcular_tmi_multiplos_uf_anos(args.ufs, args.anos, args.pop)

    if not df_tmi.empty:
        df_tmi.to_csv(args.saida, index=False, sep=';')
        print(f"\n📄 CSV salvo: '{args.saida}'")
    else:
        print("⚠️ Nenhum resultado para salvar.")
