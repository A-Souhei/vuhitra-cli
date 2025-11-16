# Step 2: Architecture Summary

Once the LLM sees the file list or key files, ask for a high-level summary.

## What to Request

- **1-paragraph purpose summary**: What does this application do?
- **High-level architecture**: Monolith, microservices, layered, MVC, etc.
- **Application flow**: Request → Response, or Module → Module interactions
- **Critical dependencies**: Database, APIs, external services
- **Data flow**: How information moves through the system

## Architecture Summary Prompt

```
Using the following file list and code snippets, produce:

1. One paragraph describing the application's purpose and main functionality
2. The architectural pattern used (e.g., MVC, microservices, layered architecture)
3. Three to five bullet points showing the typical system flow (e.g., request → routing → business logic → database → response)
4. A list of 8–10 key files/modules to understand, with 1-line reasons for each
5. Main external dependencies and integrations
```

## Expected Output Format

### Purpose Summary
One clear paragraph explaining what the application does and who it serves.

### Architecture Pattern
Identification of:
- MVC (Model-View-Controller)
- Microservices
- Layered architecture
- Modular monolith
- Event-driven
- Or combination/custom pattern

### System Flow
Example:
1. HTTP request arrives at API endpoint
2. Router directs to controller
3. Controller validates input
4. Service layer processes business logic
5. Data layer queries database
6. Response formatted and returned

### Key Files/Modules
List 8-10 critical files with brief explanations of their role.

### Dependencies
- Database systems (PostgreSQL, MongoDB, etc.)
- External APIs
- Message queues
- Caching layers
- Authentication providers

---

*Part of the LLM Codebase Interaction Guide - Step 2 of 8*
