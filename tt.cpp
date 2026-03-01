#include "tt.h"
#include <cstring>

TTEntry tt[TT_SIZE];

void tt_clear() { std::memset(tt, 0, sizeof(tt)); }

bool tt_probe(uint64_t key, int depth, int alpha, int beta, int &return_score,
              Move &return_move) {
  TTEntry *entry = &tt[key % TT_SIZE];

  if (entry->key == key) {
    return_move = entry->move;
    if (entry->depth >= depth) {
      int score = entry->score;
      if (entry->flag == FLAG_EXACT) {
        return_score = score;
        return true;
      }
      if (entry->flag == FLAG_UPPERBOUND && score <= alpha) {
        return_score = alpha;
        return true;
      }
      if (entry->flag == FLAG_LOWERBOUND && score >= beta) {
        return_score = beta;
        return true;
      }
    }
  }
  return false;
}

void tt_store(uint64_t key, int depth, int score, int flag, Move best_move) {
  TTEntry *entry = &tt[key % TT_SIZE];

  // Depth-preferred replacement: replace if old depth is smaller, or if exact,
  // or if empty (key == 0) Actually, always replace is fine too, but
  // depth-preferred is better.
  if (entry->key == 0 || entry->depth <= depth || entry->flag == FLAG_EXACT) {
    entry->key = key;
    entry->score = score;
    entry->move = best_move;
    entry->depth = depth;
    entry->flag = flag;
  }
}
