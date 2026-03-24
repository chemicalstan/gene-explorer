# API Examples

All examples target the local server at `http://localhost:8000`. Responses are piped through `python3 -m json.tool` for readability.

---
## 0. Query structure
```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the median expression of genes in breast cancer?"}' \
  | python3 -m json.tool
```

## 1. Capabilities check
No tool call expected — the agent responds from context alone.
```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How can you help me?"}'  | python3 -m json.tool
` `` 

## 2. Gene list
Triggers `get_targets("lung")`.

` ``bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the main genes involved in lung cancer?"}' | python3 -m json.tool
` ``

## 3. Median expression
Chains `get_targets` → `get_expressions`.

` ``bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the median value expression of genes involved in breast cancer?"}' | python3 -m json.tool
` ``

## 4. Missing data (hallucination guard)
The agent must **not** hallucinate genes or values for unsupported cancer types.

` ``bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the median value expression of genes involved in esophageal cancer?"}' | python3 -m json.tool
` ``

> **Expected response:** `"I don't have data for that cancer type in this dataset."`
```