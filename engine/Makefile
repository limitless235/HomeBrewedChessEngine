CXX = g++
CXXFLAGS = -std=c++17 -O3 -march=native -Wall -Wextra
DEBUGFLAGS = -std=c++17 -g -O0 -fsanitize=address -Wall -Wextra
TARGET = engine
SRCS = src/main.cpp src/board.cpp src/movegen.cpp src/attacks.cpp src/search.cpp src/evaluate.cpp src/tt.cpp src/uci.cpp
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
