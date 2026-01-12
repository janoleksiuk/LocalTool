import argparse
import shutil
import subprocess
from pathlib import Path

QUALITY_MAP = {
    "screen": "/screen",     # smallest, lowest quality
    "ebook": "/ebook",       # good balance
    "printer": "/printer",   # higher quality
    "prepress": "/prepress", # highest quality, largest
    "default": "/default",
}

def find_gs(explicit: str | None = None) -> str:
    if explicit:
        p = Path(explicit)
        if p.exists():
            return str(p)
        raise FileNotFoundError(f"Ghostscript not found at: {explicit}")

    # Windows CLI exe names (per Ghostscript docs): gswin64c/gswin32c :contentReference[oaicite:3]{index=3}
    for name in ("gswin64c", "gswin32c", "gs"):
        p = shutil.which(name)
        if p:
            return p

    raise FileNotFoundError(
        "Ghostscript not found. Install it and/or add its bin folder to PATH "
        "(so gswin64c.exe is discoverable)."
    )

def compress_pdf(
    input_pdf: Path,
    output_pdf: Path,
    preset: str = "ebook",
    dpi: int | None = None,
    gs_path: str | None = None,
) -> None:
    gs = find_gs(gs_path)
    preset_gs = QUALITY_MAP.get(preset.lower())
    if not preset_gs:
        raise ValueError(f"Unknown preset '{preset}'. Choose: {', '.join(QUALITY_MAP)}")

    cmd = [
        gs,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={preset_gs}",
        "-dNOPAUSE",
        "-dBATCH",
        "-dQUIET",
        "-dDetectDuplicateImages=true",
        "-dCompressFonts=true",
        "-dSubsetFonts=true",
        f"-sOutputFile={str(output_pdf)}",
        str(input_pdf),
    ]

    # Optional: force image downsampling (big impact for scanned PDFs)
    if dpi is not None:
        dpi = int(dpi)
        # Insert before output/input so it’s treated as params
        insert_at = len(cmd) - 2
        extra = [
            "-dDownsampleColorImages=true",
            f"-dColorImageResolution={dpi}",
            "-dDownsampleGrayImages=true",
            f"-dGrayImageResolution={dpi}",
            "-dDownsampleMonoImages=true",
            f"-dMonoImageResolution={dpi}",
        ]
        cmd[insert_at:insert_at] = extra

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "Ghostscript failed.\n"
            f"STDERR:\n{result.stderr.strip()}\n\nSTDOUT:\n{result.stdout.strip()}"
        )

def main():
    ap = argparse.ArgumentParser(description="Compress PDF using Ghostscript (Windows).")
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--preset", choices=sorted(QUALITY_MAP.keys()), default="ebook")
    ap.add_argument("--dpi", type=int, default=None, help="Downsample images to this DPI (e.g., 150)")
    ap.add_argument("--gs", type=str, default=None, help="Full path to gswin64c.exe (if not on PATH)")
    args = ap.parse_args()

    inp = args.input.resolve()
    out = args.output.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    if not inp.exists() or inp.suffix.lower() != ".pdf":
        raise SystemExit(f"Input must be an existing PDF: {inp}")

    compress_pdf(inp, out, preset=args.preset, dpi=args.dpi, gs_path=args.gs)

    before = inp.stat().st_size
    after = out.stat().st_size
    print(f"Saved: {out}")
    print(f"Size: {before/1e6:.2f} MB -> {after/1e6:.2f} MB ({after/before*100:.1f}%)")

if __name__ == "__main__":
    main()
