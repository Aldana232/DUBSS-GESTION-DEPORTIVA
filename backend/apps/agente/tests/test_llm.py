"""F7-01 — Cliente del LLM: espera ante el límite de uso de Groq y errores claros."""
import pytest

from apps.agente.services import llm


class Respuesta:
    def __init__(self, estado=200, cuerpo=None, cabeceras=None, texto=""):
        self.status_code, self._cuerpo, self.headers, self.text = estado, cuerpo or {}, cabeceras or {}, texto

    @property
    def ok(self):
        return self.status_code < 400

    def json(self):
        return self._cuerpo


OK = Respuesta(cuerpo={"choices": [{"message": {"content": "Hola", "tool_calls": [
    {"id": "c1", "function": {"name": "ver_clima", "arguments": '{"fecha": "2026-11-01"}'}}]}}]})


@pytest.fixture(autouse=True)
def clave(settings):
    settings.GROQ_API_KEY, settings.AGENTE_PROVIDER = "clave", "groq"


@pytest.fixture
def sin_esperar(monkeypatch):
    esperas = []
    monkeypatch.setattr(llm.time, "sleep", esperas.append)
    return esperas


def test_traduce_la_respuesta_con_llamadas_a_herramientas(monkeypatch):
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: OK)
    r = llm.chat([{"role": "user", "content": "x"}], [])
    assert r == {"content": "Hola", "tool_calls": [{"id": "c1", "name": "ver_clima", "arguments": '{"fecha": "2026-11-01"}'}]}


def test_si_groq_pide_una_pausa_espera_y_reintenta(monkeypatch, sin_esperar):
    respuestas = [Respuesta(429, cabeceras={"retry-after": "7"}), OK]
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: respuestas.pop(0))
    assert llm.chat([], [])["content"] == "Hola" and sin_esperar == [7.5]


def test_si_la_pausa_es_demasiado_larga_avisa_en_vez_de_colgar_al_usuario(monkeypatch, sin_esperar):
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: Respuesta(429, cabeceras={"retry-after": "60"}))
    with pytest.raises(llm.AgenteNoDisponible, match="límite de uso"):
        llm.chat([], [])
    assert sin_esperar == []


def test_reintenta_la_generacion_mal_formada_pero_no_indefinidamente(monkeypatch):
    llamadas = []
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: llamadas.append(1) or Respuesta(400, texto="tool_use_failed"))
    with pytest.raises(llm.AgenteNoDisponible):
        llm.chat([], [])
    assert len(llamadas) == 3


def test_reintenta_ante_un_fallo_momentaneo_del_servicio(monkeypatch, sin_esperar):
    respuestas = [Respuesta(503, texto="over capacity"), OK]
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: respuestas.pop(0))
    assert llm.chat([], [])["content"] == "Hola" and sin_esperar == [2]


def test_error_de_red_o_del_servicio_se_informa_sin_detalles_internos(monkeypatch):
    def cae(*a, **k):
        raise llm.requests.ConnectionError("dns")
    monkeypatch.setattr(llm.requests, "post", cae)
    with pytest.raises(llm.AgenteNoDisponible, match="contactar"):
        llm.chat([], [])
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: Respuesta(500, texto="boom"))
    with pytest.raises(llm.AgenteNoDisponible, match="no pudo procesar"):
        llm.chat([], [])
