from google.cloud import vision

# Initialize the Google Cloud Vision client
client = vision.ImageAnnotatorClient()

# Replace 'your-image-file.jpg' with a path to an image on your EC2 instance
image_path = '/home/ec2-user/414516 18YXV BELT 115CM_2 4.png'

# Read the image file
with open(image_path, 'rb') as image_file:
    content = image_file.read()

# Construct an image instance
image = vision.Image(content=content)

# Perform text detection
response = client.text_detection(image=image)
texts = response.text_annotations

# Print detected text
if texts:
    print("Detected text:")
    for text in texts:
        print(text.description)
else:
    print("No text detected.")

# Error handling
if response.error.message:
    raise Exception(f'{response.error.message}')
