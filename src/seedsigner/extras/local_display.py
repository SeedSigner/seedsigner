class ST7789:
    def __init__(self, width = 240, height = 240):
        self.width = width
        self.height = height

    def show_image(self, image, x, y):
        with open('display.bmp', 'wb') as f:
            f.write(image.tobytes())
