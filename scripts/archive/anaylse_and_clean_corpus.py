# Import libraries
import pandas as pd
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
import re
import spacy as sp

# What the index column names are: 'Search_Query', 'URL', 'Raw_Text'

# Loading the English language model from spaCy
nlp = sp.load("en_core_web_sm")

# Cleaning the raw data
file_path = 'dummy_corpus.csv'  # Path to the CSV file containing the text data
text_data = pd.read_csv(file_path, usecols=['Raw_Text'])['Raw_Text'].dropna().tolist()  # Load and clean the text data
text_data = [str(text) for text in text_data]  # Ensure all entries are strings
text_data = [text for text in text_data if text.strip()]  # Remove empty strings
text_data = [text for text in text_data if len(text.split()) > 1]  # Remove entries with only 1 word

# Changing the raw text into sentences
sentences = []
for text in text_data:
    doc = nlp(text)
    for sentence in doc.sents:
        sentences.append(sentence.text.strip())

# Cleaning the sentences based on word count, and puncuation
cleaned_sentences = []
for sentence in sentences:
    word_list = sentence.split()
    word_count = len(word_list)

# Skip any sentences with more than 120 words
    if word_count > 120:
        continue  

# Skip any sentences with more than 30 words and no punctuation
    punctuation_checker = [char for char in sentence if char in ['.', '!', '?']]
    if word_count > 30 and len(punctuation_checker) == 0:
        continue  

# Checking for boilerplate phrases and skiping those sentences
    lowercase_sentence = sentence.lower()
    boiler_plate_phrases = ['click here', 'read more', 'subscribe', 'advertisement', 'sponsored',
                            'skip to main', 'skip to content', 'privacy policy', 'terms of service', 'cookie policy',
                            'about us', 'contact us', 'follow us', 'share this', 'related'
                            ]
    if any(phrase in lowercase_sentence for phrase in boiler_plate_phrases):
        continue 
    cleaned_sentences.append(sentence)

# Counting the sentences and words in the cleaned corpus
sentence_count = len(cleaned_sentences)  # Counting total sentences
valid_text = " ".join(cleaned_sentences)  # Joining cleaned sentences into a single string
words = [word for text in text_data for word in word_tokenize(valid_text)]  # Tokenise words
word_count = len(words)  # Count total words

# Print the results
print("Total number of words in the corpus:", word_count)
print("Total number of sentences in the corpus:", sentence_count)

# Filtering out non-grammatical lists (e.g., web-site menus, random text)
cleaned_sentences = [sentence for sentence in cleaned_sentences if len(sentence.split()) < 200]

# Print max word count in a sentence - doing this for later on
if cleaned_sentences:
    max_word_count = max(len(sentence.split()) for sentence in cleaned_sentences)
    print("Maximum number of words in a sentence:", max_word_count)
    # Checking for any random-content sentences that have sneaked in
    longest_sentence = max(cleaned_sentences, key=lambda s: len(s.split()))
    print("\nLongest sentence found:\n", longest_sentence)

# Cleaning for the model code
text_data = [re.sub(r'[^\w\s]', '', text) for text in text_data]  # Remove special characters
text_data = [text.lower() for text in text_data]  # Convert to lowercase
text_data = [re.sub(r'\s+', ' ', text) for text in text_data]  # Normalise whitespace
