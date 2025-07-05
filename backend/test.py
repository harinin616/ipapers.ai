import asyncio
import logging
import os
from app.services.llm_service import llm_service

# Configure logging to see the debug output
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
# )

def main():
    
    # Test with different length texts
    test_texts = [
        "What is the capital of France?",
        "This is a medium length text that contains some scientific content about machine learning and artificial intelligence. " * 5,
        "This is a very long text that will be used to test the maximum input length limitation of the Specter2 model. It contains a lot of repetitive content to test how the model handles truncation when the input exceeds the maximum token limit. "
    ]

    # Generate embeddings using the service
    embeddings = llm_service.get_embeddings(test_texts)
    
    # Display results
    if embeddings:
        print(f"Successfully generated embeddings for {len(embeddings)} texts")
        print(f"Each embedding has {len(embeddings[0])} dimensions")
    else:
        print("❌ Failed to generate embeddings")

if __name__ == "__main__":
    main()