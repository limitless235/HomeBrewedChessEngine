with open("server.py", "r") as f:
    text = f.read()

text = text.replace("analyzing_side='player', recent_history=None):\\n    if recent_history is None:\\n        recent_history = []\\n", "analyzing_side='player', recent_history=None):\n    if recent_history is None:\n        recent_history = []\n")
text = text.replace("helpers + \"\\nclass AnalyzeMoveRequest", "helpers + \"\\nclass AnalyzeMoveRequest")
text = text.replace("helpers + \"\\\\nclass AnalyzeMoveRequest", "helpers + \"\\nclass AnalyzeMoveRequest")
with open("server.py", "w") as f:
    f.write(text)
