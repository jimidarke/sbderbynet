import os
import sys
import time
import logging
import spidev as SPI
#sys.path.append("..")
import LCD_2inch
from PIL import Image, ImageDraw, ImageFont

# Raspberry Pi pin configuration:
RST = 27
DC = 25
BL = 18
bus = 0
device = 0
logging.basicConfig(level=logging.DEBUG)

def drawSample():
    try:
        # Clear display.
        disp.clear()
        #Set the backlight to 100
        disp.bl_DutyCycle(100)

        # Create blank image for drawing.
        image1 = Image.new("RGB", (disp.height, disp.width ), "WHITE")
        draw = ImageDraw.Draw(image1)
        logging.info("draw point")

        draw.rectangle((5,10,6,11), fill = "BLACK")
        draw.rectangle((5,25,7,27), fill = "BLACK")
        draw.rectangle((5,40,8,43), fill = "BLACK")
        draw.rectangle((5,55,9,59), fill = "BLACK")

        logging.info("draw line")
        draw.line([(20, 10),(70, 60)], fill = "RED",width = 1)
        draw.line([(70, 10),(20, 60)], fill = "RED",width = 1)
        draw.line([(170,15),(170,55)], fill = "RED",width = 1)
        draw.line([(150,35),(190,35)], fill = "RED",width = 1)

        logging.info("draw rectangle")
        draw.rectangle([(20,10),(70,60)],fill = "WHITE",outline="BLUE")
        draw.rectangle([(85,10),(130,60)],fill = "BLUE")

        logging.info("draw circle")
        draw.arc((150,15,190,55),0, 360, fill =(0,255,0))
        draw.ellipse((150,65,190,105), fill = (0,255,0))

        logging.info("draw text")
        Font1 = ImageFont.truetype("Font01.ttf",25)
        Font2 = ImageFont.truetype("Font01.ttf",35)
        Font3 = ImageFont.truetype("Font02.ttf",32)

        draw.rectangle([(0,65),(140,100)],fill = "WHITE")
        draw.text((5, 68), 'Hello world', fill = "BLACK",font=Font1)
        draw.rectangle([(0,115),(190,160)],fill = "RED")
        draw.text((5, 118), 'WaveShare', fill = "WHITE",font=Font2)
        draw.text((5, 160), '1234567890', fill = "GREEN",font=Font3)
        text= u"微雪电子"
        draw.text((5, 200),text, fill = "BLUE",font=Font3)
        image1=image1.rotate(270)
        disp.ShowImage(image1)
        time.sleep(10)
        logging.info("show image")
        image = Image.open('LCD_2inch.jpg')
        image = image.rotate(90)
        disp.ShowImage(image)
        time.sleep(15)
        disp.module_exit()
        logging.info("quit:")
    except IOError as e:
        logging.info(e)
    except KeyboardInterrupt:
        disp.module_exit()
        logging.info("quit:")
        exit()


def display_hello_world_fullsize_landscape():
    '''
    Display "Hello, World!" on the screen in landscape mode big as possible
    '''
    # Clear display.
    disp.clear()
    #Set the backlight to 100
    disp.bl_DutyCycle(100)
    try:
        # Create blank image for drawing.
        image1 = Image.new("RGB", (disp.height, disp.width ), "BLACK")
        draw = ImageDraw.Draw(image1)
        logging.info("draw text")
        Font1 = ImageFont.truetype("Font01.ttf",35)
        draw.text((0, 100), 'Hello world \nHows it going yall', fill = "WHITE",font=Font1) # (x,y) x=0 is left x=320 is right, y=0 is top y=240 is bottom
        
        image1=image1.rotate(180)
        disp.ShowImage(image1)
        time.sleep(5)
        disp.module_exit()
        logging.info("quit:")
    except IOError as e:
        logging.info(e)
    except KeyboardInterrupt:
        disp.module_exit()
        logging.info("quit:")
        exit()

def draw_table_sample():
    image = Image.new("RGB", (disp.height, disp.width), "WHITE")
    draw = ImageDraw.Draw(image)
    font =  ImageFont.truetype("Font00.ttf",20)
    #font = ImageFont.load_default() 
    
    # Define table content
    rows = [
        ["ID", "Name", "Score"],
        ["1", "Alice", "85"],
        ["2", "Bob", "90"],
        ["3", "Charlie", "78"],
    ]

    # Table layout
    col_widths = [60, 100, 80]  # Adjust column widths as needed
    row_height = 30
    x_start = 10
    y_start = 10
    # Draw table
    for row_idx, row in enumerate(rows):
        y = y_start + row_idx * row_height
        x = x_start
        for col_idx, cell in enumerate(row):
            draw.rectangle([x, y, x + col_widths[col_idx], y + row_height], outline="BLACK", width=1)
            draw.text((x + 5, y + 5), cell, font=font, fill="BLACK")
            x += col_widths[col_idx]
    image = image.rotate(180)
    disp.clear()
    disp.bl_DutyCycle(100)
    disp.ShowImage(image)
    time.sleep(25)

def draw_race_table(disp, race_stats, current_time, lane_statuses, pinny_ids, toggle_states, last_run_times):
    image = Image.new("RGB", (disp.height, disp.width), "WHITE")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("Font00.ttf", 20)

    col_widths = [79, 79, 79, 79]  # Adjusted column widths
    row_height = 40
    x_start = 0
    y_start = 0

    # Row 1: Merged first three columns for race stats, last column for time
    draw.rectangle([x_start, y_start, x_start + sum(col_widths[:3]), y_start + row_height], outline="BLACK", width=2)
    draw.text((x_start + 5, y_start + 5), race_stats, font=font, fill="BLACK")
    
    x = x_start + sum(col_widths[:3])
    draw.rectangle([x, y_start, x + col_widths[3], y_start + row_height], outline="BLACK", width=2)
    draw.text((x + 5, y_start + 5), current_time, font=font, fill="BLACK")

    # Row 2: Static lane labels
    y = y_start + row_height
    for i, lane in enumerate(["Lane 1", "Lane 2", "Lane 3", "Lane 4"]):
        x = x_start + sum(col_widths[:i])
        draw.rectangle([x, y, x + col_widths[i], y + row_height], outline="BLACK", width=1)
        draw.text((x + 5, y + 5), lane, font=font, fill="BLACK")
    
    # Row 3: Online/Offline status with background colors
    y += row_height
    for i, status in enumerate(lane_statuses):
        x = x_start + sum(col_widths[:i])
        color = "GREEN" if status == "Online" else "RED"
        draw.rectangle([x, y, x + col_widths[i], y + row_height], fill=color, outline="BLACK", width=1)
        draw.text((x + 5, y + 5), status, font=font, fill="WHITE")
    
    # Row 4: PINNYIDs
    y += row_height
    for i, pinny in enumerate(pinny_ids):
        x = x_start + sum(col_widths[:i])
        draw.rectangle([x, y, x + col_widths[i], y + row_height], outline="BLACK", width=1)
        draw.text((x + 5, y + 5), pinny, font=font, fill="BLACK")
    
    # Row 5: Toggle state with background colors
    y += row_height
    for i, toggle in enumerate(toggle_states):
        x = x_start + sum(col_widths[:i])
        color = "GREEN" if toggle == "On" else "RED"
        draw.rectangle([x, y, x + col_widths[i], y + row_height], fill=color, outline="BLACK", width=1)
        draw.text((x + 5, y + 5), toggle, font=font, fill="WHITE")
    
    # Row 6: Last run time
    y += row_height
    for i, run_time in enumerate(last_run_times):
        x = x_start + sum(col_widths[:i])
        draw.rectangle([x, y, x + col_widths[i], y + row_height], outline="BLACK", width=1)
        draw.text((x + 5, y + 5), run_time, font=font, fill="BLACK")
    
    # Rotate for display
    image = image.rotate(180)
    disp.clear()
    disp.bl_DutyCycle(100)
    disp.ShowImage(image)


disp = LCD_2inch.LCD_2inch(spi=SPI.SpiDev(bus, device),spi_freq=10000000,rst=RST,dc=DC,bl=BL)
#disp = LCD_2inch.LCD_2inch()
# Initialize library.
disp.Init()
disp.clear()

#drawSample()
#display_hello_world_fullsize_landscape()
#draw_table_sample()
#disp.module_exit()

draw_race_table(disp, "Round 1 - Age 10", "12:45:32", ["Online", "Offline", "Online", "Offline"], ["1234", "5678", "9101", "1121"], ["On", "Off", "On", "Off"], ["02:45", "03:12", "01:58", "02:30"])
time.sleep(30)
disp.module_exit()
