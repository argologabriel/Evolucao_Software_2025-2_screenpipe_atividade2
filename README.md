# 🕵️ Análise de Code Smells com LLMs (Ollama)

Este projeto contém uma ferramenta de **Engenharia de Software** que utiliza Modelos de Linguagem (LLMs) rodando localmente via **Ollama** para auditar a qualidade do código de um repositório alvo.

O script:

1.  Mapeia os arquivos de código-fonte (ex: `.ts`, `.tsx`, `.rs`, `.py`) do projeto configurado (ex: `screenpipe`).
2.  Submete trechos de código a múltiplos modelos de IA (como `qwen2.5-coder`, `llama3.1`, `mistral`).
3.  Identifica e classifica **Code Smells** (como _Bloaters_, _Couplers_, _Dispensables_) baseando-se no catálogo do [Refactoring Guru](https://refactoring.guru/refactoring/smells).
4.  Gera relatórios comparativos em `.csv`, contendo métricas de tempo, contagem de problemas e sugestões de refatoração.

---

## 🚀 Como Rodar o Projeto

Siga estas etapas para configurar o ambiente e executar a auditoria.

**Nota Importante:** A estrutura de pastas esperada é que o script principal esteja dentro de `src/`. Todos os comandos abaixo devem ser executados **de dentro da pasta `src`**.

```text
Evolucao_Software_2025-2_screenpipe/
├── src/            <-- 📂 Você deve estar aqui
│   ├── resultados_corrigidos/
│   ├── analise_smells.py
│   ├── requirements.txt
│   ├── .gitignore
│   └── ...
└── ...
```

### 1. Pré-requisitos

Python 3.8+

Ollama instalado e em execução (Servidor de inferência local).

### 2. Configuração do Ambiente

**1. Configuração do Ollama:** Antes de iniciar o Python, você precisa garantir que os modelos de IA estão baixados na sua máquina. Abra seu terminal e execute:

```
ollama pull qwen2.5-coder:7b
ollama pull llama3.1:8b
ollama pull mistral

# Para confirmar a instalação
ollama list
```

Certifique-se de que o servidor Ollama está rodando (padrão: localhost:11434).

**2. Crie e Ative um Ambiente Virtual:** É altamente recomendado usar um ambiente virtual (venv) para isolar as dependências.

```
# Crie o ambiente (só precisa fazer isso uma vez)
python -m venv venv

# Ative o ambiente (precisa fazer toda vez que for rodar)
# No Windows:
.\venv\Scripts\activate
# No macOS / Linux:
source venv/bin/activate
```

**3. Instale as Dependências:** Com o ambiente ativado (você verá (venv) no seu terminal), instale as bibliotecas necessárias.

```
pip install -r requirements.txt
```

### 3. Configuração do Script

O script já vem pré-configurado para analisar o repositório screenpipe. Caso queira alterar o alvo ou os modelos, edite as variáveis no início do arquivo analise_smells.py:

```
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
```

### 4. Executando a Análise

Com o ambiente ativado `(venv)` e o Ollama rodando, execute:

```
python analise_smells.py
```

O script exibirá o progresso no terminal:

- Ele iterará sobre a lista de modelos configurada.
- Você verá barras de progresso (tqdm) indicando a leitura e análise de cada arquivo.
- Os resultados parciais são salvos automaticamente para evitar perda de dados.

## 📊 Saída (Resultados)

O script salvará os relatórios automaticamente na pasta src/resultados_corrigidos/.
A estrutura final ficará assim:

```
src/
├── resultados_corrigidos/   <-- ✅ SEUS RELATÓRIOS ESTÃO AQUI
│   ├── metricas_qwen2-5-coder_7b.csv
│   ├── metricas_llama3-1_8b.csv
│   ├── metricas_mistral.csv
│
└── analise_smells.py
```

Cada arquivo .csv conterá as seguintes colunas principais:

- `Modelo`: A IA utilizada (ex: mistral).
- `Arquivo`: O caminho do código analisado.
- `Tempo_Seg`: Tempo de processamento (latência) da análise.
- `Total_Smells`: Quantidade total de problemas encontrados.
- `Categorias`: Colunas específicas (Bloaters, Object-Orientation Abusers, etc.) com a contagem por tipo.
- `Analise_Raw`: A resposta completa da IA, contendo a explicação técnica e a sugestão de refatoração ("Refactoring Recipe").

## 🔧 Customização

_Para adicionar novos modelos:_ Baixe o modelo no Ollama (`ollama pull nome-modelo`) e adicione a string correspondente na lista `modelos_locais` dentro do script.

_Para alterar os tipos de arquivos:_ Edite a tupla `EXTENSOES_ALVO` (ex: adicione `.java` ou `.cpp`).
