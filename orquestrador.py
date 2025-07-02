import pandas as pd

# Importa as funções de cada arquivo
from partos_cesareos import calcular_proporcao_partos_cesareos
from causas_mal_definidas import calcular_indicador_causas_mal_definidas
from mortalidade_infantil import calcular_tmi
from medicos import calcular_medicos_por_mil_habitantes
from internacoes_cronicas import calcular_internacoes_cronicas_por_10mil
from pre_natal import calcular_cobertura_prenatal_adequado

# Parâmetros gerais
UF_SIGLA = 'TO'
ANO = 2022
ARQUIVO_POP = "populacao_brasil_censo_2022_com_estado.csv"

print("📊 Iniciando execução de todos os indicadores...")

# Executa cada função
df_tmi = calcular_tmi()
df_prenatal = calcular_cobertura_prenatal_adequado()
df_medicos = calcular_medicos_por_mil_habitantes()
df_partos = calcular_proporcao_partos_cesareos()
df_mal_definidas = calcular_indicador_causas_mal_definidas()
df_internacoes = calcular_internacoes_cronicas_por_10mil()

# Padroniza todos os índices para garantir join correto
for df in [df_tmi, df_prenatal, df_medicos, df_partos, df_mal_definidas, df_internacoes]:
    df.index = df.index.astype(str).str[:6]

# Junta todos os indicadores em um único DataFrame
df_final = df_tmi \
    .join(df_prenatal[["COBERTURA_PRENATAL"]], how="outer") \
    .join(df_medicos[["TAXA_MEDICOS"]], how="outer") \
    .join(df_partos[["PROP_CESAREOS"]], how="outer") \
    .join(df_mal_definidas[["PROP_MAL_DEFINIDAS"]], how="outer") \
    .join(df_internacoes[["DOENCAS_CRONICAS"]], how="outer")

# Mostra os dados
print("\n✅ Indicadores integrados:")
print(df_final.head())

# Salva o CSV final
df_final.to_csv("indicadores_integrados_tocantins_2022.csv", sep=";", encoding="utf-8-sig")
print("\n📁 Arquivo 'indicadores_integrados_tocantins_2022.csv' salvo com sucesso!")
