#include "search.h"
#include "evaluate.h"
#include <algorithm>
#include <chrono>
#include <iostream>

SearchState search_state;

static const int LMR_TABLE[64][64] = {
    // Basic LMR matrix
    // ...
};

// Function prototypes
static int move_score(Move move, Move tt_move, int ply, const Board &board);
static void sort_moves(Move *moves, int count, Move tt_move, int ply,
                       const Board &board);

int get_time_ms() {
  return std::chrono::duration_cast<std::chrono::milliseconds>(
             std::chrono::steady_clock::now().time_since_epoch())
      .count();
}

void check_limits() {
  if ((search_state.nodes & 2047) == 0) {
    if (search_state.stop.load(std::memory_order_relaxed)) {
      search_state.limits_reached = true;
    } else if (search_state.hard_limit_ms > 0) {
      long long elapsed = get_time_ms() - search_state.start_time_ms;
      if (elapsed >= search_state.hard_limit_ms) {
        search_state.limits_reached = true;
        search_state.stop.store(true, std::memory_order_relaxed);
      }
    }
  }
}

int quiescence(Board &board, int alpha, int beta, int ply) {
  search_state.nodes++;
  check_limits();
  if (search_state.limits_reached)
    return 0;

  int stand_pat = evaluate(board);
  if (stand_pat >= beta)
    return beta;
  if (alpha < stand_pat)
    alpha = stand_pat;

  Move moves[256];
  int count = generate_captures(board, moves);
  sort_moves(moves, count, 0, ply, board);

  for (int i = 0; i < count; i++) {
    Move move = moves[i];
    BoardState st = board.save_state();
    st.captured_piece = board.get_piece_on_square(get_to(move));

    board.make_move(move);

    if (is_in_check(board, board.side_to_move ^ 1)) {
      board.unmake_move(move, st);
      continue;
    }

    int score = -quiescence(board, -beta, -alpha, ply + 1);
    board.unmake_move(move, st);

    if (search_state.limits_reached)
      return 0;

    if (score >= beta)
      return beta;
    if (score > alpha)
      alpha = score;
  }

  return alpha;
}

int negamax(Board &board, int depth, int alpha, int beta, int ply,
            bool null_move_allowed) {
  search_state.nodes++;
  check_limits();
  if (search_state.limits_reached)
    return 0;

  search_state.pv_length[ply] = ply;

  // Draw conditions
  if (board.halfmove_clock >= 100)
    return 0; // Temporary repetition ignoring actual state memory

  // Check extensions
  bool in_check = is_in_check(board, board.side_to_move);
  if (in_check)
    depth++;

  // Transposition Table Probe
  int tt_score;
  Move tt_move = 0;
  if (tt_probe(board.zobrist_hash, depth, alpha, beta, tt_score, tt_move)) {
    if (ply != 0) {
      return tt_score;
    }
  }

  if (depth <= 0) {
    return quiescence(board, alpha, beta, ply);
  }

  // Null Move Pruning
  if (null_move_allowed && !in_check && depth >= 3 && evaluate(board) >= beta) {
    int R = (depth >= 6) ? 3 : 2;
    BoardState st = board.save_state();

    // Null move execution
    board.ep_square = -1;
    board.side_to_move ^= 1;
    board.zobrist_hash ^= zobrist_side;

    int null_score =
        -negamax(board, depth - 1 - R, -beta, -beta + 1, ply + 1, false);

    // Unmake null
    board.side_to_move ^= 1;
    board.ep_square = st.ep_square;
    board.zobrist_hash = st.zobrist_hash;

    if (search_state.limits_reached)
      return 0;
    if (null_score >= beta)
      return beta;
  }

  // Futility Pruning
  int static_eval = evaluate(board);
  bool futility_pruning = false;
  int futility_margin = 0;
  if (depth <= 2 && !in_check && ply != 0) {
    futility_margin = (depth == 1) ? 200 : 400;
    if (static_eval + futility_margin <= alpha) {
      futility_pruning = true;
    }
  }

  Move moves[256];
  int count = generate_moves(board, moves);
  sort_moves(moves, count, tt_move, ply, board);

  int best_score = -INF;
  Move best_move = 0;
  int original_alpha = alpha;
  int legal_moves = 0;

  for (int i = 0; i < count; i++) {
    Move move = moves[i];
    int flag = get_flag(move);
    bool is_quiet = (board.get_piece_on_square(get_to(move)) == EMPTY_PIECE &&
                     flag < MOVE_PROMO_KNIGHT && flag != MOVE_EP);

    // Futility skips
    if (futility_pruning && is_quiet && !in_check &&
        move_score(move, tt_move, ply, board) < 8000) {
      // Must verify legality to not accidentally return Stalemate when moves
      // exist
      BoardState st = board.save_state();
      board.make_move(move);
      if (is_in_check(board, board.side_to_move ^ 1)) {
        board.unmake_move(move, st);
        continue;
      }
      legal_moves++;
      board.unmake_move(move, st);

      if (static_eval > best_score)
        best_score = static_eval;
      continue;
    }

    BoardState st = board.save_state();
    st.captured_piece = board.get_piece_on_square(get_to(move));

    board.make_move(move);

    if (is_in_check(board, board.side_to_move ^ 1)) {
      board.unmake_move(move, st);
      continue;
    }
    legal_moves++;

    int score;
    bool needs_full = true;

    // Late Move Reductions (LMR)
    if (depth >= 3 && legal_moves >= 4 && is_quiet && !in_check &&
        !is_in_check(board, board.side_to_move)) {
      if (move_score(move, tt_move, ply, board) < 8000) {
        int R = 1;
        if (depth > 1 && i > 0)
          R = (depth / 3) + (i / 5);
        if (R < 1)
          R = 1;
        if (R >= depth)
          R = depth - 1;

        score =
            -negamax(board, depth - 1 - R, -alpha - 1, -alpha, ply + 1, true);
        if (score <= alpha)
          needs_full = false;
      }
    }

    // PVS / Full Window Search
    if (needs_full) {
      if (legal_moves == 1) {
        score = -negamax(board, depth - 1, -beta, -alpha, ply + 1, true);
      } else {
        score = -negamax(board, depth - 1, -alpha - 1, -alpha, ply + 1, true);
        if (score > alpha && score < beta) {
          score = -negamax(board, depth - 1, -beta, -alpha, ply + 1, true);
        }
      }
    }

    board.unmake_move(move, st);
    if (search_state.limits_reached)
      return 0;

    if (score > best_score) {
      best_score = score;
      best_move = move;

      search_state.pv[ply][ply] = move;
      for (int next = ply + 1; next < search_state.pv_length[ply + 1]; next++) {
        search_state.pv[ply][next] = search_state.pv[ply + 1][next];
      }
      search_state.pv_length[ply] = search_state.pv_length[ply + 1];

      if (score > alpha)
        alpha = score;
    }

    if (alpha >= beta) {
      if (is_quiet) {
        search_state.killers[ply][1] = search_state.killers[ply][0];
        search_state.killers[ply][0] = move;
        int p_idx = board.get_piece_on_square(get_from(move));
        search_state
            .history[board.side_to_move][get_from(move)][get_to(move)] +=
            depth * depth;
      }
      break; // Beta cutoff
    }
  }

  if (legal_moves == 0) {
    if (in_check)
      return -MATE_SCORE + ply;
    return 0; // Stalemate
  }

  int tt_flag = FLAG_EXACT;
  if (best_score <= original_alpha)
    tt_flag = FLAG_UPPERBOUND;
  else if (best_score >= beta)
    tt_flag = FLAG_LOWERBOUND;

  tt_store(board.zobrist_hash, depth, best_score, tt_flag, best_move);

  return best_score;
}

static constexpr int mvv_lva[6][6] = {
    //  P   N   B   R   Q   K
    {15, 25, 35, 45, 55, 65}, // Victim Pawn
    {14, 24, 34, 44, 54, 64}, // Victim Knight
    {13, 23, 33, 43, 53, 63}, // Victim Bishop
    {12, 22, 32, 42, 52, 62}, // Victim Rook
    {11, 21, 31, 41, 51, 61}, // Victim Queen
    {10, 20, 30, 40, 50, 60}  // Victim King
};

static int move_score(Move move, Move tt_move, int ply, const Board &board) {
  if (move == tt_move)
    return 100000;
  if (move == search_state.killers[ply][0])
    return 9000;
  if (move == search_state.killers[ply][1])
    return 8000;

  int from = get_from(move);
  int to = get_to(move);
  int flag = get_flag(move);

  if (flag == MOVE_CAPTURE || flag == MOVE_EP) {
    int attacker = board.get_piece_on_square(from) % 6;
    int victim = (flag == MOVE_EP) ? 0 : board.get_piece_on_square(to) % 6;
    return 10000 + mvv_lva[victim][attacker];
  }

  if (flag >= MOVE_PROMO_KNIGHT)
    return 10000 + 50;

  return search_state.history[board.side_to_move][from][to];
}

static void sort_moves(Move *moves, int count, Move tt_move, int ply,
                       const Board &board) {
  int scores[256];
  for (int i = 0; i < count; i++) {
    scores[i] = move_score(moves[i], tt_move, ply, board);
  }

  for (int i = 0; i < count - 1; i++) {
    int best = i;
    for (int j = i + 1; j < count; j++) {
      if (scores[j] > scores[best])
        best = j;
    }
    std::swap(moves[i], moves[best]);
    std::swap(scores[i], scores[best]);
  }
}

Move iterative_deepening(Board &board, SearchLimits limits) {
  search_state.nodes = 0;
  search_state.limits_reached = false;
  search_state.start_time_ms = get_time_ms();

  // Convert time settings to hard limit per search (roughly full time/30)
  int my_time = (board.side_to_move == WHITE) ? limits.wtime : limits.btime;
  int my_inc = (board.side_to_move == WHITE) ? limits.winc : limits.binc;

  if (limits.movetime > 0) {
    search_state.hard_limit_ms = limits.movetime;
  } else if (my_time > 0) {
    search_state.hard_limit_ms = (my_time / 30) + my_inc;
    int max_alloc = my_time / 2;
    if (search_state.hard_limit_ms > max_alloc)
      search_state.hard_limit_ms = max_alloc;
  } else {
    search_state.hard_limit_ms = 0; // Infinite
  }

  for (int i = 0; i < MAX_PLY; i++) {
    search_state.killers[i][0] = 0;
    search_state.killers[i][1] = 0;
    for (int j = 0; j < 64; j++) {
      for (int k = 0; k < 64; k++) {
        search_state.history[0][j][k] = 0;
        search_state.history[1][j][k] = 0;
      }
    }
  }

  Move best_move = 0;
  int max_depth = (limits.depth > 0) ? limits.depth : 64;

  for (int depth = 1; depth <= max_depth; depth++) {
    int alpha = -INF;
    int beta = INF;

    int score = negamax(board, depth, alpha, beta, 0, true);

    if (search_state.limits_reached)
      break;

    best_move = search_state.pv[0][0];

    std::cout << "info depth " << depth << " score cp " << score << " nodes "
              << search_state.nodes << " time "
              << (get_time_ms() - search_state.start_time_ms) << " pv ";

    for (int i = 0; i < search_state.pv_length[0]; i++) {
      Move m = search_state.pv[0][i];
      char file1 = 'a' + (get_from(m) % 8);
      char rank1 = '8' - (get_from(m) / 8);
      char file2 = 'a' + (get_to(m) % 8);
      char rank2 = '8' - (get_to(m) / 8);
      std::cout << file1 << rank1 << file2 << rank2;
      int flag = get_flag(m);
      if (flag == MOVE_PROMO_QUEEN)
        std::cout << "q";
      else if (flag == MOVE_PROMO_ROOK)
        std::cout << "r";
      else if (flag == MOVE_PROMO_BISHOP)
        std::cout << "b";
      else if (flag == MOVE_PROMO_KNIGHT)
        std::cout << "n";
      std::cout << " ";
    }
    std::cout << std::endl;

    if (score >= MATE_SCORE - MAX_PLY)
      break; // Found mate
  }

  return best_move;
}
