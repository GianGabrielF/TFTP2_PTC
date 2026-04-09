import select
import time


# ==========================================================
# CLASSE BASE CALLBACK
# ==========================================================

class Callback:

    def __init__(self, fd, timeout=None):
        self.fd = fd
        self.timeout = timeout
        self.enabled = True
        self.timeout_enabled = timeout is not None
        self.reload_timeout()

    def handle(self):
        """Chamado quando há dados disponíveis no socket"""
        pass

    def handle_timeout(self):
        """Chamado quando ocorre timeout"""
        pass

    def reload_timeout(self):
        if self.timeout_enabled:
            self.deadline = time.time() + self.timeout
        else:
            self.deadline = None

    def disable(self):
        self.enabled = False

    def disable_timeout(self):
        self.timeout_enabled = False
        self.deadline = None


# ==========================================================
# POLLER
# ==========================================================

class Poller:

    def __init__(self):
        self.callbacks = []

    def adiciona(self, callback: Callback):
        self.callbacks.append(callback)

    def despache(self):

        while any(cb.enabled for cb in self.callbacks):

            # lista de sockets ativos
            fds = [cb.fd for cb in self.callbacks if cb.enabled]

            # calcula timeout mínimo
            timeouts = [
                cb.deadline - time.time()
                for cb in self.callbacks
                if cb.enabled and cb.timeout_enabled
            ]

            if timeouts:
                timeout = max(0, min(timeouts))
            else:
                timeout = None

            if fds:
                rlist, _, _ = select.select(fds, [], [], timeout)
            else:
                time.sleep(timeout)
                rlist = []

            now = time.time()

            for cb in self.callbacks:

                if not cb.enabled:
                    continue

                # evento de leitura
                if cb.fd in rlist:
                    cb.handle()
                    cb.reload_timeout()

                # evento de timeout
                elif cb.timeout_enabled and cb.deadline and now >= cb.deadline:
                    cb.handle_timeout()
                    cb.reload_timeout()