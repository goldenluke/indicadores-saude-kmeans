# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from pysus.online_data.CNES import CNES
from utils.mapas import gerar_mapa_indicador
import argparse

def calcular_medicos_por_mil(ufs=['TO'], anos=[2022], meses=None,
                             arquivo_populacao="populacao_brasil_censo_2022_com_estado.csv"):
    """
    Calcula a taxa de médicos por 1.000 habitantes para múltiplas UFs, anos e meses,
    gerando também mapas por UF/ano/mês.

    Parâmetros:
    - ufs (list): Lista de siglas de UFs (ex: ['TO', 'MG'])
    - anos (list): Lista de anos (ex: [2021, 2022])
    - meses (list): Lista de meses (1–12). Se None ou vazio, usa ano inteiro.
    - arquivo_populacao (str): Caminho para o CSV com população municipal

    Retorna:
    - DataFrame com colunas: [
        'UF','ANO','MES','cod_mun_ibge_6','municipio','populacao',
        'n_medicos','TAXA_MEDICOS'
      ]
    """
    resultados = []
    cnes_db = CNES()
    cnes_db.load()

    processar_por_mes = bool(meses) and len(meses) > 0

    for uf in ufs:
        for ano in anos:
            meses_iterar = meses if processar_por_mes else [None]

            for mes in meses_iterar:
                if mes is None:
                    print(f"\n=== Processando {uf} / {ano} (ano inteiro) ===")
                    meses_validos = list(range(1, 13))
                else:
                    print(f"\n=== Processando {uf} / {ano} (mês {mes}) ===")
                    meses_validos = [mes]

                dfs_cnes_mes = []

                for m in meses_validos:
                    try:
                        files = cnes_db.get_files(group='PF', uf=uf, year=ano, month=m)
                        if not files:
                            print(f"⚠️ Nenhum arquivo CNES encontrado para {uf}/{ano}/{m:02d}")
                            continue
                        df_mes = cnes_db.download(files).to_dataframe()
                        dfs_cnes_mes.append(df_mes)
                    except Exception as e:
                        print(f"⚠️ Erro CNES {uf}/{ano}/{m}: {e}")
                        continue

                if not dfs_cnes_mes:
                    continue

                df_cnes = pd.concat(dfs_cnes_mes, ignore_index=True)

                # Carrega população e filtra UF
                try:
                    if isinstance(arquivo_populacao, str):
                        df_pop = pd.read_csv(arquivo_populacao, sep=';', dtype={'cod_mun_ibge_6': str})
                        df_pop_ano = df_pop[df_pop['UF'] == uf].copy()
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

                if 'CBO' not in df_cnes.columns or 'CPFUNICO' not in df_cnes.columns:
                    print("⚠️ Colunas CBO ou CPFUNICO ausentes.")
                    continue

                # filtra médicos (CBO 225)
                df_med = df_cnes[df_cnes['CBO'].astype(str).str.startswith('225')]
                contagem = (
                    df_med.groupby('CODUFMUN')['CPFUNICO']
                    .nunique()
                    .rename('n_medicos')
                )
                contagem.index = contagem.index.astype(str)

                df = (
                    df_base
                    .join(contagem, how='left')
                    .fillna({'n_medicos': 0})
                )
                df['n_medicos'] = df['n_medicos'].astype(int)
                df['TAXA_MEDICOS'] = df.apply(
                    lambda r: (r['n_medicos'] / r['populacao']) * 1000 if r['populacao'] > 0 else 0,
                    axis=1
                )

                df['UF'], df['ANO'] = uf, ano
                df['MES'] = mes if mes is not None else 0

                resultados.append(df.reset_index())

                try:
                    sufixo = f"_{mes:02d}" if mes is not None else "_ano_inteiro"
                    gerar_mapa_indicador(
                        df=df,
                        uf=uf,
                        ano=ano,
                        coluna_valor="TAXA_MEDICOS",
                        legenda="Médicos por 1.000 hab.",
                        cmap="Reds",
                        nome_arquivo=f"taxa_medicos_{uf}_{ano}{sufixo}",
                        title=f"{uf} – Médicos/1 000 hab. ({ano}{'' if mes is None else f'-{mes}'})"
                    )
                except Exception as e:
                    print(f"Erro ao gerar mapa para {uf}/{ano}{'' if mes is None else f'/{mes}'}: {e}")

    if resultados:
        df_final = pd.concat(resultados, ignore_index=True)
        print("\n✅ Médicos por mil calculado com sucesso.")
        return df_final
    else:
        print("⚠️ Nenhum dado processado.")
        return pd.DataFrame()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula a taxa de médicos por mil habitantes por UF, ano e meses.")
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs, ex: TO GO MG")
    parser.add_argument("--anos", nargs="+", type=int, default=[2021, 2022], help="Lista de anos")
    parser.add_argument("--meses", nargs="*", type=int, default=None, help="Lista de meses (1–12). Se não informado, agrega o ano inteiro")
    parser.add_argument("--pop", type=str, default="populacao_brasil_censo_2022_com_estado.csv", help="Arquivo CSV com população municipal")
    parser.add_argument("--saida", type=str, default="medicos_por_mil_multiplos_estados_anos.csv", help="Arquivo CSV de saída")

    args = parser.parse_args()

    df_med = calcular_medicos_por_mil(args.ufs, args.anos, args.meses, args.pop)

    if not df_med.empty:
        df_med.to_csv(args.saida, sep=';', index=False)
        print(f"\n📄 CSV salvo: '{args.saida}'")
    else:
        print("⚠️ Nenhum resultado para salvar.")
