from MERFrx import MEFrx
from mensagens import Modo
from poller import Poller

server = ("172.18.220.2", 1069)

poll = Poller()

rx = MEFrx(
    server=server,
    nome_local="muitos",
    nome_remoto="muitos",
    modo=Modo.Octet
)

poll.adiciona(rx)
poll.despache()

print("Status:", rx.status)