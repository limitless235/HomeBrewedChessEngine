CXX = g++
CXXFLAGS = -std=c++17 -O3 -march=native -Wall -Wextra
DEBUGFLAGS = -std=c++17 -g -O0 -fsanitize=address -Wall -Wextra
TARGET = engine
SRCS = main.cpp board.cpp movegen.cpp attacks.cpp search.cpp evaluate.cpp tt.cpp uci.cpp
OBJS = $(SRCS:.cpp=.o)

.PHONY: all clean debug

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(OBJS)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

debug:
	$(CXX) $(DEBUGFLAGS) $(SRCS) -o $(TARGET)

clean:
	rm -f $(OBJS) $(TARGET)
