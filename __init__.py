# indicadores-saude-kmeans/__init__.py

from pathlib import Path

# Caminhos principais úteis
BASE_DIR = Path(__file__).resolve().parent

# Caminhos padrão de dados e mapas
DATA_DIR = BASE_DIR / "dados"
MAPAS_DIR = BASE_DIR / "mapas"
SHAPEFILES_DIR = BASE_DIR / "shapefiles"

# Versão do pacote (opcional)
__version__ = "0.1.0"

# Exporte funcionalidades úteis se quiser
from modulos.mortalidade_infantil import calcular_tmi_multiplos_uf_anos
from modulos.pre_natal import calcular_cobertura_prenatal_multiplos_uf_anos
from modulos.medicos import calcular_medicos_por_mil
from modulos.partos_cesareos import calcular_prop_partos_cesareos_multiplos_uf_anos
from modulos.causas_mal_definidas import calcular_causas_mal_definidas
from modulos.internacoes_cronicas import calcular_internacoes_cronicas_por_10mil
