import math

def generate_qr_template(qr_size, block_size=5, show_timing_marks=False):
    html = """
    <html>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Open+Sans&display=swap" rel="stylesheet">

        <style>
            body {
                text-align: center;
                font-family: "Open Sans", sans-serif;
                -webkit-print-color-adjust: exact;
            }
            .title {
                margin-top: 0.5em;
                font-size: 1.5em;
                margin-bottom: 1em
            }
            table {
                margin-top: 1em;
                border-collapse: collapse;
            }
            td {
                padding:  0;
                margin:  0;
                border: 1px dotted #c8c8c8;
                width: 11px;
                height: 12px;
            }
            .filled {
                background-color: black;
                border: 1px solid black;
            }
            .col_name, .row_name {
                text-align: center;
                font-size: 0.7em;
                color: #aaa;
            }
            .col_name {
                border-bottom: 1px solid #bbb;
                height: 2em;
            }
            .row_name {
                border-right: 1px solid #bbb;
                width: 2em;
            }
            .col_block_divider {
                border-right: 1px solid #bbb;
            }
            .row_block_divider {
                border-bottom: 1px solid #bbb;
            }
            .no_border {
                border: none;
            }
        </style>
        <body>
    """
    html += f"""<div class="title">{qr_size}-word Seed</div>"""

    y_names = "A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,X,Y,Z"

    html += """<table align="center">"""
    html += f"""<tr rowspan="{block_size}"><td class="col_block_divider row_block_divider"></td>"""
    for j in range(0, math.ceil(qr_size/block_size)):
        html += f"""<td colspan="{block_size}" class="col_name col_block_divider">{j + 1}</td>"""
    html += "</tr>"

    for i in range(0, qr_size):
        html += """<tr>\n"""
        if i % block_size == 0:
            html += f"""<td rowspan="{block_size}" class="row_name row_block_divider">{y_names.split(",")[int(i / block_size)]}</td>"""
        for j in range(0, qr_size):
            html += f"""<td id="{i}_{j}"></td>"""
        html += """</tr>\n"""
    html += "</table>"

    html += "<script>"

    def fill(i, j):
        return f"""document.getElementById("{i}_{j}").classList.add("filled");\n"""

    def no_border(i, j):
        return f"""document.getElementById("{i}_{j}").classList.add("no_border");\n"""


    # Generate the corner registration box
    def fill_registration_box(offset_i, offset_j):
        result = ""
        for i in range(0, 7):
            i += offset_i
            result += fill(i, offset_j + 0)
            result += fill(i, offset_j + 6)
        for j in range(1, 6):
            j += offset_j
            result += fill (offset_i + 0, j)
            result += fill (offset_i + 6, j)
        for i in range(2, 5):
            i += offset_i
            result += fill(i, offset_j + 2)
            result += fill(i, offset_j + 3)
            result += fill(i, offset_j + 4)
        for i in range(offset_i, offset_i + 7):
            for j in range(offset_j, offset_j + 7):
                result += no_border(i, j)
        return result

    html += fill_registration_box(0, 0)
    html += fill_registration_box(0, qr_size - 7)
    html += fill_registration_box(qr_size - 7, 0)

    if show_timing_marks:
        # Fill the dotted timing marks
        html += fill(8, 6)
        html += fill(10, 6)
        html += fill(12, 6)
        if qr_size > 21:
            html += fill(14, 6)
            html += fill(16, 6)
            if qr_size > 25:
                html += fill(18, 6)
                html += fill(20, 6)

        html += fill(6, 8)
        html += fill(6, 10)
        html += fill(6, 12)
        if qr_size > 21:
            html += fill(6, 14)
            html += fill(6, 16)
            if qr_size > 25:
                html += fill(6, 18)
                html += fill(6, 20)

    if qr_size > 21:
        # Fill the smaller inset registration box
        html += fill(qr_size - 7, qr_size - 7)

        for i in range(qr_size - 9, qr_size - 4):
            html += fill(i, qr_size - 9)
            html += fill(i, qr_size - 5)
        for j in range(qr_size - 8, qr_size - 5):
            html += fill(qr_size - 9, j)
            html += fill(qr_size - 5, j)
        for i in range(qr_size - 9, qr_size - 4):
            for j in range(qr_size - 9, qr_size - 4):
                html += no_border(i, j)


    def add_block_dividers(i, j, class_name):
        return f"""document.getElementById("{i}_{j}").classList.add("{class_name}");\n"""

    for i in range (0, qr_size):
        for j in range (block_size - 1, qr_size, block_size):
            html += add_block_dividers(i, j, "col_block_divider")

    for i in range (block_size - 1, qr_size, block_size):
        for j in range (0, qr_size):
            html += add_block_dividers(i, j, "row_block_divider")


    html += """</script>
        </body>
    </html>"""

    return html



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="""
    Generates a blank QR code template at 21x21, 25x25, or 29x29.

        ex: python3 qr_code_template.py 25
        ex: python3 qr_code_template.py 29

    Optionally change the block size divider guides:

        python3 qr_code_template.py 29 --block_size 6
        """,
        formatter_class=argparse.RawTextHelpFormatter
    )

    # Required positional arguments
    parser.add_argument('qr_size',
                        type=int,
                        choices=[21, 25, 29],
                        help="QR code size. 21 for 21x21, 25 for 25x25, 29 for 29x29")
    parser.add_argument('-b', '--block_size',
                        type=int,
                        default=5,
                        help="Size of the manual entry zoom blocks")
    parser.add_argument('-t', '--timing_marks',
                        action='store_true',
                        default=False,
                        help="Show timing marks (the dashed blocks linking the three large registration boxes")
    args = parser.parse_args()

    html = generate_qr_template(qr_size=args.qr_size, block_size=args.block_size, show_timing_marks=args.timing_marks)
    file = open(f"qr_code_template_{args.qr_size}x{args.qr_size}.html", "w")
    file.write(html)
    file.close()

