import re


def extract_search_query(input_str):
    match = re.search(r"web_search\[(.*?)\]", input_str.strip())
    if not match:
        raise ValueError("Cannot extract 'web_search'!")
    return match.group(1)


def extract_answer(input_str):
    match = re.search(r"<answer>(.*?)</answer>", input_str.strip())
    if not match:
        return None
    return match.group(1)


def extract_content(input_str, target_tag):
    lines = input_str.strip().split("\n")
    match = re.match(r"<(\w+)>(.*?)</\1>", lines[-1])
    try:
        if not match:
            raise RuntimeError(f"Cannot extract '{target_tag}'!")
        tag, content = match.groups()
        if tag != target_tag:
            raise RuntimeError(
                f"Found different tag '{tag}' instead of '{target_tag}'!")
        return content
    except Exception as e:
        print(e)
        return None
