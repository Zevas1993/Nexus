"""
Aggregation utilities for AI assistant results.
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class SuggestionAggregator:
    """Aggregates and ranks suggestions from multiple sources."""
    
    def __init__(self):
        """Initialize suggestion aggregator."""
        self.deduplication_threshold = 0.85  # Similarity threshold
        
    def aggregate_suggestions(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Aggregate suggestions from multiple sources, removing duplicates.
        
        Args:
            results: List of results from different plugins
            
        Returns:
            List of aggregated and deduplicated suggestions
        """
        all_suggestions = []
        
        # Extract all suggestions
        for result in results:
            suggestions = result.get("suggestions", [])
            source = result.get("source", "unknown")
            source_priority = result.get("priority", 5)
            
            for suggestion in suggestions:
                all_suggestions.append({
                    "text": suggestion.get("text", ""),
                    "confidence": suggestion.get("confidence", 0.5),
                    "source": source,
                    "source_priority": source_priority,
                    "metadata": suggestion.get("metadata", {})
                })
                
        # Remove near-duplicates
        unique_suggestions = self._deduplicate(all_suggestions)
        
        # Rank by confidence and source priority
        ranked_suggestions = sorted(
            unique_suggestions,
            key=lambda s: (s["confidence"] * 0.7 + s["source_priority"] * 0.3),
            reverse=True
        )
        
        return ranked_suggestions
        
    def _deduplicate(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove near-duplicate suggestions.
        
        Args:
            suggestions: List of suggestions
            
        Returns:
            List of deduplicated suggestions
        """
        if not suggestions:
            return []
            
        unique = [suggestions[0]]
        
        for current in suggestions[1:]:
            is_duplicate = False
            current_text = current["text"]
            
            for existing in unique:
                similarity = self._calculate_similarity(current_text, existing["text"])
                if similarity > self.deduplication_threshold:
                    is_duplicate = True
                    # Keep the higher confidence one or merge them
                    if current["confidence"] > existing["confidence"]:
                        existing.update(current)
                    break
                    
            if not is_duplicate:
                unique.append(current)
                
        return unique
        
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings.
        
        Args:
            text1: First text string
            text2: Second text string
            
        Returns:
            Similarity score between 0 and 1
        """
        # Simple implementation - could use more sophisticated methods
        shorter = min(text1, text2, key=len)
        longer = max(text1, text2, key=len)
        
        if not shorter:
            return 0.0
            
        # Count matching characters
        matches = sum(c1 == c2 for c1, c2 in zip(shorter, longer))
        return matches / len(longer)


class AnalysisAggregator:
    """Aggregates and merges code analysis results."""
    
    def __init__(self):
        """Initialize analysis aggregator."""
        pass
        
    def aggregate_issues(self, results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Aggregate analysis issues from multiple sources.
        
        Args:
            results: List of results from different plugins
            
        Returns:
            Dictionary of location to list of issues
        """
        all_issues = []
        
        # Extract all issues
        for result in results:
            issues = result.get("issues", [])
            source = result.get("source", "unknown")
            
            for issue in issues:
                issue["detected_by"] = source
                all_issues.append(issue)
                
        # Group by location
        return self._group_issues_by_location(all_issues)
        
    def _group_issues_by_location(self, issues: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group issues by file location.
        
        Args:
            issues: List of issues
            
        Returns:
            Dictionary of location to list of issues
        """
        grouped = {}
        
        for issue in issues:
            location = f"{issue.get('line', 0)}:{issue.get('column', 0)}"
            
            if location not in grouped:
                grouped[location] = []
                
            grouped[location].append(issue)
            
        return grouped
