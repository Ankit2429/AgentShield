import sys
import time

def run_agent():
    print("Starting Mock Agent A...")
    while True:
        print("Agent A is operating in normal state...")
        time.sleep(5)

if __name__ == "__main__":
    try:
        run_agent()
    except KeyboardInterrupt:
        print("\nAgent A stopped.")
        sys.exit(0)
