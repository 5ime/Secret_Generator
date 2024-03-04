import os
import io
import re
import uuid
import base64
from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
user_last_request_time = {}  # 记录每个用户的上次请求时间

ALLOWED_FONT_TYPES = {'ttf', 'otf', 'woff', 'woff2'}

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Secret Generator</title>
        <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f0f0f0;
        }

        h1 {
            text-align: center;
            margin-top: 30px;
            color: #333;
        }

        form {
            width: 80%;
            max-width: 400px;
            margin: 20px auto;
            padding: 20px;
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        }

        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }

        input[type="text"],
        input[type="file"] {
            width: 100%;
            padding: 10px;
            margin-bottom: 10px;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-sizing: border-box;
        }

        input[type="submit"] {
            width: 100%;
            padding: 10px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }

        input[type="submit"]:hover {
            background-color: #45a049;
        }

        #secretImageContainer {
            margin-top: 20px;
            text-align: center;
        }

        #secretImageContainer img {
            max-width: 100%;
            height: auto;
            margin: 5px
        }
    </style>
    </head>
    <body>
        <h1>Secret Generator</h1>
        <form id="secretForm" enctype="multipart/form-data">
            <label for="secretInput">Secret Text:</label><br>
            <input type="text" id="secretInput" name="secretInput" pattern="[a-zA-Z0-9]+" title="Only letters and numbers are allowed, rest assured that there are no symbols"><br>
            <label for="fontInput">Custom Font (Optional):</label><br>
            <input type="file" id="fontInput" name="fontInput"><br><br>
            <input type="submit" value="Generate Secret Image">
        </form>

        <div id="secretImageContainer"></div>

        <script>
            document.getElementById('secretForm').addEventListener('submit', function(event) {
                event.preventDefault();
                const secretInput = document.getElementById('secretInput');
                const pattern = new RegExp(secretInput.pattern);
                if (!pattern.test(secretInput.value)) {
                    // As you can see, no special characters are needed, just case and numbers!
                    alert('Only letters and numbers are allowed for text.');
                    return;
                }

                const fontInput = document.getElementById('fontInput');
                if (fontInput.files.length === 0) {
                    alert('Please select a font file.');
                    return;
                }
                
                const formData = new FormData();
                formData.append('secret', secretInput.value);
                formData.append('font', fontInput.files[0]);

                fetch('/generate_secret_image', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert(data.error);
                    } else {
                        const originalImgUrl = 'data:image/png;base64,' + data.original_image;
                        const originalImg = document.createElement('img');
                        originalImg.src = originalImgUrl;
                        document.getElementById('secretImageContainer').innerHTML = '';
                        document.getElementById('secretImageContainer').appendChild(originalImg);
                        
                        const secretImgUrl = 'data:image/png;base64,' + data.secret_image;
                        const secretImg = document.createElement('img');
                        secretImg.src = secretImgUrl;
                        document.getElementById('secretImageContainer').appendChild(secretImg);
                    }
                })
                .catch(error => console.error('Error:', error));
            });
        </script>
    </body>
    </html>
    """

def rate_limit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        ip = request.remote_addr
        if ip in user_last_request_time:
            last_request_time = user_last_request_time[ip]
            time_since_last_request = datetime.now() - last_request_time
            if time_since_last_request < timedelta(seconds=10):
                return jsonify({'error': 'Too many requests. Please try again in 10 seconds.'}), 429
        user_last_request_time[ip] = datetime.now()
        return func(*args, **kwargs)
    return wrapper

@app.route('/generate_secret_image', methods=['POST'])
@rate_limit
def generate_secret_image():
    try:

        secret = request.form.get('secret')

        if not re.match("^[a-zA-Z0-9]+$", secret):
            return jsonify({'error': 'Secret text can only contain letters and numbers.'}), 400
        
        secret = 'pass ' + secret

        font_file = request.files.get('font')
        
        if font_file:
            font_extension = font_file.filename.rsplit('.', 1)[1].lower()
            if font_extension not in ALLOWED_FONT_TYPES:
                return jsonify({'error': 'Invalid font file type. Only TTF, OTF, WOFF, WOFF2 files are allowed.'}), 400
            
            if font_file.content_length > (10 * 1024 * 1024):
                return jsonify({'error': 'The font file is too large!'}), 400
            
            font_filename = str(uuid.uuid4()) + '.' + font_extension
            font_path = save_font_file(font_file, font_filename)
            font = ImageFont.truetype(font_path, 49, encoding='utf-8')
        else:
            return jsonify({'error': 'Please select a font file.'}), 400
        
        H = 60
        W = 30
        canvas = Image.new('RGB', (W * len(secret), H), (255, 255, 255))
        pen = ImageDraw.Draw(canvas)
        pen.text((0, 0), secret, 'black', font)
        original_canvas = canvas.copy()

        for i in range(5, len(secret)-1):
            mosaic_img(canvas, W*i, 0, W*i+W, H//2)
            mosaic_img(canvas, W*i, H//2, W*i+W, H)
        
        original_img_base64 = image_to_base64(original_canvas)
        secret_img_base64 = image_to_base64(canvas)
        
        return jsonify({'original_image': original_img_base64, 'secret_image': secret_img_base64})
    except Exception as e:
        print("An error occurred:", e)
        return jsonify({'error': 'Internal Server Error'}), 500
    
def image_to_base64(img):
    img_byte_array = io.BytesIO()
    img.save(img_byte_array, format='PNG')
    img_byte_array = img_byte_array.getvalue()
    return base64.b64encode(img_byte_array).decode()

def mosaic_img(img, L, H, R, D):
    w, h = R - L, D - H
    a = [0, 0, 0]
    cnt = 0
    for x in range(w):
        for y in range(h):
            j = img.getpixel((L+x, H+y))
            for ch in range(len(a)):
                a[ch] += j[ch]
            cnt += 1
    b = [k//cnt for k in a]
    mosaic = Image.new('RGB', (w, h), tuple(b))
    img.paste(mosaic, (L, H, R, D))

def save_font_file(font_file, font_filename):
    font_dir = 'fonts'
    os.makedirs(font_dir, exist_ok=True)
    font_path = os.path.join(font_dir, font_filename)
    font_file.save(font_path)
    return font_path

if __name__ == '__main__':
    app.run(debug=True)
