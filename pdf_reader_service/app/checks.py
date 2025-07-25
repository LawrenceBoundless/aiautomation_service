# pdf_reader_service/app/checks.py
import fitz  # PyMuPDF
import re
from datetime import datetime, timedelta

def check_edition_dates(doc: fitz.Document) -> list[str]:
    """
    Checks for inconsistent edition dates across the entire document.
    Returns a list of error messages.
    """
    errors = []
    edition_dates = set()
    
    for page_num, page in enumerate(doc):
        instances = page.search_for("Edition Date")
        for inst in instances:
            search_rect = fitz.Rect(inst.x1, inst.y0, inst.x1 + 200, inst.y1)
            text = page.get_text("text", clip=search_rect).strip()
            if text:
                edition_dates.add(text)

    if len(edition_dates) > 1:
        errors.append(f"Inconsistent edition dates found. Dates found: {list(edition_dates)}")
        
    return errors

def check_signature_date_format(doc: fitz.Document) -> list[str]:
    """
    Checks that signature dates use the mm/dd/yyyy format.
    Returns a list of error messages.
    """
    errors = []
    date_format_regex = re.compile(r"\d{2}/\d{2}/\d{4}")

    for page_num, page in enumerate(doc, 1):
        instances = page.search_for("Signature of")
        for inst in instances:
            search_rect = fitz.Rect(inst.x0, inst.y0, page.rect.width, inst.y1 + 30)
            text = page.get_text("text", clip=search_rect)
            potential_dates = re.findall(r'(\d{1,2}/\d{1,2}/\d{2,4})', text)
            for date_str in potential_dates:
                if not date_format_regex.match(date_str):
                    errors.append(f"Page {page_num}: Invalid signature date format found: '{date_str}'. Expected mm/dd/yyyy.")

    return errors

def check_signature_date_recency(doc: fitz.Document) -> list[str]:
    """
    Checks that signature dates are within the last 3 months.
    Returns a list of error messages.
    """
    errors = []
    today = datetime.now()
    three_months_ago = today - timedelta(days=90)

    for page_num, page in enumerate(doc, 1):
        text = page.get_text("text")
        potential_dates = re.findall(r'(\d{2}/\d{2}/\d{4})', text)
        for date_str in potential_dates:
            try:
                signature_date = datetime.strptime(date_str, "%m/%d/%Y")
                if not (three_months_ago <= signature_date <= today):
                    errors.append(f"Page {page_num}: Signature date '{date_str}' is not within the last 3 months.")
            except ValueError:
                continue
    return errors

def check_preparer_jeffrey_hales(doc: fitz.Document) -> list[str]:
    """
    Checks if 'Jeffrey Hales' is listed as the preparer and if a signature date is present.
    Returns a list of error messages.
    """
    errors = []
    found_preparer = False
    for page_num, page in enumerate(doc, 1):
        if page.search_for("Jeffrey Hales"):
            found_preparer = True
            text = page.get_text("text")
            if "Preparer's Signature" in text and not re.search(r'\d{2}/\d{2}/\d{4}', text):
                 errors.append(f"Page {page_num}: Jeffrey Hales listed as preparer, but signature date is missing or malformed.")
    
    if not found_preparer:
        errors.append("Preparer 'Jeffrey Hales' not found in the document.")

    return errors

# --- NEW CHECKS ADDED BELOW ---

def check_missing_pages(doc: fitz.Document) -> list[str]:
    """
    Checks for missing pages by looking for 'Page X of Y' patterns.
    Returns a list of error messages.
    """
    errors = []
    page_sequences = {}  # To hold pages for each form, e.g., {'Form I-130': {1, 2, 4}}

    for page_num, page in enumerate(doc, 1):
        text = page.get_text("text")
        # Find the form name on the page
        form_name_match = re.search(r'(Form\sI-\d{3,4}\w?)', text)
        form_name = form_name_match.group(1) if form_name_match else "Unknown Form"

        # Find the page number "X of Y"
        match = re.search(r'Page\s(\d+)\s+of\s+(\d+)', text)
        if match:
            current_page, total_pages = int(match.group(1)), int(match.group(2))
            if form_name not in page_sequences:
                page_sequences[form_name] = {"pages": set(), "total": total_pages}
            page_sequences[form_name]["pages"].add(current_page)

    for form_name, data in page_sequences.items():
        expected_pages = set(range(1, data["total"] + 1))
        missing = expected_pages - data["pages"]
        if missing:
            errors.append(f"Missing pages for {form_name}: {sorted(list(missing))}")
            
    return errors

def check_a_number_consistency(doc: fitz.Document) -> list[str]:
    """
    Finds all A-Numbers and checks for inconsistencies.
    Returns a list of error messages.
    """
    errors = []
    a_numbers = set()
    a_number_regex = re.compile(r'A\d{9}')

    for page in doc:
        text = page.get_text("text")
        found_numbers = a_number_regex.findall(text)
        for num in found_numbers:
            a_numbers.add(num)

    if len(a_numbers) > 1:
        errors.append(f"Inconsistent A-Numbers found across documents. Numbers found: {list(a_numbers)}")
    elif not a_numbers:
        errors.append("No A-Number found in the entire document set.")
        
    return errors

def check_form_i131_box_3a(doc: fitz.Document) -> list[str]:
    """
    Specifically checks that Form I-131, Page 7, Item 3a is marked NO.
    This is an example of a location-specific check.
    """
    errors = []
    # This check requires knowing the approximate location of the form and checkbox
    # For a real implementation, you would map the coordinates of the "NO" box for item 3a.
    # This is a simplified example that searches for the text.
    
    for page in doc:
        # First, confirm we are on the correct form and page
        if "I-131" in page.get_text() and "Page 7 of" in page.get_text():
            # A simple way to check a box is to see if an 'X' is placed over the "NO" text.
            # PyMuPDF can find text that is covered by other drawing elements.
            # A more robust method uses coordinates.
            no_box_area = page.search_for("3.a. Are you, or any other person included in this application, now in exclusion")
            if no_box_area:
                # Assuming the "NO" box is to the right
                search_rect = fitz.Rect(no_box_area[0].x1 - 100, no_box_area[0].y0, no_box_area[0].x1, no_box_area[0].y1)
                text_in_area = page.get_text("text", clip=search_rect)
                if "YES" in text_in_area: # A simple check if "YES" is marked instead
                    errors.append("Form I-131, Page 7, Item 3a may be incorrectly marked YES instead of NO.")

    return errors