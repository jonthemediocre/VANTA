# logos_styler.py
# Professional, Fact-Based Styling Engine for VANTA-LOGOS

import logging
import textwrap

logging.basicConfig(level=logging.INFO, format='%(asctime)s - LOGOS_STYLE - %(levelname)s - %(message)s')

# --- Configuration (Could be externalized) ---
DEFAULT_LINE_WIDTH = 80
STYLES = {
    "report": {
        "prefix": "Executive Summary:",
        "suffix": "\n(Full report available upon request)",
        "wrapper_width": DEFAULT_LINE_WIDTH
    },
    "technical": {
        "prefix": "Technical Specification:",
        "suffix": None,
        "wrapper_width": DEFAULT_LINE_WIDTH
    },
    "legal": {
        "prefix": "Legal Analysis:",
        "suffix": "\nDisclaimer: This analysis is for informational purposes only and does not constitute legal advice.",
        "wrapper_width": DEFAULT_LINE_WIDTH
    },
    "default": {
        "prefix": "Factual Statement:",
        "suffix": None,
        "wrapper_width": DEFAULT_LINE_WIDTH
    }
}

def format_professional(text, style="default"):
    """
    Formats the input text using a professional, objective style.
    Applies wrapping and optional prefixes/suffixes based on the style.
    """
    logging.info(f"Applying LOGOS styling (style: {style}) to text: '{text[:50]}...'")
    
    config = STYLES.get(style, STYLES["default"])
    prefix = config.get("prefix")
    suffix = config.get("suffix")
    width = config.get("wrapper_width", DEFAULT_LINE_WIDTH)
    
    # Use textwrap for clean formatting
    wrapped_text = textwrap.fill(text, width=width)
    
    output_parts = []
    if prefix:
        output_parts.append(prefix)
    output_parts.append(wrapped_text)
    if suffix:
        output_parts.append(suffix)
        
    formatted_output = "\n".join(output_parts)
    logging.info("LOGOS styling applied.")
    return formatted_output

# Add more specific formatting functions if needed
# def format_as_code_comment(text):
# def format_as_api_doc(text):

# Example Usage
if __name__ == "__main__":
    raw_text = "Based on the preliminary data analysis, there is a statistically significant correlation between variable X and outcome Y (p < 0.05). Further investigation is warranted to establish causality and explore potential confounding factors before implementing policy changes."
    
    print("--- Default Styling ---")
    print(format_professional(raw_text))
    
    print("\n--- Report Styling ---")
    print(format_professional(raw_text, style="report"))
    
    print("\n--- Technical Styling ---")
    print(format_professional(raw_text, style="technical"))

    print("\n--- Legal Styling ---")
    print(format_professional("The contract stipulates a non-compete clause effective for 12 months post-termination.", style="legal")) 