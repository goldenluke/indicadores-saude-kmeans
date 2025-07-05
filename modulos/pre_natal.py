# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from pysus.online_data.SINASC import download as download_sinasc
from utils.mapas import gerar_mapa_indicador
import argparse

def calcular_cobertura_prenatal_multiplos_uf_anos(
    ufs=['TO'], anos=[2022],
    arquivo_populacao="populacao_brasil_censo_2022_com_estado.csv"
):
    """
    Calcula a cobertura de pré-natal adequado (7+ consultas) para várias UFs e anos,
    gerando também mapas por UF/ano.

    Parâmetros:
    - ufs (list): Lista de siglas de UFs, ex: ['TO','MG']
    - anos (list): Lista de anos, ex: [2021,2022]
    - arquivo_populacao (str ou dict ou pd.DataFrame): CSV ou dict ano->CSV ou DataFrame já carregado.

    Retorna:
    - DataFrame com colunas:
      ['UF','ANO','cod_mun_ibge_6','municipio','populacao',
       'total_nascimentos','prenatal_7mais','COBERTURA_PRENATAL']
    """
    resultados = []

    for uf in ufs:
        for ano in anos:
            print(f"\n=== Cobertura Pré-Natal: {uf}/{ano} ===")
            # 0: carregar população
            try:
                if isinstance(arquivo_populacao, str):
                    df_pop = pd.read_csv(arquivo_populacao, sep=';', dtype={'cod_mun_ibge_6': str})
                    df_pop_ano = df_pop[df_pop['UF'] == uf].copy()  # Ajuste aqui se quiser filtrar ano
                elif isinstance(arquivo_populacao, dict):
                    df_pop_ano = pd.read_csv(arquivo_populacao[ano], sep=';', dtype={'cod_mun_ibge_6': str})
                    df_pop_ano = df_pop_ano[df_pop_ano['UF'] == uf].copy()
                elif isinstance(arquivo_populacao, pd.DataFrame):
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

            # 1: baixar SINASC
            try:
                sin = download_sinasc(states=uf, years=ano, groups=["DN"])
                if isinstance(sin, list):
                    df_sin = pd.concat([f.to_dataframe() for f in sin], ignore_index=True)
                else:
                    df_sin = sin.to_dataframe()
            except Exception as e:
                print(f"Erro SINASC {uf}/{ano}: {e}")
                continue

            # 2: total nascimentos e pré-natal ≥7 (CONSULTAS=='4')
            tot = (
                df_sin.groupby("CODMUNRES")
                .size()
                .rename("total_nascimentos")
            )
            tot.index = tot.index.astype(str).str[:6]

            pr7 = (
                df_sin[df_sin['CONSULTAS'].astype(str)=='4']
                .groupby("CODMUNRES")
                .size()
                .rename("prenatal_7mais")
            )
            pr7.index = pr7.index.astype(str).str[:6]

            # 3: juntar e calcular
            df = (
                df_base.join(tot, how="left")
                       .join(pr7, how="left")
                       .fillna(0)
            )
            df['total_nascimentos']   = df['total_nascimentos'].astype(int)
            df['prenatal_7mais']      = df['prenatal_7mais'].astype(int)
            df['COBERTURA_PRENATAL']  = df.apply(
                lambda r: (r.prenatal_7mais/r.total_nascimentos*100)
                          if r.total_nascimentos>0 else 0,
                axis=1
            )
            df['UF'], df['ANO'] = uf, ano
            resultados.append(df.reset_index())

            # 4: gerar mapa
            gerar_mapa_indicador(
                df=df,  # DataFrame com índice 'cod_mun_ibge_6'
                uf=uf,
                ano=ano,
                coluna_valor="COBERTURA_PRENATAL",
                legenda="Cobertura de Pré-Natal Adequado (7+ consultas) (%)",
                cmap="Greens",
                nome_arquivo=f"cobertura_prenatal_{uf}_{ano}"
            )

    if resultados:
        df_final = pd.concat(resultados, ignore_index=True)
        print("\n✅ Cobertura de pré-natal calculada com sucesso para todos os estados/anos.")
        return df_final
    else:
        print("⚠️ Nenhum dado processado.")
        return pd.DataFrame()


if __name__ == "__main__":


    parser = argparse.ArgumentParser(description="Calcula cobertura de pré-natal adequado (7+ consultas).")
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs, ex: TO GO MG")
    parser.add_argument("--anos", nargs="+", type=int, default=[2021, 2022], help="Lista de anos")
    parser.add_argument("--pop", type=str, default="populacao_brasil_censo_2022_com_estado.csv", help="Arquivo de população")
    parser.add_argument("--saida", type=str, default="cobertura_prenatal_multiplos_estados_anos.csv", help="Arquivo de saída")

    args = parser.parse_args()

    df = calcular_cobertura_prenatal_multiplos_uf_anos(args.ufs, args.anos, args.pop)

    if not df.empty:
        df.to_csv(args.saida, sep=";", index=False)
        print(f"\n📄 CSV salvo: {args.saida}")
    else:
        print("⚠️ Nenhum dado processado.")

