"""Plumbing temporal do loop de vídeo: relógio e medição de desempenho."""

from __future__ import annotations

import time
from collections import Counter, deque
from collections.abc import Hashable
from typing import TypeVar

T = TypeVar("T", bound=Hashable)


class VideoClock:
    """Timestamps em milissegundos, estritamente crescentes.

    O modo de vídeo do MediaPipe rejeita timestamps que não avançam, e um loop
    rápido pode produzir dois quadros dentro do mesmo milissegundo. Esta classe
    concentra essa regra, que é fácil de esquecer no meio do loop.
    """

    def __init__(self, started: float | None = None) -> None:
        self._started = time.perf_counter() if started is None else started
        self._last_ms = -1

    def tick(self, now: float | None = None) -> int:
        now = time.perf_counter() if now is None else now
        elapsed_ms = int((now - self._started) * 1000)
        self._last_ms = max(elapsed_ms, self._last_ms + 1)
        return self._last_ms


class FpsMeter:
    """FPS com média exponencial, para o número não tremer na tela."""

    def __init__(self, smoothing: float = 0.9) -> None:
        self._smoothing = smoothing
        self._fps = 0.0
        self._last: float | None = None

    def tick(self, now: float | None = None) -> float:
        now = time.perf_counter() if now is None else now
        if self._last is not None:
            elapsed = now - self._last
            if elapsed > 0:
                instant = 1.0 / elapsed
                self._fps = (
                    instant
                    if self._fps == 0.0
                    else self._smoothing * self._fps + (1 - self._smoothing) * instant
                )
        self._last = now
        return self._fps


class ValueSmoother:
    """Anti-flicker: devolve o valor mais frequente das últimas N leituras.

    ``None`` representa "sem leitura" e também entra na janela, de modo que o
    valor exibido some suavemente quando a mão sai do quadro.
    """

    def __init__(self, window: int = 5) -> None:
        if window < 1:
            raise ValueError("A janela de suavização precisa ser >= 1.")
        self._history: deque[T | None] = deque(maxlen=window)

    def update(self, value: T | None) -> T | None:
        self._history.append(value)
        return Counter(self._history).most_common(1)[0][0]
