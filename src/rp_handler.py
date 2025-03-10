# import time
# import requests
# import json
# import base64
# import uuid
# import runpod
# from runpod.serverless.utils.rp_validator import validate
# from runpod.serverless.modules.rp_logger import RunPodLogger
# from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, ContentSettings
# from requests.adapters import HTTPAdapter, Retry
# from images_utils import apply_overlay_image, remove_metadata
# from schemas.input import INPUT_SCHEMA
# import os

# blob_connect_str = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
# blob_container_name = os.environ.get('AZURE_STORAGE_CONTAINER_NAME')

# if not blob_container_name:
#     blob_container_name = 'event-images-res'

# blob_service_client = BlobServiceClient.from_connection_string(blob_connect_str)

# # BASE_URI = 'http://127.0.0.1:3000'
# BASE_URI = 'http://127.0.0.1:8188'
# VOLUME_MOUNT_PATH = '/workspacesrc'
# TIMEOUT = 600

# session = requests.Session()
# retries = Retry(total=10, backoff_factor=0.1, status_forcelist=[502, 503, 504])
# session.mount('http://', HTTPAdapter(max_retries=retries))
# logger = RunPodLogger()


# # ---------------------------------------------------------------------------- #
# #                               ComfyUI Functions                              #
# # ---------------------------------------------------------------------------- #


# def generate_blob_name(save_path):
#     """Generates a unique blob path with a new GUID if save_path is a directory."""
#     blob_name_id = str(uuid.uuid4())
#     return f"{save_path}/{blob_name_id}.png"

# def upload_image_to_blob_storage(image_path, save_path):
#     # Determine initial blob path based on whether save_path is a file or directory
#     blob_path = save_path if save_path.endswith('.jpg') or save_path.endswith('.png') else generate_blob_name(save_path)

#     # Validate image type
#     image_type = blob_path.split('.')[-1]
#     if image_type not in ['jpg', 'png']:
#         logger.error(f'Error: Invalid image type: {image_type}')
#         return f'Error: Invalid image type: {image_type}'

#     blob_client = blob_service_client.get_blob_client(container=blob_container_name, blob=blob_path)

#     # Open the image and attempt upload with retry logic
#     with open(image_path, "rb") as data:
#         for attempt in range(2):  # Attempt twice if an error occurs
#             logger.info(f'Uploading image to Azure Blob Storage started: {blob_path}')
#             try:
#                 blob_client.upload_blob(
#                     data,
#                     blob_type="BlockBlob",
#                     content_settings=ContentSettings(content_type=f'image/{image_type}')
#                 )
#                 logger.info(f'Image uploaded successfully to Azure Blob Storage: {blob_path}')
#                 break  # Exit loop if upload is successful
#             except Exception as e:
#                 if attempt == 1:  # Second attempt failed
#                     logger.error(f'Error uploading image to blob storage: {e}')
#                     return f'Error uploading image to blob storage: {e}'
#                 else:
#                     # Update blob path and client with a new GUID for retry
#                     logger.warning(f'Retry uploading image with new blob name due to error: {e}')
#                     blob_path = generate_blob_name(save_path)
#                     blob_client = blob_service_client.get_blob_client(container=blob_container_name, blob=blob_path)

#     img_blob_url = blob_client.url
#     return img_blob_url

# def wait_for_service(url):
#     retries = 0

#     while True:
#         try:
#             requests.get(url)
#             return
#         except requests.exceptions.RequestException:
#             retries += 1

#             # Only log every 15 retries so the logs don't get spammed
#             if retries % 15 == 0:
#                 logger.info(f'Service [{url}] not ready yet. Retrying...')
#         except Exception as err:
#             logger.error(f'Error: {err}')

#         time.sleep(0.2)


# def send_get_request(endpoint):
#     return session.get(
#         url=f'{BASE_URI}/{endpoint}',
#         timeout=TIMEOUT
#     )


# def send_post_request(endpoint, payload):
#     return session.post(
#         url=f'{BASE_URI}/{endpoint}',
#         json=payload,
#         timeout=TIMEOUT
#     )

# def get_txt2img_payload(workflow, payload):
#     workflow["3"]["inputs"]["seed"] = payload["seed"]
#     workflow["3"]["inputs"]["steps"] = payload["steps"]
#     workflow["3"]["inputs"]["cfg"] = payload["cfg_scale"]
#     workflow["3"]["inputs"]["sampler_name"] = payload["sampler_name"]
#     workflow["4"]["inputs"]["ckpt_name"] = payload["ckpt_name"]
#     workflow["5"]["inputs"]["batch_size"] = payload["batch_size"]
#     workflow["5"]["inputs"]["width"] = payload["width"]
#     workflow["5"]["inputs"]["height"] = payload["height"]
#     workflow["6"]["inputs"]["text"] = payload["prompt"]
#     workflow["7"]["inputs"]["text"] = payload["negative_prompt"]
#     return workflow


# def get_workflow_payload(workflow_name, payload):
#     with open(f'/workflows/{workflow_name}.json', 'r') as json_file:
#         workflow = json.load(json_file)

#     if workflow_name == 'txt2img':
#         workflow = get_txt2img_payload(workflow, payload)

#     return workflow


# def get_filenames(output):
#     for key, value in output.items():
#         if 'images' in value and isinstance(value['images'], list):
#             return value['images']


# # ---------------------------------------------------------------------------- #
# #                                RunPod Handler                                #
# # ---------------------------------------------------------------------------- #
# def handler(event):
#     try:
#         validated_input = validate(event['input'], INPUT_SCHEMA)

#         if 'errors' in validated_input:
#             return {
#                 'error': validated_input['errors']
#             }

#         payload = validated_input['validated_input']
#         save_path = payload['save_path']
#         workflow_name = payload['workflow']
#         overlay = payload['overlay']
#         frame_overlay = overlay.get('frame_img', None) if overlay is not None and 'frame_img' in overlay else None
#         logo_overlay = overlay.get('logo_img', None) if overlay is not None and 'logo_img' in overlay else None
#         logo_position = overlay.get('logo_position', None) if overlay is not None and 'logo_position' in overlay else None

#         payload = payload['payload']

#         if workflow_name == 'default':
#             workflow_name = 'txt2img'

#         logger.info(f'Workflow: {workflow_name}')
#         logger.info(f'save_path: {save_path}')
#         logger.info(f'overlay: {"True" if overlay is not None else "False"}')
#         logger.info(f'frame_overlay: {frame_overlay}')
#         logger.info(f'logo_overlay: {logo_overlay}')
#         logger.info(f'logo_position: {logo_position}')

#         if workflow_name != 'custom':
#             try:
#                 payload = get_workflow_payload(workflow_name, payload)
#             except Exception as e:
#                 logger.error(f'Unable to load workflow payload for: {workflow_name}')
#                 raise

#         logger.debug('Queuing prompt')

#         queue_response = send_post_request(
#             'prompt',
#             {
#                 'prompt': payload
#             }
#         )

#         resp_json = queue_response.json()

#         if queue_response.status_code == 200:
#             prompt_id = resp_json['prompt_id']
#             logger.info(f'Prompt queued successfully: {prompt_id}')

#             while True:
#                 logger.debug(f'Getting status of prompt: {prompt_id}')
#                 r = send_get_request(f'history/{prompt_id}')
#                 resp_json = r.json()

#                 if r.status_code == 200 and len(resp_json):
#                     break

#                 time.sleep(0.2)

#             if len(resp_json[prompt_id]['outputs']):
#                 logger.info(f'Images generated successfully for prompt: {prompt_id}')
#                 image_filenames = get_filenames(resp_json[prompt_id]['outputs'])
#                 images = []

#                 for image_filename in image_filenames:
#                     filename = image_filename['filename']
#                     image_path = f'{VOLUME_MOUNT_PATH}/ComfyUI/output/{filename}'
#                     original_image_path = image_path

#                     # remove metadata from the image
#                     try:
#                         logger.info(f'Removing metadata from the image')
#                         remove_metadata(image_path)
#                     except Exception as e:
#                         logger.error(f'Error removing metadata from the image: {e}')

#                     # apply frame overlay to the image if the frame_overlay is exsist by the schema:
#                     try:
#                         if frame_overlay is not None and frame_overlay != '':
#                             logger.info(f'Applying frame overlay')
#                             # check if the frame_overlay is a directory
#                             if frame_overlay.endswith('.png'):
#                                 frame_img = frame_overlay
#                             # else frame_overlay check if base64 image
#                             elif frame_overlay.startswith('data:image/png;base64,'):
#                                 frame_img = frame_overlay
#                             apply_overlay_image(image_path, frame_img, image_path, mode='stretch')
#                     except Exception as e:
#                         logger.error(f'Error applying frame overlay: {e}')

#                     # apply logo overlay to the image if the logo_overlay is not None
#                     try:
#                         if logo_overlay is not None and logo_overlay != '':
#                             logger.info(f'Applying logo overlay')
#                             # check if the logo_overlay is a directory
#                             if logo_overlay.endswith('.png'):
#                                 logo_img = logo_overlay
#                             # else logo_overlay check if base64 image
#                             elif logo_overlay.startswith('data:image/png;base64,'):
#                                 logo_img = logo_overlay
#                             apply_overlay_image(image_path, logo_img, image_path, mode='append', position=logo_position, padding=25)
#                     except Exception as e:
#                         logger.error(f'Error applying logo overlay: {e}')

#                     # deploy each image to the Azure blob storage
#                     if save_path is not None and save_path != '':
#                         logger.info(f'Uploading image to Azure Blob Storage: {save_path}')
#                         img_blob_url = upload_image_to_blob_storage(image_path, save_path)
#                         images.append(img_blob_url)
#                     else:
#                         logger.info(f'No save path provided, returning base64 image')
#                         with open(image_path, 'rb') as image_file:
#                             images.append(base64.b64encode(image_file.read()).decode('utf-8'))

#                 return {
#                     'images': images
#                 }

#             else:
#                 raise RuntimeError('No output found, please ensure that the model is correct and that it exists')
#         else:
#             logger.error(f'HTTP Status code: {queue_response.status_code}')
#             logger.error(json.dumps(resp_json, indent=4, default=str))
#             return resp_json
#     except Exception as e:
#         raise


# if __name__ == '__main__':
#     wait_for_service(url=f'{BASE_URI}/system_stats')
#     logger.info('[INFO] ComfyUI API is ready')
#     logger.info('[INFO] Starting RunPod Serverless...')
#     runpod.serverless.start(
#         {
#             'handler': handler
#         }
#     )


#####

import runpod
from runpod.serverless.utils import rp_upload
import json
import urllib.request
import urllib.parse
import time
import os
import requests
import base64
from io import BytesIO

# Time to wait between API check attempts in milliseconds
COMFY_API_AVAILABLE_INTERVAL_MS = 50
# Maximum number of API check attempts
COMFY_API_AVAILABLE_MAX_RETRIES = 500
# Time to wait between poll attempts in milliseconds
COMFY_POLLING_INTERVAL_MS = int(os.environ.get("COMFY_POLLING_INTERVAL_MS", 250))
# Maximum number of poll attempts
COMFY_POLLING_MAX_RETRIES = int(os.environ.get("COMFY_POLLING_MAX_RETRIES", 500))
# Host where ComfyUI is running
COMFY_HOST = "127.0.0.1:8188"
# Enforce a clean state after each job is done
# see https://docs.runpod.io/docs/handler-additional-controls#refresh-worker
REFRESH_WORKER = os.environ.get("REFRESH_WORKER", "false").lower() == "true"


def validate_input(job_input):
    """
    Validates the input for the handler function.

    Args:
        job_input (dict): The input data to validate.

    Returns:
        tuple: A tuple containing the validated data and an error message, if any.
               The structure is (validated_data, error_message).
    """
    # Validate if job_input is provided
    if job_input is None:
        return None, "Please provide input"

    # Check if input is a string and try to parse it as JSON
    if isinstance(job_input, str):
        try:
            job_input = json.loads(job_input)
        except json.JSONDecodeError:
            return None, "Invalid JSON format in input"

    # Validate 'workflow' in input
    workflow = job_input.get("workflow")
    if workflow is None:
        return None, "Missing 'workflow' parameter"

    # Validate 'images' in input, if provided
    images = job_input.get("images")
    if images is not None:
        if not isinstance(images, list) or not all(
            "name" in image and "image" in image for image in images
        ):
            return (
                None,
                "'images' must be a list of objects with 'name' and 'image' keys",
            )

    # Return validated data and no error
    return {"workflow": workflow, "images": images}, None


def check_server(url, retries=500, delay=50):
    """
    Check if a server is reachable via HTTP GET request

    Args:
    - url (str): The URL to check
    - retries (int, optional): The number of times to attempt connecting to the server. Default is 50
    - delay (int, optional): The time in milliseconds to wait between retries. Default is 500

    Returns:
    bool: True if the server is reachable within the given number of retries, otherwise False
    """

    for i in range(retries):
        try:
            response = requests.get(url)

            # If the response status code is 200, the server is up and running
            if response.status_code == 200:
                print(f"runpod-worker-comfy - API is reachable")
                return True
        except requests.RequestException as e:
            # If an exception occurs, the server may not be ready
            pass

        # Wait for the specified delay before retrying
        time.sleep(delay / 1000)

    print(
        f"runpod-worker-comfy - Failed to connect to server at {url} after {retries} attempts."
    )
    return False


def upload_images(images):
    """
    Upload a list of base64 encoded images to the ComfyUI server using the /upload/image endpoint.

    Args:
        images (list): A list of dictionaries, each containing the 'name' of the image and the 'image' as a base64 encoded string.
        server_address (str): The address of the ComfyUI server.

    Returns:
        list: A list of responses from the server for each image upload.
    """
    if not images:
        return {"status": "success", "message": "No images to upload", "details": []}

    responses = []
    upload_errors = []

    print(f"runpod-worker-comfy - image(s) upload")

    for image in images:
        name = image["name"]
        image_data = image["image"]
        blob = base64.b64decode(image_data)

        # Prepare the form data
        files = {
            "image": (name, BytesIO(blob), "image/png"),
            "overwrite": (None, "true"),
        }

        # POST request to upload the image
        response = requests.post(f"http://{COMFY_HOST}/upload/image", files=files)
        if response.status_code != 200:
            upload_errors.append(f"Error uploading {name}: {response.text}")
        else:
            responses.append(f"Successfully uploaded {name}")

    if upload_errors:
        print(f"runpod-worker-comfy - image(s) upload with errors")
        return {
            "status": "error",
            "message": "Some images failed to upload",
            "details": upload_errors,
        }

    print(f"runpod-worker-comfy - image(s) upload complete")
    return {
        "status": "success",
        "message": "All images uploaded successfully",
        "details": responses,
    }


def queue_workflow(workflow):
    """
    Queue a workflow to be processed by ComfyUI

    Args:
        workflow (dict): A dictionary containing the workflow to be processed

    Returns:
        dict: The JSON response from ComfyUI after processing the workflow
    """

    # The top level element "prompt" is required by ComfyUI
    data = json.dumps({"prompt": workflow}).encode("utf-8")

    req = urllib.request.Request(f"http://{COMFY_HOST}/prompt", data=data)
    return json.loads(urllib.request.urlopen(req).read())


def get_history(prompt_id):
    """
    Retrieve the history of a given prompt using its ID

    Args:
        prompt_id (str): The ID of the prompt whose history is to be retrieved

    Returns:
        dict: The history of the prompt, containing all the processing steps and results
    """
    with urllib.request.urlopen(f"http://{COMFY_HOST}/history/{prompt_id}") as response:
        return json.loads(response.read())


def base64_encode(img_path):
    """
    Returns base64 encoded image.

    Args:
        img_path (str): The path to the image

    Returns:
        str: The base64 encoded image
    """
    with open(img_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return f"{encoded_string}"


def process_output_images(outputs, job_id):
    """
    This function takes the "outputs" from image generation and the job ID,
    then determines the correct way to return the image, either as a direct URL
    to an AWS S3 bucket or as a base64 encoded string, depending on the
    environment configuration.

    Args:
        outputs (dict): A dictionary containing the outputs from image generation,
                        typically includes node IDs and their respective output data.
        job_id (str): The unique identifier for the job.

    Returns:
        dict: A dictionary with the status ('success' or 'error') and the message,
              which is either the URL to the image in the AWS S3 bucket or a base64
              encoded string of the image. In case of error, the message details the issue.

    The function works as follows:
    - It first determines the output path for the images from an environment variable,
      defaulting to "/comfyui/output" if not set.
    - It then iterates through the outputs to find the filenames of the generated images.
    - After confirming the existence of the image in the output folder, it checks if the
      AWS S3 bucket is configured via the BUCKET_ENDPOINT_URL environment variable.
    - If AWS S3 is configured, it uploads the image to the bucket and returns the URL.
    - If AWS S3 is not configured, it encodes the image in base64 and returns the string.
    - If the image file does not exist in the output folder, it returns an error status
      with a message indicating the missing image file.
    """

    # The path where ComfyUI stores the generated images
    COMFY_OUTPUT_PATH = os.environ.get("COMFY_OUTPUT_PATH", "/comfyui/output")

    output_images = {}

    for node_id, node_output in outputs.items():
        if "images" in node_output:
            for image in node_output["images"]:
                output_images = os.path.join(image["subfolder"], image["filename"])

    print(f"runpod-worker-comfy - image generation is done")

    # expected image output folder
    local_image_path = f"{COMFY_OUTPUT_PATH}/{output_images}"

    print(f"runpod-worker-comfy - {local_image_path}")

    # The image is in the output folder
    if os.path.exists(local_image_path):
        if os.environ.get("BUCKET_ENDPOINT_URL", False):
            # URL to image in AWS S3
            image = rp_upload.upload_image(job_id, local_image_path)
            print(
                "runpod-worker-comfy - the image was generated and uploaded to AWS S3"
            )
        else:
            # base64 image
            image = base64_encode(local_image_path)
            print(
                "runpod-worker-comfy - the image was generated and converted to base64"
            )

        return {
            "status": "success",
            "message": image,
        }
    else:
        print("runpod-worker-comfy - the image does not exist in the output folder")
        return {
            "status": "error",
            "message": f"the image does not exist in the specified output folder: {local_image_path}",
        }


def handler(job):
    """
    The main function that handles a job of generating an image.

    This function validates the input, sends a prompt to ComfyUI for processing,
    polls ComfyUI for result, and retrieves generated images.

    Args:
        job (dict): A dictionary containing job details and input parameters.

    Returns:
        dict: A dictionary containing either an error message or a success status with generated images.
    """
    job_input = job["input"]

    # Make sure that the input is valid
    validated_data, error_message = validate_input(job_input)
    if error_message:
        return {"error": error_message}

    # Extract validated data
    workflow = validated_data["workflow"]
    images = validated_data.get("images")

    # Make sure that the ComfyUI API is available
    check_server(
        f"http://{COMFY_HOST}",
        COMFY_API_AVAILABLE_MAX_RETRIES,
        COMFY_API_AVAILABLE_INTERVAL_MS,
    )

    # Upload images if they exist
    upload_result = upload_images(images)

    if upload_result["status"] == "error":
        return upload_result

    # Queue the workflow
    try:
        queued_workflow = queue_workflow(workflow)
        prompt_id = queued_workflow["prompt_id"]
        print(f"runpod-worker-comfy - queued workflow with ID {prompt_id}")
    except Exception as e:
        return {"error": f"Error queuing workflow: {str(e)}"}

    # Poll for completion
    print(f"runpod-worker-comfy - wait until image generation is complete")
    retries = 0
    try:
        while retries < COMFY_POLLING_MAX_RETRIES:
            history = get_history(prompt_id)

            # Exit the loop if we have found the history
            if prompt_id in history and history[prompt_id].get("outputs"):
                break
            else:
                # Wait before trying again
                time.sleep(COMFY_POLLING_INTERVAL_MS / 1000)
                retries += 1
        else:
            return {"error": "Max retries reached while waiting for image generation"}
    except Exception as e:
        return {"error": f"Error waiting for image generation: {str(e)}"}

    # Get the generated image and return it as URL in an AWS bucket or as base64
    images_result = process_output_images(history[prompt_id].get("outputs"), job["id"])

    result = {**images_result, "refresh_worker": REFRESH_WORKER}

    return result


# Start the handler only if this script is run directly
if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})


