import os
import tempfile
from pathlib import Path


def save_document(document, output: Path, *, force: bool = False):
    """Publish only a complete file; never clobber an output without --force."""
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{output.name}.", suffix=output.suffix, dir=output.parent)
    os.close(descriptor)
    temporary = Path(temporary)
    try:
        document.save(temporary)
        if force:
            os.replace(temporary, output)
        else:
            # Atomic create-if-absent, including protection against a concurrent writer.
            os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
