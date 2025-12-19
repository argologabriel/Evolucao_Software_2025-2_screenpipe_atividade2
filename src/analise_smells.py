import os
import requests
import pandas as pd
import time
import re
from tqdm import tqdm

# ==============================================================================
# 1. CONFIGURAÇÕES
# ==============================================================================

modelos_locais = [
    "qwen2.5-coder:7b",
    "llama3.1:8b",
    "mistral"
]

REPO_OWNER = "mediar-ai"
REPO_NAME  = "screenpipe"
BRANCH     = "main"

EXTENSOES_ALVO = (".ts", ".tsx", ".js", ".py", ".rs")
IGNORAR_CAMINHOS = ["test", "spec", "dist", "build", "node_modules", "ui"]
LIMITE_ARQUIVOS = 30

# Mapeamento do PDF Refactoring Guru
SMELL_CATALOG = {
    "Bloaters":                   ["Long Method", "Large Class", "Primitive Obsession", "Long Parameter List", "Data Clumps"],
    "Object-Orientation Abusers": ["Alternative Classes with Different Interfaces", "Refused Bequest", "Switch Statements", "Temporary Field"],
    "Change Preventers":          ["Divergent Change", "Parallel Inheritance Hierarchies", "Shotgun Surgery"],
    "Dispensables":               ["Comments", "Duplicate Code", "Data Class", "Dead Code", "Lazy Class", "Speculative Generality"],
    "Couplers":                   ["Feature Envy", "Inappropriate Intimacy", "Incomplete Library Class", "Message Chains", "Middle Man"]
}

PROMPT_TEMPLATE = """
You are a Senior Software Engineer and Code Auditor.

I will provide you with a source code file. 
Your task is to analyze it strictly based on the **Refactoring Guru** catalog of Code Smells.

--- BEGIN SOURCE CODE ---
{code}
--- END SOURCE CODE ---

TASK:
Identify any Code Smells in the code above.

Output format (for EACH smell found):
- Smell Name: [Name from Refactoring Guru catalog]
- Location: [Line number or Function name]
- Explanation: [Why it violates clean code]
- Refactoring: [Brief suggestion]

Output format (if NO smells found):
"✅ No Code Smells detected."

IMPORTANT:
1. Do NOT invent code. Analyze ONLY the code provided between the --- lines.
2. If the code is empty or too short, say "No code to analyze".
3. Be concise.
"""

# ==============================================================================
# 2. FUNÇÕES
# ==============================================================================

def get_repo_files():
    print(f"📡 Buscando lista de arquivos de {REPO_OWNER}/{REPO_NAME}...")
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/{BRANCH}?recursive=1"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200: return []
        tree = r.json().get("tree", [])
        arquivos_validos = []
        for f in tree:
            path = f["path"]
            if (path.endswith(EXTENSOES_ALVO) and not any(ign in path for ign in IGNORAR_CAMINHOS)):
                arquivos_validos.append(path)
        return arquivos_validos
    except Exception as e:
        print(f"❌ Erro: {e}")
        return []

def get_raw_code(path):
    url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{path}"
    try:
        r = requests.get(url, timeout=10)
        return r.text if r.status_code == 200 else None
    except:
        return None

def ask_ollama(model_name, prompt):
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 8192}
    }
    try:
        r = requests.post(url, json=payload, timeout=180)
        if r.status_code == 200:
            return r.json()["message"]["content"]
        return f"Erro {r.status_code}"
    except Exception as e:
        return f"Erro: {e}"

def parse_ia_response(text):
    """
    Parser robusto que aceita variações de formatação dos modelos (Llama, Mistral, Qwen).
    """
    stats = {cat: 0 for cat in SMELL_CATALOG.keys()}
    stats["Total_Smells"] = 0
    stats["Outros"] = 0
    
    # Lista de padrões Regex para tentar capturar os smells
    patterns = [
        # Padrão 1: "- Smell Name: Nome" (O ideal pedido no prompt)
        r"-\s*\**Smell Name\**:\s*(.+)",
        
        # Padrão 2: "1. **Nome**: ..." (Estilo comum do Llama)
        r"\d+\.\s*\*\*(.+?)\*\*:",
        
        # Padrão 3: "- **Nome**: ..." (Estilo lista com negrito direto)
        r"-\s*\*\*(.+?)\*\*:",
        
        # Padrão 4: "Smell Name: Nome" (Sem hífen no começo)
        r"Smell Name:\s*(.+)"
    ]

    found_smells = []
    
    # Testa cada padrão. Se achar algo, adiciona à lista.
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        # Limpa os matches (remove quebras de linha e espaços extras)
        clean_matches = [m.strip() for m in matches if len(m.strip()) < 50] # <50 evita pegar frases inteiras erradas
        found_smells.extend(clean_matches)

    # Remove duplicatas (caso mais de um regex pegue a mesma linha)
    unique_smells = list(set(found_smells))
    
    stats["Total_Smells"] = len(unique_smells)

    for smell_raw in unique_smells:
        smell_clean = smell_raw.lower()
        found_category = False
        
        # Tenta classificar nas categorias do PDF
        for category, specific_smells in SMELL_CATALOG.items():
            # Verifica se o nome oficial está contido no texto achado
            # Ex: "Long Function" (achado) contem "Long Method" (oficial)? Não.
            # Então fazemos o inverso também: O texto achado contém o oficial? 
            # E adicionamos mapeamentos comuns de erro dos modelos.
            
            for oficial in specific_smells:
                oficial_lower = oficial.lower()
                
                # Match exato ou contido
                if oficial_lower in smell_clean or smell_clean in oficial_lower:
                    stats[category] += 1
                    found_category = True
                    break
                
                # Correção de alucinações comuns (Mapeamento "De -> Para")
                # Ex: Mistral adora falar "Long Function" em vez de "Long Method"
                aliases = {
                    "long method": ["long function", "huge method"],
                    "large class": ["god object", "god class"],
                    "duplicate code": ["duplicated code", "copy paste"],
                }
                
                if oficial_lower in aliases:
                    if any(alias in smell_clean for alias in aliases[oficial_lower]):
                        stats[category] += 1
                        found_category = True
                        break

            if found_category: break
        
        if not found_category:
            stats["Outros"] += 1

    return stats

# ==============================================================================
# 3. EXECUÇÃO
# ==============================================================================

if __name__ == "__main__":
    print(f"{'='*60}")
    print(f"🚀 ANÁLISE ")
    print(f"{'='*60}\n")

    todos_arquivos = get_repo_files()
    if not todos_arquivos: exit()
        
    arquivos_para_analisar = todos_arquivos[:LIMITE_ARQUIVOS]
    
    os.makedirs("resultados_corrigidos", exist_ok=True)

    for modelo in modelos_locais:
        print(f"\n🧠 Modelo: {modelo.upper()}...")
        resultados_modelo_atual = []

        try: requests.post("http://localhost:11434/api/generate", json={"model": modelo, "prompt": "hi"})
        except: pass

        for arquivo in tqdm(arquivos_para_analisar, desc=f"Lendo com {modelo}"):
            codigo = get_raw_code(arquivo)
            if not codigo: continue
            
            prompt_final = PROMPT_TEMPLATE.replace("{code}", codigo[:6000])
            
            start = time.time()
            resposta = ask_ollama(modelo, prompt_final)
            tempo = time.time() - start
            
            metricas = parse_ia_response(resposta)
            
            dados_arquivo = {
                "Modelo": modelo,
                "Arquivo": arquivo,
                "Tempo_Seg": round(tempo, 2),
                **metricas,
                "Analise_Raw": resposta
            }
            resultados_modelo_atual.append(dados_arquivo)
            time.sleep(0.5)

        nome_clean = modelo.replace(":", "_").replace(".", "-")
        arquivo_saida = f"resultados_corrigidos/metricas_{nome_clean}.csv"
        
        df = pd.DataFrame(resultados_modelo_atual)
        
        cols_ordem = ["Modelo", "Arquivo", "Tempo_Seg", "Total_Smells"] + list(SMELL_CATALOG.keys()) + ["Outros", "Analise_Raw"]
        cols_finais = [c for c in cols_ordem if c in df.columns]
        df = df[cols_finais]

        df.to_csv(arquivo_saida, index=False, encoding="utf-8-sig")
        print(f"✅ Salvo: {arquivo_saida}")

    print("\n🏁 Agora os resultados devem refletir o código real!")