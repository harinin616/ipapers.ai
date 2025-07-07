#!/usr/bin/env python3
"""
Text preprocessing module for extracting meaningful words and phrases from arXiv papers.
Handles stopword removal, phrase extraction, term frequency analysis, and phrase clustering.
"""

import re
import spacy
from collections import Counter, defaultdict
from typing import List, Dict, Set, Tuple, Any
import numpy as np
from dataclasses import dataclass

@dataclass
class TermInfo:
    """Information about a term (word or phrase) in the corpus."""
    term: str
    frequency: int
    papers: List[str]  # arxiv_ids of papers containing this term
    contexts: List[str]  # sentence contexts where term appears

class TextProcessor:
    def __init__(self, min_phrase_freq: int = 2, max_phrase_length: int = 4):
        """
        Initialize the text processor.
        
        Args:
            min_phrase_freq: Minimum frequency for phrases to be included
            max_phrase_length: Maximum number of words in a phrase
        """
        print("🔄 Loading spaCy model...")
        self.nlp = spacy.load("en_core_web_sm")
        self.min_phrase_freq = min_phrase_freq
        self.max_phrase_length = max_phrase_length
        
        # Extended stopwords for academic papers
        self.stopwords = self._get_academic_stopwords()
        
        # Phrase clustering configuration - synonymous phrases will be merged
        self.phrase_clusters = self._get_phrase_clusters()
        
        print("✅ Text processor initialized")
    
    def _get_phrase_clusters(self) -> Dict[str, List[str]]:
        """
        Define phrase clusters where synonymous phrases should be merged.
        
        Returns:
            Dictionary mapping canonical phrase to list of variant phrases.
            The canonical phrase (key) will be used as the replacement for all variants.
        """
        return {
            # Large Language Models cluster
            "large language models": [
                "language model",
                "language models", 
                "large language",  # incomplete variant
                "llm",
                "llms",
                "large language model",
                "model llms",
                "model llm",
                "model llms",
                "model llm",
            ],
            
            # Add more phrase clusters here as needed
            # Example:
            # "neural networks": [
            #     "neural network",
            #     "artificial neural networks",
            #     "artificial neural network"
            # ],
        }
    
    def _normalize_term(self, term: str) -> str:
        """
        Normalize a term by replacing it with its canonical form if it belongs to a phrase cluster.
        
        Args:
            term: The original term to normalize
            
        Returns:
            The normalized (canonical) term
        """
        term_lower = term.lower().strip()
        
        # Check if this term is in any phrase cluster
        for canonical_phrase, variants in self.phrase_clusters.items():
            if term_lower == canonical_phrase.lower():
                return canonical_phrase  # Already canonical
            elif term_lower in [v.lower() for v in variants]:
                return canonical_phrase  # Replace with canonical form
        
        return term  # No clustering needed, return original
    
    def add_phrase_cluster(self, canonical_phrase: str, variants: List[str]):
        """
        Add a new phrase cluster for future processing.
        
        Args:
            canonical_phrase: The canonical form to use for all variants
            variants: List of variant phrases to be replaced with canonical form
        """
        self.phrase_clusters[canonical_phrase] = variants
        print(f"✅ Added phrase cluster: '{canonical_phrase}' with {len(variants)} variants")
    
    def _get_academic_stopwords(self) -> Set[str]:
        """Get comprehensive stopwords for academic papers."""
        # Basic English stopwords
        basic_stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'this', 'that',
            'these', 'those', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves',
            'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself',
            'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their',
            'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'whose', 'this', 'that',
            'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can'
        }
        
        # Academic-specific stopwords
        academic_stopwords = {
            'paper', 'study', 'research', 'work', 'approach', 'method', 'technique',
            'algorithm', 'model', 'framework', 'system', 'analysis', 'results', 'conclusion',
            'abstract', 'introduction', 'related', 'proposed', 'novel', 'new', 'existing',
            'show', 'demonstrate', 'present', 'propose', 'develop', 'design', 'implement',
            'evaluate', 'compare', 'improve', 'achieve', 'obtain', 'provide', 'offer',
            'based', 'using', 'applied', 'application', 'applications', 'problem', 'problems',
            'solution', 'solutions', 'task', 'tasks', 'data', 'dataset', 'datasets',
            'experiment', 'experiments', 'experimental', 'evaluation', 'performance',
            'effective', 'efficient', 'accuracy', 'precise', 'robust', 'scalable',
            'comprehensive', 'extensive', 'thorough', 'detailed', 'various', 'different',
            'several', 'multiple', 'many', 'few', 'some', 'each', 'every', 'all', 'any',
            'first', 'second', 'third', 'final', 'last', 'next', 'previous', 'current',
            'recent', 'future', 'past', 'present', 'time', 'times', 'case', 'cases',
            'example', 'examples', 'instance', 'instances', 'number', 'numbers', 'amount',
            'level', 'levels', 'type', 'types', 'kind', 'kinds', 'way', 'ways', 'manner',
            'significant', 'important', 'critical', 'key', 'main', 'major', 'minor',
            'general', 'specific', 'particular', 'special', 'common', 'rare', 'unique'
        }
        
        return basic_stopwords | academic_stopwords
    
    def _is_meaningful_noun(self, word: str) -> bool:
        """Check if a noun is meaningful for topic identification across all academic disciplines."""
        # Generic academic terms that don't indicate specific research topics
        generic_academic_nouns = {
            'paper', 'study', 'research', 'work', 'approach', 'method', 'technique',
            'result', 'finding', 'conclusion', 'analysis', 'evaluation', 'experiment',
            'application', 'problem', 'solution', 'task', 'challenge', 'issue',
            'case', 'example', 'instance', 'aspect', 'factor', 'element', 'component',
            'part', 'section', 'chapter', 'figure', 'table', 
            'value', 'parameter', 'variable', 'condition', 'requirement', 'constraint',
            'objective', 'goal', 'purpose', 'aim', 'target', 'outcome',
            'way', 'manner', 'means', 'process', 'procedure', 'step', 'stage',
            'phase', 'level', 'degree', 'extent', 'amount', 'number', 'quantity',
            'size', 'scale', 'scope', 'range', 'limit', 'boundary', 'threshold',
            'criterion', 'measure', 'metric', 'indicator', 'feature',
            'property', 'characteristic', 'attribute', 'quality', 'trait',
            'type', 'kind', 'sort', 'class', 'category', 'group', 'set',
            'collection', 'series', 'sequence', 'order', 'arrangement',
            'structure', 'organization', 'pattern', 'trend', 'behavior',
            'performance', 'effectiveness', 'efficiency', 'accuracy', 'precision',
            'error', 'mistake', 'fault', 'failure', 'success', 'improvement',
            'enhancement', 'development', 'implementation',
            'design', 'construction', 'creation', 'generation', 'production'
        }
        
        # Very short or very common words
        if len(word) < 3 or word in generic_academic_nouns:
            return False
        
        # Single letters or numbers
        if len(word) == 1 or word.isdigit():
            return False
        
        # Words that are mostly numbers
        if sum(c.isdigit() for c in word) > len(word) / 2:
            return False
        
        return True
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text or text == "Not found":
            return ""
        
        # Remove LaTeX commands and special characters
        text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', text)
        text = re.sub(r'\\[a-zA-Z]+', '', text)
        
        # Remove URLs and emails
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove special characters but keep hyphens and apostrophes
        text = re.sub(r'[^\w\s\-\']', ' ', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def extract_single_words(self, text: str) -> List[str]:
        """Extract meaningful nouns and proper nouns from text."""
        if not text:
            return []
        
        doc = self.nlp(text)
        words = []
        
        for token in doc:
            # Skip if it's a stopword, punctuation, space, or too short
            if (token.is_stop or token.is_punct or token.is_space or 
                len(token.text) < 3 or token.text.lower() in self.stopwords):
                continue
            
            # Only keep nouns and proper nouns for topic identification
            if token.pos_ in ['NOUN', 'PROPN']:
                # Use lemma for better grouping
                word = token.lemma_.lower().strip()
                if word and len(word) >= 3 and self._is_meaningful_noun(word):
                    words.append(word)
        
        return words
    
    def extract_phrases(self, text: str) -> List[str]:
        """Extract meaningful noun phrases and technical terms from text."""
        if not text:
            return []
        
        doc = self.nlp(text)
        phrases = []
        
        # Extract noun phrases (focus on nominal concepts)
        for chunk in doc.noun_chunks:
            phrase_text = chunk.text.lower().strip()
            phrase_words = phrase_text.split()
            
            # Filter for meaningful noun phrases
            if (len(phrase_words) <= self.max_phrase_length and 
                len(phrase_words) >= 2 and
                self._is_meaningful_noun_phrase(chunk)):
                
                # Clean the phrase (keep only meaningful parts)
                clean_phrase = self._clean_noun_phrase(phrase_words)
                
                if clean_phrase and len(clean_phrase.split()) >= 2:
                    phrases.append(clean_phrase)
        
        # Extract technical compound nouns (noun + noun patterns)
        phrases.extend(self._extract_technical_compounds(doc))
        
        # Extract named entities (scientific/technical terms)
        phrases.extend(self._extract_named_entities(doc))
        
        return list(set(phrases))  # Remove duplicates
    
    def _is_meaningful_noun_phrase(self, chunk) -> bool:
        """Check if a noun phrase contains meaningful content for topic identification."""
        # Get the tokens in the chunk
        tokens = [token for token in chunk]
        
        # Must have at least one noun or proper noun
        has_noun = any(token.pos_ in ['NOUN', 'PROPN'] for token in tokens)
        if not has_noun:
            return False
        
        # Filter out phrases that are mostly generic terms
        meaningful_words = [token.lemma_.lower() for token in tokens 
                           if token.pos_ in ['NOUN', 'PROPN'] and 
                           self._is_meaningful_noun(token.lemma_.lower())]
        
        # Need at least one meaningful noun
        return len(meaningful_words) > 0
    
    def _clean_noun_phrase(self, phrase_words: List[str]) -> str:
        """Clean a noun phrase to keep only meaningful parts."""
        # Remove common determiners and prepositions that might slip through
        skip_words = {'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by'}
        
        cleaned_words = []
        for word in phrase_words:
            if (len(word) >= 3 and 
                word.isalpha() and 
                word not in skip_words and
                word not in self.stopwords):
                cleaned_words.append(word)
        
        return ' '.join(cleaned_words)
    
    def _extract_technical_compounds(self, doc) -> List[str]:
        """Extract technical compound nouns (noun + noun patterns)."""
        compounds = []
        
        for i in range(len(doc) - 1):
            token1, token2 = doc[i], doc[i + 1]
            
            # Look for noun + noun compounds
            if (token1.pos_ in ['NOUN', 'PROPN'] and 
                token2.pos_ in ['NOUN', 'PROPN'] and
                not token1.is_stop and not token2.is_stop):
                
                compound = f"{token1.lemma_.lower()} {token2.lemma_.lower()}"
                
                # Check if both parts are meaningful
                if (self._is_meaningful_noun(token1.lemma_.lower()) and
                    self._is_meaningful_noun(token2.lemma_.lower())):
                    compounds.append(compound)
        
        return compounds
    
    def _extract_named_entities(self, doc) -> List[str]:
        """Extract named entities that represent scientific/academic concepts."""
        entities = []
        
        for ent in doc.ents:
            # Focus on entities that could be relevant across academic disciplines
            if ent.label_ in ['PRODUCT', 'ORG']:
                entity_text = ent.text.lower().strip()
                
                # Filter for multi-word entities that could be academic concepts
                if (len(entity_text.split()) >= 2 and 
                    len(entity_text.split()) <= self.max_phrase_length and
                    all(len(word) >= 3 and word.isalpha() for word in entity_text.split())):
                    entities.append(entity_text)
        
        return entities
    
    def process_papers(self, papers: List[Dict[str, Any]]) -> Dict[str, TermInfo]:
        """
        Process a list of papers and extract terms with their metadata.
        
        Args:
            papers: List of paper dictionaries
            
        Returns:
            Dictionary mapping terms to TermInfo objects
        """
        print(f"🔄 Processing {len(papers)} papers for term extraction...")
        
        term_papers = defaultdict(list)  # term -> list of paper arxiv_ids
        term_contexts = defaultdict(list)  # term -> list of contexts
        term_frequencies = Counter()
        
        for paper in papers:
            arxiv_id = paper.get('arxiv_id', 'unknown')
            title = paper.get('title', '')
            abstract = paper.get('abstract', '')
            
            # Combine title and abstract, giving title more weight
            combined_text = f"{title} {title} {abstract}"  # title appears twice for weight
            clean_text = self.clean_text(combined_text)
            
            if not clean_text:
                continue
            
            # Extract words and phrases
            words = self.extract_single_words(clean_text)
            phrases = self.extract_phrases(clean_text)
            
            # Process all terms and apply normalization
            all_terms = words + phrases
            paper_terms = set()  # Track unique terms per paper
            
            for original_term in all_terms:
                # Normalize the term (apply phrase clustering)
                normalized_term = self._normalize_term(original_term)
                
                if normalized_term not in paper_terms:  # Count each term only once per paper
                    term_papers[normalized_term].append(arxiv_id)
                    paper_terms.add(normalized_term)
                
                term_frequencies[normalized_term] += 1
                
                # Add context (sentence containing the original term)
                sentences = clean_text.split('.')
                for sentence in sentences:
                    if original_term in sentence.lower():
                        context = sentence.strip()[:200]  # Limit context length
                        if context:
                            term_contexts[normalized_term].append(context)
                        break
        
        # Create TermInfo objects
        terms_info = {}
        for term, frequency in term_frequencies.items():
            # Filter terms by minimum frequency for phrases
            if ' ' in term and frequency < self.min_phrase_freq:
                continue
            
            terms_info[term] = TermInfo(
                term=term,
                frequency=frequency,
                papers=list(set(term_papers[term])),  # Remove duplicates
                contexts=term_contexts[term][:5]  # Keep top 5 contexts
            )
        
        # Log phrase clustering results
        clustered_phrases = [term for term in terms_info.keys() if term in self.phrase_clusters.keys()]
        if clustered_phrases:
            print(f"🔗 Applied phrase clustering:")
            for phrase in clustered_phrases:
                variants = self.phrase_clusters[phrase]
                print(f"   - '{phrase}' (merged from {len(variants)} variants)")
        
        print(f"✅ Extracted {len(terms_info)} unique terms")
        print(f"   - Single words: {len([t for t in terms_info if ' ' not in t])}")
        print(f"   - Phrases: {len([t for t in terms_info if ' ' in t])}")
        
        return terms_info
    
    def get_top_terms(self, terms_info: Dict[str, TermInfo], 
                     max_terms: int = 50) -> Dict[str, TermInfo]:
        """
        Get top terms for word cloud generation.
        Uses top phrases first, then fills with words to reach max_terms total.
        """
        # Separate phrases and words
        phrases = {k: v for k, v in terms_info.items() if ' ' in k}
        words = {k: v for k, v in terms_info.items() if ' ' not in k}
        
        # Sort by frequency
        sorted_phrases = dict(sorted(phrases.items(), 
                                   key=lambda x: x[1].frequency, 
                                   reverse=True))
        sorted_words = dict(sorted(words.items(), 
                                 key=lambda x: x[1].frequency, 
                                 reverse=True))
        
        result = {}
        
        # Take top phrases first
        for term, info in list(sorted_phrases.items())[:max_terms]:
            result[term] = info
        
        # Fill remaining slots with top words if needed
        remaining_slots = max_terms - len(result)
        if remaining_slots > 0:
            for term, info in list(sorted_words.items())[:remaining_slots]:
                result[term] = info
        
        return result
    
    def categorize_papers_by_discipline(self, papers: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group papers by their primary discipline (first category) using the 8 predefined categories."""
        discipline_groups = {
            'Computer Science (cs.)': [],
            'Economics (econ.)': [],
            'Electrical Engineering & Systems Science (eess.)': [],
            'Mathematics (math.)': [],
            'Statistics (stat.)': [],
            'Quantitative Biology (q-bio.)': [],
            'Quantitative Finance (q-fin.)': [],
            'Physics': []
        }
        
        for paper in papers:
            categories = paper.get('categories', [])
            if categories:
                # Use first category to determine discipline
                first_category = categories[0]
                
                # Categorize using the same logic as analyze_categories.py
                if first_category.startswith('cs.'):
                    discipline_groups['Computer Science (cs.)'].append(paper)
                elif first_category.startswith('econ.'):
                    discipline_groups['Economics (econ.)'].append(paper)
                elif first_category.startswith('eess.'):
                    discipline_groups['Electrical Engineering & Systems Science (eess.)'].append(paper)
                elif first_category.startswith('math.'):
                    discipline_groups['Mathematics (math.)'].append(paper)
                elif first_category.startswith('stat.'):
                    discipline_groups['Statistics (stat.)'].append(paper)
                elif first_category.startswith('q-bio.'):
                    discipline_groups['Quantitative Biology (q-bio.)'].append(paper)
                elif first_category.startswith('q-fin.'):
                    discipline_groups['Quantitative Finance (q-fin.)'].append(paper)
                else:
                    discipline_groups['Physics'].append(paper)
        
        # Only return categories that have papers
        return {k: v for k, v in discipline_groups.items() if v} 