#pragma once
#include "board.h" // For Move typedef
#include <cstdint>

const uint8_t FLAG_EXACT = 0;
const uint8_t FLAG_LOWERBOUND = 1;
const uint8_t FLAG_UPPERBOUND = 2;

constexpr int MATE_SCORE = 1000000;
constexpr int INF = 9999999;

struct TTEntry {
  uint64_t key;
  int16_t score;
  uint16_t move; // 16-bit encoded move perfectly matches uint16_t sizing
  uint8_t depth;
  uint8_t flag;
};

constexpr size_t TT_SIZE = (64 * 1024 * 1024) / sizeof(TTEntry);

extern TTEntry tt[TT_SIZE];

void tt_clear();
bool tt_probe(uint64_t key, int depth, int alpha, int beta, int &return_score,
              Move &return_move);
void tt_store(uint64_t key, int depth, int score, int flag, Move best_move);
