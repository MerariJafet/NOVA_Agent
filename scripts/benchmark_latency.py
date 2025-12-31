import time
import requests
import argparse


def run_benchmark(url, prompt, iterations=10):
    print(f"🚀 Starting benchmark for {url}")
    print("Iteration | Status | Latency (ms)")
    print("-" * 35)

    latencies = []

    for i in range(iterations):
        start = time.time()
        try:
            response = requests.post(url, json={"message": prompt}, timeout=60)
            latency = int((time.time() - start) * 1000)
            if response.status_code == 200:
                print(f"{i+1:9} |   OK   | {latency:12}")
                latencies.append(latency)
            else:
                print(f"{i+1:9} |  ERR   | {response.status_code}")
        except Exception as e:
            print(f"{i+1:9} |  EXC   | {str(e)[:15]}")

    if latencies:
        avg = sum(latencies) / len(latencies)
        print("-" * 35)
        print(f"Average Latency: {avg:.2f} ms")
        print(f"Samples: {len(latencies)}")
    else:
        print("No successful samples.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark NOVA Latency")
    parser.add_argument(
        "--url", default="http://localhost:8000/api/chat", help="Target endpoint"
    )
    parser.add_argument(
        "--prompt", default="Explain quantum physics in 2 sentences", help="Test prompt"
    )
    parser.add_argument("--samples", type=int, default=5, help="Number of samples")

    args = parser.parse_args()
    run_benchmark(args.url, args.prompt, args.samples)
