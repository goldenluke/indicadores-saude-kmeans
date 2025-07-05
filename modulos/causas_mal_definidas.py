# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from pysus.online_data.SIM import download as download_sim
from utils.mapas import gerar_mapa_indicador

def calcular_causas_mal_definidas(ufs=['TO'], anos=[2022], arquivo_populacao="populacao_brasil_censo_2022_com_estado.csv"):
    """
    Calcula proporção e taxa de óbitos por causas mal definidas para múltiplas UFs e anos,
    gerando mapas e retornando um DataFrame com os resultados.

    Parâmetros:
    - ufs (list): siglas de estados, ex: ['TO', 'MA']
    - anos (list): anos, ex: [2021, 2022]
    - arquivo_populacao (str): caminho para CSV com população municipal

    Retorna:
    - DataFrame com colunas ['UF','ANO','cod_mun_ibge_6','municipio','populacao',
      'total_obitos','obitos_mal_definidas','PROP_MAL_DEFINIDAS','TX_MAL_DEFINIDAS_P10K']
    """
    resultados = []

    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando {uf}/{ano} ===")

                # --- Carrega população ---
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


            # --- Baixa SIM ---
            try:
                sim = download_sim(states=uf, years=ano, groups=["CID10"])
                df_sim = sim.to_dataframe()
            except Exception as e:
                print(f"Erro ao baixar SIM: {e}")
                continue

            # total de óbitos
            total = df_sim.groupby("CODMUNRES").size().rename("total_obitos")
            total.index = total.index.astype(str).str[:6]

            # óbitos por causas mal definidas (CID R00–R99)
            mal = df_sim[df_sim['CAUSABAS'].astype(str).str.startswith('R')]
            mal_def = mal.groupby("CODMUNRES").size().rename("obitos_mal_definidas")
            mal_def.index = mal_def.index.astype(str).str[:6]

            # --- Junta e calcula indicadores ---
            df = df_base.join(total, how="left") \
                        .join(mal_def, how="left") \
                        .fillna(0)
            df['total_obitos']          = df['total_obitos'].astype(int)
            df['obitos_mal_definidas']  = df['obitos_mal_definidas'].astype(int)
            df['PROP_MAL_DEFINIDAS']    = df.apply(
                lambda r: (r.obitos_mal_definidas/r.total_obitos*100)
                          if r.total_obitos>0 else 0, axis=1)
            df['TX_MAL_DEFINIDAS_P10K'] = df.apply(
                lambda r: (r.obitos_mal_definidas/r.populacao*10000)
                          if r.populacao>0 else 0, axis=1)

            df['UF'], df['ANO'] = uf, ano
            resultados.append(df.reset_index())


            gerar_mapa_indicador(
                df=df,
                uf=uf,
                ano=ano,
                coluna_valor="TX_MAL_DEFINIDAS_P10K",
                legenda="Óbitos causas mal definidas por 10 000 hab.",
                cmap="YlOrRd",
                nome_arquivo="mal_definidas",
                title=f"{uf} – Mal Definidas ({ano})"
            )


    if resultados:
        return pd.concat(resultados, ignore_index=True)
    else:
        print("⚠️ Nenhum dado processado.")
        return pd.DataFrame()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Calcula óbitos por causas mal definidas para múltiplos estados e anos.")
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs, ex: TO PA MG")
    parser.add_argument("--anos", nargs="+", type=int, default=[2021, 2022], help="Lista de anos")
    parser.add_argument("--pop", type=str, default="populacao_brasil_censo_2022_com_estado.csv", help="Arquivo CSV com dados populacionais")
    parser.add_argument("--saida", type=str, default="causas_mal_definidas_multiplos_estados_anos.csv", help="Arquivo CSV de saída")

    args = parser.parse_args()

    df = calcular_causas_mal_definidas(args.ufs, args.anos, args.pop)
    if not df.empty:
        df.to_csv(args.saida, index=False, sep=';')
        print(f"\n📄 CSV salvo: '{args.saida}'")
    else:
        print("⚠️ Nenhum resultado para salvar.")

