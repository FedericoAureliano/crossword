# imports
import os
import time
import json
from google.cloud import storage
from crossword.parser import parse_markdown
import vertexai
from vertexai.tuning import sft
from vertexai.generative_models import GenerativeModel

PROJECT_ID = None # Replace with your Project ID on GCS/Gemini API
LOCATION = "us-central1"  # Should be us-central1 for some vertex AI API operations
GCS_BUCKET_NAME = None # Replace with name of your GCS bucket where you'll upload your query batch

if PROJECT_ID is None:
    import os
    if os.path.exists("crossword/secrets.py"):
        from crossword.secrets import AMEESH_PROJECT_ID, AMEESH_BUCKET_NAME
        PROJECT_ID = AMEESH_PROJECT_ID
        GCS_BUCKET_NAME = AMEESH_BUCKET_NAME

def get_crossword(data_dir):
    # an iterable that yields the next loaded md file from the data dir
    for filename in os.listdir(data_dir):
        if filename.endswith(".md"):
            with open(os.path.join(data_dir, filename), 'r') as f:
                md_crossword = f.read()
            yield md_crossword

def prepare_prompt_minis(mini_md_crossword):
    crossword_obj = parse_markdown(mini_md_crossword, check=False)
    words_across = ', '.join([item[0] for item in crossword_obj.across])
    words_down = ', '.join([item[0] for item in crossword_obj.down])
    ft_example = {
        "systemInstruction": {
            "role": "system",
            "parts": [
                {
                    "text": "You are the greatest crossword constructor in the world. You will generate a coherent crossword puzzle square."
                }
            ]
            },
            "contents": [
            {
            "role": "user",
            "parts": [
                {
                "text": "Crossword size: {}\n".format(crossword_obj.size)
                }
            ]
            },
            {
            "role": "model",
            "parts": [
                {
                "text": "Crossword Grid: \n{} \n\n Words Across: {} \n\n Words Down: {}".format(crossword_obj.get_markdown_table(), 
                                                                                              words_across, words_down)
                }
            ]
            },
            ]
    }
    return ft_example

def prepare_finetuning_data(data_dir, prompt_fxn, gcs_output_filename):
    assert GCS_BUCKET_NAME, "GCS_BUCKET_NAME is not set. Please set it in the code or in a secrets.py file."
    bucket = storage.Client().get_bucket(GCS_BUCKET_NAME)
    # load the instructions from the df
    finetuning_requests = []
    crossword_loader = get_crossword(data_dir)
    for crossword in crossword_loader:
        ft_request = prompt_fxn(crossword)
        finetuning_requests.append(json.dumps(ft_request))
    print("Number of cleaned finetuning examples: ", len(finetuning_requests))
    finetuning_uri = f"gs://{GCS_BUCKET_NAME}/bridge_requests/{gcs_output_filename}.jsonl"
    new_blob = bucket.blob(f'bridge_requests/{gcs_output_filename}.jsonl')
    new_blob.upload_from_string('\n'.join(finetuning_requests), content_type='application/jsonl')
    print("Uploaded finetuning data to GCS.")
    return finetuning_uri


def run_finetuning_job(finetune_data_uri):
    assert PROJECT_ID, "PROJECT_ID is not set. Please set it in the code or in a secrets.py file."
    vertexai.init(project=PROJECT_ID, location="us-central1")

    sft_tuning_job = sft.train(
        source_model="gemini-2.0-flash-001",
        # 1.5 and 2.0 models use the same JSONL format
        train_dataset=finetune_data_uri,
    )

    # Polling for job completion
    while not sft_tuning_job.has_ended:
        time.sleep(60)
        sft_tuning_job.refresh()

    print(sft_tuning_job.tuned_model_name)
    print(sft_tuning_job.tuned_model_endpoint_name)
    print(sft_tuning_job.experiment)

def sample_from_finetuned_model(model_path: str, size: int):
    '''
    model_path should be a path to a Finetuned project job from Vertex AI
    '''
    sft_tuning_job = sft.SupervisedTuningJob(model_path)
    tuned_model = GenerativeModel(sft_tuning_job.tuned_model_endpoint_name)
    response = tuned_model.generate_content("Crossword size: {}\n".format(size))
    crossword = response.candidates[0].content.text
    print(crossword)
    return crossword