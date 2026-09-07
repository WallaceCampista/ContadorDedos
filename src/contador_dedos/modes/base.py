"""O contrato de um modo — a unidade de funcionalidade plugável do app."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Mode(ABC):
    """Uma funcionalidade selecionável.

    Adicionar uma feature ao app é escrever uma subclasse e registrá-la em
    :mod:`contador_dedos.modes`; o loop principal não muda. A partir da Fase 4 o
    menu monta seus cards a partir de ``name`` e ``icon``.
    """

    #: Rótulo exibido no card do menu.
    name: str = ""
    #: Ícone (emoji) do card.
    icon: str = ""
    #: Dica de atalhos mostrada na barra de status enquanto o modo está ativo.
    hint: str = ""

    @abstractmethod
    def process(self, frame):
        """Recebe um frame BGR e devolve o frame anotado."""

    def on_key(self, key: int) -> bool:
        """Teclas do modo (opcional).

        Devolva ``True`` para dizer que a tecla foi consumida — é assim que um
        campo de texto impede que digitar "q" encerre o app.
        """
        return False

    def on_mouse(self, event: int, x: int, y: int) -> None:  # noqa: B027
        """Cliques dentro do modo (opcional) — só o menu da Fase 4 depende disto."""

    def close(self) -> None:  # noqa: B027
        """Libera os recursos do modo (opcional): nem todo modo tem o que soltar."""
