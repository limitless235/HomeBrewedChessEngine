#include "uci.h"
#include "board.h"
#include "movegen.h"
#include "search.h"
#include "tt.h"
#include <iostream>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

std::thread search_thread;

Move parse_move(const Board &board, const std::string &move_str) {
  Move moves[256];
  int count = generate_moves(board, moves);
  for (int i = 0; i < count; i++) {
    Move m = moves[i];
    char f_char = 'a' + (get_from(m) % 8);
    char r_char = '8' - (get_from(m) / 8);
    char tf_char = 'a' + (get_to(m) % 8);
    char tr_char = '8' - (get_to(m) / 8);
    std::string s = "";
    s += f_char;
    s += r_char;
    s += tf_char;
    s += tr_char;

    int flag = get_flag(m);
    if (flag == MOVE_PROMO_QUEEN)
      s += 'q';
    else if (flag == MOVE_PROMO_ROOK)
      s += 'r';
    else if (flag == MOVE_PROMO_BISHOP)
      s += 'b';
    else if (flag == MOVE_PROMO_KNIGHT)
      s += 'n';

    if (s == move_str)
      return m;
  }
  return 0;
}

void go_thread(Board board, SearchLimits limits) {
  Move best_move = iterative_deepening(board, limits);

  if (best_move == 0) {
    std::cout << "bestmove 0000\n";
    return;
  }

  char f_char = 'a' + (get_from(best_move) % 8);
  char r_char = '8' - (get_from(best_move) / 8);
  char tf_char = 'a' + (get_to(best_move) % 8);
  char tr_char = '8' - (get_to(best_move) / 8);

  std::cout << "bestmove " << f_char << r_char << tf_char << tr_char;

  int flag = get_flag(best_move);
  if (flag == MOVE_PROMO_QUEEN)
    std::cout << "q";
  else if (flag == MOVE_PROMO_ROOK)
    std::cout << "r";
  else if (flag == MOVE_PROMO_BISHOP)
    std::cout << "b";
  else if (flag == MOVE_PROMO_KNIGHT)
    std::cout << "n";

  std::cout << "\n";
  std::cout << std::flush;
}

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
    if (!is_in_check(board, board.side_to_move ^ 1)) {
      nodes += perft(board, depth - 1);
    }
    board.unmake_move(moves[i], st);
  }
  return nodes;
}

void uci_loop() {
  Board board;
  board.set_startpos();

  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream is(line);
    std::string token;
    is >> token;

    if (token == "quit") {
      search_state.stop.store(true, std::memory_order_relaxed);
      if (search_thread.joinable())
        search_thread.join();
      break;
    } else if (token == "uci") {
      std::cout << "id name AntiGravity C++\n";
      std::cout << "id author Google Deepmind\n";
      std::cout << "uciok\n";
    } else if (token == "isready") {
      std::cout << "readyok\n";
    } else if (token == "ucinewgame") {
      tt_clear();
      board.set_startpos();
    } else if (token == "position") {
      std::string type;
      is >> type;
      if (type == "startpos") {
        board.set_startpos();
      } else if (type == "fen") {
        std::string fen = "";
        for (int i = 0; i < 6; i++) {
          std::string f_part;
          is >> f_part;
          fen += f_part + (i == 5 ? "" : " ");
        }
        board.set_fen(fen);
      }
      std::string moves_token;
      if (is >> moves_token && moves_token == "moves") {
        std::string m_str;
        while (is >> m_str) {
          Move m = parse_move(board, m_str);
          if (m != 0) {
            board.make_move(m);
          }
        }
      }
    } else if (token == "go") {
      if (search_thread.joinable()) {
        search_state.stop.store(true, std::memory_order_relaxed);
        search_thread.join();
      }
      search_state.stop.store(false, std::memory_order_relaxed);

      SearchLimits limits;
      std::string param;
      while (is >> param) {
        if (param == "wtime")
          is >> limits.wtime;
        else if (param == "btime")
          is >> limits.btime;
        else if (param == "winc")
          is >> limits.winc;
        else if (param == "binc")
          is >> limits.binc;
        else if (param == "depth")
          is >> limits.depth;
        else if (param == "movetime") {
          is >> limits.movetime;
          limits.wtime = 0;
          limits.btime = 0;
        } else if (param == "infinite")
          limits.infinite = true;
      }

      search_thread = std::thread(go_thread, board, limits);
    } else if (token == "stop") {
      search_state.stop.store(true, std::memory_order_relaxed);
      if (search_thread.joinable()) {
        search_thread.join();
      }
    } else if (token == "perft") {
      int depth = 5;
      is >> depth;
      auto start_time = std::chrono::high_resolution_clock::now();
      U64 nodes = perft(board, depth);
      auto end_time = std::chrono::high_resolution_clock::now();
      std::chrono::duration<double> diff = end_time - start_time;
      std::cout << "Depth " << depth << " Nodes: " << nodes
                << " Time: " << diff.count() << "s "
                << "NPS: " << (uint64_t)(nodes / diff.count()) << "\n";
    }
    std::cout << std::flush;
  }
}
