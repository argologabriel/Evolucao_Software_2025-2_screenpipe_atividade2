import os
import requests
import pandas as pd
from transformers import pipeline
from tqdm import tqdm
import time

# =====================================
# CONFIGURAÇÕES
# =====================================

REPO_OWNER = "mediar-ai"
REPO_NAME = "screenpipe"
BRANCH = "main"

OUTPUT_DIR = "resultados"
os.makedirs(OUTPUT_DIR, exist_ok=True)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

# =====================================
# MODELOS SELECIONADOS (3 DIFERENTES)
# =====================================

MODELOS = {
    "FLAN-T5": "google/flan-t5-base",
    "CodeT5": "Salesforce/codet5-base",
    "BART-Large": "facebook/bart-large-cnn"
}


# =====================================
# PROMPT PADRÃO PARA CODE SMELLS
# =====================================

PROMPT_TEMPLATE = """
Analyze the following source code and identify possible CODE SMELLS
based on Refactoring Guru classification.

For each smell, explain WHY it is a problem.

Source code:
----------------
{code}
----------------
"""

# =====================================
# FUNÇÕES GITHUB
# =====================================

def get_repo_tree():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/{BRANCH}?recursive=1"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()["tree"]

def get_file_content(path):
    url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{path}"
    r = requests.get(url, timeout=30)
    if r.status_code == 200:
        return r.text
    return None

# =====================================
# EXECUÇÃO PRINCIPAL
# =====================================

print("🔍 Coletando arquivos do repositório...")
tree = get_repo_tree()

code_files = [
    f["path"] for f in tree
    if f["path"].endswith((".ts", ".tsx", ".js"))
]

print(f"📂 {len(code_files)} arquivos de código encontrados.\n")

for nome_modelo, modelo_path in MODELOS.items():
    print(f"\n🤖 Analisando com o modelo: {nome_modelo}")
    print("=" * 60)

    analyzer = pipeline(
        "text2text-generation",
        model=modelo_path,
        max_new_tokens=512
    )

    resultados = []

    for file_path in tqdm(code_files[:15]):  # limita para não estourar tempo
        code = get_file_content(file_path)
        if not code:
            continue

        prompt = PROMPT_TEMPLATE.format(code=code[:1500])

        try:
            response = analyzer(prompt)[0]["generated_text"]

            resultados.append({
                "Arquivo": file_path,
                "Modelo": nome_modelo,
                "Analise": response
            })

            time.sleep(1)

        except Exception as e:
            resultados.append({
                "Arquivo": file_path,
                "Modelo": nome_modelo,
                "Analise": f"Erro: {e}"
            })

    df = pd.DataFrame(resultados)
    output_file = f"{OUTPUT_DIR}/code_smells_{nome_modelo}.csv"
    df.to_csv(output_file, index=False, encoding="utf-8-sig")

    print(f"📁 Resultado salvo em: {output_file}")

print("\n✅ ANÁLISE FINALIZADA")
