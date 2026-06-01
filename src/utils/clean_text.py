import re

def text_cleaner(text):
    # Remove markdown image links
    text = re.sub(r'!\[img-\d+\.\w+\]\(img-\d+\.\w+\)', '', text)

    # Remove horizontal rules
    text = re.sub(r'[-*]{3,}', '', text)

    # Remove markdown headers
    text = re.sub(r'#{1,6}\s+', '', text)

    # Remove markdown bold/italic
    text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^\*]+)\*', r'\1', text)

    # Remove emojis (keep Arabic, English, numbers)
    text = re.sub(r'[^\w\s\u0600-\u06FF.,!?;:()\-\'\"\/&@#$%]', '', text)

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove standalone single characters
    text = re.sub(r'\s+[a-zA-Z]\s+', ' ', text)

    # Remove multiple dots/dashes
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r'-{2,}', '-', text)

    return text.strip()