#include <iostream>
#include <vector>
#include <random>

using namespace std;

typedef unsigned long long U64;

int count_bits(U64 b) {
    int count = 0;
    while(b) { count++; b &= b - 1; }
    return count;
}

int pop_lsb(U64 &b) {
    int ls1b = __builtin_ctzll(b);
    b &= b - 1;
    return ls1b;
}

U64 set_occupancy(int index, int bits_in_mask, U64 attack_mask) {
    U64 occupancy = 0ULL;
    for (int count = 0; count < bits_in_mask; count++) {
        int square = pop_lsb(attack_mask);
        if (index & (1 << count)) occupancy |= (1ULL << square);
    }
    return occupancy;
}

U64 mask_rook_attacks(int square) {
    U64 attacks = 0ULL;
    int tr = square / 8, tf = square % 8;
    for (int r = tr + 1; r <= 6; r++) attacks |= (1ULL << (r * 8 + tf));
    for (int r = tr - 1; r >= 1; r--) attacks |= (1ULL << (r * 8 + tf));
    for (int f = tf + 1; f <= 6; f++) attacks |= (1ULL << (tr * 8 + f));
    for (int f = tf - 1; f >= 1; f--) attacks |= (1ULL << (tr * 8 + f));
    return attacks;
}

U64 mask_bishop_attacks(int square) {
    U64 attacks = 0ULL;
    int tr = square / 8, tf = square % 8;
    for (int r = tr + 1, f = tf + 1; r <= 6 && f <= 6; r++, f++) attacks |= (1ULL << (r * 8 + f));
    for (int r = tr - 1, f = tf + 1; r >= 1 && f <= 6; r--, f++) attacks |= (1ULL << (r * 8 + f));
    for (int r = tr + 1, f = tf - 1; r <= 6 && f >= 1; r++, f--) attacks |= (1ULL << (r * 8 + f));
    for (int r = tr - 1, f = tf - 1; r >= 1 && f >= 1; r--, f--) attacks |= (1ULL << (r * 8 + f));
    return attacks;
}

U64 rook_attacks_on_the_fly(int square, U64 block) {
    U64 attacks = 0ULL;
    int tr = square / 8, tf = square % 8;
    for (int r = tr + 1; r <= 7; r++) { attacks |= (1ULL << (r * 8 + tf)); if ((1ULL << (r * 8 + tf)) & block) break; }
    for (int r = tr - 1; r >= 0; r--) { attacks |= (1ULL << (r * 8 + tf)); if ((1ULL << (r * 8 + tf)) & block) break; }
    for (int f = tf + 1; f <= 7; f++) { attacks |= (1ULL << (tr * 8 + f)); if ((1ULL << (tr * 8 + f)) & block) break; }
    for (int f = tf - 1; f >= 0; f--) { attacks |= (1ULL << (tr * 8 + f)); if ((1ULL << (tr * 8 + f)) & block) break; }
    return attacks;
}

U64 bishop_attacks_on_the_fly(int square, U64 block) {
    U64 attacks = 0ULL;
    int tr = square / 8, tf = square % 8;
    for (int r = tr + 1, f = tf + 1; r <= 7 && f <= 7; r++, f++) { attacks |= (1ULL << (r * 8 + f)); if ((1ULL << (r * 8 + f)) & block) break; }
    for (int r = tr - 1, f = tf + 1; r >= 0 && f <= 7; r--, f++) { attacks |= (1ULL << (r * 8 + f)); if ((1ULL << (r * 8 + f)) & block) break; }
    for (int r = tr + 1, f = tf - 1; r <= 7 && f >= 0; r++, f--) { attacks |= (1ULL << (r * 8 + f)); if ((1ULL << (r * 8 + f)) & block) break; }
    for (int r = tr - 1, f = tf - 1; r >= 0 && f >= 0; r--, f--) { attacks |= (1ULL << (r * 8 + f)); if ((1ULL << (r * 8 + f)) & block) break; }
    return attacks;
}

U64 random_U64() {
    static mt19937_64 rng(1804289383);
    U64 u1, u2, u3, u4;
    u1 = rng() & 0xFFFF; u2 = rng() & 0xFFFF;
    u3 = rng() & 0xFFFF; u4 = rng() & 0xFFFF;
    return u1 | (u2 << 16) | (u3 << 32) | (u4 << 48);
}

U64 random_U64_fewbits() {
    return random_U64() & random_U64() & random_U64();
}

U64 find_magic(int square, int m, int is_bishop) {
    U64 mask = is_bishop ? mask_bishop_attacks(square) : mask_rook_attacks(square);
    int n = count_bits(mask);
    vector<U64> occupancies(4096), attacks(4096), used(4096, 0ULL);
    for (int i = 0; i < (1 << n); i++) {
        occupancies[i] = set_occupancy(i, n, mask);
        attacks[i] = is_bishop ? bishop_attacks_on_the_fly(square, occupancies[i]) : rook_attacks_on_the_fly(square, occupancies[i]);
    }
    for (int k = 0; k < 100000000; k++) {
        U64 magic = random_U64_fewbits();
        if (count_bits((mask * magic) & 0xFF00000000000000ULL) < 6) continue;
        fill(used.begin(), used.begin() + 4096, 0ULL);
        bool fail = false;
        for (int i = 0; !fail && i < (1 << n); i++) {
            int magic_index = (occupancies[i] * magic) >> (64 - m);
            if (used[magic_index] == 0ULL) used[magic_index] = attacks[i];
            else if (used[magic_index] != attacks[i]) fail = true;
        }
        if (!fail) return magic;
    }
    return 0ULL;
}

int main() {
    cout << "const U64 RookMagics[64] = {\n";
    for(int sq=0; sq<64; sq++) {
        int m = 64 - count_bits(mask_rook_attacks(sq));
        cout << "    0x" << hex << find_magic(sq, 64-m, 0) << "ULL,\n";
    }
    cout << "};\n\n";

    cout << "const U64 BishopMagics[64] = {\n";
    for(int sq=0; sq<64; sq++) {
        int m = 64 - count_bits(mask_bishop_attacks(sq));
        cout << "    0x" << hex << find_magic(sq, 64-m, 1) << "ULL,\n";
    }
    cout << "};\n";
    return 0;
}
