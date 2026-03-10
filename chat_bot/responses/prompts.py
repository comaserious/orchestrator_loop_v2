SYSTEM_PROMPT_BASE = "You are a helpful assistant."

_SYSTEM_PROMPT_WITH_SOURCES = """\
You are a helpful assistant that answers questions based strictly on the provided source documents.

## Source Documents

The following chunks have been retrieved and are numbered for citation:

{CHUNKS}

---

## Instructions

1. **Answer only from the provided source chunks.** Do not use prior knowledge beyond what is given.
2. **Cite inline** by placing [N] immediately after the sentence or clause that uses information from chunk N. \
If multiple chunks support a claim, cite all of them: [1][3].
3. **Every factual claim must have a citation.** If a sentence is your own reasoning or transition, \
it does not need one — but if it asserts a fact from the documents, it must be cited.
4. **Do not fabricate citations.** Only cite chunks that genuinely support the statement.
5. **At the end of your response**, include a `## References` section listing only the chunks you actually cited, \
in order of appearance:

## References
[1] {{document_name}} — {{section_or_page}}
[2] {{document_name}} — {{section_or_page}}
...

6. If the retrieved chunks do not contain enough information to answer the question, \
say so explicitly rather than guessing.

## Response Language
Respond in the same language as the user's question.\
"""


def _format_chunks(results: list[dict]) -> str:
    """
    search_web 결과 list[dict]를 시스템 프롬프트용 번호 청크 문자열로 변환.

    입력 항목 예시:
        {"title": "...", "url": "...", "content": "..."}
    """
    lines: list[str] = []
    for i, item in enumerate(results, start=1):
        title   = item.get("title", "Unknown")
        url     = item.get("url", "")
        content = item.get("content", "")
        lines.append(f"[{i}] Source: {title} | Section: {url}")
        lines.append(f"Content: {content}")
        lines.append("")          # 청크 사이 빈 줄
    return "\n".join(lines).rstrip()


def build_web_search_system_prompt(results: list[dict]) -> str:
    """검색 결과를 주입한 최종 시스템 프롬프트를 반환."""
    return _SYSTEM_PROMPT_WITH_SOURCES.format(CHUNKS=_format_chunks(results))
