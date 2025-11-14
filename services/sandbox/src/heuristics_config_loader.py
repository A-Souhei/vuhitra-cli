"""
Heuristics Configuration Loader

Loads and provides access to heuristics system configuration parameters.
"""
import yaml
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class HeuristicsConfigLoader:
    """Loads and manages heuristics configuration from YAML file."""

    def __init__(self, config_path: str = None):
        """
        Initialize the config loader.

        Args:
            config_path: Path to the heuristics_config.yaml file.
                        If None, looks for it in the parent directory of this file.
        """
        if config_path is None:
            # Default path: parent directory of this file
            current_dir = Path(__file__).parent
            config_path = current_dir.parent / "heuristics_config.yaml"

        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config if config else {}
        except FileNotFoundError:
            logger.warning(f"Heuristics config file not found at {self.config_path}, using defaults")
            return self._get_defaults()
        except Exception as e:
            logger.warning(f"Failed to load heuristics config: {e}, using defaults")
            return self._get_defaults()

    def _get_defaults(self) -> Dict[str, Any]:
        """Return default configuration values."""
        return {
            'scoring_weights': {
                'semantic_weight': 0.50,
                'levenshtein_weight': 0.25,
                'keyword_weight': 0.15,
                'rating_weight': 0.10
            },
            'keyword_weights': {
                'subject_noun': 5.0,
                'proper_noun': 4.0,
                'common_noun': 2.0,
                'verb': 1.0
            },
            'filtering': {
                'min_rating': 4,
                'max_rating_negative': 2,
                'max_stage1_candidates': 100,
                'max_stage2_candidates': 10
            },
            'confidence': {
                'threshold': 0.75
            },
            'insights': {
                'max_insight_length': 150,
                'top_entities': 5,
                'top_keywords': 10
            },
            'chaining': {
                'enabled': True,
                'min_rating_for_chaining': 4,
                'max_chain_depth': 5,
                'include_chain_in_context': True,
                'min_parent_rating': 4
            },
            'auto_iteration': {
                'max_iterations': 10,
                'negative_weight_increment': 0.1,
                'store_failed_attempts': True
            },
            'auto_pruning': {
                'enabled': True,
                'similarity_threshold': 0.85,
                'min_rating_difference': 1,
                'batch_size': 100
            }
        }

    def get(self, *keys, default=None):
        """
        Get a configuration value using dot notation.

        Args:
            *keys: Variable number of keys to traverse the config dict
            default: Default value if key not found

        Returns:
            Configuration value or default

        Examples:
            >>> config.get('scoring_weights', 'semantic_weight')
            0.50
            >>> config.get('confidence', 'threshold')
            0.75
        """
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    # Convenience methods for commonly used values
    def get_semantic_weight(self) -> float:
        """Get semantic similarity weight."""
        return self.get('scoring_weights', 'semantic_weight', default=0.50)

    def get_levenshtein_weight(self) -> float:
        """Get Levenshtein distance weight."""
        return self.get('scoring_weights', 'levenshtein_weight', default=0.25)

    def get_keyword_weight(self) -> float:
        """Get keyword overlap weight."""
        return self.get('scoring_weights', 'keyword_weight', default=0.15)

    def get_rating_weight(self) -> float:
        """Get rating influence weight."""
        return self.get('scoring_weights', 'rating_weight', default=0.10)

    def get_subject_noun_weight(self) -> float:
        """Get subject noun keyword weight."""
        return self.get('keyword_weights', 'subject_noun', default=5.0)

    def get_proper_noun_weight(self) -> float:
        """Get proper noun keyword weight."""
        return self.get('keyword_weights', 'proper_noun', default=4.0)

    def get_common_noun_weight(self) -> float:
        """Get common noun keyword weight."""
        return self.get('keyword_weights', 'common_noun', default=2.0)

    def get_verb_weight(self) -> float:
        """Get verb keyword weight."""
        return self.get('keyword_weights', 'verb', default=1.0)

    def get_min_rating(self) -> int:
        """Get minimum rating threshold."""
        return self.get('filtering', 'min_rating', default=4)

    def get_max_rating_negative(self) -> int:
        """Get maximum rating threshold for negative heuristics (anti-patterns)."""
        return self.get('filtering', 'max_rating_negative', default=2)

    def get_max_stage1_candidates(self) -> int:
        """Get maximum Stage 1 candidates."""
        return self.get('filtering', 'max_stage1_candidates', default=100)

    def get_max_stage2_candidates(self) -> int:
        """Get maximum Stage 2 candidates."""
        return self.get('filtering', 'max_stage2_candidates', default=10)

    def get_confidence_threshold(self) -> float:
        """Get confidence threshold for context injection."""
        return self.get('confidence', 'threshold', default=0.75)

    def get_max_insight_length(self) -> int:
        """Get maximum insight length."""
        return self.get('insights', 'max_insight_length', default=150)

    def get_top_entities(self) -> int:
        """Get number of top entities to extract."""
        return self.get('insights', 'top_entities', default=5)

    def get_top_keywords(self) -> int:
        """Get number of top keywords to extract."""
        return self.get('insights', 'top_keywords', default=10)

    def get_chaining_enabled(self) -> bool:
        """Get whether heuristic chaining is enabled."""
        return self.get('chaining', 'enabled', default=True)

    def get_min_rating_for_chaining(self) -> int:
        """Get minimum rating required to create a chain link."""
        return self.get('chaining', 'min_rating_for_chaining', default=4)

    def get_max_chain_depth(self) -> int:
        """Get maximum allowed chain depth."""
        return self.get('chaining', 'max_chain_depth', default=5)

    def get_include_chain_in_context(self) -> bool:
        """Get whether to include parent chain in context injection."""
        return self.get('chaining', 'include_chain_in_context', default=True)

    def get_min_parent_rating(self) -> int:
        """Get minimum rating for parent heuristics in chain."""
        return self.get('chaining', 'min_parent_rating', default=4)

    # Auto-iteration configuration
    def get_max_auto_iterations(self) -> int:
        """Get maximum number of auto-retry attempts for rating=0 responses."""
        return self.get('auto_iteration', 'max_iterations', default=10)

    def get_negative_weight_increment(self) -> float:
        """Get increment to negative heuristic weight per iteration."""
        return self.get('auto_iteration', 'negative_weight_increment', default=0.1)

    def get_store_failed_attempts(self) -> bool:
        """Get whether to store metadata for failed iteration attempts."""
        return self.get('auto_iteration', 'store_failed_attempts', default=True)

    # Auto-pruning configuration
    def get_auto_pruning_enabled(self) -> bool:
        """Get whether automatic pruning is enabled."""
        return self.get('auto_pruning', 'enabled', default=True)

    def get_pruning_similarity_threshold(self) -> float:
        """Get similarity threshold for identifying duplicate/similar heuristics."""
        return self.get('auto_pruning', 'similarity_threshold', default=0.85)

    def get_pruning_min_rating_difference(self) -> int:
        """Get minimum rating difference to consider one heuristic 'better'."""
        return self.get('auto_pruning', 'min_rating_difference', default=1)

    def get_pruning_batch_size(self) -> int:
        """Get number of heuristics to check per pruning batch."""
        return self.get('auto_pruning', 'batch_size', default=100)
