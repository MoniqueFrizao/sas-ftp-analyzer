#!/usr/bin/env python3
"""
Test suite for SAS FTP Analyzer
Validates all key functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sas_ftp_analyzer import ExtratorConexoes, _resolver_variavel


def test_resolver_variavel():
    """Test variable resolution including nested references"""
    print("Testing _resolver_variavel()...")
    
    variaveis = {
        'AMBIENTE': 'PROD',
        'SCHEMA': 'P_APP_PRODUCAO',
        'NESTED': '&AMBIENTE'
    }
    
    # Test simple resolution
    assert _resolver_variavel('&SCHEMA', variaveis) == 'P_APP_PRODUCAO'
    assert _resolver_variavel('SCHEMA', variaveis) == 'P_APP_PRODUCAO'
    
    # Test nested resolution
    assert _resolver_variavel('&NESTED', variaveis) == 'PROD'
    
    # Test unknown variable
    assert _resolver_variavel('&UNKNOWN', variaveis) == '&UNKNOWN'
    
    print("  ✓ Variable resolution works correctly")


def test_detectar_tipos():
    """Test type detection for different prefixes"""
    print("Testing type detection...")
    
    extrator = ExtratorConexoes()
    
    # TERADATA (only P_APP_)
    assert extrator._detectar_tipo_variavel('&P_APP_SCHEMA') == 'TERADATA'
    assert extrator._detectar_tipo_variavel('P_APP_SCHEMA') == 'TERADATA'
    
    # EXTERNA (P_SDS_ and REF_)
    assert extrator._detectar_tipo_variavel('&P_SDS_SCHEMA') == 'EXTERNA'
    assert extrator._detectar_tipo_variavel('&REF_SCHEMA') == 'EXTERNA'
    assert extrator._detectar_tipo_variavel('P_SDS_SCHEMA') == 'EXTERNA'
    assert extrator._detectar_tipo_variavel('REF_SCHEMA') == 'EXTERNA'
    
    # ORACLE
    assert extrator._detectar_tipo_variavel('&P_ORA_SCHEMA') == 'ORACLE'
    assert extrator._detectar_tipo_variavel('ORA_SCHEMA') == 'ORACLE'
    
    # LOCAL
    assert extrator._detectar_tipo_variavel('WORK') == 'LOCAL'
    assert extrator._detectar_tipo_variavel('TEMP') == 'LOCAL'
    
    print("  ✓ Type detection works correctly")


def test_extrair_tabelas():
    """Test table extraction from SAS code"""
    print("Testing table extraction...")
    
    codigo = """
    %LET P_APP_DB = TERADATA_APP;
    %LET P_SDS_DB = TERADATA_SDS;
    
    DATA trabalho;
        SET &P_APP_DB..CLIENTES;
    RUN;
    
    PROC SQL;
        SELECT * FROM &P_SDS_DB..VENDAS;
    QUIT;
    """
    
    extrator = ExtratorConexoes()
    extrator.variaveis = extrator._extrair_variaveis_sas(codigo)
    tabelas = extrator._extrair_tabelas(codigo)
    
    assert len(tabelas) >= 2, f"Expected at least 2 tables, got {len(tabelas)}"
    
    # Check TERADATA table
    teradata_tables = [t for t in tabelas if t['tipo'] == 'TERADATA']
    assert len(teradata_tables) >= 1, "Should find at least 1 TERADATA table"
    
    # Check EXTERNA table (P_SDS_)
    externa_tables = [t for t in tabelas if t['tipo'] == 'EXTERNA']
    assert len(externa_tables) >= 1, "Should find at least 1 EXTERNA table"
    
    print(f"  ✓ Extracted {len(tabelas)} tables correctly")


def test_filtrar_bases_locais():
    """Test filtering of local databases"""
    print("Testing local database filtering...")
    
    tabelas = [
        {'schema': 'TERADATA_APP', 'tabela': 'T1', 'tipo': 'TERADATA'},
        {'schema': 'WORK', 'tabela': 'T2', 'tipo': 'LOCAL'},
        {'schema': 'ORACLE_DB', 'tabela': 'T3', 'tipo': 'ORACLE'},
        {'schema': 'TEMP', 'tabela': 'T4', 'tipo': 'LOCAL'},
    ]
    
    extrator = ExtratorConexoes()
    filtradas = extrator._filtrar_bases_locais(tabelas)
    
    assert len(filtradas) == 2, f"Expected 2 non-local tables, got {len(filtradas)}"
    assert all(t['tipo'] != 'LOCAL' for t in filtradas), "Local tables should be filtered"
    
    print("  ✓ Local database filtering works correctly")


def test_agrupar_por_tipo():
    """Test grouping tables by type"""
    print("Testing table grouping...")
    
    tabelas = [
        {'schema': 'TD1', 'tabela': 'T1', 'tipo': 'TERADATA'},
        {'schema': 'TD2', 'tabela': 'T2', 'tipo': 'TERADATA'},
        {'schema': 'OR1', 'tabela': 'T3', 'tipo': 'ORACLE'},
        {'schema': 'EX1', 'tabela': 'T4', 'tipo': 'EXTERNA'},
    ]
    
    extrator = ExtratorConexoes()
    grupos = extrator._agrupar_por_tipo(tabelas)
    
    assert 'TERADATA' in grupos, "Should have TERADATA group"
    assert 'ORACLE' in grupos, "Should have ORACLE group"
    assert 'EXTERNA' in grupos, "Should have EXTERNA group"
    assert len(grupos['TERADATA']) == 2, "Should have 2 TERADATA tables"
    assert len(grupos['ORACLE']) == 1, "Should have 1 ORACLE table"
    assert len(grupos['EXTERNA']) == 1, "Should have 1 EXTERNA table"
    
    print("  ✓ Table grouping works correctly")


def test_detectar_senhas():
    """Test password detection"""
    print("Testing password detection...")
    
    codigo = """
    LIBNAME db1 ORACLE USER=admin PASSWORD="senha123";
    LIBNAME db2 ORACLE USER=user PWD="abc123";
    LIBNAME db3 ORACLE USER=user PASSWORD=&SENHA_VARIAVEL;
    """
    
    extrator = ExtratorConexoes()
    extrator._detectar_senhas_expostas(codigo)
    
    # Should find 2 exposed passwords (not the one using &VARIAVEL)
    assert len(extrator.senhas_expostas) >= 2, f"Expected at least 2 exposed passwords, got {len(extrator.senhas_expostas)}"
    
    # Verify it doesn't flag variables as exposed
    senhas_encontradas = [s['senha'] for s in extrator.senhas_expostas]
    assert not any(s.startswith('&') for s in senhas_encontradas), "Variables should not be flagged as exposed passwords"
    
    print(f"  ✓ Detected {len(extrator.senhas_expostas)} exposed passwords correctly")


def test_mapeamento_completo():
    """Test complete mapping workflow"""
    print("Testing complete mapping workflow...")
    
    codigo = """
    %LET P_APP_SCHEMA = TERADATA_APP;
    %LET P_SDS_SCHEMA = TERADATA_SDS;
    %LET P_ORA_SCHEMA = ORACLE_PROD;
    %LET REF_SCHEMA = EXTERNAL_REF;
    
    DATA trabalho;
        SET &P_APP_SCHEMA..CLIENTES;
    RUN;
    
    PROC SQL;
        CREATE TABLE resultado AS
        SELECT * FROM &P_SDS_SCHEMA..VENDAS;
    QUIT;
    
    DATA oracle_data;
        SET &P_ORA_SCHEMA..PRODUTOS;
    RUN;
    
    PROC SQL;
        SELECT * FROM &REF_SCHEMA..DADOS_EXTERNOS;
    QUIT;
    
    DATA WORK.temp_table;
        SET WORK.original;
    RUN;
    
    LIBNAME oralib ORACLE PASSWORD="senha123";
    """
    
    extrator = ExtratorConexoes()
    resultado = extrator.mapear_tabelas_para_conexoes(codigo)
    
    # Verify all components
    assert len(resultado['variaveis']) >= 4, "Should extract at least 4 variables"
    assert len(resultado['tabelas_externas']) >= 2, "Should have EXTERNA and TERADATA tables"
    assert len(resultado['oracle_tabelas']) >= 1, "Should have Oracle tables"
    assert len(resultado['bases_locais']) >= 1, "Should have local bases"
    assert len(resultado['senhas_expostas']) >= 1, "Should detect exposed password"
    
    print("  ✓ Complete mapping workflow successful")
    print(f"    - Variables: {len(resultado['variaveis'])}")
    print(f"    - External tables: {len(resultado['tabelas_externas'])}")
    print(f"    - Oracle tables: {len(resultado['oracle_tabelas'])}")
    print(f"    - Local bases: {len(resultado['bases_locais'])}")
    print(f"    - Exposed passwords: {len(resultado['senhas_expostas'])}")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("SAS FTP Analyzer - Test Suite")
    print("=" * 60)
    print()
    
    tests = [
        test_resolver_variavel,
        test_detectar_tipos,
        test_extrair_tabelas,
        test_filtrar_bases_locais,
        test_agrupar_por_tipo,
        test_detectar_senhas,
        test_mapeamento_completo,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__} ERROR: {e}")
            failed += 1
    
    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
