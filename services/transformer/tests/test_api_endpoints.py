"""
Tests for transformer API endpoints.
"""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import app


class TestAPIEndpoints:
    """Test Flask API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get('/health')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'transformer-nlp'

    def test_analyze_sentiment_positive(self, client):
        """Test sentiment analysis with positive text."""
        response = client.post('/api/analyze-sentiment',
                              json={'text': 'I love this! It\'s amazing!'})

        assert response.status_code == 200
        data = response.get_json()
        assert 'label' in data
        assert 'score' in data
        assert 'compound' in data
        assert data['label'] == 'POSITIVE'
        assert data['compound'] > 0

    def test_analyze_sentiment_negative(self, client):
        """Test sentiment analysis with negative text."""
        response = client.post('/api/analyze-sentiment',
                              json={'text': 'This is terrible and awful!'})

        assert response.status_code == 200
        data = response.get_json()
        assert data['label'] == 'NEGATIVE'
        assert data['compound'] < 0

    def test_analyze_sentiment_batch(self, client):
        """Test batch sentiment analysis."""
        response = client.post('/api/analyze-sentiment',
                              json={'texts': ['Great!', 'Terrible!', 'Okay.']})

        assert response.status_code == 200
        data = response.get_json()
        assert 'results' in data
        assert len(data['results']) == 3
        assert data['results'][0]['label'] == 'POSITIVE'
        assert data['results'][1]['label'] == 'NEGATIVE'

    def test_analyze_sentiment_missing_text(self, client):
        """Test sentiment analysis without text field."""
        response = client.post('/api/analyze-sentiment', json={})

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_recognize_code(self, client):
        """Test code recognition endpoint."""
        code = """
```python
def hello():
    print("hi")
```
"""
        response = client.post('/api/recognize-code', json={'text': code})

        assert response.status_code == 200
        data = response.get_json()
        assert 'code_blocks' in data
        assert 'text_segments' in data
        assert 'has_code' in data
        assert data['has_code'] is True

    def test_extract_keywords(self, client):
        """Test keyword extraction endpoint."""
        text = "Python programming is great for data science"
        response = client.post('/api/extract-keywords',
                              json={'text': text, 'top_n': 5})

        assert response.status_code == 200
        data = response.get_json()
        assert 'keywords' in data
        assert 'count' in data
        assert len(data['keywords']) <= 5

    def test_compact_text(self, client):
        """Test text compaction endpoint."""
        text = "This is a test. " * 20
        response = client.post('/api/compact-text',
                              json={'text': text, 'max_sentences': 3})

        assert response.status_code == 200
        data = response.get_json()
        assert 'original_text' in data
        assert 'compacted_text' in data
        assert 'compression_ratio' in data

    def test_compact_prompt(self, client):
        """Test prompt compaction endpoint."""
        prompt = "What is Python? " * 50  # Long prompt
        response = client.post('/api/compact-prompt',
                              json={'prompt': prompt})

        assert response.status_code == 200
        data = response.get_json()
        assert 'original_prompt' in data
        assert 'compacted_prompt' in data
        assert 'was_compacted' in data

    def test_compact_heuristics(self, client):
        """Test heuristics compaction endpoint."""
        heuristics = "Always validate input. Check edge cases. Write tests."
        response = client.post('/api/compact-heuristics',
                              json={'heuristics': heuristics})

        assert response.status_code == 200
        data = response.get_json()
        assert 'original_heuristics' in data
        assert 'compacted_heuristics' in data

    def test_create_matrix_context(self, client):
        """Test matrix context creation endpoint."""
        payload = {
            'prompt': 'How do I sort a list?',
            'heuristics': 'Use sorted() function',
            'context': '',
            'raw_text': ''
        }
        response = client.post('/api/create-matrix-context', json=payload)

        assert response.status_code == 200
        data = response.get_json()
        assert 'prompt' in data
        assert 'formatted_for_llm' in data

    def test_fix_typos(self, client):
        """Test typo fixing endpoint."""
        text = "teh quick brown fox"
        response = client.post('/api/fix-typos', json={'text': text})

        assert response.status_code == 200
        data = response.get_json()
        assert 'original_text' in data
        assert 'fixed_text' in data
        assert 'the' in data['fixed_text'].lower()

    def test_missing_required_field(self, client):
        """Test endpoints with missing required fields."""
        endpoints = [
            '/api/recognize-code',
            '/api/extract-keywords',
            '/api/compact-text',
            '/api/fix-typos'
        ]

        for endpoint in endpoints:
            response = client.post(endpoint, json={})
            assert response.status_code == 400

    def test_invalid_json(self, client):
        """Test endpoints with invalid JSON."""
        response = client.post('/api/analyze-sentiment',
                              data='invalid json',
                              content_type='application/json')

        assert response.status_code in [400, 415]  # Bad request or unsupported media type
