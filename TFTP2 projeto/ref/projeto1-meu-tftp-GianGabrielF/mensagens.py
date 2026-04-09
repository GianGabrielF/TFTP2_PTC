from enum import Enum


# ==========================================================
# ENUM MODO (TFTP)
# ==========================================================

class Modo(Enum):
    NetAscii = "netascii"
    Octet = "octet"


# ==========================================================
# RRQ (Read Request)
# ==========================================================

class RRQ:

    def __init__(self, filename: str, modo: Modo):
        self.filename = filename
        self.modo = modo

    def serialize(self):
        opcode = (1).to_bytes(2, byteorder="big")
        return (
            opcode +
            self.filename.encode("ascii") + b"\0" +
            self.modo.value.encode("ascii") + b"\0"
        )

    @staticmethod
    def cria(buffer: bytes):
        filename, modo = RRQ._parse_filename_modo(buffer)
        return RRQ(filename, Modo(modo))


# ==========================================================
# WRQ (Write Request)
# ==========================================================

class WRQ:

    def __init__(self, filename: str, modo: Modo):
        self.filename = filename
        self.modo = modo

    def serialize(self):
        opcode = (2).to_bytes(2, byteorder="big")
        return (
            opcode +
            self.filename.encode("ascii") + b"\0" +
            self.modo.value.encode("ascii") + b"\0"
        )

    @staticmethod
    def cria(buffer: bytes):
        filename, modo = WRQ._parse_filename_modo(buffer)
        return WRQ(filename, Modo(modo))


# ==========================================================
# DATA
# ==========================================================

class DATA:

    def __init__(self, bloco: int, dados: bytes):
        self.bloco = bloco
        self.dados = dados

    def serialize(self):
        opcode = (3).to_bytes(2, byteorder="big")
        bloco = self.bloco.to_bytes(2, byteorder="big")
        return opcode + bloco + self.dados

    @staticmethod
    def cria(buffer: bytes):
        bloco = int.from_bytes(buffer[2:4], byteorder="big")
        dados = buffer[4:]
        return DATA(bloco, dados)


# ==========================================================
# ACK
# ==========================================================

class ACK:

    def __init__(self, bloco: int):
        self.bloco = bloco

    def serialize(self):
        opcode = (4).to_bytes(2, byteorder="big")
        bloco = self.bloco.to_bytes(2, byteorder="big")
        return opcode + bloco

    @staticmethod
    def cria(buffer: bytes):
        bloco = int.from_bytes(buffer[2:4], byteorder="big")
        return ACK(bloco)


# ==========================================================
# ERRO
# ==========================================================

class ERRO:

    def __init__(self, codigo: int, mensagem: str):
        self.codigo = codigo
        self.mensagem = mensagem

    def serialize(self):
        opcode = (5).to_bytes(2, byteorder="big")
        codigo = self.codigo.to_bytes(2, byteorder="big")
        return opcode + codigo + self.mensagem.encode("ascii") + b"\0"

    @staticmethod
    def cria(buffer: bytes):
        codigo = int.from_bytes(buffer[2:4], byteorder="big")
        mensagem = buffer[4:-1].decode("ascii")
        return ERRO(codigo, mensagem)


# ==========================================================
# FUNÇÃO AUXILIAR (PARSE RRQ/WRQ)
# ==========================================================

def _parse_filename_modo(buffer: bytes):
    """
    Extrai filename e modo de um pacote RRQ/WRQ
    """
    partes = buffer[2:].split(b"\0")
    filename = partes[0].decode("ascii")
    modo = partes[1].decode("ascii")
    return filename, modo


# Associar método auxiliar às classes
RRQ._parse_filename_modo = staticmethod(_parse_filename_modo)
WRQ._parse_filename_modo = staticmethod(_parse_filename_modo)