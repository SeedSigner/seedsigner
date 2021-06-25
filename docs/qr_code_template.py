def generate_qr_template():
	html = """
	<html>
		<style>
			table {
				margin-top:  5em;
				border-collapse: collapse;
			}
			td {
				padding:  0;
				margin:  0;
				border: 1px dotted #d8d8d8;
				width: 11px;
				height: 12px;
			}
			.filled {
				background-color: black;
				border: 1px solid black;
			}
		</style>
		<body>
			<table align="center">
	"""

	for i in range(0, 25):
		html += """<tr>\n"""
		for j in range(0, 25):
			html += f"""<td id="{i}_{j}"></td>"""
		html += """</tr>\n"""
	html += "</table>"

	html += "<script>"

	def fill(i, j):
		return f"""document.getElementById("{i}_{j}").classList.add("filled");\n"""


	# Generate the top left registration box
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
	html += fill_registration_box(0, 18)
	html += fill_registration_box(18, 0)

	html += fill(10, 6)
	html += fill(12, 6)
	html += fill(14, 6)
	html += fill(16, 6)

	html += fill(6, 10)
	html += fill(6, 12)
	html += fill(6, 14)
	html += fill(6, 16)

	html += fill(18, 18)

	for i in range(16, 21):
		html += fill(i, 16)
		html += fill(i, 20)
	for j in range(17, 20):
		html += fill(16, j)
		html += fill(20, j)

	html += """</script>
		</body>
	</html>"""

	return html



if __name__ == "__main__":
	print(generate_qr_template())