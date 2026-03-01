#include "movegen.h"

bool is_square_attacked(const Board &board, int sq, int by_side) {
  if (by_side == WHITE) {
    if (pawn_attacks[BLACK][sq] & board.pieces[W_PAWN])
      return true;
    if (knight_attacks[sq] & board.pieces[W_KNIGHT])
      return true;
    if (get_bishop_attacks(sq, board.occupancies[BOTH]) &
        (board.pieces[W_BISHOP] | board.pieces[W_QUEEN]))
      return true;
    if (get_rook_attacks(sq, board.occupancies[BOTH]) &
        (board.pieces[W_ROOK] | board.pieces[W_QUEEN]))
      return true;
    if (king_attacks[sq] & board.pieces[W_KING])
      return true;
  } else {
    if (pawn_attacks[WHITE][sq] & board.pieces[B_PAWN])
      return true;
    if (knight_attacks[sq] & board.pieces[B_KNIGHT])
      return true;
    if (get_bishop_attacks(sq, board.occupancies[BOTH]) &
        (board.pieces[B_BISHOP] | board.pieces[B_QUEEN]))
      return true;
    if (get_rook_attacks(sq, board.occupancies[BOTH]) &
        (board.pieces[B_ROOK] | board.pieces[B_QUEEN]))
      return true;
    if (king_attacks[sq] & board.pieces[B_KING])
      return true;
  }
  return false;
}

bool is_in_check(const Board &board, int side) {
  int king_p = (side == WHITE) ? W_KING : B_KING;
  int opp_side = (side == WHITE) ? BLACK : WHITE;
  if (board.pieces[king_p] == 0)
    return false;
  int king_sq = __builtin_ctzll(board.pieces[king_p]);
  return is_square_attacked(board, king_sq, opp_side);
}

static inline void add_move(Move *move_list, int &count, int from, int to,
                            int flag) {
  move_list[count++] = encode_move(from, to, flag);
}

static inline void add_pawn_promotions(Move *move_list, int &count, int from,
                                       int to, bool capture) {
  int base_flag =
      capture ? MOVE_PROMO_KNIGHT
              : MOVE_PROMO_KNIGHT; // For captures, we still use 8-11 but we
                                   // check captures statically later via board
                                   // occupancy in search.
  // Wait, the prompt says bits 12-15 are flags (quiet, capture, ep, castling,
  // promotion piece). Let's just use 8, 9, 10, 11 for promotions. If it's a
  // promotion on an occupied square, standard UCI interprets it as capture too.
  add_move(move_list, count, from, to, MOVE_PROMO_QUEEN);
  add_move(move_list, count, from, to, MOVE_PROMO_ROOK);
  add_move(move_list, count, from, to, MOVE_PROMO_BISHOP);
  add_move(move_list, count, from, to, MOVE_PROMO_KNIGHT);
}

int generate_moves(const Board &board, Move *move_list) {
  int count = 0;
  int side = board.side_to_move;
  int opp_side = (side == WHITE) ? BLACK : WHITE;

  // Pawns
  int pawn = (side == WHITE) ? W_PAWN : B_PAWN;
  U64 pawns = board.pieces[pawn];
  while (pawns) {
    int sq = pop_lsb(pawns);
    int r = sq / 8;
    int push_sq = (side == WHITE) ? sq - 8 : sq + 8;

    // Single push
    if (push_sq >= 0 && push_sq < 64 &&
        !get_bit(board.occupancies[BOTH], push_sq)) {
      if ((side == WHITE && push_sq / 8 == 0) ||
          (side == BLACK && push_sq / 8 == 7)) {
        add_pawn_promotions(move_list, count, sq, push_sq, false);
      } else {
        add_move(move_list, count, sq, push_sq, MOVE_QUIET);
        // Double push
        if ((side == WHITE && r == 6) || (side == BLACK && r == 1)) {
          int dpush_sq = (side == WHITE) ? sq - 16 : sq + 16;
          if (!get_bit(board.occupancies[BOTH], dpush_sq)) {
            add_move(move_list, count, sq, dpush_sq, MOVE_DOUBLE_PAWN);
          }
        }
      }
    }

    // Captures
    U64 attacks = pawn_attacks[side][sq] & board.occupancies[opp_side];
    while (attacks) {
      int to = pop_lsb(attacks);
      if ((side == WHITE && to / 8 == 0) || (side == BLACK && to / 8 == 7)) {
        add_pawn_promotions(move_list, count, sq, to, true);
      } else {
        add_move(move_list, count, sq, to, MOVE_CAPTURE);
      }
    }

    // En Passant
    if (board.ep_square != -1) {
      U64 ep_attacks = pawn_attacks[side][sq] & (1ULL << board.ep_square);
      if (ep_attacks) {
        add_move(move_list, count, sq, board.ep_square, MOVE_EP);
      }
    }
  }

  // Pieces
  int pieces_types[4] = {W_KNIGHT, W_BISHOP, W_ROOK, W_QUEEN};
  if (side == BLACK) {
    pieces_types[0] += 6;
    pieces_types[1] += 6;
    pieces_types[2] += 6;
    pieces_types[3] += 6;
  }

  for (int pt : pieces_types) {
    U64 pieces_bb = board.pieces[pt];
    while (pieces_bb) {
      int sq = pop_lsb(pieces_bb);
      U64 attacks = 0ULL;
      if (pt == W_KNIGHT || pt == B_KNIGHT)
        attacks = knight_attacks[sq];
      else if (pt == W_BISHOP || pt == B_BISHOP)
        attacks = get_bishop_attacks(sq, board.occupancies[BOTH]);
      else if (pt == W_ROOK || pt == B_ROOK)
        attacks = get_rook_attacks(sq, board.occupancies[BOTH]);
      else if (pt == W_QUEEN || pt == B_QUEEN)
        attacks = get_queen_attacks(sq, board.occupancies[BOTH]);

      attacks &= ~board.occupancies[side];
      while (attacks) {
        int to = pop_lsb(attacks);
        int flag = get_bit(board.occupancies[opp_side], to) ? MOVE_CAPTURE
                                                            : MOVE_QUIET;
        add_move(move_list, count, sq, to, flag);
      }
    }
  }

  // King
  int king = (side == WHITE) ? W_KING : B_KING;
  U64 king_bb = board.pieces[king];
  if (king_bb) {
    int sq = __builtin_ctzll(king_bb);
    U64 attacks = king_attacks[sq] & ~board.occupancies[side];
    while (attacks) {
      int to = pop_lsb(attacks);
      int flag =
          get_bit(board.occupancies[opp_side], to) ? MOVE_CAPTURE : MOVE_QUIET;
      add_move(move_list, count, sq, to, flag);
    }

    // Castling
    if (side == WHITE) {
      if (board.castling_rights & CASTLE_WK) {
        // f1(61), g1(62)
        if (!get_bit(board.occupancies[BOTH], 61) &&
            !get_bit(board.occupancies[BOTH], 62)) {
          if (!is_square_attacked(board, 60, BLACK) &&
              !is_square_attacked(board, 61, BLACK) &&
              !is_square_attacked(board, 62, BLACK)) {
            add_move(move_list, count, 60, 62, MOVE_KING_CASTLE);
          }
        }
      }
      if (board.castling_rights & CASTLE_WQ) {
        // b1(57), c1(58), d1(59)
        if (!get_bit(board.occupancies[BOTH], 57) &&
            !get_bit(board.occupancies[BOTH], 58) &&
            !get_bit(board.occupancies[BOTH], 59)) {
          if (!is_square_attacked(board, 60, BLACK) &&
              !is_square_attacked(board, 59, BLACK) &&
              !is_square_attacked(board, 58, BLACK)) {
            add_move(move_list, count, 60, 58, MOVE_QUEEN_CASTLE);
          }
        }
      }
    } else {
      if (board.castling_rights & CASTLE_BK) {
        // f8(5), g8(6)
        if (!get_bit(board.occupancies[BOTH], 5) &&
            !get_bit(board.occupancies[BOTH], 6)) {
          if (!is_square_attacked(board, 4, WHITE) &&
              !is_square_attacked(board, 5, WHITE) &&
              !is_square_attacked(board, 6, WHITE)) {
            add_move(move_list, count, 4, 6, MOVE_KING_CASTLE);
          }
        }
      }
      if (board.castling_rights & CASTLE_BQ) {
        // b8(1), c8(2), d8(3)
        if (!get_bit(board.occupancies[BOTH], 1) &&
            !get_bit(board.occupancies[BOTH], 2) &&
            !get_bit(board.occupancies[BOTH], 3)) {
          if (!is_square_attacked(board, 4, WHITE) &&
              !is_square_attacked(board, 3, WHITE) &&
              !is_square_attacked(board, 2, WHITE)) {
            add_move(move_list, count, 4, 2, MOVE_QUEEN_CASTLE);
          }
        }
      }
    }
  }

  return count;
}

int generate_captures(const Board &board, Move *move_list) {
  int count = 0;
  int side = board.side_to_move;
  int opp_side = (side == WHITE) ? BLACK : WHITE;

  // Pawns
  int pawn = (side == WHITE) ? W_PAWN : B_PAWN;
  U64 pawns = board.pieces[pawn];
  while (pawns) {
    int sq = pop_lsb(pawns);
    int push_sq = (side == WHITE) ? sq - 8 : sq + 8;

    // Promotion quiet pushing is sometimes considered in QS, but usually just
    // queen promotions
    if (push_sq >= 0 && push_sq < 64 &&
        !get_bit(board.occupancies[BOTH], push_sq)) {
      if ((side == WHITE && push_sq / 8 == 0) ||
          (side == BLACK && push_sq / 8 == 7)) {
        add_move(move_list, count, sq, push_sq,
                 MOVE_PROMO_QUEEN); // Only Queen promo
      }
    }

    // Captures
    U64 attacks = pawn_attacks[side][sq] & board.occupancies[opp_side];
    while (attacks) {
      int to = pop_lsb(attacks);
      if ((side == WHITE && to / 8 == 0) || (side == BLACK && to / 8 == 7)) {
        add_pawn_promotions(move_list, count, sq, to, true);
      } else {
        add_move(move_list, count, sq, to, MOVE_CAPTURE);
      }
    }

    // En Passant
    if (board.ep_square != -1) {
      U64 ep_attacks = pawn_attacks[side][sq] & (1ULL << board.ep_square);
      if (ep_attacks) {
        add_move(move_list, count, sq, board.ep_square, MOVE_EP);
      }
    }
  }

  // Pieces
  int pieces_types[4] = {W_KNIGHT, W_BISHOP, W_ROOK, W_QUEEN};
  if (side == BLACK) {
    pieces_types[0] += 6;
    pieces_types[1] += 6;
    pieces_types[2] += 6;
    pieces_types[3] += 6;
  }

  for (int pt : pieces_types) {
    U64 pieces_bb = board.pieces[pt];
    while (pieces_bb) {
      int sq = pop_lsb(pieces_bb);
      U64 attacks = 0ULL;
      if (pt == W_KNIGHT || pt == B_KNIGHT)
        attacks = knight_attacks[sq];
      else if (pt == W_BISHOP || pt == B_BISHOP)
        attacks = get_bishop_attacks(sq, board.occupancies[BOTH]);
      else if (pt == W_ROOK || pt == B_ROOK)
        attacks = get_rook_attacks(sq, board.occupancies[BOTH]);
      else if (pt == W_QUEEN || pt == B_QUEEN)
        attacks = get_queen_attacks(sq, board.occupancies[BOTH]);

      attacks &= board.occupancies[opp_side];
      while (attacks) {
        int to = pop_lsb(attacks);
        add_move(move_list, count, sq, to, MOVE_CAPTURE);
      }
    }
  }

  // King
  int king = (side == WHITE) ? W_KING : B_KING;
  U64 king_bb = board.pieces[king];
  if (king_bb) {
    int sq = __builtin_ctzll(king_bb);
    U64 attacks = king_attacks[sq] & board.occupancies[opp_side];
    while (attacks) {
      int to = pop_lsb(attacks);
      add_move(move_list, count, sq, to, MOVE_CAPTURE);
    }
  }

  return count;
}
