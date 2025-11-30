from online_estimator_version import run_iterative_selector

# Process multiple PRs
pr_list = [6, 7]  # 1, 2 , 3, 4, 5, 6, 7
results, selector = run_iterative_selector(pr_list)