def load_hosts(file_path):
    """
    Parses a hosts-style file and returns a dictionary of records.
    Standard format: IP domain1 [domain2 ...]
    """
    records = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    ip = parts[0]
                    for domain in parts[1:]:
                        records[domain] = ip
    except Exception as e:
        print(f"Error loading hosts file {file_path}: {e}", flush=True)
    return records
