#!/usr/bin/env python3
"""Script to load data files as eternal contexts with auto-generated descriptions."""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.eternal_context import EternalContextManager
from src.utils.config_loader import ConfigLoader

def main():
    """Main function to load data files as eternal contexts."""
    print("=" * 80)
    print("Loading Data Files as Eternal Contexts")
    print("=" * 80)
    print()

    # Initialize eternal context manager
    eternal_context = EternalContextManager()

    if not eternal_context.is_enabled():
        print("ERROR: Eternal context is disabled in config.yaml")
        return 1

    # Clear existing eternal contexts
    print("🗑️  Clearing existing eternal contexts...")
    count = eternal_context.clear_all()
    print(f"   Cleared {count} existing context(s)")
    print()

    # Get data directory
    data_dir = project_root / "data" / "docs"

    if not data_dir.exists():
        print(f"ERROR: Data directory not found: {data_dir}")
        return 1

    # Find all markdown files
    md_files = list(data_dir.glob("*.md"))

    if not md_files:
        print(f"No markdown files found in {data_dir}")
        return 0

    print(f"Found {len(md_files)} markdown file(s) to load")
    print()

    # Load each file
    loaded_count = 0
    failed_count = 0

    for md_file in md_files:
        label = md_file.stem  # Use filename without extension as label
        print(f"📄 Loading: {md_file.name}")
        print(f"   Label: {label}")
        print(f"   Generating description with LLM...")

        # Load file (description will be auto-generated)
        success, message = eternal_context.load_file(str(md_file), label=label)

        if success:
            print(f"   ✓ {message}")
            loaded_count += 1
        else:
            print(f"   ✗ {message}")
            failed_count += 1

        print()

    # Summary
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Successfully loaded: {loaded_count}")
    print(f"Failed: {failed_count}")
    print(f"Total eternal contexts: {eternal_context.get_context_count()}")
    print()

    # Show loaded contexts
    if loaded_count > 0:
        print("Loaded eternal contexts:")
        for label, ctx in eternal_context.contexts.items():
            size_kb = ctx.get_size_kb()
            print(f"  • {label}: {ctx.description}")
            print(f"    Size: {size_kb:.1f} KB | File: {ctx.file_path}")
        print()

    print("✓ Done!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
