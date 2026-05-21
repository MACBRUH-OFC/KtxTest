from flask import Flask, render_template, request, send_file
from PIL import Image
import struct
import os
import uuid
import traceback

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def convert_ktx_to_png(input_path, output_path):

    with open(input_path, 'rb') as f:

        header = f.read(64)

        if len(header) < 64:
            raise Exception("Invalid KTX file")

        width = struct.unpack('<I', header[36:40])[0]
        height = struct.unpack('<I', header[40:44])[0]

        bytes_of_kv = struct.unpack('<I', header[60:64])[0]

        f.seek(64 + bytes_of_kv)

        image_size = struct.unpack('<I', f.read(4))[0]

        data = f.read(image_size)

    expected = width * height * 4

    if len(data) < expected:
        raise Exception(
            f"Texture data too small.\n"
            f"Expected: {expected}\n"
            f"Found: {len(data)}"
        )

    img = Image.frombytes(
        "RGBA",
        (width, height),
        data[:expected]
    )

    r, g, b, a = img.split()

    img = Image.merge(
        "RGBA",
        (b, g, r, a)
    )

    img = img.transpose(Image.FLIP_TOP_BOTTOM)

    img.save(output_path)

def convert_png_to_ktx(input_path, output_path):

    img = Image.open(input_path).convert("RGBA")

    img = img.transpose(Image.FLIP_TOP_BOTTOM)

    r, g, b, a = img.split()

    img = Image.merge(
        "RGBA",
        (b, g, r, a)
    )

    width, height = img.size

    pixel_data = img.tobytes()

    kv_key = b"KTXorientation"

    kv_value = b"S=r,T=d"

    kv_pair = kv_key + b"\x00" + kv_value + b"\x00"

    kv_entry = struct.pack(
        '<I',
        len(kv_pair)
    ) + kv_pair

    padding = (
        4 - (len(kv_entry) % 4)
    ) % 4

    kv_block = kv_entry + (
        b'\x00' * padding
    )

    header = struct.pack(
        '<12sIIIIIIIIIIII',
        b'\xABKTX 11\xBB\r\n\x1A\n',
        0x04030201,
        0x1401,
        1,
        0x1908,
        0x8058,
        0x1908,
        width,
        height,
        0,
        0,
        1,
        len(kv_block)
    )

    with open(output_path, 'wb') as f:

        f.write(header)

        f.write(kv_block)

        f.write(
            struct.pack(
                '<I',
                len(pixel_data)
            )
        )

        f.write(pixel_data)

@app.route("/", methods=["GET", "POST"])
def home():

    try:

        if request.method == "POST":

            mode = request.form.get("mode")

            file = request.files["file"]

            ext = os.path.splitext(file.filename)[1]

            unique = str(uuid.uuid4())

            input_path = os.path.join(
                UPLOAD_FOLDER,
                unique + ext
            )

            file.save(input_path)

            if mode == "ktx_to_png":

                output_path = os.path.join(
                    UPLOAD_FOLDER,
                    unique + ".png"
                )

                convert_ktx_to_png(
                    input_path,
                    output_path
                )

                return send_file(
                    output_path,
                    as_attachment=True
                )

            elif mode == "png_to_ktx":

                output_path = os.path.join(
                    UPLOAD_FOLDER,
                    unique + ".ktx"
                )

                convert_png_to_ktx(
                    input_path,
                    output_path
                )

                return send_file(
                    output_path,
                    as_attachment=True
                )

        return render_template("index.html")

    except Exception as e:

        return f"""
        <h1>ERROR</h1>

        <pre>
{traceback.format_exc()}
        </pre>
        """

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=10000
    )
