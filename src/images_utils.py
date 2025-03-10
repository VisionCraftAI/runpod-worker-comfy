from PIL import Image
import requests
from io import BytesIO

def apply_overlay_image(source_img_path, frame_img_path, output_path, mode='stretch', position='top-middle', padding=10):
    """
    Apply a frame overlay onto a source image with options for stretching or appending the frame with padding from the borders.
    
    Parameters:
    source_img_path (str): Path to the source image.
    frame_img_path (str): Path to the frame image (PNG with transparency).
    output_path (str): Path where the output image will be saved.
    mode (str): 'stretch' to resize the frame to source image size, 'append' to append at its original size with padding.
    position (str): Position to append the frame with padding ['top-middle', 'top-left', 'top-right', 'bottom-middle', 'bottom-left', 'bottom-right'].
    """
    # Load the source and frame images

    source_img = Image.open(source_img_path)

    # check if frame_img_path is url, and download the image or use the image from the local path
    if frame_img_path.startswith('http'):
        try:
            response = requests.get(frame_img_path)
            frame_img = Image.open(BytesIO(response.content))
        except Exception as e:
            # Handle the exception here
            print(f"Error loading frame image form url: {e}")
            # Set frame_img to None or any default image
            frame_img = None
    else:
        frame_img = Image.open(frame_img_path)
    
    # Ensure both images are in RGBA mode to handle transparency
    if source_img.mode != 'RGBA':
        source_img = source_img.convert('RGBA')
    if frame_img.mode != 'RGBA':
        frame_img = frame_img.convert('RGBA')

    if mode == 'stretch':
        # Resize the frame image to match the dimensions of the source image
        frame_img = frame_img.resize(source_img.size, Image.LANCZOS)
    else:

        # Create a new image with the size of the source image
        result_img = Image.new('RGBA', source_img.size)

        # Calculate position for appending with padding
        if 'top' in position:
            y = padding
        elif 'bottom' in position:
            y = source_img.height - frame_img.height - padding
        
        if 'left' in position:
            x = padding
        elif 'middle' in position:
            x = (source_img.width - frame_img.width) // 2
        elif 'right' in position:
            x = source_img.width - frame_img.width - padding

        # Paste the source image into the result image
        result_img.paste(source_img, (0, 0))

        # Paste the frame image at the calculated position with transparency mask
        result_img.paste(frame_img, (x, y), frame_img)

        # Set result_img to combined_img to be saved later
        combined_img = result_img

    if mode == 'stretch':
        # Composite the frame on top of the source image
        combined_img = Image.alpha_composite(source_img, frame_img)

    # Convert to RGB before saving as JPEG
    if output_path.lower().endswith('.jpg') or output_path.lower().endswith('.jpeg'):
        combined_img = combined_img.convert('RGB')
    # Save the output image
    combined_img.save(output_path)
    return combined_img

# Example usage
# frame_img = "C:\\Users\\alond\\Downloads\\filters-images\\filters\\adventurer\\2126012_7415f.png"
# source_img = "C:\\Users\\alond\\Downloads\\filters-images\\filters\\adventurer\\default.jpg"
# output_img = "C:\\Users\\alond\\Downloads\\filters-images\\filters\\adventurer\\default_with_frame.jpg"
# applay frame:
# apply_overlay_image(source_img, frame_img, output_img, mode='stretch')
# applay logo:
# apply_overlay_image(source_img, frame_img, output_img, mode='append', position='bottom-right', padding=100)


from PIL import Image, ImageDraw, ImageFont

def apply_frame(image_path, output_path, frame_widths, frame_color='black', texts=None, text_colors=None, font_sizes=None, font_path=None):
    """
    Apply a frame to an image with different widths for top, bottom, left, and right.
    Add rotated text to the left and right sides of the frame with customizable colors and font sizes.

    Parameters:
    image_path (str): Path to the input image.
    output_path (str): Path where the output image will be saved.
    frame_widths (dict): A dictionary with keys 'top', 'bottom', 'left', 'right' specifying the frame widths.
    frame_color (str): Color of the frame.
    texts (dict, optional): Dictionary with keys 'top', 'bottom', 'left', 'right' specifying the text for each side.
    text_colors (dict, optional): Dictionary with keys 'top', 'bottom', 'left', 'right' specifying the text colors for each side.
    font_sizes (dict, optional): Dictionary with keys 'top', 'bottom', 'left', 'right' specifying the font sizes for each side.
    font_path (str, optional): Path to a custom font file.
    """
    # Load the image
    img = Image.open(image_path)

    # Convert image to RGB if it's not already to avoid palette issues
    if img.mode != 'RGB':
        img = img.convert('RGB')

    original_size = img.size

    # Create a draw object to modify the image
    draw = ImageDraw.Draw(img)

    # Draw frame directly on the image
    top_width = frame_widths.get('top', 0)
    bottom_width = frame_widths.get('bottom', 0)
    left_width = frame_widths.get('left', 0)
    right_width = frame_widths.get('right', 0)

    draw.rectangle([0, 0, original_size[0], top_width], fill=frame_color)  # Top frame
    draw.rectangle([0, 0, left_width, original_size[1]], fill=frame_color)  # Left frame
    draw.rectangle([0, original_size[1] - bottom_width, original_size[0], original_size[1]], fill=frame_color)  # Bottom frame
    draw.rectangle([original_size[0] - right_width, 0, original_size[0], original_size[1]], fill=frame_color)  # Right frame

    # Draw text if specified
    if texts:
        for side, text in texts.items():
            side_font_size = font_sizes.get(side, 20)  # Default font size if not specified
            if font_path:
                font = ImageFont.truetype(font_path, side_font_size)
            else:
                font = ImageFont.load_default(side_font_size)

            text_color = text_colors.get(side, 'white')  # Default color is white if not specified
            _, _, text_width, text_height = draw.textbbox((0, 0), text=text, font=font)

            if side in ['left', 'right']:  # Rotate text for left and right sides
                text_image = Image.new('RGBA', (text_width, text_height), (255, 255, 255, 0))
                text_draw = ImageDraw.Draw(text_image)
                text_draw.text((0, 0), text, font=font, fill=text_color)
                text_image = text_image.rotate(90, expand=1)
                if side == 'left':
                    img.paste(text_image, (int(left_width / 2 - text_height / 2), int(original_size[1] / 2 - text_width / 2)), text_image)
                else:
                    img.paste(text_image, (int(original_size[0] - right_width / 2 - text_height / 2), int(original_size[1] / 2 - text_width / 2)), text_image)
            else:
                text_xy = {
                    'top': ((original_size[0] - text_width) / 2, (top_width - text_height) / 2),
                    'bottom': ((original_size[0] - text_width) / 2, original_size[1] - bottom_width + (bottom_width - text_height) / 2),
                }[side]
                draw.text(text_xy, text, font=font, fill=text_color)

    # Save the modified image to the specified output path
    img.save(output_path)


# Example usage
# adventurer_img = "C:\\Users\\alond\\Downloads\\filters-images\\filters\\adventurer\\default.jpg"
# output_img = "C:\\Users\\alond\\Downloads\\filters-images\\filters\\adventurer\\default_with_border.jpg"

# apply_frame(image_path=adventurer_img,
#             output_path=output_img,
#             frame_widths={'top': 30, 'bottom': 60, 'left': 30, 'right': 30},
#             frame_color='white',
#             texts={'top': "",
#                    'bottom': "Mitzi & Pizi wedding 2024",
#                    'right': "Elad Phothoboot 2024"
#                    },
#             text_colors={'top': 'black', 'bottom': 'black', 'left': 'grey', 'right': 'black'},
#             font_path=None,
#             font_sizes={'top': 30, 'bottom': 30, 'left': 25, 'right': 14},
#             )


# remove metadata from image
def remove_metadata(image_path):
    """
    Remove metadata from an image and overide it.

    Parameters:
    image_path (str): Path to the input image.
    """
    with Image.open(image_path) as img:
        # Create a new image with the same size and mode
        new_img = Image.new(img.mode, img.size)
        new_img.putdata(list(img.getdata()))

        # Save the new image, which should strip away the metadata
        new_img.save(image_path)