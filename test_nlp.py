import sys
import os

# Add the current directory to sys.path so we can import backend modules
sys.path.append(os.getcwd())

from backend.nlp_ops import extract_topics, short_summary, clean_html

# Sample README text simulating a Machine Learning project
readme_html = """
<h1>Image Classification Pipeline</h1>
<p>This repo implements a robust ML pipeline for image classification using TensorFlow and Keras. 
It is designed to handle large datasets efficiently through a distributed data ingestion system.</p>

<h2>Features</h2>
<ul>
    <li>End-to-end data pipeline for preprocessing and augmentation.</li>
    <li>Scalable model training using TensorFlow distributed strategies.</li>
    <li>Automated deployment scripts for cloud environments.</li>
</ul>

<p>The core logic relies on deep learning techniques to achieve high accuracy. 
We use Docker for containerization to ensure consistent environments across development and production.</p>
"""

print("--- Processing README ---")
# 1. Clean HTML
text = clean_html(readme_html)
print(f"Cleaned Text: {text[:100]}...")

# 2. Extract Topics
# We ask for a small number of clusters since the text is short
print("\n--- Extracting Topics ---")
topics = extract_topics(text, num_clusters=2, top_n=3)
for cluster_id, keywords in topics.items():
    print(f"Cluster {cluster_id}: {keywords}")

# 3. Generate Summary
print("\n--- Generating Summary ---")
summary = short_summary(text, num_sentences=1)
print(f"Summary: {summary}")
