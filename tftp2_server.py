import socket
import os
import re
import shutil
import tftp2_pb2 as pb

HOST = "0.0.0.0"
PORT = 6969
BASE_DIR = os.path.abspath("./storage")

TIMEOUT = 2
MAX_RETRIES = 5
BLOCK_SIZE = 512

os.makedirs(BASE_DIR, exist_ok=True)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))
sock.settimeout(TIMEOUT)

print(f"Servidor rodando em {HOST}:{PORT}")
print("BASE_DIR:", BASE_DIR)


def safe_path(base, user_path):
    full = os.path.abspath(os.path.join(base, user_path))
    if not full.startswith(base):
        raise Exception("Acesso inválido")
    return full


while True:
    try:
        data, addr = sock.recvfrom(65535)
    except socket.timeout:
        continue

    req = pb.Mensagem()
    req.ParseFromString(data)

    resp = pb.Mensagem()

    try:
        tipo = req.WhichOneof("msg")
        print(f"[REQ] {tipo}")

        # ================= LIST =================
        if tipo == "list":
            path = safe_path(BASE_DIR, req.list.path)

            if not os.path.exists(path):
                resp.error.errorcode = pb.FileNotFound
            else:
                lr = pb.ListResponse()

                for item in os.listdir(path):
                    full = os.path.join(path, item)
                    li = lr.items.add()

                    if os.path.isfile(full):
                        li.file.nome = item
                        li.file.tamanho = os.path.getsize(full)
                    else:
                        li.dir.path = item

                resp.list_resp.CopyFrom(lr)

            sock.sendto(resp.SerializeToString(), addr)

        # ================= SEARCH =================
        elif tipo == "search":
            base = safe_path(BASE_DIR, req.search.path)
            regex = re.compile(req.search.filtro)

            if not os.path.exists(base):
                resp.error.errorcode = pb.FileNotFound
            else:
                sr = pb.SearchResponse()

                for root, _, files in os.walk(base):
                    for f in files:
                        if regex.match(f):
                            item = sr.items.add()
                            item.path = root.replace(BASE_DIR, "")
                            item.nome = f

                resp.search_resp.CopyFrom(sr)

            sock.sendto(resp.SerializeToString(), addr)

        # ================= MKDIR =================
        elif tipo == "mkdir":
            path = safe_path(BASE_DIR, req.mkdir.path)
            os.makedirs(path, exist_ok=True)

            resp.ack.block_n = 0
            sock.sendto(resp.SerializeToString(), addr)

        # ================= RMDIR =================
        elif tipo == "rmdir":
            path = safe_path(BASE_DIR, req.rmdir.path)

            if not os.path.exists(path):
                resp.error.errorcode = pb.FileNotFound
            else:
                if req.rmdir.force:
                    shutil.rmtree(path)
                else:
                    os.rmdir(path)

                resp.ack.block_n = 0

            sock.sendto(resp.SerializeToString(), addr)

        # ================= MOVE =================
        elif tipo == "move":
            old = safe_path(BASE_DIR, req.move.nome_orig)

            if not os.path.exists(old):
                resp.error.errorcode = pb.FileNotFound
            else:
                if not req.move.nome_novo:
                    os.remove(old)
                else:
                    new = safe_path(BASE_DIR, req.move.nome_novo)
                    os.rename(old, new)

                resp.ack.block_n = 0

            sock.sendto(resp.SerializeToString(), addr)

        # ================= RRQ =================
        elif tipo == "rrq":
            path = safe_path(BASE_DIR, req.rrq.fname)

            if not os.path.exists(path):
                resp.error.errorcode = pb.FileNotFound
                sock.sendto(resp.SerializeToString(), addr)
                continue

            with open(path, "rb") as f:
                block = 1

                while True:
                    chunk = f.read(BLOCK_SIZE)

                    data_msg = pb.Mensagem()
                    data_msg.data.block_n = block
                    data_msg.data.message = chunk

                    retries = 0

                    while retries < MAX_RETRIES:
                        sock.sendto(data_msg.SerializeToString(), addr)

                        try:
                            ack_raw, _ = sock.recvfrom(65535)
                            ack = pb.Mensagem()
                            ack.ParseFromString(ack_raw)

                            if ack.HasField("ack") and ack.ack.block_n == block:
                                break

                        except socket.timeout:
                            retries += 1
                            print(f"[RRQ] Retry bloco {block}")

                    if retries == MAX_RETRIES:
                        print("[RRQ] Falha")
                        break

                    if len(chunk) < BLOCK_SIZE:
                        break

                    block += 1

        # ================= WRQ =================
        elif tipo == "wrq":
            path = safe_path(BASE_DIR, req.wrq.fname)

            resp.ack.block_n = 0
            sock.sendto(resp.SerializeToString(), addr)

            with open(path, "wb") as f:
                expected_block = 1

                while True:
                    retries = 0

                    while retries < MAX_RETRIES:
                        try:
                            data_raw, _ = sock.recvfrom(65535)
                            data_msg = pb.Mensagem()
                            data_msg.ParseFromString(data_raw)

                            if not data_msg.HasField("data"):
                                continue

                            if data_msg.data.block_n == expected_block:
                                f.write(data_msg.data.message)

                                ack = pb.Mensagem()
                                ack.ack.block_n = expected_block
                                sock.sendto(ack.SerializeToString(), addr)

                                break

                        except socket.timeout:
                            retries += 1
                            print(f"[WRQ] Retry bloco {expected_block}")

                    if retries == MAX_RETRIES:
                        print("[WRQ] Falha")
                        break

                    if len(data_msg.data.message) < BLOCK_SIZE:
                        break

                    expected_block += 1

        else:
            resp.error.errorcode = pb.IllegalOperation
            sock.sendto(resp.SerializeToString(), addr)

    except Exception as e:
        print("[ERRO]", e)