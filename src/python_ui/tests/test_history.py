import unittest
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from editor.layers import LayerStack
from editor.history import HistoryManager, HistoryEntry


class TestHistoryEntry(unittest.TestCase):
    def test_create(self):
        e = HistoryEntry("Test", [("Layer", None, True, False, 1.0, "Normal")], 0)
        self.assertEqual(e.description, "Test")
        self.assertEqual(e.active_index, 0)


class TestHistoryManager(unittest.TestCase):
    def setUp(self):
        self.stack = LayerStack(50, 50)
        self.history = HistoryManager()

    def test_initial_state(self):
        self.assertFalse(self.history.can_undo())
        self.assertFalse(self.history.can_redo())
        self.assertEqual(self.history.index, -1)

    def test_push(self):
        self.history.push("Init", self.stack.layers, self.stack.active_index)
        self.assertEqual(len(self.history.stack), 1)
        self.assertEqual(self.history.index, 0)

    def test_undo_redo(self):
        self.history.push("Init", self.stack.layers, self.stack.active_index)
        self.stack.add_layer("Layer 1")
        self.history.push("Add Layer", self.stack.layers, self.stack.active_index)

        self.assertTrue(self.history.can_undo())
        self.assertFalse(self.history.can_redo())

        self.assertTrue(self.history.undo(self.stack))
        self.assertEqual(self.history.index, 0)
        self.assertTrue(self.history.can_redo())

        self.assertTrue(self.history.redo(self.stack))
        self.assertEqual(self.history.index, 1)

    def test_undo_at_boundary(self):
        self.assertFalse(self.history.undo(self.stack))
        self.history.push("Only", self.stack.layers, self.stack.active_index)
        self.assertFalse(self.history.undo(self.stack))

    def test_redo_at_boundary(self):
        self.assertFalse(self.history.redo(self.stack))
        self.history.push("Only", self.stack.layers, self.stack.active_index)
        self.assertFalse(self.history.redo(self.stack))

    def test_jump_to(self):
        self.history.push("S0", self.stack.layers, self.stack.active_index)
        self.stack.add_layer("L1")
        self.history.push("S1", self.stack.layers, self.stack.active_index)
        self.stack.add_layer("L2")
        self.history.push("S2", self.stack.layers, self.stack.active_index)

        self.assertTrue(self.history.jump_to(self.stack, 0))
        self.assertEqual(self.history.index, 0)
        self.assertTrue(self.history.can_redo())

    def test_jump_to_invalid(self):
        self.assertFalse(self.history.jump_to(self.stack, -1))
        self.assertFalse(self.history.jump_to(self.stack, 0))

    def test_clear(self):
        self.history.push("A", self.stack.layers, self.stack.active_index)
        self.history.push("B", self.stack.layers, self.stack.active_index)
        self.history.clear()
        self.assertEqual(len(self.history.stack), 0)
        self.assertEqual(self.history.index, -1)

    def test_restore_preserves_layer_count(self):
        self.history.push("Init", self.stack.layers, self.stack.active_index)
        self.stack.add_layer("L1")
        self.stack.add_layer("L2")
        self.history.push("After Add", self.stack.layers, self.stack.active_index)
        self.history.undo(self.stack)
        self.assertEqual(len(self.stack.layers), 1)

    def test_push_truncates_redo_stack(self):
        self.history.push("S0", self.stack.layers, self.stack.active_index)
        self.history.push("S1", self.stack.layers, self.stack.active_index)
        self.history.undo(self.stack)
        self.history.push("S2", self.stack.layers, self.stack.active_index)
        self.assertEqual(len(self.history.stack), 2)
        self.assertEqual(self.history.index, 1)

    def test_max_states(self):
        small = HistoryManager(max_states=3)
        for i in range(5):
            small.push(f"S{i}", self.stack.layers, self.stack.active_index)
        self.assertLessEqual(len(small.stack), 3)

    def test_restore_restores_active_index(self):
        self.history.push("Init", self.stack.layers, 0)
        self.stack.add_layer()
        self.history.push("Added", self.stack.layers, 1)
        self.history.undo(self.stack)
        self.assertEqual(self.stack.active_index, 0)

    def test_multiple_undos(self):
        for i in range(5):
            self.stack.add_layer(f"L{i}")
            self.history.push(f"S{i}", self.stack.layers, self.stack.active_index)
        for _ in range(3):
            self.history.undo(self.stack)
        self.assertTrue(self.history.can_undo())
        self.assertTrue(self.history.can_redo())
        self.assertEqual(self.history.index, 1)


if __name__ == "__main__":
    unittest.main()
