#pragma once
#include "attacks.h"
#include "board.h"

// Move generator utilities using Magic Bitboards
bool is_square_attacked(const Board &board, int sq, int by_side);
bool is_in_check(const Board &board, int side);

// Generate all pseudo-legal moves. Returns the number of moves generated.
int generate_moves(const Board &board, Move *move_list);

// Generate only captures and queen promotions (for Quiescence search)
int generate_captures(const Board &board, Move *move_list);
