#!/usr/bin/env python3
"""
Convert sample PNG floorplan images to PDF format.

Usage:
    python scripts/convert_images_to_pdf.py

This script converts all PNG images in sample_images/ to PDF format
and saves them to sample_pdfs/. Original PNGs are preserved.
"""

import os
from pathlib import Path
from PIL import Image


def convert_images_to_pdf():
    """Convert all PNG images in sample_images/ to PDF in sample_pdfs/."""
    
    # Define paths
    project_root = Path(__file__).parent.parent
    images_dir = project_root / "sample_images"
    pdfs_dir = project_root / "sample_pdfs"
    
    # Ensure sample_pdfs directory exists
    pdfs_dir.mkdir(exist_ok=True)
    
    # Find all PNG files
    png_files = sorted(images_dir.glob("*.png"))
    
    if not png_files:
        print("No PNG files found in sample_images/")
        return
    
    print(f"Found {len(png_files)} PNG images to convert...")
    print(f"Source: {images_dir}")
    print(f"Destination: {pdfs_dir}")
    print()
    
    converted = 0
    failed = 0
    
    for png_path in png_files:
        # Generate PDF filename (same name, different extension)
        pdf_name = png_path.stem + ".pdf"
        pdf_path = pdfs_dir / pdf_name
        
        try:
            # Open image and convert to RGB (PDF doesn't support RGBA)
            with Image.open(png_path) as img:
                if img.mode == 'RGBA':
                    # Create white background for transparency
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save as PDF
                img.save(pdf_path, "PDF", resolution=100.0)
            
            print(f"  ✓ {png_path.name} -> {pdf_name}")
            converted += 1
            
        except Exception as e:
            print(f"  ✗ {png_path.name} -> FAILED: {e}")
            failed += 1
    
    print()
    print(f"Conversion complete: {converted} converted, {failed} failed")
    
    # List all PDFs in sample_pdfs/
    existing_pdfs = sorted(pdfs_dir.glob("*.pdf"))
    print(f"\nTotal PDFs in sample_pdfs/: {len(existing_pdfs)}")


if __name__ == "__main__":
    convert_images_to_pdf()
