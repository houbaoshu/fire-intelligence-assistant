# Fire Regulation Question Answering

## 1. Purpose

The Fire Regulation QA feature helps fire inspectors find and understand relevant laws, regulations, standards, and official guidance. Answers must be grounded in the configured knowledge base and accompanied by traceable sources.

## 2. Status and Scope

**Status:** Implemented. Organization-scoped retrieval, ranking, grounded generation, citations, and explicit no-evidence and retrieval-only modes are implemented.

Current scope:

- single-turn natural-language questions;
- retrieval and reranking over indexed fire-regulation documents;
- grounded answer generation;
- source citation display;
- copy, clear, and retry actions;
- explicit no-evidence behavior.

Out of scope for the first version:

- multi-turn memory;
- legal-case prediction;
- automatic enforcement decisions;
- user-uploaded private corpora during a QA request;
- answer export and sharing;
- personalized recommendations.

## 3. Users and Permissions

- **Inspector**: asks operational or legal questions within authorized knowledge sources.
- **Supervisor**: uses the same grounded-answer workflow.
- **Administrator**: manages access to knowledge sources through the knowledge-base feature.

Access to a QA answer must never reveal a source document that the current user is not authorized to view.

## 4. Goals

Users must be able to:

- ask a fire-regulation question in Chinese;
- receive a concise, evidence-grounded answer;
- identify the documents and passages supporting the answer;
- understand when evidence is incomplete or unavailable;
- copy the answer without losing its source references;
- retry after a recoverable failure.

## 5. User Workflow

```text
Open Regulation QA
  ↓
Enter Question
  ↓
Submit
  ↓
Retrieve Authorized Documents
  ↓
Rerank Evidence
  ↓
Generate Grounded Answer
  ↓
Review Answer and Citations
  ├─ Copy / Clear
  └─ Retry if Failed
```

## 6. Functional Requirements

### Question Input

- The page must support multiline Chinese text.
- `Enter` should submit when appropriate; `Shift+Enter` should insert a newline.
- Empty or whitespace-only questions must not be submitted.
- The first version should limit a question to 4,000 characters unless the backend defines a stricter limit.
- Submission must be disabled while the same request is pending.

### Answer Display

- The answer must be rendered as safe text or sanitized Markdown.
- The UI must preserve useful structure such as headings, lists, and tables.
- The answer must visually distinguish its conclusion from supporting citations.
- The UI should show retrieval count and processing time only when returned by the backend.
- Copy must include the answer and a readable source list.

### Source Display

Each source should show available metadata such as:

- document title;
- issuing authority;
- version or effective date;
- chapter, section, or article;
- page number;
- quoted or matched excerpt within safe display limits.

Internal vector identifiers and raw similarity scores should not be shown to ordinary users unless required for diagnostics.

### Clear and Retry

- Clear must reset the question and current result after an intentional user action.
- Retry must resubmit the same question without creating duplicate concurrent requests.

## 7. Business Rules

- Retrieval is mandatory whenever RAG is enabled.
- The model must not answer a regulation question solely from general model knowledge.
- The answer must not fabricate a law, article number, issuing authority, effective date, or quotation.
- If evidence conflicts, the answer must describe the conflict and identify the sources.
- If no sufficient evidence is retrieved, the system must say so and avoid a definitive legal conclusion.
- Expired or superseded documents must be labeled and should not silently outrank current documents.
- AI output is assistance, not a substitute for the inspector's legal review or an official legal decision.
- Citations must resolve to the exact indexed source metadata used to create the answer.

## 8. UI Requirements

Recommended layout:

```text
Page Introduction
  ↓
Question Composer
  ↓
Answer Card
  ↓
Source List / Expandable Source Details
```

Required states:

- empty: invite the user to enter a fire-regulation question;
- retrieving: show that regulations are being searched;
- generating: show that an answer is being prepared;
- success: show answer and sources;
- no evidence: show an explicit evidence warning;
- error: show a readable message and retry;
- offline: explain backend unavailability.

The interface must:

- remain usable by keyboard;
- announce answer updates and errors to assistive technology;
- use clear Chinese labels;
- avoid chat-like decorative behavior that obscures citations;
- not display fake suggested answers as generated results.

## 9. API Requirements

Approved contract from `API.md`:

```text
POST /api/qa/query
```

Request:

```json
{
  "question": "消防安全出口被锁闭时适用哪些规定？"
}
```

Current documented response shape:

```json
{
  "answer": "...",
  "sources": []
}
```

Before implementation, `API.md` and backend schemas must define each source object. Recommended fields are:

```json
{
  "document_id": "uuid",
  "title": "document title",
  "article": "article or section",
  "page": 1,
  "excerpt": "supporting excerpt",
  "effective_date": "YYYY-MM-DD"
}
```

The frontend must not assume fields that the backend does not return.

## 10. Data Impact

No dedicated QA history table is required for the initial version.

The feature reads authorized indexed content associated with:

- `knowledge_documents`;
- `knowledge_index_jobs`;
- the configured vector store.

If question history or feedback is introduced later, its schema, retention, privacy, and deletion behavior must be added to `DATABASE.md` before implementation.

## 11. AI Workflow and Rules

```text
Question
  ↓
Normalize Query
  ↓
Retrieve Authorized Candidate Chunks
  ↓
Rerank
  ↓
Construct Context with Source Metadata
  ↓
LLM Generates Grounded Answer
  ↓
Validate Citations
  ↓
Return Answer and Sources
```

AI rules:

- Retrieval, reranking, and generation remain separate backend responsibilities.
- Default retrieval limits must come from configuration, not UI constants.
- The model must be instructed to use only supplied evidence for legal claims.
- The response must state uncertainty when evidence is insufficient.
- Citation identifiers must be derived from retrieved records, not invented by the model.
- Model/provider names must come from environment configuration.
- Prompt text and raw model diagnostics must not be returned to the frontend.

## 12. Validation

- Reject empty questions.
- Enforce the configured length limit on both frontend and backend.
- Normalize harmless surrounding whitespace without changing meaning.
- Treat user input as untrusted content.
- Validate that returned citations reference documents available to the user.
- Reject malformed model output instead of displaying partial internal structures.

## 13. Error Handling

- Backend unavailable: retain the question and allow retry.
- Retrieval unavailable: do not fall back silently to ungrounded generation.
- No relevant evidence: return a successful no-evidence result, not a fabricated answer.
- Model timeout: show a retryable processing error.
- Invalid AI output: report that the answer could not be generated safely.
- Unauthorized source: omit the source and treat the response as invalid if it supported the answer.
- Partial citation metadata: show only fields the backend confirmed.

## 14. Security and Privacy

- All business API calls require bearer authentication.
- Retrieval must enforce document permissions before context reaches the model.
- User questions and source excerpts must not be logged in full by default.
- Rendered answer content must be sanitized.
- Do not expose vector IDs, storage paths, prompts, API keys, or provider credentials.
- Apply rate limits appropriate to model cost and abuse risk.

## 15. Non-Functional Requirements

- The user must receive visible feedback immediately after submission.
- Request cancellation should be supported when the client or backend allows it.
- Duplicate submissions must be prevented.
- Long answers and citations must remain readable on desktop and tablet.
- Citations should remain traceable across re-indexing through stable document references.
- Retrieval and generation metrics may be recorded without storing sensitive content.

## 16. Future Improvements

- multi-turn grounded conversations;
- question history and favorites;
- answer feedback and quality evaluation;
- source-document preview;
- related regulations and suggested follow-up questions;
- comparison of current and superseded provisions;
- export with citations.

## 17. Acceptance Criteria

- [x] A valid question reaches `POST /api/qa/query` through the centralized API client.
- [x] Retrieval and reranking occur before answer generation.
- [x] The answer is displayed with source metadata defined by the backend.
- [x] No-evidence results do not contain fabricated legal claims.
- [x] Expired or conflicting sources are visibly identified when present.
- [x] Copy includes a readable source list.
- [x] Empty, retrieving, generating, success, no-evidence, and error states are distinct.
- [x] Unauthorized source content is never exposed.
- [x] Unsafe Markdown or HTML is not rendered.
- [x] Available lint, type, test, and build checks pass.
