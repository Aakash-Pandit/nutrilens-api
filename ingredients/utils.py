import re
import json

def parse_ingredients_to_json(input_text):
    # 1. Clean up the string (remove extra newlines and markdown bold markers)
    clean_text = input_text.replace("**", "").replace("\\n", "\n")
    
    # 2. Extract the Summary and Verdict first (they are usually at the end)
    summary_match = re.search(r"Summary:\s*(.*)", clean_text, re.DOTALL)
    verdict_match = re.search(r"Verdict:\s*(.*)", clean_text, re.DOTALL)
    
    summary = summary_match.group(1).split("Verdict:")[0].strip() if summary_match else ""
    verdict = verdict_match.group(1).strip() if verdict_match else ""
    
    # 3. Use Regex to find ingredient names, optional percentages, and descriptions
    # Pattern looks for: Header: [Description]
    pattern = r"([^:\n]+):\s*\n?([^:]+?)(?=\n\n|\n[A-Z]|$)"
    matches = re.findall(pattern, clean_text)
    
    ingredients_list = []
    
    # 4. Iterate through matches to structure the data
    for name, description in matches:
        name = name.strip()
        description = description.strip()
        
        # Skip 'Summary' and 'Verdict' if they were caught in the loop
        if name in ["Summary", "Verdict"]:
            continue
            
        # Extract percentage if it exists in the name (e.g., "Besan (10%)")
        percentage_match = re.search(r"\((\d+%)\)", name)
        percentage = percentage_match.group(1) if percentage_match else None
        
        # Clean the name (remove the percentage part from the title)
        clean_name = re.sub(r"\(\d+%\)", "", name).strip()
        
        ingredients_list.append({
            "ingredient": clean_name,
            "percentage": percentage,
            "description": description
        })

    # 5. Build Final Dictionary (return dict for DB/API; caller can json.dumps if needed)
    data = {
        "product_metadata": {
            "name": "Rajasthani Mix",
            "summary": summary,
            "verdict": verdict
        },
        "ingredients": ingredients_list
    }
    return data