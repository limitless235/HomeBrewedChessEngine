#include <iostream>
#include <string>
#include "board.h"
#include "movegen.h"
#include "attacks.h"

int main() {
    init_zobrist();
    init_attacks();
    Board b;
    b.set_fen("r1k4r/ppp2npp/6b1/2qP1p2/B1P5/4B3/PP4PP/R2QR1K1 b - - 1 25");
    
    Move moves_list[256];
    int count = generate_moves(b, moves_list);
    
    std::cout << "Looking for f8c5 in fen r1k4r/ppp2npp/6b1/2qP1p2/B1P5/4B3/PP4PP/R2QR1K1 b - - 1 25\n";
    bool found = false;
    
    for (int j=0; j<count; j++) {
        Move m = moves_list[j];
        char f_char = 'a' + (get_from(m) % 8);
        char r_char = '8' - (get_from(m) / 8);
        char tf_char = 'a' + (get_to(m) % 8);
        char tr_char = '8' - (get_to(m) / 8);
        std::string s = ""; s += f_char; s += r_char; s += tf_char; s += tr_char;
        
        std::cout << "  " << s << "\n";
        
        if (s == "f8c5") { found = true; }
    }
    
    if (found) std::cout << "FOUND f8c5\n";
    else std::cout << "FAILED TO FIND f8c5\n";
    
    return 0;
}
