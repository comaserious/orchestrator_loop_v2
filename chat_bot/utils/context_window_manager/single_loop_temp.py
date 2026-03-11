"""
[0] system prompt (검색 결과 포함 시 매우 큼)
[1] user message
[2] function_call (iter 0, tool A)
[3] function_call_output (iter 0, tool A 결과 ~20k chars)
[4] function_call (iter 1, tool B)
[5] function_call_output (iter 1, tool B 결과 ~20k chars)
[6] function_call (iter 2, tool C)
[7] function_call_output (iter 2, tool C 결과 ~20k chars)

iter 0의 tool 결과가 아직 원본 20k chars로 남아있음 — LLM은 이미 iter 1에서 이걸 읽고 반응했으니 전체가 필요 없어
search_web 결과가 function_call_output에도 있고 시스템 프롬프트에도 있어 — 이중 과금
tool output 크기에 상한이 있지만 개수에 대한 관리가 없어

┌─────────────────────────────────────┐
│  Tier 1: 고정 (절대 건드리지 않음)     │
│  - system prompt                    │
│  - user message                     │
├─────────────────────────────────────┤
│  Tier 2: 축약 대상 (오래된 tool 교환)  │
│  - iter 0~N-2의 function_call/output│
│  → output을 짧은 요약으로 교체         │
├─────────────────────────────────────┤
│  Tier 3: 원본 유지 (최근 tool 교환)   │
│  - iter N-1의 function_call/output  │
│  → 그대로 유지                       │
└─────────────────────────────────────┘
"""
