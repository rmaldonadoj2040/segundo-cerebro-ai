# Retrieval Augmented Generation

Retrieval augmented generation is a pattern where an application retrieves relevant knowledge before asking an LLM to answer or generate content.

## Why it matters

- It helps keep answers grounded in project-specific sources.
- It can reduce hallucinations when the retrieved context is relevant.
- It allows a knowledge base to improve without retraining the model.

## Basic flow

- Store raw notes and references.
- Compile them into cleaner wiki pages.
- Query the wiki to produce answers or outputs.
