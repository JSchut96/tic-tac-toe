from game import Gamestate

def print_board(board, highlight=None):
    print(highlight)
    if highlight is None:
        highlight = set()

    for i in range(3):
        row = []

        for j in range(3):
            value = board[i][j]

            if (i, j) in highlight:
                cell = f"[{value}]"
            else:
                cell = f" {value} "

            row.append(cell)

        print(" | ".join(row))


def choose_mode():
    while True:
        print("\nChoose game mode:")
        print("1. Normal Tic Tac Toe")
        print("2. Decay mode (3 moves per player)")

        choice = input("> ").strip()

        if choice == "1":
            return "normal"
        if choice == "2":
            return "decay"

        print("Invalid choice, try again.")

def main():
    mode = choose_mode()

    game = Gamestate(mode)

    while not game.winner:
        print()
        print_board(game.board, game.peek_decay_removal())

        print(f"Current Player: {game.current_player}")

        try:
            raw = input("Enter a move (row,col): ")
            row_str, col_str = raw.split(",")
            row = int(row_str.strip()) - 1
            col = int(col_str.strip()) - 1

            if not (0 <= row < 3 and 0 <= col < 3):
                print("Row and column must be between 1 and 3.")
                continue
        except ValueError:
            print("Invalid input. Format should be row,col (e.g. 1,2)")
            continue

        success = game.make_move(row, col)

        if not success:
            print("Invalid move. Try again.")

        if game.winner == "draw":
            print()
            print_board(game.board)
            print("It's a draw!")
        elif game.winner:
            print()
            print_board(game.board, game.winning_line)
            print(f"Winner: Player {game.winner}")


if __name__ == "__main__":
    main()
