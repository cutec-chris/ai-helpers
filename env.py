def load(file_path):
    env = {}
    with open(file_path, 'r') as f:
        for line in f:
            if line != '\n'\
            and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                env[key] = value
    return env