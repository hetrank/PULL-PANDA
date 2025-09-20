# OLD: Inefficient processing
def process_data(data):
    result = []
    for item in data:
        if item % 2 == 0:
            result.append(item * 2)
        else:
            result.append(item * 3)
    return result

# NEW: Optimized with list comprehension
def process_data_optimized(data):
    return [item * 2 if item % 2 == 0 else item * 3 for item in data]

# ADDED: Batch processing for large datasets
def process_large_dataset(data, batch_size=1000):
    results = []
    for i in range(0, len(data), batch_size):
        batch = data[i:i+batch_size]
        results.extend(process_data_optimized(batch))
    return results