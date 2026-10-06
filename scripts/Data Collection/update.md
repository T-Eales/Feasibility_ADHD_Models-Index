# Data collection: updates

This folder contains the updated versions of the data collection code. While testing the previous versions, several problems were found and fixed.

## Web scraper

1. **DuckDuckGo only.** The search library's default mixed several search engines (and Wikipedia) in a random order, so the results weren't reproducible and the source wasn't really DuckDuckGo. It now uses DuckDuckGo only.
2. Reads up to 3 pages of results, so each query can still return up to 30 results.
3. **Search results are saved.** The pool of URLs is saved to its own file, so if the run stops part-way, re-running it reuses the same pool and gives the same sample.
4. **Blocked searches stop the run.** DuckDuckGo sometimes blocks searches for a while; instead of the sample quietly shrinking, the run now stops and says to try again later.
5. **Duplicates are found by their text**, so the same document found at two different URLs (web page or PDF) is only kept once.
6. The PDF download function is simpler: it only saves the file and returns its path.
7. Null characters are removed from PDF text.
8. Test mode has its own pool file, so test runs never mix with the real data.
9. The description at the top of the file has been updated.
## Cleaning and splitting

The original script (`anaylse_and_clean_corpus.py`) was replaced with a new notebook, `Preparing the Data.ipynb`.

Problems found in the original script:
- The chunking loop sat outside the document loop, so only the last document was split into chunks.
- "related" was in the boilerplate list, so sentences mentioning "ADHD-related" were removed.
- The word count was multiplied by the number of documents.
- Only the text was loaded, so each document's URL and provider were lost, which made a provider-level split impossible.
- No personal information was removed, and there was no development/calibration/test split.

The new notebook:
1. Is split into stages that can be run and checked separately, with instructions at the top listing the steps and manual checks in order.
2. Keeps every document linked to its URL, website and provider throughout.
3. Removes invisible PDF characters.
4. Replaces emails, UK phone numbers and names with [EMAIL], [PHONE] and [NAME], and counts how many were removed.
5. Gives each document a fixed ID and saves the cleaned corpus.
6. Creates `screening.xlsx` (Documents and Websites tabs) for manual screening. An existing copy is never overwritten.
7. Will not continue until screening is done. Safety checks stop it if a document isn't marked Yes/No, has no provider, or doesn't match the corpus file.
8. Replaces provider names with codes (P01, P02...), with the key saved in the restricted folder.
9. Splits documents into passages by section: removes menus and boilerplate, keeps bullet lists, merges very short sections, and splits anything over 200 words at line breaks or sentence ends.
10. Applies a broad ADHD keyword filter to remove off-topic passages; removed passages are saved for checking.
11. Saves passages still containing [NAME], [EMAIL] or [PHONE] for a manual check.
12. Splits passages 58:17:25 (development:calibration:test) by provider, so no provider appears in more than one set. Identical passages found in more than one set are kept in development only, and the split is frozen once saved.
13. Creates the rater coding sheets (Stage 1: a random third of development; Stage 2: the test set) with drop-down lists so only valid codes can be entered.
14. Saves an audit summary with all the counts needed for the Method.

**Test data removed (6 Oct 2026):** The dummy corpus from the web scraper test (unrelated gaming websites) was originally committed so the test output could be seen. It has now been removed because it contained full text copied from third-party websites, and a `.gitignore` has been added so no data files are committed in future. All data for the study will be kept in the restricted University folder.
