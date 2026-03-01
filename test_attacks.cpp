#include "attacks.h"
#include <iostream>

using namespace std;

void print_bitboard(U64 bb) {
  for (int r = 0; r < 8; r++) {
    for (int f = 0; f < 8; f++) {
      int sq = r * 8 + f;
      cout << (get_bit(bb, sq) ? "1 " : ". ");
    }
    cout << "\n";
  }
  cout << "\n";
}

int main() {
  init_attacks();
  cout << "64 Knight Attacks:\n";
  for (int sq = 0; sq < 64; sq++) {
    cout << "Square " << sq << ":\n";
    print_bitboard(knight_attacks[sq]);
  }
  return 0;
}
