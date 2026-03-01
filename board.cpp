#include "board.h"
#include <iostream>
#include <random>
#include <sstream>

U64 zobrist_piece[12][64];
U64 zobrist_side;
U64 zobrist_castling[16];
U64 zobrist_ep[8];

void init_zobrist() {
  std::mt19937_64 rng(1804289383ULL);
  for (int p = 0; p < 12; p++) {
    for (int sq = 0; sq < 64; sq++) {
      zobrist_piece[p][sq] = rng();
    }
  }
  zobrist_side = rng();
  for (int i = 0; i < 16; i++) {
    zobrist_castling[i] = rng();
  }
  for (int i = 0; i < 8; i++) {
    zobrist_ep[i] = rng();
  }
}

Board::Board() { set_startpos(); }

void Board::set_startpos() {
  set_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
}

void Board::update_occupancies() {
  occupancies[WHITE] = 0ULL;
  occupancies[BLACK] = 0ULL;
  occupancies[BOTH] = 0ULL;
  for (int p = W_PAWN; p <= W_KING; p++)
    occupancies[WHITE] |= pieces[p];
  for (int p = B_PAWN; p <= B_KING; p++)
    occupancies[BLACK] |= pieces[p];
  occupancies[BOTH] = occupancies[WHITE] | occupancies[BLACK];
}

U64 Board::compute_zobrist() const {
  U64 hash = 0ULL;
  for (int p = 0; p < 12; p++) {
    U64 bb = pieces[p];
    while (bb) {
      int sq = __builtin_ctzll(bb);
      hash ^= zobrist_piece[p][sq];
      bb &= bb - 1;
    }
  }
  if (side_to_move == BLACK)
    hash ^= zobrist_side;
  hash ^= zobrist_castling[castling_rights];
  if (ep_square != -1)
    hash ^= zobrist_ep[ep_square % 8];
  return hash;
}

void Board::set_fen(const std::string &fen) {
  for (int p = 0; p < 12; p++)
    pieces[p] = 0ULL;

  int sq = 0; // a8
  size_t i = 0;
  while (i < fen.length() && fen[i] != ' ') {
    char c = fen[i++];
    if (c == '/')
      continue;
    if (isdigit(c)) {
      sq += (c - '0');
    } else {
      int p = -1;
      switch (c) {
      case 'P':
        p = W_PAWN;
        break;
      case 'N':
        p = W_KNIGHT;
        break;
      case 'B':
        p = W_BISHOP;
        break;
      case 'R':
        p = W_ROOK;
        break;
      case 'Q':
        p = W_QUEEN;
        break;
      case 'K':
        p = W_KING;
        break;
      case 'p':
        p = B_PAWN;
        break;
      case 'n':
        p = B_KNIGHT;
        break;
      case 'b':
        p = B_BISHOP;
        break;
      case 'r':
        p = B_ROOK;
        break;
      case 'q':
        p = B_QUEEN;
        break;
      case 'k':
        p = B_KING;
        break;
      }
      if (p != -1)
        pieces[p] |= (1ULL << sq);
      sq++;
    }
  }

  side_to_move = WHITE;
  if (i < fen.length() && fen[++i] == 'b')
    side_to_move = BLACK;
  i += 2;

  castling_rights = 0;
  while (i < fen.length() && fen[i] != ' ') {
    if (fen[i] == 'K')
      castling_rights |= CASTLE_WK;
    if (fen[i] == 'Q')
      castling_rights |= CASTLE_WQ;
    if (fen[i] == 'k')
      castling_rights |= CASTLE_BK;
    if (fen[i] == 'q')
      castling_rights |= CASTLE_BQ;
    i++;
  }
  i++;

  ep_square = -1;
  if (i < fen.length() && fen[i] != '-') {
    int f = fen[i] - 'a';
    int r = 8 - (fen[i + 1] - '0'); // Rank 1 is r=7, Rank 8 is r=0
    ep_square = r * 8 + f;
    i += 2;
  } else {
    if (i < fen.length())
      i++;
  }
  i++;

  halfmove_clock = 0;
  fullmove_number = 1;

  if (i < fen.length()) {
    std::stringstream ss(fen.substr(i));
    ss >> halfmove_clock >> fullmove_number;
  }

  update_occupancies();
  zobrist_hash = compute_zobrist();
}

std::string Board::get_fen() const {
  std::stringstream fen;
  int empty = 0;
  const char ascii_pieces[13] = {'P', 'N', 'B', 'R', 'Q', 'K', 'p',
                                 'n', 'b', 'r', 'q', 'k', ' '};
  for (int r = 0; r < 8; r++) {
    for (int f = 0; f < 8; f++) {
      int sq = r * 8 + f;
      int p = get_piece_on_square(sq);
      if (p == EMPTY_PIECE) {
        empty++;
      } else {
        if (empty > 0) {
          fen << empty;
          empty = 0;
        }
        fen << ascii_pieces[p];
      }
    }
    if (empty > 0) {
      fen << empty;
      empty = 0;
    }
    if (r < 7)
      fen << '/';
  }

  fen << ' ' << (side_to_move == WHITE ? 'w' : 'b') << ' ';

  if (castling_rights == 0) {
    fen << '-';
  } else {
    if (castling_rights & CASTLE_WK)
      fen << 'K';
    if (castling_rights & CASTLE_WQ)
      fen << 'Q';
    if (castling_rights & CASTLE_BK)
      fen << 'k';
    if (castling_rights & CASTLE_BQ)
      fen << 'q';
  }

  fen << ' ';
  if (ep_square == -1) {
    fen << '-';
  } else {
    char file = 'a' + (ep_square % 8);
    char rank = '8' - (ep_square / 8);
    fen << file << rank;
  }

  fen << ' ' << halfmove_clock << ' ' << fullmove_number;
  return fen.str();
}

int Board::get_piece_on_square(int sq) const {
  U64 mask = 1ULL << sq;
  for (int p = 0; p < 12; p++) {
    if (pieces[p] & mask)
      return p;
  }
  return EMPTY_PIECE;
}

BoardState Board::save_state() const {
  return {castling_rights, ep_square, halfmove_clock, zobrist_hash,
          EMPTY_PIECE};
}

// Ensure flags match bit manipulations
static const uint8_t castling_perms[64] = {
    7,  15, 15, 15, 3,  15, 15, 11, 15, 15, 15, 15, 15, 15, 15, 15,
    15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    15, 15, 15, 15, 15, 15, 15, 15, 13, 15, 15, 15, 12, 15, 15, 14};
// a8=0 -> ~CASTLE_BQ (11: 1011) ? Wait:
// a8 = 0. Black queen rook. Removes BQ (8). ~8 = 7! So 7.
// e8 = 4. Black king. Removes BK(4)|BQ(8). ~12 = 3.
// h8 = 7. Black king rook. Removes BK(4). ~4 = 11.
// a1 = 56. White queen rook. Removes WQ(2). ~2 = 13.
// e1 = 60. White king. Removes WK(1)|WQ(2). ~3 = 12.
// h1 = 63. White king rook. Removes WK(1). ~1 = 14.

void Board::make_move(Move m) {
  int from = get_from(m);
  int to = get_to(m);
  int flag = get_flag(m);
  int piece = get_piece_on_square(from);
  int captured = get_piece_on_square(to);

  // Zobrist updates
  zobrist_hash ^= zobrist_piece[piece][from];
  pieces[piece] ^= (1ULL << from);
  pieces[piece] |= (1ULL << to);
  zobrist_hash ^= zobrist_piece[piece][to];

  if (ep_square != -1) {
    zobrist_hash ^= zobrist_ep[ep_square % 8];
    ep_square = -1;
  }
  zobrist_hash ^= zobrist_castling[castling_rights];

  halfmove_clock++;
  if (piece == W_PAWN || piece == B_PAWN || captured != EMPTY_PIECE)
    halfmove_clock = 0;

  if (flag == MOVE_CAPTURE) {
    pieces[captured] ^= (1ULL << to);
    zobrist_hash ^= zobrist_piece[captured][to];
  } else if (flag == MOVE_EP) {
    int cap_sq = (side_to_move == WHITE) ? to + 8 : to - 8;
    int cap_p = (side_to_move == WHITE) ? B_PAWN : W_PAWN;
    pieces[cap_p] ^= (1ULL << cap_sq);
    zobrist_hash ^= zobrist_piece[cap_p][cap_sq];
  } else if (flag == MOVE_DOUBLE_PAWN) {
    ep_square = (side_to_move == WHITE) ? to + 8 : to - 8;
    zobrist_hash ^= zobrist_ep[ep_square % 8];
  } else if (flag == MOVE_KING_CASTLE) {
    int rook = (side_to_move == WHITE) ? W_ROOK : B_ROOK;
    int r_from = to + 1; // h1/h8
    int r_to = to - 1;   // f1/f8
    pieces[rook] ^= (1ULL << r_from);
    pieces[rook] |= (1ULL << r_to);
    zobrist_hash ^= zobrist_piece[rook][r_from];
    zobrist_hash ^= zobrist_piece[rook][r_to];
  } else if (flag == MOVE_QUEEN_CASTLE) {
    int rook = (side_to_move == WHITE) ? W_ROOK : B_ROOK;
    int r_from = to - 2; // a1/a8
    int r_to = to + 1;   // d1/d8
    pieces[rook] ^= (1ULL << r_from);
    pieces[rook] |= (1ULL << r_to);
    zobrist_hash ^= zobrist_piece[rook][r_from];
    zobrist_hash ^= zobrist_piece[rook][r_to];
  } else if (flag >= MOVE_PROMO_KNIGHT) {
    // Promotion capture
    if (captured != EMPTY_PIECE) {
      pieces[captured] ^= (1ULL << to);
      zobrist_hash ^= zobrist_piece[captured][to];
    }
    pieces[piece] ^= (1ULL << to); // remove pawn
    zobrist_hash ^= zobrist_piece[piece][to];

    int offset = (side_to_move == WHITE) ? 0 : 6;
    int promo_piece = -1;
    if (flag == MOVE_PROMO_KNIGHT)
      promo_piece = W_KNIGHT + offset;
    else if (flag == MOVE_PROMO_BISHOP)
      promo_piece = W_BISHOP + offset;
    else if (flag == MOVE_PROMO_ROOK)
      promo_piece = W_ROOK + offset;
    else if (flag == MOVE_PROMO_QUEEN)
      promo_piece = W_QUEEN + offset;

    pieces[promo_piece] |= (1ULL << to);
    zobrist_hash ^= zobrist_piece[promo_piece][to];
  }

  castling_rights &= castling_perms[from];
  castling_rights &= castling_perms[to];
  zobrist_hash ^= zobrist_castling[castling_rights];

  side_to_move ^= 1;
  zobrist_hash ^= zobrist_side;
  if (side_to_move == WHITE)
    fullmove_number++;

  update_occupancies();
}

void Board::unmake_move(Move m, const BoardState &state) {
  side_to_move ^= 1;
  if (side_to_move == BLACK)
    fullmove_number--;

  int from = get_from(m);
  int to = get_to(m);
  int flag = get_flag(m);
  int piece = get_piece_on_square(to);

  if (flag >= MOVE_PROMO_KNIGHT) {
    int pawn = (side_to_move == WHITE) ? W_PAWN : B_PAWN;
    pieces[piece] ^= (1ULL << to); // remove promo piece
    pieces[pawn] |= (1ULL << to);  // put pawn back for loop inverse
    piece = pawn;
  }

  pieces[piece] &= ~(1ULL << to);
  pieces[piece] |= (1ULL << from);

  if (flag == MOVE_CAPTURE ||
      (flag >= MOVE_PROMO_KNIGHT && state.captured_piece != EMPTY_PIECE)) {
    pieces[state.captured_piece] |= (1ULL << to);
  } else if (flag == MOVE_EP) {
    int cap_sq = (side_to_move == WHITE) ? to + 8 : to - 8;
    int cap_p = (side_to_move == WHITE) ? B_PAWN : W_PAWN;
    pieces[cap_p] |= (1ULL << cap_sq);
  } else if (flag == MOVE_KING_CASTLE) {
    int rook = (side_to_move == WHITE) ? W_ROOK : B_ROOK;
    pieces[rook] &= ~(1ULL << (to - 1));
    pieces[rook] |= (1ULL << (to + 1));
  } else if (flag == MOVE_QUEEN_CASTLE) {
    int rook = (side_to_move == WHITE) ? W_ROOK : B_ROOK;
    pieces[rook] &= ~(1ULL << (to + 1));
    pieces[rook] |= (1ULL << (to - 2));
  }

  castling_rights = state.castling_rights;
  ep_square = state.ep_square;
  halfmove_clock = state.halfmove_clock;
  zobrist_hash = state.zobrist_hash;

  update_occupancies();
}

void Board::print() const {
  const char ascii_pieces[13] = {'P', 'N', 'B', 'R', 'Q', 'K', 'p',
                                 'n', 'b', 'r', 'q', 'k', '.'};
  for (int r = 0; r < 8; r++) {
    for (int f = 0; f < 8; f++) {
      int sq = r * 8 + f;
      int p = get_piece_on_square(sq);
      std::cout << ascii_pieces[p] << " ";
    }
    std::cout << "\n";
  }
  std::cout << "Side: " << (side_to_move == WHITE ? "White" : "Black") << "\n";
  std::cout << "EP: " << ep_square << "\n";
  std::cout << "Hash: " << std::hex << zobrist_hash << std::dec << "\n\n";
}
