scans = {}
next_scan_id = 1


def save_scan(scan_result):
    global next_scan_id

    scan_id = next_scan_id
    next_scan_id += 1

    scan_result["id"] = scan_id
    scans[scan_id] = scan_result

    return scan_id


def get_scan_by_id(scan_id: int):
    return scans.get(scan_id)