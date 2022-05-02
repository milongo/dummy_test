import os
from clearml import Task, Dataset, StorageManager
from PredictionModule.utils.logging_convenience import logging_standard

log_path = os.path.join(os.getcwd(), "test.log")
logging_standard(level="info", log_filename=log_path)


@timer_logging
def download_from_s3(building_name: str):
    path_to_folder = StorageManager.download_folder(
        remote_url="s3://bbai-ai-data/" + building_name
    )
    return path_to_folder


@timer_logging
def download_from_clearml(building_name: str):
    dataset = Dataset.get(dataset_project=building_name, dataset_name=building_name)
    path_to_data = dataset.get_local_copy()
    return path_to_data


if __name__ == "__main__":

    path_to_data = download_from_clearml("TOR-BGO-150KingW")
    x = 1
