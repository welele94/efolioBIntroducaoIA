"""Experimental runner for testing a lighter majority-pressure heuristic.

This file does not replace main.py. It imports the current agent from main.py,
then only changes the pressure weight used when a player is close to majority.

To test locally:
    cp test_main.py main.py   # only if you want VPL to run this exact variant

Or run directly:
    python test_main.py
"""

from pathlib import Path

import main as agent

# Experimental change: moderate majority pressure.
# Current main.py uses 90. This variant tests 60 to push for closing games,
# but with less greed/risk than the previous heavier pressure.
agent.MAJORITY_PRESSURE_WEIGHT = 60

# Keep the current speed and depth profile from main.py.
# Do not change the rules, move generation, opening book, or CSV protocol here.
agent.RESULTS_PATH = Path("resultados.csv")


def main() -> None:
    agent.run_results_csv(agent.RESULTS_PATH, agent.MAX_DEPTH)


if __name__ == "__main__":
    main()
