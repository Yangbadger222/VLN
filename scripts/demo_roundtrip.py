from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from navida_deploy.client import demo_roundtrip


if __name__ == "__main__":
    print(demo_roundtrip())
