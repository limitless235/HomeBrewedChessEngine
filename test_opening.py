from server import load_opening_book, identify_opening, ECO_MOVE_MAP
import sys

# already loaded on import, but just in case
print(f"Loaded {len(ECO_MOVE_MAP)} moves.")
print("Dict keys sample:", list(ECO_MOVE_MAP.keys())[:5])

print("e2e4 c7c5 g1f3 in ECO_MOVE_MAP?", ("e2e4", "c7c5", "g1f3") in ECO_MOVE_MAP)

# test identify
print(identify_opening(["e2e4", "c7c5", "g1f3"]))
