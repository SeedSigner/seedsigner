def generate_qr_template(size):
    html = """
    <html>
        <style>
            body {
                font-size: 1em;
            }
            table {
                margin-top:  5em;
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
            .col_name .row_name {
                font-size: 0.6em;
                text-align: center;
            }
        </style>
        <body>
            <table align="center">
    """

    y_names = "A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,X,Y,Z,AA,BB,CC,DD"

    # html += "<tr><td></td>"
    # for j in range(0, size):
    #     html += f"""<td class="col_name">{j + 1}</td>"""
    # html += "</tr>"

    for i in range(0, size):
        html += """<tr>\n"""
        # html += f"""<td class="row_name">{y_names.split(",")[i]}</td>"""
        for j in range(0, size):
            html += f"""<td id="{i}_{j}"></td>"""
        html += """</tr>\n"""
    html += "</table>"

    html += "<script>"

    def fill(i, j):
        return f"""document.getElementById("{i}_{j}").classList.add("filled");\n"""


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
        return result

    html += fill_registration_box(0, 0)
    html += fill_registration_box(0, size - 7)
    html += fill_registration_box(size - 7, 0)

    # Fill the dotted timing lines
    html += fill(8, 6)
    html += fill(10, 6)
    html += fill(12, 6)
    html += fill(14, 6)
    html += fill(16, 6)
    if size ==  29:
        html += fill(18, 6)
        html += fill(20, 6)

    html += fill(6, 8)
    html += fill(6, 10)
    html += fill(6, 12)
    html += fill(6, 14)
    html += fill(6, 16)
    if size == 29:
        html += fill(6, 18)
        html += fill(6, 20)

    # Fill the smaller inset registration box
    html += fill(size - 7, size - 7)

    for i in range(size - 9, size - 4):
        html += fill(i, size - 9)
        html += fill(i, size - 5)
    for j in range(size - 8, size - 5):
        html += fill(size - 9, j)
        html += fill(size - 5, j)

    html += """</script>
        </body>
    </html>"""

    return html



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="""
    Generates a blank QR code template at either 25x25 or 29x29.

    ex: python3 qr_code_template.py 25
    ex: python3 qr_code_template.py 29
        """,
        formatter_class=argparse.RawTextHelpFormatter
    )

    # Required positional arguments
    parser.add_argument('size',
                        type=int,
                        choices=[25, 29],
                        help="QR code size. 25 for 25x25, 29 for 29x29")
    args = parser.parse_args()

    html = generate_qr_template(args.size)
    file = open(f"qr_code_template_{args.size}x{args.size}.html", "w")
    file.write(html)
    file.close()

