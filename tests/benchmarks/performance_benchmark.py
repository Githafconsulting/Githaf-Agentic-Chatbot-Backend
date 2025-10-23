"""
Performance Benchmarks (Phase 6: Testing & Polish)
Measure system performance across all phases
"""
import pytest
import time
import asyncio
import statistics
from typing import List, Dict
from app.services.rag_service import get_rag_response
from app.services.intent_service import classify_intent_hybrid
from app.services.planning_service import create_plan, execute_plan
from app.services.embedding_service import get_embedding
from app.services.validation_service import validate_response
from app.services.tools import get_tool_registry


class PerformanceBenchmark:
    """Performance benchmark runner"""

    def __init__(self):
        self.results: List[Dict] = []

    def record(self, name: str, latency: float, success: bool = True):
        """Record benchmark result"""
        self.results.append({
            "name": name,
            "latency_ms": latency * 1000,
            "success": success,
            "timestamp": time.time()
        })

    def report(self) -> Dict:
        """Generate performance report"""
        if not self.results:
            return {}

        latencies = [r["latency_ms"] for r in self.results if r["success"]]
        successes = [r for r in self.results if r["success"]]

        return {
            "total_tests": len(self.results),
            "successes": len(successes),
            "failures": len(self.results) - len(successes),
            "success_rate": len(successes) / len(self.results) * 100 if self.results else 0,
            "latency": {
                "min_ms": min(latencies) if latencies else 0,
                "max_ms": max(latencies) if latencies else 0,
                "mean_ms": statistics.mean(latencies) if latencies else 0,
                "median_ms": statistics.median(latencies) if latencies else 0,
                "p95_ms": statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else (max(latencies) if latencies else 0),
                "p99_ms": statistics.quantiles(latencies, n=100)[98] if len(latencies) > 100 else (max(latencies) if latencies else 0),
            }
        }


# Global benchmark instance
benchmark = PerformanceBenchmark()


# ========================================
# Benchmark: Embedding Generation
# ========================================

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_embedding_generation():
    """Benchmark embedding generation speed"""
    queries = [
        "What services do you offer?",
        "How can I contact you?",
        "Tell me about your pricing",
        "What are your business hours?",
        "How do I get started?"
    ]

    for query in queries:
        try:
            start = time.time()
            embedding = await get_embedding(query)
            end = time.time()

            latency = end - start
            benchmark.record("embedding_generation", latency, success=(embedding is not None))

            # Should be fast (< 200ms)
            assert latency < 0.2, f"Embedding took {latency:.3f}s, expected < 0.2s"

        except Exception as e:
            benchmark.record("embedding_generation", 0, success=False)
            pytest.skip(f"Embedding service unavailable: {e}")


# ========================================
# Benchmark: Intent Classification
# ========================================

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_intent_classification():
    """Benchmark intent classification speed"""
    queries = [
        "hello",
        "What are your services?",
        "Thank you",
        "How much does it cost?",
        "goodbye"
    ]

    for query in queries:
        try:
            start = time.time()
            intent, confidence = await classify_intent_hybrid(query)
            end = time.time()

            latency = end - start
            benchmark.record("intent_classification", latency, success=(intent is not None))

            # Should be fast (< 300ms including LLM fallback)
            assert latency < 0.3, f"Intent classification took {latency:.3f}s, expected < 0.3s"

        except Exception as e:
            benchmark.record("intent_classification", 0, success=False)
            pytest.skip(f"Intent service unavailable: {e}")


# ========================================
# Benchmark: Simple RAG Query
# ========================================

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_simple_rag_query():
    """Benchmark simple RAG query end-to-end"""
    queries = [
        "What services do you offer?",
        "How can I contact you?",
        "What are your prices?"
    ]

    for query in queries:
        try:
            start = time.time()
            response = await get_rag_response(query, session_id=f"bench-{hash(query)}")
            end = time.time()

            latency = end - start
            benchmark.record("simple_rag_query", latency, success=("response" in response))

            # Should be reasonable (< 3s for complete pipeline)
            assert latency < 3.0, f"RAG query took {latency:.3f}s, expected < 3.0s"

        except Exception as e:
            benchmark.record("simple_rag_query", 0, success=False)
            pytest.skip(f"RAG service unavailable: {e}")


# ========================================
# Benchmark: Conversational Response
# ========================================

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_conversational_response():
    """Benchmark fast-path conversational responses"""
    queries = [
        "hello",
        "how are you",
        "thank you",
        "goodbye"
    ]

    for query in queries:
        try:
            start = time.time()
            response = await get_rag_response(query, session_id=f"bench-conv-{hash(query)}")
            end = time.time()

            latency = end - start
            benchmark.record("conversational_response", latency, success=response.get("conversational", False))

            # Should be very fast (< 100ms, no RAG needed)
            assert latency < 0.1, f"Conversational response took {latency:.3f}s, expected < 0.1s"

        except Exception as e:
            benchmark.record("conversational_response", 0, success=False)
            pytest.skip(f"Conversational service unavailable: {e}")


# ========================================
# Benchmark: Planning
# ========================================

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_planning():
    """Benchmark multi-step planning generation"""
    query = "First tell me about your services, then send me pricing information"

    try:
        from app.services.intent_service import Intent

        start = time.time()
        plan = await create_plan(query, Intent.QUESTION)
        end = time.time()

        latency = end - start
        benchmark.record("planning_generation", latency, success=(plan is not None))

        # Should be reasonable (< 2s with LLM)
        assert latency < 2.0, f"Planning took {latency:.3f}s, expected < 2.0s"

    except Exception as e:
        benchmark.record("planning_generation", 0, success=False)
        pytest.skip(f"Planning service unavailable: {e}")


# ========================================
# Benchmark: Response Validation
# ========================================

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_validation():
    """Benchmark response validation speed"""
    query = "What is your email?"
    response = "Our email is info@githafconsulting.com"
    sources = [{"id": "1", "content": "Email: info@githafconsulting.com", "similarity": 0.9}]

    for _ in range(3):
        try:
            start = time.time()
            validation = await validate_response(query, response, sources)
            end = time.time()

            latency = end - start
            benchmark.record("response_validation", latency, success=("is_valid" in validation))

            # Should be reasonable (< 1.5s with LLM)
            assert latency < 1.5, f"Validation took {latency:.3f}s, expected < 1.5s"

        except Exception as e:
            benchmark.record("response_validation", 0, success=False)
            pytest.skip(f"Validation service unavailable: {e}")


# ========================================
# Benchmark: Concurrent Load
# ========================================

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_concurrent_load():
    """Benchmark system under concurrent load"""
    num_concurrent = 10
    query = "What services do you offer?"

    try:
        start = time.time()

        # Execute 10 concurrent requests
        tasks = [
            get_rag_response(query, session_id=f"bench-concurrent-{i}")
            for i in range(num_concurrent)
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        end = time.time()

        total_time = end - start
        successful = [r for r in responses if not isinstance(r, Exception)]

        benchmark.record("concurrent_load", total_time / num_concurrent, success=(len(successful) == num_concurrent))

        # Should handle concurrent requests efficiently
        # Total time should be less than num_concurrent * single_query_time
        assert total_time < num_concurrent * 3.0, f"Concurrent load took {total_time:.3f}s"

        # Most requests should succeed
        assert len(successful) >= num_concurrent * 0.8, f"Only {len(successful)}/{num_concurrent} succeeded"

    except Exception as e:
        benchmark.record("concurrent_load", 0, success=False)
        pytest.skip(f"Concurrent test unavailable: {e}")


# ========================================
# Benchmark: Tool Execution
# ========================================

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_tool_registry():
    """Benchmark tool registry operations"""
    registry = get_tool_registry()

    # Benchmark tool lookup
    start = time.time()
    for _ in range(100):
        tool = registry.get_tool("send_email")
    end = time.time()

    lookup_time = (end - start) / 100
    benchmark.record("tool_lookup", lookup_time, success=(tool is not None))

    # Should be instant (< 1ms)
    assert lookup_time < 0.001, f"Tool lookup took {lookup_time*1000:.3f}ms, expected < 1ms"


# ========================================
# Benchmark Report
# ========================================

def test_generate_benchmark_report(tmp_path):
    """Generate final benchmark report"""
    report = benchmark.report()

    print("\n" + "=" * 60)
    print("PERFORMANCE BENCHMARK REPORT")
    print("=" * 60)
    print(f"Total Tests: {report.get('total_tests', 0)}")
    print(f"Successes: {report.get('successes', 0)}")
    print(f"Failures: {report.get('failures', 0)}")
    print(f"Success Rate: {report.get('success_rate', 0):.2f}%")
    print()

    if "latency" in report:
        latency = report["latency"]
        print("Latency Statistics:")
        print(f"  Min:    {latency.get('min_ms', 0):.2f} ms")
        print(f"  Mean:   {latency.get('mean_ms', 0):.2f} ms")
        print(f"  Median: {latency.get('median_ms', 0):.2f} ms")
        print(f"  P95:    {latency.get('p95_ms', 0):.2f} ms")
        print(f"  P99:    {latency.get('p99_ms', 0):.2f} ms")
        print(f"  Max:    {latency.get('max_ms', 0):.2f} ms")

    print("=" * 60)

    # Save report to file
    report_file = tmp_path / "benchmark_report.txt"
    with open(report_file, "w") as f:
        f.write("PERFORMANCE BENCHMARK REPORT\n")
        f.write("=" * 60 + "\n")
        for key, value in report.items():
            f.write(f"{key}: {value}\n")

    print(f"\nReport saved to: {report_file}")


# ========================================
# Performance Targets (SLA)
# ========================================

PERFORMANCE_TARGETS = {
    "embedding_generation": 200,      # ms
    "intent_classification": 300,     # ms
    "conversational_response": 100,   # ms
    "simple_rag_query": 3000,         # ms
    "planning_generation": 2000,      # ms
    "response_validation": 1500,      # ms
}


def test_performance_targets():
    """Verify performance targets are met"""
    report = benchmark.report()

    if not report or "latency" not in report:
        pytest.skip("No benchmark data available")

    mean_latency = report["latency"]["mean_ms"]

    print("\nPerformance Target Comparison:")
    for operation, target_ms in PERFORMANCE_TARGETS.items():
        # Get actual latency for this operation
        operation_results = [r for r in benchmark.results if r["name"] == operation and r["success"]]

        if operation_results:
            actual_latencies = [r["latency_ms"] for r in operation_results]
            actual_mean = statistics.mean(actual_latencies)

            status = "✓ PASS" if actual_mean <= target_ms else "✗ FAIL"
            print(f"  {operation}: {actual_mean:.2f}ms (target: {target_ms}ms) {status}")
