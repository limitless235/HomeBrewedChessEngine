#pragma once
#include <cstdint>

typedef uint64_t U64;

// Precomputed attack tables
extern U64 knight_attacks[64];
extern U64 king_attacks[64];
extern U64 pawn_attacks[2][64];

extern const U64 RookMagics[64];
extern U64 RookMasks[64];
extern int RookShifts[64];
extern U64 RookAttacks[64][4096];

extern const U64 BishopMagics[64];
extern U64 BishopMasks[64];
extern int BishopShifts[64];
extern U64 BishopAttacks[64][512];

void init_attacks();

// Inline bit manipulation
inline int pop_lsb(U64 &b) {
  int ls1b = __builtin_ctzll(b);
  b &= b - 1;
  return ls1b;
}

inline int count_bits(U64 b) { return __builtin_popcountll(b); }

inline void set_bit(U64 &bitboard, int square) { bitboard |= (1ULL << square); }

inline void clear_bit(U64 &bitboard, int square) {
  bitboard &= ~(1ULL << square);
}

inline bool get_bit(U64 bitboard, int square) {
  return (bitboard & (1ULL << square)) != 0;
}

// Fast Magic Bitboard lookups
inline U64 get_rook_attacks(int sq, U64 occupancy) {
  occupancy &= RookMasks[sq];
  occupancy *= RookMagics[sq];
  occupancy >>= RookShifts[sq];
  return RookAttacks[sq][occupancy];
}

inline U64 get_bishop_attacks(int sq, U64 occupancy) {
  occupancy &= BishopMasks[sq];
  occupancy *= BishopMagics[sq];
  occupancy >>= BishopShifts[sq];
  return BishopAttacks[sq][occupancy];
}

inline U64 get_queen_attacks(int sq, U64 occupancy) {
  return get_rook_attacks(sq, occupancy) | get_bishop_attacks(sq, occupancy);
}
