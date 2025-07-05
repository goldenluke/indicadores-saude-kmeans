# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from pysus.online_data.SIH import SIH
from utils.mapas import gerar_mapa_indicador
import argparse

def calcular_internacoes_cronicas_por_10mil(
    ufs=['TO'],
    anos=[2022],
    meses=None,  # pode ser None ou lista vazia
    arquivo_populacao="populacao_brasil_censo_2022_com_estado.csv"
):
    """
    Calcula o indicador de internações por doenças crônicas para múltiplas UFs, anos e meses.

    Parâmetros:
    - ufs (list): Lista de siglas de estados.
    - anos (list): Lista de anos.
    - meses (list ou None): Lista de meses a serem processados. Se None ou vazio, processa o ano inteiro.
    - arquivo_populacao (str): Caminho para o CSV com dados populacionais.

    Retorna:
    - DataFrame combinado com os indicadores calculados.
    """
    DOENCAS_CID10 = ["I10", "I11", "I12", "I13", "I15", "E10", "E11", "E12", "E13", "E14", "J45", "J46"]
    df_resultados = []

    # Se meses for None ou vazio, processa o ano inteiro como um único grupo
    processar_por_mes = bool(meses) and len(meses) > 0

    for uf in ufs:
        for ano in anos:
            meses_iterar = meses if processar_por_mes else [None]

            for mes in meses_iterar:
                if mes is None:
                    print(f"\n=== Processando {uf} / {ano} (ano inteiro) ===")
                else:
                    print(f"\n=== Processando {uf} / {ano} (mês {mes:02d}) ===")

                # Carrega população e filtra UF (e ano, se disponível)
                try:
                    if isinstance(arquivo_populacao, str):
                        df_pop = pd.read_csv(arquivo_populacao, sep=';', dtype={'cod_mun_ibge_6': str})
                        if 'ANO' in df_pop.columns:
                            df_pop_ano = df_pop[(df_pop['UF'] == uf) & (df_pop['ANO'] == ano)].copy()
                        else:
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

                # Carrega dados do SIH para o mês e ano especificados
                try:
                    sih = SIH()
                    sih.load()
                    files = sih.get_files(group='RD', uf=uf, year=ano, month=mes)
                    if not files:
                        if mes is None:
                            print(f"Nenhum arquivo SIH encontrado para {uf}/{ano} (ano inteiro)")
                        else:
                            print(f"Nenhum arquivo SIH encontrado para {uf}/{ano}/{mes:02d}")
                        continue

                    parquet_set = sih.download(files)
                    df_sih = pd.concat([p.to_dataframe() for p in parquet_set], ignore_index=True)
                except Exception as e:
                    if mes is None:
                        print(f"Erro ao carregar dados do SIH para {uf}/{ano} (ano inteiro): {e}")
                    else:
                        print(f"Erro ao carregar dados do SIH para {uf}/{ano}/{mes:02d}: {e}")
                    continue

                # Verifica coluna DIAG_PRINC
                if "DIAG_PRINC" not in df_sih.columns:
                    print("Coluna DIAG_PRINC não encontrada no SIH.")
                    continue

                # Filtra internações por doenças crônicas
                df_cronicas = df_sih[df_sih["DIAG_PRINC"].astype(str).str[:3].isin([cid[:3] for cid in DOENCAS_CID10])].copy()

                # Agrupa por município
                df_cronicas["MUNIC_RES"] = df_cronicas["MUNIC_RES"].astype(str).str.zfill(6)
                internacoes = df_cronicas.groupby("MUNIC_RES").size().to_frame("n_internacoes")

                # Junta os dados de internações com a base populacional
                df_base = df_base.join(internacoes, how="left")
                df_base["n_internacoes"] = df_base["n_internacoes"].fillna(0).astype(int)

                # Calcula o indicador por 10 mil habitantes
                df_base["DOENCAS_CRONICAS"] = df_base.apply(
                    lambda row: (row["n_internacoes"] / row["populacao"]) * 10000 if row["populacao"] > 0 else 0,
                    axis=1
                )

                df_base["UF"] = uf
                df_base["ANO"] = ano
                df_base["MES"] = mes if mes is not None else 0
                df_resultados.append(df_base.reset_index())

                # Gera o mapa
                try:
                    sufixo = f"_{mes:02d}" if mes is not None else "_ano_inteiro"
                    gerar_mapa_indicador(
                        df=df_base,
                        uf=uf,
                        ano=ano,
                        coluna_valor='DOENCAS_CRONICAS',
                        legenda='Internações por Doenças Crônicas (por 10 mil Hab.)',
                        cmap='OrRd',
                        nome_arquivo=f'internacoes_cronicas_{uf}_{ano}{sufixo}',
                        title=f'{uf} - Internações por Doenças Crônicas ({ano}{"" if mes is None else f"-{mes:02d}"})'
                    )
                except Exception as e:
                    print(f"Erro ao gerar mapa para {uf}/{ano}{'' if mes is None else f'/{mes:02d}'}: {e}")

    if df_resultados:
        return pd.concat(df_resultados, ignore_index=True)
    else:
        return pd.DataFrame()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula internações por doenças crônicas por 10 mil habitantes.")
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs (ex: TO PA MG)")
    parser.add_argument("--anos", nargs="+", type=int, default=[2022], help="Lista de anos (ex: 2021 2022)")
    parser.add_argument("--meses", nargs="*", type=int, default=None, help="Lista de meses (ex: 1 2 12). Se não informado, processa o ano inteiro")
    parser.add_argument("--pop", type=str, default="populacao_brasil_censo_2022_com_estado.csv", help="Arquivo CSV com dados populacionais")
    parser.add_argument("--saida", type=str, default="internacoes_cronicas_resultado.csv", help="Arquivo CSV de saída")

    args = parser.parse_args()

    df_resultado = calcular_internacoes_cronicas_por_10mil(
        ufs=args.ufs,
        anos=args.anos,
        meses=args.meses,
        arquivo_populacao=args.pop
    )

    if not df_resultado.empty:
        print("\n✅ Indicador calculado com sucesso.")
        print(df_resultado[['UF', 'ANO', 'MES', 'municipio', 'populacao', 'n_internacoes', 'DOENCAS_CRONICAS']].head())
        df_resultado.to_csv(args.saida, index=False, sep=';')
        print(f"\n📄 Resultado salvo como '{args.saida}'")
    else:
        print("⚠️ Nenhum dado foi retornado.")
