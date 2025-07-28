import fitz
import uuid
import re
import json
import os
import sys
from datetime import datetime
from collections import Counter


ARABIC_NUMERAL_PATTERN = re.compile(r"^((\d+)(\.\d+)*)\s+")

JAPANESE_HEADING_PATTERNS = [
    (re.compile(r"^第[一二三四五六七八九十\d]+章"), "H1"),
    (re.compile(r"^第[一二三四五六七八九十\d]+節"), "H2"),
    (re.compile(r"^第[一二三四五六七八九十\d]+項"), "H3"),
    (re.compile(r"^第[一二三四五六七八九十\d]+目"), "H4"),
]

PARENTHESIZED_NUMERAL_PATTERN = re.compile(r"^\s*\(([\d\w])\)\s*(.*)")

SPECIAL_SECTION_PATTERNS = [
    (re.compile(r"^\s*(?:[\d\W_]*\s*)?(Appendix\s*([A-Z]|\d+)?[:\s].*)", re.IGNORECASE), "H2"),
    (re.compile(r"^\s*(?:[\d\W_]*\s*)?(Appendix)$", re.IGNORECASE), "H2"),
    (re.compile(r"^\s*(?:[\d\W_]*\s*)?(Conclusion|Conclusions)\s*[:\s]?.*", re.IGNORECASE), "H2"),
]

HEADING_FONT_DELTAS = {
    "H1": 6,
    "H2": 3,
    "H3": 1,
    "H4": 0,
    "H5": -2,
}

BOLD_FONT_ADJUSTMENT = 0

LARGE_SPACE_MULTIPLIER = 1.5
VERY_LARGE_SPACE_MULTIPLIER = 3.0
VERY_LARGE_SPACE_ADJUSTMENT = -3

ALL_CAPS_BOOST = -2

X0_TOLERANCE = 5

def analyze_font_sizes_and_x0(doc):
    """
    Analyzes the document to find the most common font size and x0 position.
    This helps in determining the body text font size and the common left margin.
    """
    font_sizes_counts = Counter()
    x0_counts = Counter()

    use_font_info_local = hasattr(fitz, 'TEXT_FONT_INFO')

    for page_num in range(len(doc)):
        page = doc[page_num]
        if use_font_info_local:
            # Get text blocks with font information
            blocks = page.get_text("dict", flags=fitz.TEXT_FONT_INFO)["blocks"]
        else:
            # If TEXT_FONT_INFO is not available, return None for font size and x0
            return None, None

        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    # Round font sizes to 1 decimal place for better grouping
                    font_sizes_counts[round(span["size"], 1)] += 1
                # Use the x0 of the first span in the line for x0 position
                x0_counts[round(line["spans"][0]["bbox"][0], 1)] += 1

    # Get the most common font size and x0 position
    most_common_font_size = font_sizes_counts.most_common(1)[0][0] if font_sizes_counts else None
    most_common_x0 = x0_counts.most_common(1)[0][0] if x0_counts else None

    return most_common_font_size, most_common_x0


def is_all_caps(text):
    """Checks if the given text is entirely in uppercase and contains at least one alphabet."""
    return text.isupper() and any(c.isalpha() for c in text)

def is_title_case(text):
    """
    Checks if the given text is predominantly title case.
    This function is currently not used in the main logic but can be extended for future use.
    """
    words = text.split()
    if not words:
        return False

    capitalized_words = [word for word in words if word and word[0].isupper()]
    return len(capitalized_words) >= len(words) * 0.5 and any(c.isalpha() for c in text)


def get_heading_level(text, font_size=None, is_bold=False, body_text_font_size=None, space_above=None, x0_position=None, min_x0_doc=None):
    """
    Determines the heading level of a given text based on various heuristics:
    font size, boldness, space above, x0 position, and predefined patterns.
    """
    text_stripped = text.strip()

    inferred_level_by_font = None
    if font_size is not None and body_text_font_size is not None:
        # Define thresholds for large and very large spaces based on body text font size
        large_space_threshold = body_text_font_size * LARGE_SPACE_MULTIPLIER
        very_large_space_threshold = body_text_font_size * VERY_LARGE_SPACE_MULTIPLIER

        # Iterate through heading levels to infer based on font size
        for level_key in ["H1", "H2", "H3", "H4", "H5"]:
            delta = HEADING_FONT_DELTAS[level_key]
            threshold = body_text_font_size + delta

            # Adjust threshold for bold text
            effective_threshold = threshold + (BOLD_FONT_ADJUSTMENT if is_bold else 0)

            # Adjust threshold based on space above the line
            if space_above is not None and body_text_font_size is not None:
                if space_above > very_large_space_threshold:
                    effective_threshold += VERY_LARGE_SPACE_ADJUSTMENT
                elif space_above > large_space_threshold:
                    effective_threshold -= 1

            # Boost for all caps text
            if is_all_caps(text_stripped):
                effective_threshold += ALL_CAPS_BOOST

            # Adjust for text aligned with the document's main x0 (left margin)
            if min_x0_doc is not None and x0_position is not None:
                if abs(x0_position - min_x0_doc) < X0_TOLERANCE:
                    if level_key in ["H1", "H2"]:
                        effective_threshold -= 1

            # If the font size meets the effective threshold, infer the level
            if font_size >= effective_threshold:
                inferred_level_by_font = level_key
                break

    # Check for Arabic numeral patterns (e.g., 1, 1.1, 1.1.1)
    match_arabic = ARABIC_NUMERAL_PATTERN.match(text_stripped)
    if match_arabic:
        # Calculate depth based on number of dots
        calculated_depth = match_arabic.group(1).count('.') + 1
        clean_text = text_stripped[len(match_arabic.group(0)):].strip()
        level_from_arabic = f"H{calculated_depth}" if 1 <= calculated_depth <= 5 else None

        # Prioritize font-based inference if it suggests a higher level
        if inferred_level_by_font and int(inferred_level_by_font[1:]) < int(level_from_arabic[1:]):
            return (inferred_level_by_font, clean_text)
        else:
            return (level_from_arabic, clean_text)

    # Check for parenthesized numeral patterns (e.g., (1), (a))
    match_parenthesized = PARENTHESIZED_NUMERAL_PATTERN.match(text_stripped)
    if match_parenthesized:
        clean_text = match_parenthesized.group(2).strip()
        level_from_parenthesized = "H3" # Default to H3 for parenthesized items

        # Prioritize font-based inference if it suggests a higher level
        if inferred_level_by_font and int(inferred_level_by_font[1:]) < int(level_from_parenthesized[1:]):
            return (inferred_level_by_font, clean_text)
        return (level_from_parenthesized, clean_text)

    # Check for Japanese heading patterns
    for pattern, pattern_level in JAPANESE_HEADING_PATTERNS:
        match_japanese = pattern.match(text_stripped)
        if match_japanese:
            clean_text = text_stripped
            level_from_japanese = pattern_level
            # Prioritize font-based inference if it suggests a higher level
            if inferred_level_by_font and int(inferred_level_by_font[1:]) < int(level_from_japanese[1:]):
                return (inferred_level_by_font, clean_text)
            return (level_from_japanese, clean_text)

    # Check for special section patterns (e.g., Appendix, Conclusion)
    for pattern, pattern_level in SPECIAL_SECTION_PATTERNS:
        match_special = pattern.match(text_stripped)
        if match_special:
            clean_text = match_special.group(1).strip()
            return (pattern_level, clean_text)

    # If a level was inferred by font, apply additional checks for validity
    if inferred_level_by_font:
        return (inferred_level_by_font, text_stripped)

    return (None, None)

def extract_pdf_outline(pdf_path):
    """
    Extracsts the outline (table of contents) from a PDF document.
    It identifies headings based on font properties, numbering patterns, and content.
    """
    try:
        doc = fitz.open(pdf_path)
    except fitz.FileDataError:
        print(f"Error: Could not open PDF file at {pdf_path}. Please check the path and file integrity.")
        return {"title": os.path.splitext(os.path.basename(pdf_path))[0].replace("_", " ").title(), "outline": []}

    extracted_title = None
    all_detected_headings = [] # Temporarily store all detected headings for sorting later
    seen_titles = set() # To avoid duplicate entries in the outline

    use_font_info = hasattr(fitz, 'TEXT_FONT_INFO') # Check if font info is available in fitz

    body_text_font_size = None
    min_x0_doc = None
    if use_font_info:
        # Analyze font sizes and x0 positions across the document to set baselines
        body_text_font_size, min_x0_doc = analyze_font_sizes_and_x0(doc)

    potential_footers_headers = Counter()
    pages_to_check_for_footers = min(len(doc), 10) # Check first few pages for recurring headers/footers

    # Identify common headers/footers to exclude from outline
    for page_num in range(pages_to_check_for_footers):
        page = doc[page_num]
        if use_font_info:
            blocks = page.get_text("dict", flags=fitz.TEXT_FONT_INFO)["blocks"]
        else:
            blocks = page.get_text("dict")["blocks"]

        blocks.sort(key=lambda b: b["bbox"][1]) # Sort blocks by their vertical position

        top_lines = []
        bottom_lines = []

        # Collect lines from the top and bottom of the page
        for block in blocks[:min(len(blocks), 2)]: # Check top 2 blocks
            if "lines" in block:
                for line in block["lines"]:
                    line_text = " ".join([span["text"].strip() for span in line["spans"]]).strip()
                    if line_text and len(line_text) > 5:
                        top_lines.append(line_text)

        for block in blocks[max(0, len(blocks)-2):]: # Check bottom 2 blocks
            if "lines" in block:
                for block_line in block["lines"]:
                    line_text = " ".join([span["text"].strip() for span in block_line["spans"]]).strip()
                    if line_text and len(line_text) > 5:
                        bottom_lines.append(line_text)

        for text in top_lines + bottom_lines:
            potential_footers_headers[text] += 1

    excluded_texts = set()
    for text, count in potential_footers_headers.items():
        # If a text appears on more than 50% of the checked pages, exclude it
        if count >= pages_to_check_for_footers * 0.5:
            excluded_texts.add(text)

    # Attempt to extract the main title from the first page
    extracted_title_candidates = []
    if len(doc) > 0:
        first_page = doc[0]
        if use_font_info:
            first_page_blocks = first_page.get_text("dict", flags=fitz.TEXT_FONT_INFO)["blocks"]
        else:
            first_page_blocks = first_page.get_text("dict")["blocks"]

        # Sort by font size descending, then y0 for title candidates
        first_page_blocks.sort(key=lambda b: (-max([s["size"] for l in b.get("lines", []) for s in l["spans"]]) if use_font_info and b.get("lines") else 0, b["bbox"][1]))

        for block in first_page_blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                line_text = " ".join([span["text"].strip() for span in line["spans"]]).strip()
                if line_text:
                    max_font_size = 0
                    if use_font_info:
                        for span in line["spans"]:
                            max_font_size = max(max_font_size, span["size"])

                    extracted_title_candidates.append({
                        "text": line_text,
                        "font_size": max_font_size,
                        "y0": line["bbox"][1],
                        "y1": line["bbox"][3]
                    })

        # Sort title candidates primarily by font size (descending) then by y-position
        extracted_title_candidates.sort(key=lambda x: (-x["font_size"], x["y0"]))

        if extracted_title_candidates:
            # Try to combine multiple lines for the main title
            main_title_parts = []
            if use_font_info and extracted_title_candidates[0]["font_size"] > 0:
                # Set a threshold for what constitutes a "large" font size for the title
                # This could be the largest font size, or a certain delta from the body text size
                title_font_size_threshold = extracted_title_candidates[0]["font_size"] - 2 # Allow slight variations

                prev_y1 = -1
                for candidate in extracted_title_candidates:
                    if candidate["text"] in excluded_texts:
                        continue

                    # Only consider lines that are large enough and relatively close to the previous line
                    if candidate["font_size"] >= title_font_size_threshold and \
                       (prev_y1 == -1 or (candidate["y0"] - prev_y1) < (candidate["font_size"] * 2)): # Heuristic for vertical proximity
                        main_title_parts.append(candidate["text"])
                        prev_y1 = candidate["y1"]
                    elif main_title_parts: # Stop if we encounter a line that's not part of the title block
                        break

                if main_title_parts:
                    extracted_title = " ".join(main_title_parts).strip()

            # Fallback if combining lines didn't yield a title, or if font info isn't available
            if extracted_title is None:
                for candidate in extracted_title_candidates:
                    if candidate["text"] in excluded_texts:
                        continue
                    if 10 < len(candidate["text"]) < 200:
                        extracted_title = candidate["text"]
                        break

    # Fallback title if no title is extracted
    if extracted_title is None:
        extracted_title = os.path.splitext(os.path.basename(pdf_path))[0].replace("_", " ").title()

    # Initialize the outline list here
    outline = []
    # Main loop to extract outline entries from each page
    for page_num in range(len(doc)):
        page = doc[page_num]

        prev_line_bbox_y1_on_page = None # To calculate space between lines

        if use_font_info:
            blocks = page.get_text("dict", flags=fitz.TEXT_FONT_INFO)["blocks"]
        else:
            blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                line_text_parts = []
                max_font_size_in_line = 0
                is_line_bold = False
                x0_position_in_line = None

                if use_font_info:
                    for span in line["spans"]:
                        span_text = span["text"].strip()
                        if span_text:
                            line_text_parts.append(span_text)
                            max_font_size_in_line = max(max_font_size_in_line, span["size"])
                            if (span["flags"] & 1): # Check for bold flag
                                is_line_bold = True
                            if x0_position_in_line is None:
                                x0_position_in_line = span["bbox"][0]
                else:
                    # Fallback for when font info is not available (only text extraction)
                    line_text_parts = [span["text"].strip() for span in line["spans"] if span["text"].strip()]

                text = " ".join(line_text_parts).strip()

                current_line_y0 = line["bbox"][1]
                space_above_current_line = 0
                if prev_line_bbox_y1_on_page is not None:
                    space_above_current_line = current_line_y0 - prev_line_bbox_y1_on_page

                prev_line_bbox_y1_on_page = line["bbox"][3]

                # Skip empty lines, the extracted title, or excluded texts
                if not text or text == extracted_title or text in excluded_texts:
                    continue

                if use_font_info:
                    # Use the comprehensive get_heading_level function with font info
                    is_valid_heading, cleaned_text = get_heading_level(text, max_font_size_in_line, is_line_bold, body_text_font_size, space_above_current_line, x0_position_in_line, min_x0_doc)
                else:
                    # Fallback heading detection if font info is not available
                    is_valid_heading = None
                    cleaned_text = None

                    match_arabic = ARABIC_NUMERAL_PATTERN.match(text)
                    if match_arabic:
                        calculated_depth = match_arabic.group(1).count('.') + 1
                        is_valid_heading = f"H{calculated_depth}" if 1 <= calculated_depth <= 5 else None
                        cleaned_text = text[len(match_arabic.group(0)):].strip()

                    if not is_valid_heading:
                        match_parenthesized = PARENTHESIZED_NUMERAL_PATTERN.match(text)
                        if match_parenthesized:
                            is_valid_heading = "H3" # Default to H3 for parenthesized items if no font info
                            cleaned_text = match_parenthesized.group(2).strip()

                    if not is_valid_heading:
                        for pattern, level in JAPANESE_HEADING_PATTERNS:
                            if pattern.match(text):
                                is_valid_heading = level
                                cleaned_text = text.strip()
                                break

                    if not is_valid_heading:
                        for pattern, level in SPECIAL_SECTION_PATTERNS:
                            match_special = pattern.match(text)
                            if match_special:
                                is_valid_heading = level
                                cleaned_text = match_special.group(1).strip()
                                break

                    if not is_valid_heading:
                        # Simple heuristic for potential headings without font info
                        if 5 < len(text) < 50 and text[0].isupper() and not '.' in text:
                            is_valid_heading = "H1"
                            cleaned_text = text.strip()
                        else:
                            is_valid_heading = None
                            cleaned_text = None


                if is_valid_heading and cleaned_text and cleaned_text not in seen_titles:
                    # Store all detected headings temporarily with their original level and y0 for sorting
                    all_detected_headings.append({
                        "level": is_valid_heading,
                        "text": cleaned_text,
                        "page": page_num + 1, # Convert to 1-indexed page number
                        "y0": line["bbox"][1] # Store y0 for sorting within a page
                    })
                    seen_titles.add(cleaned_text) # Mark as seen to avoid duplicates

    # Sort all detected headings
    # Primary sort: page number
    # Secondary sort: heading level (H1 < H2 < H3...) - this is now a straightforward numerical sort
    # Tertiary sort: y0 position on the page
    def sort_key(item):
        level_num = int(item["level"][1:]) # Convert "H1" to 1, "H2" to 2, etc.
        return (item["page"], level_num, item["y0"])

    all_detected_headings.sort(key=sort_key)

    # Populate the final outline without any remapping, reflecting the sorted order directly
    for heading_info in all_detected_headings:
        outline.append({
            "level": heading_info["level"], # Use the detected level directly
            "text": heading_info["text"],
            "page": heading_info["page"]
        })

    return {
        "title": extracted_title,
        "outline": outline
    }

def main():
    args = sys.argv[1:]

    if "--count" in args:
        if len(args) < 2:
            print("❌ Missing PDF path for --count")
            sys.exit(1)
        pdf_path = args[1]
        try:
            doc = fitz.open(pdf_path)
            print(len(doc))
        except Exception as e:
            print(f"❌ Failed to open PDF: {e}")
            sys.exit(1)
        return

    if len(args) == 1:
        pdf_path = args[0]
        result = extract_pdf_outline(pdf_path)
        output_file = os.path.splitext(pdf_path)[0] + ".json"

    elif len(args) == 4:
        pdf_path = args[0]
        start_page = int(args[1])
        end_page = int(args[2])
        output_file = args[3]

        # Generate a unique temp file name for safe parallel execution
        temp_pdf_path = f"_temp_extract_slice_{uuid.uuid4().hex}.pdf"

        try:
            doc = fitz.open(pdf_path)
            doc.select(range(start_page, end_page))
            doc.save(temp_pdf_path)
            doc.close()

            result = extract_pdf_outline(temp_pdf_path)
        except Exception as e:
            print(f"❌ Failed to extract from {pdf_path} (pages {start_page}-{end_page}): {e}")
            sys.exit(1)
        finally:
            try:
                os.remove(temp_pdf_path)
            except FileNotFoundError:
                print(f"⚠️ Temp file {temp_pdf_path} not found for cleanup.")

    else:
        print("❌ Usage:\n"
              "  python3 extract.py <pdf_path>\n"
              "  python3 extract.py <pdf_path> <start_page> <end_page> <output_path>\n"
              "  python3 extract.py --count <pdf_path>")
        sys.exit(1)

    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print(f"✅ Output saved to {output_file}")


if __name__ == "__main__":
    main()

