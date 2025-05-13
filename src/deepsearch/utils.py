import json
import re


def extract_plan_result(json_string):
    data = json.loads(json_string)
    query_list = []
    for k, v in data.items():
        query_list.append(v)
    return query_list


# def extract_search_query(input_str):
#     match = re.search(r"web_search\[(.*?)\]", input_str.strip())
#     if not match:
#         raise ValueError("Cannot extract 'web_search'!")
#     return match.group(1)


# def extract_answer(input_str):
#     match = re.search(r"<answer>(.*?)</answer>", input_str.strip())
#     if not match:
#         return None
#     return match.group(1)


def extract_content(input_str, target_tag):
    pattern = rf"<{target_tag}>(.*?)</{target_tag}>"
    matches = re.findall(pattern, input_str, re.DOTALL)
    try:
        if not matches:
            raise RuntimeError(f"Cannot extract '{target_tag}'!")
        content = matches[-1].strip()
        return content
    except Exception as e:
        print(e)
        return None


def extract_last_json_block(markdown_text):
    # Find all code blocks that might contain JSON
    json_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)```', markdown_text)
    
    if not json_blocks:
        return None
    return json_blocks[-1].strip()
