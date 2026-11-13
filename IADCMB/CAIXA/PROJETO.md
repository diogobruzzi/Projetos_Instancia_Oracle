# Automação de Download - Lista de Imóveis Caixa Econômica Federal (RJ)

## 📋 Objetivo
Baixar a lista de imóveis disponíveis para venda no estado do Rio de Janeiro (RJ) no portal oficial da Caixa Econômica Federal.

## 🌐 Fonte
- **Site**: https://venda-imoveis.caixa.gov.br/sistema/download-lista.asp
- **URL direta do arquivo**: https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_RJ.csv

---

## 🛠️ Metodologia

### Tentativa 1: Playwright (Automação Completa)
Tentativa de automação completa navegando pelo site:
1. Acessar a página de download
2. Selecionar UF = RJ no dropdown
3. Clicar no botão "Próximo"
4. Aguardar download

**Problema encontrado**: O site possui proteção anti-bot (Radware/perfdrive.com) que intercepta o envio do formulário e redireciona para uma página de validação, impedindo o download automatizado via navegador.

### Tentativa 2: Download Direto com `requests` ✅ **SUCESSO**
Abordagem simplificada: download direto da URL conhecida do arquivo CSV, usando apenas a biblioteca `requests` do Python.

---

## 📦 Estrutura do Projeto

```
CAIXA/
├── venv/                          # Ambiente virtual Python
├── downloads/
│   └── caixa/
│       └── Lista_imoveis_RJ.csv   # Arquivo baixado (2.83 MB)
├── download_caixa_imoveis.py      # Script Playwright (não funcional completo)
└── PROJETO.md                     # Este arquivo
```

---

## 🚀 Como Executar

### Pré-requisitos
```bash
# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install requests
```

### Download Direto (Recomendado)
```bash
source venv/bin/activate
python3 -c "
import requests
url = 'https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_RJ.csv'
headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}
r = requests.get(url, headers=headers, timeout=30)
with open('./downloads/caixa/Lista_imoveis_RJ.csv', 'wb') as f:
    f.write(r.content)
print(f'Download OK: {len(r.content)} bytes')
"
```

---

## 📊 Validação do Arquivo Baixado

| Parâmetro | Valor |
|-----------|-------|
| **Nome do arquivo** | `Lista_imoveis_RJ.csv` |
| **Caminho absoluto** | `/home/ubuntu/CAIXA/downloads/caixa/Lista_imoveis_RJ.csv` |
| **Tamanho** | 2.964.670 bytes (2,83 MB) |
| **Extensão** | `.csv` |
| **Formato** | CSV (separador: ponto e vírgula `;`) |
| **Encoding** | UTF-8 (com caracteres especiais) |
| **Linhas totais** | 8.327 |
| **Cabeçalho** | 1 linha |
| **Registros de imóveis** | 8.326 |

### Estrutura do CSV
```csv
Nº do imóvel;UF;Cidade;Bairro;Endereço;Preço;Valor de avaliação;Desconto;Financiamento;Descrição;Modalidade de venda;Link de acesso
8444413568670;RJ;ARARUAMA;ITATIQUARA;RUA WALDOMIRO MAXIMO CARVALHO, N. 106...;64.962,97;164.000,00;60.39;Não;Casa, 0.00 de área total...;Venda Direta Online;https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=8444413568670
```

### Colunas Disponíveis
1. **Nº do imóvel** - Identificador único
2. **UF** - Estado (RJ)
3. **Cidade** - Município
4. **Bairro** - Bairro
5. **Endereço** - Endereço completo
6. **Preço** - Preço de venda
7. **Valor de avaliação** - Valor de avaliação do imóvel
8. **Desconto** - Percentual de desconto
9. **Financiamento** - Se aceita financiamento (Sim/Não)
10. **Descrição** - Detalhes do imóvel (tipo, áreas, vagas)
11. **Modalidade de venda** - Ex: Venda Direta Online
12. **Link de acesso** - URL para detalhes no portal

---

## ⚠️ Observações Importantes

1. **Proteção Anti-Bot**: O portal utiliza Radware Bot Manager que bloqueia automações via navegador (Playwright/Selenium) ao detectar envio de formulário programático.

2. **URL Estável**: A URL direta `https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_RJ.csv` funciona consistentemente para o estado do RJ.

3. **Atualização**: A lista é atualizada periodicamente pela Caixa. A data de geração consta no cabeçalho do arquivo (ex: "Data de geração: 03/11/2026").

4. **Outros Estados**: Para outros estados, alterar `RJ` na URL para a UF desejada (ex: `SP`, `MG`, `RS`).

---

## 📝 Conclusão

O download foi realizado com sucesso utilizando abordagem direta via HTTP request, contornando a necessidade de automação de navegador complexa. O arquivo CSV baixado contém **8.326 imóveis** do estado do Rio de Janeiro com todas as informações necessárias para análise.

**Status**: ✅ **CONCLUÍDO COM SUCESSO**