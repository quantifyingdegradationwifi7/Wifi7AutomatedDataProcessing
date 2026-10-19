#!/usr/bin/env python3
import unittest
import sys
from pathlib import Path

def main():
    print("=== Wi-Fi 7 Pipeline Test Suite ===")
    
    # Ensure src directory is in the Python path
    src_path = Path(__file__).parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent / "tests"
    
    # Ensure tests directory exists
    if not start_dir.exists():
        print(f"Error: Could not find tests directory at {start_dir}")
        sys.exit(1)
        
    suite = loader.discover(str(start_dir), pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if not result.wasSuccessful():
        print("\n[!] Some tests failed. Please review the output above.")
        sys.exit(1)
    else:
        print("\n[+] All tests completed successfully!")

if __name__ == "__main__":
    main()