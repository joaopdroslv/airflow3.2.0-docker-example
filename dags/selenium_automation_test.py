from __future__ import annotations

import logging
from datetime import timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

# from airflow.utils.dates import days_ago

log = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "automation",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=3),
}

SEARCH_TERM = "running automations with Apache Airflow"
HEADLESS = True  # False if you need to see the browser
IMPLICIT_WAIT_SECONDS = 10
PAGE_LOAD_TIMEOUT = 60


def _build_driver():
    """Return a Selenium Chrome WebDriver ready to use."""

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    options = Options()

    if HEADLESS:
        options.add_argument("--headless=new")  # modern headless flag
    options.add_argument("--no-sandbox")  # required inside Docker/CI
    options.add_argument("--disable-dev-shm-usage")  # prevents crashes on low /dev/shm
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    # If chromedriver is on PATH, Service() with no arguments works fine.
    # Otherwise pass: Service(executable_path="/path/to/chromedriver")
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)

    driver.implicitly_wait(IMPLICIT_WAIT_SECONDS)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

    return driver


def open_google_and_search(search_term: str, **context) -> None:
    """
    Open Google, search for *search_term*, and push the results page title
    to XCom (key ``results_page_title``).

    Saves a screenshot to ``/temp/screenshots/google_search_<run_id>.png``
    and detects results via multiple selectors, since Google's layout changes
    frequently.
    """

    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    driver = _build_driver()

    try:
        log.info("Opening Google...")
        driver.get("https://www.google.com")

        # Accept cookies banner if present
        try:
            accept_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(., 'Accept')]")
                )
            )
            accept_btn.click()
            log.info("Accepted cookies banner.")
        except Exception:
            log.info("No cookies banner found — continuing.")

        # Locate the search box
        search_box = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )

        log.info("Typing search term: '%s'", search_term)
        search_box.clear()
        search_box.send_keys(search_term)
        search_box.send_keys(Keys.RETURN)

        # Wait for ANY of these selectors — Google changes its layout often
        result_selectors = [
            (By.ID, "search"),
            (By.ID, "rso"),  # organic results container
            (By.CSS_SELECTOR, "div[data-async-context]"),
            (By.CSS_SELECTOR, "h3"),  # at least one result title
        ]

        result_found = False
        for by, selector in result_selectors:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((by, selector))
                )
                log.info("Results detected via selector: %s='%s'", by, selector)
                result_found = True
                break
            except Exception:
                continue

        # Save screenshot for debugging
        screenshot_path = (
            f"/temp/screenshots/google_search_{context['run_id'].replace(':', '_')}.png"
        )
        driver.save_screenshot(screenshot_path)
        log.info("Screenshot saved to: %s", screenshot_path)

        if not result_found:
            log.warning(
                "No known result selector matched. Page title: '%s'", driver.title
            )
            log.warning("Page source snippet: %s", driver.page_source[:500])

        page_title = driver.title
        log.info("Results page title: '%s'", page_title)
        context["ti"].xcom_push(key="results_page_title", value=page_title)

    finally:
        driver.quit()
        log.info("WebDriver closed.")


def validate_search_result(**context) -> None:
    """
    Pull the page title from XCom and verify the search actually ran.
    Replace this with whatever post-processing your automation needs.
    """

    ti = context["ti"]
    title = ti.xcom_pull(task_ids="open_google_and_search", key="results_page_title")

    if not title:
        raise ValueError("No page title was captured — search may have failed.")

    log.info("Validating result — page title received: '%s'", title)

    if SEARCH_TERM.split()[0].lower() not in title.lower():
        log.warning(
            "Search term '%s' not found in page title '%s'. "
            "Google may have redirected or changed its layout.",
            SEARCH_TERM,
            title,
        )
    else:
        log.info("Validation passed!")


with DAG(
    dag_id="google_search_automation",
    description="Opens Google and searches for a term using Selenium (headless Chrome).",
    default_args=DEFAULT_ARGS,
    schedule="0 8 * * *",  # every day at 08:00 — same cron syntax you already know
    # start_date=days_ago(1),
    catchup=False,  # don't backfill missed runs
    max_active_runs=1,  # avoid parallel browser sessions
    tags=["selenium", "automation", "google", "test"],
) as dag:

    search_task = PythonOperator(
        task_id="open_google_and_search",
        python_callable=open_google_and_search,
        op_kwargs={"search_term": SEARCH_TERM},
    )
    validation_task = PythonOperator(
        task_id="validate_search_result",
        python_callable=validate_search_result,
    )

    search_task >> validation_task
