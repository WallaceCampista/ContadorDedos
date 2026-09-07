"""Testes da captura — com uma `VideoCapture` de mentira, sem webcam."""

from __future__ import annotations

import numpy as np
import pytest

from contador_dedos.core import camera as camera_module
from contador_dedos.core.camera import Camera, CameraError


class FakeCapture:
    """Imita o suficiente de `cv2.VideoCapture` para exercitar a `Camera`."""

    def __init__(self, leituras, opened: bool = True):
        self._leituras = list(leituras)
        self._opened = opened
        self.released = False

    def isOpened(self) -> bool:  # o nome camelCase vem do OpenCV
        return self._opened

    def read(self):
        return self._leituras.pop(0) if self._leituras else (False, None)

    def release(self) -> None:
        self.released = True


@pytest.fixture
def capturando(monkeypatch):
    """Instala uma captura falsa e devolve o objeto criado."""
    criadas = []

    def _instalar(leituras, opened: bool = True):
        def _factory(_index):
            fake = FakeCapture(leituras, opened)
            criadas.append(fake)
            return fake

        monkeypatch.setattr(camera_module.cv2, "VideoCapture", _factory)
        return criadas

    return _instalar


def quadro(valor: int = 7) -> np.ndarray:
    """Frame assimétrico: permite detectar o espelhamento."""
    img = np.zeros((4, 4, 3), dtype=np.uint8)
    img[:, 0] = valor  # marca só a coluna da esquerda
    return img


def test_camera_indisponivel_avisa_e_libera(capturando):
    criadas = capturando([], opened=False)
    with pytest.raises(CameraError, match="Não consegui abrir a câmera 0"):
        Camera(0).open()
    assert criadas[0].released, "a captura precisa ser liberada mesmo ao falhar"


def test_ler_sem_abrir_e_erro(capturando):
    capturando([])
    with pytest.raises(CameraError, match="não foi aberta"):
        Camera().read()


def test_espelhamento_inverte_o_frame(capturando):
    capturando([(True, quadro())])
    with Camera(mirror=True) as cam:
        frame = cam.read()
    assert frame[0, 0, 0] == 0 and frame[0, -1, 0] == 7


def test_sem_espelhamento_o_frame_vem_como_veio(capturando):
    capturando([(True, quadro())])
    with Camera(mirror=False) as cam:
        frame = cam.read()
    assert frame[0, 0, 0] == 7 and frame[0, -1, 0] == 0


def test_frame_invalido_devolve_none_e_o_loop_continua(capturando):
    capturando([(False, None), (True, quadro())])
    with Camera(mirror=False) as cam:
        assert cam.read() is None
        assert cam.read() is not None


def test_falhas_seguidas_esgotam_a_tolerancia(capturando):
    capturando([(False, None)] * 5)
    with Camera(max_failures=3) as cam:
        assert cam.read() is None
        assert cam.read() is None
        with pytest.raises(CameraError, match="parou de entregar frames"):
            cam.read()


def test_um_frame_bom_zera_o_contador_de_falhas(capturando):
    """Falhas esparsas são normais; só uma sequência longa significa problema."""
    capturando([(False, None), (True, quadro()), (False, None), (True, quadro())])
    with Camera(max_failures=2, mirror=False) as cam:
        assert cam.read() is None
        assert cam.read() is not None
        assert cam.read() is None  # não estoura: o contador foi zerado
        assert cam.read() is not None


def test_context_manager_libera_a_captura(capturando):
    criadas = capturando([(True, quadro())])
    with Camera() as cam:
        cam.read()
    assert criadas[0].released


def test_captura_e_liberada_mesmo_com_erro_dentro_do_bloco(capturando):
    criadas = capturando([(True, quadro())])
    with pytest.raises(RuntimeError, match="falha no meio"), Camera():
        raise RuntimeError("falha no meio")
    assert criadas[0].released
