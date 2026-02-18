# SAS FTP Analyzer - Guia de Uso

## Descrição

O SAS FTP Analyzer é uma ferramenta Python que analisa código SAS para identificar:
- Conexões a bancos de dados (Oracle, Teradata)
- Referências a tabelas externas
- Variáveis definidas no código
- Senhas expostas (potenciais vulnerabilidades de segurança)

## Requisitos

- Python 3.6+
- pandas
- openpyxl

## Instalação

```bash
pip install pandas openpyxl
```

## Uso

### Linha de Comando

```bash
python sas_ftp_analyzer.py <arquivo_sas> [arquivo_saida.xlsx]
```

**Exemplos:**

```bash
# Analisa arquivo e gera relatorio_ftp.xlsx (padrão)
python sas_ftp_analyzer.py meu_codigo.sas

# Analisa arquivo e gera relatorio_customizado.xlsx
python sas_ftp_analyzer.py meu_codigo.sas relatorio_customizado.xlsx
```

### Como Módulo Python

```python
from sas_ftp_analyzer import diagnosticar_ftp, ExtratorConexoes

# Análise completa com geração de relatório Excel
diagnosticar_ftp('meu_codigo.sas', 'relatorio.xlsx')

# Uso programático
extrator = ExtratorConexoes()

# Ler código SAS
with open('meu_codigo.sas', 'r') as f:
    codigo = f.read()

# Processar e obter resultados
resultado = extrator.mapear_tabelas_para_conexoes(codigo)

print(f"Tabelas externas encontradas: {len(resultado['tabelas_externas'])}")
print(f"Tabelas Oracle encontradas: {len(resultado['oracle_tabelas'])}")
print(f"Senhas expostas: {len(resultado['senhas_expostas'])}")
```

## Estrutura do Código

### Principais Componentes

1. **`_resolver_variavel()`**: Resolve referências de macro variáveis SAS (&VAR)
   - Suporta resolução recursiva de variáveis aninhadas
   
2. **`ExtratorConexoes`**: Classe principal para extração de informações
   - `_extrair_tabelas()`: Extrai referências de tabelas do código
   - `_extrair_variaveis_sas()`: Extrai definições %LET
   - `_detectar_tipo_variavel()`: Identifica tipo baseado em prefixos
   - `_filtrar_bases_locais()`: Remove referências a WORK, TEMP, etc.
   - `_agrupar_por_tipo()`: Agrupa tabelas por tipo de conexão
   - `mapear_tabelas_para_conexoes()`: Função principal de mapeamento

3. **`diagnosticar_ftp()`**: Função de alto nível que gera relatório Excel

4. **`main()`**: Ponto de entrada para execução via linha de comando

## Detecção de Tipos

O analyzer identifica tabelas baseado nos seguintes prefixos:

### TERADATA (Tabelas Externas)
- Variáveis iniciando com `P_APP_`
  - Exemplo: `&P_APP_SCHEMA..CLIENTES`

### EXTERNA (Tabelas Externas)
- Variáveis iniciando com `P_SDS_`
  - Exemplo: `&P_SDS_SCHEMA..VENDAS`
- Variáveis iniciando com `REF_`
  - Exemplo: `&REF_SCHEMA..DADOS`

### ORACLE
- Variáveis iniciando com `P_ORA_` ou `ORA_`
  - Exemplo: `&P_ORA_SCHEMA..PRODUTOS`

### LOCAL (Filtradas do relatório)
- `WORK`, `TEMP`, `TMP`
  - Exemplo: `WORK.temp_data`

## Formato do Relatório Excel

O relatório gerado contém 4 abas:

### 1. Tabelas-Externas
Tabelas TERADATA e referências externas (P_APP_, P_SDS_, REF_)

| Coluna | Descrição |
|--------|-----------|
| schema | Nome do schema resolvido |
| tabela | Nome da tabela |
| schema_original | Nome original da variável (com &) |
| tipo | TERADATA ou EXTERNA |

### 2. Oracle-Tabelas
Tabelas Oracle identificadas (P_ORA_, ORA_)

| Coluna | Descrição |
|--------|-----------|
| schema | Nome do schema resolvido |
| tabela | Nome da tabela |
| schema_original | Nome original da variável |
| tipo | ORACLE |

### 3. Senhas-Expostas
Senhas encontradas em texto claro no código (⚠️ vulnerabilidade)

| Coluna | Descrição |
|--------|-----------|
| senha | Senha exposta |
| contexto | Linha de código onde foi encontrada |

### 4. Resumo
Métricas gerais da análise

| Métrica | Descrição |
|---------|-----------|
| Total de Tabelas Externas | Quantidade de tabelas TERADATA/EXTERNA |
| Total de Tabelas Oracle | Quantidade de tabelas Oracle |
| Total de Bases Locais | Quantidade de bases temporárias |
| Total de Senhas Expostas | ⚠️ Senhas em texto claro |
| Total de Variáveis Definidas | Variáveis %LET encontradas |

## Exemplo de Código SAS Suportado

```sas
/* Definição de variáveis */
%LET P_APP_SCHEMA = TERADATA_APP;
%LET P_SDS_SCHEMA = TERADATA_SDS;
%LET P_ORA_SCHEMA = ORACLE_PROD;

/* Tabela TERADATA (vai para Tabelas-Externas) */
DATA trabalho;
    SET &P_APP_SCHEMA..CLIENTES;
RUN;

/* Tabela Oracle (vai para Oracle-Tabelas) */
PROC SQL;
    SELECT * FROM &P_ORA_SCHEMA..PRODUTOS;
QUIT;

/* Tabela local (filtrada) */
DATA WORK.temp;
    x = 1;
RUN;
```

## Indentação e Estrutura

Todo o código segue as convenções Python:
- 4 espaços por nível de indentação
- Métodos de classe corretamente aninhados
- Funções auxiliares no nível de módulo quando apropriado
- Docstrings completas em todas as funções

## Tratamento de Variáveis SAS

### Sintaxe de Referência
- Macro variável: `&VAR`
- Tabela com macro: `&SCHEMA..TABELA` (duplo ponto)
- Tabela literal: `SCHEMA.TABELA` (ponto simples)

### Resolução Recursiva
O analyzer resolve variáveis aninhadas:
```sas
%LET AMBIENTE = PROD;
%LET SCHEMA_&AMBIENTE = P_APP_PRODUCAO;
/* &SCHEMA_PROD será resolvido corretamente */
```

## Segurança

### Detecção de Senhas Expostas

O analyzer identifica padrões comuns de senhas em texto claro:
- `PASSWORD="senha"`
- `PWD="senha"`
- `PASS="senha"`

⚠️ **Atenção**: Senhas expostas representam riscos de segurança e devem ser substituídas por variáveis protegidas ou sistemas de gerenciamento de credenciais.

## Contribuindo

Para contribuir com melhorias:
1. Adicione novos padrões de detecção em `_extrair_tabelas()`
2. Adicione novos tipos de conexão em `_detectar_tipo_variavel()`
3. Mantenha a estrutura de indentação (4 espaços)
4. Adicione testes para novos recursos

## Licença

Este projeto está sob licença MIT.
