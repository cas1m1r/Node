import json, os
from pathlib import Path


class ArchetypeCharacter:
    def __init__(self, name, title, role, system_prompt, tone, core_functions, appearance):
        self.name = name
        self.title = title
        self.role = role
        self.system_prompt = system_prompt
        self.tone = tone
        self.core_functions = core_functions
        self.appearance = appearance

    def to_prompt(self):
        return (
            f"{self.name} ({self.title})\n"
            f"Role: {self.role}\n"
            f"Tone: {', '.join(self.tone)}\n"
            f"Style: {self.appearance['style']}\n"
            f"System Prompt:\n{self.system_prompt}"
        )


def load_archetypes(directory: str):
    """
    Load all archetype JSON files from a directory and return a list of ArchetypeCharacter objects.
    """
    archetypes = []
    for file_path in Path(directory).glob("*.json"):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            char = ArchetypeCharacter(
                name=data["archetype"],
                title=data["title"],
                role=data["role"],
                system_prompt=data["system_prompt"],
                tone=data["tone"],
                core_functions=data["core_functions"],
                appearance=data["appearance"]
            )
            archetypes.append(char)
    return archetypes


def load_personas(path_in):
    personas = {}
    for fname in os.listdir(path_in):
        character = fname.split('.')[0].replace('_', ' ')
        if character not in personas.keys():
            print(f'Adding {character}')
            personas[character] = json.loads(
                open(os.path.join(path_in, fname), 'r').read())
    return personas