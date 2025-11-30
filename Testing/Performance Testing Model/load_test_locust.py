import time
from locust import User, task, between, events

# Import your main pipeline
from iterative_prompt_selector import IterativePromptSelector

# Create one shared instance so heavy init happens only once
selector = IterativePromptSelector()


class PRReviewUser(User):
    """
    Each Locust user = one concurrent PR review runner.
    We are not doing HTTP calls, just calling Python code directly.
    """

    # Wait between task runs for each user (you can tweak this)
    wait_time = between(1, 3)

    @task
    def review_pr_1(self):
        """
        Run the full pipeline for PR #1 once.
        Locust will call this many times, possibly in parallel.
        """
        pr_number = 1  # we keep it fixed as you decided

        start_time = time.time()
        try:
            # Run your full review pipeline (no GitHub comment posting)
            selector.process_pr(pr_number, post_to_github=False)

            total_ms = (time.time() - start_time) * 1000.0

            # Tell Locust that a "request" succeeded
            events.request.fire(
                request_type="PR",  # shows as "Type" in the UI
                name="process_pr_1",  # "Name" column
                response_time=total_ms,  # in milliseconds
                response_length=0,
                exception=None,
            )
        except Exception as e:
            total_ms = (time.time() - start_time) * 1000.0

            # Tell Locust that a "request" failed
            events.request.fire(
                request_type="PR",
                name="process_pr_1",
                response_time=total_ms,
                response_length=0,
                exception=e,
            )
