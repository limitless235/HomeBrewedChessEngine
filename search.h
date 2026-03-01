#pragma once
#include "board.h"
#include "movegen.h"
#include "tt.h"
#include <atomic>

constexpr int MAX_PLY = 100;

struct SearchLimits {
  int movetime = -1;
  int wtime = 0, btime = 0;
  int winc = 0, binc = 0;
  int depth = -1;
  bool infinite = false;
};

struct SearchState {
  std::atomic<bool> stop{false};
  uint64_t nodes = 0;

  Move killers[MAX_PLY][2];
  int history[2][64][64]; // [Color][From][To]

  Move pv[MAX_PLY][MAX_PLY];
  int pv_length[MAX_PLY];

  // Time management inside thread
  long long start_time_ms = 0;
  long long hard_limit_ms = 0;
  bool limits_reached = false;
};

extern SearchState search_state;

int negamax(Board &board, int depth, int alpha, int beta, int ply,
            bool null_move_allowed);
int quiescence(Board &board, int alpha, int beta, int ply);
Move iterative_deepening(Board &board, SearchLimits limits);
