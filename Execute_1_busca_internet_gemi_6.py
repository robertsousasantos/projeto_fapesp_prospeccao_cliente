#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrator FAPESP - Versão Funcional Completa
Com batch configurável e formato de saída específico
"""

import json
import os
import sys
import time
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging
import re

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suprimir warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['PYTHONWARNINGS'] = 'ignore'

def configurar_api_key():
    """Configura a API key do Gemini"""
    api_key = ''
    os.environ['GOOGLE_API_KEY'] = api_key
    print("✅ API Key configurada")
    return True

# Importar dependências
try:
    import google.generativeai as genai
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        WEBDRIVER_MANAGER_OK = True
    except ImportError:
        WEBDRIVER_MANAGER_OK = False
        
except ImportError as e:
    print(f"❌ Erro: {e}")
    print("Execute: pip install google-generativeai selenium pandas webdriver-manager")
    sys.exit(1)

# Configurações
CONFIG = {
    'PASTA_NOMES': Path("/home/phelipe/Documentos/Scrips_projeto_FAPES_PHELIPE/Olho_de_ferro/Passo_1_Lista_nomes_cvs"), #entrada dos arquivos
'PASTA_RESULTADOS': Path("/home/phelipe/Documentos/Scrips_projeto_FAPES_PHELIPE/Olho_de_ferro/Passo_2_json_extraido"), #saida dos arquivos
    'TIMEOUT_SELENIUM': 20,
    'DELAY_ENTRE_REQUESTS': 3,
    'MAX_TENTATIVAS': 3
}

# Modelos Gemini - EXPANDIDO
MODELOS_GEMINI = {
    '1': {'name': 'gemini-1.5-flash', 'display': 'Gemini 1.5 Flash (Recomendado)', 'temperature': 0.1},
    '2': {'name': 'gemini-1.5-pro', 'display': 'Gemini 1.5 Pro (Mais inteligente)', 'temperature': 0.1},
    '3': {'name': 'gemini-1.0-pro', 'display': 'Gemini 1.0 Pro (Estável)', 'temperature': 0.2},
    '4': {'name': 'gemini-2.0-flash-exp', 'display': 'Gemini 2.0 Flash (Experimental)', 'temperature': 0.1},
    '5': {'name': 'gemini-2.5-flash-exp', 'display': 'Gemini 2.5 Flash (Experimental)', 'temperature': 0.1}
}

# Campos CSV completos
CAMPOS_CSV = [
    'nome_completo', 'resumo_academico_completo', 'formacao_academica',
    'titulacao_atual', 'instituicao_vinculo', 'laboratorios_pesquisa',
    'linhas_pesquisa', 'palavras_chave', 'projetos_pesquisa',
    'historico_bolsas', 'colaboracoes_internacionais', 'producao_cientifica_destacada',
    'cargo_atual', 'empresa_startup', 'areas_especializacao', 'tecnicas_utilizadas',
    'url_lattes', 'url_fapesp', 'orcid', 'email_contato', 'pais_origem',
    'bv_numeros_auxilios_contratados', 'bv_numeros_auxilios_concluidos', 
    'bv_numeros_bolsas_concluidas', 'bv_numeros_total_processos',
    'colaboradores_frequentes', 'auxilios_pesquisa_contratados', 'auxilios_pesquisa_concluidos',
    'bolsas_concluidas', 'materias_agencia_fapesp', 'materias_outras_midias',
    'palavras_chave_detalhadas', 'publicacoes_resultantes', 'processos_fapesp',
    'status_processamento', 'modo_processamento'
]

class ExtratorFAPESP:
    """Extrator FAPESP com batch configurável"""
    
    def __init__(self):
        self.pasta_resultados = CONFIG['PASTA_RESULTADOS']
        self.pasta_nomes = CONFIG['PASTA_NOMES']
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.driver = None
        self.modelo_gemini = None
        self.wait = None
        self.criar_pastas()
        
    def criar_pastas(self):
        """Cria pastas necessárias"""
        for pasta in [self.pasta_resultados, self.pasta_nomes]:
            pasta.mkdir(parents=True, exist_ok=True)
            print(f"📁 Pasta verificada: {pasta}")
    
    def mostrar_banner(self):
        """Banner do aplicativo"""
        print("=" * 70)
        print("🔬 EXTRATOR FAPESP GEMINI - VERSÃO FUNCIONAL COMPLETA")
        print("⚡ Batch configurável (3-10 pesquisadores)")
        print("🤖 Modelos Gemini 2.0 e 2.5 incluídos")
        print("📋 Formato de saída completo e detalhado")
        print("🌐 Fonte: https://bv.fapesp.br")
        print(f"📁 Resultados: {self.pasta_resultados}")
        print("=" * 70)
        print()
    
    def selecionar_modelo(self):
        """Seleção de modelo"""
        print("\n🤖 MODELOS GEMINI DISPONÍVEIS:")
        print("-" * 60)
        
        for key, modelo in MODELOS_GEMINI.items():
            print(f"{key}. {modelo['display']}")
        
        while True:
            escolha = input("\nEscolha o modelo (1-5) [1]: ").strip() or "1"
            if escolha in MODELOS_GEMINI:
                modelo_info = MODELOS_GEMINI[escolha]
                print(f"✅ Selecionado: {modelo_info['display']}")
                return modelo_info
            print("❌ Opção inválida!")
    
    def obter_configuracao(self):
        """Obtém configuração completa"""
        print("\n🔧 CONFIGURAÇÃO DE PROCESSAMENTO")
        print("-" * 40)
        print("1. 📝 Nome único (individual)")
        print("2. 📊 Lista de exemplo (individual)")
        print("3. 📁 Carregar CSV (individual)")
        print("4. ⚡ Carregar CSV (BATCH OTIMIZADO)")
        
        while True:
            opcao = input("\nEscolha a opção (1-4) [4]: ").strip() or "4"
            
            if opcao == "1":
                nome = input("Nome do pesquisador: ").strip()
                if nome:
                    return {
                        'nomes': [nome],
                        'batch_otimizado': False,
                        'batch_size': 1
                    }
                print("❌ Nome não pode estar vazio")
                
            elif opcao == "2":
                nomes = ["Mona das Neves Oliveira", "Phelipe Augusto Mariano Vitale"]
                print(f"✅ Usando {len(nomes)} nomes de exemplo")
                return {
                    'nomes': nomes,
                    'batch_otimizado': False,
                    'batch_size': 1
                }
                
            elif opcao == "3":
                nomes = self.carregar_csv()
                if nomes:
                    return {
                        'nomes': nomes,
                        'batch_otimizado': False,
                        'batch_size': 1
                    }
                    
            elif opcao == "4":
                nomes = self.carregar_csv()
                if nomes:
                    batch_size = self.configurar_batch_size()
                    print("\n⚡ MODO BATCH OTIMIZADO ATIVADO")
                    print(f"🔥 {batch_size} pesquisadores por chamada Gemini")
                    print("💰 Economia de 70-80% nos tokens")
                    return {
                        'nomes': nomes,
                        'batch_otimizado': True,
                        'batch_size': batch_size
                    }
                    
            else:
                print("❌ Opção inválida!")
    
    def configurar_batch_size(self):
        """Configura tamanho do batch"""
        print("\n⚡ CONFIGURAÇÃO DO BATCH SIZE")
        print("-" * 35)
        print("Escolha quantos pesquisadores processar por vez:")
        print("• 3-5: Recomendado para modelos básicos")
        print("• 6-8: Para modelos mais robustos")
        print("• 9-10: Para modelos experimentais")
        
        while True:
            try:
                batch_size = input("Batch size (3-10) [5]: ").strip() or "5"
                batch_size = int(batch_size)
                
                if 3 <= batch_size <= 10:
                    print(f"✅ Batch size: {batch_size} pesquisadores")
                    return batch_size
                else:
                    print("❌ Digite um número entre 3 e 10")
            except ValueError:
                print("❌ Digite um número válido")
    
    def carregar_csv(self):
        """Carrega nomes de arquivo CSV"""
        try:
            arquivos_csv = list(self.pasta_nomes.glob("*.csv"))
            
            if not arquivos_csv:
                print("❌ Nenhum arquivo CSV encontrado")
                print(f"📁 Coloque arquivos CSV em: {self.pasta_nomes}")
                
                # Criar exemplo
                resposta = input("Criar arquivo CSV de exemplo? (s/N): ").lower()
                if resposta in ['s', 'sim', 'y', 'yes']:
                    return self.criar_csv_exemplo()
                return None
            
            print(f"\n📁 {len(arquivos_csv)} arquivo(s) CSV encontrado(s):")
            for i, arquivo in enumerate(arquivos_csv, 1):
                print(f"   {i}. {arquivo.name}")
            
            while True:
                try:
                    escolha = int(input(f"\nEscolha o arquivo (1-{len(arquivos_csv)}): "))
                    if 1 <= escolha <= len(arquivos_csv):
                        arquivo_selecionado = arquivos_csv[escolha - 1]
                        return self.ler_csv(arquivo_selecionado)
                    else:
                        print("❌ Número inválido!")
                except ValueError:
                    print("❌ Digite um número válido!")
                    
        except Exception as e:
            print(f"❌ Erro ao carregar CSV: {e}")
            return None
    
    def criar_csv_exemplo(self):
        """Cria arquivo CSV de exemplo"""
        try:
            nomes_exemplo = [
                "Mona das Neves Oliveira",
                "Phelipe Augusto Mariano Vitale",
                "Carlos Eduardo Silva",
                "Ana Paula Santos",
                "Roberto Mendes Junior"
            ]
            
            arquivo_csv = self.pasta_nomes / f"pesquisadores_exemplo_{self.timestamp}.csv"
            df = pd.DataFrame({'nome': nomes_exemplo})
            df.to_csv(arquivo_csv, index=False, encoding='utf-8')
            
            print(f"✅ Arquivo exemplo criado: {arquivo_csv.name}")
            print(f"📊 {len(nomes_exemplo)} nomes incluídos")
            return nomes_exemplo
            
        except Exception as e:
            print(f"❌ Erro ao criar exemplo: {e}")
            return None
    
    def ler_csv(self, arquivo_csv):
        """Lê nomes do arquivo CSV"""
        try:
            df = pd.read_csv(arquivo_csv, encoding='utf-8')
            
            # Procurar coluna com nomes
            colunas_nomes = ['nome', 'name', 'pesquisador', 'researcher', 'Nome', 'Name']
            coluna_encontrada = None
            
            for col in colunas_nomes:
                if col in df.columns:
                    coluna_encontrada = col
                    break
            
            if coluna_encontrada:
                nomes = df[coluna_encontrada].dropna().astype(str).tolist()
                nomes = [nome.strip() for nome in nomes if nome.strip()]
                print(f"✅ {len(nomes)} nomes carregados de {arquivo_csv.name}")
                return nomes
            else:
                print(f"❌ Colunas disponíveis: {list(df.columns)}")
                print("❌ Nenhuma coluna de nomes encontrada")
                return None
                
        except Exception as e:
            print(f"❌ Erro ao ler CSV: {e}")
            return None
    
    def inicializar_selenium(self, headless=True):
        """Inicializa Selenium"""
        try:
            print("🔄 Inicializando Selenium...")
            
            options = Options()
            if headless:
                options.add_argument('--headless=new')
            
            # Configurações essenciais
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Tentar diferentes métodos
            if WEBDRIVER_MANAGER_OK:
                try:
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=options)
                    print("✅ Selenium inicializado com WebDriver Manager")
                except Exception:
                    self.driver = webdriver.Chrome(options=options)
                    print("✅ Selenium inicializado (método direto)")
            else:
                self.driver = webdriver.Chrome(options=options)
                print("✅ Selenium inicializado (método direto)")
            
            self.wait = WebDriverWait(self.driver, CONFIG['TIMEOUT_SELENIUM'])
            
            # Teste básico
            self.driver.get("https://www.google.com")
            time.sleep(2)
            print("✅ Teste de navegação OK")
            return True
            
        except Exception as e:
            print(f"❌ Erro no Selenium: {e}")
            return False
    
    def inicializar_gemini(self, modelo_info):
        """Inicializa Gemini"""
        try:
            print(f"🔄 Inicializando {modelo_info['display']}...")
            genai.configure(api_key=os.environ['GOOGLE_API_KEY'])
            
            self.modelo_gemini = genai.GenerativeModel(
                modelo_info['name'],
                generation_config=genai.types.GenerationConfig(
                    temperature=modelo_info['temperature']
                )
            )
            
            # Teste básico
            response = self.modelo_gemini.generate_content("Teste: responda apenas 'OK'")
            if response and response.text:
                print("✅ Gemini inicializado e testado")
                return True
            else:
                print("❌ Gemini não respondeu ao teste")
                return False
                
        except Exception as e:
            print(f"❌ Erro no Gemini: {e}")
            return False
    
    def buscar_pesquisador(self, nome):
        """Busca pesquisador na FAPESP"""
        try:
            print(f"🔍 Buscando: {nome}")
            
            self.driver.get("https://bv.fapesp.br")
            time.sleep(3)
            
            # Procurar campo de busca
            seletores = ['input[type="search"]', 'input[name="q"]', '#search']
            campo_busca = None
            
            for seletor in seletores:
                try:
                    campo_busca = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor)))
                    break
                except TimeoutException:
                    continue
            
            if not campo_busca:
                print("❌ Campo de busca não encontrado")
                return None
            
            # Realizar busca
            campo_busca.clear()
            campo_busca.send_keys(nome)
            campo_busca.send_keys(Keys.RETURN)
            time.sleep(4)
            
            # Procurar resultado
            links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/pesquisador/"]')
            
            if links:
                url = links[0].get_attribute('href')
                print(f"✅ Encontrado: {url}")
                return url
            else:
                print(f"❌ Não encontrado: {nome}")
                return None
                
        except Exception as e:
            print(f"❌ Erro na busca: {e}")
            return None
    
    def extrair_dados_pagina(self, url):
        """Extrai dados da página"""
        try:
            print(f"📄 Extraindo: {url}")
            
            self.driver.get(url)
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            time.sleep(3)
            
            conteudo = self.driver.find_element(By.TAG_NAME, 'body').text
            print(f"✅ {len(conteudo)} caracteres extraídos")
            return conteudo
            
        except Exception as e:
            print(f"❌ Erro na extração: {e}")
            return None
    
    def processar_individual_gemini(self, conteudo, nome_pesquisador):
        """Processa com Gemini - FORMATO EXATO ESPECIFICADO"""
        try:
            print(f"🤖 Processando {nome_pesquisador} com Gemini...")
            
            prompt = f"""Você é um especialista em extrair informações acadêmicas detalhadas de páginas da FAPESP. 

PESQUISADOR: {nome_pesquisador}

INSTRUÇÕES CRÍTICAS - LEIA ATENTAMENTE:
1. Procure por um parágrafo biográfico longo que começa com formação acadêmica (ex: "Doutor em ciências pelo Instituto...")
2. Este parágrafo DEVE ser copiado INTEGRALMENTE no campo "Resumo Academico Completo"
3. NÃO RESUMIR, NÃO CORTAR, NÃO PARAFRASEAR - copie palavra por palavra
4. Incluir também "(Fonte: Currículo Lattes)" se presente
5. Para outros campos, extrair todas as informações disponíveis
6. Para campos não encontrados, usar "Não encontrado"

ATENÇÃO ESPECIAL: O texto biográfico principal (que geralmente é longo e detalhado) deve aparecer COMPLETO no campo "Resumo Academico Completo". Este é o texto mais importante da página.

FORMATO DE SAÍDA OBRIGATÓRIO:

Nome Completo: [nome completo do pesquisador]
Resumo Academico Completo: [TEXTO BIOGRÁFICO COMPLETO - COPIAR INTEGRALMENTE sem resumir, incluindo todos os detalhes sobre formação, experiência, bolsas, projetos, startup, etc. Este deve ser o texto mais longo da extração]
Formacao Academica: [graduação, mestrado, doutorado, pós-doutorado com detalhes]
Titulacao Atual: [título/cargo acadêmico atual]
Instituicao Vinculo: [universidade/instituição de vínculo]
Laboratorios Pesquisa: [laboratórios onde atua com detalhes]
Linhas Pesquisa: [áreas de pesquisa detalhadas]
Palavras Chave: [TODAS as palavras-chave listadas na página]
Projetos Pesquisa: [projetos em andamento ou concluídos com detalhes]
Historico Bolsas: [TODAS as bolsas mencionadas com datas e detalhes]
Colaboracoes Internacionais: [parcerias internacionais]
Producao Cientifica Destacada: [principais publicações com detalhes]
Cargo Atual: [cargo/posição atual]
Empresa Startup: [empresas ou startups vinculadas - ex: BIOLINKER]
Areas Especializacao: [áreas de especialização]
Tecnicas Utilizadas: [técnicas e métodos de pesquisa]
Url Lattes: [link do currículo Lattes]
Url Fapesp: [link do perfil FAPESP]
Orcid: [ID ORCID completo]
Email Contato: [email de contato]
Pais Origem: [país de origem]
BV Numeros Auxilios Contratados: [número de auxílios contratados]
BV Numeros Auxilios Concluidos: [número de auxílios concluídos]  
BV Numeros Bolsas Concluidas: [número de bolsas concluídas]
BV Numeros Total Processos: [total de auxílios e bolsas]
Colaboradores Frequentes: [lista de colaboradores mais frequentes]
Auxilios Pesquisa Contratados: [lista detalhada de auxílios contratados recentes]
Auxilios Pesquisa Concluidos: [lista detalhada de auxílios concluídos]
Bolsas Concluidas: [lista detalhada de bolsas concluídas]
Materias Agencia FAPESP: [matérias publicadas na Agência FAPESP]
Materias Outras Midias: [matérias em outras mídias]
Palavras Chave Detalhadas: [todas as palavras-chave com frequência de uso]
Publicacoes Resultantes: [número e detalhes de publicações]
Processos FAPESP: [números de processos específicos mencionados]

LEMBRE-SE: O campo "Resumo Academico Completo" deve conter o texto biográfico INTEGRAL, que é o conteúdo mais valioso da página.

TEXTO DA PÁGINA:
{conteudo[:10000]}"""

            response = self.modelo_gemini.generate_content(prompt)
            
            if response and response.text:
                print("✅ Gemini processou com sucesso")
                return response.text
            else:
                print("❌ Gemini retornou resposta vazia")
                return None
                
        except Exception as e:
            print(f"❌ Erro no Gemini: {e}")
            return None
    
    def processar_batch_gemini(self, dados_batch):
        """Processa batch com Gemini - FORMATO EXATO ESPECIFICADO"""
        try:
            print(f"🤖 Processando batch de {len(dados_batch)} pesquisadores...")
            
            prompt = f"""Você é um especialista em extrair informações acadêmicas detalhadas de páginas da FAPESP. 

INSTRUÇÕES CRÍTICAS - LEIA ATENTAMENTE:
1. Procure por um parágrafo biográfico longo que começa com formação acadêmica (ex: "Doutor em ciências pelo Instituto...")
2. Este parágrafo DEVE ser copiado INTEGRALMENTE no campo "Resumo Academico Completo"
3. NÃO RESUMIR, NÃO CORTAR, NÃO PARAFRASEAR - copie palavra por palavra
4. Incluir também "(Fonte: Currículo Lattes)" se presente
5. Para outros campos, extrair todas as informações disponíveis
6. Para campos não encontrados, usar "Não encontrado"

ATENÇÃO ESPECIAL: O texto biográfico principal (que geralmente é longo e detalhado) deve aparecer COMPLETO no campo "Resumo Academico Completo". Este é o texto mais importante da página.

PROCESSE TODOS OS {len(dados_batch)} PESQUISADORES fornecidos abaixo.

FORMATO DE SAÍDA OBRIGATÓRIO - Para cada pesquisador:

=== PESQUISADOR [NUMERO] ===
Nome Completo: [nome completo do pesquisador]
Resumo Academico Completo: [TEXTO BIOGRÁFICO COMPLETO - COPIAR INTEGRALMENTE sem resumir, incluindo todos os detalhes sobre formação, experiência, bolsas, projetos, startup, etc. Este deve ser o texto mais longo da extração]
Formacao Academica: [graduação, mestrado, doutorado, pós-doutorado com detalhes]
Titulacao Atual: [título/cargo acadêmico atual]
Instituicao Vinculo: [universidade/instituição de vínculo]
Laboratorios Pesquisa: [laboratórios onde atua com detalhes]
Linhas Pesquisa: [áreas de pesquisa detalhadas]
Palavras Chave: [TODAS as palavras-chave listadas na página]
Projetos Pesquisa: [projetos em andamento ou concluídos com detalhes]
Historico Bolsas: [TODAS as bolsas mencionadas com datas e detalhes]
Colaboracoes Internacionais: [parcerias internacionais]
Producao Cientifica Destacada: [principais publicações com detalhes]
Cargo Atual: [cargo/posição atual]
Empresa Startup: [empresas ou startups vinculadas - ex: BIOLINKER]
Areas Especializacao: [áreas de especialização]
Tecnicas Utilizadas: [técnicas e métodos de pesquisa]
Url Lattes: [link do currículo Lattes]
Url Fapesp: [link do perfil FAPESP]
Orcid: [ID ORCID completo]
Email Contato: [email de contato]
Pais Origem: [país de origem]
BV Numeros Auxilios Contratados: [número de auxílios contratados]
BV Numeros Auxilios Concluidos: [número de auxílios concluídos]  
BV Numeros Bolsas Concluidas: [número de bolsas concluídas]
BV Numeros Total Processos: [total de auxílios e bolsas]
Colaboradores Frequentes: [lista de colaboradores mais frequentes]
Auxilios Pesquisa Contratados: [lista detalhada de auxílios contratados recentes]
Auxilios Pesquisa Concluidos: [lista detalhada de auxílios concluídos]
Bolsas Concluidas: [lista detalhada de bolsas concluídas]
Materias Agencia FAPESP: [matérias publicadas na Agência FAPESP]
Materias Outras Midias: [matérias em outras mídias]
Palavras Chave Detalhadas: [todas as palavras-chave com frequência de uso]
Publicacoes Resultantes: [número e detalhes de publicações]
Processos FAPESP: [números de processos específicos mencionados]

LEMBRE-SE: O campo "Resumo Academico Completo" deve conter o texto biográfico INTEGRAL, que é o conteúdo mais valioso da página.

DADOS DOS PESQUISADORES:
"""
            
            for i, dados in enumerate(dados_batch, 1):
                prompt += f"\n--- PESQUISADOR {i}: {dados['nome']} ---\n"
                prompt += f"URL: {dados['url']}\n"
                prompt += f"TEXTO DA PÁGINA:\n{dados['conteudo'][:10000]}\n\n"
            
            response = self.modelo_gemini.generate_content(prompt)
            
            if response and response.text:
                print("✅ Batch processado com sucesso")
                return response.text
            else:
                print("❌ Batch retornou resposta vazia")
                return None
                
        except Exception as e:
            print(f"❌ Erro no batch: {e}")
            return None
    
    def processar_resposta_gemini(self, resposta):
        """Processa resposta do Gemini"""
        dados = {}
        
        try:
            linhas = resposta.strip().split('\n')
            
            for linha in linhas:
                if ':' in linha:
                    chave, valor = linha.split(':', 1)
                    chave_limpa = chave.strip().lower().replace(' ', '_')
                    valor_limpo = valor.strip()
                    
                    if valor_limpo and 'não encontrado' not in valor_limpo.lower():
                        dados[chave_limpa] = valor_limpo
            
            dados['status_processamento'] = 'Sucesso'
            print(f"✅ {len(dados)} campos extraídos")
            
        except Exception as e:
            print(f"❌ Erro ao processar resposta: {e}")
            dados = {'status_processamento': 'Erro no processamento'}
        
        return dados
    
    def separar_resposta_batch(self, resposta_completa, nomes_batch, urls_batch):
        """Separa resposta do batch em dados individuais"""
        resultados = []
        
        try:
            secoes = resposta_completa.split("=== PESQUISADOR")
            
            for i, secao in enumerate(secoes[1:], 1):
                try:
                    dados = self.processar_resposta_gemini(secao)
                    
                    # Adicionar dados do batch
                    if i <= len(urls_batch):
                        dados['url_fapesp'] = urls_batch[i-1]
                    
                    if i <= len(nomes_batch):
                        if 'nome_completo' not in dados or dados['nome_completo'] == 'Não encontrado':
                            dados['nome_completo'] = nomes_batch[i-1]
                    
                    dados['modo_processamento'] = 'Batch Otimizado'
                    resultados.append(dados)
                    
                except Exception as e:
                    print(f"❌ Erro no pesquisador {i}: {e}")
                    nome_fallback = nomes_batch[i-1] if i <= len(nomes_batch) else f"Pesquisador {i}"
                    resultados.append({
                        'nome_completo': nome_fallback,
                        'status_processamento': 'Erro no processamento',
                        'modo_processamento': 'Batch Otimizado'
                    })
            
            return resultados
            
        except Exception as e:
            print(f"❌ Erro ao separar batch: {e}")
            return []
    
    def salvar_resultado(self, dados, nome_pesquisador, index):
        """Salva resultado individual"""
        try:
            nome_arquivo = re.sub(r'[^\w\s-]', '', nome_pesquisador)
            nome_arquivo = re.sub(r'\s+', '_', nome_arquivo.strip())[:50]
            nome_base = f"FAPESP_{nome_arquivo}_{self.timestamp}"
            
            # JSON
            arquivo_json = self.pasta_resultados / f"{nome_base}.json"
            dados_json = {
                "metadados": {
                    "timestamp": self.timestamp,
                    "data_hora": datetime.now().isoformat(),
                    "versao": "funcional-completa",
                    "index": index,
                    "modo": dados.get('modo_processamento', 'Individual')
                },
                "dados": dados
            }
            
            with open(arquivo_json, 'w', encoding='utf-8') as f:
                json.dump(dados_json, f, indent=2, ensure_ascii=False)
            
            # CSV
            arquivo_csv = self.pasta_resultados / f"{nome_base}.csv"
            linha = {}
            for campo in CAMPOS_CSV:
                linha[campo] = dados.get(campo, 'Não encontrado')
            
            df = pd.DataFrame([linha])
            df.to_csv(arquivo_csv, index=False, encoding='utf-8')
            
            print(f"💾 Salvo: {nome_base}")
            
        except Exception as e:
            print(f"❌ Erro ao salvar {nome_pesquisador}: {e}")
    
    def processar_individual(self, nome, index):
        """Processa um pesquisador individual"""
        try:
            print(f"\n📋 [{index}] PROCESSANDO: {nome}")
            print("=" * 50)
            
            # Buscar
            url = self.buscar_pesquisador(nome)
            if not url:
                return {
                    'nome_completo': nome,
                    'status_processamento': 'Não encontrado',
                    'modo_processamento': 'Individual'
                }
            
            # Extrair
            conteudo = self.extrair_dados_pagina(url)
            if not conteudo:
                return {
                    'nome_completo': nome,
                    'status_processamento': 'Erro na extração',
                    'modo_processamento': 'Individual'
                }
            
            # Processar com Gemini
            resposta = self.processar_individual_gemini(conteudo, nome)
            if not resposta:
                return {
                    'nome_completo': nome,
                    'status_processamento': 'Erro no Gemini',
                    'modo_processamento': 'Individual'
                }
            
            # Processar resposta
            dados = self.processar_resposta_gemini(resposta)
            dados['url_fapesp'] = url
            dados['modo_processamento'] = 'Individual'
            
            # Salvar
            self.salvar_resultado(dados, nome, index)
            
            print(f"✅ [{index}] {nome} - CONCLUÍDO")
            return dados
            
        except Exception as e:
            print(f"❌ [{index}] Erro geral: {e}")
            return {
                'nome_completo': nome,
                'status_processamento': f'Erro: {str(e)[:100]}',
                'modo_processamento': 'Individual'
            }
    
    def processar_batch(self, nomes, batch_size):
        """Processa pesquisadores em batch"""
        try:
            resultados_totais = []
            
            # Dividir em grupos
            for i in range(0, len(nomes), batch_size):
                grupo = nomes[i:i+batch_size]
                numero_grupo = (i // batch_size) + 1
                total_grupos = (len(nomes) + batch_size - 1) // batch_size
                
                print(f"\n🚀 GRUPO {numero_grupo}/{total_grupos}")
                print(f"📋 {len(grupo)} pesquisadores: {', '.join(grupo)}")
                print("=" * 60)
                
                # Coletar dados
                dados_batch = []
                nomes_batch = []
                urls_batch = []
                
                for nome in grupo:
                    print(f"🔍 Coletando: {nome}")
                    
                    url = self.buscar_pesquisador(nome)
                    if url:
                        conteudo = self.extrair_dados_pagina(url)
                        if conteudo:
                            dados_batch.append({
                                'nome': nome,
                                'url': url,
                                'conteudo': conteudo
                            })
                            nomes_batch.append(nome)
                            urls_batch.append(url)
                            print(f"✅ Coletado: {nome}")
                        else:
                            print(f"❌ Erro na extração: {nome}")
                    else:
                        print(f"❌ Não encontrado: {nome}")
                
                if dados_batch:
                    print(f"\n🤖 Processando {len(dados_batch)} pesquisadores em batch...")
                    
                    # Processar com Gemini
                    resposta_batch = self.processar_batch_gemini(dados_batch)
                    
                    if resposta_batch:
                        # Separar resultados
                        resultados_grupo = self.separar_resposta_batch(resposta_batch, nomes_batch, urls_batch)
                        
                        # Salvar individuais
                        for j, resultado in enumerate(resultados_grupo):
                            index_global = i + j + 1
                            nome_pesquisador = resultado.get('nome_completo', f'Pesquisador_{index_global}')
                            self.salvar_resultado(resultado, nome_pesquisador, index_global)
                            resultados_totais.append(resultado)
                        
                        print(f"✅ Grupo {numero_grupo} processado: {len(resultados_grupo)} resultados")
                    else:
                        print(f"❌ Erro no processamento do grupo {numero_grupo}")
                
                # Delay entre grupos
                if i + batch_size < len(nomes):
                    delay = CONFIG['DELAY_ENTRE_REQUESTS']
                    print(f"⏳ Aguardando {delay} segundos...")
                    time.sleep(delay)
            
            return resultados_totais
            
        except Exception as e:
            print(f"❌ Erro no batch: {e}")
            return []
    
    def gerar_relatorios_finais(self, nomes_iniciais, resultados):
        """Gera relatórios CSV de comparação e de nomes não encontrados."""
        try:
            print("\n📊 Gerando relatórios finais...")
            
            # Usar nomes iniciais como a fonte da verdade
            dados_comparacao = []
            nomes_nao_encontrados = []
            
            # Criar um conjunto de nomes encontrados com sucesso para busca rápida
            nomes_sucesso = {r.get('nome_completo', '').strip().lower() 
                             for r in resultados 
                             if r.get('status_processamento') == 'Sucesso'}

            for nome in nomes_iniciais:
                if nome.strip().lower() in nomes_sucesso:
                    status = 'Encontrado'
                else:
                    status = 'Não Encontrado'
                    nomes_nao_encontrados.append(nome)
                
                dados_comparacao.append({'nome_pesquisado': nome, 'status': status})

            if dados_comparacao:
                df_comp = pd.DataFrame(dados_comparacao)
                arquivo_comp = self.pasta_resultados / f"relatorio_comparativo_{self.timestamp}.csv"
                df_comp.to_csv(arquivo_comp, index=False, encoding='utf-8')
                print(f"✅ Relatório de comparação salvo em: {arquivo_comp}")

            # 2. Gerar lista de não encontrados
            if nomes_nao_encontrados:
                df_nao_encontrados = pd.DataFrame(nomes_nao_encontrados, columns=['nome_nao_encontrado'])
                arquivo_nao_encontrados = self.pasta_resultados / f"nomes_nao_encontrados_{self.timestamp}.csv"
                df_nao_encontrados.to_csv(arquivo_nao_encontrados, index=False, encoding='utf-8')
                print(f"✅ Lista de nomes não encontrados salva em: {arquivo_nao_encontrados}")
            else:
                print("👍 Todos os nomes da lista foram encontrados.")

        except Exception as e:
            print(f"❌ Erro ao gerar relatórios finais: {e}")
    
    def executar(self):
        """Execução principal"""
        try:
            self.mostrar_banner()
            
            # Configuração
            modelo_info = self.selecionar_modelo()
            config = self.obter_configuracao()
            
            if not config:
                print("❌ Configuração inválida")
                return False
            
            nomes = config['nomes']
            batch_otimizado = config['batch_otimizado']
            batch_size = config['batch_size']
            
            # Mostrar configuração
            modo = f"BATCH ({batch_size} por vez)" if batch_otimizado else "INDIVIDUAL"
            print(f"\n🚀 CONFIGURAÇÃO FINAL:")
            print(f"   🤖 Modelo: {modelo_info['display']}")
            print(f"   ⚡ Modo: {modo}")
            print(f"   📊 Pesquisadores: {len(nomes)}")
            print(f"   📁 Resultados: {self.pasta_resultados}")
            
            if batch_otimizado:
                grupos = (len(nomes) + batch_size - 1) // batch_size
                print(f"   🔥 Grupos: {grupos}")
                print(f"   💰 Economia estimada: 70-80%")
            
            # Confirmação
            input("\n⏯️ Pressione Enter para iniciar...")
            
            # Inicialização
            headless = input("🖥️ Executar sem mostrar browser? (S/n): ").lower() != 'n'
            
            if not self.inicializar_selenium(headless):
                return False
            
            if not self.inicializar_gemini(modelo_info):
                return False
            
            # Processamento
            tempo_inicio = time.time()
            
            if batch_otimizado:
                print(f"\n⚡ PROCESSAMENTO EM BATCH OTIMIZADO")
                resultados = self.processar_batch(nomes, batch_size)
            else:
                print(f"\n🔄 PROCESSAMENTO INDIVIDUAL")
                resultados = []
                
                for i, nome in enumerate(nomes, 1):
                    resultado = self.processar_individual(nome, i)
                    resultados.append(resultado)
                    
                    if i < len(nomes):
                        delay = CONFIG['DELAY_ENTRE_REQUESTS']
                        print(f"⏳ Aguardando {delay} segundos...")
                        time.sleep(delay)
            
            # Gerar relatórios finais
            self.gerar_relatorios_finais(nomes, resultados)
            
            # Estatísticas
            tempo_total = time.time() - tempo_inicio
            sucessos = sum(1 for r in resultados if r.get('status_processamento') == 'Sucesso')
            
            print(f"\n🏁 PROCESSAMENTO CONCLUÍDO!")
            print(f"⏱️ Tempo total: {tempo_total/60:.1f} minutos")
            print(f"✅ Sucessos: {sucessos}/{len(resultados)}")
            print(f"📈 Taxa de sucesso: {(sucessos/len(resultados)*100):.1f}%")
            print(f"📁 Arquivos salvos em: {self.pasta_resultados}")
            
            if batch_otimizado:
                economia = len(nomes) - ((len(nomes) + batch_size - 1) // batch_size)
                print(f"💰 Chamadas economizadas: {economia}")
            
            return True
            
        except KeyboardInterrupt:
            print("\n⏹️ Interrompido pelo usuário")
            return False
        except Exception as e:
            print(f"\n❌ Erro geral: {e}")
            return False
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    print("✅ Browser fechado")
                except:
                    pass

def main():
    """Função principal"""
    print("🔬 EXTRATOR FAPESP - VERSÃO FUNCIONAL COMPLETA")
    print("⚡ Batch configurável + Modelos 2.0/2.5 + Formato específico")
    print()
    
    if not configurar_api_key():
        return
    
    extrator = ExtratorFAPESP()
    
    try:
        sucesso = extrator.executar()
        if sucesso:
            print("\n🎉 EXTRAÇÃO CONCLUÍDA COM SUCESSO!")
        else:
            print("\n💥 EXTRAÇÃO FINALIZADA COM PROBLEMAS")
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO: {e}")
    finally:
        input("\n🔚 Pressione Enter para sair...")

if __name__ == "__main__":
    main()