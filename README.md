# 🧪 Automação de Rotina Diária — Laboratório

Script Python que automatiza o fluxo completo de liberação de laudos:
login no sistema → verificação de status e pagamento → download do PDF → envio via WhatsApp Web.

---

## 📦 Estrutura do Projeto

```
lab_automation/
├── .env.example       ← Modelo de configuração (não editar)
├── .env               ← Suas configurações reais (CRIAR ESTE ARQUIVO)
├── config.py          ← Carrega as configurações do .env
├── lab_bot.py         ← Automação do sistema do laboratório
├── whatsapp_bot.py    ← Automação do WhatsApp Web
├── main.py            ← Ponto de entrada do script
├── requirements.txt   ← Dependências Python
└── lab_automation.log ← Log gerado automaticamente após cada execução
```

---

## ⚙️ Configuração Inicial (faça apenas uma vez)

### 1. Instale o Python
Versão 3.9 ou superior: https://python.org/downloads

### 2. Instale as dependências
Abra o PowerShell nesta pasta e execute:
```powershell
pip install -r requirements.txt
```

### 3. Configure o arquivo `.env`
Copie o modelo de configuração:
```powershell
Copy-Item .env.example .env
```
Abra o arquivo `.env` com o Bloco de Notas e preencha **todos os campos**:

| Campo | O que preencher |
|---|---|
| `LAB_URL` | URL completa da tela de login do sistema |
| `LAB_USUARIO` | Seu nome de usuário no sistema |
| `LAB_SENHA` | Sua senha no sistema |
| `SELETOR_*` | Seletores CSS dos elementos HTML (veja abaixo) |
| `TEXTO_STATUS_FINALIZADO` | Texto exato do badge de status (ex: `Finalizado`) |
| `TEXTO_PAGAMENTO_CONFIRMADO` | Texto exato do badge de pagamento (ex: `Pago`) |
| `PASTA_LAUDOS` | Caminho local para salvar os PDFs (ex: `C:/Laudos/`) |
| `MSG_TEMPLATE` | Template da mensagem do WhatsApp |

### 4. Como encontrar os seletores CSS?

1. Abra o sistema do laboratório no Microsoft Edge
2. Clique com o botão direito no elemento desejado (campo de login, botão, etc.)
3. Clique em **"Inspecionar"**
4. No painel que abre, clique com botão direito no elemento destacado em azul
5. Vá em **"Copiar" → "Copiar seletor"**
6. Cole o valor no campo correspondente do `.env`

---

## 🚀 Como Usar

### Pré-requisitos antes de executar:
- ✅ Arquivo `.env` configurado
- ✅ Microsoft Edge aberto com **WhatsApp Web autenticado** (web.whatsapp.com)

### Execução:
```powershell
python main.py --pedido 12345 --telefone 5511987654321 --paciente "Maria Silva"
```

### Parâmetros:

| Parâmetro | Obrigatório | Descrição |
|---|---|---|
| `--pedido` | ✅ | Número do pedido no sistema |
| `--telefone` | ✅ | Telefone do paciente (formato: `55` + DDD + número, sem espaços) |
| `--paciente` | ✅ | Nome do paciente (usado na mensagem do WhatsApp) |

### Exemplo de mensagem gerada:
```
Olá, Maria Silva! 🧪 Seu laudo do pedido nº 12345 já está disponível.
Data de liberação: 18/06/2026. Em caso de dúvidas, entre em contato conosco.
Att, Laboratório.
```
*(Template configurável no `.env`)*

---

## 📋 O que o script faz (passo a passo)

```
1. Abre o Microsoft Edge e acessa o sistema do laboratório
2. Faz login com suas credenciais
3. Pesquisa o número do pedido
4. Verifica se o status é "Finalizado"    → se não, encerra e avisa
5. Verifica se o pagamento foi confirmado → se não, encerra e avisa
6. Clica em "Download do Laudo"
7. Captura o PDF aberto na nova aba e salva em PASTA_LAUDOS
8. Localiza a aba do WhatsApp Web no Edge
9. Abre conversa com o número do paciente
10. Envia a mensagem personalizada
11. Envia o PDF como anexo
```

---

## 📝 Logs

Após cada execução, um arquivo `lab_automation.log` é gerado/atualizado na pasta do projeto com todos os passos e erros para facilitar diagnóstico.

---

## ❓ Problemas Comuns

| Problema | Solução |
|---|---|
| `EnvironmentError: variável não definida` | Abra o `.env` e preencha o campo indicado |
| `RuntimeError: nova aba não abriu` | Verifique `SELETOR_BTN_DOWNLOAD` no `.env` |
| `WhatsApp Web não encontrado` | Abra `web.whatsapp.com` no Edge antes de executar |
| `TimeoutException` | O sistema demorou a responder; aumente `TIMEOUT` em `lab_bot.py` |
| PDF não abre / seletor errado | Re-inspecione os elementos com F12 no Edge e atualize o `.env` |

---

## 🔒 Segurança

- O arquivo `.env` contém suas credenciais — **nunca o compartilhe**
- Adicione `.env` ao `.gitignore` se usar controle de versão
