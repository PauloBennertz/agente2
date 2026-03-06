import requests
import getpass
import json
import re
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track
from rich.prompt import Prompt, IntPrompt, Confirm
from transformers import pipeline

# --- Configuração e Constantes ---
CONSOLE = Console()
CRYPTO_TICKERS = {
    'BTC', 'ETH', 'USDT', 'BNB', 'XRP', 'ADA', 'SOL', 'DOGE', 'DOT', 'MATIC',
    'SHIB', 'AVAX', 'LINK', 'UNI', 'LTC', 'ATOM', 'XLM', 'ETC', 'FIL', 'TRX'
}

# --- Classe Principal do Agente ---

class AgenteNoticiasCrypto:
    def __init__(self, api_key):
        self.api_key = api_key
        CONSOLE.print("[bold green]Carregando modelos de IA...[/bold green]")
        try:
            self.summarizer = pipeline("summarization", model="t5-small")
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis", 
                model="nlptown/bert-base-multilingual-uncased-sentiment"
            )
            CONSOLE.print("[bold green]Modelos prontos![/bold green]\n")
        except Exception as e:
            CONSOLE.print(f"[bold red]Erro ao carregar modelos de IA: {e}[/bold red]")
            exit()

    def _analisar_sentimento(self, texto):
        try:
            resultado = self.sentiment_analyzer(texto)
            estrelas = int(resultado[0]['label'].split(' ')[0])
            if estrelas >= 4: return "🟢 Positivo"
            if estrelas <= 2: return "🔴 Negativo"
            return "🟡 Neutro"
        except: return "🟡 Neutro" # Padrão para erros

    def _resumir_texto(self, texto):
        if not texto or len(texto.split()) < 30:
            return "Texto muito curto para resumir."
        try:
            texto_limitado = texto[:1024]
            resumo_ia = self.summarizer(f"summarize: {texto_limitado}", max_length=60, min_length=10, do_sample=False)
            return resumo_ia[0]['summary_text']
        except: return "Erro ao resumir."

    def _extrair_keywords(self, artigos):
        CONSOLE.print("Extraindo palavras-chave dos artigos...")
        keywords_gerais = set()
        for artigo in artigos:
            texto = f"{artigo['titulo']} {artigo.get('content', '')} {artigo.get('description', '')}"
            # Encontra tickers de cripto (ex: BTC, ETH)
            tickers_encontrados = {ticker for ticker in CRYPTO_TICKERS if ticker in texto.upper()}
            keywords_gerais.update(tickers_encontrados)
            
            # Encontra palavras capitalizadas (nomes próprios, etc.)
            palavras_capitalizadas = {palavra for palavra in re.findall(r'\b[A-Z][a-z]+\b', texto) if len(palavra) > 2}
            keywords_gerais.update(palavras_capitalizadas)
        
        return sorted(list(keywords_gerais))

    def buscar_e_processar(self, termo, qtd_artigos):
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": termo, "language": "pt", "pageSize": qtd_artigos,
            "sortBy": "publishedAt", "apiKey": self.api_key
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            artigos_brutos = response.json().get("articles", [])
        except requests.exceptions.RequestException as e:
            CONSOLE.print(f"[bold red]Erro na busca de notícias: {e}[/bold red]")
            if e.response.status_code == 401:
                CONSOLE.print("[bold red]Sua chave da API pode ser inválida.[/bold red]")
            return None, None, None

        if not artigos_brutos:
            CONSOLE.print("[yellow]Nenhuma notícia encontrada para este termo.[/yellow]")
            return None, None, None

        artigos_processados = []
        sentimentos = []

        # Usando a barra de progresso do Rich
        for artigo in track(artigos_brutos, description="Processando notícias com IA..."):
            texto = artigo.get('content') or artigo.get('description', '')
            
            resumo = self._resumir_texto(texto)
            sentimento = self._analisar_sentimento(artigo['title'])
            
            sentimentos.append(sentimento)
            artigos_processados.append({
                "titulo": artigo['title'],
                "fonte": artigo['source']['name'],
                "link": artigo['url'],
                "resumo": resumo,
                "sentimento": sentimento
            })
        
        keywords = self._extrair_keywords(artigos_brutos)
        return artigos_processados, sentimentos, keywords

# --- Classe da Aplicação (Interface com o Usuário) ---

class App:
    def __init__(self):
        self.agente = None
        self.api_key = None

    def obter_chave(self):
        CONSOLE.print(Panel("Bem-vindo ao [bold cyan]Agente de Notícias Crypto Pro[/bold cyan]!\n"
                            "Para começar, você precisa de uma chave da API do [link=https://newsapi.org/]NewsAPI.org[/link].",
                            title="🚀 Inicialização"))
        while not self.api_key:
            chave = getpass.getpass("Digite sua chave da NewsAPI.org (a digitação será oculta): ")
            if chave:
                self.api_key = chave
                self.agente = AgenteNoticiasCrypto(api_key=self.api_key)
            else:
                CONSOLE.print("[bold red]A chave não pode estar vazia.[/bold red]")
    
    def exibir_menu(self):
        return Prompt.ask(
            "\nO que você deseja fazer?",
            choices=["buscar", "sair"],
            default="buscar"
        )

    def executar_busca(self):
        termo = Prompt.ask("🔍 Digite o termo para buscar (ex: Bitcoin, NFTs, Ethereum)", default="cryptocurrency")
        qtd = IntPrompt.ask("📊 Quantos artigos você quer analisar?", default=5)
        
        artigos, sentimentos, keywords = self.agente.buscar_e_processar(termo, qtd)
        
        if not artigos:
            return

        # 1. Resumo do Sentimento Geral
        pos = sentimentos.count("🟢 Positivo")
        neg = sentimentos.count("🔴 Negativo")
        neu = sentimentos.count("🟡 Neutro")
        
        sentimento_geral = "Neutro"
        if pos > neg and pos > neu: sentimento_geral = "Positivo"
        elif neg > pos and neg > neu: sentimento_geral = "Negativo"
        
        CONSOLE.print(Panel(
            f"Análise de {len(artigos)} artigos sobre '{termo}':\n\n"
            f"🟢 Positivos: {pos} | 🔴 Negativos: {neg} | 🟡 Neutros: {neu}\n\n"
            f"[bold]Sentimento Geral do Mercado: {sentimento_geral}[/bold]",
            title=f"📈 Panorama do Sentimento"
        ))

        # 2. Tabela Detalhada
        table = Table(title=f"Relatório Detalhado: '{termo}'", show_header=True, header_style="bold magenta")
        table.add_column("Título", style="cyan", no_wrap=True, width=50)
        table.add_column("Fonte", style="dim", width=15)
        table.add_column("Sentimento", justify="center")
        table.add_column("Resumo da IA", style="green")
        for art in artigos:
            table.add_row(art["titulo"], art["fonte"], art["sentimento"], art["resumo"])
        CONSOLE.print(table)

        # 3. Palavras-chave
        if keywords:
            CONSOLE.print(Panel(", ".join(keywords[:20]), title="🔑 Palavras-chave Encontradas"))

        # 4. Opção de salvar
        if Confirm.ask("\n💾 Deseja salvar este relatório em um arquivo JSON?"):
            self.salvar_relatorio(artigos, termo, sentimento_geral, keywords)

    def salvar_relatorio(self, artigos, termo, sentimento_geral, keywords):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nome_arquivo = f"relatorio_crypto_{timestamp}.json"
        dados = {
            "data_geracao": timestamp,
            "termo_pesquisado": termo,
            "sentimento_geral": sentimento_geral,
            "palavras_chave": keywords,
            "artigos_analisados": artigos
        }
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)
        CONSOLE.print(f"[green]Relatório salvo com sucesso em '{nome_arquivo}'[/green]")

    def run(self):
        self.obter_chave()
        while True:
            escolha = self.exibir_menu()
            if escolha == "buscar":
                self.executar_busca()
            elif escolha == "sair":
                CONSOLE.print("[bold green]Obrigado por usar o Agente Crypto Pro. Até logo![/bold green]")
                break

# --- Ponto de Entrada ---
if __name__ == "__main__":
    app = App()
    app.run()