import requests
import getpass
import json
import re
import time
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track, Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.layout import Layout
from rich.columns import Columns
from rich.align import Align
from transformers import pipeline

# --- Configuração e Constantes ---
CONSOLE = Console()
# Paleta de cores futurista
ESTILO_TITULO = "bold cyan"
ESTILO_POSITIVO = "bold green"
ESTILO_NEGATIVO = "bold red"
ESTILO_NEUTRO = "bold yellow"
ESTILO_TEXTO = "white"
ESTILO_MENU = "bold magenta"
ESTILO_SISTEMA = "dim cyan"

CRYPTO_TICKERS = {
    'BTC', 'ETH', 'USDT', 'BNB', 'XRP', 'ADA', 'SOL', 'DOGE', 'DOT', 'MATIC',
    'SHIB', 'AVAX', 'LINK', 'UNI', 'LTC', 'ATOM', 'XLM', 'ETC', 'FIL', 'TRX'
}

# --- Funções de Interface Visual ---

def exibir_logo():
    logo = """
[bold magenta]╭─────────────────────────────────────────────────────────────╮[/bold magenta]
[bold magenta]│                                                             │[/bold magenta]
[bold cyan]│    C  R  Y  P  T  O - A G E N T   v.2.0                       │[/bold cyan]
[bold cyan]│                                                             │[/bold cyan]
[bold cyan]│    [ANÁLISE DE INTELIGÊNCIA DE MERCADO]                      │[/bold cyan]
[bold magenta]│                                                             │[/bold magenta]
[bold magenta]╰─────────────────────────────────────────────────────────────╯[/bold magenta]
"""
    CONSOLE.print(Align.center(logo))
    time.sleep(1.5)

def sequencia_boot():
    """Simula uma sequência de inicialização do sistema."""
    CONSOLE.clear()
    exibir_logo()
    boot_tasks = [
        "[SISTEMA] Verificando integridade dos módulos de IA...",
        "[SISTEMA] Conectando aos fluxos de dados da NewsAPI...",
        "[SISTEMA] Carregando modelo de análise de sentimento BERT...",
        "[SISTEMA] Carregando modelo de resumo T5...",
        "[SISTEMA] Calibrando analisador de palavras-chave...",
        "[SISTEMA] Interface neural online. Pronto para operação.",
    ]
    for task in boot_tasks:
        CONSOLE.print(f"[{ESTILO_SISTEMA}]{task}[/{ESTILO_SISTEMA}]", style="cyan")
        time.sleep(0.7)
    time.sleep(1)
    CONSOLE.print("\n[bold green]>>> SISTEMA PRONTO. AGUARDANDO COMANDOS. <<<[/bold green]\n")
    time.sleep(1.5)


# --- Classe Principal do Agente (Lógica inalterada) ---

class AgenteNoticiasCrypto:
    def __init__(self, api_key):
        self.api_key = api_key
        # A sequência de boot cuidará da parte visual do carregamento
        try:
            self.summarizer = pipeline("summarization", model="t5-small")
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis", 
                model="nlptown/bert-base-multilingual-uncased-sentiment"
            )
        except Exception as e:
            CONSOLE.print(f"[bold red]ERRO CRÍTICO: Falha ao carregar modelos de IA: {e}[/bold red]")
            exit()

    def _analisar_sentimento(self, texto):
        try:
            resultado = self.sentiment_analyzer(texto)
            estrelas = int(resultado[0]['label'].split(' ')[0])
            if estrelas >= 4: return "🟢 Positivo"
            if estrelas <= 2: return "🔴 Negativo"
            return "🟡 Neutro"
        except: return "🟡 Neutro"

    def _resumir_texto(self, texto):
        if not texto or len(texto.split()) < 30:
            return "Texto muito curto para resumir."
        try:
            texto_limitado = texto[:1024]
            resumo_ia = self.summarizer(f"summarize: {texto_limitado}", max_length=60, min_length=10, do_sample=False)
            return resumo_ia[0]['summary_text']
        except: return "Erro ao resumir."

    def _extrair_keywords(self, artigos):
        keywords_gerais = set()
        for artigo in artigos:
            texto = f"{artigo['titulo']} {artigo.get('content', '')} {artigo.get('description', '')}"
            tickers_encontrados = {ticker for ticker in CRYPTO_TICKERS if ticker in texto.upper()}
            keywords_gerais.update(tickers_encontrados)
            palavras_capitalizadas = {palavra for palavra in re.findall(r'\b[A-Z][a-z]+\b', texto) if len(palavra) > 2}
            keywords_gerais.update(palavras_capitalizadas)
        return sorted(list(keywords_gerais))

    def buscar_e_processar(self, termo, qtd_artigos):
        url = "https://newsapi.org/v2/everything"
        params = {"q": termo, "language": "pt", "pageSize": qtd_artigos, "sortBy": "publishedAt", "apiKey": self.api_key}
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            artigos_brutos = response.json().get("articles", [])
        except requests.exceptions.RequestException as e:
            CONSOLE.print(f"[bold red]ERRO DE CONEXÃO: {e}[/bold red]")
            if e.response.status_code == 401: CONSOLE.print("[bold red]FALHA DE AUTENTICAÇÃO: Chave da API inválida.[/bold red]")
            return None, None, None
        if not artigos_brutos:
            CONSOLE.print(f"[yellow]AVISO: Nenhum dado encontrado para o termo '{termo}'.[/yellow]")
            return None, None, None

        artigos_processados = []
        sentimentos = []
        for artigo in track(artigos_brutos, description="[cyan]Processando dados com IA...[/cyan]", transient=True):
            texto = artigo.get('content') or artigo.get('description', '')
            resumo = self._resumir_texto(texto)
            sentimento = self._analisar_sentimento(artigo['title'])
            sentimentos.append(sentimento)
            artigos_processados.append({"titulo": artigo['title'], "fonte": artigo['source']['name'], "link": artigo['url'], "resumo": resumo, "sentimento": sentimento})
        
        keywords = self._extrair_keywords(artigos_brutos)
        return artigos_processados, sentimentos, keywords

# --- Classe da Aplicação (Interface com o Usuário) ---

class App:
    def __init__(self):
        self.agente = None
        self.api_key = None

    def obter_chave(self):
        CONSOLE.print(Panel.fit("[bold cyan]INICIANDO PROTOCOLO DE AUTENTICAÇÃO[/bold cyan]", border_style="magenta"))
        while not self.api_key:
            chave = getpass.getpass(">>> INSERIR CHAVE DE API [NewsAPI.org]: ")
            if chave:
                self.api_key = chave
                # A sequência de boot será chamada após a criação do agente
                self.agente = AgenteNoticiasCrypto(api_key=self.api_key)
                sequencia_boot()
            else:
                CONSOLE.print("[bold red]ERRO: Campo de chave não pode ser nulo.[/bold red]")
    
    def exibir_menu(self):
        return Prompt.ask(
            "\n[bold green]root@cyber-agent:~$[/bold green] [bold white]INSERIR COMANDO[/bold white]",
            choices=["buscar", "sair"],
            default="buscar",
            show_choices=False
        )

    def executar_busca(self):
        termo = Prompt.ask(">>> [bold white]DEFINIR PARÂMETRO DE BUSCA[/bold white]", default="cryptocurrency", show_default=False)
        qtd = IntPrompt.ask(">>> [bold white]DEFINir LIMITE DE ARTIGOS[/bold white]", default=5, show_default=False)
        
        artigos, sentimentos, keywords = self.agente.buscar_e_processar(termo, qtd)
        
        if not artigos: return

        # --- Dashboard de Resultados ---
        pos, neg, neu = sentimentos.count("🟢 Positivo"), sentimentos.count("🔴 Negativo"), sentimentos.count("🟡 Neutro")
        sentimento_geral = "Neutro"
        if pos > neg and pos > neu: sentimento_geral = "Positivo"
        elif neg > pos and neg > neu: sentimento_geral = "Negativo"

        # Painel de Sentimento
        painel_sentimento = Panel(
            f"[{ESTILO_POSITIVO}]Positivos: {pos}[/{ESTILO_POSITIVO}] | "
            f"[{ESTILO_NEGATIVO}]Negativos: {neg}[/{ESTILO_NEGATIVO}] | "
            f"[{ESTILO_NEUTRO}]Neutros: {neu}[/{ESTILO_NEUTRO}]\n\n"
            f"Sentimento Geral: [bold white]{sentimento_geral}[/bold white]",
            title=f"📊 ANÁLISE DE SENTIMENTO: '{termo.upper()}'",
            border_style="cyan"
        )
        # Painel de Keywords
        painel_keywords = Panel(
            f"[{ESTILO_TEXTO}]{', '.join(keywords[:15])}[/{ESTILO_TEXTO}]" if keywords else "N/A",
            title="🔑 TERMOS-CHAVE IDENTIFICADOS",
            border_style="magenta"
        )
        # Usando Columns para o layout de dashboard
        CONSOLE.print(Columns([painel_sentimento, painel_keywords], equal=True, expand=True))
        
        # Tabela Detalhada
        table = Table(title=f"FEED DE DADOS DETALHADO: '{termo.upper()}'", show_header=True, header_style=ESTILO_TITULO, border_style="dim")
        table.add_column("TÍTULO", style="cyan", no_wrap=True, width=50)
        table.add_column("FONTE", style="dim", width=15)
        table.add_column("SENTIMENTO", justify="center", width=15)
        table.add_column("RESUMO DA IA", style=ESTILO_TEXTO)
        for art in artigos:
            table.add_row(art["titulo"], art["fonte"], art["sentimento"], art["resumo"])
        CONSOLE.print(table)

        if Confirm.ask("\n[bold green]root@cyber-agent:~$[/bold green] [bold white]SALVAR RELATÓRIO EM ARQUIVO DE DADOS? (Y/N)[/bold white]"):
            self.salvar_relatorio(artigos, termo, sentimento_geral, keywords)

    def salvar_relatorio(self, artigos, termo, sentimento_geral, keywords):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nome_arquivo = f"relatorio_crypto_{timestamp}.json"
        dados = {"data_geracao": timestamp, "termo_pesquisado": termo, "sentimento_geral": sentimento_geral, "palavras_chave": keywords, "artigos_analisados": artigos}
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)
        CONSOLE.print(f"[{ESTILO_POSITIVO}]DADOS GRAVADOS COM SUCESSO EM: '{nome_arquivo}'[/{ESTILO_POSITIVO}]")

    def run(self):
        self.obter_chave()
        while True:
            escolha = self.exibir_menu()
            if escolha == "buscar":
                self.executar_busca()
            elif escolha == "sair":
                CONSOLE.print(Panel.fit("[bold red]ENCERRANDO SISTEMA...[/bold red]", border_style="red"))
                time.sleep(1)
                CONSOLE.clear()
                break

# --- Ponto de Entrada ---
if __name__ == "__main__":
    app = App()
    app.run()