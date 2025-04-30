# VANTA /v1/chat API Workflow

This document outlines the workflow for the OpenAI-compatible `/v1/chat` endpoint implemented in `vanta_router_and_lora.py`.

```mermaid
graph TD
    A[Client Sends POST Request to /v1/chat] --> B{Receive ChatRequest};
    B --> C[Extract Prompt from Messages];
    C --> D[TaskRouter: pick_model(prompt)];
    D --> E{Get LLM Instance};
    C --> F[Construct Final Prompt (with Headers)];
    F --> G[Define SamplingParams];
    E --> H[Call llm.generate(prompt, sampling_params)];
    G --> H;
    H --> I[Extract Text from LLM Output];
    I --> J{Format ChatResponse};
    J --> K[Return ChatResponse to Client];

    subgraph vanta_router_and_lora.py
        B; C; D; E; F; G; H; I; J;
    end

    style A fill:#f9f,stroke:#333,stroke-width:2px;
    style K fill:#f9f,stroke:#333,stroke-width:2px;
```

## Workflow Explanation

1.  **Receive Request:** The FastAPI application receives a POST request at the `/v1/chat` endpoint, containing data structured like OpenAI's Chat Completion request (`ChatRequest`).
2.  **Extract Prompt:** The core text content is extracted from the incoming message list.
3.  **Route Task:** The `TaskRouter` analyzes the extracted prompt to determine the most suitable internal LLM or LoRA model (`model_key`).
4.  **Get LLM:** The corresponding LLM instance (likely from a pre-loaded dictionary `llm_instances`) is retrieved.
5.  **Construct Prompt:** A final prompt is assembled, potentially adding system headers or specific instructions (like step-by-step reasoning requests).
6.  **Define Sampling:** Sampling parameters (`temperature`, `max_tokens`, etc.) are set up based on the request.
7.  **Generate:** The selected LLM's `generate` method is called asynchronously with the final prompt and sampling parameters.
8.  **Extract Output:** The raw text response is extracted from the LLM's output object.
9.  **Format Response:** The extracted text and the model used are formatted into the `ChatResponse` structure.
10. **Return Response:** The `ChatResponse` is sent back to the client. 