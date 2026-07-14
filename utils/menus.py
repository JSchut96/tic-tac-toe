def choose_mode():
    while True:
        print("\nChoose game mode:")
        print("1. Normal")
        print("2. Decay")

        choice = input("> ").strip()

        if choice == "1":
            print("You selected the normal game mode.")
            return "normal"
        elif choice == "2":
            print("You selected the decay game mode.")
            return "decay"

        print("Invalid choice.")

def choose_connection():
    while True:
        print("\nChoose how to play:")
        print("1. Local")
        print("2. Host game")
        print("3. Join game")

        choice = input("> ").strip()

        if choice == "1":
            return "local"
        elif choice == "2":
            return "host"
        elif choice == "3":
            return "join"

        print("Invalid choice.")
