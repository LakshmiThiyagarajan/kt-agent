# Future Improvements

KT-Agent is designed for internal project KT usage. For organization-wide deployment, the following enhancements are planned.

---

## 1. PII and Sensitive Information Filtering

If used in a real company environment:

- Add a PII detection layer before embedding documents
- Mask emails, phone numbers, IDs, credentials
- Prevent sensitive data from entering the vector database
- Add output filter to prevent GPT from exposing sensitive info

---

## 2. Authentication & Access Control

For enterprise usage:

- Login using organization email (SSO / OAuth)
- Role-based access (only project members can access their KT)
- Namespace isolation per team/project
- API authentication using JWT tokens

---

## 3. Advanced Evaluation Dashboard

- Visual dashboard for evaluation scores
- Track RAG performance over time
- Detect degradation in retrieval quality

---

## 4. Hybrid Search

- Combine vector search + keyword search for higher accuracy

---
