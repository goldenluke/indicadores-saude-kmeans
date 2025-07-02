# -*- coding: utf-8 -*-
import pandas as pd
import io

def limpar_e_formatar_censo_csv(input_filename):
    """
    Lê um arquivo CSV do Censo, limpa-o, formata e adiciona uma coluna
    com a sigla do estado.
    """
    print(f"Iniciando a limpeza e formatação do arquivo: {input_filename}")

    try:
        # --- Leitura Inteligente do Arquivo ---
        df = pd.read_csv(input_filename, sep=';', skiprows=4, names=['cod_mun_ibge_7', 'municipio_uf', 'populacao'])

        # --- Limpeza dos Dados ---
        df['populacao'] = pd.to_numeric(df['populacao'], errors='coerce')
        df.dropna(subset=['populacao'], inplace=True)
        df['populacao'] = df['populacao'].astype(int)
        df['cod_mun_ibge_7'] = df['cod_mun_ibge_7'].astype(str)

        print("Dados brutos carregados e linhas de rodapé removidas.")

        # --- Formatação e Criação de Novas Colunas ---

        # 1. Cria a coluna com o código IBGE de 6 dígitos
        df['cod_mun_ibge_6'] = df['cod_mun_ibge_7'].str[:6]

        # 2. **NOVO PASSO:** Extrai a sigla do estado para uma nova coluna 'estado'
        # A expressão regular r'\((\w{2})\)$' captura as duas letras dentro dos parênteses no final da string.
        df['UF'] = df['municipio_uf'].str.extract(r'\((\w{2})\)$')
        print("Coluna 'estado' criada com sucesso.")

        # 3. Limpa o nome do município para remover a sigla do estado (ex: "(RO)")
        df['municipio'] = df['municipio_uf'].str.replace(r'\s\(\w{2}\)$', '', regex=True)

        # 4. Seleciona e reordena as colunas para o formato final, incluindo a nova coluna 'estado'
        colunas_finais = ['cod_mun_ibge_7', 'municipio', 'UF', 'populacao', 'cod_mun_ibge_6']
        df_final = df[colunas_finais]

        print(f"Processamento concluído. Total de {df_final.shape[0]} municípios formatados.")

        # --- Salvando o arquivo ---
        output_filename = "populacao_brasil_censo_2022_com_estado.csv"
        df_final.to_csv(output_filename, sep=';', encoding='utf-8-sig', index=False)

        print(f"\n✅ Arquivo '{output_filename}' salvo com sucesso no diretório atual!")
        print("\n--- Amostra dos dados gerados ---")
        print(df_final.head())

        return df_final

    except FileNotFoundError:
        print(f"❌ ERRO: O arquivo de entrada '{input_filename}' não foi encontrado.")
        return None
    except Exception as e:
        print(f"\n❌ Ocorreu um erro inesperado durante o processo: {e}")
        return None

# Executa a função com o arquivo fornecido
# (Assumindo que o nome do arquivo é 'input_file_8.csv' como no seu exemplo)
df_resultado = limpar_e_formatar_censo_csv('tabela4714.csv')
