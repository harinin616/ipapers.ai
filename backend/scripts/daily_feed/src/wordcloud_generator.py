#!/usr/bin/env python3
"""
Word cloud generation module for creating visual representations of arXiv paper terms.
Supports customizable styling, phrase handling, and category-specific themes.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from wordcloud import WordCloud
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path
import random
from PIL import Image, ImageDraw, ImageFont
import io
import base64
from dataclasses import dataclass

from src.text_processor import TermInfo

@dataclass
class WordCloudConfig:
    """Configuration for word cloud generation."""
    width: int = 1600
    height: int = 900
    max_words: int = 150
    background_color: str = 'white'
    colormap: str = 'viridis'
    font_path: Optional[str] = None
    prefer_horizontal: float = 0.7  # Allow more vertical text for better packing
    min_font_size: int = 15  # Slightly larger minimum for better readability
    max_font_size: int = 80  # Smaller maximum to reduce size variation
    relative_scaling: float = 0.3  # Lower value for more compact layout

class WordCloudGenerator:
    def __init__(self, output_dir: str = "output/wordclouds"):
        """
        Initialize the word cloud generator.
        
        Args:
            output_dir: Directory to save generated word clouds
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Category-specific color schemes using the exact category names
        self.category_colors = {
            'Computer Science (cs.)': ['#2E8B57', '#4682B4', '#6A5ACD', '#20B2AA', '#32CD32'],  # Blues and greens
            'Mathematics (math.)': ['#8B4513', '#CD853F', '#DEB887', '#F4A460', '#D2691E'],  # Browns and golds
            'Physics': ['#DC143C', '#FF6347', '#FF4500', '#FF8C00', '#FFD700'],  # Reds and oranges
            'Economics (econ.)': ['#4B0082', '#8A2BE2', '#9370DB', '#BA55D3', '#DA70D6'],  # Purples
            'Electrical Engineering & Systems Science (eess.)': ['#228B22', '#32CD32', '#7CFC00', '#ADFF2F', '#98FB98'],  # Greens
            'Statistics (stat.)': ['#B22222', '#DC143C', '#FF0000', '#FF6347', '#FFA07A'],  # Reds
            'Quantitative Biology (q-bio.)': ['#006400', '#008B8B', '#2E8B57', '#3CB371', '#20B2AA'],  # Teal greens
            'Quantitative Finance (q-fin.)': ['#191970', '#4169E1', '#0000FF', '#1E90FF', '#00BFFF'],  # Blues
            'default': ['#2C3E50', '#34495E', '#7F8C8D', '#95A5A6', '#BDC3C7']  # Grays
        }
        
        # Category names are already the display names
        self.category_names = {
            'Computer Science (cs.)': 'Computer Science',
            'Mathematics (math.)': 'Mathematics', 
            'Physics': 'Physics',
            'Economics (econ.)': 'Economics',
            'Electrical Engineering & Systems Science (eess.)': 'Electrical Engineering & Systems Science',
            'Statistics (stat.)': 'Statistics',
            'Quantitative Biology (q-bio.)': 'Quantitative Biology',
            'Quantitative Finance (q-fin.)': 'Quantitative Finance'
        }
        
        print(f"✅ Word cloud generator initialized, output directory: {self.output_dir}")
    
    def _get_color_function(self, category: str):
        """Create a color function for the given category."""
        colors = self.category_colors.get(category, self.category_colors['default'])
        
        def color_func(word, font_size, position, orientation, random_state=None, **kwargs):
            return random.choice(colors)
        
        return color_func
    
    def _prepare_frequency_dict(self, terms_info: Dict[str, TermInfo], 
                               max_terms: int = 50) -> Dict[str, int]:
        """
        Prepare frequency dictionary for word cloud generation.
        Uses top phrases first, then fills remaining slots with words to reach max_terms total.
        
        Args:
            terms_info: Dictionary of terms and their information
            max_terms: Total number of terms to include in word cloud
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
        
        frequency_dict = {}
        
        # Take top phrases first
        for term, term_info in list(sorted_phrases.items())[:max_terms]:
            frequency_dict[term] = term_info.frequency
        
        # Fill remaining slots with top words if needed
        remaining_slots = max_terms - len(frequency_dict)
        if remaining_slots > 0:
            for term, term_info in list(sorted_words.items())[:remaining_slots]:
                frequency_dict[term] = term_info.frequency
        
        return frequency_dict
    
    def generate_wordcloud(self, terms_info: Dict[str, TermInfo], 
                          category: str, 
                          date: str,
                          config: Optional[WordCloudConfig] = None,
                          max_terms: int = 50) -> Tuple[WordCloud, str]:
        """
        Generate a word cloud for the given terms and category.
        
        Args:
            terms_info: Dictionary of terms and their information
            category: Category name (e.g., 'cs', 'math')
            date: Date string for filename
            config: Optional configuration override
            
        Returns:
            Tuple of (WordCloud object, output filename)
        """
        if not terms_info:
            print(f"⚠️  No terms found for category {category}")
            return None, None
        
        if config is None:
            config = WordCloudConfig()
        
        print(f"🎨 Generating word cloud for {category} ({len(terms_info)} terms)")
        
        # Prepare frequency dictionary
        frequency_dict = self._prepare_frequency_dict(terms_info, max_terms=max_terms)
        
        if not frequency_dict:
            print(f"⚠️  No valid terms for word cloud in category {category}")
            return None, None
        
        # Create word cloud
        wordcloud = WordCloud(
            width=config.width,
            height=config.height,
            max_words=config.max_words,
            background_color=config.background_color,
            color_func=self._get_color_function(category),
            prefer_horizontal=config.prefer_horizontal,
            min_font_size=config.min_font_size,
            max_font_size=config.max_font_size,
            relative_scaling=config.relative_scaling,
            font_path=config.font_path,
            collocations=False,  # Avoid grouping words that appear together
            margin=2,  # Smaller margin for tighter packing
            repeat=True,  # Allow word repetition to fill space better
            random_state=42  # For reproducible results
        ).generate_from_frequencies(frequency_dict)
        
        # Save the word cloud
        category_name = self.category_names.get(category, category)
        # Since we're in a category-specific directory, use simple filename
        filename = "wordcloud.png"
        filepath = self.output_dir / filename
        
        # Create a figure with title and metadata
        fig, ax = plt.subplots(figsize=(16, 10))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        
        # Add title
        # title = f"{category_name} - {date}"
        # ax.set_title(title, fontsize=20, fontweight='bold', pad=20)
        
        # Add metadata text
        total_papers = len(set().union(*[info.papers for info in terms_info.values()]))
        displayed_words = len([t for t in frequency_dict.keys() if ' ' not in t])
        displayed_phrases = len([t for t in frequency_dict.keys() if ' ' in t])
        
        if displayed_words > 0:
            metadata_text = f"Papers: {total_papers} | Displayed: {displayed_phrases} phrases + {displayed_words} words"
        else:
            metadata_text = f"Papers: {total_papers} | Displayed: {displayed_phrases} phrases"
        # fig.text(0.5, 0.02, metadata_text, ha='center', fontsize=12, style='italic')
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"✅ Word cloud saved: {filepath}")
        return wordcloud, str(filepath)
    
    def save_term_analysis(self, terms_info: Dict[str, TermInfo], 
                          category: str, 
                          date: str,
                          max_terms: int = 50) -> str:
        """
        Save detailed term analysis to a text file.
        
        Args:
            terms_info: Dictionary of terms and their information
            category: Category name
            date: Date string
            
        Returns:
            Output filename
        """
        if not terms_info:
            return None
        
        # Since we're in a category-specific directory, use simple filename
        filename = "term_analysis.txt"
        filepath = self.output_dir / filename
        
        category_name = self.category_names.get(category, category)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Term Analysis Report\n")
            f.write(f"====================\n\n")
            f.write(f"Category: {category_name}\n")
            f.write(f"Date: {date}\n")
            f.write(f"Total Terms: {len(terms_info)}\n")
            
            # Analyze what was used for word cloud
            phrases = {k: v for k, v in terms_info.items() if ' ' in k}
            words = {k: v for k, v in terms_info.items() if ' ' not in k}
            
            # Get what was actually displayed in word cloud
            frequency_dict = self._prepare_frequency_dict(terms_info, max_terms=max_terms)
            displayed_phrases = [term for term in frequency_dict.keys() if ' ' in term]
            displayed_words = [term for term in frequency_dict.keys() if ' ' not in term]
            
            f.write(f"Total Phrases Available: {len(phrases)}\n")
            f.write(f"Total Words Available: {len(words)}\n")
            f.write(f"Displayed in Word Cloud: {len(displayed_phrases)} phrases + {len(displayed_words)} words\n\n")
            
            if displayed_phrases:
                f.write(f"TOP PHRASES (Displayed)\n")
                f.write(f"========================\n\n")
                
                # Sort phrases by frequency
                sorted_phrases = sorted([(k, v) for k, v in phrases.items() if k in displayed_phrases], 
                                      key=lambda x: x[1].frequency, reverse=True)
                
                for phrase, info in sorted_phrases:
                    f.write(f"{phrase:<30} | Freq: {info.frequency:3d} | Papers: {len(info.papers):3d}\n")
                    f.write(f"  Papers: {', '.join(info.papers[:5])}\n")
                    if info.contexts:
                        context = info.contexts[0][:100] + "..." if len(info.contexts[0]) > 100 else info.contexts[0]
                        f.write(f"  Context: {context}\n")
                    f.write(f"\n")
            
            if displayed_words:
                f.write(f"TOP WORDS (Displayed)\n")
                f.write(f"=====================\n\n")
                
                # Sort words by frequency
                sorted_words = sorted([(k, v) for k, v in words.items() if k in displayed_words], 
                                    key=lambda x: x[1].frequency, reverse=True)
                
                for word, info in sorted_words:
                    f.write(f"{word:<30} | Freq: {info.frequency:3d} | Papers: {len(info.papers):3d}\n")
                    f.write(f"  Papers: {', '.join(info.papers[:5])}\n")
                    if info.contexts:
                        context = info.contexts[0][:100] + "..." if len(info.contexts[0]) > 100 else info.contexts[0]
                        f.write(f"  Context: {context}\n")
                    f.write(f"\n")
        
        print(f"✅ Term analysis saved: {filepath}")
        return str(filepath) 