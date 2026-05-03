WIN_LINES = [
    {(0,0), (0,1), (0,2)},
    {(1,0), (1,1), (1,2)},
    {(2,0), (2,1), (2,2)},
    {(0,0), (1,0), (2,0)},
    {(0,1), (1,1), (2,1)},
    {(0,2), (1,2), (2,2)},
    {(0,0), (1,1), (2,2)},
    {(0,2), (1,1), (2,0)},
]

class Gamestate:
    def __init__(self, game_mode="normal"):
        self.board = [[' ' for _ in range(3)] for _ in range(3)]
        self.current_player = 'X'
        self.winner = None
        self.winning_line = []
        self.move_history = []
        self.game_mode = game_mode
        self.decaying_pos = None

    def make_move(self, row, col):
        # return invalid move
        if self.board[row][col] != ' ':
            return False

        # make and store move
        self.board[row][col] = self.current_player
        self.move_history.append((self.current_player, (row,col)))

        # apply decay if correct gamemode
        if self.game_mode == "decay":
            self.apply_decay_rule()

        self.check_winner()
        self.switch_player()
        return True

    def check_winner(self):
        for line in WIN_LINES:
            values = [self.board[i][j] for i, j in line]

            if values[0] != " " and len(set(values)) == 1:
                self.winner = values[0]
                self.winning_line = line
                return

        # draw check
        if all(cell != " " for row in self.board for cell in row):
            self.winner = "draw"
            self.winning_line = None


    def switch_player(self):
        if self.current_player == 'X':
            self.current_player = 'O'
        else:
            self.current_player = 'X'

    def apply_decay_rule(self):
        player_moves = [m for m in self.move_history if m[0] == self.current_player]

        if len(player_moves) > 3:
            oldest_move = player_moves[0]
            _, (row, col) = oldest_move

            # remove from board
            self.board[row][col] = " "

            # remove from history
            self.move_history.remove(oldest_move)

            return (row, col)

        return None

    def peek_decay_removal(self):
        if self.game_mode != "decay":
            return None

        player_moves = [m for m in self.move_history if m[0] == self.current_player]

        if len(player_moves) >= 3:
            oldest_move = player_moves[0]
            return {oldest_move[1]}

        return None
