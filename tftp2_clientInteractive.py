import socket
import shlex
import tftp2_pb2 as pb

SERVER = ("127.0.0.1", 6969)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send(msg):
    sock.sendto(msg.SerializeToString(), SERVER)
    data, _ = sock.recvfrom(65535)

    resp = pb.Mensagem()
    resp.ParseFromString(data)
    return resp


def show_help():
    print("\nComandos disponíveis:")
    print("  help")
    print("  list [path]")
    print("  search <path> <regex>")
    print("  mkdir <path>")
    print("  rmdir <path> [force]")
    print("  move <orig> [novo]  (sem novo = delete)")
    print("  exit\n")


def print_response(resp):
    tipo = resp.WhichOneof("msg")

    if tipo == "list_resp":
        print("\nLIST:")
        if len(resp.list_resp.items) == 0:
            print("(vazio)")
        for e in resp.list_resp.items:
            if e.HasField("file"):
                print(f"[FILE] {e.file.nome} ({e.file.tamanho} bytes)")
            else:
                print(f"[DIR ] {e.dir.path}")

    elif tipo == "search_resp":
        print("\nSEARCH:")
        if len(resp.search_resp.items) == 0:
            print("(nenhum resultado)")
        for item in resp.search_resp.items:
            print(f"{item.path}/{item.nome}")

    elif tipo == "ack":
        print("\nOK")

    elif tipo == "error":
        print(f"\nERRO: código {resp.error.errorcode}")

    else:
        print("\nResposta desconhecida")


# ================= LOOP PRINCIPAL =================

print("Digite 'help' para ver os comandos\n")

while True:
    try:
        cmd = input(">> ").strip()

        if not cmd:
            continue

        if cmd == "exit":
            print("Encerrando cliente...")
            break

        if cmd == "help":
            show_help()
            continue

        parts = shlex.split(cmd)
        msg = pb.Mensagem()

        # ================= LIST =================
        if parts[0] == "list":
            path = parts[1] if len(parts) > 1 else ""
            msg.list.path = path

        # ================= SEARCH =================
        elif parts[0] == "search":
            if len(parts) < 3:
                print("Uso: search <path> <regex>")
                continue

            msg.search.path = parts[1]
            msg.search.filtro = parts[2]

        # ================= MKDIR =================
        elif parts[0] == "mkdir":
            if len(parts) < 2:
                print("Uso: mkdir <path>")
                continue

            msg.mkdir.path = parts[1]

        # ================= RMDIR =================
        elif parts[0] == "rmdir":
            if len(parts) < 2:
                print("Uso: rmdir <path> [force]")
                continue

            msg.rmdir.path = parts[1]
            msg.rmdir.force = ("force" in parts)

        # ================= MOVE =================
        elif parts[0] == "move":
            if len(parts) < 2:
                print("Uso: move <orig> [novo]")
                continue

            msg.move.nome_orig = parts[1]
            msg.move.nome_novo = parts[2] if len(parts) > 2 else ""

        else:
            print("Comando desconhecido.")
            show_help()
            continue

        # ================= ENVIO =================
        resp = send(msg)
        print_response(resp)

    except KeyboardInterrupt:
        print("\nEncerrando cliente...")
        break

    except Exception as e:
        print("Erro:", e)