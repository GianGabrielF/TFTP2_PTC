import socket
import shlex
import tftp2_pb2 as pb

SERVER = ("127.0.0.1", 6969)

TIMEOUT = 2
MAX_RETRIES = 5
BLOCK_SIZE = 512

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(TIMEOUT)


def send(msg):
    sock.sendto(msg.SerializeToString(), SERVER)
    data, _ = sock.recvfrom(65535)

    resp = pb.Mensagem()
    resp.ParseFromString(data)
    return resp


def print_response(resp):
    tipo = resp.WhichOneof("msg")

    if tipo == "list_resp":
        print("\nLIST:")
        for e in resp.list_resp.items:
            if e.HasField("file"):
                print(f"[FILE] {e.file.nome} ({e.file.tamanho} bytes)")
            else:
                print(f"[DIR ] {e.dir.path}")

    elif tipo == "search_resp":
        print("\nSEARCH:")
        for item in resp.search_resp.items:
            print(f"{item.path}/{item.nome}")

    elif tipo == "ack":
        print("\nOK")

    elif tipo == "error":
        print(f"\nERRO: código {resp.error.errorcode}")


print("Digite 'help' para comandos\n")

while True:
    cmd = input(">> ").strip()

    if not cmd:
        continue

    if cmd == "exit":
        break

    if cmd == "help":
        print("list [path]")
        print("search <path> <regex>")
        print("mkdir <path>")
        print("rmdir <path> [force]")
        print("move <orig> [novo]")
        print("get <arquivo>")
        print("put <arquivo>")
        continue

    parts = shlex.split(cmd)
    msg = pb.Mensagem()

    try:
        if parts[0] == "list":
            msg.list.path = parts[1] if len(parts) > 1 else ""
            print_response(send(msg))

        elif parts[0] == "search":
            msg.search.path = parts[1]
            msg.search.filtro = parts[2]
            print_response(send(msg))

        elif parts[0] == "mkdir":
            msg.mkdir.path = parts[1]
            print_response(send(msg))

        elif parts[0] == "rmdir":
            msg.rmdir.path = parts[1]
            msg.rmdir.force = ("force" in parts)
            print_response(send(msg))

        elif parts[0] == "move":
            msg.move.nome_orig = parts[1]
            msg.move.nome_novo = parts[2] if len(parts) > 2 else ""
            print_response(send(msg))

        # ================= GET =================
        elif parts[0] == "get":
            filename = parts[1]

            msg.rrq.fname = filename
            msg.rrq.mode = pb.octet

            sock.sendto(msg.SerializeToString(), SERVER)

            with open(filename, "wb") as f:
                expected_block = 1

                while True:
                    retries = 0

                    while retries < MAX_RETRIES:
                        try:
                            data_raw, _ = sock.recvfrom(65535)
                            data_msg = pb.Mensagem()
                            data_msg.ParseFromString(data_raw)

                            if data_msg.HasField("data") and data_msg.data.block_n == expected_block:
                                f.write(data_msg.data.message)

                                ack = pb.Mensagem()
                                ack.ack.block_n = expected_block
                                sock.sendto(ack.SerializeToString(), SERVER)

                                break

                        except socket.timeout:
                            retries += 1
                            print(f"[GET] Retry bloco {expected_block}")

                    if retries == MAX_RETRIES:
                        print("Falha download")
                        break

                    if len(data_msg.data.message) < BLOCK_SIZE:
                        break

                    expected_block += 1

            print("Download concluído")

        # ================= PUT =================
        elif parts[0] == "put":
            filename = parts[1]

            msg.wrq.fname = filename
            msg.wrq.mode = pb.octet

            sock.sendto(msg.SerializeToString(), SERVER)
            sock.recvfrom(65535)  # ACK 0

            with open(filename, "rb") as f:
                block = 1

                while True:
                    chunk = f.read(BLOCK_SIZE)

                    data_msg = pb.Mensagem()
                    data_msg.data.block_n = block
                    data_msg.data.message = chunk

                    retries = 0

                    while retries < MAX_RETRIES:
                        sock.sendto(data_msg.SerializeToString(), SERVER)

                        try:
                            ack_raw, _ = sock.recvfrom(65535)
                            ack = pb.Mensagem()
                            ack.ParseFromString(ack_raw)

                            if ack.HasField("ack") and ack.ack.block_n == block:
                                break

                        except socket.timeout:
                            retries += 1
                            print(f"[PUT] Retry bloco {block}")

                    if retries == MAX_RETRIES:
                        print("Falha upload")
                        break

                    if len(chunk) < BLOCK_SIZE:
                        break

                    block += 1

            print("Upload concluído")

    except Exception as e:
        print("Erro:", e)