"""Feedback sonoro — bipes curtos, opcionais e inofensivos.

O `sounddevice` depende do PortAudio, que nem toda máquina tem (servidores, CI,
containers). Por isso o import é tardio e **toda** falha desliga o som em vez de
derrubar o app: um bipe que não toca nunca deve custar um frame.
"""

from __future__ import annotations

import contextlib

import numpy as np

SAMPLE_RATE = 44_100
#: Nome do tom → (frequência em Hz, duração em segundos).
TONES: dict[str, tuple[float, float]] = {
    "change": (880.0, 0.06),
    "recognized": (1320.0, 0.10),
}
#: Volume baixo de propósito: é um aviso, não um alarme.
AMPLITUDE = 0.18


def tone_wave(frequency: float, duration: float, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Senoide curta com *fade* nas pontas, para não estalar."""
    amostras = max(int(sample_rate * duration), 1)
    t = np.arange(amostras, dtype=np.float32) / sample_rate
    onda = np.sin(2 * np.pi * frequency * t, dtype=np.float32) * AMPLITUDE
    envelope = min(amostras // 4, 256)
    if envelope:
        rampa = np.linspace(0.0, 1.0, envelope, dtype=np.float32)
        onda[:envelope] *= rampa
        onda[-envelope:] *= rampa[::-1]
    return onda


class Beeper:
    """Toca bipes curtos. Silencioso quando desabilitado ou sem áudio."""

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled
        self.error: str | None = None
        self._sounddevice = None
        self._waves = {nome: tone_wave(*params) for nome, params in TONES.items()}

    def _backend(self):
        if self._sounddevice is None:
            import sounddevice  # tardio: só quem liga o som paga o PortAudio

            self._sounddevice = sounddevice
        return self._sounddevice

    def play(self, tone: str) -> bool:
        """Toca um tom sem bloquear. Devolve se realmente saiu som."""
        if not self.enabled or tone not in self._waves:
            return False
        try:
            self._backend().play(self._waves[tone], SAMPLE_RATE, blocking=False)
        except Exception as error:  # sem PortAudio, sem placa, dispositivo ocupado…
            self.enabled = False
            self.error = str(error)
            return False
        return True

    def close(self) -> None:
        if self._sounddevice is not None:
            with contextlib.suppress(Exception):  # encerrar nunca pode falhar
                self._sounddevice.stop()


#: Instância única, configurada uma vez pelo `main`. Segue o mesmo padrão do
#: idioma: evita levar um objeto de som por toda a árvore de modos.
_default = Beeper()


def configure(enabled: bool) -> Beeper:
    """Liga ou desliga o feedback sonoro do app inteiro."""
    _default.enabled = enabled
    return _default


def beep(tone: str) -> bool:
    """Toca um tom pela instância padrão."""
    return _default.play(tone)


def close() -> None:
    _default.close()
