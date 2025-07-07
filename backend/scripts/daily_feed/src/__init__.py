#!/usr/bin/env python3
"""
DailyFeed Word Cloud System

A simplified system for analyzing arXiv papers and generating word clouds
with top phrase extraction and contributing paper identification.
"""

from .text_processor import TextProcessor, TermInfo
from .wordcloud_generator import WordCloudGenerator, WordCloudConfig
from .wordcloud_pipeline import WordCloudPipeline

__version__ = "2.0.0"
__author__ = "DailyFeed Project"

__all__ = [
    # Core pipeline
    "WordCloudPipeline",
    
    # Text processing
    "TextProcessor",
    "TermInfo", 
    
    # Word cloud generation
    "WordCloudGenerator",
    "WordCloudConfig"
] 