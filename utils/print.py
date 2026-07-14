def print_board(board, highlight=None):
    if highlight is None:
        highlight = set()

    highlight = {tuple(pos) for pos in highlight}

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
