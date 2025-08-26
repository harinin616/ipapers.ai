#!/usr/bin/env python3
"""
Test script for search summary functionality
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.search_summary_service import search_summary_service
from app.models.paper import Paper

async def test_search_summary():
    """Test the search summary functionality with sample data."""
    
    # Create sample papers for testing
    sample_papers = [
        Paper(
            paper_id="2301.12345",
            title="Advances in Neural Network Architecture for Computer Vision",
            authors=["John Smith", "Jane Doe", "Bob Johnson"],
            abstract="This paper presents novel neural network architectures that significantly improve performance on computer vision tasks. We introduce a new attention mechanism that enhances feature extraction and reduces computational overhead.",
            categories=["cs.CV", "cs.LG"],
            pdf_url="https://arxiv.org/pdf/2301.12345.pdf",
            published_date=datetime(2023, 1, 15),
            platform="arxiv"
        ),
        Paper(
            paper_id="2301.67890",
            title="Transformer Models for Natural Language Processing: A Comprehensive Study",
            authors=["Alice Brown", "Charlie Wilson"],
            abstract="We conduct a comprehensive analysis of transformer models for various NLP tasks. Our findings show that certain architectural modifications can lead to substantial improvements in performance while maintaining efficiency.",
            categories=["cs.CL", "cs.LG"],
            pdf_url="https://arxiv.org/pdf/2301.67890.pdf",
            published_date=datetime(2023, 1, 20),
            platform="arxiv"
        ),
        Paper(
            paper_id="2301.11111",
            title="Deep Learning for Medical Image Analysis: Recent Breakthroughs",
            authors=["Dr. Sarah Lee", "Prof. Michael Chen", "Dr. Emily Davis"],
            abstract="This review paper examines recent breakthroughs in applying deep learning techniques to medical image analysis. We discuss advances in diagnostic accuracy and clinical applications.",
            categories=["cs.CV", "q-bio.QM"],
            pdf_url="https://arxiv.org/pdf/2301.11111.pdf",
            published_date=datetime(2023, 1, 25),
            platform="arxiv"
        )
    ]
    
    print("🧪 Testing Search Summary Service")
    print("=" * 50)
    
    try:
        # Test 1: Full summary generation
        print("\n📝 Test 1: Generating full summary...")
        query = "machine learning neural networks"
        full_summary = search_summary_service.generate_search_summary(query, sample_papers)
        
        print(f"Query: '{query}'")
        print(f"Papers: {len(sample_papers)}")
        print(f"Summary length: {len(full_summary)} characters")
        print("\nGenerated Summary:")
        print("-" * 30)
        print(full_summary)
        
        # Test 2: Quick summary generation
        print("\n" + "=" * 50)
        print("📝 Test 2: Generating quick summary...")
        quick_summary = search_summary_service.generate_quick_summary(query, sample_papers)
        
        print(f"Quick summary length: {len(quick_summary)} characters")
        print("\nGenerated Quick Summary:")
        print("-" * 30)
        print(quick_summary)
        
        # Test 3: Empty papers list
        print("\n" + "=" * 50)
        print("📝 Test 3: Testing with empty papers list...")
        empty_summary = search_summary_service.generate_search_summary("test query", [])
        print(f"Empty summary: {empty_summary}")
        
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function to run the tests."""
    print("Starting search summary tests...")
    
    # Check if GEMINI_API_KEY is available
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  Warning: GEMINI_API_KEY not found in environment variables")
        print("   The summary generation tests will fail without a valid API key")
        print("   Please set GEMINI_API_KEY in your .env file")
        return
    
    asyncio.run(test_search_summary())

if __name__ == "__main__":
    main()
