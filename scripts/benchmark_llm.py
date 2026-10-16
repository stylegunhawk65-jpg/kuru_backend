"""Standalone benchmarking tool for local and mock LLM inference on Career Twin tasks."""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
import torch

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.skill import StudentSkill
from app.schemas.intelligence import PrioritizedGapItem
from app.schemas.llm import (
    InterviewPrepRequest,
    ResumeTailorRequest,
    RoadmapGenerateRequest,
)
from app.services.llm.career_tasks import career_task_service
from app.services.llm.factory import get_llm_provider


async def run_benchmark(eval_path: str = "eval/career_twin_eval_dataset.json") -> None:
    """Execute benchmark across all dataset cases and print performance metrics."""
    if not os.path.exists(eval_path):
        print(f"Error: Evaluation dataset not found at '{eval_path}'")
        return

    with open(eval_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    provider = get_llm_provider()
    print("=" * 70)
    print(f"  KURU BACKEND — LLM INFERENCE BENCHMARK")
    print(f"  Provider:       {provider.name}")
    print(f"  CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  GPU Device:     {torch.cuda.get_device_name(0)}")
        print(f"  Initial VRAM:   {torch.cuda.memory_allocated() / (1024*1024):.1f} MB")
    print(f"  Test Cases:     {len(cases)}")
    print("=" * 70)

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
        })

    total_time = round(time.perf_counter() - total_start, 2)
    success_rate = (sum(1 for r in results if r["valid_schema"]) / len(results)) * 100

    print("\n" + "=" * 70)
    print(f"  BENCHMARK SUMMARY")
    print(f"  Total Duration:      {total_time}s")
    print(f"  Schema Compliance:   {success_rate:.1f}% ({sum(1 for r in results if r['valid_schema'])}/{len(results)})")
    avg_latency = round(sum(r["duration_s"] for r in results) / len(results), 3)
    print(f"  Average Latency:     {avg_latency}s / task")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
