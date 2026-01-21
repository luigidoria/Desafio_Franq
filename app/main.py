import json
from src.validation import validar_csv_completo

# Carregar template
with open("database/template.json") as f:
    template = json.load(f)

# Validar um arquivo
resultado = validar_csv_completo("sample_data/multiplos_problemas.csv", template)

if resultado["valido"]:
    print("CSV pronto para ingestao!")
else:
    print(f"Encontrados {resultado['total_erros']} problema(s):")
    for erro in resultado["detalhes"]:
        print(f"  - {erro}")