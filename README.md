# FastAPI Repository Chat Agent - Multi-Agent MCP System

A production-ready multi-agent system that answers questions about the FastAPI codebase using the Model Context Protocol (MCP), LangGraph orchestration, Neo4j knowledge graph, and OpenAI's ChatGPT API.

## 🎯 Overview

This system implements a sophisticated multi-agent architecture where specialized agents collaborate to provide comprehensive answers about the FastAPI repository:

- **Indexer Agent**: Parses Python code using AST and populates the Neo4j knowledge graph
- **Graph Query Agent**: Traverses the knowledge graph to find relationships and dependencies
- **Code Analyst Agent**: Performs deep code analysis and generates LLM-powered explanations
- **Orchestrator Agent**: Coordinates agents using LangGraph and synthesizes responses

## 🏗️ Architecture

```
User Query
     ↓
FastAPI Gateway (/api/chat)
     ↓
Orchestrator Agent (LangGraph)
     ├→ Indexer Agent (AST parsing, Neo4j population)
     ├→ Graph Query Agent (Cypher queries, graph traversal)
     └→ Code Analyst Agent (Code analysis, LLM explanations)
     ↓
Response Synthesis (OpenAI)
     ↓
User Response
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Docker and Docker Compose (for Neo4j)
- OpenAI API key

### 1. Clone and Setup

```bash
cd /Users/sheru/Documents/cv/fastapi-repo-chat-agent

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
# Required
OPENAI_API_KEY=your-openai-api-key-here
NEO4J_PASSWORD=your-secure-password

# Optional (defaults are fine for development)
OPENAI_MODEL=gpt-4o-mini
NEO4J_URI=bolt://localhost:7687
```

### 3. Start Neo4j

```bash
docker-compose up -d
```

Verify Neo4j is running:
- Browser UI: http://localhost:7474
- Login: neo4j / fastapi-chat-password (or your password from docker-compose.yml)

### 4. Run the Application

```bash
python -m gateway.main
```

The API will be available at http://localhost:8000

## 📚 API Endpoints

### Chat

**POST /api/chat**

Send a message and get a response from the multi-agent system.

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the FastAPI class?",
    "session_id": "optional-session-id"
  }'
```

Response:
```json
{
  "response": "The FastAPI class is the main application class...",
  "session_id": "abc123",
  "agents_used": ["graph_query", "code_analyst"],
  "processing_time": 2.5
}
```

### Indexing

**POST /api/index**

Trigger repository indexing (one-time setup, takes 5-15 minutes):

```bash
curl -X POST http://localhost:8000/api/index
```

**GET /api/index/status**

Check indexing status:

```bash
curl http://localhost:8000/api/index/status
```

### Health & Statistics

**GET /api/agents/health**

Check system health:

```bash
curl http://localhost:8000/api/agents/health
```

**GET /api/graph/statistics**

Get knowledge graph statistics:

```bash
curl http://localhost:8000/api/graph/statistics
```

### WebSocket

**WS /ws/chat**

Real-time chat over WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};

ws.send(JSON.stringify({
  message: "How does FastAPI handle request validation?"
}));
```

## 🧪 Testing

### Example Queries

**Simple (single agent):**
```
"What is the FastAPI class?"
"Show me the docstring for the Depends function"
```

**Medium (2-3 agents):**
```
"How does FastAPI handle request validation?"
"What classes inherit from APIRouter?"
"Find all decorators used in the routing module"
```

**Complex (multiple agents + synthesis):**
```
"Explain the complete lifecycle of a FastAPI request"
"How does dependency injection work and show me examples"
"Compare how Path and Query parameters are implemented"
"What design patterns are used in FastAPI's core and why?"
```

### Health Check

```bash
# Quick health check
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/api/agents/health
```

## 🛠️ Project Structure

```
fastapi-repo-chat-agent/
├── config/              # Configuration and settings
│   ├── settings.py      # Pydantic settings
│   └── logging_config.py
├── core/                # Core models and types
│   ├── exceptions.py
│   ├── models.py
│   └── types.py
├── database/            # Neo4j client and schema
│   ├── neo4j_client.py
│   └── schema.py
├── memory/              # Conversation and caching
│   ├── conversation.py
│   └── cache.py
├── agents/              # Specialized agents
│   ├── indexer/         # Repository parsing
│   ├── graph_query/     # Graph traversal
│   ├── code_analyst/    # Code analysis
│   └── orchestrator/    # LangGraph coordination
├── gateway/             # FastAPI application
│   ├── main.py
│   ├── dependencies.py
│   └── routes/
└── utils/               # Utilities
```

## 🔧 Configuration

Key configuration options in `.env`:

```env
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini        # or gpt-4o for better quality
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=2000

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j

# Application
ENVIRONMENT=development          # development, testing, or production
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

# Repository
FASTAPI_REPO_URL=https://github.com/tiangolo/fastapi.git
REPO_CLONE_PATH=./data/repositories/fastapi
INDEX_ON_STARTUP=false          # Set to true to index on startup

# Agents
AGENT_TIMEOUT=30
AGENT_MAX_RETRIES=3
MAX_CONVERSATION_HISTORY=20
```

## 🎨 Features

### Multi-Agent Coordination
- **LangGraph** workflow for intelligent agent routing
- Conditional execution based on query complexity
- Parallel agent invocation where possible

### Intelligent Query Analysis
- LLM-powered intent classification
- Entity extraction from user queries
- Automatic agent selection

### Knowledge Graph
- Complete AST-based code parsing
- Rich relationship modeling (CONTAINS, IMPORTS, INHERITS_FROM, etc.)
- Efficient Cypher query builders

### Conversation Memory
- Session-based conversation history
- Context window management
- Response caching with TTL

### Production-Ready
- Comprehensive error handling
- Structured logging with correlation IDs
- Type hints throughout
- Pydantic validation
- Async/await patterns

## 📊 Monitoring

### Logs

Logs include correlation IDs for tracing requests across agents:

```
[2024-01-29 12:00:00] [abc123def456] [orchestrator] [INFO] Processing query
[2024-01-29 12:00:01] [abc123def456] [graph_query] [INFO] Executing Cypher query
[2024-01-29 12:00:02] [abc123def456] [code_analyst] [INFO] Analyzing function
```

### Metrics

Get system statistics:

```bash
curl http://localhost:8000/api/graph/statistics
```

Response:
```json
{
  "total_nodes": 1542,
  "total_relationships": 3821,
  "nodes_by_type": {
    "Module": 95,
    "Class": 234,
    "Function": 876
  }
}
```

## 🐛 Troubleshooting

### Neo4j Connection Failed

```bash
# Check Neo4j is running
docker ps | grep neo4j

# View Neo4j logs
docker logs fastapi-chat-neo4j

# Restart Neo4j
docker-compose restart neo4j
```

### OpenAI API Errors

- Verify API key in `.env`
- Check API quota/limits
- Review model name (gpt-4o-mini, gpt-4o, etc.)

### Indexing Issues

- Ensure sufficient disk space (FastAPI repo ~50MB)
- Check network connectivity for git clone
- Review logs for parsing errors

## 📝 Development

### Adding a New Agent

1. Create agent directory in `agents/`
2. Implement tools in `tools.py`
3. Register in orchestrator workflow
4. Update routing logic

### Extending the Knowledge Graph

1. Add new entity types in `core/types.py`
2. Update parser in `agents/indexer/parser.py`
3. Add schema constraints in `database/schema.py`

## 🔒 Security Notes

- **API Keys**: Never commit `.env` file
- **Neo4j**: Use strong passwords in production
- **CORS**: Restrict origins in production (update `gateway/main.py`)
- **Query Validation**: Cypher queries are validated for dangerous operations

## 📄 License

This project is for educational and demonstration purposes.

## 🙏 Acknowledgments

- **FastAPI**: https://github.com/tiangolo/fastapi
- **LangGraph**: Agent orchestration framework
- **Neo4j**: Graph database
- **OpenAI**: LLM API

---

**Built with ❤️ using FastAPI, LangGraph, Neo4j, and OpenAI**
