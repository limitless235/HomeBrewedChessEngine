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
    
    std::string moves[] = {"e2e4", "e7e5", "g1f3", "b8c6", "c2c3", "g8f6", "e4e5", "f6d5", "d2d4", "c5c4", "c3d4", "d7d6", "f1c4", "d5b6", "c4d3", "d6e5", "d4e5", "c8g4", "e1g1", "e7e6", "c1f4", "f8e7", "b1d2", "d8d3", "d2b3", "d3f3", "g2f3", "g4h5", "b3d4", "a8d8", "f4e3", "c6e5", "d1e2", "d8d4", "e3d4", "e5f3", "g1h1", "f3d4", "e2h5", "e8g8", "h5g4", "e7f6", "a1b1", "f8c8", "f1c1", "c8c1", "b1c1", "g7g6", "g4f4", "g8g7", "f4e3", "b6d5", "e3d2", "h7h6", "b2b4", "a7a6", "a2a4", "b7b5", "a4b5", "a6b5", "d2e1", "f6g5", "c1c5", "g5f6", "h1g1", "f6e7", "c5c8", "d4f5", "e1a1", "e7f6", "a1a6", "d5b4", "a6b5", "b4d5", "b5d7", "d5c3", "g1f1", "c3e4", "f1e2", "e4c3", "e2d3", "c3d5", "c8a8", "d5b6"};
    
    // "b6" doesn't work, let's use the list above up to "c8a8"
    for (int i=0; i<81; i++) {
        std::string m_str = moves[i];
        Move moves_list[256];
        int count = generate_moves(b, moves_list);
        Move final_m = 0;
        for (int j=0; j<count; j++) {
            Move m = moves_list[j];
            char f_char = 'a' + (get_from(m) % 8);
            char r_char = '8' - (get_from(m) / 8);
            char tf_char = 'a' + (get_to(m) % 8);
            char tr_char = '8' - (get_to(m) / 8);
            std::string s = ""; s += f_char; s += r_char; s += tf_char; s += tr_char;
            int flag = get_flag(m);
            if (flag == MOVE_PROMO_QUEEN) s += 'q';
            else if (flag == MOVE_PROMO_ROOK) s += 'r';
            else if (flag == MOVE_PROMO_BISHOP) s += 'b';
            else if (flag == MOVE_PROMO_KNIGHT) s += 'n';
            
            if (s == m_str) { final_m = m; break; }
        }
        if (final_m == 0) {
            std::cout << "FAILED AT MOVE: " << m_str << std::endl;
            b.print();
            break;
        }
        BoardState st = b.save_state();
        st.captured_piece = b.get_piece_on_square(get_to(final_m));
        b.make_move(final_m);
        std::cout << m_str << " ";
    }
    std::cout << std::endl;
    b.print();
    return 0;
}
