# Matty's development hardware

Recorded 2026-10-12 from Matty's Windows About screenshot and read-only local checks.
This is hardware inventory, not an accepted deployment pin or a performance result.
Device name, product ID, device ID and the raw screenshot are excluded from publication.

| Item | Evidence |
|---|---|
| Laptop | Lenovo Yoga 9 2-in-1 14ILL10, from the screenshot |
| CPU | Intel Core Ultra 7 258V, 2.20 GHz |
| System RAM | 32 GB installed, 31.5 GB usable |
| GPU | Intel Arc 140V integrated graphics; Windows labels it “(16GB)” |
| GPU driver | 32.0.101.8132, read from Win32_VideoController |
| Ollama | Original inventory: 0.40.3. Read-only CLI/API recheck on 2026-10-18: 0.40.5; deployment acceptance remains pending. |
| Installed models | Local `/api/tags` and `ollama list` now show `qwen3:8b` Q4_K_M and the preserved `llama3.2:3b` |
| Loaded models | `ollama ps` was empty at inspection |

Intel integrated graphics uses system RAM and has no separate dedicated VRAM bank.
The screenshot's 16 GB label is consistent with a shared-memory allowance, rather
than 16 GB of dedicated VRAM. Its 128 MB tile and the different WMI AdapterRAM value
are driver reports, not evidence of a usable dedicated-memory pool. The exact
available graphics budget still needs runtime measurement. [Intel memory documentation](https://www.intel.com/content/www/us/en/support/articles/000020962/graphics.html).

Ollama documents Vulkan support on Windows and Linux, including Intel graphics;
Vulkan is enabled by default when its backend is installed. This identifies a
possible acceleration path, not proof that this laptop has offloaded the selected
model. [Ollama hardware documentation](https://docs.ollama.com/gpu).

Update 2026-10-25: the accepted Ollama 0.40.5 runtime's actual log explains the
CPU-only A01 run. It detected the Arc 140V through Vulkan, then dropped the
integrated GPU because `OLLAMA_IGPU_ENABLE` was unset. A later isolated,
metadata-only launch with `OLLAMA_IGPU_ENABLE=1` retained the Arc 140V as Vulkan
inference compute and reported 18.0 GiB total / 17.2 GiB available shared graphics
memory. No model was loaded and zero requests were sent. This resolves a concrete
host candidate, not model offload, throughput, context-fit or 120-second acceptance.
[Evidence and limits](handoffs/A01_IGPU_HOST_CANDIDATE_2026-10-25.md).

Update 2026-10-12: Matty authorized and completed Qwen3 8B installation. [The setup guide](OLLAMA_SETUP.md) records its digest/license and independently verified blobs. No model was loaded or called; the existing Llama model is preserved and is not an approved substitute. No GPU driver or service environment was changed.

Qwen's full digest/license metadata is now recorded. [The later runtime inventory](evidence/ollama-qwen3-8b-2026-10-18.json) retains the observed 0.40.5 runtime and changed rendered parameter-text hash; original evidence is preserved. This recheck made no model call or machine setting change. Before live readiness, accept the exact
deployment configuration, validate the prompt/context policy, and authorize a
bounded development smoke run. Capture actual `ollama ps` processor/offload output,
memory use, token throughput and latency against the 120-second call target.
Those measurements, warm-up/accounting rules, exact trial seeds and run limits
remain pending under [Q09](decisions/Q09_OLLAMA_QWEN3.md).
