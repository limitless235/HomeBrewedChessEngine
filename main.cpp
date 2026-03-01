#include "attacks.h"
#include "board.h"
#include "tt.h"
#include "uci.h"

int main() {
  init_zobrist();
  init_attacks();
  tt_clear();

  uci_loop();

  return 0;
}
