import pandas as pd
import matplotlib.pyplot as plt
import os

def generate_plots():
    # Find results.csv in the same directory as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "results.csv")
    
    if not os.path.exists(csv_path):
        print(f"[Error] {csv_path} not found. Run benchmark.py first.")
        return

    df = pd.read_csv(csv_path)
    
    # --- Plot 1: System Latency Breakdown ---
    system_df = df[df['operation'].isna() | df['operation'].str.startswith('P')] # Simple filter logic
    # More robust filter: anything that is in 'phase' column
    # Actually, the benchmark.py saved everything in one 'operation' or 'phase' column? 
    # Let's fix the dataframe filter based on benchmark.py structure.
    
    # Re-read with flexible column check
    system_phases = df[df['phase'].notna()]
    crypto_ops = df[df['operation'].notna()]

    if not system_phases.empty:
        plt.figure(figsize=(10, 6))
        plt.bar(system_phases['phase'], system_phases['time_ms'], color=['#3498db', '#e67e22', '#2ecc71'])
        plt.ylabel('Latency (ms)')
        plt.title('Anon-Network: Phase-wise Latency Breakdown')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig('benchmark/latency_breakdown.png')
        print("[Success] Saved benchmark/latency_breakdown.png")

    # --- Plot 2: Cryptographic Overhead ---
    if not crypto_ops.empty:
        plt.figure(figsize=(10, 6))
        plt.barh(crypto_ops['operation'], crypto_ops['time_ms'], color='#9b59b6')
        plt.xlabel('Time (ms)')
        plt.title('Cryptographic Operation Performance (Local)')
        plt.grid(axis='x', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig('benchmark/crypto_performance.png')
        print("[Success] Saved benchmark/crypto_performance.png")

if __name__ == "__main__":
    # Use a non-interactive backend for server-side generation if needed
    plt.switch_backend('Agg') 
    generate_plots()
