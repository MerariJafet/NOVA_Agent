import pytest
from nova.core.episodic_memory import episodic_memory
import sqlite3
from nova.core.memoria import _get_conn


@pytest.fixture
def clean_facts_table():
    """Clean facts table before and after tests."""
    # Clean before test
    with _get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM facts")

    yield

    # Clean after test
    with _get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM facts")


class TestEpisodicMemory:
    """Test suite for EpisodicMemory class."""

    def test_extract_facts_name(self, clean_facts_table):
        """Test name extraction from messages."""
        facts = episodic_memory.extract_facts("Me llamo Juan Pérez")
        assert len(facts) == 1
        assert facts[0]['fact_type'] == 'name'
        assert facts[0]['fact_value'] == 'Juan Pérez'
        assert facts[0]['confidence'] == 1.0

    def test_extract_facts_age(self, clean_facts_table):
        """Test age extraction from messages."""
        facts = episodic_memory.extract_facts("Tengo 30 años")
        assert len(facts) == 1
        assert facts[0]['fact_type'] == 'age'
        assert facts[0]['fact_value'] == '30'

    def test_extract_facts_employer(self, clean_facts_table):
        """Test employer extraction from messages."""
        facts = episodic_memory.extract_facts("Trabajo en Google")
        assert len(facts) == 1
        assert facts[0]['fact_type'] == 'employer'
        assert facts[0]['fact_value'] == 'Google'

    def test_extract_facts_job_title(self, clean_facts_table):
        """Test job title extraction from messages."""
        facts = episodic_memory.extract_facts("Trabajo como ingeniero de software")
        assert len(facts) == 1
        assert facts[0]['fact_type'] == 'job_title'
        assert facts[0]['fact_value'] == 'ingeniero de software'

    def test_extract_facts_likes(self, clean_facts_table):
        """Test likes extraction from messages."""
        facts = episodic_memory.extract_facts("Me gusta programar en Python")
        assert len(facts) == 1
        assert facts[0]['fact_type'] == 'likes'
        assert facts[0]['fact_value'] == 'programar en Python'

    def test_extract_facts_location(self, clean_facts_table):
        """Test location extraction from messages."""
        facts = episodic_memory.extract_facts("Vivo en Madrid, España")
        assert len(facts) == 1
        assert facts[0]['fact_type'] == 'location'
        assert facts[0]['fact_value'] == 'Madrid'

    def test_extract_facts_multiple(self, clean_facts_table):
        """Test extraction of multiple facts from one message."""
        facts = episodic_memory.extract_facts("Me llamo Juan Pérez y tengo 30 años")
        # Should extract name and age
        fact_types = [f['fact_type'] for f in facts]
        assert 'name' in fact_types
        assert 'age' in fact_types

    def test_save_fact_new(self, clean_facts_table):
        """Test saving a new fact."""
        session_id = "test_session_123"
        fact = {
            'fact_type': 'name',
            'fact_key': 'name_juan_perez',
            'fact_value': 'Juan Pérez',
            'confidence': 1.0
        }

        result = episodic_memory.save_fact(session_id, fact)
        assert result == True

        # Verify it was saved
        facts = episodic_memory.get_facts(session_id)
        assert len(facts) == 1
        assert facts[0]['fact_value'] == 'Juan Pérez'

    def test_save_fact_duplicate_update(self, clean_facts_table):
        """Test that duplicate facts are not created, but values are updated."""
        session_id = "test_session_123"
        fact1 = {
            'fact_type': 'name',
            'fact_key': 'name_juan_perez',
            'fact_value': 'Juan Pérez',
            'confidence': 1.0
        }
        fact2 = {
            'fact_type': 'name',
            'fact_key': 'name_juan_perez',
            'fact_value': 'Juan P. Pérez',
            'confidence': 1.0
        }

        # Save first fact
        episodic_memory.save_fact(session_id, fact1)
        facts = episodic_memory.get_facts(session_id)
        assert len(facts) == 1
        assert facts[0]['fact_value'] == 'Juan Pérez'

        # Save "duplicate" with different value - should update
        episodic_memory.save_fact(session_id, fact2)
        facts = episodic_memory.get_facts(session_id)
        assert len(facts) == 1  # Still only one fact
        assert facts[0]['fact_value'] == 'Juan P. Pérez'  # Value updated

    def test_get_facts_by_type(self, clean_facts_table):
        """Test retrieving facts filtered by type."""
        session_id = "test_session_123"

        # Save facts of different types
        facts_data = [
            {'fact_type': 'name', 'fact_key': 'name_juan', 'fact_value': 'Juan', 'confidence': 1.0},
            {'fact_type': 'age', 'fact_key': 'age_30', 'fact_value': '30', 'confidence': 1.0},
            {'fact_type': 'employer', 'fact_key': 'employer_google', 'fact_value': 'Google', 'confidence': 1.0},
        ]

        for fact in facts_data:
            episodic_memory.save_fact(session_id, fact)

        # Get all facts
        all_facts = episodic_memory.get_facts(session_id)
        assert len(all_facts) == 3

        # Get only name facts
        name_facts = episodic_memory.get_facts(session_id, 'name')
        assert len(name_facts) == 1
        assert name_facts[0]['fact_type'] == 'name'

    def test_format_facts_for_prompt(self, clean_facts_table):
        """Test formatting facts for prompt inclusion."""
        session_id = "test_session_123"

        # Save some facts
        facts_data = [
            {'fact_type': 'name', 'fact_key': 'name_juan', 'fact_value': 'Juan Pérez', 'confidence': 1.0},
            {'fact_type': 'employer', 'fact_key': 'employer_google', 'fact_value': 'Google', 'confidence': 1.0},
            {'fact_type': 'likes', 'fact_key': 'likes_python', 'fact_value': 'Python', 'confidence': 1.0},
        ]

        for fact in facts_data:
            episodic_memory.save_fact(session_id, fact)

        formatted = episodic_memory.format_facts_for_prompt(session_id)

        # Check that formatted text contains expected sections
        assert "--- Información sobre el usuario ---" in formatted
        assert "👤 Personal:" in formatted
        assert "• Se llama Juan Pérez" in formatted
        assert "💼 Profesional:" in formatted
        assert "• Trabaja en Google" in formatted
        assert "⭐ Preferencias:" in formatted
        assert "• Le gusta Python" in formatted
        assert "--- Fin información usuario ---" in formatted

    def test_format_facts_empty(self, clean_facts_table):
        """Test formatting when no facts exist."""
        session_id = "empty_session"
        formatted = episodic_memory.format_facts_for_prompt(session_id)
        assert formatted == ""

    def test_delete_fact(self, clean_facts_table):
        """Test deleting a fact."""
        session_id = "test_session_123"
        fact = {
            'fact_type': 'name',
            'fact_key': 'name_juan',
            'fact_value': 'Juan Pérez',
            'confidence': 1.0
        }

        # Save fact
        episodic_memory.save_fact(session_id, fact)
        facts = episodic_memory.get_facts(session_id)
        assert len(facts) == 1
        fact_id = facts[0]['id']

        # Delete fact
        result = episodic_memory.delete_fact(fact_id)
        assert result == True

        # Verify it's gone
        facts = episodic_memory.get_facts(session_id)
        assert len(facts) == 0

    def test_delete_fact_not_found(self, clean_facts_table):
        """Test deleting a non-existent fact."""
        result = episodic_memory.delete_fact(99999)
        assert result == False