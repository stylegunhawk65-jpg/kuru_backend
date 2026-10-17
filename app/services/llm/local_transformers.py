"""Local HuggingFace Transformers provider for Qwen2.5-3B-Instruct with 4-bit quantization on RTX 4050."""

import asyncio
import logging
import os
import time
try:
    import torch
except ImportError:
    torch = None
from app.services.llm.base import BaseLLMProvider, LLMInferenceError, LLMResponse

logger = logging.getLogger("kuru.llm.local")


class LocalTransformersProvider(BaseLLMProvider):
    """Local inference provider running Qwen2.5-3B-Instruct with 4-bit NF4 quantization.

    Designed for 6GB VRAM GPUs (NVIDIA RTX 4050 Laptop).
    Weights are lazy-loaded on-demand and NEVER downloaded at application startup.
    """

    name = "local"

    def __init__(
        self,
        model_id: str | None = None,
        model_path: str | None = None,
        device: str | None = None,
        quantization: str | None = None,
    ):
        self.model_id = model_id or settings.LOCAL_MODEL_ID
        self.model_path = model_path or settings.LOCAL_MODEL_PATH
        self.device = device or settings.LOCAL_MODEL_DEVICE
        self.quantization = quantization or settings.LOCAL_MODEL_QUANTIZATION

        self._model = None
        self._tokenizer = None
        self._load_lock = asyncio.Lock()

    def is_ready(self) -> bool:
        """Check if model weights and tokenizer are loaded in memory."""
        return self._model is not None and self._tokenizer is not None

    def get_memory_stats(self) -> dict[str, float]:
        """Inspect current GPU VRAM and process memory footprint in MB."""
        stats: dict[str, float] = {
            "vram_allocated_mb": 0.0,
            "vram_reserved_mb": 0.0,
            "cuda_available": torch.cuda.is_available(),
        }
        if torch.cuda.is_available():
            stats["vram_allocated_mb"] = round(torch.cuda.memory_allocated() / (1024 * 1024), 2)
            stats["vram_reserved_mb"] = round(torch.cuda.memory_reserved() / (1024 * 1024), 2)
        return stats

    def _sync_load_model(self) -> None:
        """Synchronously load tokenizer and model onto device."""
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        # Determine local model path
        default_local = os.path.join(os.path.expanduser("~"), ".cache", "kuru_models", "Qwen2.5-3B-Instruct")
        target_source = self.model_path
        if not target_source or not os.path.exists(target_source):
            if os.path.exists(default_local) and os.path.isfile(os.path.join(default_local, "config.json")):
                target_source = default_local
            else:
                target_source = self.model_id

        logger.info(
            "Loading local model '%s' (quantization=%s, device=%s)...",
            target_source,
            self.quantization,
            self.device,
        )

        tokenizer = AutoTokenizer.from_pretrained(
            target_source,
            trust_remote_code=True,
            padding_side="left",
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model_kwargs: dict[str, Any] = {"trust_remote_code": True}

        use_cuda = self.device == "cuda" and torch.cuda.is_available()

        if use_cuda:
            if self.quantization == "4bit":
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                )
                model_kwargs["quantization_config"] = bnb_config
                model_kwargs["device_map"] = "auto"
            elif self.quantization == "8bit":
                bnb_config = BitsAndBytesConfig(load_in_8bit=True)
                model_kwargs["quantization_config"] = bnb_config
                model_kwargs["device_map"] = "auto"
            else:
                model_kwargs["torch_dtype"] = torch.float16
                model_kwargs["device_map"] = "auto"
        else:
            logger.warning("CUDA unavailable or CPU device selected; loading model on CPU.")
            model_kwargs["device_map"] = "cpu"
            model_kwargs["torch_dtype"] = torch.float32

        try:
            model = AutoModelForCausalLM.from_pretrained(target_source, **model_kwargs)
        except (torch.cuda.OutOfMemoryError, RuntimeError) as exc:
            if "CUDA" in str(exc) or "out of memory" in str(exc).lower():
                logger.warning(
                    "CUDA 4-bit load error (%s). Falling back to CPU float32...", exc
                )
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                fallback_kwargs = {
                    "device_map": "cpu",
                    "torch_dtype": torch.float32,
                    "trust_remote_code": True,
                }
                model = AutoModelForCausalLM.from_pretrained(target_source, **fallback_kwargs)
            else:
                raise

        model.eval()

        self._tokenizer = tokenizer
        self._model = model
        logger.info("Local model '%s' successfully loaded. Memory: %s", target_source, self.get_memory_stats())

    async def ensure_loaded(self) -> None:
        """Asynchronously ensure model is loaded into memory without concurrent duplicate loads."""
        if self.is_ready():
            return

        async with self._load_lock:
            if not self.is_ready():
                try:
                    await asyncio.to_thread(self._sync_load_model)
                except Exception as exc:
                    logger.error("Failed to load local model weights: %s", exc, exc_info=True)
                    raise LLMInferenceError(
                        f"Could not load local model '{self.model_id}': {exc}",
                        provider=self.name,
                        cause=exc,
                    )

    def _sync_generate(
        self,
        prompt: str,
        system_prompt: str | None,
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """Run token generation in worker thread."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        if hasattr(self._tokenizer, "apply_chat_template"):
            formatted_input = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            formatted_input = f"System: {system_prompt}\nUser: {prompt}\nAssistant:"

        inputs = self._tokenizer(formatted_input, return_tensors="pt")
        input_ids = inputs["input_ids"].to(self._model.device)
        attention_mask = inputs.get("attention_mask")
        if attention_mask is not None:
            attention_mask = attention_mask.to(self._model.device)

        prompt_len = input_ids.shape[1]
        start_time = time.perf_counter()

        generation_kwargs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "max_new_tokens": max_tokens,
            "pad_token_id": self._tokenizer.pad_token_id,
            "eos_token_id": self._tokenizer.eos_token_id,
        }

        if temperature > 0.0:
            generation_kwargs["do_sample"] = True
            generation_kwargs["temperature"] = max(0.01, temperature)
            generation_kwargs["top_p"] = 0.9
        else:
            generation_kwargs["do_sample"] = False

        with torch.no_grad():
            output_tokens = self._model.generate(**generation_kwargs)

        latency = time.perf_counter() - start_time
        new_tokens = output_tokens[0][prompt_len:]
        completion_text = self._tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        return LLMResponse(
            text=completion_text,
            prompt_tokens=prompt_len,
            completion_tokens=len(new_tokens),
            latency_seconds=round(latency, 3),
            model_name=self.model_id,
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate tokens with thread offload and timeout enforcement."""
        await self.ensure_loaded()

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self._sync_generate,
                    prompt,
                    system_prompt,
                    max_tokens,
                    temperature,
                ),
                timeout=settings.LLM_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError as exc:
            raise LLMInferenceError(
                f"Local generation timed out after {settings.LLM_TIMEOUT_SECONDS}s",
                provider=self.name,
                cause=exc,
            )
        except torch.cuda.OutOfMemoryError as exc:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            raise LLMInferenceError(
                f"CUDA Out of Memory on {self.device}. Consider reducing context length or batch size.",
                provider=self.name,
                cause=exc,
            )
        except Exception as exc:
            raise LLMInferenceError(
                f"Local inference generation failed: {exc}",
                provider=self.name,
                cause=exc,
            )
