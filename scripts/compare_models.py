"""Command-line entry point for the shared comparison evaluator."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.eval.model_comparison import main

if __name__ == '__main__':main()
