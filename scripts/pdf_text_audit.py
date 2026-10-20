"""Conservative local PDF text gate; this does not inspect raster text or layout.

Exit 0: extractable text passes the implemented checks; 1: definite findings;
2: local text audit is incomplete (missing extractor, unreadable/empty text).
Python is required. Auto uses pypdf, then an installed pdftotext executable.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path


RULES = (
    ("UNRESOLVED_REFERENCE", re.compile(
        r"(?<![A-Za-z])(?:fig(?:ure)?s?\.?|tables?|tab\.|equations?|eqs?\.?|"
        r"sections?|secs?\.?|appendix|appendices|references?|refs?\.?)"
        r"(?:(?:\s+(?:no\.?\s*)?|\s*[\[(]\s*)[?？]+|[?？]{2,})", re.I)),
    ("UNRESOLVED_REFERENCE", re.compile(
        r"(?:图|表|公式|式|章节|附录|参考文献)(?:\s+[?？]+|\s*[（(\[【]?\s*[?？]{2,})")),
    ("UNRESOLVED_CITATION", re.compile(r"\[\s*\?+\s*\]")),
    ("WORD_REFERENCE_ERROR", re.compile(
        r"Error\s*!\s*(?:Reference source not found|Bookmark not defined|"
        r"Hyperlink reference not valid)\.?|错误\s*[!！]\s*(?:未找到引用源|未定义书签)", re.I)),
    ("DRAFT_PLACEHOLDER", re.compile(
        r"\[(?:TODO|TBD|FIXME|PLACEHOLDER|INSERT\b[^\]\n]{0,80})\]|"
        r"<(?:insert|placeholder)\b[^>\n]{0,80}>|"
        r"^\s*(?:TODO|FIXME)\s*[:：]|^\s*(?:TODO|TBD|FIXME)\s*$|"
        r"[\[【](?:待补充|待填(?:写)?|待完善|待插入|此处填写)[\]】]", re.I | re.M)),
)


def scan_text(text: str, page: int) -> list[dict]:
    findings = []
    for code, pattern in RULES:
        for match in pattern.finditer(text):
            excerpt = " ".join(text[max(0, match.start() - 30):match.end() + 60].split())
            findings.append({"code": code, "page": page, "detail": excerpt[:140]})
    return findings


def unreadable_reason(text: str) -> str | None:
    if not text.strip():
        return "no_extractable_text; image_only_or_blank_page_requires_review"
    if not any(char.isalpha() for char in text):
        return "no_extractable_letters; numeric_footer_or_symbols_do_not_establish_text_coverage"
    if "\ufffd" in text or re.search(r"\(cid:\d+\)", text) or any(
        unicodedata.category(char) in {"Cc", "Cs"} and char not in "\r\n\t\f" for char in text
    ):
        return "replacement_glyph_or_unmapped_character; extraction_requires_review"
    return None


def extract_pages(pdf: Path, extractor: str, pdftotext_path: str | None) -> tuple[list[str], str]:
    failures = []
    if extractor in {"auto", "pypdf"}:
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                from pypdf import PdfReader
                import pypdf
                reader = PdfReader(str(pdf))
                if reader.is_encrypted and reader.decrypt("") == 0:
                    raise ValueError("encrypted_pdf_password_required")
                pages = [page.extract_text() or "" for page in reader.pages]
            return pages, "pypdf " + pypdf.__version__
        except Exception as exc:
            failures.append("pypdf: " + type(exc).__name__ + ": " + str(exc)[:200])
    if extractor in {"auto", "pdftotext"}:
        executable = pdftotext_path or shutil.which("pdftotext")
        if not executable or not Path(executable).is_file():
            failures.append("pdftotext: extractor_unavailable")
        else:
            try:
                result = subprocess.run(
                    [str(executable), "-enc", "UTF-8", "-layout", str(pdf), "-"],
                    capture_output=True, timeout=30, check=True,
                )
                pages = result.stdout.decode("utf-8", errors="strict").split("\f")
                # A final form-feed is a terminator, not an additional blank page.
                if pages and not pages[-1].strip():
                    pages.pop()
                return pages, "pdftotext"
            except Exception as exc:
                failures.append("pdftotext: " + type(exc).__name__ + ": " + str(exc)[:200])
    raise RuntimeError("; ".join(failures))


def audit(pdf: Path, extractor: str = "auto", pdftotext_path: str | None = None,
          denylist_file: Path | None = None) -> dict:
    report = {"schema_version": "1.0.0", "status": "UNVERIFIED", "extractor": None,
              "scope": "extractable_text_only; raster_text_and_visual_layout_require_manual_review",
              "pages": 0, "characters": 0, "findings": [], "unverified": []}
    try:
        pdf = pdf.resolve(strict=True)
        pages, used = extract_pages(pdf, extractor, pdftotext_path)
        report.update(extractor=used, pages=len(pages), characters=sum(map(len, pages)))
        if not pages:
            report["unverified"].append({"page": None, "reason": "no_pages_extracted"})
        terms = []
        if denylist_file is not None:
            terms = [line.strip() for line in denylist_file.read_text(encoding="utf-8-sig").splitlines()
                     if line.strip() and not line.strip().startswith("#")]
        for number, text in enumerate(pages, start=1):
            reason = unreadable_reason(text)
            if reason:
                report["unverified"].append({"page": number, "reason": reason})
            report["findings"].extend(scan_text(text, number))
            for term in terms:
                if term.casefold() in text.casefold():
                    report["findings"].append({"code": "ANONYMITY_DENYLIST", "page": number,
                                               "detail": "term=" + term})
        for term in terms:
            if term.casefold() in pdf.name.casefold():
                report["findings"].append({"code": "ANONYMITY_DENYLIST", "page": None,
                                           "detail": "filename_term=" + term})
        report["status"] = "FAIL" if report["findings"] else "UNVERIFIED" if report["unverified"] else "PASS"
    except Exception as exc:
        report["unverified"].append({"page": None, "reason": type(exc).__name__ + ": " + str(exc)[:400]})
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--extractor", choices=("auto", "pypdf", "pdftotext"), default="auto")
    parser.add_argument("--pdftotext-path")
    parser.add_argument("--denylist-file", type=Path)
    args = parser.parse_args()
    report = audit(args.pdf, args.extractor, args.pdftotext_path, args.denylist_file)
    print(json.dumps(report, ensure_ascii=True))
    return {"PASS": 0, "FAIL": 1, "UNVERIFIED": 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
