#!/bin/bash
mkdir -p openings
cd openings
echo "Downloading Lichess ECO TSV files..."
curl -O https://raw.githubusercontent.com/lichess-org/chess-openings/master/a.tsv
curl -O https://raw.githubusercontent.com/lichess-org/chess-openings/master/b.tsv
curl -O https://raw.githubusercontent.com/lichess-org/chess-openings/master/c.tsv
curl -O https://raw.githubusercontent.com/lichess-org/chess-openings/master/d.tsv
curl -O https://raw.githubusercontent.com/lichess-org/chess-openings/master/e.tsv
echo "Done!"
