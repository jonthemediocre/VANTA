import os
from typing import Dict, List
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageSequenceClip
import datetime

# Attempt to find a usable font path - this may need user configuration
DEFAULT_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", # Linux
    "/Library/Fonts/Arial Unicode.ttf",             # macOS
    "C:/Windows/Fonts/arialuni.ttf",                # Windows (common Unicode font)
    "C:/Windows/Fonts/seguisym.ttf"                 # Windows (Segoe UI Symbol)
]

GLYPH_FONT_PATH = None
for path in DEFAULT_FONT_PATHS:
    if os.path.exists(path):
        GLYPH_FONT_PATH = path
        break

if not GLYPH_FONT_PATH:
    print("WARNING: Could not find a default TrueType font with good Unicode support. Glyphs may render incorrectly. Install DejaVuSans or specify GLYPH_FONT_PATH.")
    # Fallback to Pillow's default, which has poor glyph support

OUTPUT_DIR = Path("vanta_output/swarm_glyph_visuals")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

class SwarmGlyphVisualGenerator:
    GLYPH_SIZE = 64 # Reduced size for better fitting
    GLYPH_SPACING = 20
    ROW_SPACING = 100
    AGENT_LABEL_SIZE = 24
    PADDING = 40
    BG_COLOR = (10, 10, 10)
    ACTIVE_FG_COLOR = (220, 220, 220)
    INACTIVE_FG_COLOR = (60, 60, 60)
    AGENT_COLOR = (120, 120, 255)

    @classmethod
    def generate(cls, swarm_chains: Dict[str, List[str]], fps: int = 1) -> tuple[Path | None, Path | None]:
        """Generate swarm ritual visualizations (PNG snapshot and MP4 animation).

        Args:
            swarm_chains: Dictionary mapping agent names to their glyph chains.
            fps: Frames per second for the animation.

        Returns:
            A tuple containing the path to the generated PNG and MP4 files, or None if generation failed.
        """
        if not swarm_chains:
            print("ERROR: No swarm chains provided.")
            return None, None

        # Determine max glyph chain length
        max_len = 0
        if swarm_chains.values():
            max_len = max(len(chain) for chain in swarm_chains.values() if chain) # Handle empty chains

        if max_len == 0:
            print("WARNING: All swarm chains are empty. Cannot generate visualization.")
            return None, None # Or generate an empty state image?

        frames = []
        for step in range(max_len + 1): # Include final state
            try:
                img = cls._render_frame(swarm_chains, step)
                frames.append(img)
            except Exception as e:
                print(f"ERROR: Failed to render frame {step}: {e}")
                return None, None

        # Export PNG snapshot (final frame)
        png_path = None
        if frames:
            try:
                png_path = cls._export_png(frames[-1])
            except Exception as e:
                print(f"ERROR: Failed to export PNG: {e}")

        # Export MP4 animation
        mp4_path = None
        if frames:
            try:
                mp4_path = cls._export_mp4(frames, fps=fps)
            except Exception as e:
                print(f"ERROR: Failed to export MP4: {e}")

        return png_path, mp4_path

    @classmethod
    def _get_font(cls, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Attempts to load the preferred font, falling back to default."""
        if GLYPH_FONT_PATH:
            try:
                return ImageFont.truetype(GLYPH_FONT_PATH, size)
            except IOError:
                print(f"WARNING: Failed to load specified font {GLYPH_FONT_PATH}. Falling back to default.")
        return ImageFont.load_default()

    @classmethod
    def _render_frame(cls, swarm_chains: Dict[str, List[str]], step: int) -> Image.Image:
        """Render a single frame of the swarm ritual visualization."""
        num_agents = len(swarm_chains)
        max_len = 0
        if swarm_chains.values():
             max_len = max(len(chain) for chain in swarm_chains.values() if chain)

        # Calculate image dimensions dynamically
        agent_font = cls._get_font(cls.AGENT_LABEL_SIZE)
        glyph_font = cls._get_font(cls.GLYPH_SIZE)

        # Estimate max label width (conservative)
        max_label_width = max(agent_font.getlength(f"{agent}: ") for agent in swarm_chains.keys()) if swarm_chains else 100
        content_width = max_len * (cls.GLYPH_SIZE + cls.GLYPH_SPACING)
        width = int(max_label_width + content_width + 2 * cls.PADDING)
        height = cls.ROW_SPACING * num_agents + 2 * cls.PADDING

        img = Image.new("RGB", (width, height), cls.BG_COLOR)
        draw = ImageDraw.Draw(img)

        current_y = cls.PADDING
        for agent, chain in swarm_chains.items():
            agent_label = f"{agent}: "
            # Draw agent label
            draw.text((cls.PADDING, current_y + (cls.ROW_SPACING - cls.AGENT_LABEL_SIZE) // 2),
                      agent_label, fill=cls.AGENT_COLOR, font=agent_font)

            current_x = max_label_width + cls.PADDING
            for g_idx, glyph in enumerate(chain):
                # Determine color based on the current step
                color = cls.ACTIVE_FG_COLOR if g_idx < step else cls.INACTIVE_FG_COLOR
                # Draw glyph
                draw.text((current_x, current_y + (cls.ROW_SPACING - cls.GLYPH_SIZE) // 2),
                          glyph, fill=color, font=glyph_font, anchor="lm") # Anchor left-middle
                current_x += cls.GLYPH_SIZE + cls.GLYPH_SPACING

            current_y += cls.ROW_SPACING

        return img

    @classmethod
    def _export_png(cls, img: Image.Image) -> Path:
        """Export static PNG snapshot."""
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = OUTPUT_DIR / f"swarm_snapshot_{timestamp}.png"
        img.save(filename)
        print(f"[SwarmGlyphVisualGenerator] Saved PNG snapshot: {filename}")
        return filename

    @classmethod
    def _export_mp4(cls, frames: List[Image.Image], fps: int = 1) -> Path:
        """Export animated MP4 ritual playback."""
        if not frames:
            raise ValueError("Cannot export MP4 with no frames.")

        # Ensure moviepy is available
        try:
            from moviepy.editor import ImageSequenceClip
        except ImportError:
            print("ERROR: moviepy library not found. Cannot export MP4. Install it: pip install moviepy")
            raise

        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = OUTPUT_DIR / f"swarm_ritual_{timestamp}.mp4"

        # Convert Pillow images to NumPy arrays for moviepy
        img_arrays = [list(img.convert("RGB").getdata()) for img in frames]
        frame_size = frames[0].size
        
        # Create the clip
        clip = ImageSequenceClip([Image.frombytes("RGB", frame_size, bytes(bytearray(p for pix in data for p in pix))) for data in img_arrays], fps=fps)
        
        # Write the video file
        # Use a high quality preset, adjust threads/logger as needed
        clip.write_videofile(str(filename), codec="libx264", preset='slow', ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None, threads=4)
        clip.close()
        print(f"[SwarmGlyphVisualGenerator] Saved ritual animation: {filename}")
        return filename

# Example usage
if __name__ == "__main__":
    print(f"Checking font path: {GLYPH_FONT_PATH}")
    swarm_chains_example = {
        "Agent_A": ["🧭", "🌀", "🔥", "🕳️"],
        "Agent_B": ["👁️", "🧭", "⚡", "🕳️"],
        "Agent_C": ["🧠", "🌀", "🔥", "⭕", "🕳️"],
        "Agent_D_Short": ["💾", "✅"],
    }
    try:
        png_file, mp4_file = SwarmGlyphVisualGenerator.generate(swarm_chains_example)
        if png_file:
            print(f"PNG generated: {png_file}")
        if mp4_file:
            print(f"MP4 generated: {mp4_file}")
    except Exception as e:
        print(f"An error occurred during generation: {e}") 