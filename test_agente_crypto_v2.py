import sys
from unittest.mock import MagicMock

# Mocking dependencies before they are imported by agente_crypto_v2
mock_requests = MagicMock()
mock_rich = MagicMock()
mock_transformers = MagicMock()

sys.modules["requests"] = mock_requests
sys.modules["rich"] = mock_rich
sys.modules["rich.console"] = mock_rich.console
sys.modules["rich.table"] = mock_rich.table
sys.modules["rich.panel"] = mock_rich.panel
sys.modules["transformers"] = mock_transformers

import pytest
from unittest.mock import patch

# Define a mock RequestException that inherits from Exception
class MockRequestException(Exception):
    def __init__(self, message, response=None):
        super().__init__(message)
        self.response = response

mock_requests.exceptions.RequestException = MockRequestException

# Now we can import the module under test
from agente_crypto_v2 import obter_chave_api, AgenteNoticiasCrypto

@pytest.fixture
def mock_agent():
    with patch("agente_crypto_v2.pipeline") as mock_pipeline, \
         patch("agente_crypto_v2.Console") as mock_console:
        mock_pipeline.side_effect = [MagicMock(), MagicMock()]
        agent = AgenteNoticiasCrypto(api_key="test_key")
        return agent

@patch("agente_crypto_v2.getpass.getpass")
@patch("agente_crypto_v2.Console")
def test_obter_chave_api_sucesso(mock_console, mock_getpass):
    mock_getpass.return_value = "minha_chave_123"
    chave = obter_chave_api()
    assert chave == "minha_chave_123"
    mock_getpass.assert_called_once()

@patch("agente_crypto_v2.getpass.getpass")
@patch("agente_crypto_v2.Console")
def test_obter_chave_api_vazia_depois_sucesso(mock_console, mock_getpass):
    mock_getpass.side_effect = ["", "chave_valida"]
    chave = obter_chave_api()
    assert chave == "chave_valida"
    assert mock_getpass.call_count == 2
    mock_console.return_value.print.assert_any_call("[bold red]Erro: A chave não pode estar vazia. Tente novamente.[/bold red]\n")

@patch("agente_crypto_v2.pipeline")
@patch("agente_crypto_v2.Console")
def test_agente_init_sucesso(mock_console, mock_pipeline):
    mock_pipeline.side_effect = [MagicMock(), MagicMock()]
    agente = AgenteNoticiasCrypto(api_key="test_key")
    assert agente.api_key == "test_key"
    assert mock_pipeline.call_count == 2
    mock_console.return_value.print.assert_any_call("[bold green]Modelos carregados com sucesso![/bold green]\n")

@patch("agente_crypto_v2.pipeline")
@patch("agente_crypto_v2.Console")
def test_agente_init_erro_modelo(mock_console, mock_pipeline):
    mock_pipeline.side_effect = Exception("Erro de download")
    with pytest.raises(SystemExit):
        AgenteNoticiasCrypto(api_key="test_key")
    mock_console.return_value.print.assert_any_call("[bold red]Erro ao carregar os modelos de IA: Erro de download[/bold red]")

@patch("agente_crypto_v2.requests.get")
@patch("agente_crypto_v2.Console")
def test_buscar_noticias_sucesso(mock_console, mock_requests_get, mock_agent):
    mock_response = MagicMock()
    mock_response.json.return_value = {"articles": [{"title": "Crypto Mooning", "source": {"name": "TestSource"}, "url": "http://test.com"}]}
    mock_requests_get.return_value = mock_response

    artigos = mock_agent.buscar_noticias()

    assert len(artigos) == 1
    assert artigos[0]["title"] == "Crypto Mooning"
    mock_requests_get.assert_called_once()

@patch("agente_crypto_v2.requests.get")
@patch("agente_crypto_v2.Console")
def test_buscar_noticias_erro_401(mock_console, mock_requests_get, mock_agent):
    mock_response = MagicMock()
    mock_response.status_code = 401
    error = MockRequestException("Unauthorized", response=mock_response)
    mock_requests_get.side_effect = error

    artigos = mock_agent.buscar_noticias()

    assert artigos == []
    mock_console.return_value.print.assert_any_call("[bold red]Parece que sua chave da API é inválida. Verifique e tente novamente.[/bold red]")

def test_processar_noticias_texto_curto(mock_agent):
    artigos = [{"title": "Title", "source": {"name": "S"}, "url": "L", "description": "Too short"}]
    mock_agent.sentiment_analyzer.return_value = [{"label": "5 stars"}]

    processados = mock_agent.processar_noticias(artigos)

    assert processados[0]["resumo"] == "Texto muito curto para resumir."
    assert processados[0]["sentimento"] == "🟢 Positivo"

def test_processar_noticias_sucesso(mock_agent):
    long_text = " ".join(["word"] * 50)
    artigos = [{"title": "Neutral news", "source": {"name": "S"}, "url": "L", "content": long_text}]
    mock_agent.summarizer.return_value = [{"summary_text": "This is a summary"}]
    mock_agent.sentiment_analyzer.return_value = [{"label": "3 stars"}]

    processados = mock_agent.processar_noticias(artigos)

    assert processados[0]["resumo"] == "This is a summary"
    assert processados[0]["sentimento"] == "🟡 Neutro"

def test_processar_noticias_negativo(mock_agent):
    long_text = " ".join(["word"] * 50)
    artigos = [{"title": "Bad news", "source": {"name": "S"}, "url": "L", "content": long_text}]
    mock_agent.summarizer.return_value = [{"summary_text": "Summary"}]
    mock_agent.sentiment_analyzer.return_value = [{"label": "1 star"}]

    processados = mock_agent.processar_noticias(artigos)

    assert processados[0]["sentimento"] == "🔴 Negativo"

@patch("agente_crypto_v2.Table")
@patch("agente_crypto_v2.Console")
def test_exibir_relatorio(mock_console, mock_table, mock_agent):
    artigos = [{"titulo": "T", "fonte": "F", "sentimento": "S", "resumo": "R", "link": "L"}]

    mock_agent.exibir_relatorio(artigos)

    mock_table.return_value.add_row.assert_called_once_with("T", "F", "S", "R")
    mock_console.return_value.print.assert_any_call(mock_table.return_value)

@patch("agente_crypto_v2.AgenteNoticiasCrypto.buscar_noticias")
@patch("agente_crypto_v2.AgenteNoticiasCrypto.processar_noticias")
@patch("agente_crypto_v2.AgenteNoticiasCrypto.exibir_relatorio")
def test_executar(mock_exibir, mock_processar, mock_buscar, mock_agent):
    mock_buscar.return_value = ["artigo1"]
    mock_processar.return_value = ["processado1"]

    mock_agent.executar()

    mock_buscar.assert_called_once()
    mock_processar.assert_called_once_with(["artigo1"])
    mock_exibir.assert_called_once_with(["processado1"])
