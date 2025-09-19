"""
Full Paper Analysis Prompt Template

This module contains the prompt template used for analyzing full PDF content
of research papers using Google Gemini.
"""

FULL_PAPER_ANALYSIS_PROMPT = """
Based on the user's query: "{combined_query}"
Please provide whatever the user wants. Focus on: reasoning context provided to know what the user wants which is: {reasoning_context}.
Based on the user query decide which paper to analyzw from the given papers. You may need to analyze single or multiple depending on the user query.
"""
