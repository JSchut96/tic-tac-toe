import socket
import threading
from game import Gamestate
import random
from dataclasses import asdict
from modals import Message
import json
import urllib.request

class GameSession:
    def __init__(self) -> None:
        self.game = None
        self.player_symbols = {}
        self.connections: dict[int, socket.socket] = {}
        self.connection_files = {}
        self.lock = threading.Lock()
        self.disconnected = False
        self.mode = None
        self.rematch_votes = {}
        self.rematch_event = threading.Event()
        self.game_finished = threading.Event()
        self.rematch_lock = threading.Lock()
        self.score: dict[int | str, int] = {
            "draw": 0,
            0: 0,
            1: 0,
        }
        self.players = {
            0: "Player 1",
            1: "Player 2",
        }

    def start(self):
        assert self.mode is not None

        self.game = Gamestate(self.mode)

        # Determine starting player X
        if random.randint(0, 1) == 0:
            self.player_symbols = {0: "X", 1: "O"}
        else:
            self.player_symbols = {0: "O", 1: "X"}

        # Send Game Start message
        for player_id in self.connections:
            self.send_to_player(
                player_id,
                Message(
                    type="GAME_START",
                    payload={
                        "board": self.game.board,
                        "symbol": self.player_symbols[player_id],
                        "current_player": self.game.current_player,
                    },
                ),
            )
        # Inform starting user
        for player_id, symbol in self.player_symbols.items():
            if symbol == "X":
                self.send_to_player(
                    player_id,
                    Message(
                        type="YOUR_TURN",
                        payload={
                            "text": "Your turn.",
                            "board": self.game.board,
                        }
                    )
                )

    def get_player_from_symbol(self, symbol: str) -> int:
        for player_id, player_symbol in self.player_symbols.items():
            if player_symbol == symbol:
                return player_id

        raise ValueError(f"Unknown symbol: {symbol}")

    def run_game(self):
        while not self.disconnected:
            self.game_finished.clear()
            self.start()

            # Wait for this game to finish
            self.game_finished.wait()

            if self.disconnected:
                break

            assert self.game is not None
            assert self.game.winner is not None


            # Communicate draw/winner
            if self.game.winner == "draw":
                text = "It's a draw!"
                winning_player = None
            else:
                winning_player = self.get_player_from_symbol(self.game.winner)
                text = f"{self.players[winning_player]} wins!"

            self.broadcast(
                Message(
                    type="GAME_OVER",
                    payload={
                        "text": text,
                        "board": self.game.board,
                        "winning_line": (
                            list(self.game.winning_line)
                            if self.game.winning_line is not None
                            else None
                        )
                    }
                )
            )

            # Calculate and communicate scoring
            if winning_player is None:
                self.score["draw"] += 1
            else:
                self.score[winning_player] += 1

            self.broadcast(
                Message(
                    type="MESSAGE",
                    payload={"text": f"Current score: Player 1: {self.score[0]} win(s) | Player 2: {self.score[1]} win(s) | Draws: {self.score['draw']}"}
                )
            )

            # Start Rematch Vote
            self.rematch_votes.clear()
            self.rematch_event.clear()

            self.broadcast(
                Message(
                    type="REMATCH_REQUEST",
                    payload={"text": "Play again?"}
                )
            )

            self.rematch_event.wait()

            if self.disconnected:
                break

            # Abort session if some one votes no to a rematch
            if not all(self.rematch_votes.values()):
                declined_player = next(
                    player_id
                    for player_id, accepted in self.rematch_votes.items()
                    if not accepted
                )

                for player_id in self.connections:
                    if player_id == declined_player:
                        text = "You did not want a rematch."
                    else:
                        text = "Your opponent did not want a rematch."

                    self.send_to_player(
                        player_id,
                        Message(
                            type="SESSION_END",
                            payload={
                                "text": text
                            }
                        )
                    )

                break

        self.end_session()

    def end_session(self):
        self.disconnected = True

        self.rematch_event.set()
        self.game_finished.set()

        for conn in self.connections.values():
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            try:
                conn.close()
            except OSError:
                pass

    def wait_for_mode(self):
        message = self.receive_message(0)

        if message is None:
            self.disconnected = True
            return False

        if message.type == "SET_MODE":
            self.mode = message.payload["mode"]
            return True

        return False

    def _send_message(self, conn, message: Message):
        try:
            conn.sendall((json.dumps(asdict(message)) + "\n").encode())
        except (ConnectionError, OSError):
            self.disconnected = True

    def receive_message(self, player_id: int) -> Message | None:
        try:
            line = self.connection_files[player_id].readline()

            if not line:
                return None

            return Message(**json.loads(line))

        except (ConnectionResetError, BrokenPipeError, OSError):
            return None

    def send_to_player(self, player_id: int, message: Message):
        conn = self.connections[player_id]
        self._send_message(conn, message)

    def broadcast(self, message: Message):
        for conn in self.connections.values():
            self._send_message(conn, message)

    def get_other_player(self, player_id: int) -> int:
        return 1 - player_id

    def handle_player(self, player_id: int):
        while not self.disconnected:
            message = self.receive_message(player_id)

            if message is None:
                self.handle_disconnect(player_id)
                break

            if message.type == "REMATCH":
                self.handle_rematch(player_id, message)
                continue

            if self.game is None:
                continue

            with self.lock:
                self.handle_move(player_id, message)

    def handle_disconnect(self, player_id: int):
        self.disconnected = True

        other_player = self.get_other_player(player_id)

        if other_player in self.connections:
            try:
                self.send_to_player(
                    other_player,
                    Message(
                        type="OPPONENT_LEFT",
                        payload={"text": "Opponent disconnected."}
                    )
                )
            except OSError:
                pass

        self.end_session()

    def handle_rematch(self, player_id: int, message: Message):
        with self.rematch_lock:
            accepted = message.payload["accept"]
            self.rematch_votes[player_id] = accepted

            if not accepted or len(self.rematch_votes) == 2:
                self.rematch_event.set()

    def handle_move(self, player_id: int, message: Message):
        assert self.game is not None

        if not self.validate_move(player_id, message):
            return

        row = message.payload["row"]
        col = message.payload["col"]

        success = self.game.make_move(row, col)

        if not success:
            self.send_invalid_move(player_id)
            return

        if self.game.winner:
            self.game_finished.set()
            return

        self.send_board_update(player_id)

    def validate_move(self, player_id: int, message: Message) -> bool:
        assert self.game is not None

        if self.player_symbols[player_id] != self.game.current_player:
            self.send_to_player(
                player_id,
                Message(
                    type="ERROR",
                    payload={
                        "text": "Not your turn.",
                        "board": self.game.board,
                    },
                ),
            )
            return False

        if message.type != "MOVE":
            self.send_to_player(
                player_id,
                Message(
                    type="ERROR",
                    payload={
                        "text": "Expected MOVE message.",
                        "board": self.game.board,
                    },
                ),
            )
            return False

        row = message.payload["row"]
        col = message.payload["col"]

        if row is None or col is None:
            self.send_to_player(
                player_id,
                Message(
                    type="ERROR",
                    payload={
                        "text": "Move is missing row or column.",
                        "board": self.game.board,
                    },
                ),
            )
            return False

        if not (0 <= row < 3 and 0 <= col < 3):
            self.send_to_player(
                player_id,
                Message(
                    type="ERROR",
                    payload={
                        "text": "Row and column must be between 0 and 2.",
                        "board": self.game.board,
                    },
                ),
            )
            return False

        return True

    def send_invalid_move(self, player_id: int):
        assert self.game is not None

        highlight = self.game.peek_decay_removal()

        self.send_to_player(
            player_id,
            Message(
                type="ERROR",
                payload={
                    "text": "Invalid move.",
                    "board": self.game.board,
                    "highlight": highlight,
                },
            ),
        )

        self.send_to_player(
            player_id,
            Message(
                type="YOUR_TURN",
                payload={
                    "board": self.game.board,
                    "highlight": highlight,
                    "text": "Try again.",
                },
            ),
        )

    def send_board_update(self, player_id: int):
        assert self.game is not None

        highlight = self.game.peek_decay_removal()

        self.broadcast(
            Message(
                type="BOARD_UPDATE",
                payload={
                    "board": self.game.board,
                    "highlight": list(highlight) if highlight else None,
                    "text": f"Current Player: {self.game.current_player}",
                },
            )
        )

        self.send_to_player(
            self.get_other_player(player_id),
            Message(
                type="YOUR_TURN",
                payload={
                    "text": f"Current Player: {self.game.current_player}",
                },
            ),
        )

class GameServer:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port
        self.session = GameSession()

    def run(self):
        local_ip = socket.gethostbyname(socket.gethostname())

        try:
            public_ip = urllib.request.urlopen(
                "https://api.ipify.org"
            ).read().decode()
        except Exception:
            public_ip = "Unavailable"

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1,
        )

        try:
            server_socket.bind((self.host, self.port))
            server_socket.listen(2)

            print(f"Server listening on port {self.port}")


            # Connect host
            conn, addr = server_socket.accept()

            player_id = 0

            self.session.connections[player_id] = conn
            self.session.connection_files[player_id] = conn.makefile("r")

            self.session.send_to_player(
                0,
                Message(
                    type="HOST_INFO",
                    payload={
                        "local_ip": f"{local_ip}:{self.port}",
                        "public_ip": f"{public_ip}:{self.port}",
                    },
                ),
            )

            # Host chooses mode
            if not self.session.wait_for_mode():
                return


            # Wait for second player
            conn, addr = server_socket.accept()

            player_id = 1

            self.session.connections[player_id] = conn
            self.session.connection_files[player_id] = conn.makefile("r")

            self.session.send_to_player(0, Message(
                type="MESSAGE",
                payload={"text": "An opponent has arrived!"}
            ))

            # Start game loop first
            game_thread = threading.Thread(
                target=self.session.run_game,
            )
            game_thread.start()

            # Start listeners
            threads = []
            for player_id in self.session.connections:
                thread = threading.Thread(
                    target=self.session.handle_player,
                    args=(player_id,),
                )
                thread.start()
                threads.append(thread)

            game_thread.join()

        finally:
            server_socket.close()

            self.session.end_session()


if __name__ == '__main__':
    GameServer().run()
