import json
import re


def extract_plan_result(json_string):
    data = json.loads(json_string)
    query_list = []
    for k, v in data.items():
        query_list.append(v)
    return query_list


def remove_xml_blocks(markdown_text):
    # This pattern matches triple backtick blocks labeled as xml
    pattern = r"```xml(.*?)```"
    # re.DOTALL makes '.' match newlines as well
    cleaned_text = re.sub(pattern, r"\1", markdown_text, flags=re.DOTALL)
    return cleaned_text


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


def remove_think_cot(input_str):
    cleaned_str = re.sub(r"<think>.*?</think>\s*", "", input_str, flags=re.DOTALL)
    return cleaned_str.strip()
