import inspect
import asyncio
from typing import Callable, Any, Optional


class Signal:
    def __init__(self, name: str = ""):
        self.name = name
        self._receivers: list[tuple[Any, Callable, Optional[Any]]] = []

    def connect(
        self, receiver: Callable, sender: Optional[Any] = None, weak: bool = True
    ):
        """
        Signal tinglovchisini biriktirish.
        """
        lookup_key = id(receiver)
        for r_id, r_func, r_sender in self._receivers:
            if r_id == lookup_key and r_sender == sender:
                return
        self._receivers.append((lookup_key, receiver, sender))

    def disconnect(self, receiver: Callable, sender: Optional[Any] = None):
        """
        Signal tinglovchisini o'chirish.
        """
        lookup_key = id(receiver)
        self._receivers = [
            (r_id, r_func, r_sender)
            for r_id, r_func, r_sender in self._receivers
            if not (r_id == lookup_key and r_sender == sender)
        ]

    def send(self, sender: Any, **kwargs) -> List[Tuple[Callable, Any]]:
        """
        Signalni sinxron chaqirish.
        """
        responses = []
        for r_id, receiver, r_sender in self._receivers:
            if (
                r_sender is None
                or r_sender == sender
                or (isinstance(sender, type) and issubclass(sender, r_sender))
            ):
                if inspect.iscoroutinefunction(receiver):
                    try:
                        loop = asyncio.get_running_loop()
                        res = loop.create_task(receiver(sender=sender, **kwargs))
                    except RuntimeError:
                        res = asyncio.run(receiver(sender=sender, **kwargs))
                else:
                    res = receiver(sender=sender, **kwargs)
                responses.append((receiver, res))
        return responses

    async def send_async(self, sender: Any, **kwargs) -> List[Tuple[Callable, Any]]:
        """
        Signalni asinxron chaqirish.
        """
        responses = []
        for r_id, receiver, r_sender in self._receivers:
            if (
                r_sender is None
                or r_sender == sender
                or (isinstance(sender, type) and issubclass(sender, r_sender))
            ):
                if inspect.iscoroutinefunction(receiver):
                    res = await receiver(sender=sender, **kwargs)
                else:
                    res = receiver(sender=sender, **kwargs)
                responses.append((receiver, res))
        return responses


pre_init = Signal("pre_init")
post_init = Signal("post_init")
pre_save = Signal("pre_save")
post_save = Signal("post_save")
pre_delete = Signal("pre_delete")
post_delete = Signal("post_delete")


def receiver(signal: Union[Signal, List[Signal]], sender: Optional[Any] = None):
    """
    Signal receiver sifatida bezash uchun dekorator.
    """

    def decorator(func: Callable):
        signals = signal if isinstance(signal, (list, tuple)) else [signal]
        for s in signals:
            s.connect(func, sender=sender)
        return func

    return decorator
