#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exemplo de uso do analisador SAS FTP
"""

import sys
from pathlib import Path

# Mock openpyxl if not available
try:
    import openpyxl
except ImportError:
    print("Warning: openpyxl not installed, mocking it for demonstration...")
    from unittest.mock import MagicMock
    sys.modules['openpyxl'] = MagicMock()
    sys.modules['openpyxl.styles'] = MagicMock()

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from analisador_sas_ftp import (
    EtratorConexoes,
    AnalisadorSAS,
    DetectorSenhas,
    ServicoExcelPorCaminho
)


def exemplo_analise_simples():
    """Exemplo de análise simples de código SAS"""
    
    codigo_sas = """
    %let schema_tera = P_APP_;
    %let schema_oracle = P_;
    %let schema_lake = REF_;
    
    libname mylib oracle user=admin password=secret123;
    
    proc sql;
    create table work.resultado as
    select 
        a.id,
        a.nome,
        b.produto,
        c.valor
    from &schema_tera.CLIENTES a
    inner join &schema_oracle.PRODUTOS b on a.id = b.cliente_id
    inner join &schema_lake.VENDAS c on a.id = c.cliente_id
    where a.ativo = 'S';
    quit;
    """
    
    print("="*70)
    print("EXEMPLO: Análise de Código SAS")
    print("="*70)
    
    # 1. Extrair conexões e tabelas
    print("\n1. Extrator de Conexões")
    extrator = EtratorConexoes()
    resultado = extrator.processar_codigo(codigo_sas, "exemplo.sas")
    
    print(f"   Variáveis encontradas: {len(resultado['variaveis'])}")
    for var, valor in resultado['variaveis'].items():
        print(f"     - {var} = {valor}")
    
    print(f"\n   Tabelas encontradas: {len(resultado['tabelas'])}")
    for tabela in resultado['tabelas']:
        print(f"     - {tabela['tabela']:30s} [{tabela['tipo']}]")
    
    print(f"\n   Tabelas externas: {len(resultado['tabelas_externas'])}")
    for tabela in resultado['tabelas_externas']:
        print(f"     - {tabela['tabela']:30s} [{tabela['tipo']}]")
    
    # 2. Análise geral
    print("\n2. Analisador SAS")
    analisador = AnalisadorSAS()
    analise = analisador.analisar_codigo(codigo_sas)
    
    print(f"   Libnames: {analise['libnames']}")
    print(f"   Tabelas SQL: {len(analise['tabelas'])}")
    print(f"   Senhas expostas: {len(analise['senhas'])}")
    
    # 3. Detector de senhas
    print("\n3. Detector de Senhas")
    detector = DetectorSenhas()
    senhas = detector.detectar(codigo_sas, "exemplo.sas")
    
    if senhas:
        print(f"   ⚠️  ALERTA: {len(senhas)} senha(s) exposta(s)!")
        for senha in senhas:
            print(f"     - Linha {senha['linha']}: {senha['contexto'][:60]}")
    else:
        print("   ✅ Nenhuma senha exposta detectada")
    
    # 4. Agrupamento por tipo
    print("\n4. Agrupamento por Tipo de Banco")
    for tipo, tabelas in resultado['agrupadas'].items():
        if tabelas:
            print(f"   {tipo}: {len(tabelas)} tabela(s)")
            for t in tabelas:
                print(f"     - {t['tabela']}")
    
    print("\n" + "="*70)
    print("Exemplo concluído com sucesso!")
    print("="*70)


def exemplo_deteccao_tipos():
    """Exemplo de detecção de tipos de tabelas"""
    
    print("\n\n")
    print("="*70)
    print("EXEMPLO: Detecção de Tipos de Tabelas")
    print("="*70)
    
    extrator = EtratorConexoes()
    
    exemplos = [
        'P_APP_CLIENTES',
        'P_SDS_VENDAS',
        'P_DADOS_PRODUTOS',
        'REF_USUARIOS',
        'EXP_RELATORIO',
        'LDW_ANALISE',
        'AG_AGREGADOS',
        'WORK.TEMP',
        'MYSCHEMA.TABELA'
    ]
    
    print("\nTabela                      | Tipo Detectado")
    print("-" * 70)
    
    for tabela in exemplos:
        tipo = extrator._detectar_tipo_variavel(tabela)
        print(f"{tabela:30s} | {tipo}")
    
    print("="*70)


def exemplo_resolucao_variaveis():
    """Exemplo de resolução de variáveis SAS"""
    
    print("\n\n")
    print("="*70)
    print("EXEMPLO: Resolução de Variáveis SAS")
    print("="*70)
    
    extrator = EtratorConexoes()
    
    # Definir variáveis
    extrator.variaveis = {
        'SCHEMA': 'P_APP_',
        'BASE': 'CLIENTES',
        'AMBIENTE': 'PROD',
        'SUFIXO': '_2024'
    }
    
    exemplos = [
        '&SCHEMA.&BASE',
        '&SCHEMA.&BASE.&SUFIXO',
        'TABELA_&AMBIENTE',
        '&SCHEMA.VENDAS'
    ]
    
    print("\nVariáveis definidas:")
    for var, valor in extrator.variaveis.items():
        print(f"  {var} = {valor}")
    
    print("\nResolução:")
    print("\nOriginal                    | Resolvido")
    print("-" * 70)
    
    for original in exemplos:
        resolvido = extrator._resolver_variavel(original)
        print(f"{original:30s} | {resolvido}")
    
    print("="*70)


if __name__ == "__main__":
    # Executar exemplos
    exemplo_analise_simples()
    exemplo_deteccao_tipos()
    exemplo_resolucao_variaveis()
    
    print("\n\n✅ Todos os exemplos executados com sucesso!")
    print("\nPara análise completa de arquivos, use:")
    print("  python3 backend/analisador_sas_ftp.py --caminho /path/to/files --output relatorio.xlsx")
