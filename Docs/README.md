# Guia de Execução Local (Sem Docker)

Este documento descreve o passo a passo para configurar e rodar o projeto **Contratos Auto LogTudo** localmente em seu computador de desenvolvimento sem o uso de Docker.

O projeto possui duas interfaces distintas:
1. **Aplicativo Desktop (Tkinter):** Uma interface gráfica direta executada localmente no Windows.
2. **Aplicativo Web (FastAPI + React/Vite):** Uma arquitetura web cliente-servidor (Backend + Frontend).

---

## Pré-requisitos Gerais
* **Python 3.10+** (Recomendado adicionar ao PATH do sistema durante a instalação)
* **Node.js 18+** (Necessário apenas se for rodar/buildar a interface Web)
* **Google Chrome** instalado no sistema (Playwright usará ou baixará sua própria instância compatível)

---

## 🖥️ Opção 1: Rodar o Aplicativo Desktop (Interface Tkinter)

A interface Desktop é executada diretamente a partir do arquivo `main.py` na raiz do projeto.

### Passo 1: Criar e Ativar Ambiente Virtual (Recomendado)
Abra o terminal (CMD ou PowerShell) na raiz do projeto (`Contratos_auto/`) e execute:

**No Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**No Windows (CMD):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

### Passo 2: Instalar Dependências do Python
Com o ambiente virtual ativo, instale as bibliotecas necessárias:
```bash
pip install -r requirements.txt
```

### Passo 3: Instalar o Navegador Playwright
O Playwright precisa do binário do Chromium para realizar a automação:
```bash
playwright install chromium
```

### Passo 4: Executar o Aplicativo
Execute o script principal:
```bash
python main.py
```
> [!NOTE]
> O arquivo `config.ini` e o histórico de logs `log_automacao.txt` serão criados automaticamente na pasta onde você iniciou o script.

---

## 🌐 Opção 2: Rodar o Aplicativo Web (FastAPI + React/Vite)

A versão web é dividida em um **Backend (FastAPI)** e um **Frontend (Vite + React)**.

### 🔌 Passo 2.1: Configurar e Iniciar o Backend (FastAPI)

1. Com o seu ambiente virtual ativado na raiz do projeto, instale as dependências específicas do backend:
   ```bash
   pip install -r backend/requirements.txt
   ```

2. Certifique-se de que os navegadores do Playwright estão instalados (caso não tenha feito na Opção 1):
   ```bash
   playwright install chromium
   ```

3. Configure o caminho base (`BASE_PATH`) da API se desejar. Por padrão, ele roda sob o prefixo `/contratos`. Se quiser rodar diretamente na raiz, você pode definir a variável de ambiente:
   
   **No PowerShell:**
   ```powershell
   $env:BASE_PATH=""
   ```
   **No CMD:**
   ```cmd
   set BASE_PATH=
   ```

4. Inicie o servidor FastAPI usando o Uvicorn a partir da raiz:
   ```bash
   python -m uvicorn backend.app.main:app --reload --port 8000
   ```
   * O backend estará disponível em: `http://localhost:8000/` (ou `http://localhost:8000/contratos/` se a variável `BASE_PATH` não tiver sido limpa).

---

### 🎨 Passo 2.2: Configurar e Iniciar o Frontend (React/Vite)

Você tem duas formas de executar o frontend:

#### Método A: Modo Desenvolvimento (Hot Reloading)
Útil para alterar código do frontend e ver as atualizações em tempo real.

1. Abra um novo terminal na pasta `web/` do projeto:
   ```bash
   cd web
   ```

2. Instale as dependências do Node.js:
   ```bash
   npm install
   ```

3. Inicie o servidor de desenvolvimento do Vite:
   ```bash
   npm run dev
   ```
   * O frontend estará disponível em: `http://localhost:5173/`

#### Método B: Servir em Produção via FastAPI (Recomendado)
Permite que o FastAPI sirva os arquivos estáticos diretamente, sem a necessidade de manter o Node.js rodando.

1. Navegue até a pasta `web/` e faça o build do frontend:
   ```bash
   cd web
   npm install
   npm run build
   ```

2. O build gerará a pasta `web/dist/`. 
3. O servidor backend FastAPI (iniciado no Passo 2.1) detectará automaticamente esta pasta e servirá a interface estática do app diretamente em `http://localhost:8000/` (ou `/contratos/`).

---

## 🛠️ Solução de Problemas Comuns

### 1. Erro ao ativar o script do PowerShell (Restrição de Execução)
Caso receba um erro de segurança ao tentar ativar o ambiente virtual no PowerShell:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```
E tente ativar o ambiente virtual `.venv` novamente.

### 2. O Navegador Playwright não abre ou dá erro de inicialização
Certifique-se de ter rodado o comando de instalação do navegador dentro do ambiente virtual:
```bash
playwright install chromium
```

### 3. Portas já em uso (Port 8000 ou 5173)
Se você receber um erro informando que a porta está ocupada, altere a porta de execução:
* Para o backend: adicione o argumento `--port <nova-porta>` no comando do uvicorn.
* Para o frontend: o Vite tentará a próxima porta disponível automaticamente (ex: 5174).
