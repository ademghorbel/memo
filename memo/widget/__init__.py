"""Memo's desktop character (tkinter, standard library only)."""


def run(vault=None, config=None, every_min: float = 10, skin: str = "memo") -> None:
    from .app import MemoApp
    from ..__main__ import default_vault

    MemoApp(vault or default_vault(), config, every_min, skin).run()
