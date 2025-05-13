import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from AutoManager.supervisor import handle_crash_and_generate_patch

if __name__ == "__main__":
    handle_crash_and_generate_patch(
        file_path="TradingBot/crash_test_file.py",
        error="SyntaxError: expected ':'",
    )
