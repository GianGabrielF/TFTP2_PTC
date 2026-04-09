from MEFtx import MEFtx
from mensagens import Modo
from poller import Poller

server = ("172.18.220.2", 1069)

poll = Poller()

tx = MEFtx(
    server=server,
    nome_local="muitos",
    nome_remoto="muitos",
    modo=Modo.Octet
)

poll.adiciona(tx)
poll.despache()

print("Status:", tx.status)