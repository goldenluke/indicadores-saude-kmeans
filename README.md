# Análise de Indicadores de Saúde e Clusterização de Municípios Brasileiros

![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Este projeto realiza um fluxo completo de análise de dados de saúde pública, desde a coleta automatizada de dados brutos de fontes governamentais até a aplicação de técnicas de machine learning para agrupar municípios brasileiros segundo seus perfis de saúde.

O objetivo é transformar dados públicos do DATASUS e IBGE em inteligência acionável, culminando na criação de um painel de indicadores consolidados e na segmentação dos municípios por estado do Brasil por meio do algoritmo K-Means.

---

## 🚀 Principais Funcionalidades

- **Coleta Automatizada de Dados:** Scripts para baixar dados diretamente dos sistemas do SUS (SIM, SINASC, CNES, SIH, SINAN).
- **Cálculo de Indicadores:** Automatiza o cálculo de indicadores de saúde fundamentais:
  - Taxa de Mortalidade Infantil (TMI)
  - Proporção de Partos Cesáreos
  - Cobertura de Pré-Natal Adequado (7+ consultas)
  - Taxa de Médicos por 1.000 Habitantes
  - Proporção de Óbitos por Causas Mal Definidas
  - Taxa de Internações por Complicações de Doenças Crônicas
- **Consolidação de Dados:** Integra indicadores em um arquivo único CSV indexado por município.
- **Análise de Cluster (K-Means):** Agrupa municípios em perfis de vulnerabilidade/eficiência por meio de K-Means.
- **Visualização:** Gera mapas de calor, "Snake Plots" e outros gráficos para análise e apresentação dos resultados.

---

## 📚 Fontes de Dados

- SIM (Sistema de Informações sobre Mortalidade)
- SINASC (Sistema de Informações sobre Nascidos Vivos)
- CNES (Cadastro Nacional de Estabelecimentos de Saúde)
- SIH (Sistema de Informações Hospitalares)
- SINAN (Sistema de Informação de Agravos de Notificação)
- FTP do IBGE

Todos os dados são públicos e obtidos via DATASUS e IBGE.

---

## ⚙️ Como Usar

1. Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```
2. Baixe os shapefiles do IBGE e coloque-os na pasta `shapefiles/`.
3. Execute `orquestrador.py` para gerar e consolidar os indicadores.
4. Execute `analise_cluster.py` para realizar a clusterização e gerar as visualizações.

> **Obs:** Certifique-se de possuir as bases populacionais atualizadas (`populacao_brasil_censo_2022_com_estado.csv`).

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Abra uma issue ou envie um pull request para sugestões, correções ou melhorias.

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para detalhes.
