# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from pysus.online_data.SINASC import download as download_sinasc
from utils.mapas import gerar_mapa_indicador
import argparse

def calcular_prop_partos_cesareos_multiplos_uf_anos(
    ufs=['TO'], anos=[2022],
    arquivo_populacao="populacao_brasil_censo_2022_com_estado.csv"
):
    """
    Calcula a proporção de partos cesáreos (%) para múltiplas UFs e anos,
    gerando também mapas por UF/ano.

    Parâmetros:
    - ufs (list): Lista de siglas de UFs (ex: ['TO', 'MG'])
    - anos (list): Lista de anos (ex: [2021, 2022])
    - arquivo_populacao (str): Caminho para o CSV com população municipal

    Retorna:
    - DataFrame com colunas:
      ['UF','ANO','cod_mun_ibge_6','municipio','populacao',
       'total_nascimentos','partos_cesareos','PROP_CESAREOS']
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

            # SINASC: nascidos vivos
            try:
                sinasc = download_sinasc(states=uf, years=ano, groups=["DN"])
                if isinstance(sinasc, list):
                    df_sin = pd.concat(
                        [f.to_dataframe() for f in sinasc], ignore_index=True
                    )
                else:
                    df_sin = sinasc.to_dataframe()
            except Exception as e:
                print(f"⚠️ Erro SINASC {uf}/{ano}: {e}")
                continue

            # total de nascimentos por município
            tot = (
                df_sin.groupby("CODMUNRES")
                .size()
                .rename("total_nascimentos")
            )
            tot.index = tot.index.astype(str).str[:6]

            # partos cesáreos: PARTO == '2'
            ces = (
                df_sin[df_sin['PARTO'].astype(str) == '2']
                .groupby("CODMUNRES")
                .size()
                .rename("partos_cesareos")
            )
            ces.index = ces.index.astype(str).str[:6]

            # junta e calcula proporção
            df = (
                df_base
                .join(tot, how="left")
                .join(ces, how="left")
                .fillna(0)
            )
            df['total_nascimentos'] = df['total_nascimentos'].astype(int)
            df['partos_cesareos']    = df['partos_cesareos'].astype(int)
            df['PROP_CESAREOS'] = df.apply(
                lambda r: (r.partos_cesareos / r.total_nascimentos * 100)
                          if r.total_nascimentos > 0 else 0,
                axis=1
            )

            df['UF'], df['ANO'] = uf, ano
            resultados.append(df.reset_index())

            # gera mapa
        gerar_mapa_indicador(
            df=df,
            uf=uf,
            ano=ano,
            coluna_valor='PROP_CESAREOS',
            legenda='Proporção de Partos Cesáreos (%)',
            cmap='Blues',
            nome_arquivo='prop_cesareos',
        )



    if resultados:
        df_final = pd.concat(resultados, ignore_index=True)
        print("\n✅ Proporção de cesáreos calculada para todos os estados/anos.")
        return df_final
    else:
        print("⚠️ Nenhum dado processado.")
        return pd.DataFrame()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Calcula a proporção de partos cesáreos por UF e ano.")
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs, ex: TO GO MG")
    parser.add_argument("--anos", nargs="+", type=int, default=[2021, 2022], help="Lista de anos")
    parser.add_argument("--pop", type=str, default="populacao_brasil_censo_2022_com_estado.csv", help="Arquivo CSV com população municipal")
    parser.add_argument("--saida", type=str, default="prop_cesareos_multiplos_estados_anos.csv", help="Arquivo CSV de saída")

    args = parser.parse_args()

    df_prop = calcular_prop_partos_cesareos_multiplos_uf_anos(args.ufs, args.anos, args.pop)

    if not df_prop.empty:
        df_prop.to_csv(args.saida, sep=';', index=False)
        print(f"\n📄 CSV salvo: '{args.saida}'")
    else:
        print("⚠️ Nenhum resultado para salvar.")

