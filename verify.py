#!/usr/bin/env python3
"""Quick verification script to test imports and basic functionality."""

import sys

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...\n")
    
    try:
        print("✓ Config imports...")
        from config.settings import get_settings
        from config.logging_config import get_logger
        
        print("✓ Core imports...")
        from core.exceptions import AgentException
        from core.models import ChatRequest, ChatResponse
        from core.types import AgentType, QueryType
        
        print("✓ Database imports...")
        from database.neo4j_client import Neo4jClient
        from database.schema import initialize_schema
        
        print("✓ Memory imports...")
        from memory.conversation import ConversationMemory
        from memory.cache import ResponseCache
        
        print("✓ Agent imports...")
        from agents.indexer.tools import get_indexer_tools
        from agents.graph_query.tools import get_graph_query_tools
        from agents.code_analyst.tools import get_code_analyst_tools
        from agents.orchestrator.graph import get_orchestrator_graph
        
        print("✓ Gateway imports...")
        from gateway.main import app
        
        print("\n✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_configuration():
    """Test configuration loading."""
    print("\n" + "="*50)
    print("Testing configuration...\n")
    
    try:
        from config.settings import get_settings
        
        settings = get_settings()
        print(f"✓ Environment: {settings.environment}")
        print(f"✓ Log level: {settings.log_level}")
        print(f"✓ API port: {settings.api_port}")
        print(f"✓ OpenAI model: {settings.openai_model}")
        print(f"✓ Max conversation history: {settings.max_conversation_history}")
        
        print("\n✅ Configuration loaded successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Configuration test failed: {e}")
        return False


def test_models():
    """Test Pydantic models."""
    print("\n" + "="*50)
    print("Testing Pydantic models...\n")
    
    try:
        from core.models import ChatRequest, QueryIntent
        from core.types import QueryType
        
        # Test ChatRequest
        request = ChatRequest(
            message="Test message",
            session_id="test-123"
        )
        print(f"✓ ChatRequest: {request.message}")
        
        # Test QueryIntent
        intent = QueryIntent(
            query_type=QueryType.SIMPLE,
            entities=["FastAPI", "Request"],
            intent="Test intent",
            requires_code_analysis=True,
            requires_graph_query=False
        )
        print(f"✓ QueryIntent: {intent.query_type.value}")
        
        print("\n✅ Models validated successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Model test failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("="*50)
    print("FastAPI Repository Chat Agent - Verification")
    print("="*50)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_configuration()))
    results.append(("Models", test_models()))
    
    print("\n" + "="*50)
    print("VERIFICATION SUMMARY")
    print("="*50)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:20} {status}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "="*50)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("\nNext steps:")
        print("1. Start Neo4j: docker-compose up -d")
        print("2. Add OpenAI key to .env")
        print("3. Run: python -m gateway.main")
        print("="*50)
        return 0
    else:
        print("⚠️  SOME TESTS FAILED")
        print("\nPlease install dependencies:")
        print("  pip install -r requirements.txt")
        print("="*50)
        return 1


if __name__ == "__main__":
    sys.exit(main())
