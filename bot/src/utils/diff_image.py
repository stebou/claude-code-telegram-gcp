"""
Diff image generator for Telegram bot.
Generates PNG images with red/green diff highlighting like Claude Code Desktop.
"""
import difflib
import io
from typing import Tuple
from PIL import Image, ImageDraw, ImageFont


# Color scheme (similar to GitHub/Claude Code)
BG_COLOR = "#0d1117"  # Dark background
LINE_NUM_COLOR = "#6e7681"  # Gray line numbers
TEXT_COLOR = "#c9d1d9"  # Light gray text
ADDED_BG = "#1a3d1a"  # Green background for added lines
ADDED_TEXT = "#7ee787"  # Bright green text
REMOVED_BG = "#3d1a1a"  # Red background for removed lines
REMOVED_TEXT = "#f8514958"  # Bright red text
UNCHANGED_BG = "#0d1117"  # Same as background

# Layout constants
FONT_SIZE = 13
LINE_HEIGHT = 18
PADDING = 10
LINE_NUM_WIDTH = 50
MAX_WIDTH = 800
MAX_LINES = 100  # Limit for performance


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def generate_diff_image(
    old_content: str,
    new_content: str,
    filename: str = "file"
) -> bytes:
    """
    Generate PNG image showing diff between old and new content.

    Args:
        old_content: Original file content
        new_content: Modified file content
        filename: Filename for header

    Returns:
        PNG image as bytes
    """
    # Generate unified diff
    diff_lines = list(difflib.unified_diff(
        old_content.splitlines(keepends=False),
        new_content.splitlines(keepends=False),
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm=''
    ))

    if not diff_lines:
        # No changes - create simple "No changes" image
        return _create_no_changes_image()

    # Limit lines for performance
    if len(diff_lines) > MAX_LINES:
        diff_lines = diff_lines[:MAX_LINES]
        diff_lines.append(f"... ({len(diff_lines) - MAX_LINES} more lines truncated)")

    # Calculate image dimensions
    num_lines = len(diff_lines)
    img_width = MAX_WIDTH
    img_height = PADDING * 2 + (num_lines * LINE_HEIGHT)

    # Create image
    img = Image.new('RGB', (img_width, img_height), hex_to_rgb(BG_COLOR))
    draw = ImageDraw.Draw(img)

    # Try to load monospace font, fallback to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", FONT_SIZE)
    except:
        try:
            font = ImageFont.truetype("DejaVuSansMono.ttf", FONT_SIZE)
        except:
            font = ImageFont.load_default()

    # Draw diff lines
    y_offset = PADDING
    for i, line in enumerate(diff_lines):
        line_type = _get_line_type(line)

        # Draw line background
        bg_color = _get_bg_color(line_type)
        if bg_color != BG_COLOR:
            draw.rectangle(
                [(0, y_offset), (img_width, y_offset + LINE_HEIGHT)],
                fill=hex_to_rgb(bg_color)
            )

        # Draw line number
        line_num = f"{i+1:4d}"
        draw.text(
            (PADDING, y_offset),
            line_num,
            font=font,
            fill=hex_to_rgb(LINE_NUM_COLOR)
        )

        # Draw line content
        text_color = _get_text_color(line_type)
        display_text = line if len(line) < 100 else line[:97] + "..."

        draw.text(
            (PADDING + LINE_NUM_WIDTH, y_offset),
            display_text,
            font=font,
            fill=hex_to_rgb(text_color)
        )

        y_offset += LINE_HEIGHT

    # Convert to bytes
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def _get_line_type(line: str) -> str:
    """Determine line type from diff line."""
    if line.startswith('+++') or line.startswith('---'):
        return 'header'
    elif line.startswith('@@'):
        return 'hunk'
    elif line.startswith('+'):
        return 'added'
    elif line.startswith('-'):
        return 'removed'
    else:
        return 'unchanged'


def _get_bg_color(line_type: str) -> str:
    """Get background color for line type."""
    colors = {
        'added': ADDED_BG,
        'removed': REMOVED_BG,
        'header': BG_COLOR,
        'hunk': BG_COLOR,
        'unchanged': UNCHANGED_BG,
    }
    return colors.get(line_type, UNCHANGED_BG)


def _get_text_color(line_type: str) -> str:
    """Get text color for line type."""
    colors = {
        'added': ADDED_TEXT,
        'removed': REMOVED_TEXT,
        'header': LINE_NUM_COLOR,
        'hunk': LINE_NUM_COLOR,
        'unchanged': TEXT_COLOR,
    }
    return colors.get(line_type, TEXT_COLOR)


def _create_no_changes_image() -> bytes:
    """Create simple image indicating no changes."""
    img_width = 400
    img_height = 100

    img = Image.new('RGB', (img_width, img_height), hex_to_rgb(BG_COLOR))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 16)
    except:
        font = ImageFont.load_default()

    text = "✓ No changes detected"
    draw.text(
        (img_width // 2 - 100, img_height // 2 - 10),
        text,
        font=font,
        fill=hex_to_rgb(ADDED_TEXT)
    )

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()
