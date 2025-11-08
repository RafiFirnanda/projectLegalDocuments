import os
import re
import fitz
import string
import logging
import argparse
import time
from pathlib import Path
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

def setup_argparse() -> argparse.Namespace:
    """Setup command line argument parsing."""
    parser = argparse.ArgumentParser(description='Process legal document PDFs')
    parser.add_argument('--input', type=str, default='Dataset',
                      help='Input folder containing PDF files')
    parser.add_argument('--output', type=str, default='data/raw',
                      help='Output folder for processed text files')
    parser.add_argument('--log', type=str, default='logs/cleaning.log',
                      help='Path to log file')
    parser.add_argument('--workers', type=int, default=4,
                      help='Number of worker threads')
    parser.add_argument('--batch-size', type=int, default=10,
                      help='Number of files to process in one batch')
    return parser.parse_args()

# Parse command line arguments
args = setup_argparse()

# Get absolute paths
current_dir = Path(__file__).parent.absolute()
input_folder = current_dir / args.input
output_folder = current_dir / args.output
log_file_path = current_dir / args.log

# Create necessary directories
os.makedirs(output_folder, exist_ok=True)
os.makedirs(log_file_path.parent, exist_ok=True)

# Setup logging after ensuring directory exists
logging.basicConfig(
    filename=str(log_file_path),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Pastikan folder ada
os.makedirs(output_folder, exist_ok=True)
os.makedirs(log_file_path.parent, exist_ok=True)


# Constants and configurations
class Config:
    # Frasa yang perlu dihapus
    HAPUS_FRASA = [
        "mahkamah agung republik indonesia", "direktori putusan", "hkama",
        "salinan putusan", "putusan.mahkamahagung.go.id", "halaman",
        "email kepaniteraanmahkamahagunggoid", "telp", "fax", "website",
        "ahkamah agung", "mah agung republik indonesia", "blik indonesi"
    ]

    # Frasa hukum penting
    PEMISAH_PARAGRAF = [
        "menimbang bahwa", "membaca", "mengadili", "memutuskan",
        "terdakwa", "menyatakan", "menjatuhkan", "memperhatikan"
    ]

    # Regular expressions
    DISCLAIMER_PATTERN = r"disclaimer\s+kepaniteraan mahkamah agung republik indonesia.+?kami sajikan,? hal mana akan terus kami perbaiki dari waktu ke[ -]?waktu\."
    HAL_PATTERN = r"hal\s*\d+\s*dari\s*\d+\s*hal\s*putusan nomor.*"
    INAKURASI_PATTERN = r"dalam hal anda menemukan inakurasi informasi.+?(?=email|telp|website|$)"
    EMAIL_TELP_PATTERN = r"(email\s*:\s*[^\s\n]+)?\s*(telp\s*:\s*(ext\.?\d{1,5}|ext\.?|)?)"
    PHONE_PATTERN = r"[-\s]?\d{3,4}[-\s]?\d{3,4}\s*(ext\.?|extension)?\.?\s*\d{1,4}"
    EXT_PATTERN = r"\bext[.:]?\s*\d{1,5}\b"
    HALAMAN_PATTERN = r"halaman\s+\d+\s+dari\s+\d+\s+halaman.*"

class TextProcessor:
    def __init__(self):
        self.config = Config()
        self.stats = {
            'total_chars_removed': 0,
            'total_lines_removed': 0
        }

    def normalisasi_teks(self, teks: str) -> str:
        """
        Normalize and clean the text by removing unwanted patterns and standardizing format.
        
        Args:
            teks (str): Input text to be normalized
            
        Returns:
            str: Normalized text
        """
        original_length = len(teks)
        teks = teks.lower()

        # Hapus bagian seperti disclaimer menggunakan patterns dari Config
        patterns = [
            (self.config.DISCLAIMER_PATTERN, re.DOTALL | re.IGNORECASE),
            (self.config.HAL_PATTERN, re.IGNORECASE),
            (self.config.INAKURASI_PATTERN, re.DOTALL | re.IGNORECASE),
            (self.config.EMAIL_TELP_PATTERN, re.IGNORECASE),
            (self.config.PHONE_PATTERN, re.IGNORECASE),
            (self.config.EXT_PATTERN, re.IGNORECASE),
            (self.config.HALAMAN_PATTERN, 0)
        ]

        for pattern, flags in patterns:
            teks = re.sub(pattern, "", teks, flags=flags)

        # Remove unwanted punctuation
        exclude = ''.join(c for c in string.punctuation if c not in ['.', ',', '-', '/', ':'])
        teks = teks.translate(str.maketrans("", "", exclude))
        
        # Normalize whitespace
        teks = re.sub(r'[ \t]+', ' ', teks)
        teks = teks.strip()
        
        # Update statistics
        self.stats['total_chars_removed'] += original_length - len(teks)
        
        return teks

    def bersihkan_teks(self, teks: str) -> str:
        """
        Clean the text by removing unwanted lines and formatting paragraphs.
        
        Args:
            teks (str): Input text to be cleaned
            
        Returns:
            str: Cleaned text
        """
        hasil_bersih = []
        original_lines = len(teks.split('\n'))
        
        for line in teks.split('\n'):
            line_lower = line.lower().strip()
            
            # Skip empty lines or lines with just numbers
            if not line_lower or re.fullmatch(r"\s*\d+\s*", line):
                self.stats['total_lines_removed'] += 1
                continue
                
            # Check for unwanted phrases
            if (any(line_lower.startswith(frasa) for frasa in self.config.HAPUS_FRASA) 
                and len(line_lower.split()) <= 6):
                if not ("pidana" in line_lower or "menjatuhkan" in line_lower):
                    self.stats['total_lines_removed'] += 1
                    continue
                    
            # Format important legal phrases
            if any(re.search(rf"\b{p}\b", line_lower) for p in self.config.PEMISAH_PARAGRAF):
                hasil_bersih.append("\n" + line.strip())
            else:
                hasil_bersih.append(line.strip())
                
        teks_bersih = '\n'.join(hasil_bersih)
        return self.normalisasi_teks(teks_bersih)

    def get_stats(self) -> Dict[str, int]:
        """Get text processing statistics."""
        return self.stats.copy()

def process_pdf(args: tuple) -> Dict[str, any]:
    """
    Process a single PDF file.
    
    Args:
        args: Tuple containing (filename, idx, total_files, text_processor)
        
    Returns:
        Dict containing processing results and statistics
    """
    filename, idx, total_files, text_processor = args
    result = {
        'success': False,
        'filename': filename,
        'error': None,
        'stats': {}
    }
    
    try:
        file_path = os.path.join(input_folder, filename)
        doc = fitz.open(file_path)
        full_text = ""
        
        try:
            for page in doc:
                full_text += page.get_text("text")
        finally:
            doc.close()

        teks_bersih = text_processor.bersihkan_teks(full_text)
        
        output_filename = f"case_{idx:03}.txt"
        output_path = os.path.join(output_folder, output_filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"[case_id: {idx}]\n[filename: {filename}]\n\n{teks_bersih}")
            
        result['success'] = True
        result['stats'] = text_processor.get_stats()
        
    except fitz.FileDataError:
        result['error'] = "Invalid PDF file"
    except Exception as e:
        result['error'] = str(e)
        
    return result

def main():
    """Main function to process PDF files."""
    # Main processing logic starts here - logging is already setup at module level

    try:
        # Get list of PDF files
        pdf_files = sorted([f for f in os.listdir(input_folder) if f.endswith(".pdf")])
        total_files = len(pdf_files)
        
        if not pdf_files:
            logging.warning("No PDF files found in the input folder")
            print("No PDF files found in the input folder")
            return

        # Initialize text processor
        text_processor = TextProcessor()
        
        # Prepare arguments for parallel processing
        process_args = [
            (filename, idx, total_files, text_processor)
            for idx, filename in enumerate(pdf_files, start=1)
        ]

        # Process files with progress bar
        with tqdm(total=total_files, desc="Processing PDFs") as pbar:
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = [executor.submit(process_pdf, arg) for arg in process_args]
                
                for future in as_completed(futures):
                    result = future.result()
                    filename = result['filename']
                    
                    if result['success']:
                        msg = f"✔️ Success"
                        logging.info(f"Successfully processed {filename}")
                    else:
                        msg = f"❌ Error: {result['error']}"
                        logging.error(f"Failed to process {filename}: {result['error']}")
                    
                    print(f"[{filename}] → {msg}")
                    pbar.update(1)

        # Print final statistics
        print("\nProcessing Statistics:")
        print(f"Total files processed: {total_files}")
        print(f"Characters removed: {text_processor.stats['total_chars_removed']}")
        print(f"Lines removed: {text_processor.stats['total_lines_removed']}")

    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        print(f"Fatal error: {str(e)}")
        return

if __name__ == "__main__":
    start_time = time.time()
    main()
    elapsed_time = time.time() - start_time
    print(f"\nTotal execution time: {elapsed_time:.2f} seconds")
