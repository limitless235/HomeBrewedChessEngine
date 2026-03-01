#include <iostream>
#include <string>
#include "board.h"
#include "movegen.h"
#include "attacks.h"

int main() {
    init_zobrist();
    init_attacks();
    Board b;
    b.set_startpos();
    
    std::string moves[] = {"e2e4", "e7e5"};
    
    for (int i=0; i<2; i++) {
        std::string m_str = moves[i];
        Move moves_list[256];
        int count = generate_moves(b, moves_list);
        
        std::cout << "Turn " << i << " (" << (b.side_to_move == WHITE ? "W" : "B") << ") looking for " << m_str << "\n";
        bool found = false;
        Move final_m = 0;
        
        for (int j=0; j<count; j++) {
            Move m = moves_list[j];
            char f_char = 'a' + (get_from(m) % 8);
            char r_char = '8' - (get_from(m) / 8);
            char tf_char = 'a' + (get_to(m) % 8);
            char tr_char = '8' - (get_to(m) / 8);
            std::string s = ""; s += f_char; s += r_char; s += tf_char; s += tr_char;
            if (s == "e4e5" || s == "e7e5") {
                std::cout << "  Generated: " << s << " Flag: " << get_flag(m) << "\n";
            }
            if (s == m_str) { final_m = m; found = true; }
        }
        
        if (!found) { std::cout << "FAILED TO FIND MOVE\n"; return 1; }
        b.make_move(final_m);
    }
    std::cout << "Success\n";
    return 0;
}
