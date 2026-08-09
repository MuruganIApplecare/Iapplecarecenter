import os
import re
import hashlib
from PIL import Image

def compress_images(directory):
    print("Starting image conversion to WebP...")
    image_extensions = ('.png', '.jpg', '.jpeg', '.jfif')
    converted_count = 0
    total_original_size = 0
    total_new_size = 0

    for root, dirs, files in os.walk(directory):
        # Skip the archived scraped files to avoid clutter if any, but process main images
        for file in files:
            if file.lower().endswith(image_extensions):
                full_path = os.path.join(root, file)
                # Keep original extension but change the output file to .webp
                base, ext = os.path.splitext(full_path)
                webp_path = base + ".webp"

                try:
                    original_size = os.path.getsize(full_path)
                    total_original_size += original_size

                    # Open image
                    with Image.open(full_path) as img:
                        # Convert RGBA to RGB if saving as WebP (Pillow handles RGBA->WebP perfectly though)
                        # We just save it with quality=80
                        img.save(webp_path, "WEBP", quality=80)

                    new_size = os.path.getsize(webp_path)
                    total_new_size += new_size
                    converted_count += 1
                    print(f"Converted: {os.path.relpath(full_path, directory)} -> WebP ({original_size/1024:.1f}KB -> {new_size/1024:.1f}KB)")
                except Exception as e:
                    print(f"Error converting {full_path}: {e}")

    print(f"Successfully converted {converted_count} images.")
    if total_original_size > 0:
        reduction = (1 - (total_new_size / total_original_size)) * 100
        print(f"Total size reduction: {total_original_size/(1024*1024):.2f}MB -> {total_new_size/(1024*1024):.2f}MB ({reduction:.1f}% saved)")


def minify_css(css_content):
    # Remove comments
    css = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
    # Remove whitespace around delimiters
    css = re.sub(r'\s*([\{\}:;,])\s*', r'\1', css)
    # Remove multiple spaces/newlines
    css = re.sub(r'\s+', ' ', css)
    return css.strip()


def minify_js(js_content):
    # Remove single line comments (careful with URLs)
    # Match double slashes that are not preceded by a colon (like http://)
    js = re.sub(r'(?<!:)//.*', '', js_content)
    # Remove multi-line comments
    js = re.sub(r'/\*.*?\*/', '', js, flags=re.DOTALL)
    # Remove multiple newlines and spaces
    lines = []
    for line in js.splitlines():
        line = line.strip()
        if line:
            lines.append(line)
    # Join with newlines to keep it safe from missing semicolons, but strip empty space
    return '\n'.join(lines)


def process_code_files(base_dir):
    print("Minifying CSS and JS...")
    # Minify styles.css
    styles_path = os.path.join(base_dir, "styles.css")
    styles_min_path = os.path.join(base_dir, "styles.min.css")
    if os.path.exists(styles_path):
        with open(styles_path, 'r', encoding='utf-8') as f:
            css_data = f.read()
        minified_css = minify_css(css_data)
        with open(styles_min_path, 'w', encoding='utf-8') as f:
            f.write(minified_css)
        print(f"Minified CSS: {os.path.getsize(styles_path)/1024:.1f}KB -> {os.path.getsize(styles_min_path)/1024:.1f}KB")

    # Minify script.js
    script_path = os.path.join(base_dir, "script.js")
    script_min_path = os.path.join(base_dir, "script.min.js")
    if os.path.exists(script_path):
        with open(script_path, 'r', encoding='utf-8') as f:
            js_data = f.read()
        minified_js = minify_js(js_data)
        with open(script_min_path, 'w', encoding='utf-8') as f:
            f.write(minified_js)
        print(f"Minified JS: {os.path.getsize(script_path)/1024:.1f}KB -> {os.path.getsize(script_min_path)/1024:.1f}KB")

    # Calculate content hashes for cache-busting
    css_hash = "1"
    js_hash = "1"
    if os.path.exists(styles_min_path):
        with open(styles_min_path, 'r', encoding='utf-8') as f:
            css_hash = hashlib.md5(f.read().encode('utf-8')).hexdigest()[:8]
    if os.path.exists(script_min_path):
        with open(script_min_path, 'r', encoding='utf-8') as f:
            js_hash = hashlib.md5(f.read().encode('utf-8')).hexdigest()[:8]

    print(f"Content hashes - CSS: {css_hash}, JS: {js_hash}")

    # Rewrite HTML files
    html_files = ["index.html", "booking.html", "privacy-policy.html", "terms-of-service.html", "404.html"]
    image_extensions_pattern = re.compile(r'images/([^"\'\>]+)\.(png|jpg|jpeg|jfif)', re.IGNORECASE)

    for html_name in html_files:
        html_path = os.path.join(base_dir, html_name)
        if not os.path.exists(html_path):
            continue

        print(f"Updating references in {html_name}...")
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 1. Replace styles link with cache-busted version
        content = re.sub(
            r'href=["\'](?:styles\.css|styles\.min\.css)(?:\?v=[a-fA-F0-9]+)?["\']',
            f'href="styles.min.css?v={css_hash}"',
            content
        )

        # 2. Replace script link with cache-busted version
        content = re.sub(
            r'src=["\'](?:script\.js|script\.min\.js)(?:\?v=[a-fA-F0-9]+)?["\'](?:\s+defer)?',
            f'src="script.min.js?v={js_hash}" defer',
            content
        )

        # 3. Replace image extensions with .webp
        def img_replace(match):
            path = match.group(1)
            return f"images/{path}.webp"

        content = image_extensions_pattern.sub(img_replace, content)

        # 4. Add loading="lazy" for below-the-fold images if they don't have it, excluding hero-image
        img_tags = re.findall(r'<img[^>]+>', content)
        for img_tag in img_tags:
            if 'hero-image' in img_tag or 'loading=' in img_tag:
                continue
            
            new_img_tag = img_tag.replace('src=', 'loading="lazy" src=')
            content = content.replace(img_tag, new_img_tag)

        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {html_name} successfully.")


if __name__ == "__main__":
    base_dir = r"d:\FinalIApple"
    images_dir = os.path.join(base_dir, "images")

    compress_images(images_dir)
    process_code_files(base_dir)
    print("All performance optimizations applied successfully!")
