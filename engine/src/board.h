#pragma once
#include <cstdint>
#include <string>
#include <vector>

typedef uint64_t U64;

enum Piece {
  W_PAWN,
  W_KNIGHT,
  W_BISHOP,
  W_ROOK,
  W_QUEEN,
  W_KING,
  B_PAWN,
  B_KNIGHT,
  B_BISHOP,
  B_ROOK,
  B_QUEEN,
  B_KING,
  EMPTY_PIECE
};

enum Color { WHITE, BLACK, BOTH };

// Move representation as uint32_t
// bits 0-5: from square (0-63)
// bits 6-11: to square (0-63)
// bits 12-15: flags
// flags:
// 0: quiet
// 1: double pawn push
// 2: king castle
// 3: queen castle
// 4: captures
// 5: ep capture
// 8-15: promotions (e.g. 8=knight promo, 9=bishop, 10=rook, 11=queen)
// Wait, prompt request: bits 12-15: flags (quiet, capture, ep, castling,
// promotion piece). Let's define the flags:
#define MOVE_QUIET 0
#define MOVE_DOUBLE_PAWN 1
#define MOVE_KING_CASTLE 2
#define MOVE_QUEEN_CASTLE 3
#define MOVE_CAPTURE 4
#define MOVE_EP 5
#define MOVE_PROMO_KNIGHT 8
#define MOVE_PROMO_BISHOP 9
#define MOVE_PROMO_ROOK 10
#define MOVE_PROMO_QUEEN 11

typedef uint32_t Move;

inline Move encode_move(int from, int to, int flag) {
  return (from & 0x3F) | ((to & 0x3F) << 6) | ((flag & 0xF) << 12);
}

inline int get_from(Move move) { return move & 0x3F; }
inline int get_to(Move move) { return (move >> 6) & 0x3F; }
inline int get_flag(Move move) { return (move >> 12) & 0xF; }

// Castling rights mapping: K=1, Q=2, k=4, q=8
#define CASTLE_WK 1
#define CASTLE_WQ 2
#define CASTLE_BK 4
#define CASTLE_BQ 8

struct BoardState {
  uint8_t castling_rights;
  int ep_square;
  int halfmove_clock;
  uint64_t zobrist_hash;
  int captured_piece; // To restore efficiently
};

extern U64 zobrist_side;

void init_zobrist();

class Board {
public:
  U64 pieces[12];
  U64 occupancies[3]; // WHITE, BLACK, BOTH

  int side_to_move;        // 0=white, 1=black
  uint8_t castling_rights; // 4 bits: KQkq
  int ep_square;           // -1 if none, 0-63 otherwise
  int halfmove_clock;
  int fullmove_number;
  U64 zobrist_hash;

  Board();

  void set_startpos();
  void set_fen(const std::string &fen);
  std::string get_fen() const;

  void make_move(Move m);
  void unmake_move(Move m, const BoardState &saved_state);
  BoardState save_state() const;

  int get_piece_on_square(int sq) const;
  void print() const;

  // Internal updaters
  void update_occupancies();
  U64 compute_zobrist() const;
};
