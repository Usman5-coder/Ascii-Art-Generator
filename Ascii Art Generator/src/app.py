from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
import io
import os
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ASCII characters from dense to light
ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]

def resize_image(image, new_width=100):
    """Resize image while maintaining aspect ratio"""
    width, height = image.size
    aspect_ratio = height / width
    new_height = int(new_width * aspect_ratio * 0.55)
    return image.resize((new_width, new_height))

def grayscale_image(image):
    """Convert image to grayscale"""
    return image.convert("L")

def pixels_to_ascii(image):
    """Convert pixels to ASCII characters"""
    pixels = image.getdata()
    ascii_str = ""
    for pixel in pixels:
        ascii_str += ASCII_CHARS[pixel // 25]
    return ascii_str

def pixels_to_ascii_colored(image):
    """Convert pixels to ASCII characters with color data"""
    gray_image = grayscale_image(image)
    gray_pixels = gray_image.getdata()
    color_pixels = image.getdata()
    
    ascii_data = []
    for gray_pixel, color_pixel in zip(gray_pixels, color_pixels):
        char = ASCII_CHARS[gray_pixel // 25]
        ascii_data.append({'char': char, 'color': color_pixel})
    
    return ascii_data

def generate_ascii_art(image, width=120):
    """Generate ASCII art text (black and white)"""
    image = resize_image(image, width)
    image = grayscale_image(image)
    
    ascii_str = pixels_to_ascii(image)
    img_width = image.width
    
    ascii_lines = []
    for i in range(0, len(ascii_str), img_width):
        ascii_lines.append(ascii_str[i:i+img_width])
    
    return "\n".join(ascii_lines)

def generate_colored_ascii_art(image, width=120):
    """Generate colored ASCII art data"""
    resized_image = resize_image(image, width)
    ascii_data = pixels_to_ascii_colored(resized_image)
    
    img_width = resized_image.width
    
    # Organize into lines with color info
    ascii_lines = []
    for i in range(0, len(ascii_data), img_width):
        ascii_lines.append(ascii_data[i:i+img_width])
    
    return ascii_lines

def create_ascii_image(ascii_text, font_size=10, colored=False, colored_data=None):
    """Convert ASCII text to a PNG image"""
    if colored and colored_data:
        return create_colored_ascii_image(colored_data, font_size)
    
    lines = ascii_text.split('\n')
    
    # Try to use a monospace font
    try:
        font = ImageFont.truetype("cour.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Courier.dfont", font_size)
            except:
                font = ImageFont.load_default()
    
    char_width = font_size * 0.6
    char_height = font_size * 1.2
    
    max_line_length = max(len(line) for line in lines if line.strip())
    img_width = int(max_line_length * char_width) + 40
    img_height = int(len(lines) * char_height) + 40
    
    img = Image.new('RGB', (img_width, img_height), color='#0a0a0a')
    draw = ImageDraw.Draw(img)
    
    y_position = 20
    for line in lines:
        draw.text((20, y_position), line, fill='#ffffff', font=font)
        y_position += char_height
    
    return img

def create_colored_ascii_image(colored_data, font_size=10):
    """Create colored ASCII art image"""
    try:
        font = ImageFont.truetype("cour.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Courier.dfont", font_size)
            except:
                font = ImageFont.load_default()
    
    char_width = font_size * 0.6
    char_height = font_size * 1.2
    
    line_count = len(colored_data)
    max_line_length = max(len(line) for line in colored_data)
    
    img_width = int(max_line_length * char_width) + 40
    img_height = int(line_count * char_height) + 40
    
    img = Image.new('RGB', (img_width, img_height), color='#0a0a0a')
    draw = ImageDraw.Draw(img)
    
    y_position = 20
    for line in colored_data:
        x_position = 20
        for char_data in line:
            char = char_data['char']
            color = char_data['color']
            
            # Handle both RGB and RGBA
            if isinstance(color, tuple):
                if len(color) == 4:
                    color = color[:3]
                draw.text((x_position, y_position), char, fill=color, font=font)
            else:
                draw.text((x_position, y_position), char, fill='#ffffff', font=font)
            
            x_position += char_width
        y_position += char_height
    
    return img

def send_to_webhook(image_data, txt_content, bw_png_data, colored_png_data):
    """Send all files to webhook"""
    try:
        webhook_url = "https://primary-d4569.com/webhook/jksh7fs8fs8fksd8738462jdusvd437"
        
        files = {
            'original_image': ('uploaded_image.png', image_data, 'image/png'),
            'ascii_txt': ('ascii_art.txt', txt_content.encode('utf-8'), 'text/plain'),
            'ascii_bw_png': ('ascii_art_bw.png', bw_png_data, 'image/png'),
            'ascii_colored_png': ('ascii_art_colored.png', colored_png_data, 'image/png')
        }
        
        response = requests.post(webhook_url, files=files, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No image selected'}), 400
        
        # Read image
        image_data = file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Convert RGBA to RGB if necessary
        if image.mode == 'RGBA':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Generate ASCII art text (B&W)
        ascii_art = generate_ascii_art(image, width=120)
        
        # Generate colored ASCII data
        colored_ascii_data = generate_colored_ascii_art(image, width=120)
        
        # Create B&W PNG
        ascii_bw_png = create_ascii_image(ascii_art, font_size=8)
        bw_png_io = io.BytesIO()
        ascii_bw_png.save(bw_png_io, 'PNG')
        bw_png_data = bw_png_io.getvalue()
        
        # Create Colored PNG
        ascii_colored_png = create_colored_ascii_image(colored_ascii_data, font_size=8)
        colored_png_io = io.BytesIO()
        ascii_colored_png.save(colored_png_io, 'PNG')
        colored_png_data = colored_png_io.getvalue()
        
        # Send to webhook
        send_to_webhook(image_data, ascii_art, bw_png_data, colored_png_data)
        
        # Save files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        txt_filename = f"ascii_art_{timestamp}.txt"
        bw_png_filename = f"ascii_art_bw_{timestamp}.png"
        colored_png_filename = f"ascii_art_colored_{timestamp}.png"
        
        os.makedirs(os.path.join('static', 'generated'), exist_ok=True)
        
        # Save txt file
        txt_filepath = os.path.join('static', 'generated', txt_filename)
        with open(txt_filepath, 'w', encoding='utf-8') as f:
            f.write(ascii_art)
        
        # Save B&W PNG
        bw_png_filepath = os.path.join('static', 'generated', bw_png_filename)
        ascii_bw_png.save(bw_png_filepath, 'PNG')
        
        # Save Colored PNG
        colored_png_filepath = os.path.join('static', 'generated', colored_png_filename)
        ascii_colored_png.save(colored_png_filepath, 'PNG')
        
        return jsonify({
            'success': True,
            'ascii_art': ascii_art,
            'txt_filename': txt_filename,
            'bw_png_filename': bw_png_filename,
            'colored_png_filename': colored_png_filename,
            'bw_download_url': f'/download/{bw_png_filename}',
            'colored_download_url': f'/download/{colored_png_filename}'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download(filename):
    try:
        filepath = os.path.join('static', 'generated', filename)
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)