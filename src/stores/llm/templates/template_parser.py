import os


class TemplateParser:
    
    def __init__(self, language: str=None, default_language= "en"):
        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.default_language = default_language
        self.language = None
        self.set_language(language)
        
    def set_language(self, language: str):
        requested = language if language else self.default_language
        language_path = os.path.join(self.current_path, "locales", requested)
        if os.path.exists(language_path):
            self.language = requested
        else:
            self.language = self.default_language
        
    def get(self, group: str, key: str, vars: dict={}):
        """Check if there's group(locale's files) in inside each group have 'keys(EX:system_prompt)' have variables """
        
        if not group or not key:
            return None
        
        # Ex: Users/files/src/llm/templates -> locales -> ar/en.py
        group_path = os.path.join(self.current_path, 'locales', self.language, f"{group}.py") 
        targeted_langage = self.language
        if not os.path.exists(group_path):
            group_path = os.path.join(self.current_path, 'locales', self.default_language, f"{group}.py") 
            targeted_langage= self.default_language
        if not os.path.exists(group_path):
            return None
        
        # import group module
        module = __import__(f"stores.llm.templates.locales.{targeted_langage}.{group}", fromlist=[group])
        
        if not module:
            return None
        
        key_attribute = getattr(module, key) # get attribute (from, attribute)
        return key_attribute.substitute(vars)
        
        