# Erudite

**Beacon Computing Initiative**  
**Developer Seal: Chance Joaquin Boone (CJB)**

Erudite is a local language-model project with custom model and tokenizer code.
The GitHub repository slug remains `bci-sovereign-engine`; the application title is **Erudite**.

Observe accurately. Preserve faithfully. Analyze transparently. Communicate securely. Act deliberately.

## Existing components

- `source/model.py`: `ModernLLM`, a decoder-only Transformer with RoPE, RMSNorm, SwiGLU, causal attention, tied embedding/output weights, KV caching, and checkpoint helpers.
- `source/tokenizer.py`: `CustomBPETokenizer`, a byte-based BPE tokenizer trained from a corpus; `bci_tokenizer.json` is a checked-in tokenizer artifact.
- `source/interpreter.py`: document parsing and model/tokenizer loading.
- `train_pipeline.py`: a separate training path defining `SovereignTransformer` and using character-code modulo token IDs.
- `app.py`: Streamlit interface using that separate model/checkpoint format.
- `GUI/`: desktop interfaces and training/inference workers.
- `dataset/`: checked-in corpus files. Their content, provenance, and training suitability have not been fully audited.

The inspected model constructors initialize weights locally rather than loading a pretrained external base model. This does not establish the provenance of every dataset or tokenizer artifact.

## Entry points and current status

From a checked-out repository with suitable dependencies installed:

```bash
# Beacon Computing Initiative | Developer Seal: Chance Joaquin Boone (CJB)
python -m streamlit run app.py
```

The title-only update does not establish that training or generation works end to end.
Known integration issues found by source inspection:

1. `GUI/workers.py` and `source/train.py` import `CustomCharTokenizer` and `CharacterLLM`, while the current source modules define `CustomBPETokenizer` and `ModernLLM` instead.
2. The root Streamlit/training path uses character-code modulo encoding and a different architecture/checkpoint format from `source/model.py`; these paths cannot interchange checkpoints directly.
3. `requirements.txt` does not declare all imports used by the desktop/BPE/document paths, including PyQt5, regex, and pandas.
4. `prepare_data.py` substitutes repeated text when its corpus download fails; that fallback is not evidence of a useful training corpus.

A single agreed model/tokenizer/checkpoint path and held-out evaluation are the next engineering steps. Existing model class names and checkpoint filenames are preserved by the title change for compatibility.

## Title-change validation

Python syntax was checked for all four modified UI files. Streamlit/PyQt rendering and model training were not exercised in the editing environment because their dependencies were unavailable.

`ERUDITE_SHA256SUMS` records SHA-256 hashes of the four changed UI files and this README. It excludes itself. The developer seal identifies attribution; it is not a cryptographic signature. Intentional edits require regeneration of the hashes.
