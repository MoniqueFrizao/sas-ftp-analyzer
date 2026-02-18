#!/usr/bin/env python3
"""
SAS FTP Analyzer - Analisador de conexões FTP em código SAS
Analisa arquivos SAS para extrair conexões, tabelas e variáveis
"""

import re
import os
from typing import Dict, List, Tuple, Set, Any
from collections import defaultdict
import pandas as pd


def _resolver_variavel(variavel: str, variaveis_definidas: Dict[str, str]) -> str:
    """
    Resolve referências de variáveis SAS substituindo-as por seus valores.
    
    Args:
        variavel: Nome da variável a ser resolvida (com ou sem &)
        variaveis_definidas: Dicionário de variáveis já definidas
    
    Returns:
        Valor resolvido da variável ou a própria variável se não encontrada
    """
    def substituir(match):
        """Função aninhada para substituir variáveis encontradas"""
        var_name = match.group(1)
        return variaveis_definidas.get(var_name, match.group(0))
    
    # Remove & se presente
    var_limpa = variavel.lstrip('&')
    
    # Tenta encontrar no dicionário
    if var_limpa in variaveis_definidas:
        valor = variaveis_definidas[var_limpa]
        # Resolve referências aninhadas
        while '&' in valor:
            valor_anterior = valor
            valor = re.sub(r'&(\w+)', substituir, valor)
            if valor == valor_anterior:  # Evita loop infinito
                break
        return valor
    
    return variavel


class ExtratorConexoes:
    """
    Classe para extrair informações de conexões, tabelas e variáveis de arquivos SAS
    """
    
    def __init__(self):
        """Inicializa o extrator com estruturas de dados vazias"""
        self.conexoes = []
        self.tabelas = []
        self.variaveis = {}
        self.senhas_expostas = []
        self.tabelas_externas = []
        self.oracle_tabelas = []
        self.bases_locais = []
        
    def _extrair_tabelas(self, codigo_sas: str) -> List[Dict[str, str]]:
        """
        Extrai referências de tabelas do código SAS.
        
        Args:
            codigo_sas: Código SAS a ser analisado
            
        Returns:
            Lista de dicionários com informações das tabelas
        """
        tabelas_encontradas = []
        
        # Padrões para diferentes tipos de referências de tabelas
        # SAS usa .. para macro variables e . para literais
        padroes = [
            # FROM clause com macro variable
            r'FROM\s+(&\w+)\.\.(\w+)',
            # FROM clause literal
            r'FROM\s+(\w+)\.(\w+)',
            # SET statement com macro variable
            r'SET\s+(&\w+)\.\.(\w+)',
            # SET statement literal
            r'SET\s+(\w+)\.(\w+)',
            # DATA statement com macro variable
            r'DATA\s+(&\w+)\.\.(\w+)',
            # DATA statement literal
            r'DATA\s+(\w+)\.(\w+)',
        ]
        
        for padrao in padroes:
            matches = re.finditer(padrao, codigo_sas, re.IGNORECASE)
            for match in matches:
                schema_original = match.group(1)
                tabela = match.group(2)
                
                # Resolve variáveis se necessário
                schema_resolvido = _resolver_variavel(schema_original, self.variaveis)
                
                # Usa o schema ORIGINAL para detectar o tipo (não o resolvido)
                # Isso permite detectar P_APP_, P_SDS_, etc. antes da resolução
                tipo = self._detectar_tipo_variavel(schema_original)
                
                tabelas_encontradas.append({
                    'schema': schema_resolvido,
                    'tabela': tabela,
                    'schema_original': schema_original,
                    'tipo': tipo
                })
        
        return tabelas_encontradas
    
    def _extrair_variaveis_sas(self, codigo_sas: str) -> Dict[str, str]:
        """
        Extrai definições de variáveis do código SAS.
        
        Args:
            codigo_sas: Código SAS a ser analisado
            
        Returns:
            Dicionário com variáveis e seus valores
        """
        variaveis = {}
        
        # Padrão para %LET statements
        padrao_let = r'%LET\s+(\w+)\s*=\s*([^;]+);'
        matches = re.finditer(padrao_let, codigo_sas, re.IGNORECASE)
        
        for match in matches:
            var_name = match.group(1)
            var_value = match.group(2).strip()
            
            # Resolve variáveis aninhadas
            var_value = _resolver_variavel(var_value, variaveis)
            variaveis[var_name] = var_value
        
        return variaveis
    
    def _detectar_tipo_variavel(self, nome_variavel: str) -> str:
        """
        Detecta o tipo de variável/schema baseado em prefixos conhecidos.
        
        Args:
            nome_variavel: Nome da variável ou schema
            
        Returns:
            Tipo detectado (ORACLE, TERADATA, EXTERNA, LOCAL, etc.)
        """
        # Remove & se presente (para macro variables)
        nome_limpo = nome_variavel.lstrip('&')
        nome_upper = nome_limpo.upper()
        
        # Referências externas - REF_ e P_SDS_ (verificar primeiro)
        if nome_upper.startswith('REF_') or nome_upper.startswith('P_SDS_'):
            return 'EXTERNA'
        
        # TERADATA - apenas P_APP_ (P_SDS_ já foi tratado como EXTERNA)
        if nome_upper.startswith('P_APP_'):
            return 'TERADATA'
        
        # ORACLE - P_ORA_ ou ORA_
        if nome_upper.startswith('P_ORA_') or nome_upper.startswith('ORA_'):
            return 'ORACLE'
        
        # Bases locais - WORK, TEMP, etc
        if nome_upper in ['WORK', 'TEMP', 'TMP']:
            return 'LOCAL'
        
        return 'DESCONHECIDO'
    
    def _detectar_tipo_fonte_schema(self, schema: str) -> str:
        """
        Detecta o tipo de fonte do schema.
        Identifica se é Oracle, Teradata, referência externa ou base local.
        
        Args:
            schema: Nome do schema a ser analisado
            
        Returns:
            Tipo da fonte (ORACLE, TERADATA, EXTERNA, LOCAL)
        """
        schema_upper = schema.upper()
        
        # Referências externas - REF_ e P_SDS_ devem ir para EXTERNA (verificar primeiro)
        if schema_upper.startswith('REF_') or schema_upper.startswith('P_SDS_'):
            return 'EXTERNA'
        
        # TERADATA - apenas P_APP_ (P_SDS_ já foi tratado acima como EXTERNA)
        if schema_upper.startswith('P_APP_'):
            return 'TERADATA'
        
        # ORACLE
        if schema_upper.startswith('P_ORA_') or schema_upper.startswith('ORA_'):
            return 'ORACLE'
        
        # Bases locais
        if schema_upper in ['WORK', 'TEMP', 'TMP']:
            return 'LOCAL'
        
        return 'DESCONHECIDO'
    
    def _filtrar_bases_locais(self, tabelas: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Filtra bases locais da lista de tabelas.
        
        Args:
            tabelas: Lista de tabelas a filtrar
            
        Returns:
            Lista de tabelas sem as bases locais
        """
        return [
            tabela for tabela in tabelas
            if tabela['tipo'] != 'LOCAL'
        ]
    
    def _agrupar_por_tipo(self, tabelas: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
        """
        Agrupa tabelas por tipo (ORACLE, TERADATA, EXTERNA).
        
        Args:
            tabelas: Lista de tabelas para agrupar
            
        Returns:
            Dicionário com tabelas agrupadas por tipo
        """
        grupos = defaultdict(list)
        
        for tabela in tabelas:
            tipo = tabela['tipo']
            grupos[tipo].append(tabela)
        
        return dict(grupos)
    
    def mapear_tabelas_para_conexoes(self, codigo_sas: str) -> Dict[str, Any]:
        """
        Mapeia tabelas encontradas no código SAS para suas respectivas conexões.
        
        Args:
            codigo_sas: Código SAS a ser analisado
            
        Returns:
            Dicionário com o mapeamento de tabelas e conexões
        """
        # Primeiro extrai variáveis
        self.variaveis = self._extrair_variaveis_sas(codigo_sas)
        
        # Extrai tabelas
        tabelas_brutas = self._extrair_tabelas(codigo_sas)
        
        # Remove duplicatas
        tabelas_unicas = []
        tabelas_set = set()
        for tabela in tabelas_brutas:
            chave = f"{tabela['schema']}.{tabela['tabela']}"
            if chave not in tabelas_set:
                tabelas_set.add(chave)
                tabelas_unicas.append(tabela)
        
        # Filtra bases locais
        tabelas_externas = self._filtrar_bases_locais(tabelas_unicas)
        
        # Agrupa por tipo
        grupos = self._agrupar_por_tipo(tabelas_externas)
        
        # Separa em categorias específicas
        self.tabelas_externas = grupos.get('EXTERNA', []) + grupos.get('TERADATA', [])
        self.oracle_tabelas = grupos.get('ORACLE', [])
        self.bases_locais = [t for t in tabelas_unicas if self._detectar_tipo_fonte_schema(t['schema']) == 'LOCAL']
        
        # Detecta senhas expostas no código
        self._detectar_senhas_expostas(codigo_sas)
        
        return {
            'tabelas_externas': self.tabelas_externas,
            'oracle_tabelas': self.oracle_tabelas,
            'bases_locais': self.bases_locais,
            'senhas_expostas': self.senhas_expostas,
            'variaveis': self.variaveis
        }
    
    def _detectar_senhas_expostas(self, codigo_sas: str):
        """
        Detecta senhas expostas em conexões no código SAS.
        
        Args:
            codigo_sas: Código SAS a ser analisado
        """
        # Padrões comuns de conexões com senha
        padroes_senha = [
            r'PASSWORD\s*=\s*["\']([^"\']+)["\']',
            r'PWD\s*=\s*["\']([^"\']+)["\']',
            r'PASS\s*=\s*["\']([^"\']+)["\']',
        ]
        
        for padrao in padroes_senha:
            matches = re.finditer(padrao, codigo_sas, re.IGNORECASE)
            for match in matches:
                senha = match.group(1)
                # Não considera variáveis como senhas expostas
                if not senha.startswith('&'):
                    self.senhas_expostas.append({
                        'senha': senha,
                        'contexto': match.group(0)
                    })


def diagnosticar_ftp(arquivo_sas: str, arquivo_saida: str = 'relatorio_ftp.xlsx'):
    """
    Diagnostica arquivo SAS e gera relatório em Excel.
    
    Args:
        arquivo_sas: Caminho para o arquivo SAS a ser analisado
        arquivo_saida: Caminho para o arquivo Excel de saída
    """
    # Lê o arquivo SAS
    if not os.path.exists(arquivo_sas):
        raise FileNotFoundError(f"Arquivo não encontrado: {arquivo_sas}")
    
    with open(arquivo_sas, 'r', encoding='utf-8', errors='ignore') as f:
        codigo_sas = f.read()
    
    # Cria extrator e processa
    extrator = ExtratorConexoes()
    resultado = extrator.mapear_tabelas_para_conexoes(codigo_sas)
    
    # Cria DataFrames para cada aba
    df_tabelas_externas = pd.DataFrame(resultado['tabelas_externas']) if resultado['tabelas_externas'] else pd.DataFrame(columns=['schema', 'tabela', 'tipo'])
    df_oracle = pd.DataFrame(resultado['oracle_tabelas']) if resultado['oracle_tabelas'] else pd.DataFrame(columns=['schema', 'tabela', 'tipo'])
    df_senhas = pd.DataFrame(resultado['senhas_expostas']) if resultado['senhas_expostas'] else pd.DataFrame(columns=['senha', 'contexto'])
    
    # Cria resumo
    resumo_data = {
        'Métrica': [
            'Total de Tabelas Externas',
            'Total de Tabelas Oracle',
            'Total de Bases Locais',
            'Total de Senhas Expostas',
            'Total de Variáveis Definidas'
        ],
        'Valor': [
            len(resultado['tabelas_externas']),
            len(resultado['oracle_tabelas']),
            len(resultado['bases_locais']),
            len(resultado['senhas_expostas']),
            len(resultado['variaveis'])
        ]
    }
    df_resumo = pd.DataFrame(resumo_data)
    
    # Gera arquivo Excel com todas as abas
    with pd.ExcelWriter(arquivo_saida, engine='openpyxl') as writer:
        df_tabelas_externas.to_excel(writer, sheet_name='Tabelas-Externas', index=False)
        df_oracle.to_excel(writer, sheet_name='Oracle-Tabelas', index=False)
        df_senhas.to_excel(writer, sheet_name='Senhas-Expostas', index=False)
        df_resumo.to_excel(writer, sheet_name='Resumo', index=False)
    
    print(f"Relatório gerado com sucesso: {arquivo_saida}")
    print(f"- Tabelas Externas: {len(resultado['tabelas_externas'])}")
    print(f"- Tabelas Oracle: {len(resultado['oracle_tabelas'])}")
    print(f"- Bases Locais: {len(resultado['bases_locais'])}")
    print(f"- Senhas Expostas: {len(resultado['senhas_expostas'])}")
    print(f"- Variáveis: {len(resultado['variaveis'])}")


def main():
    """
    Função principal - ponto de entrada do programa.
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python sas_ftp_analyzer.py <arquivo_sas> [arquivo_saida.xlsx]")
        print("\nExemplo:")
        print("  python sas_ftp_analyzer.py meu_codigo.sas")
        print("  python sas_ftp_analyzer.py meu_codigo.sas relatorio.xlsx")
        sys.exit(1)
    
    arquivo_sas = sys.argv[1]
    arquivo_saida = sys.argv[2] if len(sys.argv) > 2 else 'relatorio_ftp.xlsx'
    
    try:
        diagnosticar_ftp(arquivo_sas, arquivo_saida)
    except Exception as e:
        print(f"Erro ao processar arquivo: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
