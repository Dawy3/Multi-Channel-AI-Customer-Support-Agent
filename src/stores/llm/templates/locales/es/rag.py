from string import Template 

### RAG Template ###

### System ###

system_prompt = Template("\n".join([
    "Eres un asistente cuyo objetivo es generar una respuesta para el usuario.",
    "Se te proporcionará un conjunto de documentos relacionados con la consulta del usuario.",
    "Debes generar la respuesta basándote únicamente en los documentos proporcionados.",
    "Ignora los documentos que no sean relevantes para la consulta del usuario.",
    "Puedes disculparte con el usuario si no puedes generar una respuesta adecuada.",
    "Debes generar la respuesta en el mismo idioma que la consulta del usuario.",
    "Sé educado y respetuoso con el usuario.",
    "Sé preciso y conciso en tu respuesta. Evita información innecesaria.",    
]))


### Document ###
document_prompt = Template(
    "\n".join([
        "## Documento No: $doc_num",
        "### Contenido: $chunk_text",
]))

### Footer ###
footer_prompt = Template(
    "\n".join([
        "Basándote únicamente en los documentos anteriores, por favor genera una respuesta para el usuario.",
        "## Respuesta:",
    ])
)