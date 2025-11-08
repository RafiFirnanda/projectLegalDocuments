import os
import re
import pandas as pd
from pathlib import Path
from datetime import datetime

# Setup paths
current_dir = Path(__file__).parent.absolute()
input_folder = current_dir / "data" / "raw"
output_folder = current_dir / "data" / "processed"
output_file = output_folder / "putusan_summary.xlsx"

# Create output folder
os.makedirs(output_folder, exist_ok=True)

class DocumentParser:
    def __init__(self):
        self.patterns = {
            'nomor_putusan': [
                # Pattern untuk mencari nomor putusan sampai PN YYK
                r'Nomor\s*:?\s*(\d+[-/]?[A-Za-z0-9./]+/[^/\n]*?(?:PN\.?)?\.?YYK)',
                r'Putusan\s+No[.:]?\s*(\d+[-/]?[A-Za-z0-9./]+/[^/\n]*?(?:PN\.?)?\.?YYK)',
                r'No[.:]?\s*(\d+[-/]?[A-Za-z0-9./]+/[^/\n]*?(?:PN\.?)?\.?YYK)'
            ],
            'barang_bukti': [
                # Prioritize explicit 'Barang bukti berupa:' phrasing (multiline)
                r'Barang\s*bukti\s*berupa[:\s]*(.*?)(?=MENGINGAT|MENGADILI|MEMUTUSKAN|MENETAPKAN|MENYATAKAN|Membebankan|$)',
                r'menetapkan\s+barang\s+bukti\s+berupa[:\s]*(.*?)(?=MENGINGAT|MENGADILI|MEMUTUSKAN|MENETAPKAN|MENYATAKAN|Membebankan|$)',
                r'terbukti[:\s]*(.*?)(?=MENGINGAT|MENGADILI|MEMUTUSKAN|MENETAPKAN|MENYATAKAN|$)',
                r'telah\s+ditemukan\s*(.*?)(?=MENGINGAT|MENGADILI|MEMUTUSKAN|MENETAPKAN|MENYATAKAN|$)',
                r'ditemukan\s*(.*?)(?=MENGINGAT|MENGADILI|MEMUTUSKAN|MENETAPKAN|MENYATAKAN|$)'
            ],
            'amar_putusan': [
                r'Menyatakan\s+[Tt]erdakwa\s*(.*?)(?=KEDUA|KETIGA|KEEMPAT|KELIMA|MENETAPKAN|MEMBEBANKAN|$)',
                r'MENYATAKAN\s+[Tt]erdakwa\s*(.*?)(?=KEDUA|KETIGA|KEEMPAT|KELIMA|MENETAPKAN|MEMBEBANKAN|$)'
            ]
        }
    
    def extract_nomor_putusan(self, text: str) -> str:
        """Extract nomor putusan from text."""
        for pattern in self.patterns['nomor_putusan']:
            if match := re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                return match.group(1).strip()
        return "Tidak ditemukan"
    
    def extract_lembaga_peradilan(self, text: str) -> str:
        """Return PN Yogyakarta for all cases."""
        return "PN YOGYAKARTA"
    
    def extract_barang_bukti(self, text: str) -> str:
        """Extract barang bukti from text based on 'terbukti' or 'ditemukan'."""
        # Try to capture in the original multi-line text first (DOTALL)
        for pattern in self.patterns['barang_bukti']:
            if match := re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                bukti = match.group(1).strip()

                # Normalize list bullets and newlines into semicolon-separated items
                bukti = re.sub(r"\n\s*[-•]\s*", "; ", bukti)
                bukti = re.sub(r"\n\s*\d+\s*[)\.]\s*", "; ", bukti)

                # Remove page markers and putusan markers inside the captured block
                bukti = self._remove_page_and_putusan_markers(bukti)

                # Clean unwanted symbols and unnecessary punctuation
                bukti = self._clean_bukti_text(bukti)

                # Trim and limit length for Excel readability
                bukti = bukti.strip()
                if len(bukti) > 1500:
                    bukti = bukti[:1500].rsplit(' ', 1)[0] + '...'
                return bukti

        return "Tidak ditemukan"

    def _clean_bukti_text(self, bukti: str) -> str:
        """Clean unwanted bullets and unnecessary punctuation from barang bukti text.

        - Remove non-standard bullet characters and list markers
        - Remove prefixes like "-", "a.", "1." at the start of items
        - Collapse sequences like ':;' to ';'
        - Normalize repeated numeric-word forms like '12 dua belas' -> '12'
        - Ensure consistent spacing after semicolons
        """
        # Remove common bullet/control characters and non-printable ranges
        bukti = re.sub(r"[\u2000-\u206F\u2E00-\u2E7F\u3000-\u303F\u25A0-\u25FF\u2600-\u26FF]+", " ", bukti)

        # Remove list markers at the start of items (after semicolons or at start)
        bukti = re.sub(r"(?:^|;\s*)[-a-z0-9]+[.)]?\s+", "", bukti, flags=re.IGNORECASE)
        bukti = re.sub(r"(?:^|;\s*)[-•]\s*", "", bukti)

        # Remove any characters except basic punctuation we want to keep
        bukti = re.sub(r"[^0-9A-Za-zÀ-ÖØ-öø-ÿ\s,.;:()%\-/]", " ", bukti)

        # Remove sequences of colon+semicolon or mixed punctuation
        bukti = re.sub(r"[:;]{2,}", ";", bukti)
        bukti = re.sub(r"[:;]\s*[:;]+", ";", bukti)

        # Collapse multiple semicolons or commas
        bukti = re.sub(r";{2,}", ";", bukti)
        bukti = re.sub(r",{2,}", ",", bukti)

        # Replace patterns like '1 satu' or '12 dua belas' -> keep numeric form
        num_words = r"satu|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh|sebelas|dua belas|tiga belas|empat belas|lima belas"
        bukti = re.sub(rf"\b(\d+)\s+(?:{num_words})\b", r"\1", bukti, flags=re.IGNORECASE)

        # Remove phrases like 'dirampas untuk dimusnahkan' or variants (remove trailing clause)
        bukti = re.sub(r"dirampas\s*(?:untuk\s*(?:di\s*)?dimusnahkan)\b[\s\S]*$", "", bukti, flags=re.IGNORECASE)
        bukti = re.sub(r"dirampas\s*(?:untuk\s*(?:di\s*)?dimusnahkan)\b", "", bukti, flags=re.IGNORECASE)

        # Remove standalone 'yyk' or 'pn yyk' that may remain
        bukti = re.sub(r"\b(?:pn\s*)?yyk\b[\.:,;\-]*", "", bukti, flags=re.IGNORECASE)

        # Remove stray spaces before punctuation and ensure single space after semicolon
        bukti = re.sub(r"\s+([,.;:])", r"\1", bukti)
        bukti = re.sub(r";\s*", "; ", bukti)

        # Collapse multiple spaces
        bukti = re.sub(r"\s+", " ", bukti).strip()

        # Remove leading/trailing punctuation
        bukti = re.sub(r"^[,.;:]+", "", bukti)
        bukti = re.sub(r"[,.;:]+$", "", bukti)

        return bukti

    def _remove_page_and_putusan_markers(self, text: str) -> str:
        """Remove page headers like 'hal 2 dari 17 hal' and 'Putusan Nomor ...' markers and remove 'yyk'."""
        # Remove page markers: 'hal 2 dari 17 hal' or 'hal 2 dari 17' including trailing 'yyk' tokens
        text = re.sub(r"\bhal\b\s*\d+\s*(?:dari|/)\s*\d+\s*(?:hal)?(?:\s*yyk)?\b[\.:,;\-]*", " ", text, flags=re.IGNORECASE)

        # Remove patterns like 'Putusan Nomor 185/Pid.Sus/2023/PN YYK' (case-insensitive)
        text = re.sub(r"\bputusan\s+nomor\s+[A-Za-z0-9\./-]+(?:\s*/?\s*pn\s*yyk)?\b[\.:,;\-]*", " ", text, flags=re.IGNORECASE)

        # Remove standalone 'yyk' or 'pn yyk' tokens
        text = re.sub(r"\b(?:pn\s*)?yyk\b[\.:,;\-]*", " ", text, flags=re.IGNORECASE)

        # Remove any leftover 'case_xxx' markers
        text = re.sub(r"case_\d{1,4}", " ", text, flags=re.IGNORECASE)

        # Collapse whitespace after removals
        text = re.sub(r"\s+", " ", text).strip()
        return text
    
    def extract_amar_putusan(self, text: str) -> str:
        """Extract amar putusan starting from 'Menyatakan terdakwa'."""
        # Prefer to find the full decision block starting at 'Menyatakan Terdakwa'
        text_norm = text.replace('\r', '')
        start_match = re.search(r'(Menyatakan\s+[Tt]erdakwa)', text_norm, re.IGNORECASE)
        if start_match:
            start = start_match.start()
            # Heuristic: capture a generous block after the start (up to 4000 chars)
            end = min(len(text_norm), start + 4000)
            amar_block = text_norm[start:end]

            # If there's a clear next-section marker after start, use it as end
            next_marker = re.search(r'\n\s{0,5}[A-Z]{3,}\b', text_norm[start+50:start+4000])
            if next_marker:
                end_rel = next_marker.start() + start + 50
                amar_block = text_norm[start:end_rel]

            # Remove page and putusan markers inside the captured block
            amar_block = self._remove_page_and_putusan_markers(amar_block)

            # Normalize bullets and whitespace similar to barang bukti
            amar_block = re.sub(r"\n\s*[-•]\s*", "; ", amar_block)
            amar_block = re.sub(r"\s+", " ", amar_block).strip()

            # Clean residual unwanted characters
            amar_block = re.sub(r"[^\x00-\x7F]+", " ", amar_block)

            # Limit length but keep meaningful content
            if len(amar_block) > 3000:
                amar_block = amar_block[:3000].rsplit(' ', 1)[0] + '...'
            return amar_block

        # Fallback: try regex patterns (shorter capture)
        text_flat = re.sub(r'\n+', ' ', text)
        for pattern in self.patterns['amar_putusan']:
            if match := re.search(pattern, text_flat, re.IGNORECASE | re.DOTALL):
                amar = match.group(0).strip()
                amar = re.sub(r'\s+', ' ', amar)
                return amar

        return "Tidak ditemukan"

def main():
    # Initialize parser
    parser = DocumentParser()
    data_list = []
    
    # Process all text files
    print("\nProcessing text files...")
    files = sorted([f for f in os.listdir(input_folder) if f.endswith('.txt')])
    
    for idx, file in enumerate(files, 1):
        try:
            path = os.path.join(input_folder, file)
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
                
            # Extract information
            data_list.append({
                "no": idx,
                "nomor_putusan": parser.extract_nomor_putusan(text),
                "lembaga_peradilan": parser.extract_lembaga_peradilan(text),
                "barang_bukti": parser.extract_barang_bukti(text),
                "amar_putusan": parser.extract_amar_putusan(text)
            })
            
            print(f"✔️ Processed {file}")
            
        except Exception as e:
            print(f"❌ Error processing {file}: {str(e)}")
            continue
    
    if not data_list:
        print("No documents were processed successfully!")
        return
        
    # Create DataFrame
    df = pd.DataFrame(data_list)
    
    # Save to Excel (handle if file is open / permission denied)
    try:
        df.to_excel(output_file, index=False, sheet_name='Putusan')
        print(f"\nSaved {len(data_list)} documents to {output_file}")
    except PermissionError:
        # Try a timestamped fallback filename
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        fallback = output_file.with_name(f"putusan_summary_{ts}.xlsx")
        try:
            df.to_excel(fallback, index=False, sheet_name='Putusan')
            print(f"\nSaved {len(data_list)} documents to {fallback} (fallback due to permission)")
        except Exception as e:
            print(f"Failed to save Excel file: {e}")
    print("\nColumns in the Excel file:")
    print("1. No: Nomor urut dokumen")
    print("2. Nomor Putusan: Nomor putusan pengadilan sampai PN YYK")
    print("3. Lembaga Peradilan: PN YOGYAKARTA")
    print("4. Barang Bukti: Daftar barang yang terbukti atau ditemukan")
    print("5. Amar Putusan: Putusan yang dimulai dari 'Menyatakan terdakwa'")

if __name__ == "__main__":
    main()