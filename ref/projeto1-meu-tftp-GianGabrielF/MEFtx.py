from socket import socket, AF_INET, SOCK_DGRAM, IPPROTO_UDP
import poller
from mensagens import *

class MEFtx(poller.Callback):

    Timeout = 5  # segundos

    def __init__(self, server: tuple, nome_local: str, nome_remoto: str, modo: Modo):

        sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
        poller.Callback.__init__(self, sock, MEFtx.Timeout)

        self.server = server
        self.tid = None
        self.status = "Sucesso"

        self.nome_local = nome_local
        self.nome_remoto = nome_remoto
        self.modo = modo

        self.arq = open(self.nome_local, "rb")

        self.j = 0              # último bloco enviado
        self.last_data = None   # último DATA enviado

        # envia WRQ
        msg_wrq = WRQ(self.nome_remoto, self.modo)
        self.fd.sendto(msg_wrq.serialize(), self.server)

        self._handle = self.handle_init


    # ==========================================================
    # RECEPÇÃO DE PACOTES
    # ==========================================================

    def handle(self):

        data, addr = self.fd.recvfrom(516)

        if addr[0] != self.server[0]:
            return

        if self.tid is None:
            self.server = addr
            self.tid = addr[1]

        if addr[1] != self.tid:
            return

        opcode = int.from_bytes(data[0:2], byteorder="big")

        if opcode == 4:  # ACK
            msg = ACK.cria(data)
        elif opcode == 5:  # ERRO
            msg = ERRO.cria(data)
        else:
            return

        self._handle(msg)


    def handle_timeout(self):
        self._handle(None)


    # ==========================================================
    # ESTADO INIT (esperando ACK do WRQ)
    # ==========================================================

    def handle_init(self, evento):

        if evento is None:
            print("Timeout no WRQ")
            self._handle = self.handle_erro
            return

        if isinstance(evento, ACK):

            dados = self.arq.read(512)
            self.j = 1

            msg_data = DATA(self.j, dados)
            self.last_data = msg_data

            self.fd.sendto(msg_data.serialize(), self.server)

            if len(dados) < 512:
                self._handle = self.handle_ultima
            else:
                self._handle = self.handle_tx

        elif isinstance(evento, ERRO):
            self._handle = self.handle_erro


    # ==========================================================
    # ESTADO TX (enviando blocos intermediários)
    # ==========================================================

    def handle_tx(self, evento):

        if evento is None:
            print("Timeout — retransmitindo bloco", self.j)
            if self.last_data:
                self.fd.sendto(self.last_data.serialize(), self.server)
            return

        if isinstance(evento, ACK):

            if evento.bloco == self.j:

                dados = self.arq.read(512)

                if not dados:
                    self._handle = self.handle_fim
                    return

                self.j += 1

                msg_data = DATA(self.j, dados)
                self.last_data = msg_data

                self.fd.sendto(msg_data.serialize(), self.server)

                if len(dados) < 512:
                    self._handle = self.handle_ultima

        elif isinstance(evento, ERRO):
            self._handle = self.handle_erro


    # ==========================================================
    # ESTADO ULTIMA (último bloco enviado)
    # ==========================================================

    def handle_ultima(self, evento):

        if evento is None:
            print("Timeout — retransmitindo último bloco", self.j)
            if self.last_data:
                self.fd.sendto(self.last_data.serialize(), self.server)
            return

        if isinstance(evento, ACK):
            if evento.bloco == self.j:
                self._handle = self.handle_fim

        elif isinstance(evento, ERRO):
            self._handle = self.handle_erro


    # ==========================================================
    # ESTADO FIM
    # ==========================================================

    def handle_fim(self, evento):

        print("Transferência concluída com sucesso")

        self.arq.close()
        self.disable()
        self.disable_timeout()


    # ==========================================================
    # ESTADO ERRO
    # ==========================================================

    def handle_erro(self, evento):

        print("Erro na transferência")

        self.status = "Erro"
        self.arq.close()
        self.disable()
        self.disable_timeout()