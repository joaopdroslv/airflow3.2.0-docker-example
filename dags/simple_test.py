from datetime import datetime

from airflow.sdk import dag, task


@dag(
    dag_id="simple_test",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["test"],
)
def simple_test():

    @task
    def initial():
        print("initial task")

    @task
    def middle():
        print("middle task")

    @task
    def end():
        print("end task")

    initial() >> middle() >> end()


dag = simple_test()
