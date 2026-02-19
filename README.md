# SAS FTP Analyzer

Analisador completo de scripts SAS com suporte a conexões FTP e geração de relatórios Excel detalhados.

## 📋 Características

### Classes Implementadas

1. **ConectorFTP** - Gerencia conexões FTP e leitura de arquivos
2. **AnalisadorSAS** - Analisa código SAS e extrai informações
3. **EtratorConexoes** - Extrai e classifica conexões e tabelas
4. **DetectorSenhas** - Detecta senhas expostas em código
5. **DetectorTabelasReplicadas** - Identifica tabelas replicadas
6. **ServicoExcelPorCaminho** - Gera relatórios Excel completos

### Detecção Inteligente de Tipos

O analisador detecta automaticamente o tipo de banco de dados:

- **TERADATA**: `P_APP_*`, `P_SDS_*`
- **ORACLE**: `P_*` (genérico), `AG*`
- **DATALAKE**: `REF_*`, `EXP_*`, `LDW*`
- **OUTROS**: Demais casos

### Relatório Excel com 13 Abas

1. **Catalogo** - Lista de arquivos analisados
2. **Conexoes-Externas** - Conexões detectadas
3. **Variaveis-Sas** - Variáveis macro (%let)
4. **Outros** - Informações diversas
5. **Tabelas-Externas** - Tabelas externas (incluindo REF_ e P_SDS_)
6. **Bases** - Bases de dados
7. **Tabelas-Replicadas** - Tabelas usadas em múltiplos arquivos
8. **Tabelas-Por-Tipo** - Agrupamento por tipo de banco
9. **Teradata-Roles** - Roles e permissões Teradata
10. **Datalake-Tabelas** - Tabelas do Datalake
11. **Oracle-Tabelas** - Tabelas Oracle
12. **Senhas-Expostas** - Senhas em texto plano (SEGURANÇA)
13. **Resumo** - Estatísticas gerais

## 🚀 Uso

### Análise Local

```bash
python3 backend/analisador_sas_ftp.py --caminho /path/to/sas/files --output relatorio.xlsx
```

### Análise via FTP

```bash
python3 backend/analisador_sas_ftp.py \
    --caminho /remote/path \
    --ftp-host ftp.example.com \
    --ftp-usuario user \
    --ftp-senha password \
    --output relatorio.xlsx
```

### Diagnóstico FTP

```bash
python3 backend/analisador_sas_ftp.py \
    --diagnostico \
    --ftp-host ftp.example.com \
    --ftp-usuario user \
    --ftp-senha password
```

## 📦 Dependências

```bash
pip install openpyxl
```

## ✅ Testes

Execute os testes para validar a instalação:

```bash
python3 test_analyzer.py
```

## 🔧 Funcionalidades Técnicas

### Extração de Variáveis SAS

- Detecta e resolve variáveis `%let`
- Substitui `&variavel` nos nomes de tabelas

### Análise de Tabelas

- Extrai tabelas de: `FROM`, `SET`, `CREATE TABLE`, `UPDATE`, `MERGE`
- Identifica schema e tipo de conexão
- Filtra bases locais vs. externas

### Segurança

- Detecta senhas expostas em código
- Identifica padrões: `password=`, `pwd=`, `senha=`
- Reporta arquivo, linha e contexto

### Performance

- Processamento em lote de múltiplos arquivos
- Suporte a grandes volumes de código
- Cache de variáveis entre processamentos

## 📝 Correções Implementadas

✅ Indentação correta (4 espaços por nível)
✅ Todos os métodos nas classes corretas
✅ Detecção TERADATA corrigida (P_APP_, P_SDS_)
✅ REF_ e P_SDS_ tratados como tabelas externas
✅ Todas as 13 abas do Excel funcionando
✅ Funções main() e diagnosticar_ftp() completas

## 📄 Licença

Este projeto é parte do sistema de análise SAS FTP.
