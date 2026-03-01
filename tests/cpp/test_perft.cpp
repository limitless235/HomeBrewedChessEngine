#include "attacks.h"
#include "board.h"
#include "movegen.h"
#include <chrono>
#include <iostream>

using namespace std;
using namespace std::chrono;

U64 perft(Board &board, int depth) {
  if (depth == 0)
    return 1ULL;

  Move moves[256];
  int count = generate_moves(board, moves);

  U64 nodes = 0;
  for (int i = 0; i < count; i++) {
    BoardState st = board.save_state();
    st.captured_piece = board.get_piece_on_square(get_to(moves[i]));

    board.make_move(moves[i]);

    int opp_side = board.side_to_move ^ 1;
    if (!is_in_check(board, opp_side)) {
      nodes += perft(board, depth - 1);
    }

    board.unmake_move(moves[i], st);
  }
  return nodes;
}

void run_perft(int depth) {
  Board board;
  board.set_startpos();

  auto start = high_resolution_clock::now();
  U64 nodes = perft(board, depth);
  auto end = high_resolution_clock::now();

  duration<double> diff = end - start;
  cout << "Depth " << depth << " Nodes: " << nodes << " Time: " << diff.count()
       << "s"
       << " NPS: " << (uint64_t)(nodes / diff.count()) << "\n";
}

int main() {
  init_attacks();
  init_zobrist();

  for (int i = 1; i <= 5; i++) {
    run_perft(i);
  }
  return 0;
}
