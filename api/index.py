from flask import Flask, request, render_template, send_file
import struct
import os
import uuid
from PIL import Image
import texture2ddecoder

app = Flask(__name__)

UPLOAD_FOLDER = "/tmp"

def convert_ktx_to_png(input_path, output_path):
    with open(input_path, 'rb') as f:
        header = f.read(64)

        gl_internal_format = struct.unpack('<I', header[28:32])[0]
        width = struct.unpack('<I', header[36:40])[0]
        height = struct.unpack('<I', header[40:44])[0]
        bytes_of_kv = struct.unpack('<I', header[60:64])[0]

        f.seek(64 + bytes_of_kv)

        image_size = struct.unpack('<I', f.read(4))[0]
        data = f.read(image_size)

    if gl_internal_format == 0x8D64:
        decoded = texture2ddecoder.decode_etc1(data, width, height)

    elif 0x93B0 <= gl_internal_format <= 0x93BD:
        astc_formats = {
            0x93B0:(4,4),
            0x93B1:(5,4),
            0x93B2:(5,5),
            0x93B3:(6,5),
            0x93B4:(6,6),
            0x93B5:(8,5),
            0x93B6:(8,6),
            0x93B7:(8,8),
            0x93B8:(10,5)
        }

        bx, by = astc_formats[gl_internal_format]
        decoded = texture2ddecoder.decode_astc(
            data,
            width,
            height,
            bx,
            by
        )
    else:
        decoded = data

    img = Image.frombytes(
        "RGBA",
        (width, height),
        decoded
    )

    r, g, b, a = img.split()

    img = Image.merge(
        "RGBA",
        (b, g, r, a)
    ).transpose(Image.FLIP_TOP_BOTTOM)

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
        f.write(struct.pack('<I', len(pixel_data)))
        f.write(pixel_data)

@app.route("/", methods=["GET", "POST"])
def home():

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

if __name__ == "__main__":
    app.run()
