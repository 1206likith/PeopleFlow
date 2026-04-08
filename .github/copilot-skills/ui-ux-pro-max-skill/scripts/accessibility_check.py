#!/usr/bin/env python3
"""
Accessibility & Contrast Checker

Usage:
    python3 accessibility_check.py design-system/MASTER.md
    python3 accessibility_check.py --colors "#E8B4B8" "#2D3436"
"""

import argparse
import re
from pathlib import Path


def parse_hex_color(hex_str):
    """Parse hex color to RGB"""
    hex_str = hex_str.strip('#')
    if len(hex_str) == 6:
        r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
        return (r, g, b)
    raise ValueError(f"Invalid hex color: {hex_str}")


def relative_luminance(rgb):
    """Calculate relative luminance per WCAG"""
    r, g, b = [x / 255.0 for x in rgb]
    
    def adjust(c):
        if c <= 0.03928:
            return c / 12.92
        return pow((c + 0.055) / 1.055, 2.4)
    
    r, g, b = adjust(r), adjust(g), adjust(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(color1, color2):
    """Calculate WCAG contrast ratio"""
    l1 = relative_luminance(color1)
    l2 = relative_luminance(color2)
    
    lighter = max(l1, l2)
    darker = min(l1, l2)
    
    return (lighter + 0.05) / (darker + 0.05)


def check_wcag_level(ratio):
    """Determine WCAG compliance level"""
    if ratio >= 7:
        return "AAA (enhanced)"
    elif ratio >= 4.5:
        return "AA (at least 18.66px bold or larger)"
    elif ratio >= 3:
        return "Fail (need larger/bolder text)"
    else:
        return "Fail (not accessible)"


def extract_colors_from_md(md_path):
    """Extract color definitions from markdown"""
    content = Path(md_path).read_text()
    
    # Find color definitions like: - **Primary**: #E8B4B8
    pattern = r'- \*\*([^*]+)\*\*:?\s*(#[0-9A-Fa-f]{6})'
    matches = re.findall(pattern, content)
    
    colors = {}
    for name, hex_color in matches:
        try:
            colors[name.strip()] = parse_hex_color(hex_color)
        except ValueError:
            pass
    
    return colors


def check_palette_accessibility(colors):
    """Check contrast between key color pairs"""
    print("\\n🎨 Color Palette Accessibility Check\\n")
    print("=" * 70)
    
    # Test pairs (foreground, background)
    test_pairs = [
        ("Text", "Background"),
        ("Primary", "Background"),
        ("CTA", "Background"),
        ("Secondary", "Background"),
        ("Text", "Primary"),
    ]
    
    results = []
    
    for fg_name, bg_name in test_pairs:
        if fg_name in colors and bg_name in colors:
            fg_color = colors[fg_name]
            bg_color = colors[bg_name]
            ratio = contrast_ratio(fg_color, bg_color)
            level = check_wcag_level(ratio)
            
            status = "✓" if ratio >= 4.5 else "✗"
            results.append({
                'pair': f"{fg_name} on {bg_name}",
                'ratio': ratio,
                'level': level,
                'status': status
            })
    
    # Print results
    for result in results:
        print(f"{result['status']} {result['pair']:30} Ratio: {result['ratio']:.2f}  {result['level']}")
    
    print("\\n" + "=" * 70)
    
    accessible = sum(1 for r in results if r['status'] == '✓')
    total = len(results)
    print(f"\\nSummary: {accessible}/{total} color pairs accessible (WCAG AA)")
    
    if accessible < total:
        print("\\n⚠️  Recommendation: Adjust colors for better contrast")
        print("   - Lighter backgrounds need darker text")
        print("   - Darker backgrounds need lighter text")
        print("   - Use tools like contrast-ratio.com to find alternatives")


def check_from_args(colors_list):
    """Check specific color pairs from command line"""
    print("\\n🎨 Direct Color Contrast Check\\n")
    print("=" * 70)
    
    if len(colors_list) < 2:
        print("Error: Provide at least 2 colors")
        return
    
    # Group colors into pairs
    for i in range(0, len(colors_list) - 1, 2):
        fg_hex = colors_list[i]
        bg_hex = colors_list[i + 1] if i + 1 < len(colors_list) else colors_list[0]
        
        try:
            fg_color = parse_hex_color(fg_hex)
            bg_color = parse_hex_color(bg_hex)
            ratio = contrast_ratio(fg_color, bg_color)
            level = check_wcag_level(ratio)
            
            status = "✓" if ratio >= 4.5 else "✗"
            print(f"{status} {fg_hex} on {bg_hex}")
            print(f"   Ratio: {ratio:.2f}x  Level: {level}\\n")
        except ValueError as e:
            print(f"✗ Error: {e}")


def generate_accessible_palette(primary_hex):
    """Suggest accessible color combinations"""
    print(f"\\n🎨 Accessible Palette Suggestions for {primary_hex}\\n")
    print("=" * 70)
    
    try:
        primary = parse_hex_color(primary_hex)
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    print("Use this palette for guaranteed accessibility:\\n")
    print("- Text: #000000 (pure black)")
    print("- Background: #FFFFFF (pure white)")
    print(f"- Accent: {primary_hex}")
    print("\\nContrast ratios:")
    print(f"- Black on white: {contrast_ratio((0, 0, 0), (255, 255, 255)):.2f}x (Maximum)")


def main():
    parser = argparse.ArgumentParser(description="Check accessibility & color contrast")
    parser.add_argument(
        "file",
        nargs='?',
        help="Path to design-system/MASTER.md"
    )
    parser.add_argument(
        "--colors",
        nargs='+',
        help="Check specific color pairs: --colors '#HEX1' '#HEX2' '#HEX3' ..."
    )
    parser.add_argument(
        "--suggest",
        help="Suggest accessible palette for primary color"
    )
    
    args = parser.parse_args()
    
    if args.suggest:
        generate_accessible_palette(args.suggest)
    elif args.colors:
        check_from_args(args.colors)
    elif args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"Error: File not found: {path}")
            return
        
        colors = extract_colors_from_md(path)
        if colors:
            print(f"Found {len(colors)} colors in {path}")
            check_palette_accessibility(colors)
        else:
            print("No colors found. Use format: - **Color Name**: #HEXCODE")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
