def load(file_path):
    env = {}
    with open(file_path, 'r') as f:
        for line in f:
            key, value = line.strip().split('=', 1)
            env[key] = value
    return env