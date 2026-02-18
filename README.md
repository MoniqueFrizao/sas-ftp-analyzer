# SAS FTP Analyzer

Analisador de código SAS para identificar conexões FTP, tabelas externas e vulnerabilidades de segurança.

## 🚀 Início Rápido

### Instalação

```bash
pip install -r requirements.txt
```

### Uso Básico

```bash
python sas_ftp_analyzer.py seu_codigo.sas relatorio.xlsx
```

## 📊 Funcionalidades

- ✅ Extração de conexões TERADATA (P_APP_, P_SDS_)
- ✅ Extração de conexões ORACLE (P_ORA_, ORA_)
- ✅ Identificação de referências externas (REF_)
- ✅ Detecção de senhas expostas
- ✅ Geração de relatório Excel com 4 abas:
  - Tabelas-Externas
  - Oracle-Tabelas
  - Senhas-Expostas
  - Resumo

## 📖 Documentação

Veja o [Guia de Uso Completo](GUIA_USO.md) para:
- Exemplos detalhados
- API de programação
- Estrutura do código
- Padrões suportados

## 🏗️ Estrutura do Código

Todo o código segue boas práticas Python:
- Indentação correta (4 espaços)
- Métodos organizados em classes
- Funções com docstrings completas
- Tipagem de parâmetros e retornos

## 🔍 Exemplo

```sas
%LET P_APP_SCHEMA = TERADATA_APP;

DATA trabalho;
    SET &P_APP_SCHEMA..CLIENTES;
RUN;
```

Gera relatório identificando:
- Schema: TERADATA_APP
- Tabela: CLIENTES
- Tipo: TERADATA (Tabelas-Externas)

## 🛡️ Segurança

O analyzer detecta senhas expostas em:
- `PASSWORD="senha"`
- `PWD="senha"`  
- `PASS="senha"`

## 📝 Licença

MIT License

