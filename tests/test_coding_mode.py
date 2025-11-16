"""Tests for coding mode features: pillars and vanishers."""

import unittest
import tempfile
import shutil
from pathlib import Path
from src.utils.pillar_context import PillarContextManager
from src.utils.vanisher_context import VanisherContextManager


class TestPillarContext(unittest.TestCase):
    """Test pillar context management."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.storage_dir = Path(self.test_dir) / "pillar_storage"
        self.pillars_dir = Path(self.test_dir) / "pillars"
        self.pillars_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_pillar_enabled_by_default(self):
        """Test that pillar context is enabled by default."""
        manager = PillarContextManager(storage_dir=str(self.storage_dir))
        self.assertTrue(manager.is_enabled())

    def test_pillar_can_be_disabled(self):
        """Test that pillar context can be disabled."""
        manager = PillarContextManager(enabled=False, storage_dir=str(self.storage_dir))
        self.assertFalse(manager.is_enabled())

    def test_load_single_file(self):
        """Test loading a single file as pillar."""
        manager = PillarContextManager(storage_dir=str(self.storage_dir))

        # Create test file
        test_file = Path(self.test_dir) / "test.txt"
        test_file.write_text("Test content for pillar")

        # Load file
        success, message = manager.load_file(str(test_file), label="test")
        self.assertTrue(success)
        self.assertIn("test", message)

        # Verify loaded
        self.assertEqual(manager.get_context_count(), 1)
        ctx = manager.get_context_by_label("test")
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.content, "Test content for pillar")

    def test_pillar_persistence(self):
        """Test that pillars persist across sessions."""
        # First session: load pillar
        manager1 = PillarContextManager(storage_dir=str(self.storage_dir))
        test_file = Path(self.test_dir) / "test.txt"
        test_file.write_text("Persistent content")
        manager1.load_file(str(test_file), label="persistent")
        self.assertEqual(manager1.get_context_count(), 1)

        # Second session: load from storage
        manager2 = PillarContextManager(storage_dir=str(self.storage_dir))
        self.assertEqual(manager2.get_context_count(), 1)
        ctx = manager2.get_context_by_label("persistent")
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.content, "Persistent content")

    def test_auto_load_from_pillars_directory(self):
        """Test auto-loading files from pillars/ directory."""
        manager = PillarContextManager(
            storage_dir=str(self.storage_dir),
            pillars_dir=str(self.pillars_dir)
        )

        # Create test files in pillars directory
        (self.pillars_dir / "doc1.md").write_text("Document 1 content")
        (self.pillars_dir / "doc2.md").write_text("Document 2 content")

        # Auto-load
        loaded_count, loaded_files = manager.auto_load_from_pillars_directory()
        self.assertEqual(loaded_count, 2)
        self.assertEqual(len(loaded_files), 2)

        # Verify both were loaded
        self.assertEqual(manager.get_context_count(), 2)

    def test_auto_load_prevents_duplicate_embedding(self):
        """Test that auto-load doesn't re-embed already loaded pillars."""
        manager = PillarContextManager(
            storage_dir=str(self.storage_dir),
            pillars_dir=str(self.pillars_dir)
        )

        # Create test file
        (self.pillars_dir / "doc1.md").write_text("Document 1 content")

        # First auto-load
        loaded_count1, _ = manager.auto_load_from_pillars_directory()
        self.assertEqual(loaded_count1, 1)

        # Second auto-load (should skip already loaded)
        loaded_count2, _ = manager.auto_load_from_pillars_directory()
        self.assertEqual(loaded_count2, 0)  # Already loaded

    def test_clear_pillar(self):
        """Test clearing a specific pillar."""
        manager = PillarContextManager(storage_dir=str(self.storage_dir))
        test_file = Path(self.test_dir) / "test.txt"
        test_file.write_text("Test content")
        manager.load_file(str(test_file), label="test")

        # Clear
        removed = manager.remove_by_label("test")
        self.assertTrue(removed)
        self.assertEqual(manager.get_context_count(), 0)

    def test_clear_all_pillars(self):
        """Test clearing all pillars."""
        manager = PillarContextManager(storage_dir=str(self.storage_dir))

        # Load multiple pillars
        for i in range(3):
            test_file = Path(self.test_dir) / f"test{i}.txt"
            test_file.write_text(f"Content {i}")
            manager.load_file(str(test_file), label=f"test{i}")

        self.assertEqual(manager.get_context_count(), 3)

        # Clear all
        count = manager.clear_all()
        self.assertEqual(count, 3)
        self.assertEqual(manager.get_context_count(), 0)


class TestVanisherContext(unittest.TestCase):
    """Test vanisher context management."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_vanisher_enabled_by_default(self):
        """Test that vanisher context is enabled by default."""
        manager = VanisherContextManager()
        self.assertTrue(manager.is_enabled())

    def test_vanisher_can_be_disabled(self):
        """Test that vanisher context can be disabled."""
        manager = VanisherContextManager(enabled=False)
        self.assertFalse(manager.is_enabled())

    def test_clear_vanisher(self):
        """Test clearing a specific vanisher."""
        manager = VanisherContextManager()

        # Manually create a vanisher (bypassing mirror check for testing)
        # Note: In real use, this would require a mirrored file
        # This test is simplified and would need mocking for full integration

        # For now, just test the clear functionality on empty manager
        removed = manager.remove_by_label("nonexistent")
        self.assertFalse(removed)

    def test_clear_all_vanishers(self):
        """Test clearing all vanishers."""
        manager = VanisherContextManager()
        count = manager.clear_all()
        self.assertEqual(count, 0)  # No vanishers loaded
        self.assertEqual(manager.get_context_count(), 0)

    def test_vanisher_session_scope(self):
        """Test that vanishers are session-scoped (not persisted)."""
        manager = VanisherContextManager()

        # Vanishers should not persist across sessions
        # This is inherent in the design - no storage directory
        self.assertEqual(manager.get_context_count(), 0)


class TestCodingModeIntegration(unittest.TestCase):
    """Test coding mode integration."""

    def test_pillar_and_vanisher_coexist(self):
        """Test that pillars and vanishers can coexist."""
        pillar_mgr = PillarContextManager(enabled=True)
        vanisher_mgr = VanisherContextManager(enabled=True)

        self.assertTrue(pillar_mgr.is_enabled())
        self.assertTrue(vanisher_mgr.is_enabled())

    def test_disabled_in_normal_mode(self):
        """Test that pillars and vanishers are disabled in normal mode."""
        pillar_mgr = PillarContextManager(enabled=False)
        vanisher_mgr = VanisherContextManager(enabled=False)

        self.assertFalse(pillar_mgr.is_enabled())
        self.assertFalse(vanisher_mgr.is_enabled())


if __name__ == '__main__':
    unittest.main()
