from airflow.decorators import dag, task


@dag(dag_id="poi_finder")
def find_pois():

    @task(task_id="show_context")
    def show_context(**kwargs):
        data = kwargs["dag_run"].conf

        # Access your POIFinderRequest data
        user_id = data.get("user_id")
        location = data.get("location")
        preferences = data.get("preferences")
        max_distance = data.get("max_distance")
        max_results = data.get("max_results")

        print(f"Processing request for user: {user_id}")
        print(f"Location: {location}")
        print(f"Preferences: {preferences}")
        print(f"Max distance: {max_distance}")
        print(f"Max results: {max_results}")

    show_context()


find_pois()
