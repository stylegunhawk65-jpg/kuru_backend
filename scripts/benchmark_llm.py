"""Standalone benchmarking tool for local and mock LLM inference on Career Twin tasks."""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
import torch

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.models.skill import StudentSkill
from app.schemas.intelligence import PrioritizedGapItem
from app.schemas.llm import (
    InterviewPrepRequest,
    ResumeTailorRequest,
    RoadmapGenerateRequest,
)
from app.services.llm.career_tasks import career_task_service
from app.services.llm.factory import LLMProviderFactory
from app.services.llm.local_transformers import LocalTransformersProvider
from app.services.llm.mock_provider import MockLLMProvider


async def run_benchmark(
    eval_path: str = "eval/career_twin_eval_dataset.json",
    output_path: str = "evaluation_results/real_benchmark_results.json",
    provider_name: str | None = None,
    model_path: str | None = None,
) -> dict:
    """Execute benchmark across all dataset cases and print performance metrics."""
    if not os.path.exists(eval_path):
        print(f"Error: Evaluation dataset not found at '{eval_path}'")
        return {}

    with open(eval_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    # Instantiate provider
    prov_type = (provider_name or settings.LLM_PROVIDER).lower()
    if prov_type == "local":
        resolved_path = (
            model_path
            or settings.LOCAL_MODEL_PATH
            or os.path.join(os.path.expanduser("~"), ".cache", "kuru_models", "Qwen2.5-3B-Instruct")
        )
        provider = LocalTransformersProvider(
            model_path=resolved_path,
            device=settings.LOCAL_MODEL_DEVICE,
            quantization=settings.LOCAL_MODEL_QUANTIZATION,
        )
    else:
        provider = MockLLMProvider()

    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A"
    total_vram_mb = (
        round(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024), 2)
        if torch.cuda.is_available()
        else 0.0
    )

    print("=" * 70)
    print("  KURU BACKEND — LLM INFERENCE BENCHMARK")
    print(f"  Provider:       {provider.name}")
    print(f"  CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  GPU Device:     {gpu_name} ({total_vram_mb:.1f} MB VRAM)")
        print(f"  Initial VRAM:   {torch.cuda.memory_allocated() / (1024*1024):.1f} MB")
    print(f"  Test Cases:     {len(cases)}")
    print(f"  Output File:    {output_path}")
    print("=" * 70)

    # Warmup / load model if local
    if hasattr(provider, "ensure_loaded"):
        print("\n[*] Initializing / warming up model weights...")
        await provider.ensure_loaded()
        print(f"[*] Memory after load: {provider.get_memory_stats()}")

    results = []
    total_start = time.perf_counter()

    for idx, case in enumerate(cases, 1):
        task_type = case["task"]
        case_id = case["id"]
        print(f"\n[{idx}/{len(cases)}] Running {case_id} ({task_type})...")

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

        case_start = time.perf_counter()
        valid_schema = False
        error_msg = None
        output_data = None

        try:
            if task_type == "resume_tailor":
                skills = [
                    StudentSkill(
                        firebase_uid="bench_user",
                        skill_name=s,
                        category="Language",
                        confidence_score=0.9,
                    )
                    for s in case.get("candidate_skills", [])
                ]
                req = ResumeTailorRequest(
                    target_role=case["target_role"],
                    bullet_points=case["bullet_points"],
                    job_description=case.get("job_description"),
                )
                output = await career_task_service.tailor_resume_bullet_points(provider, skills, req)
                valid_schema = bool(output.bullet_points and output.tailored_summary)
                output_data = output.model_dump()

            elif task_type == "roadmap_generate":
                gaps = [
                    PrioritizedGapItem(
                        skill_name=s,
                        priority_rank=i,
                        priority_score=90.0 - i * 5,
                        market_demand_pct=75.0,
                        graph_proximity="1-Hop",
                        reasons=["High demand"],
                    )
                    for i, s in enumerate(case.get("focus_skills", []), 1)
                ]
                req = RoadmapGenerateRequest(
                    target_role=case["target_role"],
                    focus_skills=case.get("focus_skills", []),
                    weekly_hours_available=case.get("weekly_hours_available", 12),
                )
                output = await career_task_service.generate_learning_roadmap(provider, gaps, req)
                valid_schema = bool(output.weekly_modules)
                output_data = output.model_dump()

            elif task_type == "interview_prep":
                skills = [
                    StudentSkill(
                        firebase_uid="bench_user",
                        skill_name=s,
                        category="Language",
                        confidence_score=0.9,
                    )
                    for s in case.get("focus_skills", [])
                ]
                req = InterviewPrepRequest(
                    target_role=case["target_role"],
                    company_name=case.get("company_name"),
                    focus_skills=case.get("focus_skills", []),
                )
                output = await career_task_service.generate_interview_prep(provider, skills, req)
                valid_schema = bool(output.technical_questions)
                output_data = output.model_dump()

        except Exception as exc:
            error_msg = str(exc)
            valid_schema = False

        duration = round(time.perf_counter() - case_start, 3)
        peak_vram = (
            round(torch.cuda.max_memory_allocated() / (1024 * 1024), 2)
            if torch.cuda.is_available()
            else 0.0
        )

        status_str = "PASS [Valid Schema]" if valid_schema else f"FAIL [{error_msg}]"
        print(f"    -> Duration: {duration}s | Peak VRAM: {peak_vram} MB | Status: {status_str}")

        results.append({
            "case_id": case_id,
            "task": task_type,
            "duration_s": duration,
            "peak_vram_mb": peak_vram,
            "valid_schema": valid_schema,
            "error": error_msg,
            "output_preview": output_data,
        })

    total_time = round(time.perf_counter() - total_start, 2)
    valid_count = sum(1 for r in results if r["valid_schema"])
    success_rate = (valid_count / len(results)) * 100 if results else 0.0
    avg_latency = round(sum(r["duration_s"] for r in results) / len(results), 3) if results else 0.0
    overall_peak_vram = max((r["peak_vram_mb"] for r in results), default=0.0)

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hardware": {
            "gpu_name": gpu_name,
            "total_vram_mb": total_vram_mb,
            "cuda_available": torch.cuda.is_available(),
            "torch_version": torch.__version__,
        },
        "provider": {
            "name": provider.name,
            "model_path": getattr(provider, "model_path", None),
            "device": getattr(provider, "device", None),
            "quantization": getattr(provider, "quantization", None),
        },
        "metrics": {
            "total_cases": len(cases),
            "passed_cases": valid_count,
            "schema_compliance_rate_pct": round(success_rate, 2),
            "total_duration_s": total_time,
            "average_latency_s": avg_latency,
            "overall_peak_vram_mb": overall_peak_vram,
        },
        "case_results": results,
    }

    print("\n" + "=" * 70)
    print("  BENCHMARK SUMMARY")
    print(f"  Total Duration:      {total_time}s")
    print(f"  Schema Compliance:   {success_rate:.1f}% ({valid_count}/{len(results)})")
    print(f"  Average Latency:     {avg_latency}s / task")
    print(f"  Peak VRAM:           {overall_peak_vram} MB")
    print("=" * 70)

    # Save to json file
    if output_path:
        out_dir = os.path.dirname(os.path.abspath(output_path))
        os.makedirs(out_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"\n[+] Results successfully saved to: {output_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Career Twin LLM Inference Benchmark Runner")
    parser.add_argument("--eval-dataset", type=str, default="eval/career_twin_eval_dataset.json")
    parser.add_argument("--output", type=str, default="evaluation_results/real_benchmark_results.json")
    parser.add_argument("--provider", type=str, default=None, choices=["local", "mock"])
    parser.add_argument("--model-path", type=str, default=None)
    args = parser.parse_args()

    asyncio.run(
        run_benchmark(
            eval_path=args.eval_dataset,
            output_path=args.output,
            provider_name=args.provider,
            model_path=args.model_path,
        )
    )


if __name__ == "__main__":
    main()
