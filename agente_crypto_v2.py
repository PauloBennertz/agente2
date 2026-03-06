import requests
import getpass # Biblioteca para ocultar a digitação da chave
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from transformers import pipeline

# --- Função para Obter a Chave da API ---

def obter_chave_api():
    """
    Solicita e valida a chave da API do usuário de forma segura.
    """
    console = Console()
    console.print("[bold cyan]Bem-vindo ao Agente de Notícias Crypto![/bold cyan]")
    console.print("Para começar, você precisa de uma chave da API do [link=https://newsapi.org/]NewsAPI.org[/link].\n")
    
    while True:
        # getpass oculta o que o usuário digita
        api_key = getpass.getpass("Digite sua chave da NewsAPI.org (a digitação será oculta): ")
        
        if not api_key:
            console.print("[bold red]Erro: A chave não pode estar vazia. Tente novamente.[/bold red]\n")
        else:
            console.print("[green]Chave recebida. Inicializando o agente...[/green]\n")
            return api_key

# --- Classe do Agente de Notícias ---

class AgenteNoticiasCrypto:
    """
    Um agente que busca, resume e analisa o sentimento de notícias sobre criptomoedas.
    """
    def __init__(self, api_key):
        """Inicializa o agente com a chave da API e carrega os modelos de IA."""
        self.api_key = api_key
        console = Console()
        
        console.print("[bold green]Inicializando o Agente de Notícias Crypto...[/bold green]")
        
        # Carrega os modelos de IA. Isso pode levar alguns segundos na primeira execução.
        try:
            console.print("Carregando modelo de resumo (T5)...")
            self.summarizer = pipeline("summarization", model="t5-small")
            
            console.print("Carregando modelo de análise de sentimento (BERT multilíngue)...")
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis", 
                model="nlptown/bert-base-multilingual-uncased-sentiment"
            )
            console.print("[bold green]Modelos carregados com sucesso![/bold green]\n")
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar os modelos de IA: {e}[/bold red]")
            console.print("[yellow]Verifique sua conexão com a internet e tente novamente.[/yellow]")
            exit()

    def buscar_noticias(self, query="cryptocurrency", language="pt", page_size=5):
        """
        Busca notícias na NewsAPI.org com base em uma query.
        """
        url = f"https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "language": language,
            "pageSize": page_size,
            "sortBy": "publishedAt",
            "apiKey": self.api_key # Usa a chave armazenada na instância
        }
        
        console = Console()
        console.print(f"Buscando as últimas {page_size} notícias sobre '{query}'...")
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json().get("articles", [])
        except requests.exceptions.RequestException as e:
            console.print(f"[bold red]Erro ao buscar notícias: {e}[/bold red]")
            # Verifica se o erro foi por causa de uma chave inválida
            if response.status_code == 401:
                 console.print("[bold red]Parece que sua chave da API é inválida. Verifique e tente novamente.[/bold red]")
            return []

    def processar_noticias(self, artigos):
        """
        Processa uma lista de artigos, resumindo e analisando o sentimento de cada um.
        """
        console = Console()
        if not artigos:
            console.print("[yellow]Nenhuma notícia encontrada para processar.[/yellow]")
            return []

        artigos_processados = []
        console.print("Processando artigos com IA (resumo e sentimento)...")

        for i, artigo in enumerate(artigos):
            console.print(f"  -> Processando artigo {i+1}/{len(artigos)}: {artigo['title'][:50]}...")
            
            texto_para_resumir = artigo.get('content') or artigo.get('description')
            if not texto_para_resumir or len(texto_para_resumir.split()) < 30:
                resumo = "Texto muito curto para resumir."
            else:
                texto_para_resumir = texto_para_resumir[:1024]
                try:
                    resumo_ia = self.summarizer(f"summarize: {texto_para_resumir}", max_length=60, min_length=10, do_sample=False)
                    resumo = resumo_ia[0]['summary_text']
                except Exception as e:
                    resumo = f"Erro ao resumir: {e}"
            
            try:
                sentimento_ia = self.sentiment_analyzer(artigo['title'])
                estrelas = int(sentimento_ia[0]['label'].split(' ')[0])
                if estrelas >= 4:
                    sentimento = "🟢 Positivo"
                elif estrelas <= 2:
                    sentimento = "🔴 Negativo"
                else:
                    sentimento = "🟡 Neutro"
            except Exception as e:
                sentimento = f"Erro na análise: {e}"

            artigos_processados.append({
                "titulo": artigo['title'],
                "fonte": artigo['source']['name'],
                "link": artigo['url'],
                "resumo": resumo,
                "sentimento": sentimento
            })
        
        console.print("[bold green]Processamento concluído![/bold green]\n")
        return artigos_processados

    def exibir_relatorio(self, artigos):
        """
        Exibe os artigos processados em uma tabela formatada no terminal.
        """
        console = Console()
        if not artigos:
            return

        table = Table(title="📈 Relatório de Notícias do Mercado de Criptomoedas 📉", show_header=True, header_style="bold magenta")
        table.add_column("Título", style="cyan", no_wrap=True, width=50)
        table.add_column("Fonte", style="dim", width=15)
        table.add_column("Sentimento", justify="center", width=12)
        table.add_column("Resumo da IA", style="green", width=60)

        for artigo in artigos:
            table.add_row(
                artigo["titulo"],
                artigo["fonte"],
                artigo["sentimento"],
                artigo["resumo"]
            )

        console.print(table)
        
        links_texto = "\n".join([f"• {art['titulo'][:40]}...: {art['link']}" for art in artigos])
        console.print(Panel(links_texto, title="🔗 Links para Leitura Completa", expand=False))


    def executar(self):
        """
        Método principal que orquestra a execução do agente.
        """
        artigos = self.buscar_noticias()
        artigos_processados = self.processar_noticias(artigos)
        self.exibir_relatorio(artigos_processados)


# --- Execução do Agente ---
if __name__ == "__main__":
    # 1. Obtém a chave da API do usuário
    chave = obter_chave_api()
    
    # 2. Cria uma instância do agente com a chave fornecida
    agente = AgenteNoticiasCrypto(api_key=chave)
    
    # 3. Executa o agente
    agente.executar()