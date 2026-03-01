#include "evaluate.h"
#include <algorithm>

// Piece Values
static constexpr int MG_VALUE[6] = {100, 320, 330, 500, 900, 20000};
static constexpr int EG_VALUE[6] = {120, 300, 330, 500, 900, 20000};

static constexpr int BISHOP_PAIR_MG = 30;
static constexpr int BISHOP_PAIR_EG = 50;

// PSTs (White, from A8=0 to H1=63)
static constexpr int PST_MG_PAWN[64] = {
    0,  0,  0,  0,   0,   0,  0,  0,  50, 50, 50,  50, 50, 50,  50, 50,
    10, 10, 20, 30,  30,  20, 10, 10, 5,  5,  10,  25, 25, 10,  5,  5,
    0,  0,  0,  20,  20,  0,  0,  0,  5,  -5, -10, 0,  0,  -10, -5, 5,
    5,  10, 10, -20, -20, 10, 10, 5,  0,  0,  0,   0,  0,  0,   0,  0};

static constexpr int PST_EG_PAWN[64] = {
    0,  0,  0,  0,  0,  0,  0,  0,  80, 80, 80, 80, 80, 80, 80, 80,
    50, 50, 50, 50, 50, 50, 50, 50, 30, 30, 30, 30, 30, 30, 30, 30,
    20, 20, 20, 20, 20, 20, 20, 20, 10, 10, 10, 10, 10, 10, 10, 10,
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0};

static constexpr int PST_MG_KNIGHT[64] = {
    -50, -40, -30, -30, -30, -30, -40, -50, -40, -20, 0,   0,   0,
    0,   -20, -40, -30, 0,   10,  15,  15,  10,  0,   -30, -30, 5,
    15,  20,  20,  15,  5,   -30, -30, 0,   15,  20,  20,  15,  0,
    -30, -30, 5,   10,  15,  15,  10,  5,   -30, -40, -20, 0,   5,
    5,   0,   -20, -40, -50, -40, -30, -30, -30, -30, -40, -50};

static constexpr int PST_MG_BISHOP[64] = {
    -20, -10, -10, -10, -10, -10, -10, -20, -10, 0,   0,   0,   0,
    0,   0,   -10, -10, 0,   5,   10,  10,  5,   0,   -10, -10, 5,
    5,   10,  10,  5,   5,   -10, -10, 0,   10,  10,  10,  10,  0,
    -10, -10, 10,  10,  10,  10,  10,  10,  -10, -10, 5,   0,   0,
    0,   0,   5,   -10, -20, -10, -10, -10, -10, -10, -10, -20};

static constexpr int PST_MG_ROOK[64] = {
    0,  0, 0, 0, 0, 0, 0, 0,  5,  10, 10, 10, 10, 10, 10, 5,
    -5, 0, 0, 0, 0, 0, 0, -5, -5, 0,  0,  0,  0,  0,  0,  -5,
    -5, 0, 0, 0, 0, 0, 0, -5, -5, 0,  0,  0,  0,  0,  0,  -5,
    -5, 0, 0, 0, 0, 0, 0, -5, 0,  0,  0,  5,  5,  0,  0,  0};

static constexpr int PST_MG_QUEEN[64] = {
    -20, -10, -10, -5, -5, -10, -10, -20, -10, 0,   0,   0,  0,  0,   0,   -10,
    -10, 0,   5,   5,  5,  5,   0,   -10, -5,  0,   5,   5,  5,  5,   0,   -5,
    0,   0,   5,   5,  5,  5,   0,   -5,  -10, 5,   5,   5,  5,  5,   0,   -10,
    -10, 0,   5,   0,  0,  0,   0,   -10, -20, -10, -10, -5, -5, -10, -10, -20};

static constexpr int PST_MG_KING[64] = {
    -30, -40, -40, -50, -50, -40, -40, -30, -30, -40, -40, -50, -50,
    -40, -40, -30, -30, -40, -40, -50, -50, -40, -40, -30, -30, -40,
    -40, -50, -50, -40, -40, -30, -20, -30, -30, -40, -40, -30, -30,
    -20, -10, -20, -20, -20, -20, -20, -20, -10, 20,  20,  0,   0,
    0,   0,   20,  20,  20,  30,  10,  0,   0,   10,  30,  20};

static constexpr int PST_EG_KING[64] = {
    -50, -40, -30, -20, -20, -30, -40, -50, -30, -20, -10, 0,   0,
    -10, -20, -30, -30, -10, 20,  30,  30,  20,  -10, -30, -30, -10,
    30,  40,  40,  30,  -10, -30, -30, -10, 30,  40,  40,  30,  -10,
    -30, -30, -10, 20,  30,  30,  20,  -10, -30, -30, -30, 0,   0,
    0,   0,   -30, -30, -50, -30, -30, -30, -30, -30, -30, -50};

// Passed Pawn Bonus (rank 1 to 6)
static constexpr int PASS_BONUS[8] = {0, 120, 90, 60, 40, 20, 10, 0};

inline int flip_sq(int sq) { return sq ^ 56; }

int evaluate(const Board &board) {
  int score_mg = 0;
  int score_eg = 0;

  int w_pawns = __builtin_popcountll(board.pieces[W_PAWN]);
  int b_pawns = __builtin_popcountll(board.pieces[B_PAWN]);
  int w_knights = __builtin_popcountll(board.pieces[W_KNIGHT]);
  int b_knights = __builtin_popcountll(board.pieces[B_KNIGHT]);
  int w_bishops = __builtin_popcountll(board.pieces[W_BISHOP]);
  int b_bishops = __builtin_popcountll(board.pieces[B_BISHOP]);
  int w_rooks = __builtin_popcountll(board.pieces[W_ROOK]);
  int b_rooks = __builtin_popcountll(board.pieces[B_ROOK]);
  int w_queens = __builtin_popcountll(board.pieces[W_QUEEN]);
  int b_queens = __builtin_popcountll(board.pieces[B_QUEEN]);

  // Phase
  int phase = (w_queens + b_queens) * 4 + (w_rooks + b_rooks) * 2 +
              (w_bishops + b_bishops) + (w_knights + b_knights);
  if (phase > 24)
    phase = 24;

  // Material
  score_mg += (w_pawns - b_pawns) * MG_VALUE[0];
  score_eg += (w_pawns - b_pawns) * EG_VALUE[0];
  score_mg += (w_knights - b_knights) * MG_VALUE[1];
  score_eg += (w_knights - b_knights) * EG_VALUE[1];
  score_mg += (w_bishops - b_bishops) * MG_VALUE[2];
  score_eg += (w_bishops - b_bishops) * EG_VALUE[2];
  score_mg += (w_rooks - b_rooks) * MG_VALUE[3];
  score_eg += (w_rooks - b_rooks) * EG_VALUE[3];
  score_mg += (w_queens - b_queens) * MG_VALUE[4];
  score_eg += (w_queens - b_queens) * EG_VALUE[4];

  // Bishop pair
  if (w_bishops >= 2) {
    score_mg += BISHOP_PAIR_MG;
    score_eg += BISHOP_PAIR_EG;
  }
  if (b_bishops >= 2) {
    score_mg -= BISHOP_PAIR_MG;
    score_eg -= BISHOP_PAIR_EG;
  }

  // Evaluate pieces
  U64 bb;

  // White Pawns
  bb = board.pieces[W_PAWN];
  int w_p_counts[8] = {0};
  while (bb) {
    int sq = __builtin_ctzll(bb);
    int r = sq / 8;
    int f = sq % 8;
    w_p_counts[f]++;
    score_mg += PST_MG_PAWN[sq];
    score_eg += PST_EG_PAWN[sq];

    // Passed Pawn
    U64 block_mask = 0ULL;
    for (int row = r - 1; row >= 0; row--) {
      block_mask |= (1ULL << (row * 8 + f));
      if (f > 0)
        block_mask |= (1ULL << (row * 8 + (f - 1)));
      if (f < 7)
        block_mask |= (1ULL << (row * 8 + (f + 1)));
    }
    if ((block_mask & board.pieces[B_PAWN]) == 0) {
      score_mg += PASS_BONUS[r];
      score_eg += PASS_BONUS[r] * 2;
    }
    bb &= bb - 1;
  }

  // Black Pawns
  bb = board.pieces[B_PAWN];
  int b_p_counts[8] = {0};
  while (bb) {
    int sq = __builtin_ctzll(bb);
    int r = sq / 8;
    int f = sq % 8;
    b_p_counts[f]++;
    score_mg -= PST_MG_PAWN[flip_sq(sq)];
    score_eg -= PST_EG_PAWN[flip_sq(sq)];

    // Passed Pawn
    U64 block_mask = 0ULL;
    for (int row = r + 1; row <= 7; row++) {
      block_mask |= (1ULL << (row * 8 + f));
      if (f > 0)
        block_mask |= (1ULL << (row * 8 + (f - 1)));
      if (f < 7)
        block_mask |= (1ULL << (row * 8 + (f + 1)));
    }
    if ((block_mask & board.pieces[W_PAWN]) == 0) {
      score_mg -= PASS_BONUS[7 - r];
      score_eg -= PASS_BONUS[7 - r] * 2;
    }
    bb &= bb - 1;
  }

  // Structure
  for (int f = 0; f < 8; f++) {
    // Doubled Pawns
    if (w_p_counts[f] > 1) {
      score_mg -= 20;
      score_eg -= 20;
    }
    if (b_p_counts[f] > 1) {
      score_mg += 20;
      score_eg += 20;
    }

    // Isolated Pawns
    if (w_p_counts[f] > 0) {
      if ((f == 0 || w_p_counts[f - 1] == 0) &&
          (f == 7 || w_p_counts[f + 1] == 0)) {
        score_mg -= 15 * w_p_counts[f];
        score_eg -= 15 * w_p_counts[f];
      }
    }
    if (b_p_counts[f] > 0) {
      if ((f == 0 || b_p_counts[f - 1] == 0) &&
          (f == 7 || b_p_counts[f + 1] == 0)) {
        score_mg += 15 * b_p_counts[f];
        score_eg += 15 * b_p_counts[f];
      }
    }
  }

  // Knights
  bb = board.pieces[W_KNIGHT];
  while (bb) {
    int sq = __builtin_ctzll(bb);
    score_mg += PST_MG_KNIGHT[sq];
    score_eg += PST_MG_KNIGHT[sq];
    bb &= bb - 1;
  }
  bb = board.pieces[B_KNIGHT];
  while (bb) {
    int sq = __builtin_ctzll(bb);
    score_mg -= PST_MG_KNIGHT[flip_sq(sq)];
    score_eg -= PST_MG_KNIGHT[flip_sq(sq)];
    bb &= bb - 1;
  }

  // Bishops
  bb = board.pieces[W_BISHOP];
  while (bb) {
    int sq = __builtin_ctzll(bb);
    score_mg += PST_MG_BISHOP[sq];
    score_eg += PST_MG_BISHOP[sq];
    bb &= bb - 1;
  }
  bb = board.pieces[B_BISHOP];
  while (bb) {
    int sq = __builtin_ctzll(bb);
    score_mg -= PST_MG_BISHOP[flip_sq(sq)];
    score_eg -= PST_MG_BISHOP[flip_sq(sq)];
    bb &= bb - 1;
  }

  // Rooks
  bb = board.pieces[W_ROOK];
  while (bb) {
    int sq = __builtin_ctzll(bb);
    score_mg += PST_MG_ROOK[sq];
    score_eg += PST_MG_ROOK[sq];
    bb &= bb - 1;
  }
  bb = board.pieces[B_ROOK];
  while (bb) {
    int sq = __builtin_ctzll(bb);
    score_mg -= PST_MG_ROOK[flip_sq(sq)];
    score_eg -= PST_MG_ROOK[flip_sq(sq)];
    bb &= bb - 1;
  }

  // Queens
  bb = board.pieces[W_QUEEN];
  while (bb) {
    int sq = __builtin_ctzll(bb);
    score_mg += PST_MG_QUEEN[sq];
    score_eg += PST_MG_QUEEN[sq];
    bb &= bb - 1;
  }
  bb = board.pieces[B_QUEEN];
  while (bb) {
    int sq = __builtin_ctzll(bb);
    score_mg -= PST_MG_QUEEN[flip_sq(sq)];
    score_eg -= PST_MG_QUEEN[flip_sq(sq)];
    bb &= bb - 1;
  }

  // Kings
  bb = board.pieces[W_KING];
  if (bb) {
    int sq = __builtin_ctzll(bb);
    score_mg += PST_MG_KING[sq];
    score_eg += PST_EG_KING[sq];
  }
  bb = board.pieces[B_KING];
  if (bb) {
    int sq = __builtin_ctzll(bb);
    score_mg -= PST_MG_KING[flip_sq(sq)];
    score_eg -= PST_EG_KING[flip_sq(sq)];
  }

  int score = (score_mg * phase + score_eg * (24 - phase)) / 24;
  return (board.side_to_move == WHITE) ? score : -score;
}
