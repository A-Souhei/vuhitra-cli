#!/usr/bin/env python3
"""
Test the /show TODO_list command.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cli import get_todo_list_from_redis

def test_show_todo_list():
    """Test retrieving TODO_list from Redis."""
    print("=" * 80)
    print("TEST: /show TODO_list Command")
    print("=" * 80)
    
    print("\n📤 Fetching TODO_list from Redis...")
    todo_list = get_todo_list_from_redis()
    
    if todo_list is None:
        print("❌ No TODO_list found in Redis")
        return False
    
    if not todo_list:
        print("⚠️  TODO_list is empty")
        return False
    
    print(f"✅ Retrieved TODO_list with {len(todo_list)} items\n")
    
    # Display the TODO_list
    print("=" * 80)
    print("📋 TODO LIST")
    print("=" * 80)
    print(f"\nTotal items: {len(todo_list)}\n")
    
    for item in todo_list:
        status_emoji = "⏳" if item['status'] == 'pending' else "✅"
        print(f"{status_emoji} {item['step_number']}. {item['action']}")
        print(f"   ➤ {item['details']}")
        print(f"   Status: [{item['status'].upper()}]")
        print()
    
    print("=" * 80)
    
    return True

if __name__ == "__main__":
    success = test_show_todo_list()
    sys.exit(0 if success else 1)
