import time
import requests
import json
import base64
import uuid
import runpod
from runpod.serverless.utils.rp_validator import validate
from runpod.serverless.modules.rp_logger import RunPodLogger
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, ContentSettings
from requests.adapters import HTTPAdapter, Retry
from images_utils import apply_overlay_image, remove_metadata
from schemas.input import INPUT_SCHEMA
import os

blob_connect_str = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
blob_container_name = os.environ.get('AZURE_STORAGE_CONTAINER_NAME')

if not blob_container_name:
    blob_container_name = 'event-images-res'

blob_service_client = BlobServiceClient.from_connection_string(blob_connect_str)

# BASE_URI = 'http://127.0.0.1:3000'
BASE_URI = 'http://127.0.0.1:8188'
VOLUME_MOUNT_PATH = '/workspacesrc'
TIMEOUT = 600

session = requests.Session()
retries = Retry(total=10, backoff_factor=0.1, status_forcelist=[502, 503, 504])
session.mount('http://', HTTPAdapter(max_retries=retries))
logger = RunPodLogger()


# ---------------------------------------------------------------------------- #
#                               ComfyUI Functions                              #
# ---------------------------------------------------------------------------- #


def generate_blob_name(save_path):
    """Generates a unique blob path with a new GUID if save_path is a directory."""
    blob_name_id = str(uuid.uuid4())
    return f"{save_path}/{blob_name_id}.png"

def upload_image_to_blob_storage(image_path, save_path):
    # Determine initial blob path based on whether save_path is a file or directory
    blob_path = save_path if save_path.endswith('.jpg') or save_path.endswith('.png') else generate_blob_name(save_path)

    # Validate image type
    image_type = blob_path.split('.')[-1]
    if image_type not in ['jpg', 'png']:
        logger.error(f'Error: Invalid image type: {image_type}')
        return f'Error: Invalid image type: {image_type}'

    blob_client = blob_service_client.get_blob_client(container=blob_container_name, blob=blob_path)

    # Open the image and attempt upload with retry logic
    with open(image_path, "rb") as data:
        for attempt in range(2):  # Attempt twice if an error occurs
            logger.info(f'Uploading image to Azure Blob Storage started: {blob_path}')
            try:
                blob_client.upload_blob(
                    data,
                    blob_type="BlockBlob",
                    content_settings=ContentSettings(content_type=f'image/{image_type}')
                )
                logger.info(f'Image uploaded successfully to Azure Blob Storage: {blob_path}')
                break  # Exit loop if upload is successful
            except Exception as e:
                if attempt == 1:  # Second attempt failed
                    logger.error(f'Error uploading image to blob storage: {e}')
                    return f'Error uploading image to blob storage: {e}'
                else:
                    # Update blob path and client with a new GUID for retry
                    logger.warning(f'Retry uploading image with new blob name due to error: {e}')
                    blob_path = generate_blob_name(save_path)
                    blob_client = blob_service_client.get_blob_client(container=blob_container_name, blob=blob_path)

    img_blob_url = blob_client.url
    return img_blob_url

def wait_for_service(url):
    retries = 0

    while True:
        try:
            requests.get(url)
            return
        except requests.exceptions.RequestException:
            retries += 1

            # Only log every 15 retries so the logs don't get spammed
            if retries % 15 == 0:
                logger.info(f'Service [{url}] not ready yet. Retrying...')
        except Exception as err:
            logger.error(f'Error: {err}')

        time.sleep(0.2)


def send_get_request(endpoint):
    return session.get(
        url=f'{BASE_URI}/{endpoint}',
        timeout=TIMEOUT
    )


def send_post_request(endpoint, payload):
    return session.post(
        url=f'{BASE_URI}/{endpoint}',
        json=payload,
        timeout=TIMEOUT
    )

def get_txt2img_payload(workflow, payload):
    workflow["3"]["inputs"]["seed"] = payload["seed"]
    workflow["3"]["inputs"]["steps"] = payload["steps"]
    workflow["3"]["inputs"]["cfg"] = payload["cfg_scale"]
    workflow["3"]["inputs"]["sampler_name"] = payload["sampler_name"]
    workflow["4"]["inputs"]["ckpt_name"] = payload["ckpt_name"]
    workflow["5"]["inputs"]["batch_size"] = payload["batch_size"]
    workflow["5"]["inputs"]["width"] = payload["width"]
    workflow["5"]["inputs"]["height"] = payload["height"]
    workflow["6"]["inputs"]["text"] = payload["prompt"]
    workflow["7"]["inputs"]["text"] = payload["negative_prompt"]
    return workflow


def get_workflow_payload(workflow_name, payload):
    with open(f'/workflows/{workflow_name}.json', 'r') as json_file:
        workflow = json.load(json_file)

    if workflow_name == 'txt2img':
        workflow = get_txt2img_payload(workflow, payload)

    return workflow


def get_filenames(output):
    for key, value in output.items():
        if 'images' in value and isinstance(value['images'], list):
            return value['images']


# ---------------------------------------------------------------------------- #
#                                RunPod Handler                                #
# ---------------------------------------------------------------------------- #
def handler(event):
    try:
        validated_input = validate(event['input'], INPUT_SCHEMA)

        if 'errors' in validated_input:
            return {
                'error': validated_input['errors']
            }

        payload = validated_input['validated_input']
        save_path = payload['save_path']
        workflow_name = payload['workflow']
        overlay = payload['overlay']
        frame_overlay = overlay.get('frame_img', None) if overlay is not None and 'frame_img' in overlay else None
        logo_overlay = overlay.get('logo_img', None) if overlay is not None and 'logo_img' in overlay else None
        logo_position = overlay.get('logo_position', None) if overlay is not None and 'logo_position' in overlay else None

        payload = payload['payload']

        if workflow_name == 'default':
            workflow_name = 'txt2img'

        logger.info(f'Workflow: {workflow_name}')
        logger.info(f'save_path: {save_path}')
        logger.info(f'overlay: {"True" if overlay is not None else "False"}')
        logger.info(f'frame_overlay: {frame_overlay}')
        logger.info(f'logo_overlay: {logo_overlay}')
        logger.info(f'logo_position: {logo_position}')

        if workflow_name != 'custom':
            try:
                payload = get_workflow_payload(workflow_name, payload)
            except Exception as e:
                logger.error(f'Unable to load workflow payload for: {workflow_name}')
                raise

        logger.debug('Queuing prompt')

        queue_response = send_post_request(
            'prompt',
            {
                'prompt': payload
            }
        )

        resp_json = queue_response.json()

        if queue_response.status_code == 200:
            prompt_id = resp_json['prompt_id']
            logger.info(f'Prompt queued successfully: {prompt_id}')

            while True:
                logger.debug(f'Getting status of prompt: {prompt_id}')
                r = send_get_request(f'history/{prompt_id}')
                resp_json = r.json()

                if r.status_code == 200 and len(resp_json):
                    break

                time.sleep(0.2)

            if len(resp_json[prompt_id]['outputs']):
                logger.info(f'Images generated successfully for prompt: {prompt_id}')
                image_filenames = get_filenames(resp_json[prompt_id]['outputs'])
                images = []

                for image_filename in image_filenames:
                    filename = image_filename['filename']
                    image_path = f'{VOLUME_MOUNT_PATH}/ComfyUI/output/{filename}'
                    original_image_path = image_path

                    # remove metadata from the image
                    try:
                        logger.info(f'Removing metadata from the image')
                        remove_metadata(image_path)
                    except Exception as e:
                        logger.error(f'Error removing metadata from the image: {e}')

                    # apply frame overlay to the image if the frame_overlay is exsist by the schema:
                    try:
                        if frame_overlay is not None and frame_overlay != '':
                            logger.info(f'Applying frame overlay')
                            # check if the frame_overlay is a directory
                            if frame_overlay.endswith('.png'):
                                frame_img = frame_overlay
                            # else frame_overlay check if base64 image
                            elif frame_overlay.startswith('data:image/png;base64,'):
                                frame_img = frame_overlay
                            apply_overlay_image(image_path, frame_img, image_path, mode='stretch')
                    except Exception as e:
                        logger.error(f'Error applying frame overlay: {e}')

                    # apply logo overlay to the image if the logo_overlay is not None
                    try:
                        if logo_overlay is not None and logo_overlay != '':
                            logger.info(f'Applying logo overlay')
                            # check if the logo_overlay is a directory
                            if logo_overlay.endswith('.png'):
                                logo_img = logo_overlay
                            # else logo_overlay check if base64 image
                            elif logo_overlay.startswith('data:image/png;base64,'):
                                logo_img = logo_overlay
                            apply_overlay_image(image_path, logo_img, image_path, mode='append', position=logo_position, padding=25)
                    except Exception as e:
                        logger.error(f'Error applying logo overlay: {e}')

                    # deploy each image to the Azure blob storage
                    if save_path is not None and save_path != '':
                        logger.info(f'Uploading image to Azure Blob Storage: {save_path}')
                        img_blob_url = upload_image_to_blob_storage(image_path, save_path)
                        images.append(img_blob_url)
                    else:
                        logger.info(f'No save path provided, returning base64 image')
                        with open(image_path, 'rb') as image_file:
                            images.append(base64.b64encode(image_file.read()).decode('utf-8'))

                return {
                    'images': images
                }

            else:
                raise RuntimeError('No output found, please ensure that the model is correct and that it exists')
        else:
            logger.error(f'HTTP Status code: {queue_response.status_code}')
            logger.error(json.dumps(resp_json, indent=4, default=str))
            return resp_json
    except Exception as e:
        raise


if __name__ == '__main__':
    wait_for_service(url=f'{BASE_URI}/system_stats')
    logger.info('[INFO] ComfyUI API is ready')
    logger.info('[INFO] Starting RunPod Serverless...')
    runpod.serverless.start(
        {
            'handler': handler
        }
    )