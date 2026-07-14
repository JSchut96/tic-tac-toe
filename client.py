import json
import socket
from dataclasses import asdict
from modals import Message
from utils.print import print_board
from utils.menus import choose_mode

def send_message(conn, message: Message):
    conn.sendall((json.dumps(asdict(message)) + "\n").encode())

def receive_message(conn) -> Message | None:
    data = conn.recv(1024).decode()

    if not data:
        return None

    return Message(**json.loads(data))

def client(address = None):
    if not address:
        address = input("Enter server address (IP:port): ")

    host, port = address.split(":")
    port = int(port)

    client_socket = socket.socket()
    client_socket.connect((host, port))

    sock_file = client_socket.makefile("r")

    while True:
        line = sock_file.readline()

        if not line:
            print("Disconnected from server.")
            client_socket.close()
            return False

        message = Message(**json.loads(line))

        match message.type:
            case "HOST_INFO":
                print("Share this address with your opponent:")
                print(f"Local: {message.payload['local_ip']}")
                print(f"Internet: {message.payload['public_ip']}")

                mode = choose_mode()

                send_message(
                    client_socket,
                    Message(
                        type="SET_MODE",
                        payload={
                            "mode": mode
                        }
                    )
                )
            case "GAME_START":
                my_symbol = message.payload["symbol"]

                print("Game started!")
                print(f"You are playing as {my_symbol}")
                print(f"Starting player: {message.payload['current_player']}")

                print_board(message.payload["board"])

                if message.payload["current_player"] == my_symbol:
                    print("It is your turn.")
                else:
                    print("Waiting for opponent...")

            case "BOARD_UPDATE":
                print_board(message.payload["board"], message.payload["highlight"])
                print(message.payload["text"])

            case "YOUR_TURN":
                move = input("Enter move (row,col): ")

                try:
                    row, col = map(int, move.split(","))
                except ValueError:
                    print("Invalid format.")
                    continue

                send_message(
                    client_socket,
                    Message(
                        type="MOVE",
                        payload={
                            "row": row - 1,
                            "col": col - 1
                        }
                    )
                )
            case "REMATCH_REQUEST":
                choice = input("Play again? (y/n): ").lower()

                send_message(
                    client_socket,
                    Message(
                        type="REMATCH",
                        payload={
                            "accept": choice == "y"
                        }
                    )
                )
            case "SESSION_END":
                print(message.payload["text"])
            case "ERROR":
                print(message.payload["text"])

            case "GAME_OVER":
                print_board(
                    message.payload["board"],
                    message.payload.get("winning_line")
                )
                print(message.payload["text"])
            case "OPPONENT_LEFT":
                print(message.payload["text"])
                return False
            case "MESSAGE":
                print(message.payload["text"])

            case _:
                print(f"Unknown message type: {message.type}")

    client_socket.close()

if __name__ == "__main__":
    client()
