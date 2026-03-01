#include "attacks.h"

// Define uninitialized tables
U64 knight_attacks[64];
U64 king_attacks[64];
U64 pawn_attacks[2][64];

U64 RookMasks[64];
int RookShifts[64];
U64 RookAttacks[64][4096];

U64 BishopMasks[64];
int BishopShifts[64];
U64 BishopAttacks[64][512];

const U64 RookMagics[64] = {
    0x1180004004108520ULL, 0x2c40034010012004ULL, 0x100200041001008ULL,
    0x8880080010008004ULL, 0x100110004020800ULL,  0x200041008810200ULL,
    0x2100540100008200ULL, 0x600048204410024ULL,  0x2002080420100ULL,
    0x8502004100208200ULL, 0x1002004200802010ULL, 0x8058800802100080ULL,
    0x2b08800800040080ULL, 0x900808004000200ULL,  0x4003000900040600ULL,
    0x200200020044910cULL, 0x8080004020004008ULL, 0x20004010002040ULL,
    0x20018010012080ULL,   0x24444b0010010060ULL, 0x408008008800400ULL,
    0x4400808004000200ULL, 0x6808010100040200ULL, 0x2000820020804411ULL,
    0x400880008022ULL,     0xc900400140201001ULL, 0x2020010100201044ULL,
    0x90100100020ULL,      0x8244000808004080ULL, 0x801000900240002ULL,
    0x8000010080800200ULL, 0x40010c4200008114ULL, 0x2080004008c02001ULL,
    0xd0c0804010802004ULL, 0x4190040800200020ULL, 0x210001480800800ULL,
    0x8040081800800ULL,    0x4100020080800400ULL, 0x811004000208ULL,
    0x2000800040800100ULL, 0x1000803040008000ULL, 0x2a000804000802cULL,
    0xa00802012020040ULL,  0x400812020020ULL,     0x4019010800110004ULL,
    0x400020004008080ULL,  0x40100188040002ULL,   0x9140840911a0014ULL,
    0x18000c000201140ULL,  0x8000400020008480ULL, 0x1010002000841080ULL,
    0x8011000800880ULL,    0x841800800040280ULL,  0x2040800400020080ULL,
    0x180800100020080ULL,  0x8848141089104200ULL, 0x18c020800303ULL,
    0x8201080400105ULL,    0x400104500082001ULL,  0x2001008805209001ULL,
    0x1001008000285ULL,    0x409000804000203ULL,  0x800020810208104ULL,
    0x100840039008442ULL};

const U64 BishopMagics[64] = {
    0x28100888004680ULL,   0x8a10024a01461100ULL, 0x8020400300400ULL,
    0xb0820404000a501ULL,  0x201104080040100ULL,  0x31012010003010ULL,
    0x4802020120080000ULL, 0x80a806300c01ULL,     0x202088841380205ULL,
    0x1021025002108101ULL, 0x1810e1060109ULL,     0x8800822082000004ULL,
    0x108020211140080ULL,  0x2200009010090808ULL, 0x12040104822044ULL,
    0x809044208010810ULL,  0x4082204040804ULL,    0x2060000841040880ULL,
    0x1210042020a0200ULL,  0x800a42040104cULL,    0x4031000820080600ULL,
    0x41002200420210ULL,   0x30a080404aa1804ULL,  0x71000201008282ULL,
    0x4090110841242102ULL, 0x1080060080120ULL,    0x4002880050002821ULL,
    0x1011080009004100ULL, 0x1081001207004001ULL, 0x800801080080a002ULL,
    0x101a020020482204ULL, 0x1006414604840440ULL, 0x4b00403c00404ULL,
    0x204100400020408ULL,  0xa42004101100100ULL,  0x2201100820040400ULL,
    0x128010040b00802ULL,  0x2010e008008080cULL,  0x241020096062801ULL,
    0x403800484c008200ULL, 0x104220250004020ULL,  0x1401043082114400ULL,
    0x1082010401004200ULL, 0x8804200840802ULL,    0x4010404091010a00ULL,
    0x7840012051000080ULL, 0x2008880100404400ULL, 0xa04808c102004044ULL,
    0x10c8440229402300ULL, 0x432024442188004ULL,  0x4000c04200900c00ULL,
    0x4200010084040922ULL, 0x2000101102020012ULL, 0x1002061002020008ULL,
    0x20129001130000ULL,   0x20084120408008ULL,   0x9c060840a884080ULL,
    0x81202082501000ULL,   0x42c28202052400ULL,   0x564011260840400ULL,
    0x150002040104100ULL,  0x2000022498100440ULL, 0x370050a00820d280ULL,
    0x6102040104010200ULL};

U64 set_occupancy(int index, int bits_in_mask, U64 attack_mask) {
  U64 occupancy = 0ULL;
  for (int count = 0; count < bits_in_mask; count++) {
    int square = pop_lsb(attack_mask);
    if (index & (1 << count))
      occupancy |= (1ULL << square);
  }
  return occupancy;
}

U64 mask_rook_attacks(int square) {
  U64 attacks = 0ULL;
  int tr = square / 8, tf = square % 8;
  for (int r = tr + 1; r <= 6; r++)
    attacks |= (1ULL << (r * 8 + tf));
  for (int r = tr - 1; r >= 1; r--)
    attacks |= (1ULL << (r * 8 + tf));
  for (int f = tf + 1; f <= 6; f++)
    attacks |= (1ULL << (tr * 8 + f));
  for (int f = tf - 1; f >= 1; f--)
    attacks |= (1ULL << (tr * 8 + f));
  return attacks;
}

U64 mask_bishop_attacks(int square) {
  U64 attacks = 0ULL;
  int tr = square / 8, tf = square % 8;
  for (int r = tr + 1, f = tf + 1; r <= 6 && f <= 6; r++, f++)
    attacks |= (1ULL << (r * 8 + f));
  for (int r = tr - 1, f = tf + 1; r >= 1 && f <= 6; r--, f++)
    attacks |= (1ULL << (r * 8 + f));
  for (int r = tr + 1, f = tf - 1; r <= 6 && f >= 1; r++, f--)
    attacks |= (1ULL << (r * 8 + f));
  for (int r = tr - 1, f = tf - 1; r >= 1 && f >= 1; r--, f--)
    attacks |= (1ULL << (r * 8 + f));
  return attacks;
}

U64 rook_attacks_on_the_fly(int square, U64 block) {
  U64 attacks = 0ULL;
  int tr = square / 8, tf = square % 8;
  for (int r = tr + 1; r <= 7; r++) {
    attacks |= (1ULL << (r * 8 + tf));
    if ((1ULL << (r * 8 + tf)) & block)
      break;
  }
  for (int r = tr - 1; r >= 0; r--) {
    attacks |= (1ULL << (r * 8 + tf));
    if ((1ULL << (r * 8 + tf)) & block)
      break;
  }
  for (int f = tf + 1; f <= 7; f++) {
    attacks |= (1ULL << (tr * 8 + f));
    if ((1ULL << (tr * 8 + f)) & block)
      break;
  }
  for (int f = tf - 1; f >= 0; f--) {
    attacks |= (1ULL << (tr * 8 + f));
    if ((1ULL << (tr * 8 + f)) & block)
      break;
  }
  return attacks;
}

U64 bishop_attacks_on_the_fly(int square, U64 block) {
  U64 attacks = 0ULL;
  int tr = square / 8, tf = square % 8;
  for (int r = tr + 1, f = tf + 1; r <= 7 && f <= 7; r++, f++) {
    attacks |= (1ULL << (r * 8 + f));
    if ((1ULL << (r * 8 + f)) & block)
      break;
  }
  for (int r = tr - 1, f = tf + 1; r >= 0 && f <= 7; r--, f++) {
    attacks |= (1ULL << (r * 8 + f));
    if ((1ULL << (r * 8 + f)) & block)
      break;
  }
  for (int r = tr + 1, f = tf - 1; r <= 7 && f >= 0; r++, f--) {
    attacks |= (1ULL << (r * 8 + f));
    if ((1ULL << (r * 8 + f)) & block)
      break;
  }
  for (int r = tr - 1, f = tf - 1; r >= 0 && f >= 0; r--, f--) {
    attacks |= (1ULL << (r * 8 + f));
    if ((1ULL << (r * 8 + f)) & block)
      break;
  }
  return attacks;
}

void init_leapers() {
  for (int sq = 0; sq < 64; sq++) {
    knight_attacks[sq] = 0;
    king_attacks[sq] = 0;
    pawn_attacks[0][sq] = 0; // white
    pawn_attacks[1][sq] = 0; // black

    int r = sq / 8;
    int f = sq % 8;

    // Knight
    int knight_offsets[8][2] = {{-2, -1}, {-2, 1}, {-1, -2}, {-1, 2},
                                {1, -2},  {1, 2},  {2, -1},  {2, 1}};
    for (int i = 0; i < 8; i++) {
      int nr = r + knight_offsets[i][0];
      int nf = f + knight_offsets[i][1];
      if (nr >= 0 && nr <= 7 && nf >= 0 && nf <= 7) {
        set_bit(knight_attacks[sq], nr * 8 + nf);
      }
    }

    // King
    int king_offsets[8][2] = {{-1, -1}, {-1, 0}, {-1, 1}, {0, -1},
                              {0, 1},   {1, -1}, {1, 0},  {1, 1}};
    for (int i = 0; i < 8; i++) {
      int nr = r + king_offsets[i][0];
      int nf = f + king_offsets[i][1];
      if (nr >= 0 && nr <= 7 && nf >= 0 && nf <= 7) {
        set_bit(king_attacks[sq], nr * 8 + nf);
      }
    }

    // White pawns (move up, so rank decreases in 0-63 notation where 0 is rank
    // 8, wait, rank 8 is 0? Let's standardise: sq = r * 8 + f. r=0 is rank 8
    // (a8..h8), r=7 is rank 1. wait, let's keep usual mapping: a8=0, h1=63.
    // White pawn on e2 (r=6, f=4). attacks to d3 (r=5, f=3) and f3 (r=5, f=5).
    // so white attacks are r-1.

    if (r - 1 >= 0) {
      if (f - 1 >= 0)
        set_bit(pawn_attacks[0][sq], (r - 1) * 8 + (f - 1));
      if (f + 1 <= 7)
        set_bit(pawn_attacks[0][sq], (r - 1) * 8 + (f + 1));
    }

    // Black pawns (e7 = r=1, f=4. attacks d6 r=2, f=3)
    if (r + 1 <= 7) {
      if (f - 1 >= 0)
        set_bit(pawn_attacks[1][sq], (r + 1) * 8 + (f - 1));
      if (f + 1 <= 7)
        set_bit(pawn_attacks[1][sq], (r + 1) * 8 + (f + 1));
    }
  }
}

void init_sliders() {
  for (int sq = 0; sq < 64; sq++) {
    // Bishop
    BishopMasks[sq] = mask_bishop_attacks(sq);
    int b_bits = count_bits(BishopMasks[sq]);
    BishopShifts[sq] = 64 - b_bits;

    int b_indices = (1 << b_bits);
    for (int i = 0; i < b_indices; i++) {
      U64 occupancy = set_occupancy(i, b_bits, BishopMasks[sq]);
      int magic_idx = (occupancy * BishopMagics[sq]) >> BishopShifts[sq];
      BishopAttacks[sq][magic_idx] = bishop_attacks_on_the_fly(sq, occupancy);
    }

    // Rook
    RookMasks[sq] = mask_rook_attacks(sq);
    int r_bits = count_bits(RookMasks[sq]);
    RookShifts[sq] = 64 - r_bits;

    int r_indices = (1 << r_bits);
    for (int i = 0; i < r_indices; i++) {
      U64 occupancy = set_occupancy(i, r_bits, RookMasks[sq]);
      int magic_idx = (occupancy * RookMagics[sq]) >> RookShifts[sq];
      RookAttacks[sq][magic_idx] = rook_attacks_on_the_fly(sq, occupancy);
    }
  }
}

void init_attacks() {
  init_leapers();
  init_sliders();
}
