# -*- coding: utf-8 -*-
import pandas as pd
from functools import reduce

# Supondo que todos os scripts de indicadores foram refatorados para serem funções modulares
from modulos.mortalidade_infantil import calcular_tmi_multiplos_uf_anos
from modulos.pre_natal import calcular_cobertura_prenatal_multiplos_uf_anos
from modulos.medicos import calcular_medicos_por_mil
from modulos.partos_cesareos import calcular_prop_partos_cesareos_multiplos_uf_anos
from modulos.causas_mal_definidas import calcular_causas_mal_definidas
from modulos.internacoes_cronicas import calcular_internacoes_cronicas_por_10mil

if __name__ == "__main__":
    # --- Configurações da Análise ---
    UFS  = ['TO', 'GO']
    ANOS = [2021, 2022]
    POP_FILE = "populacao_brasil_censo_2022_com_estado.csv"

    print("📊 Iniciando orquestrador para múltiplos UF/anos...\n")

    # --- Execução dos Módulos ---
    # --- Execução dos Módulos ---
    df_tmi = calcular_tmi_multiplos_uf_anos(
        ufs=UFS,
        anos=ANOS,
        arquivo_populacao=POP_FILE
    )

    df_prenatal = calcular_cobertura_prenatal_multiplos_uf_anos(
        ufs=UFS,
        anos=ANOS,
        arquivo_populacao=POP_FILE
    )

    df_medicos = calcular_medicos_por_mil(
        ufs=UFS,
        anos=ANOS,
        meses=None,
        arquivo_populacao=POP_FILE
    )

    df_partos = calcular_prop_partos_cesareos_multiplos_uf_anos(
        ufs=UFS,
        anos=ANOS,
        arquivo_populacao=POP_FILE
    )

    df_mal_def = calcular_causas_mal_definidas(
        ufs=UFS,
        anos=ANOS,
        arquivo_populacao=POP_FILE
    )

    df_intern = calcular_internacoes_cronicas_por_10mil(
        ufs=UFS,
        anos=ANOS,
        meses=None,
        arquivo_populacao=POP_FILE
    )

    print("\n🔄 Todos os cálculos foram concluídos. Integrando os resultados...")

    # --- Consolidação Robusta ---

    # 1. Cria uma lista dos DataFrames de indicadores, selecionando apenas o essencial
    # A chave de junção é ['cod_mun_ibge_6', 'ANO']
    lista_dfs = []
    if not df_tmi.empty:
        lista_dfs.append(df_tmi[['cod_mun_ibge_6', 'ANO', 'UF', 'municipio', 'populacao', 'TMI']])
    if not df_prenatal.empty:
        lista_dfs.append(df_prenatal[['cod_mun_ibge_6', 'ANO', 'COBERTURA_PRENATAL']])
    if not df_medicos.empty:
        lista_dfs.append(df_medicos[['cod_mun_ibge_6', 'ANO', 'TAXA_MEDICOS']])
    if not df_partos.empty:
        lista_dfs.append(df_partos[['cod_mun_ibge_6', 'ANO', 'PROP_CESAREOS']])
    if not df_mal_def.empty:
        lista_dfs.append(df_mal_def[['cod_mun_ibge_6', 'ANO', 'PROP_MAL_DEFINIDAS']])
    if not df_intern.empty:
        lista_dfs.append(df_intern[['cod_mun_ibge_6', 'ANO', 'DOENCAS_CRONICAS']])

    # 2. Usa a função 'reduce' para aplicar o merge sequencialmente
    if lista_dfs:
        df_final = reduce(
            lambda left, right: pd.merge(
                left,
                right,
                on=['cod_mun_ibge_6', 'ANO'], # Chave de junção
                how='outer' # 'outer' garante que nenhuma linha seja perdida
            ),
            lista_dfs
        )

        # 3. Limpeza final
        df_final.fillna(0, inplace=True)

        # --- Salvamento do Resultado ---
        output_filename = f"indicadores_integrados.csv"
        df_final.to_csv(output_filename, sep=';', encoding='utf-8-sig', index=False)

        print("\n✅ Indicadores integrados com sucesso!")
        print(f"📁 Arquivo consolidado e sem duplicatas salvo como: '{output_filename}'")
        print("\n--- Amostra do Painel de Dados Final ---")
        print(df_final.head())
    else:
        print("⚠️ Nenhum dado foi calculado com sucesso. Nenhum arquivo foi gerado.")
