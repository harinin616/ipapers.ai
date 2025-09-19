COMPARISON_PROMPT = """
You are an expert academic researcher. I need you to provide a comprehensive comparative analysis of two sets of research papers.

{all_papers_summary}

The user wants to understand the relationship between {query} and {comparison_query}. {relationship_context}

{aspects_context}

Please provide a detailed comparative analysis. Structure your analysis in whatever way makes the most sense for this comparison - you decide the format based on the relationship, aspects, and the papers provided. Be academic, insightful, and cite specific papers when making points.
"""
