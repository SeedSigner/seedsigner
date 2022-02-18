import math

def generate_qr_template(qr_size, block_size=5, show_timing_marks=False):
    if qr_size == 29:
        num_words = 24
        word_cols = 2
    else:
        num_words = 12
        word_cols = 1

    html = """
    <html>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Open+Sans&display=swap" rel="stylesheet">

        <style>
            body {
                margin-top: 5em;
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
            .qr_table {
                margin-top: 5em;
                margin-right: 4em;
                float: right;
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

            .word_list_table {
    """

    if num_words == 12:
        html += "margin-left: 10em;\n"
    else:
        html += "margin-left: 0;\n"

    html += """
                float: left;
            }
            .word_list {
                text-align: right;
                padding-top: 2em;
                padding-left: 1em;
                padding-right: 1em;
            }
            .word_row {
                height: 2.5em;
            }
            .word_num {
                width: 1em;
                text-align: right;
                color: #999;
            }
            .word_blank {
                color: #ccc;
            }
        </style>
        <body>
    """

    html += """
        <table align="center" class="word_list_table">
            <tr>
                <td class="word_list">
    """
    for i in range(1, num_words + 1):
        if i == 13:
            html += """
                </td>
                <td class="word_list">
            """
        html += f"""<div class="word_row">
                <span class="word_num">{i}:&nbsp;</span><span class="word_blank">____________________________</span>
            </div>
        """
    html += "</td></tr></table>"

    y_names = "A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,X,Y,Z"

    html += """<table align="center" class="qr_table">"""
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

