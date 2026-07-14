import socket
from client import client
import subprocess
import sys
import time
from utils.menus import choose_mode, choose_connection
from local_game import play_local

def main():
    while True:
        # Open menu for local/host/join
        connection = choose_connection()

        if connection == "local":
            mode = choose_mode()
            play_local(mode)

        elif connection == "host":
            print("Starting server...")

            # Start server in background
            subprocess.Popen([sys.executable, "server.py"])

            # Give the server a moment to start listening
            time.sleep(1)

            client(f"{socket.gethostbyname(socket.gethostname())}:5000")

        elif connection == "join":
            success = client()

            if not success:
                continue


if __name__ == "__main__":
    main()
