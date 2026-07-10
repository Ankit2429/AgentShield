import time
from attack_scenarios import trigger_prompt_injection, trigger_privilege_escalation

def run_demo():
    print("=== Starting AgentShield Demo Runner ===")
    time.sleep(1)
    
    print("\n1. Simulating regular agent interactions...")
    time.sleep(1)
    print("Normal exchange verified. Trust index stable.")

    print("\n2. Executing malicious simulation...")
    time.sleep(1)
    trigger_prompt_injection()
    trigger_privilege_escalation()

    print("\n=== Demo Simulation Completed ===")

if __name__ == "__main__":
    run_demo()
