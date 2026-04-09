from socket import socket, AF_INET, SOCK_DGRAM, IPPROTO_UDP
import poller
from mensagens import *

class MEFrx(poller.Callback):

    Timeout = 5  # segundos

    def __init__(self, server: tuple, nome_local: str, nome_remoto: str, modo: Modo):

        sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
        poller.Callback.__init__(self, sock, MEFrx.Timeout)

        self.server = server
        self.tid = None
        self.status = "Sucesso"

        self.nome_local = nome_local
        self.nome_remoto = nome_remoto
        self.modo = modo

        self.arq = open(self.nome_local, "wb")

        self.seq = 1            # próximo bloco esperado
        self.last_packet = None # último pacote enviado (RRQ ou ACK)

        # envia RRQ
        msg_rrq = RRQ(self.nome_remoto, self.modo)
        self.last_packet = msg_rrq
        self.fd.sendto(msg_rrq.serialize(), self.server)

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

        if opcode == 3:  # DATA
            msg = DATA.cria(data)
        elif opcode == 5:  # ERRO
            msg = ERRO.cria(data)
        else:
            return

        self._handle(msg)


    def handle_timeout(self):
        print("Timeout — retransmitindo último pacote")
        if self.last_packet:
            self.fd.sendto(self.last_packet.serialize(), self.server)
        self._handle(None)


    # ==========================================================
    # ESTADO INIT (esperando primeiro DATA)
    # ==========================================================

    def handle_init(self, evento):

        if evento is None:
            return

        if isinstance(evento, DATA):

            if evento.bloco != self.seq:
                return

            self.arq.write(evento.dados)

            ack = ACK(self.seq)
            self.last_packet = ack
            self.fd.sendto(ack.serialize(), self.server)

            if len(evento.dados) < 512:
                self._handle = self.handle_fim
            else:
                self.seq += 1
                self._handle = self.handle_rx

        elif isinstance(evento, ERRO):
            self._handle = self.handle_erro


    # ==========================================================
    # ESTADO RX (recebendo blocos seguintes)
    # ==========================================================

    def handle_rx(self, evento):

        if evento is None:
            return

        if isinstance(evento, DATA):

            if evento.bloco == self.seq:

                self.arq.write(evento.dados)

                ack = ACK(self.seq)
                self.last_packet = ack
                self.fd.sendto(ack.serialize(), self.server)

                if len(evento.dados) < 512:
                    self._handle = self.handle_fim
                else:
                    self.seq += 1

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