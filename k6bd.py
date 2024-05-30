#-------------------------------------------------------------------------------------------------------------------------------------------
# k6bd.py : Crawl Kill6BillionDemons and grab every comic page, hover text, and short story, then compile them into a PDF.
#-------------------------------------------------------------------------------------------------------------------------------------------
# Imports.

# Local imports.
# System imports.
import io
import requests
import textwrap
import urllib
import urllib.request
# Global imports.
import bs4
import PIL
import reportlab.lib.colors
import reportlab.lib.styles
import reportlab.lib.units
import reportlab.lib.utils
import reportlab.pdfbase.pdfmetrics
import reportlab.pdfbase.ttfonts
import reportlab.pdfgen.canvas
import reportlab.platypus
import tinify

#-------------------------------------------------------------------------------------------------------------------------------------------
# Constants.

# Hard script constants.
PATH_STATE = "./state.txt"
PATH_DIR = "./Render/"
PAGE_START = "https://killsixbilliondemons.com/comic/kill-six-billion-demons-chapter-1/"
PAGE_TARGETS = {
	"comic": ["div", "id", "comic"],
	"entry": ["div", "class", "entry"],
	"next": ["a", "class", "navi comic-nav-next navi-next"],
}
FONT_SIZE = 12
WRAP_SIZE = 120
tinify.key = "TINYPNG KEY HERE."
TO_TINY = False
# Soft script constants.
FONT_PAD = FONT_SIZE / 2
# Hard string constants.

#-------------------------------------------------------------------------------------------------------------------------------------------
# Functions for handling HTML.

# Grab a page and return it as a string.
def get_page(in_url):
	page_raw = urllib.request.urlopen(in_url)
	page_bytes = page_raw.read()
	page_string = page_bytes.decode("UTF-8")
	return page_string

# Take in a raw webpage in a string and parse it.
def get_html(in_string):
	page_html = bs4.BeautifulSoup(in_string, features="html.parser")
	return page_html

# Take in a URL and return a parsed HTML object.
def get_url(in_url):
	page_raw = get_page(in_url)
	page_html = get_html(page_raw)
	return page_html

# Get a specific element type's field's value.
def get_elem(in_html, in_type, in_field, in_value):
	elem_target = in_html.find(in_type, {in_field: in_value})
	return elem_target

# Parse a target group of info and get the element.
def get_target(in_html, in_list):
	target_data = get_elem(in_html, *in_list)
	return target_data

# Get a child element of a parent element.
def get_child(in_parent, in_type):
	elem_list = in_parent.findChildren(in_type, recursive=True)
	return elem_list

# Convert to PNG.
def check_image(in_image):
	image_data = PIL.Image.open(in_image)
	if not image_data.format == "PNG":
		with io.BytesIO() as handle_io:
			image_data.save(handle_io, format="png")
			return handle_io.getvalue()
	return image_data

# Get an image from a URL.
def get_image(in_url):
	image_raw = requests.get(in_url)
	image_original = check_image(io.BytesIO(image_raw.content))
	image_process = image_original
	if TO_TINY:
		image_process = tinify.from_buffer(image_original)
	image_io = io.BytesIO(image_process.to_buffer())
	page_image = reportlab.lib.utils.ImageReader(image_io)
	return page_image

#-------------------------------------------------------------------------------------------------------------------------------------------
# Functions for resuming progress.

# Load a file into a string.
def get_file(in_path):
	handle_file = open(in_path)
	file_string = handle_file.read()
	handle_file.close()
	return file_string

# Append a string to a file.
def append_file(in_path, in_string):
	handle_file = open(in_path, "a")
	handle_file.write(in_string + "\n")
	handle_file.close()
	return

# Get the last stateful URL.
def get_state():
	state_get = get_file(FILE_STATE)
	if state_get == "":
		return PAGE_START
	state_split = state_get.split("\n")
	state_pair = state_split[-2].split(", ")
	return (int(state_pair[0]), state_pair[1])

# Add the last stateful URL.
def add_state(in_counter, in_url):
	state_string = f"{in_counter}, {in_url}"
	append_file(FILE_STATE, state_string)
	return

#-------------------------------------------------------------------------------------------------------------------------------------------
# Functions for crawling pages.

# Clean artifact spacing in entries.
def clean_text(in_text):
	text_check = in_text
	while "\n" in text_check:
		text_check = text_check.replace("\n", " ")
	while "  " in text_check:
		text_check = text_check.replace("  ", " ")
	return text_check

# Get all of the current page's info that we want.
def get_info(in_url):
	page_data = get_url(in_url)
	target_comic = get_target(page_data, PAGE_TARGETS["comic"])
	target_comic_image = get_child(target_comic, "img")
	# Fix random brokey shit like an odd character and an Imgur link.
	page_image = [temp_elem.attrs["src"].replace("", "%10") for temp_elem in target_comic_image if temp_elem.get("src", None) and "imgur" not in temp_elem.get("src")]
	page_hover = [temp_elem.attrs["alt"] for temp_elem in target_comic_image if temp_elem.get("alt", None)]
	page_hover = " ".join(page_hover)
	page_hover = clean_text(page_hover)
	target_next = get_target(page_data, PAGE_TARGETS["next"])
	page_next = None
	if target_next != None:
		page_next = target_next.get("href")
	target_entry = get_target(page_data, PAGE_TARGETS["entry"])
	entry_string = ""
	for temp_p in target_entry.findChildren("p"):
		entry_string = entry_string + temp_p.text + " "
	entry_string = clean_text(entry_string)
	return [page_image, page_hover, entry_string, page_next]

#-------------------------------------------------------------------------------------------------------------------------------------------
# Functions for PDF manipulation.

# Create a PDF and set some settings we want.
def make_pdf(in_counter):
	handle_pdf = reportlab.pdfgen.canvas.Canvas(PATH_DIR + str(in_counter) + ".pdf")
	handle_font = reportlab.pdfbase.ttfonts.TTFont("Ubuntu", "Ubuntu-R.ttf")
	reportlab.pdfbase.pdfmetrics.registerFont(handle_font)
	handle_pdf.setFont("Ubuntu", FONT_SIZE)
	return handle_pdf

# Write an image to the PDF.
def write_image(in_pdf, in_url):
	image_data = get_image(in_url)
	in_pdf.setPageSize(image_data.getSize())
	in_pdf.drawImage(image_data, 0, 0)
	in_pdf.showPage()
	return

# Wrap text to a certain char width.
def wrap_text(in_text):
	wrap_list = textwrap.wrap(in_text, WRAP_SIZE)
	return wrap_list

# Write the hover text and entry to the PDF.
def write_story(in_pdf, in_hover, in_entry):
	string_list = ""
	if in_entry != "":
		string_list = list(reversed(wrap_text(in_hover)+ [" "] + wrap_text(in_entry)))
	else:
		string_list = list(reversed(wrap_text(in_hover)))
	string_max = 0
	string_big = ""
	for temp_string in string_list:
		if len(temp_string) > string_max:
			string_max = len(temp_string)
			string_big = temp_string
	string_width = reportlab.pdfbase.pdfmetrics.stringWidth(string_big, "Ubuntu", 12)
	string_count = len(string_list)
	in_pdf.setPageSize((string_width + (FONT_SIZE * 3), FONT_SIZE * string_count + FONT_PAD))
	for temp_height in reversed(range(0, string_count)):
		in_pdf.drawString(FONT_PAD, temp_height * FONT_SIZE + FONT_PAD, string_list[temp_height])
	in_pdf.showPage()
	return

#-------------------------------------------------------------------------------------------------------------------------------------------
# Main entrance function.

def main():
	state_counter, state_now = get_state()
	while True:
		# page_image, page_hover, entry_string, page_next
		page_info = get_info(state_now)
		print(f"[{state_counter}] : \"{page_info[1]}\"")
		handle_pdf = make_pdf(state_counter)
		for temp_image in page_info[0]:
			print("    " + temp_image)
			write_image(handle_pdf, temp_image)
		if ((page_info[1] != "") or (page_info[2] != "")):
			write_story(handle_pdf, page_info[1], page_info[2])
		handle_pdf.save()
		state_now = page_info[3]
		state_counter += 1
		add_state(state_counter, state_now)
	return

#-------------------------------------------------------------------------------------------------------------------------------------------
# Run the program.

if __name__ == "__main__":
	main()
	quit()

#-------------------------------------------------------------------------------------------------------------------------------------------