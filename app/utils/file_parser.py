"""
File parsing utilities for various document formats
"""
from typing import Optional
import io
from pathlib import Path
from pypdf import PdfReader
from docx import Document
from app.utils.logger import get_logger

logger = get_logger(__name__)


def parse_pdf(file_content: bytes) -> str:
    """
    Extract text from PDF file

    Args:
        file_content: PDF file bytes

    Returns:
        str: Extracted text
    """
    try:
        pdf_file = io.BytesIO(file_content)
        reader = PdfReader(pdf_file)

        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)

        full_text = "\n\n".join(text_parts)
        logger.info(f"Successfully parsed PDF, extracted {len(full_text)} characters")

        return full_text

    except Exception as e:
        logger.error(f"Error parsing PDF: {e}")
        raise ValueError(f"Failed to parse PDF file: {str(e)}")


def parse_docx(file_content: bytes) -> str:
    """
    Extract text from DOCX file

    Args:
        file_content: DOCX file bytes

    Returns:
        str: Extracted text
    """
    try:
        docx_file = io.BytesIO(file_content)
        doc = Document(docx_file)

        text_parts = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)

        full_text = "\n\n".join(text_parts)
        logger.info(f"Successfully parsed DOCX, extracted {len(full_text)} characters")

        return full_text

    except Exception as e:
        logger.error(f"Error parsing DOCX: {e}")
        raise ValueError(f"Failed to parse DOCX file: {str(e)}")


def parse_txt(file_content: bytes) -> str:
    """
    Extract text from TXT file

    Args:
        file_content: TXT file bytes

    Returns:
        str: File content
    """
    try:
        text = file_content.decode('utf-8')
        logger.info(f"Successfully parsed TXT, extracted {len(text)} characters")
        return text

    except UnicodeDecodeError:
        # Try with different encoding
        try:
            text = file_content.decode('latin-1')
            logger.info(f"Successfully parsed TXT with latin-1 encoding")
            return text
        except Exception as e:
            logger.error(f"Error parsing TXT: {e}")
            raise ValueError(f"Failed to parse TXT file: {str(e)}")


def parse_file(file_content: bytes, filename: str) -> str:
    """
    Parse file based on extension

    Args:
        file_content: File bytes
        filename: Name of the file

    Returns:
        str: Extracted text

    Raises:
        ValueError: If file type is unsupported
    """
    extension = Path(filename).suffix.lower()

    if extension == '.pdf':
        return parse_pdf(file_content)
    elif extension == '.docx':
        return parse_docx(file_content)
    elif extension == '.txt':
        return parse_txt(file_content)
    else:
        raise ValueError(f"Unsupported file type: {extension}")
