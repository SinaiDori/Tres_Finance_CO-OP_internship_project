#!/usr/bin/env python3
"""
Simple test to verify browser automation is working correctly.
"""
import asyncio
from browser_use import Agent, Controller
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_browser_connection():
    """Test if browser automation can open a simple webpage."""
    try:
        print("🔍 Testing browser connection...")
        
        # Create a simple controller for testing
        controller = Controller()
        llm = ChatOpenAI(model="gpt-4o")
        
        # Simple task to test browser connection
        test_task = "Open https://www.google.com and tell me the page title."
        
        agent = Agent(task=test_task, llm=llm, controller=controller)
        result = await agent.run()
        
        print("✅ Browser connection test successful!")
        print(f"Result: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Browser connection test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_browser_connection())
