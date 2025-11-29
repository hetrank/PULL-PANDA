# 🐼 PULL-PANDA

**Intelligent GitHub PR Review Agent**

> Automated code review powered by RAG, Semgrep Static Analysis, Online Learning, and Real-time Analytics

[![Dashboard](https://img.shields.io/badge/Dashboard-Live-blue)](https://pull-panda-delta.vercel.app/)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)

---

## 📋 Overview

PULL-PANDA is an automated GitHub Pull Request review agent that combines AI, static analysis, and machine learning to deliver context-aware, high-quality code reviews. The system learns from each review to continuously improve its performance.

**Live Dashboard:** [https://pull-panda-delta.vercel.app/](https://pull-panda-delta.vercel.app/)

### Key Features

- ✅ **Automated PR Reviews** — Posted directly to GitHub pull requests
- 🔍 **Semgrep Static Analysis** — Security and maintainability checks
- 🧠 **RAG (Retrieval-Augmented Generation)** — Context-aware reviews using Pinecone
- 📈 **Online Learning** — Optimizes prompts based on review quality
- 📊 **Analytics Dashboard** — Real-time visualization of review metrics

---

## 🏗️ Architecture

```
GitHub PR → Fetch Metadata → Semgrep Analysis → RAG Retrieval
                                                      ↓
                                              Feature Extraction
                                                      ↓
                                              Prompt Selection
                                                      ↓
                                              Review Generation
                                                      ↓
                                        Evaluation & Scoring
                                                      ↓
                                  Result Logging & GitHub Comment
```

### System Components

1. **PR Pulling** — Fetch metadata and diffs from GitHub
2. **Semgrep Static Analysis** — Run security and maintainability checks
3. **RAG Retrieval** — Retrieve repository context from Pinecone index
4. **Feature Extraction** — Compute structural features from PR diff
5. **Prompt Selection** — Online learning model selects best-performing prompt
6. **Review Generation** — LLM produces structured review
7. **Evaluation System** — Combines heuristic metrics for quality scoring
8. **Result Logging** — Saves structured JSON and markdown files
9. **GitHub Integration** — Posts final review as PR comment

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Node.js 16+
- GitHub account with API access
- Groq API key
- Pinecone account

### Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/your-username/pull-panda.git
cd pull-panda
```

#### 2. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

#### 3. Configure Environment Variables

Create a `.env` file in the root directory:

```env
OWNER=your-github-username
REPO=your-repo-name
GITHUB_TOKEN=your-github-token
GROQ_API_KEY=your-groq-api-key
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX_NAME=pull-panda-rag
```

#### 4. Run the PR Review Agent

```bash
python main.py
```

#### 5. Run the Dashboard (Optional)

```bash
cd dashboard
npm install
npm run dev
```

The dashboard will be available at `http://localhost:3000`

---

## 🛠️ Technology Stack

### Backend
- **Python** — Core application logic
- **FastAPI** — API framework
- **GitHub REST API** — PR data fetching
- **Groq** — Cloud-hosted LLMs
- **Pinecone** — Vector database for RAG
- **Semgrep** — Static code analysis

### Machine Learning
- **RAG** — Retrieval-Augmented Generation
- **Embedding Models** — Semantic code understanding
- **SGDRegressor** — Online learning for prompt optimization
- **Heuristic Evaluation** — Review quality scoring

### Frontend
- **Next.js 14** — React framework
- **TailwindCSS** — Styling
- **ShadCN** — UI components
- **Vercel** — Deployment platform

---

## 🧪 Testing Strategy

PULL-PANDA implements comprehensive testing at multiple levels:

### Test Coverage

- **Unit Testing** — Feature extraction, prompt selection, evaluation scoring
- **Integration Testing** — Full PR-to-review pipeline
- **Static Testing** — Semgrep rule validation
- **Black-Box Testing** — Randomized diffs and multi-language tests
- **Performance Testing** — Load and spike testing for large PRs
- **GUI Testing** — Dashboard component and page-level testing

---

## 📊 System Capabilities

### AI Review Engine
- Cloud-hosted LLM inference via Groq
- Structured, context-aware feedback generation
- Multi-source input integration (diff, static analysis, RAG context)

### Semgrep Static Analysis
- Vulnerability detection
- Code quality issue identification
- Security pattern matching

### RAG System
- Repository-level code indexing
- Document and configuration file embedding
- Query-based context retrieval via Pinecone

### Online Learning
- SGDRegressor-based prompt optimization
- Multi-feature learning (PR stats, static analysis, evaluation scores)
- Continuous performance improvement

### Analytics Dashboard
- Evaluation summaries and trends
- Static analysis result visualization
- Generated review inspection
- Automatic updates after each review

---

## 📈 Development Timeline

### Sprint 1: Cloud LLM Integration
Initial PR fetch → LLM → Review comment pipeline

### Sprint 2: Static Analysis Integration
Added Semgrep scanning and enriched prompts

### Sprint 3: RAG Integration
Implemented Pinecone indexing and context-aware reviews

### Sprint 4: Online Learning Model
Built prompt selection and evaluation system

### Final Sprint: Dashboard & Testing
Full analytics dashboard and comprehensive test suite

---

## 🔮 Future Roadmap

### Planned Enhancements

- **Local/Offline Processing** — Migration to local LLMs (Ollama) for private reviews
- **Performance Optimization** — Reduced RAG latency and cached embeddings
- **Advanced Features**
  - Inline code change suggestions
  - Automatic PR labeling
  - Repository-level audit reports
  - Background workers for large-scale scanning

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 📧 Contact

For questions or feedback, please open an issue on GitHub.

---

**Built with ❤️ for better code reviews**
