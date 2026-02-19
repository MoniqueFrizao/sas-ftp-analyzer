#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analisador SAS FTP - Análise completa de scripts SAS e conexões FTP
"""

import re
import ftplib
import os
from pathlib import Path
from typing import Dict, List, Tuple, Set
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment


class ConectorFTP:
    """Gerencia conexões FTP e operações de leitura de arquivos"""
    
    def __init__(self, host: str, usuario: str, senha: str, porta: int = 21):
        self.host = host
        self.usuario = usuario
        self.senha = senha
        self.porta = porta
        self.ftp = None
    
    def conectar(self):
        """Estabelece conexão FTP"""
        try:
            self.ftp = ftplib.FTP()
            self.ftp.connect(self.host, self.porta)
            self.ftp.login(self.usuario, self.senha)
            return True
        except Exception as e:
            print(f"Erro ao conectar ao FTP: {e}")
            return False
    
    def desconectar(self):
        """Encerra conexão FTP"""
        if self.ftp:
            try:
                self.ftp.quit()
            except:
                pass
    
    def listar_arquivos(self, caminho: str, extensao: str = ".sas") -> List[str]:
        """Lista arquivos no caminho FTP especificado"""
        arquivos = []
        try:
            self.ftp.cwd(caminho)
            items = self.ftp.nlst()
            for item in items:
                if item.endswith(extensao):
                    arquivos.append(item)
        except Exception as e:
            print(f"Erro ao listar arquivos em {caminho}: {e}")
        return arquivos
    
    def ler_arquivo(self, caminho_completo: str) -> str:
        """Lê conteúdo de um arquivo do FTP"""
        linhas = []
        try:
            self.ftp.retrlines(f'RETR {caminho_completo}', linhas.append)
            return '\n'.join(linhas)
        except Exception as e:
            print(f"Erro ao ler arquivo {caminho_completo}: {e}")
            return ""


class AnalisadorSAS:
    """Analisa código SAS para extrair informações relevantes"""
    
    def __init__(self):
        self.padroes = {
            'libname': re.compile(r'libname\s+(\w+)\s+', re.IGNORECASE),
            'proc_sql': re.compile(r'proc\s+sql', re.IGNORECASE),
            'create_table': re.compile(r'create\s+table\s+(\S+)', re.IGNORECASE),
            'from_clause': re.compile(r'from\s+(\S+)', re.IGNORECASE),
            'set_statement': re.compile(r'set\s+(\S+)', re.IGNORECASE),
            'merge_statement': re.compile(r'merge\s+(.+?)(?:;|\s+by\s+)', re.IGNORECASE),
            'update_statement': re.compile(r'update\s+(\S+)', re.IGNORECASE),
            'password': re.compile(r'(password|pwd|senha)\s*=\s*["\']?([^"\';\s]+)', re.IGNORECASE),
        }
    
    def analisar_codigo(self, codigo: str) -> Dict:
        """Analisa código SAS e retorna informações estruturadas"""
        return {
            'libnames': self._extrair_libnames(codigo),
            'tabelas': self._extrair_tabelas_codigo(codigo),
            'senhas': self._extrair_senhas(codigo),
            'conexoes': self._extrair_conexoes(codigo)
        }
    
    def _extrair_libnames(self, codigo: str) -> List[str]:
        """Extrai declarações LIBNAME"""
        return self.padroes['libname'].findall(codigo)
    
    def _extrair_tabelas_codigo(self, codigo: str) -> List[str]:
        """Extrai referências a tabelas no código"""
        tabelas = set()
        
        # FROM clauses
        tabelas.update(self.padroes['from_clause'].findall(codigo))
        
        # CREATE TABLE
        tabelas.update(self.padroes['create_table'].findall(codigo))
        
        # SET statements
        tabelas.update(self.padroes['set_statement'].findall(codigo))
        
        # UPDATE statements
        tabelas.update(self.padroes['update_statement'].findall(codigo))
        
        return list(tabelas)
    
    def _extrair_senhas(self, codigo: str) -> List[Tuple[str, str]]:
        """Extrai senhas expostas no código"""
        return self.padroes['password'].findall(codigo)
    
    def _extrair_conexoes(self, codigo: str) -> List[Dict]:
        """Extrai informações de conexões"""
        conexoes = []
        # Implementação básica - pode ser expandida
        for match in re.finditer(r'libname.*?;', codigo, re.IGNORECASE | re.DOTALL):
            conexoes.append({'declaracao': match.group(0)})
        return conexoes


class EtratorConexoes:
    """Extrai e classifica conexões e tabelas de código SAS"""
    
    def __init__(self):
        self.conexoes = {
            'TERADATA': [],
            'ORACLE': [],
            'DATALAKE': [],
            'OUTRAS': []
        }
        self.tabelas = []
        self.variaveis = {}
    
    def processar_codigo(self, codigo: str, arquivo: str) -> Dict:
        """Processa código SAS completo"""
        # Extrair variáveis SAS
        self._extrair_variaveis_sas(codigo)
        
        # Extrair tabelas
        tabelas_raw = self._extrair_tabelas(codigo)
        
        # Resolver variáveis nas tabelas
        tabelas_resolvidas = []
        for tabela in tabelas_raw:
            tabela_resolvida = self._resolver_variavel(tabela)
            tabelas_resolvidas.append({
                'tabela': tabela_resolvida,
                'original': tabela,
                'arquivo': arquivo,
                'tipo': self._detectar_tipo_variavel(tabela_resolvida)
            })
        
        # Mapear tabelas para conexões ANTES de filtrar
        tabelas_mapeadas = self.mapear_tabelas_para_conexoes(tabelas_resolvidas)
        
        # Filtrar bases locais
        tabelas_externas = self._filtrar_bases_locais(tabelas_mapeadas)
        
        # Agrupar por tipo
        agrupadas = self._agrupar_por_tipo(tabelas_externas)
        
        return {
            'tabelas': tabelas_resolvidas,
            'tabelas_externas': tabelas_externas,
            'agrupadas': agrupadas,
            'variaveis': self.variaveis
        }
    
    def _extrair_tabelas(self, codigo: str) -> List[str]:
        """Extrai todas as referências a tabelas do código"""
        tabelas = set()
        
        # Padrões para diferentes construções SAS
        padroes = [
            r'from\s+(\S+)',
            r'set\s+(\S+)',
            r'create\s+table\s+(\S+)',
            r'update\s+(\S+)',
            r'insert\s+into\s+(\S+)',
            r'merge\s+(\S+)',
        ]
        
        for padrao in padroes:
            matches = re.finditer(padrao, codigo, re.IGNORECASE)
            for match in matches:
                tabela = match.group(1).strip(';').strip()
                if tabela and not tabela.startswith('('):
                    tabelas.add(tabela)
        
        return list(tabelas)
    
    def _extrair_variaveis_sas(self, codigo: str):
        """Extrai variáveis macro do SAS (%let)"""
        padrao = re.compile(r'%let\s+(\w+)\s*=\s*([^;]+);', re.IGNORECASE)
        matches = padrao.findall(codigo)
        for var, valor in matches:
            self.variaveis[var.upper()] = valor.strip()
    
    def _resolver_variavel(self, tabela: str) -> str:
        """Resolve variáveis SAS em nomes de tabelas"""
        def substituir(match):
            var_name = match.group(1).upper()
            return self.variaveis.get(var_name, match.group(0))
        
        # Resolve &variavel
        resultado = re.sub(r'&(\w+)', substituir, tabela)
        return resultado
    
    def _detectar_tipo_variavel(self, tabela: str) -> str:
        """Detecta o tipo de fonte/schema da tabela"""
        tabela_upper = tabela.upper()
        
        # TERADATA - P_APP_ e P_SDS_ têm prioridade
        if tabela_upper.startswith('P_APP_') or tabela_upper.startswith('P_SDS_'):
            return 'TERADATA'
        
        # ORACLE - P_ genérico (mas não P_APP_ ou P_SDS_)
        if tabela_upper.startswith('P_') and not (tabela_upper.startswith('P_APP_') or tabela_upper.startswith('P_SDS_')):
            return 'ORACLE'
        
        # DATALAKE - REF_, EXP_, LDW
        if any(tabela_upper.startswith(prefix) for prefix in ['REF_', 'EXP_', 'LDW']):
            return 'DATALAKE'
        
        # ORACLE - AG
        if tabela_upper.startswith('AG'):
            return 'ORACLE'
        
        return 'OUTROS'
    
    def _filtrar_bases_locais(self, tabelas: List[Dict]) -> List[Dict]:
        """Filtra tabelas removendo bases locais, mantendo apenas externas"""
        # REF_ e P_SDS_ vão para TABELAS-EXTERNAS, não para BASES
        tabelas_externas = []
        for tabela in tabelas:
            nome_upper = tabela['tabela'].upper()
            # Não considerar como base local se for REF_ ou P_SDS_
            if nome_upper.startswith('REF_') or nome_upper.startswith('P_SDS_'):
                tabelas_externas.append(tabela)
            elif '.' in nome_upper:
                # Tem schema, é externa
                tabelas_externas.append(tabela)
            elif tabela['tipo'] in ['TERADATA', 'ORACLE', 'DATALAKE']:
                # Tipos conhecidos são externos
                tabelas_externas.append(tabela)
        
        return tabelas_externas
    
    def _agrupar_por_tipo(self, tabelas: List[Dict]) -> Dict[str, List[Dict]]:
        """Agrupa tabelas por tipo de conexão"""
        grupos = {
            'TERADATA': [],
            'ORACLE': [],
            'DATALAKE': [],
            'OUTROS': []
        }
        
        for tabela in tabelas:
            tipo = tabela.get('tipo', 'OUTROS')
            grupos[tipo].append(tabela)
        
        return grupos
    
    def mapear_tabelas_para_conexoes(self, tabelas: List[Dict]) -> List[Dict]:
        """Mapeia tabelas para suas conexões correspondentes"""
        # Este método retorna as tabelas com tipo já detectado
        return tabelas
    
    def _detectar_tipo_fonte_schema(self, tabela: str) -> str:
        """Detecta tipo baseado no schema/fonte"""
        # Comentários sobre a detecção:
        # - P_APP_ e P_SDS_ são TERADATA
        # - P_ genérico é ORACLE
        # - REF_, EXP_, LDW são DATALAKE
        # - AG é ORACLE
        return self._detectar_tipo_variavel(tabela)


class DetectorSenhas:
    """Detecta senhas expostas em código SAS"""
    
    def __init__(self):
        self.padroes_senha = [
            re.compile(r'password\s*=\s*["\']?([^"\';\s]+)', re.IGNORECASE),
            re.compile(r'pwd\s*=\s*["\']?([^"\';\s]+)', re.IGNORECASE),
            re.compile(r'senha\s*=\s*["\']?([^"\';\s]+)', re.IGNORECASE),
        ]
    
    def detectar(self, codigo: str, arquivo: str) -> List[Dict]:
        """Detecta senhas expostas no código"""
        senhas_encontradas = []
        
        linhas = codigo.split('\n')
        for num_linha, linha in enumerate(linhas, 1):
            for padrao in self.padroes_senha:
                matches = padrao.finditer(linha)
                for match in matches:
                    senhas_encontradas.append({
                        'arquivo': arquivo,
                        'linha': num_linha,
                        'senha': match.group(1),
                        'contexto': linha.strip()
                    })
        
        return senhas_encontradas


class DetectorTabelasReplicadas:
    """Detecta tabelas que são replicadas em múltiplos scripts"""
    
    def __init__(self):
        self.tabelas_por_arquivo = {}
    
    def adicionar_tabelas(self, arquivo: str, tabelas: List[str]):
        """Adiciona tabelas encontradas em um arquivo"""
        self.tabelas_por_arquivo[arquivo] = tabelas
    
    def detectar_replicadas(self) -> Dict[str, List[str]]:
        """Detecta quais tabelas aparecem em múltiplos arquivos"""
        tabela_arquivos = {}
        
        # Contar em quantos arquivos cada tabela aparece
        for arquivo, tabelas in self.tabelas_por_arquivo.items():
            for tabela in tabelas:
                if tabela not in tabela_arquivos:
                    tabela_arquivos[tabela] = []
                tabela_arquivos[tabela].append(arquivo)
        
        # Filtrar apenas as que aparecem em mais de um arquivo
        replicadas = {
            tabela: arquivos 
            for tabela, arquivos in tabela_arquivos.items() 
            if len(arquivos) > 1
        }
        
        return replicadas


class ServicoExcelPorCaminho:
    """Gera arquivo Excel com todas as análises organizadas em abas"""
    
    def __init__(self, arquivo_saida: str):
        self.arquivo_saida = arquivo_saida
        self.wb = openpyxl.Workbook()
        self.wb.remove(self.wb.active)  # Remove sheet padrão
    
    def criar_excel_completo(self, dados: Dict):
        """Cria todas as abas do Excel com os dados analisados"""
        
        # Aba: Catalogo
        self._criar_aba_catalogo(dados.get('catalogo', []))
        
        # Aba: Conexoes-Externas
        self._criar_aba_conexoes_externas(dados.get('conexoes', {}))
        
        # Aba: Variaveis-Sas
        self._criar_aba_variaveis_sas(dados.get('variaveis', {}))
        
        # Aba: Outros
        self._criar_aba_outros(dados.get('outros', []))
        
        # Aba: Tabelas-Externas
        self._criar_aba_tabelas_externas(dados.get('tabelas_externas', []))
        
        # Aba: Bases
        self._criar_aba_bases(dados.get('bases', []))
        
        # Aba: Tabelas-Replicadas
        self._criar_aba_tabelas_replicadas(dados.get('replicadas', {}))
        
        # Aba: Tabelas-Por-Tipo
        self._criar_aba_tabelas_por_tipo(dados.get('por_tipo', {}))
        
        # Aba: Teradata-Roles
        self._criar_aba_teradata_roles(dados.get('teradata', []))
        
        # Aba: Datalake-Tabelas
        self._criar_aba_datalake_tabelas(dados.get('datalake', []))
        
        # Aba: Oracle-Tabelas
        self._criar_aba_oracle_tabelas(dados.get('oracle', []))
        
        # Aba: Senhas-Expostas
        self._criar_aba_senhas_expostas(dados.get('senhas', []))
        
        # Aba: Resumo
        self._criar_aba_resumo(dados)
        
        # Salvar arquivo
        self.wb.save(self.arquivo_saida)
    
    def _criar_aba_catalogo(self, dados: List[Dict]):
        """Cria aba Catalogo"""
        ws = self.wb.create_sheet("Catalogo")
        self._adicionar_cabecalho(ws, ["Arquivo", "Caminho", "Tabelas", "Conexões"])
        
        for idx, item in enumerate(dados, 2):
            ws[f'A{idx}'] = item.get('arquivo', '')
            ws[f'B{idx}'] = item.get('caminho', '')
            ws[f'C{idx}'] = item.get('num_tabelas', 0)
            ws[f'D{idx}'] = item.get('num_conexoes', 0)
    
    def _criar_aba_conexoes_externas(self, dados: Dict):
        """Cria aba Conexoes-Externas"""
        ws = self.wb.create_sheet("Conexoes-Externas")
        self._adicionar_cabecalho(ws, ["Tipo", "Conexão", "Arquivos"])
        
        idx = 2
        for tipo, conexoes in dados.items():
            for conexao in conexoes:
                ws[f'A{idx}'] = tipo
                ws[f'B{idx}'] = conexao.get('nome', '')
                ws[f'C{idx}'] = ', '.join(conexao.get('arquivos', []))
                idx += 1
    
    def _criar_aba_variaveis_sas(self, dados: Dict):
        """Cria aba Variaveis-Sas"""
        ws = self.wb.create_sheet("Variaveis-Sas")
        self._adicionar_cabecalho(ws, ["Variável", "Valor", "Arquivos"])
        
        idx = 2
        for var, valor in dados.items():
            ws[f'A{idx}'] = var
            ws[f'B{idx}'] = valor
            ws[f'C{idx}'] = ''  # Lista de arquivos pode ser adicionada
            idx += 1
    
    def _criar_aba_outros(self, dados: List[Dict]):
        """Cria aba Outros"""
        ws = self.wb.create_sheet("Outros")
        self._adicionar_cabecalho(ws, ["Tipo", "Descrição", "Arquivo", "Linha"])
        
        for idx, item in enumerate(dados, 2):
            ws[f'A{idx}'] = item.get('tipo', '')
            ws[f'B{idx}'] = item.get('descricao', '')
            ws[f'C{idx}'] = item.get('arquivo', '')
            ws[f'D{idx}'] = item.get('linha', '')
    
    def _criar_aba_tabelas_externas(self, dados: List[Dict]):
        """Cria aba Tabelas-Externas"""
        ws = self.wb.create_sheet("Tabelas-Externas")
        self._adicionar_cabecalho(ws, ["Tabela", "Tipo", "Arquivo", "Schema"])
        
        for idx, item in enumerate(dados, 2):
            ws[f'A{idx}'] = item.get('tabela', '')
            ws[f'B{idx}'] = item.get('tipo', '')
            ws[f'C{idx}'] = item.get('arquivo', '')
            schema = item.get('tabela', '').split('.')[0] if '.' in item.get('tabela', '') else ''
            ws[f'D{idx}'] = schema
    
    def _criar_aba_bases(self, dados: List[Dict]):
        """Cria aba Bases"""
        ws = self.wb.create_sheet("Bases")
        self._adicionar_cabecalho(ws, ["Base", "Tipo", "Arquivos", "Quantidade"])
        
        for idx, item in enumerate(dados, 2):
            ws[f'A{idx}'] = item.get('base', '')
            ws[f'B{idx}'] = item.get('tipo', '')
            ws[f'C{idx}'] = ', '.join(item.get('arquivos', []))
            ws[f'D{idx}'] = len(item.get('arquivos', []))
    
    def _criar_aba_tabelas_replicadas(self, dados: Dict):
        """Cria aba Tabelas-Replicadas"""
        ws = self.wb.create_sheet("Tabelas-Replicadas")
        self._adicionar_cabecalho(ws, ["Tabela", "Quantidade", "Arquivos"])
        
        idx = 2
        for tabela, arquivos in dados.items():
            ws[f'A{idx}'] = tabela
            ws[f'B{idx}'] = len(arquivos)
            ws[f'C{idx}'] = ', '.join(arquivos)
            idx += 1
    
    def _criar_aba_tabelas_por_tipo(self, dados: Dict):
        """Cria aba Tabelas-Por-Tipo"""
        ws = self.wb.create_sheet("Tabelas-Por-Tipo")
        self._adicionar_cabecalho(ws, ["Tipo", "Tabela", "Arquivo"])
        
        idx = 2
        for tipo, tabelas in dados.items():
            for tabela in tabelas:
                ws[f'A{idx}'] = tipo
                ws[f'B{idx}'] = tabela.get('tabela', '')
                ws[f'C{idx}'] = tabela.get('arquivo', '')
                idx += 1
    
    def _criar_aba_teradata_roles(self, dados: List[Dict]):
        """Cria aba Teradata-Roles"""
        ws = self.wb.create_sheet("Teradata-Roles")
        self._adicionar_cabecalho(ws, ["Role", "Tabelas", "Arquivos"])
        
        for idx, item in enumerate(dados, 2):
            ws[f'A{idx}'] = item.get('role', '')
            ws[f'B{idx}'] = ', '.join(item.get('tabelas', []))
            ws[f'C{idx}'] = ', '.join(item.get('arquivos', []))
    
    def _criar_aba_datalake_tabelas(self, dados: List[Dict]):
        """Cria aba Datalake-Tabelas"""
        ws = self.wb.create_sheet("Datalake-Tabelas")
        self._adicionar_cabecalho(ws, ["Tabela", "Prefixo", "Arquivo"])
        
        for idx, item in enumerate(dados, 2):
            ws[f'A{idx}'] = item.get('tabela', '')
            ws[f'B{idx}'] = item.get('prefixo', '')
            ws[f'C{idx}'] = item.get('arquivo', '')
    
    def _criar_aba_oracle_tabelas(self, dados: List[Dict]):
        """Cria aba Oracle-Tabelas"""
        ws = self.wb.create_sheet("Oracle-Tabelas")
        self._adicionar_cabecalho(ws, ["Tabela", "Schema", "Arquivo"])
        
        for idx, item in enumerate(dados, 2):
            ws[f'A{idx}'] = item.get('tabela', '')
            ws[f'B{idx}'] = item.get('schema', '')
            ws[f'C{idx}'] = item.get('arquivo', '')
    
    def _criar_aba_senhas_expostas(self, dados: List[Dict]):
        """Cria aba Senhas-Expostas"""
        ws = self.wb.create_sheet("Senhas-Expostas")
        self._adicionar_cabecalho(ws, ["Arquivo", "Linha", "Contexto", "Severidade"])
        
        for idx, item in enumerate(dados, 2):
            ws[f'A{idx}'] = item.get('arquivo', '')
            ws[f'B{idx}'] = item.get('linha', '')
            ws[f'C{idx}'] = item.get('contexto', '')
            ws[f'D{idx}'] = 'CRÍTICA'
    
    def _criar_aba_resumo(self, dados: Dict):
        """Cria aba Resumo"""
        ws = self.wb.create_sheet("Resumo")
        self._adicionar_cabecalho(ws, ["Métrica", "Valor"])
        
        metricas = [
            ("Total de Arquivos", len(dados.get('catalogo', []))),
            ("Total de Tabelas", sum(len(v) for v in dados.get('por_tipo', {}).values())),
            ("Tabelas TERADATA", len(dados.get('teradata', []))),
            ("Tabelas ORACLE", len(dados.get('oracle', []))),
            ("Tabelas DATALAKE", len(dados.get('datalake', []))),
            ("Tabelas Replicadas", len(dados.get('replicadas', {}))),
            ("Senhas Expostas", len(dados.get('senhas', []))),
            ("Conexões Externas", sum(len(v) for v in dados.get('conexoes', {}).values())),
        ]
        
        for idx, (metrica, valor) in enumerate(metricas, 2):
            ws[f'A{idx}'] = metrica
            ws[f'B{idx}'] = valor
    
    def _adicionar_cabecalho(self, ws, colunas: List[str]):
        """Adiciona cabeçalho formatado a uma planilha"""
        fonte_negrito = Font(bold=True)
        fundo_cinza = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
        
        for idx, coluna in enumerate(colunas, 1):
            celula = ws.cell(row=1, column=idx)
            celula.value = coluna
            celula.font = fonte_negrito
            celula.fill = fundo_cinza
            celula.alignment = Alignment(horizontal='center')


def scan_caminho(caminho: str, conector_ftp=None) -> Dict:
    """Escaneia um caminho (local ou FTP) e analisa todos os arquivos SAS"""
    
    analisador = AnalisadorSAS()
    extrator = EtratorConexoes()
    detector_senhas = DetectorSenhas()
    detector_replicadas = DetectorTabelasReplicadas()
    
    resultados = {
        'catalogo': [],
        'conexoes': {},
        'variaveis': {},
        'outros': [],
        'tabelas_externas': [],
        'bases': [],
        'replicadas': {},
        'por_tipo': {},
        'teradata': [],
        'datalake': [],
        'oracle': [],
        'senhas': []
    }
    
    # Se for caminho local
    if not conector_ftp:
        caminho_obj = Path(caminho)
        if not caminho_obj.exists():
            print(f"Caminho não encontrado: {caminho}")
            return resultados
        
        arquivos_sas = list(caminho_obj.rglob("*.sas"))
        
        for arquivo in arquivos_sas:
            try:
                with open(arquivo, 'r', encoding='utf-8', errors='ignore') as f:
                    codigo = f.read()
                
                # Processar arquivo
                resultado = _processar_arquivo_sas(
                    str(arquivo), codigo, analisador, extrator, 
                    detector_senhas, detector_replicadas
                )
                
                # Agregar resultados
                _agregar_resultados(resultados, resultado)
                
            except Exception as e:
                print(f"Erro ao processar {arquivo}: {e}")
    
    # Se for FTP
    else:
        arquivos_sas = conector_ftp.listar_arquivos(caminho)
        
        for arquivo in arquivos_sas:
            try:
                caminho_completo = f"{caminho}/{arquivo}"
                codigo = conector_ftp.ler_arquivo(caminho_completo)
                
                # Processar arquivo
                resultado = _processar_arquivo_sas(
                    arquivo, codigo, analisador, extrator,
                    detector_senhas, detector_replicadas
                )
                
                # Agregar resultados
                _agregar_resultados(resultados, resultado)
                
            except Exception as e:
                print(f"Erro ao processar {arquivo}: {e}")
    
    # Detectar tabelas replicadas
    resultados['replicadas'] = detector_replicadas.detectar_replicadas()
    
    return resultados


def _processar_arquivo_sas(arquivo: str, codigo: str, analisador, extrator,
                            detector_senhas, detector_replicadas) -> Dict:
    """Processa um único arquivo SAS"""
    
    # Análise básica
    analise = analisador.analisar_codigo(codigo)
    
    # Extração de conexões e tabelas
    processamento = extrator.processar_codigo(codigo, arquivo)
    
    # Detectar senhas
    senhas = detector_senhas.detectar(codigo, arquivo)
    
    # Adicionar tabelas ao detector de replicadas
    tabelas_nomes = [t['tabela'] for t in processamento['tabelas']]
    detector_replicadas.adicionar_tabelas(arquivo, tabelas_nomes)
    
    return {
        'arquivo': arquivo,
        'analise': analise,
        'processamento': processamento,
        'senhas': senhas
    }


def _agregar_resultados(resultados: Dict, resultado: Dict):
    """Agrega resultados de um arquivo ao resultado geral"""
    
    arquivo = resultado['arquivo']
    processamento = resultado['processamento']
    
    # Catálogo
    resultados['catalogo'].append({
        'arquivo': arquivo,
        'caminho': arquivo,
        'num_tabelas': len(processamento['tabelas']),
        'num_conexoes': len(resultado['analise']['conexoes'])
    })
    
    # Variáveis
    resultados['variaveis'].update(processamento['variaveis'])
    
    # Tabelas externas
    resultados['tabelas_externas'].extend(processamento['tabelas_externas'])
    
    # Agrupar por tipo
    for tipo, tabelas in processamento['agrupadas'].items():
        if tipo not in resultados['por_tipo']:
            resultados['por_tipo'][tipo] = []
        resultados['por_tipo'][tipo].extend(tabelas)
    
    # Separar por banco
    for tabela in processamento['tabelas_externas']:
        tipo = tabela.get('tipo', 'OUTROS')
        if tipo == 'TERADATA':
            resultados['teradata'].append(tabela)
        elif tipo == 'ORACLE':
            resultados['oracle'].append(tabela)
        elif tipo == 'DATALAKE':
            resultados['datalake'].append(tabela)
    
    # Senhas
    resultados['senhas'].extend(resultado['senhas'])


def diagnosticar_ftp(host: str, usuario: str, senha: str, porta: int = 21) -> Dict:
    """Diagnostica conexão FTP e retorna informações"""
    
    diagnostico = {
        'conectado': False,
        'erro': None,
        'diretorios': [],
        'arquivos_sas': 0
    }
    
    conector = ConectorFTP(host, usuario, senha, porta)
    
    try:
        if conector.conectar():
            diagnostico['conectado'] = True
            
            # Tentar listar diretório raiz
            try:
                ftp = conector.ftp
                items = ftp.nlst()
                diagnostico['diretorios'] = items
                
                # Contar arquivos .sas
                for item in items:
                    try:
                        arquivos = conector.listar_arquivos(item, ".sas")
                        diagnostico['arquivos_sas'] += len(arquivos)
                    except:
                        pass
                
            except Exception as e:
                diagnostico['erro'] = f"Erro ao listar diretórios: {e}"
            
            conector.desconectar()
        else:
            diagnostico['erro'] = "Falha na conexão"
    
    except Exception as e:
        diagnostico['erro'] = str(e)
    
    return diagnostico


def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analisador SAS FTP')
    parser.add_argument('--caminho', required=True, help='Caminho local ou FTP para análise')
    parser.add_argument('--ftp-host', help='Host FTP')
    parser.add_argument('--ftp-usuario', help='Usuário FTP')
    parser.add_argument('--ftp-senha', help='Senha FTP')
    parser.add_argument('--ftp-porta', type=int, default=21, help='Porta FTP')
    parser.add_argument('--output', default='analise_sas.xlsx', help='Arquivo Excel de saída')
    parser.add_argument('--diagnostico', action='store_true', help='Executar diagnóstico FTP')
    
    args = parser.parse_args()
    
    # Diagnóstico FTP
    if args.diagnostico and args.ftp_host:
        print("Executando diagnóstico FTP...")
        diag = diagnosticar_ftp(args.ftp_host, args.ftp_usuario, args.ftp_senha, args.ftp_porta)
        print(f"Conectado: {diag['conectado']}")
        print(f"Diretórios encontrados: {len(diag['diretorios'])}")
        print(f"Arquivos SAS encontrados: {diag['arquivos_sas']}")
        if diag['erro']:
            print(f"Erro: {diag['erro']}")
        return
    
    # Análise de código
    print(f"Analisando caminho: {args.caminho}")
    
    conector_ftp = None
    if args.ftp_host:
        print("Conectando ao FTP...")
        conector_ftp = ConectorFTP(args.ftp_host, args.ftp_usuario, args.ftp_senha, args.ftp_porta)
        if not conector_ftp.conectar():
            print("Erro ao conectar ao FTP!")
            return
    
    # Escanear e analisar
    print("Escaneando arquivos...")
    resultados = scan_caminho(args.caminho, conector_ftp)
    
    # Gerar Excel
    print(f"Gerando relatório Excel: {args.output}")
    servico_excel = ServicoExcelPorCaminho(args.output)
    servico_excel.criar_excel_completo(resultados)
    
    # Resumo
    print("\n=== RESUMO ===")
    print(f"Arquivos analisados: {len(resultados['catalogo'])}")
    print(f"Tabelas encontradas: {sum(len(v) for v in resultados['por_tipo'].values())}")
    print(f"Tabelas TERADATA: {len(resultados['teradata'])}")
    print(f"Tabelas ORACLE: {len(resultados['oracle'])}")
    print(f"Tabelas DATALAKE: {len(resultados['datalake'])}")
    print(f"Tabelas replicadas: {len(resultados['replicadas'])}")
    print(f"Senhas expostas: {len(resultados['senhas'])}")
    
    if conector_ftp:
        conector_ftp.desconectar()
    
    print(f"\nRelatório gerado com sucesso: {args.output}")


if __name__ == "__main__":
    main()
