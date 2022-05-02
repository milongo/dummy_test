from typing import Optional
from clearml import Task


def create_enqueue_controller(
    building_id: int,
    building_name: str,
    application_id: int,
    control_zone: Optional[str] = None,
) -> Task:
    """
    Create the enqueue controller task based on the building name, application name and control zone name provided.

    Args:
        building_id (int): The id of the building
        building_name (str): The name of the building
        application_id (int): The id of the application
        control_zone (Optional[str], optional): The name of the control zone. Defaults to None.

    Returns:
        Task: The enqueue controller task
    """

    clearml_task = Task.create(
        project_name="Emilio/dummy_test",
        task_name="dummy_create_enqueue",
        task_type=Task.TaskTypes.controller,
        repo="keras_mnist",
        branch="master",
        script="./dummy_pipeline.py",
        requirements_file="./requirements_file",
        docker=None,
        # packages=True,
        add_task_init_call=False,
    )

    # TEMPORARY -- this info will be injected from the client side (username or others)

    parameters = {
        "building_id": 9,
        "building_name": "MTL-CLEARML-911",
        "application_id": "1",
        "application_name": "dummy_test",
        "control_zone_id": "dummy_control",
        "client": "client_1",
    }
    clearml_task.connect(parameters)

    queue_name = "cpu"
    Task.enqueue(task=clearml_task.id, queue_name=queue_name)
    return clearml_task.id


if __name__ == "__name__":

    create_enqueue_controller(1, "1", 1, "1")
