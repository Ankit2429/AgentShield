import sys
import time

def run_agent():
    print("Starting Mock Agent B...")
    while True:
        print("Agent B checking queue...")
        time.sleep(5)

if __name__ == "__main__":
    try:
        run_agent()
    except KeyboardInterrupt:
        print("\nAgent B stopped.")
        sys.exit(0)
